"""
run_reader.py — read-only joiner for LongMemEval runs under experiments/runs/.

Feeds the monitor's Run view. It joins, per run:
  - manifest.json
  - the pinned dataset index (longmemeval.sqlite) for planned questions + add-unit totals
  - predicted_<project>/<qid>.json  (per-question results as they complete)
  - longmemeval_results_*.json       (unified metrics, once finished)
  - mem0_trace.jsonl[.gz]            (server trace: add/extraction/search/scoring)
  - eval_trace.jsonl[.gz]            (eval trace: answer + judge prompts/verdicts)
  - results/oss/longmemeval_gpt5.json (Mem0's published gpt-5 per-question verdict)

Everything degrades gracefully while a run is still going: traces are plain .jsonl during
the run (readable line-by-line) and only gzipped at the end, so the same reader works live.
Nothing here writes, runs, or imports the benchmark.
"""

from __future__ import annotations

import glob
import gzip
import json
import os
import random
import sqlite3
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXP = os.path.dirname(_HERE)
RUNS_DIR = os.path.join(_EXP, "runs")
DB_PATH = os.environ.get("LME_DB", os.path.join(_HERE, "longmemeval.sqlite"))
PUBLISHED_GPT5 = os.path.join(_EXP, "memory-benchmarks", "results", "oss", "longmemeval_gpt5.json")

CUTOFFS = [200, 50, 20, 10]


# --------------------------------------------------------------------------- io helpers
def _load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _open_any(path):
    return gzip.open(path, "rt", encoding="utf-8") if path.endswith(".gz") else open(path, encoding="utf-8")


def _trace_path(run_dir, base):
    for cand in (os.path.join(run_dir, base), os.path.join(run_dir, base + ".gz")):
        if os.path.exists(cand):
            return cand
    return None


def iter_events(path):
    if not path or not os.path.exists(path):
        return
    try:
        with _open_any(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
    except Exception:
        return


def split_user_id(uid):
    """longmemeval_<qid>_<run_id> -> (qid, run_id). run_id is always the final field."""
    if not uid or not uid.startswith("longmemeval_"):
        return None, None
    rest = uid[len("longmemeval_"):]
    qid, _, run_id = rest.rpartition("_")
    return (qid or None), (run_id or None)


# --------------------------------------------------------------------------- dataset
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def reproduce_sample(manifest):
    """Reproduce the runner's stratified sample from manifest sample_args (mirror of run.py)."""
    args = (manifest or {}).get("sample_args", "") or ""
    toks = args.split()
    per_type, seed, selected, all_q = 5, 42, None, False
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == "--per-type" and i + 1 < len(toks):
            per_type = int(toks[i + 1]); i += 2; continue
        if t == "--seed" and i + 1 < len(toks):
            seed = int(toks[i + 1]); i += 2; continue
        if t == "--question-types" and i + 1 < len(toks):
            selected = toks[i + 1].split(","); i += 2; continue
        if t == "--all-questions":
            all_q = True; i += 1; continue
        i += 1

    conn = _db()
    rows = [dict(r) for r in conn.execute(
        "SELECT question_id, question_type, n_add_units, n_evidence, n_sessions, is_abstention FROM questions")]
    conn.close()

    if all_q:
        chosen = rows
    else:
        typefilter = set(selected) if selected else None
        groups = {}
        for r in rows:
            if typefilter and r["question_type"] not in typefilter:
                continue
            groups.setdefault(r["question_type"], []).append(r)
        for g in groups.values():
            g.sort(key=lambda r: r["question_id"])
        rng = random.Random(seed)
        chosen = []
        for qtype in sorted(groups):
            g = groups[qtype]
            chosen.extend(rng.sample(g, min(per_type, len(g))))
    chosen.sort(key=lambda r: r["question_id"])
    return chosen


def _question_meta(qids):
    if not qids:
        return {}
    conn = _db()
    out = {}
    qmarks = ",".join("?" * len(qids))
    for r in conn.execute(
        f"SELECT question_id, question_type, question, answer, question_date, n_add_units, "
        f"n_evidence, n_sessions, is_abstention FROM questions WHERE question_id IN ({qmarks})",
        list(qids),
    ):
        out[r["question_id"]] = dict(r)
    conn.close()
    return out


def _evidence_pairs(qid):
    """Map first-user-message content -> (session_id, is_evidence) for one question's haystack.

    Lets us tag a stored memory (via its creating add's messages) as coming from an evidence
    session, and link an add-unit back to the dataset session.
    """
    conn = _db()
    sess = {r["session_id"]: r["is_evidence"] for r in conn.execute(
        "SELECT session_id, is_evidence FROM links WHERE question_id = ?", (qid,))}
    out = {}
    if sess:
        qmarks = ",".join("?" * len(sess))
        for r in conn.execute(
            f"SELECT session_id, content FROM turns WHERE session_id IN ({qmarks}) AND role='user'",
            list(sess),
        ):
            key = (r["content"] or "").strip()[:200]
            if key and key not in out:
                out[key] = {"session_id": r["session_id"], "is_evidence": bool(sess[r["session_id"]])}
    conn.close()
    return out


# --------------------------------------------------------------------------- published gpt5
_PUB = {"mtime": None, "map": {}}


def published_map():
    try:
        mt = os.path.getmtime(PUBLISHED_GPT5)
    except OSError:
        return {}
    if _PUB["mtime"] == mt:
        return _PUB["map"]
    data = _load_json(PUBLISHED_GPT5) or {}
    m = {}
    for e in data.get("evaluations", []):
        cr = e.get("cutoff_results")
        if not cr:
            continue
        top = cr.get("top_200") or next(iter(cr.values()), {})
        m[e["question_id"]] = {
            "judgment": top.get("judgment"),
            "answer": top.get("generated_answer"),
            "score": top.get("score"),
            "judge_raw": top.get("judge_raw"),
            "cutoff": "top_200",
        }
    _PUB["mtime"] = mt
    _PUB["map"] = m
    return m


# --------------------------------------------------------------------------- runs
def is_lme_run(name, manifest):
    if manifest and manifest.get("benchmark") == "longmemeval":
        return True
    return name.startswith("lme")


def list_runs():
    out = []
    if not os.path.isdir(RUNS_DIR):
        return out
    for name in sorted(os.listdir(RUNS_DIR)):
        d = os.path.join(RUNS_DIR, name)
        if not os.path.isdir(d):
            continue
        m = _load_json(os.path.join(d, "manifest.json")) or {}
        if not is_lme_run(name, m):
            continue
        out.append({"name": name, "manifest": m, "mtime": os.path.getmtime(d)})
    out.sort(key=lambda r: r["mtime"], reverse=True)
    return out


def _predict_dir(run_dir):
    hits = sorted(glob.glob(os.path.join(run_dir, "predicted_*")))
    return hits[0] if hits else None


def _predict_files(run_dir):
    pd = _predict_dir(run_dir)
    if not pd:
        return {}
    out = {}
    for p in glob.glob(os.path.join(pd, "*.json")):
        qid = os.path.splitext(os.path.basename(p))[0]
        if not qid.startswith("_"):
            out[qid] = p
    return out


def _unified_metrics(run_dir):
    files = sorted(glob.glob(os.path.join(run_dir, "longmemeval_results_*.json")))
    if not files:
        return None
    return (_load_json(files[-1]) or {}).get("metrics_by_cutoff")


# --------------------------------------------------------------------------- trace aggregation (cached)
_TRACE_CACHE = {}


def _trace_sig(run_dir):
    sig = []
    for base in ("mem0_trace.jsonl", "eval_trace.jsonl"):
        p = _trace_path(run_dir, base)
        sig.append((p, os.path.getsize(p) if p else 0))
    return tuple(sig)


def _aggregate_traces(run_dir):
    """Per-qid live progress from the server + eval traces. Cached on file sizes."""
    sig = _trace_sig(run_dir)
    cached = _TRACE_CACHE.get(run_dir)
    if cached and cached["sig"] == sig:
        return cached["data"]

    adds_done, searched, answered, judged = {}, {}, {}, {}
    mp = _trace_path(run_dir, "mem0_trace.jsonl")
    for o in iter_events(mp):
        qid, _ = split_user_id(o.get("user_id") or "")
        if not qid:
            continue
        comp, op = o.get("component"), o.get("operation")
        if comp == "entry" and op == "add.response":
            adds_done[qid] = adds_done.get(qid, 0) + 1
        elif comp == "entry" and op == "search.request":
            searched[qid] = True

    ep = _trace_path(run_dir, "eval_trace.jsonl")
    for o in iter_events(ep):
        qid = (o.get("inputs") or {}).get("question_id") if isinstance(o.get("inputs"), dict) else None
        qid = qid or (split_user_id(o.get("user_id") or "")[0])
        if not qid:
            continue
        comp = o.get("component")
        if comp == "answerer":
            answered.setdefault(qid, 0)
            answered[qid] += 1
        elif comp == "judge":
            judged.setdefault(qid, 0)
            judged[qid] += 1
        elif comp == "mem0_client" and o.get("operation") == "search":
            searched[qid] = True

    data = {"adds_done": adds_done, "searched": searched, "answered": answered, "judged": judged}
    _TRACE_CACHE[run_dir] = {"sig": sig, "data": data}
    return data


# --------------------------------------------------------------------------- board
def board(name):
    run_dir = os.path.join(RUNS_DIR, name)
    manifest = _load_json(os.path.join(run_dir, "manifest.json")) or {}
    planned = reproduce_sample(manifest)
    predict = _predict_files(run_dir)
    agg = _aggregate_traces(run_dir)
    pub = published_map()

    # Include any qids seen in predictions/traces but not in the reproduced sample.
    planned_ids = [r["question_id"] for r in planned]
    extra = [q for q in predict if q not in set(planned_ids)]
    meta = _question_meta(set(planned_ids) | set(predict.keys()))
    order = planned_ids + sorted(extra)

    rows = []
    for qid in order:
        m = meta.get(qid, {})
        total = m.get("n_add_units", 0)
        done = agg["adds_done"].get(qid, 0)
        pj = _load_json(predict.get(qid)) if qid in predict else None

        verdicts = {}
        if pj and pj.get("cutoff_results"):
            for ck, cv in pj["cutoff_results"].items():
                verdicts[ck] = cv.get("judgment")

        # Stage.
        if verdicts:
            stage = "judged"
        elif agg["judged"].get(qid):
            stage = "judging"
        elif agg["answered"].get(qid):
            stage = "answering"
        elif agg["searched"].get(qid):
            stage = "searching"
        elif done and total and done < total:
            stage = f"adding {done}/{total}"
        elif done:
            stage = "searching"
        else:
            stage = "queued"

        p = pub.get(qid, {})
        rows.append({
            "question_id": qid,
            "question_type": m.get("question_type"),
            "is_abstention": bool(m.get("is_abstention")),
            "stage": stage,
            "adds_done": done,
            "adds_total": total,
            "verdicts": verdicts,
            "mem0_gpt5_verdict": p.get("judgment"),
            "mem0_gpt5_cutoff": p.get("cutoff"),
        })

    running = any(r["stage"] not in ("judged", "queued") for r in rows)
    done_n = sum(1 for r in rows if r["stage"] == "judged")
    return {
        "name": name, "manifest": manifest,
        "cutoffs": [f"top_{c}" for c in CUTOFFS],
        "counts": {"total": len(rows), "done": done_n},
        "running": running,
        "rows": rows,
    }


# --------------------------------------------------------------------------- question pipeline
def _server_ops_for(run_dir, qid):
    """Collect this question's add + search ops from the server trace, keyed by request_id."""
    adds = {}        # request_id -> {request, llm, response}
    add_order = []
    scoring = None
    search_req = None
    mp = _trace_path(run_dir, "mem0_trace.jsonl")
    for o in iter_events(mp):
        q, _ = split_user_id(o.get("user_id") or "")
        if q != qid:
            continue
        comp, op, rid = o.get("component"), o.get("operation"), o.get("request_id")
        if comp == "entry" and op == "add.request":
            adds.setdefault(rid, {})["request"] = o
            add_order.append(rid)
        elif comp == "llm" and op == "generate_response":
            adds.setdefault(rid, {})["llm"] = o
        elif comp == "entry" and op == "add.response":
            adds.setdefault(rid, {})["response"] = o
        elif comp == "entry" and op == "search.request":
            search_req = o
        elif comp == "scoring" and op == "score_and_rank":
            scoring = o
    return adds, add_order, search_req, scoring


def question_pipeline(name, qid):
    run_dir = os.path.join(RUNS_DIR, name)
    manifest = _load_json(os.path.join(run_dir, "manifest.json")) or {}
    meta = _question_meta([qid]).get(qid, {})
    ev_pairs = _evidence_pairs(qid)
    pub = published_map().get(qid, {})
    predict = _load_json(_predict_files(run_dir).get(qid)) if qid in _predict_files(run_dir) else None

    adds, add_order, search_req, scoring = _server_ops_for(run_dir, qid)

    def _match_session(messages):
        for msg in messages or []:
            if msg.get("role") == "user":
                key = (msg.get("content") or "").strip()[:200]
                hit = ev_pairs.get(key)
                if hit:
                    return hit
        return None

    # ADD panel + memory_id -> evidence/session map (for SEARCH tagging).
    add_panel = []
    mem_meta = {}
    for rid in add_order:
        a = adds.get(rid, {})
        req = (a.get("request") or {}).get("inputs") or {}
        llm = (a.get("llm") or {}).get("outputs") or {}
        llm_in = (a.get("llm") or {}).get("inputs") or {}
        resp = (a.get("response") or {}).get("outputs") or {}
        msgs = req.get("messages") or []
        sess = _match_session(msgs)
        stored = resp.get("results") or []
        for mem in stored:
            mem_meta[mem.get("id")] = {
                "memory": mem.get("memory"),
                "is_evidence": bool(sess and sess["is_evidence"]),
                "session_id": sess["session_id"] if sess else None,
            }
        add_panel.append({
            "request_id": rid,
            "session_id": sess["session_id"] if sess else None,
            "is_evidence": bool(sess and sess["is_evidence"]),
            "messages": msgs,
            "timestamp_sent": req.get("timestamp"),
            "extraction_prompt": llm_in.get("messages"),
            "extraction_response": llm.get("raw"),
            "facts": llm.get("parsed_facts"),
            "stored_memories": stored,
            "token_usage": llm.get("token_usage"),
            "add_latency_ms": (a.get("response") or {}).get("duration_ms")
            or (a.get("request") or {}).get("duration_ms"),
        })

    # SEARCH panel.
    search_panel = None
    if scoring or search_req:
        ranked = ((scoring or {}).get("outputs") or {}).get("ranked") or []
        cands = []
        for pos, c in enumerate(ranked):
            mm = mem_meta.get(c.get("id"), {})
            sd = c.get("score_details") or {}
            cands.append({
                "rank": pos + 1,
                "id": c.get("id"),
                "memory": mm.get("memory"),
                "is_evidence": mm.get("is_evidence", False),
                "session_id": mm.get("session_id"),
                "final_score": c.get("score", sd.get("final_score")),
                "semantic": sd.get("semantic_score"),
                "bm25": sd.get("bm25_score"),
                "entity_boost": sd.get("entity_boost"),
            })
        ev_ranks = [c["rank"] for c in cands if c["is_evidence"]]
        search_panel = {
            "query": ((search_req or {}).get("inputs") or {}).get("query")
            or (predict or {}).get("retrieval", {}).get("search_query"),
            "n_candidates": len(cands),
            "candidates": cands,
            "evidence_ranks": ev_ranks,
            "evidence_in": {f"top_{c}": sum(1 for r in ev_ranks if r <= c) for c in CUTOFFS},
        }

    # ANSWER + JUDGE panels from eval trace (exact prompts) + predict JSON (verdicts).
    answers, judges = {}, {}
    for o in iter_events(_trace_path(run_dir, "eval_trace.jsonl")):
        inp = o.get("inputs") or {}
        if inp.get("question_id") != qid:
            continue
        cut = inp.get("cutoff")
        cutk = f"top_{cut}" if isinstance(cut, int) else cut
        if o.get("component") == "answerer":
            answers[cutk] = {"prompt": inp.get("user"), "answer": (o.get("outputs") or {}).get("answer"),
                             "token_usage": (o.get("outputs") or {}).get("token_usage")}
        elif o.get("component") == "judge":
            judges[cutk] = {"prompt": inp.get("user"), "raw": (o.get("outputs") or {}).get("answer")}

    cutoff_results = (predict or {}).get("cutoff_results") or {}
    answer_panel, judge_panel = [], []
    for c in CUTOFFS:
        ck = f"top_{c}"
        cr = cutoff_results.get(ck) or {}
        answer_panel.append({
            "cutoff": ck,
            "prompt": (answers.get(ck) or {}).get("prompt"),
            "answer": (answers.get(ck) or {}).get("answer") or cr.get("generated_answer"),
            "token_usage": (answers.get(ck) or {}).get("token_usage"),
        })
        judge_panel.append({
            "cutoff": ck,
            "prompt": (judges.get(ck) or {}).get("prompt"),
            "verdict": cr.get("judgment"),
            "judge_raw": cr.get("judge_raw") or (judges.get(ck) or {}).get("raw"),
        })

    return {
        "name": name, "question_id": qid, "manifest": manifest,
        "question": meta.get("question"), "gold_answer": meta.get("answer"),
        "question_date": meta.get("question_date"), "question_type": meta.get("question_type"),
        "is_abstention": bool(meta.get("is_abstention")),
        "n_add_units": meta.get("n_add_units"), "n_evidence": meta.get("n_evidence"),
        "add": add_panel, "search": search_panel, "answer": answer_panel, "judge": judge_panel,
        "mem0_gpt5": {"answer": pub.get("answer"), "verdict": pub.get("judgment"),
                      "cutoff": pub.get("cutoff")},
        "gold": meta.get("answer"),
    }


# --------------------------------------------------------------------------- summary
def summary(name):
    run_dir = os.path.join(RUNS_DIR, name)
    manifest = _load_json(os.path.join(run_dir, "manifest.json")) or {}
    planned = reproduce_sample(manifest)
    qids = [r["question_id"] for r in planned]
    meta = _question_meta(set(qids))
    predict_files = _predict_files(run_dir)
    pub = published_map()

    # Ours: per-qid verdict per cutoff from predict JSONs.
    types = sorted({meta[q]["question_type"] for q in qids if q in meta})
    ours = {t: {f"top_{c}": [0, 0] for c in CUTOFFS} for t in types}   # [correct, total]
    ours_overall = {f"top_{c}": [0, 0] for c in CUTOFFS}
    mem0_row = {t: [0, 0] for t in types}
    mem0_overall = [0, 0]

    for qid in qids:
        t = meta.get(qid, {}).get("question_type")
        if not t:
            continue
        pj = _load_json(predict_files.get(qid)) if qid in predict_files else None
        cr = (pj or {}).get("cutoff_results") or {}
        for c in CUTOFFS:
            ck = f"top_{c}"
            if ck in cr and cr[ck].get("judgment"):
                ok = 1 if cr[ck]["judgment"] == "PASS" else 0
                ours[t][ck][0] += ok
                ours[t][ck][1] += 1
                ours_overall[ck][0] += ok
                ours_overall[ck][1] += 1
        # Mem0 published (top_200 only).
        p = pub.get(qid)
        if p and p.get("judgment"):
            ok = 1 if p["judgment"] == "PASS" else 0
            mem0_row[t][0] += ok
            mem0_row[t][1] += 1
            mem0_overall[0] += ok
            mem0_overall[1] += 1

    def pct(pair):
        return round(100 * pair[0] / pair[1], 1) if pair[1] else None

    by_type = []
    for t in types:
        row = {"type": t, "ours": {ck: {"pct": pct(ours[t][ck]), "n": ours[t][ck][1]} for ck in ours[t]},
               "mem0_gpt5_top200": {"pct": pct(mem0_row[t]), "n": mem0_row[t][1]}}
        by_type.append(row)
    overall = {"ours": {ck: {"pct": pct(ours_overall[ck]), "n": ours_overall[ck][1]} for ck in ours_overall},
               "mem0_gpt5_top200": {"pct": pct(mem0_overall), "n": mem0_overall[1]}}
    return {"name": name, "cutoffs": [f"top_{c}" for c in CUTOFFS],
            "by_type": by_type, "overall": overall,
            "note": "Mem0's published gpt-5 run reports top_200 only; compared on the same question_ids."}
