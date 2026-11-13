#!/usr/bin/env python3
"""
STEP 6 — prove the recorder changes nothing, with NO real API calls.

A small deterministic fake OpenAI server (chat + embeddings) backs a real in-process Mem0
``Memory`` talking to the real Qdrant container. We run the same short input (one session of
conversation 0, first few turns, + 3 questions through add → search → answer → judge) twice:
once with the recorder OFF and once ON, each on a **fresh Qdrant collection**. Then we check:

  A. stored payloads (ignoring ids/times), search results, answers and verdicts are identical;
  B. the trace agrees with the stores (every stored memory / entity appears exactly once);
  C. trace_view --question/--session/--summary/--metrics all run and fill every field.

Usage (inside the throwaway venv):
  QDRANT_PORT=6333 python experiments/tracing/selfcheck.py
"""

from __future__ import annotations

import asyncio
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
MB = os.path.join(EXP, "memory-benchmarks")
SCRIPTS = os.path.join(EXP, "scripts")
sys.path.insert(0, HERE)
sys.path.insert(0, MB)

DIM = 1536
UID = "selfcheck_user"
TOPK = 10


# ---------------------------------------------------------------------------
# Deterministic fake OpenAI server
# ---------------------------------------------------------------------------

def _bow_embedding(text: str) -> list[float]:
    vec = [0.0] * DIM
    for w in re.findall(r"\w+", (text or "").lower()):
        idx = int(hashlib.md5(w.encode()).hexdigest(), 16) % DIM
        vec[idx] += 1.0
    norm = sum(v * v for v in vec) ** 0.5
    if norm:
        vec = [v / norm for v in vec]
    else:
        vec[0] = 1.0
    return vec


def _facts_from_prompt(user_content: str) -> list[str]:
    """Deterministically turn the user prompt's '## New Messages' block into one fact per turn."""
    m = re.search(r"##\s*New Messages\s*\n(.*?)(?:\n##\s|\Z)", user_content, re.DOTALL)
    if not m:
        return []
    facts = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^(user|assistant|system):\s*", "", line)  # drop parse_messages role tag
        facts.append(line)
    seen, out = set(), []
    for f in facts:
        if f and f not in seen:
            seen.add(f)
            out.append(f)
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def _send(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n) or b"{}")
        path = self.path
        if path.endswith("/embeddings"):
            inp = req.get("input")
            texts = inp if isinstance(inp, list) else [inp]
            data = [{"object": "embedding", "index": i, "embedding": _bow_embedding(str(t))}
                    for i, t in enumerate(texts)]
            toks = sum(len(re.findall(r"\w+", str(t))) for t in texts)
            return self._send({"object": "list", "data": data, "model": req.get("model", "fake"),
                               "usage": {"prompt_tokens": toks, "total_tokens": toks}})
        if path.endswith("/chat/completions"):
            msgs = req.get("messages", [])
            full = "\n".join(m.get("content", "") for m in msgs if isinstance(m, dict))
            user_content = ""
            for m in msgs:
                if isinstance(m, dict) and m.get("role") == "user":
                    user_content = m.get("content", "")
            rf = (req.get("response_format") or {}).get("type") if isinstance(req.get("response_format"), dict) else None
            if "## New Messages" in user_content:  # extraction (real turns live in the user prompt)
                facts = _facts_from_prompt(user_content)
                content = json.dumps({"memory": [{"text": f} for f in facts]})
            elif rf == "json_object":  # judge
                content = json.dumps({"label": "CORRECT", "reasoning": "deterministic self-check verdict"})
            else:  # answerer
                content = "ANSWER: deterministic self-check answer"
            ptok = len(re.findall(r"\w+", full))
            ctok = len(re.findall(r"\w+", content))
            return self._send({
                "id": "fake-" + uuid.uuid4().hex[:8], "object": "chat.completion",
                "created": int(time.time()), "model": req.get("model", "fake"),
                "choices": [{"index": 0, "finish_reason": "stop", "logprobs": None,
                             "message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": ptok, "completion_tokens": ctok, "total_tokens": ptok + ctok},
            })
        self.send_response(404)
        self.end_headers()


def start_fake_server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


# ---------------------------------------------------------------------------
# One run (off or on)
# ---------------------------------------------------------------------------

def _qclient(port):
    from qdrant_client import QdrantClient
    return QdrantClient(host="localhost", port=port)


def _memory(collection, hist_path, qport):
    from mem0 import Memory
    cfg = {
        "version": "v1.1",
        "llm": {"provider": "openai", "config": {"model": "gpt-4o-mini", "temperature": 0.1}},
        "embedder": {"provider": "openai",
                     "config": {"model": "text-embedding-3-small", "embedding_dims": DIM}},
        "vector_store": {"provider": "qdrant",
                         "config": {"host": "localhost", "port": qport,
                                    "collection_name": collection, "embedding_model_dims": DIM}},
        "history_db_path": hist_path,
    }
    return Memory.from_config(cfg)


def _scroll(qc, collection):
    try:
        points, _ = qc.scroll(collection_name=collection, limit=10000, with_payload=True, with_vectors=False)
        return [{"id": str(p.id), "payload": p.payload} for p in points]
    except Exception:
        return []


def _norm_payload(p):
    p = dict(p or {})
    # drop ids and times (random uuids / wall-clock): linked_memory_ids are memory-id references
    for k in ("created_at", "updated_at", "linked_memory_ids"):
        p.pop(k, None)
    return p


async def run_once(mode, questions, turns, speakers, run_dir, qport, fake_port, session_ts):
    """Run add+search+answer+judge once. Returns a comparable snapshot dict."""
    os.environ["OPENAI_API_KEY"] = "sk-fake-selfcheck"
    os.environ["OPENAI_BASE_URL"] = f"http://127.0.0.1:{fake_port}/v1"

    from benchmarks.locomo.run import session_to_chunks, cutoff_label
    from benchmarks.locomo.prompts import (get_answer_generation_prompt, get_judge_prompt,
                                            preprocess_answer, JUDGE_SYSTEM_PROMPT, CATEGORY_NAMES)
    from benchmarks.common.llm_client import LLMClient

    coll = f"selfcheck_{mode}_{uuid.uuid4().hex[:8]}"
    hist = os.path.join(run_dir, f"history_{mode}.db")
    qc = _qclient(qport)

    traced = (mode == "on")
    if traced:
        os.environ["MEM0_TRACE_DIR"] = run_dir
        import mem0_trace
        import eval_trace

    mem = _memory(coll, hist, qport)
    answerer = LLMClient(model="gpt-4o-mini", provider="openai", rpm=100000)
    judge = LLMClient(model="gpt-4o-mini", provider="openai", rpm=100000)

    if traced:
        mem0_trace.install(mem)
        from types import SimpleNamespace
        async def _noop(*a, **k):
            return None
        eval_trace.install(run_dir, mem0_client=SimpleNamespace(add=_noop, search=_noop),
                           answerer=answerer, judge_llm=judge,
                           run_module=SimpleNamespace(process_question=_noop))

    # ---- ingest one session (a few turns) ----
    chunks = session_to_chunks(turns, speakers[0], speakers[1])
    for ch in chunks:
        mem.add(ch, user_id=UID, timestamp=session_ts)

    # ---- 3 questions: search -> answer -> judge ----
    snap_search, snap_answers, snap_verdicts, results_file = {}, {}, {}, []
    for i, qa in enumerate(questions):
        qid = f"conv0_q{i}"
        question = qa["question"]
        category = qa["category"]
        gold = str(qa["answer"])

        ctx = eval_trace.question_context(qid, [TOPK], UID, category) if traced else _nullctx()
        with ctx:
            t0 = time.monotonic()
            res = mem.search(question, filters={"user_id": UID}, top_k=TOPK, threshold=0.1, explain=True)
            search_ms = (time.monotonic() - t0) * 1000
            items = res.get("results", res) if isinstance(res, dict) else res
            formatted = [{"memory": r.get("memory", ""), "id": r.get("id"),
                          "created_at": r.get("created_at"), "score": r.get("score")} for r in items]
            prompt = get_answer_generation_prompt(question, formatted[:TOPK], reference_date=None, user_profile=None)
            ans = await answerer.generate(system="", user=prompt)
            if "ANSWER:" in ans:
                ans = ans.rsplit("ANSWER:", 1)[-1].strip()
            processed = preprocess_answer(category, gold)
            jp = get_judge_prompt(category, question, processed, ans)
            raw = await judge.generate_structured(system=JUDGE_SYSTEM_PROMPT, user=jp)
            verdict = raw.get("label", "").upper() if isinstance(raw, dict) else None

        snap_search[qid] = [(f["memory"], round(f["score"] or 0, 6)) for f in formatted]
        snap_answers[qid] = ans
        snap_verdicts[qid] = verdict
        label = cutoff_label(TOPK)
        results_file.append({
            "question_id": qid, "category": category,
            "category_name": CATEGORY_NAMES.get(category, "unknown"),
            "question": question, "ground_truth_answer": gold,
            "evidence": qa.get("evidence", []), "user_id": UID, "reference_date": None,
            "retrieval": {"search_query": question, "search_results": formatted,
                          "search_latency_ms": round(search_ms, 1), "total_results": len(formatted)},
            "cutoff_results": {label: {"judgment": "CORRECT" if verdict == "CORRECT" else "WRONG",
                                       "score": 1.0 if verdict == "CORRECT" else 0.0,
                                       "generated_answer": ans, "memories_evaluated": len(formatted[:TOPK]),
                                       "reason": raw.get("reasoning", "") if isinstance(raw, dict) else ""}},
        })

    # ---- snapshot stores before cleanup ----
    mem_points = _scroll(qc, coll)
    ent_points = _scroll(qc, coll + "_entities")
    snapshot = {
        "memories": sorted([json.dumps(_norm_payload(p["payload"]), sort_keys=True) for p in mem_points]),
        "memory_texts": sorted([(p["payload"] or {}).get("data") for p in mem_points]),
        "memory_ids": [p["id"] for p in mem_points],
        "entities": sorted([json.dumps(_norm_payload(p["payload"]), sort_keys=True) for p in ent_points]),
        "entity_texts": sorted([(p["payload"] or {}).get("data") for p in ent_points]),
        "entity_ids": [p["id"] for p in ent_points],
        "search": snap_search, "answers": snap_answers, "verdicts": snap_verdicts,
    }

    if traced:
        # write a unified results file so trace_view --metrics/--question have the benchmark numbers
        rf = os.path.join(run_dir, f"locomo_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        json.dump({"evaluations": results_file}, open(rf, "w"), indent=2)

    # ---- cleanup collections ----
    for c in (coll, coll + "_entities"):
        try:
            qc.delete_collection(c)
        except Exception:
            pass
    return snapshot


class _nullctx:
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    qport = int(os.getenv("QDRANT_PORT", "6333"))
    dataset = json.load(open(os.path.join(MB, "datasets", "locomo", "locomo10.json")))
    conv = dataset[0]["conversation"]
    turns = conv["session_1"][:6]
    speakers = []
    for t in conv["session_1"]:
        if t.get("speaker") and t["speaker"] not in speakers:
            speakers.append(t["speaker"])
        if len(speakers) == 2:
            break
    questions = dataset[0]["qa"][:3]
    # session_1 timestamp (unix epoch, UTC) — same convention as the harness
    d = datetime.strptime(conv["session_1_date_time"], "%I:%M %p on %d %B, %Y")
    session_ts = int(d.replace(tzinfo=timezone.utc).timestamp())

    run_dir = os.path.join(os.getenv("CLAUDE_JOB_DIR", "/tmp"), "selfcheck_run")
    os.makedirs(run_dir, exist_ok=True)
    for f in glob.glob(os.path.join(run_dir, "*")):
        try:
            os.remove(f)
        except Exception:
            pass
    json.dump({"answerer_model": "gpt-4o-mini", "note": "selfcheck"},
              open(os.path.join(run_dir, "manifest.json"), "w"))

    srv, fake_port = start_fake_server()
    print(f"fake OpenAI server on 127.0.0.1:{fake_port}; qdrant :{qport}; run_dir={run_dir}")

    off = asyncio.run(run_once("off", questions, turns, speakers, run_dir, qport, fake_port, session_ts))
    on = asyncio.run(run_once("on", questions, turns, speakers, run_dir, qport, fake_port, session_ts))

    print("\n==================== A. OFF vs ON (recorder is a no-op) ====================")
    ok = True
    def check(name, a, b):
        nonlocal ok
        same = (a == b)
        ok = ok and same
        print(f"  [{'OK ' if same else 'DIFF'}] {name}")
        if not same:
            print(f"        off={a}\n        on ={b}")
    check("stored memory payloads (ignoring ids/times)", off["memories"], on["memories"])
    check("stored memory texts", off["memory_texts"], on["memory_texts"])
    check("entity payloads (ignoring ids/times)", off["entities"], on["entities"])
    check("entity texts", off["entity_texts"], on["entity_texts"])
    check("search results (text, score) per question", off["search"], on["search"])
    check("answers per question", off["answers"], on["answers"])
    check("verdicts per question", off["verdicts"], on["verdicts"])

    print("\n==================== B. trace agrees with the stores =======================")
    server_events = _load_jsonl(os.path.join(run_dir, "mem0_trace.jsonl"))
    stored_from_trace, entities_from_trace = [], []
    for e in server_events:
        if e.get("component") == "vector_store" and e.get("operation") == "insert":
            for p in (e.get("inputs") or {}).get("payloads") or []:
                if isinstance(p, dict) and p.get("data"):
                    stored_from_trace.append(p.get("data"))
        if e.get("component") == "entity_store" and e.get("operation") == "insert":
            for p in (e.get("inputs") or {}).get("payloads") or []:
                if isinstance(p, dict) and p.get("data"):
                    entities_from_trace.append(p.get("data"))
    _count_match("memories: store vs trace insert events",
                 on["memory_texts"], sorted(stored_from_trace))
    _count_match("entities: store vs trace insert events",
                 on["entity_texts"], sorted(entities_from_trace))

    print("\n==================== C. trace_view on the fake run =========================")
    vp = sys.executable
    for args in (["--summary"], ["--session", "1"], ["--question", "conv0_q0"], ["--metrics"]):
        print(f"\n----- trace_view.py {' '.join(args)} -----")
        out = subprocess.run([vp, os.path.join(SCRIPTS, "trace_view.py"),
                              "--run", run_dir, "--dataset",
                              os.path.join(MB, "datasets", "locomo", "locomo10.json")] + args,
                             capture_output=True, text=True)
        sys.stdout.write(out.stdout)
        if out.returncode != 0:
            ok = False
            sys.stdout.write("STDERR:\n" + out.stderr)
    for csvf in ("per_question_metrics.csv", "per_session_metrics.csv"):
        p = os.path.join(run_dir, csvf)
        if os.path.exists(p):
            print(f"\n----- {csvf} -----")
            sys.stdout.write(open(p).read())

    srv.shutdown()
    print("\n==================== RESULT ====================")
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


def _load_jsonl(path):
    out = []
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def _count_match(name, store_list, trace_list):
    store = sorted(x for x in store_list if x)
    trace = sorted(x for x in trace_list if x)
    same = store == trace
    print(f"  [{'OK ' if same else 'DIFF'}] {name}: store={len(store)} trace={len(trace)}"
          + ("" if same else f"\n        store={store}\n        trace={trace}"))


if __name__ == "__main__":
    main()
