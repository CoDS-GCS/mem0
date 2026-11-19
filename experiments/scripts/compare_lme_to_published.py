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
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXP = os.path.dirname(_HERE)
PUBLISHED_DIR = os.path.join(_EXP, "memory-benchmarks", "results", "oss")

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


def accuracy_table(qids, qtype, our_verd, their_verd):
    """Overall + per-type accuracy on the SAME qids: ours @ each cutoff, theirs @ top_200."""
    # counters[type_or_overall][cutoff] = [correct, total]; theirs keyed under "top_200".
    rows = {}
    buckets = TYPES + ["overall"]
    for b in buckets:
        rows[b] = {c: [0, 0] for c in CUTOFFS}
        rows[b]["their_top_200"] = [0, 0]
    for qid in qids:
        t = qtype.get(qid)
        targets = [t, "overall"] if t else ["overall"]
        for c in CUTOFFS:
            j = our_verd.get(qid, {}).get(c)
            if j:
                for b in targets:
                    rows[b][c][0] += 1 if j == "PASS" else 0
                    rows[b][c][1] += 1
        tj = their_verd.get(qid)
        if tj:
            for b in targets:
                rows[b]["their_top_200"][0] += 1 if tj == "PASS" else 0
                rows[b]["their_top_200"][1] += 1
    return rows


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
        "add_calls": 0, "add_resp": 0, "mem_stored": 0,
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
                f["mem_stored"] += len((o.get("outputs") or {}).get("results") or [])
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
    f["search_ms_avg"] = round(sum(f["search_ms"]) / len(f["search_ms"]), 1) if f["search_ms"] else None
    return f


# --------------------------------------------------------------------------- formatting
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


def build_readme(run_dir, manifest, run_file, run_data, choice, pub_data):
    lines = []
    name = manifest.get("run_name") or os.path.basename(run_dir.rstrip("/"))
    our_verd, qtype = ours_verdicts(run_data)
    qids = sorted(our_verd)
    their_verd = published_verdicts(pub_data) if pub_data else {}
    matched_60 = [q for q in qids if q in their_verd]

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
    lines.append("## 1. Setup — ours vs matched published run")
    lines.append("")
    lines.append("`not recorded` = the published run's file does not state it.")
    lines.append("")
    lines.append("| field | ours | " + (choice["label"] if choice["path"] else "published") + " |")
    lines.append("|---|---|---|")
    setup = [
        ("extraction model", manifest.get("extraction_llm"),
         "parasail gpt-120b" if choice["file"] == "longmemeval_parasail_120b.json"
         else (pub_meta.get("project_name") or "not recorded")),
        ("extraction provider", manifest.get("extraction_provider_pin"), "not recorded"),
        ("reasoning", manifest.get("reasoning_effort"), "not recorded"),
        ("extraction max_tokens", manifest.get("extraction_max_tokens"), "not recorded"),
        ("embedder", manifest.get("embedder_label") or manifest.get("embedder"), "not recorded"),
        ("embedding dims", manifest.get("embedding_dims"), "not recorded"),
        ("answerer", manifest.get("answerer_model"), pub_meta.get("answerer_model") or "not recorded"),
        ("judge", manifest.get("judge_model"), pub_meta.get("judge_model") or "not recorded"),
        ("answerer/judge provider", manifest.get("provider"), pub_meta.get("provider") or "not recorded"),
        ("top_k", manifest.get("top_k"), pub_meta.get("top_k") or "not recorded"),
        ("cutoffs", manifest.get("top_k_cutoffs"),
         ", ".join(pub_meta.get("top_k_cutoffs", [])) or "not recorded"),
        ("Mem0 version", f"{manifest.get('mem0_ref')} ({(manifest.get('mem0_commit') or '')[:7]})", "not recorded"),
        ("dataset", f"{os.path.basename(manifest.get('dataset_path', '') or '')} "
                    f"(sha {str(manifest.get('dataset_sha256', ''))[:12]}…)",
         f"{pub_meta.get('total_questions', 'not recorded')} questions"
         + (" (all)" if pub_meta.get("all_questions") else "")),
    ]
    for field, ours, theirs in setup:
        lines.append(f"| {field} | {ours if ours not in (None, '') else 'not recorded'} | {theirs} |")
    lines.append("")

    # ---------- 2. accuracy on same 60 ----------
    lines.append(f"## 2. Accuracy on the same {len(matched_60)} question_ids")
    lines.append("")
    lines.append(
        "Judge PASS rate on the identical question set. The published run reports **top_200 only**; "
        "our 50/20/10 columns are our own retrieval-cutoff sweep (no published counterpart)."
    )
    lines.append("")
    if their_verd:
        acc = accuracy_table(matched_60, qtype, our_verd, their_verd)
        lines.append("| question type | ours @200 | theirs @200 | ours @50 | ours @20 | ours @10 |")
        lines.append("|---|---|---|---|---|---|")
        for b in TYPES + ["overall"]:
            r = acc[b]
            label = "**overall**" if b == "overall" else b
            lines.append(
                f"| {label} | {_cell(r['top_200'])} | {_cell(r['their_top_200'])} | "
                f"{_cell(r['top_50'])} | {_cell(r['top_20'])} | {_cell(r['top_10'])} |"
            )
    else:
        lines.append("_The matched published file has no per-question verdicts, so no same-set comparison is possible._")
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
        lines.append("| **cost (USD)** | _fill in from OpenRouter_ |")
    else:
        lines.append("_No mem0 trace found in the run folder._")
    lines.append("")

    # ---------- 6. observations ----------
    lines.append("## Observations")
    lines.append("")
    lines.append("<!-- written by hand -->")
    lines.append("")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="path to the run folder")
    ap.add_argument("--out", default=None, help="output README path (default: <run>/README.md)")
    ap.add_argument("--print", action="store_true", help="also print the README to stdout")
    args = ap.parse_args()

    run_dir = os.path.abspath(args.run)
    manifest = load_json(os.path.join(run_dir, "manifest.json"))
    run_file, run_data = unified_results(run_dir)
    choice = published_choice(manifest)
    pub_data = load_json(choice["path"]) if choice["path"] else None

    readme = build_readme(run_dir, manifest, run_file, run_data, choice, pub_data)
    out = args.out or os.path.join(run_dir, "README.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(readme)
    print(f"wrote {out}")
    if args.print:
        print()
        print(readme)


if __name__ == "__main__":
    main()
