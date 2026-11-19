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

import datetime as dt
import glob
import gzip
import json
import os
import random
import sqlite3
import time

import trace_index

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXP = os.path.dirname(_HERE)
RUNS_DIR = os.path.join(_EXP, "runs")
DB_PATH = os.environ.get("LME_DB", os.path.join(_HERE, "longmemeval.sqlite"))
PUBLISHED_DIR = os.path.join(_EXP, "memory-benchmarks", "results", "oss")

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


# --------------------------------------------------------------------------- published (like-with-like)
def published_choice(manifest):
    """Pick the published OSS result file whose extraction model matches this run.

    Compare like with like: a GPT-OSS-120B run is judged against Mem0's "parasail
    gpt-120b" file, a gpt-5 run against their gpt5 file, anything else gets no row.
    Returns {"path", "file", "label", "model"}; path is None when nothing matches.
    """
    m = ((manifest or {}).get("extraction_llm") or "").lower()
    if "120b" in m or "gpt-oss" in m or "oss-120" in m:
        f, label = "longmemeval_parasail_120b.json", "Mem0 parasail gpt-120b"
    elif m in ("gpt-5", "gpt5") or m.startswith("gpt-5"):
        f, label = "longmemeval_gpt5.json", "Mem0 gpt-5"
    else:
        return {"path": None, "file": None, "label": "no published row", "model": m}
    path = os.path.join(PUBLISHED_DIR, f)
    return {"path": path if os.path.exists(path) else None, "file": f, "label": label, "model": m}


_PUB = {}  # path -> {"mtime", "map"}


def published_map(path):
    """question_id -> published top_200 verdict for the given file (cached on mtime)."""
    if not path:
        return {}
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return {}
    cached = _PUB.get(path)
    if cached and cached["mtime"] == mt:
        return cached["map"]
    data = _load_json(path) or {}
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
    _PUB[path] = {"mtime": mt, "map": m}
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


def runs_add_calls():
    """Measured add calls per run, grouped by question type + total — from traces only.

    The home page uses this instead of any dataset-derived add-unit estimate: it is the
    number of mem0.add() calls actually traced for each run. Runs with no trace are omitted.
    """
    out = []
    for run in list_runs():
        name, manifest = run["name"], run["manifest"]
        run_dir = os.path.join(RUNS_DIR, name)
        try:
            agg = trace_index.aggregate(run_dir) if trace_index.supported(run_dir) else _aggregate_traces(run_dir)
        except Exception:
            continue
        per_q = agg.get("per_q", {})
        meta = _question_meta(set(per_q))
        by_type, total, nq = {}, 0, 0
        for qid, mq in per_q.items():
            ac = mq.get("add_calls") or 0
            if ac <= 0:
                continue
            total += ac
            nq += 1
            t = meta.get(qid, {}).get("question_type") or "(other)"
            by_type[t] = by_type.get(t, 0) + ac
        if total:
            out.append({"name": name, "extraction_llm": manifest.get("extraction_llm"),
                        "by_type": by_type, "total": total, "n_questions": nq})
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


def _iso_s(a, b):
    """Seconds between two ISO-8601 time strings, or None if either is unparseable."""
    try:
        return (dt.datetime.fromisoformat(b) - dt.datetime.fromisoformat(a)).total_seconds()
    except (ValueError, TypeError):
        return None


def _blank_q():
    return {"add_calls": 0, "add_resp": 0, "add_zero": 0, "mem_stored": 0, "tok_in": 0,
            "tok_out": 0, "tok_total": 0, "cutoffs": 0, "parse_fail": 0, "errors": 0,
            "search_ms": 0.0, "first": None, "last": None}


def _finalize_per_q(per):
    """Turn raw per-qid accumulators into the measured shape the UI renders."""
    out = {}
    for qid, d in per.items():
        wall = _iso_s(d["first"], d["last"])
        out[qid] = {
            "add_calls": d["add_calls"], "add_resp": d["add_resp"],
            "add_failed": max(0, d["add_calls"] - d["add_resp"]),
            "add_zero": d["add_zero"],   # adds that stored 0 memories (silent empty extraction)
            "mem_stored": d["mem_stored"],
            "mem_per_add": round(d["mem_stored"] / d["add_resp"], 2) if d["add_resp"] else None,
            "tok_in": d["tok_in"], "tok_out": d["tok_out"], "tok_total": d["tok_total"],
            "cutoffs": d["cutoffs"], "parse_fail": d["parse_fail"], "errors": d["errors"],
            "search_ms": round(d["search_ms"], 1) if d["search_ms"] else None,
            "wall_ms": round(wall * 1000, 1) if wall is not None else None,
        }
    return out


def _aggregate_traces(run_dir):
    """Per-qid measured metrics from the server + eval traces. Cached on file sizes.

    Everything here is counted from the trace, never projected: add calls / failures,
    memories stored, extraction tokens (input/output/total), cut-offs, parse failures,
    per-question search latency and wall time. GPT-OSS reasoning tokens are not broken
    out by the API, so only input/output/total are reported.
    """
    sig = _trace_sig(run_dir)
    cached = _TRACE_CACHE.get(run_dir)
    if cached and cached["sig"] == sig:
        return cached["data"]

    adds_done, searched, answered, judged = {}, {}, {}, {}
    # Global extraction health + token totals. 0 cut-offs / 0 parse-fail is healthy.
    extraction = {"calls": 0, "cutoffs": 0, "parse_fail": 0, "errors": 0,
                  "tok_in": 0, "tok_out": 0, "tok_total": 0,
                  "add_calls": 0, "add_resp": 0, "add_zero": 0, "mem_stored": 0,
                  "reasoning_recorded": False}
    span = {"first": None, "last": None}
    ex_models, ans_models = set(), set()   # model names the API/gateway actually reports
    per = {}

    def pq(qid):
        d = per.get(qid)
        if d is None:
            d = _blank_q()
            per[qid] = d
        return d

    mp = _trace_path(run_dir, "mem0_trace.jsonl")
    for o in iter_events(mp):
        comp, op = o.get("component"), o.get("operation")
        qid, _ = split_user_id(o.get("user_id") or "")
        gt = o.get("time")
        if gt:
            if span["first"] is None:
                span["first"] = gt
            span["last"] = gt
        if comp == "llm" and op == "generate_response":
            out = o.get("outputs") or {}
            tu = out.get("token_usage") or {}
            pi, co, to = tu.get("prompt_tokens") or 0, tu.get("completion_tokens") or 0, tu.get("total_tokens") or 0
            extraction["calls"] += 1
            extraction["tok_in"] += pi
            extraction["tok_out"] += co
            extraction["tok_total"] += to
            if any("reason" in k.lower() for k in tu):
                extraction["reasoning_recorded"] = True
            cut = out.get("finish_reason") == "length"
            pf = out.get("parse_ok") is False
            er = bool(out.get("error"))
            if cut:
                extraction["cutoffs"] += 1
            if pf:
                extraction["parse_fail"] += 1
            if er:
                extraction["errors"] += 1
            mr = out.get("model_reported")
            if mr:
                ex_models.add(mr)
            if qid:
                d = pq(qid)
                d["tok_in"] += pi
                d["tok_out"] += co
                d["tok_total"] += to
                d["cutoffs"] += 1 if cut else 0
                d["parse_fail"] += 1 if pf else 0
                d["errors"] += 1 if er else 0
        if not qid:
            continue
        d = pq(qid)
        t = o.get("time")
        if d["first"] is None:
            d["first"] = t
        d["last"] = t
        if comp == "entry" and op == "add.request":
            extraction["add_calls"] += 1
            d["add_calls"] += 1
        elif comp == "entry" and op == "add.response":
            adds_done[qid] = adds_done.get(qid, 0) + 1
            res = (o.get("outputs") or {}).get("results") or []
            extraction["add_resp"] += 1
            extraction["mem_stored"] += len(res)
            d["add_resp"] += 1
            d["mem_stored"] += len(res)
            if not res:                        # add stored 0 memories
                extraction["add_zero"] += 1
                d["add_zero"] += 1
        elif comp == "entry" and op == "search.request":
            searched[qid] = True
        elif comp == "entry" and op == "search.response":
            d["search_ms"] += o.get("duration_ms") or 0.0

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
            mr = (o.get("outputs") or {}).get("model_reported")
            if mr:
                ans_models.add(mr)
        elif comp == "judge":
            judged.setdefault(qid, 0)
            judged[qid] += 1
        elif comp == "mem0_client" and o.get("operation") == "search":
            searched[qid] = True

    extraction["add_failed"] = max(0, extraction["add_calls"] - extraction["add_resp"])
    extraction["mem_per_add"] = (round(extraction["mem_stored"] / extraction["add_resp"], 2)
                                 if extraction["add_resp"] else None)
    run_wall = _iso_s(span["first"], span["last"])
    extraction["wall_ms"] = round(run_wall * 1000, 1) if run_wall is not None else None
    data = {"adds_done": adds_done, "searched": searched, "answered": answered,
            "judged": judged, "extraction": extraction, "per_q": _finalize_per_q(per),
            "models_reported": {"extraction": sorted(ex_models), "answerer": sorted(ans_models)}}
    _TRACE_CACHE[run_dir] = {"sig": sig, "data": data}
    return data


# --------------------------------------------------------------------------- board
def board(name):
    run_dir = os.path.join(RUNS_DIR, name)
    manifest = _load_json(os.path.join(run_dir, "manifest.json")) or {}
    planned = reproduce_sample(manifest)
    predict = _predict_files(run_dir)
    # Live runs: answer from the incremental index (reads only newly-appended bytes).
    # Finished runs (trace gzipped) fall back to the legacy full scan.
    agg = trace_index.aggregate(run_dir) if trace_index.supported(run_dir) else _aggregate_traces(run_dir)
    choice = published_choice(manifest)
    pub = published_map(choice["path"])
    per_q = agg.get("per_q", {})

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
            "adds_total": total,          # dataset target (planned add-units)
            "verdicts": verdicts,
            "measured": per_q.get(qid, {}),   # add calls/fail, mem stored, tokens, search, wall
            "published_verdict": p.get("judgment"),
            "published_cutoff": p.get("cutoff"),
        })

    running = any(r["stage"] not in ("judged", "queued") for r in rows)
    done_n = sum(1 for r in rows if r["stage"] == "judged")
    return {
        "name": name, "manifest": manifest,
        "cutoffs": [f"top_{c}" for c in CUTOFFS],
        "counts": {"total": len(rows), "done": done_n},
        "extraction": agg.get("extraction", {}),
        "models_reported": agg.get("models_reported", {"extraction": [], "answerer": []}),
        "published": choice,
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


def _collect_ops(run_dir, qid, page, page_size):
    """Normalize one question's server + eval events across the fast and legacy paths.

    Fast path (live run, plain trace): the index gives us byte offsets, so we read only
    this question's events — all (small) requests/responses for correct SEARCH tagging,
    but only the current page's (large) extraction llm lines. Legacy path (gzipped,
    finished run): one full scan, all add-units on a single page.
    """
    if trace_index.supported(run_dir):
        io = trace_index.question_ops(run_dir, qid, page, page_size)
        if io is None:
            return {}, [], [], None, None, [], 0, 0, page_size
        adds = {rid: {"request": io["requests"].get(rid), "llm": io["llm"].get(rid),
                      "response": io["responses"].get(rid)} for rid in io["order_all"]}
        return (adds, io["order_all"], io["page_order"], io["search_req"], io["scoring"],
                io["eval"], io["total_units"], io["page"], io["page_size"])

    adds, add_order, search_req, scoring = _server_ops_for(run_dir, qid)
    eval_objs = list(iter_events(_trace_path(run_dir, "eval_trace.jsonl")))
    return (adds, add_order, add_order, search_req, scoring,
            eval_objs, len(add_order), 0, max(len(add_order), 1))


def question_pipeline(name, qid, page=0, page_size=25):
    run_dir = os.path.join(RUNS_DIR, name)
    manifest = _load_json(os.path.join(run_dir, "manifest.json")) or {}
    meta = _question_meta([qid]).get(qid, {})
    ev_pairs = _evidence_pairs(qid)
    choice = published_choice(manifest)
    pub = published_map(choice["path"]).get(qid, {})
    predict = _load_json(_predict_files(run_dir).get(qid)) if qid in _predict_files(run_dir) else None

    (adds, add_order, page_order, search_req, scoring,
     eval_objs, add_total, add_page, add_page_size) = _collect_ops(run_dir, qid, page, page_size)

    def _match_session(messages):
        for msg in messages or []:
            if msg.get("role") == "user":
                key = (msg.get("content") or "").strip()[:200]
                hit = ev_pairs.get(key)
                if hit:
                    return hit
        return None

    # memory_id -> evidence/session map, built from ALL add-units so SEARCH can tag every
    # candidate regardless of which page its creating add-unit falls on.
    mem_meta = {}
    for rid in add_order:
        a = adds.get(rid, {})
        req = (a.get("request") or {}).get("inputs") or {}
        resp = (a.get("response") or {}).get("outputs") or {}
        sess = _match_session(req.get("messages") or [])
        for mem in (resp.get("results") or []):
            mem_meta[mem.get("id")] = {
                "memory": mem.get("memory"),
                "is_evidence": bool(sess and sess["is_evidence"]),
                "session_id": sess["session_id"] if sess else None,
            }

    # ADD panel — only the current page of add-units (the heavy extraction llm lines are
    # read for this page alone).
    add_panel = []
    for j, rid in enumerate(page_order):
        a = adds.get(rid, {})
        req = (a.get("request") or {}).get("inputs") or {}
        llm = (a.get("llm") or {}).get("outputs") or {}
        llm_in = (a.get("llm") or {}).get("inputs") or {}
        resp = (a.get("response") or {}).get("outputs") or {}
        msgs = req.get("messages") or []
        sess = _match_session(msgs)
        stored = resp.get("results") or []
        add_panel.append({
            "n": add_page * add_page_size + j + 1,
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
    for o in eval_objs:
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
        "add_total": add_total, "add_page": add_page, "add_page_size": add_page_size,
        "published": choice,
        "published_result": {"answer": pub.get("answer"), "verdict": pub.get("judgment"),
                             "cutoff": pub.get("cutoff")},
        "gold": meta.get("answer"),
    }


# --------------------------------------------------------------------------- summary
_MEASURED_KEYS = ("add_calls", "add_failed", "add_resp", "add_zero", "mem_stored",
                  "tok_in", "tok_out", "tok_total", "cutoffs", "parse_fail", "errors")


def _measured_bucket():
    b = {k: 0 for k in _MEASURED_KEYS}
    b["search_ms_sum"], b["search_n"] = 0.0, 0
    return b


def _measured_add(b, mq):
    for k in _MEASURED_KEYS:
        b[k] += mq.get(k) or 0
    if mq.get("search_ms") is not None:
        b["search_ms_sum"] += mq["search_ms"]
        b["search_n"] += 1


def _measured_out(b):
    # No wall-time sum: questions run in parallel, so summing per-question spans overcounts.
    # Wall time is reported per question (board) and as the whole-run span (totals).
    out = {k: b[k] for k in _MEASURED_KEYS}
    out["search_ms_avg"] = round(b["search_ms_sum"] / b["search_n"], 1) if b["search_n"] else None
    out["mem_per_add"] = round(b["mem_stored"] / b["add_resp"], 2) if b["add_resp"] else None
    return out


def summary(name):
    run_dir = os.path.join(RUNS_DIR, name)
    manifest = _load_json(os.path.join(run_dir, "manifest.json")) or {}
    planned = reproduce_sample(manifest)
    qids = [r["question_id"] for r in planned]
    meta = _question_meta(set(qids))
    predict_files = _predict_files(run_dir)
    choice = published_choice(manifest)
    pub = published_map(choice["path"])
    agg = trace_index.aggregate(run_dir) if trace_index.supported(run_dir) else _aggregate_traces(run_dir)
    per_q = agg.get("per_q", {})

    # Ours: per-qid verdict per cutoff from predict JSONs.
    types = sorted({meta[q]["question_type"] for q in qids if q in meta})
    ours = {t: {f"top_{c}": [0, 0] for c in CUTOFFS} for t in types}   # [correct, total]
    ours_overall = {f"top_{c}": [0, 0] for c in CUTOFFS}
    pub_row = {t: [0, 0] for t in types}
    pub_overall = [0, 0]
    meas = {t: _measured_bucket() for t in types}
    meas_overall = _measured_bucket()

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
        # Measured metrics per type + overall (from the trace).
        mq = per_q.get(qid)
        if mq:
            _measured_add(meas[t], mq)
            _measured_add(meas_overall, mq)
        # Published (top_200 only), same question_ids.
        p = pub.get(qid)
        if p and p.get("judgment"):
            ok = 1 if p["judgment"] == "PASS" else 0
            pub_row[t][0] += ok
            pub_row[t][1] += 1
            pub_overall[0] += ok
            pub_overall[1] += 1

    def pct(pair):
        return round(100 * pair[0] / pair[1], 1) if pair[1] else None

    by_type = []
    for t in types:
        by_type.append({
            "type": t,
            "ours": {ck: {"pct": pct(ours[t][ck]), "n": ours[t][ck][1]} for ck in ours[t]},
            "published_top200": {"pct": pct(pub_row[t]), "n": pub_row[t][1]},
            "measured": _measured_out(meas[t]),
        })
    overall_measured = _measured_out(meas_overall)
    overall_measured["wall_ms"] = agg.get("extraction", {}).get("wall_ms")   # whole-run span
    overall = {
        "ours": {ck: {"pct": pct(ours_overall[ck]), "n": ours_overall[ck][1]} for ck in ours_overall},
        "published_top200": {"pct": pct(pub_overall), "n": pub_overall[1]},
        "measured": overall_measured,
    }
    note = (f"Compared on the same question_ids against {choice['label']} "
            f"({choice['file']}), which reports top_200 only."
            if choice["path"] else
            f"No published row for extraction model {choice['model']!r}; accuracy shown for ours only.")
    return {"name": name, "cutoffs": [f"top_{c}" for c in CUTOFFS],
            "published": choice,
            "by_type": by_type, "overall": overall, "note": note}


# --------------------------------------------------------------------------- compare two+ runs
def _run_verdicts(name):
    """One run's per-qid verdicts per cutoff + question types, from its unified results
    (or predict files while still running)."""
    run_dir = os.path.join(RUNS_DIR, name)
    manifest = _load_json(os.path.join(run_dir, "manifest.json")) or {}
    cuts = [f"top_{c}" for c in CUTOFFS]
    verd, qtype = {}, {}
    files = sorted(glob.glob(os.path.join(run_dir, "longmemeval_results_*.json")))
    if files:
        for e in (_load_json(files[-1]) or {}).get("evaluations", []):
            qid = e["question_id"]
            qtype[qid] = e.get("question_type")
            cr = e.get("cutoff_results") or {}
            verd[qid] = {c: (cr.get(c) or {}).get("judgment") for c in cuts}
    else:
        for qid, p in _predict_files(run_dir).items():
            pj = _load_json(p) or {}
            cr = pj.get("cutoff_results") or {}
            verd[qid] = {c: (cr.get(c) or {}).get("judgment") for c in cuts}
            qtype[qid] = pj.get("question_type")
    return manifest, verd, qtype


def compare(names):
    """Compare two or more of our runs on their shared question_ids: accuracy per type per
    cutoff, a per-question top_200 verdict grid with flips, and each run's published row."""
    cuts = [f"top_{c}" for c in CUTOFFS]
    runs = []
    for n in names:
        manifest, verd, qtype = _run_verdicts(n)
        runs.append({"name": n, "manifest": manifest, "verd": verd, "qtype": qtype,
                     "extraction_llm": manifest.get("extraction_llm"),
                     "extraction_endpoint": manifest.get("extraction_endpoint"),
                     "published": published_choice(manifest)})

    shared = None
    for r in runs:
        s = set(r["verd"])
        shared = s if shared is None else (shared & s)
    shared = sorted(shared or [])

    qtype = {}
    for q in shared:
        for r in runs:
            if r["qtype"].get(q):
                qtype[q] = r["qtype"][q]
                break
    types = sorted({t for t in qtype.values() if t})

    def pct(pair):
        return round(100 * pair[0] / pair[1], 1) if pair[1] else None

    accuracy = []
    for r in runs:
        by = {t: {ck: [0, 0] for ck in cuts} for t in types}
        ov = {ck: [0, 0] for ck in cuts}
        for q in shared:
            t = qtype.get(q)
            for ck in cuts:
                j = r["verd"].get(q, {}).get(ck)
                if j:
                    ok = 1 if j == "PASS" else 0
                    if t:
                        by[t][ck][0] += ok
                        by[t][ck][1] += 1
                    ov[ck][0] += ok
                    ov[ck][1] += 1
        accuracy.append({
            "name": r["name"], "extraction_llm": r["extraction_llm"],
            "by_type": {t: {ck: {"pct": pct(by[t][ck]), "n": by[t][ck][1]} for ck in cuts} for t in types},
            "overall": {ck: {"pct": pct(ov[ck]), "n": ov[ck][1]} for ck in cuts},
        })

    # Per-question top_200 verdict grid, flips = runs disagree.
    grid, flips = [], 0
    for q in shared:
        verds = [r["verd"].get(q, {}).get("top_200") for r in runs]
        flip = len({v for v in verds if v}) > 1
        flips += 1 if flip else 0
        grid.append({"question_id": q, "question_type": qtype.get(q), "verdicts": verds, "flip": flip})

    # Each run's published row on the shared qids (top_200), where a published match exists.
    published = []
    for r in runs:
        ch = r["published"]
        pm = published_map(ch["path"])
        c = n = 0
        for q in shared:
            p = pm.get(q)
            if p and p.get("judgment"):
                n += 1
                c += 1 if p["judgment"] == "PASS" else 0
        published.append({"name": r["name"], "label": ch["label"],
                          "has": bool(ch["path"]) and n > 0, "pct": pct([c, n]), "n": n})

    return {
        "runs": [{"name": r["name"], "extraction_llm": r["extraction_llm"],
                  "extraction_endpoint": r["extraction_endpoint"]} for r in runs],
        "cutoffs": cuts, "types": types, "shared_count": len(shared),
        "accuracy": accuracy, "grid": grid, "flips": flips, "published": published,
    }
