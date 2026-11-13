#!/usr/bin/env python3
"""
trace_metrics.py — system cost & latency from the traces (STEP 5).

Imported by trace_view.py --metrics. Writes per_question_metrics.csv and
per_session_metrics.csv into the run folder and prints a markdown summary.

Only the **system** is measured (Mem0 + the answerer). The judge's cost is NOT measured.
Numbers already produced by the benchmark are reused and labelled as such; anything not in the
logs is written ``n/a`` (never estimated).

Per-question metrics are reported at a single cutoff — the **largest** cutoff the answerer was
run at (e.g. top_200, the full retrieval that the headline J uses). The chosen cutoff is named
in the summary and in a `cutoff` column.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# tiktoken (optional)
# ---------------------------------------------------------------------------

def _encoder_for(model):
    """Return (encoder, encoding_name) or (None, reason)."""
    try:
        import tiktoken
    except Exception:
        return None, "tiktoken-not-installed"
    try:
        enc = tiktoken.encoding_for_model(model)
        return enc, enc.name
    except Exception:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("o200k_base")
            return enc, "o200k_base (fallback; model unknown to tiktoken)"
        except Exception:
            return None, "tiktoken-encoding-unavailable"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _manifest(run_dir):
    try:
        return json.load(open(os.path.join(run_dir, "manifest.json")))
    except Exception:
        return {}


def _sha1_messages(messages):
    try:
        return hashlib.sha1(json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    except Exception:
        return ""


def _pct(values, q):
    vals = sorted(v for v in values if isinstance(v, (int, float)))
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = q * (len(vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(vals) - 1)
    frac = pos - lo
    return vals[lo] * (1 - frac) + vals[hi] * frac


def _stats(values):
    vals = [v for v in values if isinstance(v, (int, float))]
    if not vals:
        return {"n": 0, "mean": None, "p50": None, "p95": None}
    return {"n": len(vals), "mean": round(sum(vals) / len(vals), 2),
            "p50": round(_pct(vals, 0.5), 2), "p95": round(_pct(vals, 0.95), 2)}


def _memory_block_tokens(prompt_text, enc):
    """Count tokens of the dated memory lines the answer prompt places before the question."""
    if enc is None or not prompt_text:
        return None
    lines = [ln for ln in prompt_text.splitlines()
             if re.match(r"^\((?:\w+, \w+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2})\)", ln.strip())]
    if not lines:
        return None
    return len(enc.encode("\n".join(lines)))


def cutoff_num(label):
    m = re.search(r"(\d+)", str(label))
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# main entry (called by trace_view.py)
# ---------------------------------------------------------------------------

def run_metrics(trace, dataset, run_dir, out):
    manifest = _manifest(run_dir)
    answer_model = manifest.get("answerer_model") or "gpt-5"
    enc, enc_name = _encoder_for(answer_model)

    results = _load_results(run_dir)

    # session epoch -> session number (for per-session join by timestamp)
    epoch_to_session = {}
    for conv_idx, entry in enumerate(dataset):
        conv = entry["conversation"]
        for key in conv:
            m = re.match(r"^session_(\d+)$", key)
            if m:
                ep = _session_epoch(conv.get(f"{key}_date_time", ""))
                if ep is not None:
                    epoch_to_session[ep] = (conv_idx, int(m.group(1)))

    # ---------- per question ----------
    q_rows = []
    qids = sorted({(e.get("inputs") or {}).get("question_id")
                   for e in trace.eval if e.get("component") == "answerer"} - {None},
                  key=_qid_key)
    if not qids:  # server-only / eval trace missing → fall back to result files
        qids = sorted(results.keys(), key=_qid_key)

    for qid in qids:
        answers = trace.eval_answers(qid)
        cutoffs = [(a.get("inputs") or {}).get("cutoff") for a in answers]
        cutoffs = [c for c in cutoffs if c is not None]
        chosen = max(cutoffs, key=lambda c: cutoff_num(c) or 0) if cutoffs else None

        a_ev = next((a for a in answers if (a.get("inputs") or {}).get("cutoff") == chosen), None)
        j_ev = next((j for j in trace.eval_judges(qid)
                     if (j.get("inputs") or {}).get("cutoff") == chosen), None)

        res = results.get(qid, {})
        category = res.get("category_name") or res.get("category")
        # verdict: prefer eval judge; else result file cutoff_results
        verdict = (j_ev.get("outputs") or {}).get("verdict") if j_ev else None
        if verdict is None and chosen is not None:
            verdict = ((res.get("cutoff_results") or {}).get(str(chosen)) or {}).get("judgment")

        # search latency: reuse the benchmark's number (results file); cross-check eval trace
        search_latency = (res.get("retrieval") or {}).get("search_latency_ms")
        search_src = "benchmark(results.json)"
        if search_latency is None:
            se = trace.eval_search(qid)
            search_latency = se.get("duration_ms") if se else None
            search_src = "eval_trace" if se else "n/a"

        # server search time: server trace entry search.response duration for the matching query
        server_search = _server_search_ms(trace, res.get("question"))

        answer_latency = a_ev.get("duration_ms") if a_ev else None
        total_latency = (search_latency + answer_latency) if (isinstance(search_latency, (int, float))
                                                              and isinstance(answer_latency, (int, float))) else None
        mem_tokens = _memory_block_tokens((a_ev.get("inputs") or {}).get("user") if a_ev else None, enc)

        q_rows.append({
            "question_id": qid,
            "category": category,
            "cutoff": chosen,
            "verdict": verdict,
            "search_latency_ms": _r(search_latency),
            "search_latency_src": search_src,
            "server_search_ms": _r(server_search),
            "answer_latency_ms": _r(answer_latency),
            "total_latency_ms": _r(total_latency),
            "memory_tokens": mem_tokens if mem_tokens is not None else "n/a",
        })

    # ---------- per session (per add request) ----------
    # join eval client-add (latency) to server add (extraction tokens, memories) by messages sha1
    eval_add_by_sha = {}
    for e in trace.eval_adds():
        sha = (e.get("inputs") or {}).get("messages_sha1")
        if sha:
            eval_add_by_sha[sha] = e

    s_rows = []
    for rid, evs in trace.add_reqs:
        req = trace.add_request_event(evs)
        messages = (req.get("inputs") or {}).get("messages") if req else None
        ts = (req.get("inputs") or {}).get("timestamp") if req else None
        conv_sess = epoch_to_session.get(ts)
        sha = _sha1_messages(messages) if messages else ""
        ev_add = eval_add_by_sha.get(sha)
        add_latency = ev_add.get("duration_ms") if ev_add else None
        ext = trace.extraction(evs) or {}
        usage = ext.get("token_usage") or {}
        s_rows.append({
            "request_id": rid,
            "conv": conv_sess[0] if conv_sess else "n/a",
            "session": conv_sess[1] if conv_sess else "n/a",
            "timestamp": ts,
            "add_latency_ms": _r(add_latency) if add_latency is not None else "n/a",
            "add_latency_src": "eval_trace" if ev_add else "n/a (no eval add match)",
            "extraction_prompt_tokens": usage.get("prompt_tokens", "n/a") if usage else "n/a",
            "extraction_completion_tokens": usage.get("completion_tokens", "n/a") if usage else "n/a",
            "memories_stored": len(trace.stored_memories(evs)),
        })

    # ---------- write CSVs ----------
    q_path = os.path.join(run_dir, "per_question_metrics.csv")
    s_path = os.path.join(run_dir, "per_session_metrics.csv")
    _write_csv(q_path, q_rows, ["question_id", "category", "cutoff", "verdict",
                                "search_latency_ms", "search_latency_src", "server_search_ms",
                                "answer_latency_ms", "total_latency_ms", "memory_tokens"])
    _write_csv(s_path, s_rows, ["request_id", "conv", "session", "timestamp", "add_latency_ms",
                                "add_latency_src", "extraction_prompt_tokens",
                                "extraction_completion_tokens", "memories_stored"])

    # ---------- summary ----------
    out("# Metrics")
    out()
    out(f"- answerer model: `{answer_model}`; memory-token encoding: `{enc_name}`")
    out(f"- per-question cutoff: **{_chosen_cutoff_note(q_rows)}** (largest cutoff the answerer ran at)")
    out(f"- wrote `{os.path.basename(q_path)}` ({len(q_rows)} rows), "
        f"`{os.path.basename(s_path)}` ({len(s_rows)} rows)")
    out("- judge cost is intentionally **not** measured.")
    out()

    def block(title, rows):
        out(f"### {title}")
        for field in ("search_latency_ms", "total_latency_ms", "memory_tokens"):
            st = _stats([_num(r.get(field)) for r in rows])
            out(f"- {field}: n={st['n']}, mean={st['mean']}, p50={st['p50']}, p95={st['p95']}")
        out()

    out("## Per-question latency & tokens (overall)")
    block("all questions", q_rows)

    cats = sorted({r.get("category") for r in q_rows if r.get("category") is not None}, key=str)
    if cats:
        out("## Per-question by category")
        for c in cats:
            block(str(c), [r for r in q_rows if r.get("category") == c])

    # memory building totals
    ext_prompt = sum(_num(r["extraction_prompt_tokens"]) or 0 for r in s_rows)
    ext_compl = sum(_num(r["extraction_completion_tokens"]) or 0 for r in s_rows)
    add_times = [_num(r["add_latency_ms"]) for r in s_rows]
    add_total = sum(v for v in add_times if v is not None)
    out("## Memory building (conversation totals)")
    out(f"- add requests: {len(s_rows)}; memories stored: {sum(r['memories_stored'] for r in s_rows)}")
    out(f"- total extraction tokens: prompt={ext_prompt}, completion={ext_compl}, "
        f"total={ext_prompt + ext_compl}")
    n_add_measured = sum(1 for v in add_times if v is not None)
    out(f"- total add time (client): {round(add_total, 1)} ms over {n_add_measured} measured add(s)"
        + ("" if n_add_measured == len(s_rows) else f" ({len(s_rows) - n_add_measured} n/a)"))


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _load_results(run_dir):
    import glob
    results = {}
    files = sorted(glob.glob(os.path.join(run_dir, "locomo_results_*.json")))
    if files:
        try:
            data = json.load(open(files[-1]))
            for ev in data.get("evaluations", data.get("results", [])):
                if ev.get("question_id"):
                    results[ev["question_id"]] = ev
        except Exception:
            pass
    if not results:
        for p in glob.glob(os.path.join(run_dir, "predicted_*", "*.json")):
            if os.path.basename(p).startswith("_"):
                continue
            try:
                ev = json.load(open(p))
                if ev.get("question_id"):
                    results[ev["question_id"]] = ev
            except Exception:
                pass
    return results


def _server_search_ms(trace, question):
    if not question:
        return None
    rid, evs = trace.search_for_query(question)
    if not evs:
        return None
    for e in evs:
        if e.get("component") == "entry" and e.get("operation") == "search.response":
            return e.get("duration_ms")
    return None


def _session_epoch(date_str):
    for fmt in ("%I:%M %p on %d %B, %Y", "%I:%M %p on %d %b, %Y"):
        try:
            d = datetime.strptime(date_str, fmt)
            return int(d.replace(tzinfo=timezone.utc).timestamp())
        except (ValueError, TypeError):
            continue
    return None


def _qid_key(qid):
    m = re.match(r"conv(\d+)_q(\d+)", str(qid))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def _r(x):
    return round(x, 2) if isinstance(x, (int, float)) else x


def _num(x):
    return x if isinstance(x, (int, float)) else None


def _write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def _chosen_cutoff_note(rows):
    cutoffs = {r.get("cutoff") for r in rows if r.get("cutoff") is not None}
    if len(cutoffs) == 1:
        return str(next(iter(cutoffs)))
    return "/".join(sorted(str(c) for c in cutoffs)) or "n/a"
