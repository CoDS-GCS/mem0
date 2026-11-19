#!/usr/bin/env python3
"""
compare_lme_to_published.py — build a run's README from measured numbers only.

Given one finished LongMemEval run folder, this compares OUR run against Mem0's
published OSS result whose *extraction model matches ours* (like with like), and writes
<run>/README.md with:

  1. setup table      — ours vs the matched published run (field by field)
  2. accuracy (same 60 qids) — ours vs theirs at top_200, plus ours at 50/20/10
  3. published on all 500    — theirs, for reference
  4. per-question agreement  — both right / both wrong / only ours / only theirs (+ qids)
  5. run facts               — wall time, tokens, cut-offs / parse failures (measured)
  6. Observations            — left empty for a human to fill in

Everything printed is read from the run's own files (manifest.json, the unified
longmemeval_results_*.json, and the mem0 trace). The run folder is only READ.

Publication match (by manifest "extraction_llm"):
  gpt-oss-120b / *120b*  -> results/oss/longmemeval_parasail_120b.json  ("parasail gpt-120b")
  gpt-5 / gpt5           -> results/oss/longmemeval_gpt5.json           ("gpt-5")
  anything else          -> no published row

Usage:
  python3 experiments/scripts/compare_lme_to_published.py \
      --run experiments/runs/lme_A_default_oss120b_60q
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import gzip
import hashlib
import json
import os
import sys

# GitHub rejects any file over 100 MB; such artifacts are left out of git and only
# recorded here by path / size / sha256.
GH_LIMIT = 100 * 1024 * 1024

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXP = os.path.dirname(_HERE)
PUBLISHED_DIR = os.path.join(_EXP, "memory-benchmarks", "results", "oss")
# Mem0's GPT-5 run is always shown as a reference column, regardless of the matched file.
GPT5_FILE = os.path.join(PUBLISHED_DIR, "longmemeval_gpt5.json")

# Measured OpenRouter/OpenAI cost for this run, entered by Loubna from the billing pages.
COST = {
    "extraction": ("GPT-OSS-120B via OpenRouter", 24.97),
    "answer_judge": ("GPT-5 via OpenAI", 9.95),
    "total": 34.92,
}

# Fixed question-type order so every table lines up.
TYPES = [
    "knowledge-update",
    "multi-session",
    "single-session-assistant",
    "single-session-preference",
    "single-session-user",
    "temporal-reasoning",
]
CUTOFFS = ["top_200", "top_50", "top_20", "top_10"]


# --------------------------------------------------------------------------- io
def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def unified_results(run_dir):
    files = sorted(glob.glob(os.path.join(run_dir, "longmemeval_results_*.json")))
    if not files:
        sys.exit(f"No longmemeval_results_*.json in {run_dir}")
    return files[-1], load_json(files[-1])


# --------------------------------------------------------------------------- published pick
def published_choice(manifest):
    """Pick the published OSS file whose extraction model matches this run."""
    m = (manifest.get("extraction_llm") or "").lower()
    if "120b" in m or "gpt-oss" in m or "oss-120" in m:
        f, label = "longmemeval_parasail_120b.json", "Mem0 published — parasail gpt-120b"
    elif m in ("gpt-5", "gpt5") or m.startswith("gpt-5"):
        f, label = "longmemeval_gpt5.json", "Mem0 published — gpt-5"
    else:
        return {"path": None, "file": None, "label": "no published row", "model": m}
    path = os.path.join(PUBLISHED_DIR, f)
    return {
        "path": path if os.path.exists(path) else None,
        "file": f,
        "label": label,
        "model": m,
    }


def published_verdicts(pub_data):
    """question_id -> PASS/FAIL at top_200 (None if the file has no per-q cutoff_results)."""
    out = {}
    for e in pub_data.get("evaluations", []):
        cr = e.get("cutoff_results") or {}
        top = cr.get("top_200") or (next(iter(cr.values()), None) if cr else None)
        if top and top.get("judgment"):
            out[e["question_id"]] = top["judgment"]
    return out


# --------------------------------------------------------------------------- accuracy
def ours_verdicts(run_data):
    """question_id -> {cutoff: PASS/FAIL}, plus question_type map."""
    verd, qtype = {}, {}
    for e in run_data.get("evaluations", []):
        qid = e["question_id"]
        qtype[qid] = e.get("question_type")
        cr = e.get("cutoff_results") or {}
        verd[qid] = {c: (cr.get(c) or {}).get("judgment") for c in CUTOFFS}
    return verd, qtype


def pct(correct, total):
    return round(100 * correct / total, 1) if total else None


def accuracy_table(qids, qtype, our_verd, their_maps):
    """Overall + per-type accuracy on the SAME qids.

    ours @ each cutoff, plus each published map in ``their_maps`` (name -> {qid: PASS/FAIL})
    at its top_200. rows[bucket][cutoff] and rows[bucket]["their"][name] = [correct, total].
    """
    rows = {}
    for b in TYPES + ["overall"]:
        rows[b] = {c: [0, 0] for c in CUTOFFS}
        rows[b]["their"] = {k: [0, 0] for k in their_maps}
    for qid in qids:
        t = qtype.get(qid)
        targets = [t, "overall"] if t else ["overall"]
        for c in CUTOFFS:
            j = our_verd.get(qid, {}).get(c)
            if j:
                for b in targets:
                    rows[b][c][0] += 1 if j == "PASS" else 0
                    rows[b][c][1] += 1
        for name, tv in their_maps.items():
            tj = tv.get(qid)
            if tj:
                for b in targets:
                    rows[b]["their"][name][0] += 1 if tj == "PASS" else 0
                    rows[b]["their"][name][1] += 1
    return rows


def pub_setup_col(data, extraction_label, extraction_provider):
    """Setup-table column for a published run.

    Cells come from the run's result file; where that is silent, from Mem0's benchmarks
    README L242 ("All runs use the same embedder (Qwen 600M via SageMaker), the same
    Qdrant vector store, and GPT-5 as the answerer and judge"), cited in brackets.
    "not recorded" is kept only where neither the result file nor the README says anything.
    """
    meta = (data or {}).get("metadata", {})
    n_scored = len(published_verdicts(data)) if data else 0
    return {
        "extraction model": extraction_label,
        "extraction provider": extraction_provider,
        "reasoning": "not recorded",
        "extraction max_tokens": "not recorded",
        "embedder": "Qwen 600M via SageMaker [README L242]",
        "embedding dims": "not stated; their sagemaker_embedder.py defaults to 768",
        "vector store": "Qdrant [README L242]",
        "answerer": meta.get("answerer_model") or "GPT-5 [README L242]",
        "judge": meta.get("judge_model") or "GPT-5 [README L242]",
        "answerer/judge provider": meta.get("provider") or "not recorded",
        "top_k": meta.get("top_k") or "not recorded",
        "cutoffs": ", ".join(meta.get("top_k_cutoffs", [])) or "not recorded",
        "Mem0 version": "not recorded",
        "dataset": f"{n_scored} questions (all)" if n_scored else "not recorded",
    }


def agreement(qids, our_verd, their_verd):
    both_r = both_w = []
    buckets = {"both_right": [], "both_wrong": [], "only_ours": [], "only_theirs": []}
    for qid in qids:
        ours = our_verd.get(qid, {}).get("top_200") == "PASS"
        if qid not in their_verd:
            continue
        theirs = their_verd[qid] == "PASS"
        if ours and theirs:
            buckets["both_right"].append(qid)
        elif not ours and not theirs:
            buckets["both_wrong"].append(qid)
        elif ours and not theirs:
            buckets["only_ours"].append(qid)
        else:
            buckets["only_theirs"].append(qid)
    return buckets


# --------------------------------------------------------------------------- run facts (trace)
def _qid_of(uid):
    if not uid or not uid.startswith("longmemeval_"):
        return None
    q, _, _run = uid[len("longmemeval_"):].rpartition("_")
    return q or None


def run_facts(run_dir):
    """Measured facts from the mem0 trace. Returns None if no trace is present."""
    path = None
    for cand in ("mem0_trace.jsonl", "mem0_trace.jsonl.gz"):
        p = os.path.join(run_dir, cand)
        if os.path.exists(p):
            path = p
            break
    if not path:
        return None

    f = {
        "add_calls": 0, "add_resp": 0, "add_zero": 0, "mem_stored": 0,
        "llm_calls": 0, "cutoffs": 0, "parse_fail": 0, "llm_err": 0,
        "tok_in": 0, "tok_out": 0, "tok_total": 0,
        "reasoning_recorded": False,
        "first": None, "last": None, "search_ms": [],
    }
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            t = o.get("time")
            if t:
                if f["first"] is None:
                    f["first"] = t
                f["last"] = t
            comp, op = o.get("component"), o.get("operation")
            if comp == "entry" and op == "add.request":
                f["add_calls"] += 1
            elif comp == "entry" and op == "add.response":
                f["add_resp"] += 1
                res = (o.get("outputs") or {}).get("results") or []
                f["mem_stored"] += len(res)
                if not res:
                    f["add_zero"] += 1
            elif comp == "entry" and op == "search.response":
                d = o.get("duration_ms")
                if d is not None:
                    f["search_ms"].append(d)
            elif comp == "llm" and op == "generate_response":
                f["llm_calls"] += 1
                outs = o.get("outputs") or {}
                tu = outs.get("token_usage") or {}
                f["tok_in"] += tu.get("prompt_tokens") or 0
                f["tok_out"] += tu.get("completion_tokens") or 0
                f["tok_total"] += tu.get("total_tokens") or 0
                if any("reason" in k.lower() for k in tu):
                    f["reasoning_recorded"] = True
                if outs.get("finish_reason") == "length":
                    f["cutoffs"] += 1
                if outs.get("parse_ok") is False:
                    f["parse_fail"] += 1
                if outs.get("error"):
                    f["llm_err"] += 1

    wall_s = None
    if f["first"] and f["last"]:
        try:
            wall_s = (dt.datetime.fromisoformat(f["last"]) - dt.datetime.fromisoformat(f["first"])).total_seconds()
        except ValueError:
            wall_s = None
    f["wall_s"] = wall_s
    f["add_failed"] = max(0, f["add_calls"] - f["add_resp"])
    f["mem_per_add"] = round(f["mem_stored"] / f["add_resp"], 2) if f["add_resp"] else None
    f["add_zero_pct"] = round(100 * f["add_zero"] / f["add_resp"], 1) if f["add_resp"] else None
    f["search_ms_avg"] = round(sum(f["search_ms"]) / len(f["search_ms"]), 1) if f["search_ms"] else None
    return f


# --------------------------------------------------------------------------- formatting
def large_artifacts(run_dir):
    """Files in the run dir over GitHub's 100 MB limit: (relpath, bytes, sha256)."""
    out = []
    for root, _dirs, files in os.walk(run_dir):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            if sz > GH_LIMIT:
                h = hashlib.sha256()
                with open(p, "rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        h.update(chunk)
                out.append((os.path.relpath(p, run_dir), sz, h.hexdigest()))
    return sorted(out)


def memory_store_section(run_dir):
    """Render a '## Memory store' section from <run>/store_facts.json, if present.

    store_facts.json is written by run_longmemeval.sh at the end of a run (and can be
    refreshed by re-querying Qdrant + the mem0_history volume). Returns [] if absent so
    the READMEs degrade gracefully.
    """
    path = os.path.join(run_dir, "store_facts.json")
    if not os.path.exists(path):
        return []
    try:
        sf = load_json(path)
    except Exception:
        return []
    q = sf.get("qdrant", {})
    h = sf.get("history_db", {})
    a = sf.get("adds", {})
    tr = sf.get("trace", {})
    L = ["## Memory store", "",
         f"Measured {sf.get('measured_utc', '')}. " + (sf.get("note") or ""), ""]
    if q:
        L.append("**Qdrant** (collection dedicated to this run):")
        L.append("")
        L.append(f"- memories: **{_n(q.get('memories'))}** in `{q.get('memories_collection')}`"
                 + (f" (the trace's add-responses summed to {_n(tr.get('memories_from_add_responses'))}; "
                    f"+{_n(tr.get('qdrant_surplus_over_trace'))} surplus, see adds below)" if tr else ""))
        et = q.get("entity_types") or {}
        et_str = " · ".join(f"{k} {v:,}" for k, v in et.items())
        uniq = (f", **{q['entities_unique_text']:,}** unique by text"
                if q.get("entities_unique_text") is not None else "")
        L.append(f"- entities: **{_n(q.get('entities'))}** points in `{q.get('entities_collection')}`"
                 + uniq + (f" ({et_str})" if et_str else "")
                 + ". Mem0 stores entities in a parallel `<collection>_entities` collection, each "
                 "linking back to memory ids.")
        L.append("")
    if h:
        L.append(f"**History DB** ({h.get('location', 'mem0_history volume')}):")
        L.append("")
        L.append(f"- `history` table: **{_n(h.get('history_table_rows_this_run'))}** rows for this run — "
                 + (h.get("history_row_meaning") or ""))
        L.append(f"- `messages` table: **{_n(h.get('messages_table_rows_this_run'))}** rows for this run — "
                 + (h.get("stores_raw_messages") or ""))
        L.append("")
    if a:
        L.append("**Add reconciliation** (calls vs stored):")
        L.append("")
        L.append(f"- {_n(a.get('add_calls'))} add calls, {_n(a.get('add_responses'))} with a traced "
                 f"response, {_n(a.get('missing_responses'))} without: "
                 f"**{_n(a.get('failed_llm_error'))} failed on an LLM error**, "
                 f"{_n(a.get('no_llm_call'))} had no LLM call (failed early), and "
                 f"{_n(a.get('successful_llm_untraced_response'))} had a successful LLM call but no "
                 "recorded response (their vectors explain the Qdrant surplus above).")
        L.append("")
    return L


def _n(x):
    return "—" if x is None else f"{x:,}"


def _fmt_hms(seconds):
    if seconds is None:
        return "not measured"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}h {m}m {s}s ({seconds:,.0f}s)"


def _cell(pair):
    c, n = pair
    return f"{pct(c, n)}% ({c}/{n})" if n else "—"


def build_readme(run_dir, manifest, run_file, run_data, choice, pub_data, gpt5_data):
    lines = []
    name = manifest.get("run_name") or os.path.basename(run_dir.rstrip("/"))
    our_verd, qtype = ours_verdicts(run_data)
    qids = sorted(our_verd)
    their_verd = published_verdicts(pub_data) if pub_data else {}
    gpt5_verd = published_verdicts(gpt5_data) if gpt5_data else {}
    matched_60 = [q for q in qids if q in their_verd]
    matched_label = choice["label"] if choice["path"] else "matched"
    matched_extraction = (
        "parasail gpt-120b" if choice["file"] == "longmemeval_parasail_120b.json"
        else "gpt-5" if choice["file"] == "longmemeval_gpt5.json"
        else ((pub_data or {}).get("metadata", {}).get("project_name") or "not recorded")
    )

    metrics = run_data.get("metrics_by_cutoff", {})
    pub_metrics = (pub_data or {}).get("metrics_by_cutoff", {}).get("top_200", {}) if pub_data else {}
    pub_meta = (pub_data or {}).get("metadata", {}) if pub_data else {}
    facts = run_facts(run_dir)

    lines.append(f"# {name}")
    lines.append("")
    lines.append(
        f"LongMemEval run, **{len(qids)} questions** "
        f"(`{manifest.get('sample_args', '')}`). Compared like-with-like against the "
        f"published Mem0 OSS result whose extraction model matches ours."
    )
    lines.append("")
    if choice["path"]:
        lines.append(f"- **Matched published file:** `memory-benchmarks/results/oss/{choice['file']}` — {choice['label']}")
    else:
        lines.append(f"- **Matched published file:** none — {choice['label']} for extraction model `{choice['model']}`")
    lines.append(f"- **Our results file:** `{os.path.basename(run_file)}`")
    lines.append(
        "- Generated by `experiments/scripts/compare_lme_to_published.py`. "
        "All numbers are measured from this run's files; nothing is projected."
    )
    lines.append("")

    # ---------- 1. setup ----------
    lines.append("## 1. Setup — ours vs the two published runs")
    lines.append("")
    lines.append("Published cells come from the run's **result file**; where it is silent, from "
                 "Mem0's **benchmarks README L242** (same embedder / vector store / answerer / judge "
                 "for all their LongMemEval OSS rows), cited in brackets. `not recorded` is kept only "
                 "where neither the result file nor the README says anything. The published columns "
                 "share the same answerer/judge (GPT-5) as ours; they differ in the **extraction** model.")
    lines.append("")
    ours_map = {
        "extraction model": manifest.get("extraction_llm"),
        "extraction provider": manifest.get("extraction_provider_pin"),
        "reasoning": manifest.get("reasoning_effort"),
        "extraction max_tokens": manifest.get("extraction_max_tokens"),
        "embedder": manifest.get("embedder_label") or manifest.get("embedder"),
        "embedding dims": manifest.get("embedding_dims"),
        "vector store": "Qdrant",
        "answerer": manifest.get("answerer_model"),
        "judge": manifest.get("judge_model"),
        "answerer/judge provider": manifest.get("provider"),
        "top_k": manifest.get("top_k"),
        "cutoffs": manifest.get("top_k_cutoffs"),
        "Mem0 version": f"{manifest.get('mem0_ref')} ({(manifest.get('mem0_commit') or '')[:7]})",
        "dataset": f"{os.path.basename(manifest.get('dataset_path', '') or '')} "
                   f"(sha {str(manifest.get('dataset_sha256', ''))[:12]}…)",
    }
    pub_meta_m = (pub_data or {}).get("metadata", {})
    matched_provider = (
        f"Parasail [{choice['file']}, project {pub_meta_m.get('project_name', '?')}]"
        if choice["file"] == "longmemeval_parasail_120b.json" else "not recorded"
    )
    matched_col = pub_setup_col(pub_data, matched_extraction, matched_provider)
    gpt5_col = pub_setup_col(gpt5_data, "gpt-5", "not recorded")
    col_h = (matched_label if choice["path"] else "matched (none)")
    lines.append(f"| field | ours | {col_h} | Mem0 gpt-5 run |")
    lines.append("|---|---|---|---|")
    for field, ours in ours_map.items():
        o = ours if ours not in (None, "") else "not recorded"
        lines.append(f"| {field} | {o} | {matched_col[field]} | {gpt5_col[field]} |")
    lines.append("")

    # ---------- 2. accuracy on same 60 ----------
    lines.append(f"## 2. Accuracy on the same {len(matched_60)} question_ids")
    lines.append("")
    lines.append(
        "Judge PASS rate on the identical question set. The published run reports **top_200 only**; "
        "our 50/20/10 columns are our own retrieval-cutoff sweep (no published counterpart)."
    )
    lines.append("")
    their_maps = {}
    if their_verd:
        their_maps[matched_extraction] = their_verd
    if gpt5_verd:
        their_maps["gpt-5"] = gpt5_verd
    if their_maps:
        acc = accuracy_table(matched_60, qtype, our_verd, their_maps)
        hdr = ["question type", "ours @200"]
        if their_verd:
            hdr.append(f"{matched_extraction} @200")
        if gpt5_verd:
            hdr.append("gpt-5 @200")
        hdr += ["ours @50", "ours @20", "ours @10"]
        lines.append("| " + " | ".join(hdr) + " |")
        lines.append("|" + "---|" * len(hdr))
        for b in TYPES + ["overall"]:
            r = acc[b]
            label = "**overall**" if b == "overall" else b
            cells = [label, _cell(r["top_200"])]
            if their_verd:
                cells.append(_cell(r["their"][matched_extraction]))
            if gpt5_verd:
                cells.append(_cell(r["their"]["gpt-5"]))
            cells += [_cell(r["top_50"]), _cell(r["top_20"]), _cell(r["top_10"])]
            lines.append("| " + " | ".join(cells) + " |")
    else:
        lines.append("_No per-question published verdicts available, so no same-set comparison is possible._")
    lines.append("")

    # ---------- 3. published on all 500 ----------
    lines.append("## 3. Published numbers on all " + str(pub_meta.get("total_questions", "?")) + " (reference)")
    lines.append("")
    if pub_metrics:
        lines.append("Mem0's published run over its full question set — **not** our 60. For context only.")
        lines.append("")
        lines.append("| question type | accuracy |")
        lines.append("|---|---|")
        bt = pub_metrics.get("by_question_type", {})
        for t in TYPES:
            v = bt.get(t)
            if v:
                lines.append(f"| {t} | {round(v['accuracy'], 1)}% ({v['correct']}/{v['total']}) |")
        ov = pub_metrics.get("overall", {})
        if ov:
            lines.append(f"| **overall** | **{round(ov['accuracy'], 1)}% ({ov['correct']}/{ov['total']})** |")
    else:
        lines.append("_No published metrics available._")
    lines.append("")

    # ---------- 4. per-question agreement ----------
    lines.append("## 4. Per-question agreement (top_200)")
    lines.append("")
    if their_verd:
        ag = agreement(matched_60, our_verd, their_verd)
        lines.append("| bucket | count |")
        lines.append("|---|---|")
        lines.append(f"| both right | {len(ag['both_right'])} |")
        lines.append(f"| both wrong | {len(ag['both_wrong'])} |")
        lines.append(f"| only ours right | {len(ag['only_ours'])} |")
        lines.append(f"| only theirs right | {len(ag['only_theirs'])} |")
        lines.append("")
        lines.append("Disagreements (question_ids):")
        lines.append("")
        lines.append(f"- **only ours right** ({len(ag['only_ours'])}): "
                     + (", ".join(f"`{q}`" for q in ag["only_ours"]) or "none"))
        lines.append(f"- **only theirs right** ({len(ag['only_theirs'])}): "
                     + (", ".join(f"`{q}`" for q in ag["only_theirs"]) or "none"))
        lines.append(f"- **both wrong** ({len(ag['both_wrong'])}): "
                     + (", ".join(f"`{q}`" for q in ag["both_wrong"]) or "none"))
    else:
        lines.append("_No per-question published verdicts to compare against._")
    lines.append("")

    # ---------- 5. run facts ----------
    lines.append("## 5. Run facts (measured)")
    lines.append("")
    if facts:
        reasoning = (
            "not separately recorded (GPT-OSS reasoning is counted within the output tokens above)"
            if not facts["reasoning_recorded"] else "recorded"
        )
        lines.append("| metric | value |")
        lines.append("|---|---|")
        lines.append(f"| wall time (trace span) | {_fmt_hms(facts['wall_s'])} |")
        lines.append(f"| add calls made | {_n(facts['add_calls'])} |")
        lines.append(f"| add calls without response | {_n(facts['add_failed'])} |")
        lines.append(f"| memories stored | {_n(facts['mem_stored'])} |")
        lines.append(f"| memories per add | {facts['mem_per_add']} |")
        lines.append(f"| adds that stored 0 memories | {_n(facts['add_zero'])} "
                     f"({facts['add_zero_pct']}%) |")
        lines.append(f"| extraction LLM calls | {_n(facts['llm_calls'])} |")
        lines.append(f"| extraction tokens — input | {_n(facts['tok_in'])} |")
        lines.append(f"| extraction tokens — output | {_n(facts['tok_out'])} |")
        lines.append(f"| extraction tokens — reasoning | {reasoning} |")
        lines.append(f"| extraction tokens — total | {_n(facts['tok_total'])} |")
        lines.append(f"| cut-offs (finish_reason=length) | {_n(facts['cutoffs'])} |")
        lines.append(f"| parse failures (parse_ok=false) | {_n(facts['parse_fail'])} |")
        lines.append(f"| extraction LLM errors | {_n(facts['llm_err'])} |")
        lines.append(f"| search latency (avg over {len(facts['search_ms'])} searches) | "
                     f"{facts['search_ms_avg']} ms |" if facts["search_ms_avg"] is not None
                     else "| search latency | not measured |")
    else:
        lines.append("_No mem0 trace found in the run folder._")
    lines.append("")

    # ---------- 6. cost ----------
    lines.append("## 6. Cost")
    lines.append("")
    lines.append("Source: OpenRouter and OpenAI billing pages, entered by Loubna.")
    lines.append("")
    n_q = len(qids) or 1
    ex_label, ex_cost = COST["extraction"]
    aj_label, aj_cost = COST["answer_judge"]
    total = COST["total"]
    lines.append("| component | model / provider | cost (USD) | per question (÷%d) |" % len(qids))
    lines.append("|---|---|---|---|")
    lines.append(f"| extraction | {ex_label} | ${ex_cost:.2f} | ${ex_cost / n_q:.4f} |")
    lines.append(f"| answerer + judge | {aj_label} | ${aj_cost:.2f} | ${aj_cost / n_q:.4f} |")
    lines.append(f"| **total** | | **${total:.2f}** | **${total / n_q:.4f}** |")
    lines.append("")

    # ---------- 7. large artifacts not committed ----------
    big = large_artifacts(run_dir)
    if big:
        lines.append("## 7. Large artifacts not committed (over GitHub's 100 MB limit)")
        lines.append("")
        lines.append("These stay on the machine; recorded here by path / size / sha256 so they can "
                     "be re-identified. Everything else in this folder is committed.")
        lines.append("")
        lines.append("| file | size | sha256 |")
        lines.append("|---|---|---|")
        for rel, sz, sha in big:
            lines.append(f"| `{rel}` | {sz:,} bytes ({sz / 1e6:.1f} MB) | `{sha}` |")
        lines.append("")

    # ---------- memory store (from store_facts.json, if present) ----------
    lines += memory_store_section(run_dir)

    # ---------- observations ----------
    lines.append("## Observations")
    lines.append("")
    lines.append("<!-- written by hand -->")
    lines.append("")

    return "\n".join(lines)


def run_verdicts_types(run_data):
    """question_id -> {cutoff: PASS/FAIL} and question_id -> question_type."""
    verd, qtype = {}, {}
    for e in run_data.get("evaluations", []):
        qid = e["question_id"]
        qtype[qid] = e.get("question_type")
        cr = e.get("cutoff_results") or {}
        verd[qid] = {c: (cr.get(c) or {}).get("judgment") for c in CUTOFFS}
    return verd, qtype


def build_two_run_readme(run_dir, manifest, run_file, run_data, ref_dir):
    """README comparing OUR run (e.g. Luna) against another of OUR runs (e.g. GPT-OSS):
    setup, accuracy per type per cutoff, flips, run facts, a cost line, empty Observations."""
    name = manifest.get("run_name") or os.path.basename(run_dir.rstrip("/"))
    ref_manifest = load_json(os.path.join(ref_dir, "manifest.json"))
    ref_name = ref_manifest.get("run_name") or os.path.basename(ref_dir.rstrip("/"))
    _ref_file, ref_data = unified_results(ref_dir)
    ov, oqt = run_verdicts_types(run_data)
    rv, rqt = run_verdicts_types(ref_data)
    shared = sorted(set(ov) & set(rv))
    qtype = {q: (oqt.get(q) or rqt.get(q)) for q in shared}
    types = [t for t in TYPES if t in set(qtype.values())] or TYPES
    facts = run_facts(run_dir)

    L = []
    L.append(f"# {name}")
    L.append("")
    L.append(f"LongMemEval run — extraction **{manifest.get('extraction_llm')}** via "
             f"{manifest.get('extraction_endpoint', 'n/a')}. Compared against our "
             f"**{ref_manifest.get('extraction_llm')}** run `{ref_name}` on their "
             f"{len(shared)} shared question_ids.")
    L.append("")

    # ---- setup ----
    L.append("## 1. Setup — this run vs the reference run")
    L.append("")
    L.append(f"| field | {name} | {ref_name} |")
    L.append("|---|---|---|")
    fields = ["extraction_llm", "extraction_endpoint", "extraction_provider_pin",
              "extraction_max_tokens", "reasoning_effort", "answerer_model", "judge_model",
              "answerer_endpoint", "embedder_label", "embedding_dims", "top_k", "top_k_cutoffs",
              "mem0_ref", "collection_name"]
    labels = {"extraction_llm": "extraction model", "extraction_endpoint": "extraction endpoint",
              "extraction_provider_pin": "extraction provider", "extraction_max_tokens": "extraction max_tokens",
              "reasoning_effort": "reasoning", "answerer_model": "answerer", "judge_model": "judge",
              "answerer_endpoint": "answerer/judge endpoint", "embedder_label": "embedder",
              "embedding_dims": "embedding dims", "top_k": "top_k", "top_k_cutoffs": "cutoffs",
              "mem0_ref": "Mem0 version", "collection_name": "collection"}
    for f in fields:
        L.append(f"| {labels.get(f, f)} | {manifest.get(f, '—')} | {ref_manifest.get(f, '—')} |")
    L.append("")

    # ---- accuracy per type per cutoff ----
    L.append(f"## 2. Accuracy on the same {len(shared)} question_ids — per type, per cutoff")
    L.append("")

    def acc(verd):
        by = {t: {c: [0, 0] for c in CUTOFFS} for t in types}
        ov_ = {c: [0, 0] for c in CUTOFFS}
        for q in shared:
            t = qtype.get(q)
            for c in CUTOFFS:
                j = verd.get(q, {}).get(c)
                if j:
                    ok = 1 if j == "PASS" else 0
                    if t in by:
                        by[t][c][0] += ok
                        by[t][c][1] += 1
                    ov_[c][0] += ok
                    ov_[c][1] += 1
        return by, ov_
    oby, oov = acc(ov)
    rby, rov = acc(rv)
    head = ["type"] + [f"{name.split('_')[-1] or 'ours'} {c.replace('top_', '@')}" for c in CUTOFFS] \
        + [f"ref {c.replace('top_', '@')}" for c in CUTOFFS]
    # keep headers short
    head = ["type"] + [f"this @{c.split('_')[1]}" for c in CUTOFFS] + [f"ref @{c.split('_')[1]}" for c in CUTOFFS]
    L.append("| " + " | ".join(head) + " |")
    L.append("|" + "---|" * len(head))
    for t in types + ["overall"]:
        ob = oov if t == "overall" else oby[t]
        rb = rov if t == "overall" else rby[t]
        label = "**overall**" if t == "overall" else t
        cells = [label] + [_cell(ob[c]) for c in CUTOFFS] + [_cell(rb[c]) for c in CUTOFFS]
        L.append("| " + " | ".join(cells) + " |")
    L.append("")
    L.append(f"Columns: `this` = {name} ({manifest.get('extraction_llm')}), "
             f"`ref` = {ref_name} ({ref_manifest.get('extraction_llm')}).")
    L.append("")

    # ---- flips ----
    L.append("## 3. Flips (top_200)")
    L.append("")
    both_r = both_w = only_this = only_ref = 0
    flip_this, flip_ref = [], []
    for q in shared:
        a = ov.get(q, {}).get("top_200") == "PASS"
        b = rv.get(q, {}).get("top_200") == "PASS"
        if a and b:
            both_r += 1
        elif not a and not b:
            both_w += 1
        elif a and not b:
            only_this += 1
            flip_this.append(q)
        else:
            only_ref += 1
            flip_ref.append(q)
    L.append("| bucket | count |")
    L.append("|---|---|")
    L.append(f"| both right | {both_r} |")
    L.append(f"| both wrong | {both_w} |")
    L.append(f"| only this run right | {only_this} |")
    L.append(f"| only reference right | {only_ref} |")
    L.append("")
    L.append(f"- **only {name} right** ({only_this}): " + (", ".join(f"`{q}`" for q in flip_this) or "none"))
    L.append(f"- **only {ref_name} right** ({only_ref}): " + (", ".join(f"`{q}`" for q in flip_ref) or "none"))
    L.append("")

    # ---- run facts ----
    L.append("## 4. Run facts (measured)")
    L.append("")
    if facts:
        reasoning = ("recorded" if facts["reasoning_recorded"]
                     else "reported within completion tokens (not separately summed)")
        L.append("| metric | value |")
        L.append("|---|---|")
        L.append(f"| wall time (trace span) | {_fmt_hms(facts['wall_s'])} |")
        L.append(f"| add calls made | {_n(facts['add_calls'])} |")
        L.append(f"| add calls without response (rate-limit/quota/gateway) | {_n(facts['add_failed'])} |")
        L.append(f"| memories stored | {_n(facts['mem_stored'])} |")
        L.append(f"| memories per add | {facts['mem_per_add']} |")
        L.append(f"| adds that stored 0 memories | {_n(facts['add_zero'])} ({facts['add_zero_pct']}%) |")
        L.append(f"| extraction LLM calls | {_n(facts['llm_calls'])} |")
        L.append(f"| extraction tokens — input / output / total | "
                 f"{_n(facts['tok_in'])} / {_n(facts['tok_out'])} / {_n(facts['tok_total'])} |")
        L.append(f"| reasoning tokens | {reasoning} |")
        L.append(f"| cut-offs (finish_reason=length) | {_n(facts['cutoffs'])} |")
        L.append(f"| parse failures | {_n(facts['parse_fail'])} |")
        L.append(f"| extraction LLM errors | {_n(facts['llm_err'])} |")
        if facts["search_ms_avg"] is not None:
            L.append(f"| search latency (avg) | {facts['search_ms_avg']} ms |")
    else:
        L.append("_No mem0 trace found in the run folder._")
    L.append("")

    # ---- cost ----
    L.append("## 5. Cost")
    L.append("")
    L.append("Source: OpenRouter / OpenAI / Sub2API billing, entered by Loubna.")
    L.append("")
    L.append("| component | model / endpoint | cost (USD) |")
    L.append("|---|---|---|")
    L.append(f"| extraction | {manifest.get('extraction_llm')} via {manifest.get('extraction_endpoint','gateway')} | _fill in_ |")
    L.append(f"| answerer + judge | {manifest.get('answerer_model')} via {manifest.get('answerer_endpoint','OpenAI')} | _fill in_ |")
    L.append("| **total** | | _fill in_ |")
    L.append("")

    big = large_artifacts(run_dir)
    if big:
        L.append("## 6. Large artifacts not committed (over GitHub's 100 MB limit)")
        L.append("")
        L.append("| file | size | sha256 |")
        L.append("|---|---|---|")
        for rel, sz, sha in big:
            L.append(f"| `{rel}` | {sz:,} bytes ({sz / 1e6:.1f} MB) | `{sha}` |")
        L.append("")

    L += memory_store_section(run_dir)

    L.append("## Observations")
    L.append("")
    L.append("<!-- written by hand -->")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="path to the run folder")
    ap.add_argument("--vs", default=None, help="compare against another of OUR runs (path); "
                                               "writes a two-run README instead of the published one")
    ap.add_argument("--out", default=None, help="output README path (default: <run>/README.md)")
    ap.add_argument("--print", action="store_true", help="also print the README to stdout")
    args = ap.parse_args()

    run_dir = os.path.abspath(args.run)
    manifest = load_json(os.path.join(run_dir, "manifest.json"))
    run_file, run_data = unified_results(run_dir)

    if args.vs:
        readme = build_two_run_readme(run_dir, manifest, run_file, run_data, os.path.abspath(args.vs))
    else:
        choice = published_choice(manifest)
        pub_data = load_json(choice["path"]) if choice["path"] else None
        gpt5_data = load_json(GPT5_FILE) if os.path.exists(GPT5_FILE) else None
        readme = build_readme(run_dir, manifest, run_file, run_data, choice, pub_data, gpt5_data)

    out = args.out or os.path.join(run_dir, "README.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(readme)
    print(f"wrote {out}")
    if args.print:
        print()
        print(readme)


if __name__ == "__main__":
    main()
