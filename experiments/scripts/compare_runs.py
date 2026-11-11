#!/usr/bin/env python3
"""Compare two LoCoMo conv0 run folders: facts only, no interpretation.

Usage:
    experiments/memory-benchmarks/.venv/bin/python experiments/scripts/compare_runs.py <run_folder_A> <run_folder_B>

Reads, for each run folder:
    manifest.json
    locomo_results_*.json (latest by filename, same convention as summarize_run.py)
    console.log
    store_snapshot/{memories,entities}.jsonl (must already exist; run export_store.py first)
    storage_profile.md (must already exist; run profile_storage.py first)
    trace_facts/<question_id>.md (used only to build links; must already exist for
        every flipped question, in both run folders; run trace_question.py first)

Prints Markdown to stdout. States facts only; draws no conclusions about why
questions failed or why the two runs differ.
"""

import glob
import json
import re
import statistics
import sys
from pathlib import Path

import tiktoken

CUTOFFS = ["top_10", "top_20", "top_50", "top_200"]
CATEGORIES = ["multi-hop", "open-domain", "single-hop", "temporal"]


def load_manifest(run_dir: Path) -> dict:
    return json.load(open(run_dir / "manifest.json"))


def load_results(run_dir: Path):
    files = sorted(glob.glob(str(run_dir / "locomo_results_*.json")))
    if not files:
        raise SystemExit(f"no locomo_results_*.json found in {run_dir}")
    results_path = Path(files[-1])
    return results_path, json.load(open(results_path))


def load_console_lines(run_dir: Path) -> list[str]:
    path = run_dir / "console.log"
    if not path.exists():
        return []
    data = path.read_text()
    parts = re.split(r"[\r\n]+", data)
    return [p for p in parts if p.strip()]


def final_progress_lines(console_lines: list[str], prefix: str) -> list[str]:
    """Return the console.log lines starting with `prefix` that reached 100%,
    in the order they appear (last one(s) are the final state for that bar)."""
    return [line for line in console_lines if line.startswith(prefix) and "100%" in line]


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def results_mtime_utc(results_path: Path) -> str:
    import datetime

    return datetime.datetime.fromtimestamp(
        results_path.stat().st_mtime, tz=datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_started_utc(manifest: dict) -> "object":
    import datetime

    return datetime.datetime.strptime(manifest["started_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc
    )


def parse_mtime_utc(ts_str: str) -> "object":
    import datetime

    return datetime.datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc
    )


def fmt_timedelta(td) -> str:
    total_seconds = int(td.total_seconds())
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s ({total_seconds}s)"


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile on a sorted copy of values (0 <= pct <= 100)."""
    if not values:
        return float("nan")
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (pct / 100.0) * (len(s) - 1)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def token_stats(evaluations: list[dict], enc) -> dict:
    stats = {}
    for cutoff in CUTOFFS:
        n = int(cutoff.split("_")[1])
        per_question_tokens = []
        for e in evaluations:
            memories = e["retrieval"]["search_results"][:n]
            text = "\n".join(m["memory"] for m in memories)
            per_question_tokens.append(len(enc.encode(text)))
        stats[cutoff] = {
            "mean": statistics.mean(per_question_tokens),
            "median": statistics.median(per_question_tokens),
        }
    return stats


def parse_storage_profile(run_dir: Path) -> dict:
    """Pull the few numbers we need back out of storage_profile.md (facts
    already computed by profile_storage.py; not recomputed here)."""
    path = run_dir / "storage_profile.md"
    if not path.exists():
        raise SystemExit(f"missing {path}; run profile_storage.py first")
    text = path.read_text()

    def grab(pattern: str, cast=str):
        m = re.search(pattern, text)
        return cast(m.group(1)) if m else None

    return {
        "memories": grab(r"- Memories: (\d+)", int),
        "entities": grab(r"- Entities: (\d+)", int),
        "links_median": grab(r"## Links per entity\n- min: [\d.]+\n- median: ([\d.]+)", float),
        "links_mean": grab(r"- mean: ([\d.]+)", float),
        "links_max": grab(r"- max: (\d+)", int),
    }


def judgment(evaluation: dict, cutoff: str) -> str:
    return evaluation["cutoff_results"].get(cutoff, {}).get("judgment", "not recorded")


def cell(text) -> str:
    """Flatten a value for a Markdown table cell: no raw newlines, no pipes."""
    if text is None:
        return "not recorded"
    s = str(text)
    s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    s = s.replace("|", "\\|")
    return s.strip()


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} <run_folder_A> <run_folder_B>")
    run_a = Path(sys.argv[1])
    run_b = Path(sys.argv[2])

    manifest_a = load_manifest(run_a)
    manifest_b = load_manifest(run_b)
    results_path_a, results_a = load_results(run_a)
    results_path_b, results_b = load_results(run_b)
    console_a = load_console_lines(run_a)
    console_b = load_console_lines(run_b)

    evals_a = {e["question_id"]: e for e in results_a["evaluations"]}
    evals_b = {e["question_id"]: e for e in results_b["evaluations"]}
    common_qids = sorted(set(evals_a) & set(evals_b), key=lambda q: int(q.split("_q")[1]))
    if set(evals_a) != set(evals_b):
        only_a = set(evals_a) - set(evals_b)
        only_b = set(evals_b) - set(evals_a)
        print(f"NOTE: question_id sets differ. Only in A: {sorted(only_a)}. Only in B: {sorted(only_b)}.", file=sys.stderr)

    lines = []
    lines.append(f"# Comparison: {run_a.name} (A) vs {run_b.name} (B)")
    lines.append("")
    lines.append(f"- A: `{run_a}`")
    lines.append(f"- B: `{run_b}`")
    lines.append("")

    # ---- 1. J ----
    lines.append("## 1. J")
    lines.append("")
    lines.append("J = % of questions the judge model labelled CORRECT.")
    lines.append("")
    lines.append("| cutoff | J_A (%) | J_B (%) | diff (pts, B-A) | correct_A/total | correct_B/total | diff (questions, B-A) |")
    lines.append("|---|---|---|---|---|---|---|")
    for cutoff in CUTOFFS:
        ma = results_a["metrics_by_cutoff"][cutoff]["overall"]
        mb = results_b["metrics_by_cutoff"][cutoff]["overall"]
        diff_pts = mb["accuracy"] - ma["accuracy"]
        diff_q = mb["correct"] - ma["correct"]
        lines.append(
            f"| {cutoff} | {ma['accuracy']:.1f} | {mb['accuracy']:.1f} | {diff_pts:+.1f} | "
            f"{ma['correct']}/{ma['total']} | {mb['correct']}/{mb['total']} | {diff_q:+d} |"
        )
    lines.append("")

    lines.append("Per-category at top_200:")
    lines.append("")
    lines.append("| category | correct_A/total | correct_B/total | diff (questions, B-A) |")
    lines.append("|---|---|---|---|")
    cat_a = results_a["metrics_by_cutoff"]["top_200"]["by_category"]
    cat_b = results_b["metrics_by_cutoff"]["top_200"]["by_category"]
    for cat in CATEGORIES:
        ca = cat_a.get(cat)
        cb = cat_b.get(cat)
        if ca is None or cb is None:
            lines.append(f"| {cat} | not recorded | not recorded | not recorded |")
            continue
        diff_q = cb["correct"] - ca["correct"]
        lines.append(f"| {cat} | {ca['correct']}/{ca['total']} | {cb['correct']}/{cb['total']} | {diff_q:+d} |")
    lines.append("")

    # ---- 2. Flips at top_200 ----
    lines.append("## 2. Flips at top_200 (match by question_id)")
    lines.append("")
    correct_a_wrong_b = []
    wrong_a_correct_b = []
    for qid in common_qids:
        ja = judgment(evals_a[qid], "top_200")
        jb = judgment(evals_b[qid], "top_200")
        if ja == "CORRECT" and jb == "WRONG":
            correct_a_wrong_b.append(qid)
        elif ja == "WRONG" and jb == "CORRECT":
            wrong_a_correct_b.append(qid)

    def cat_counts(qids, eval_map):
        counts = {}
        for qid in qids:
            cat = eval_map[qid]["category_name"]
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    counts_cab = cat_counts(correct_a_wrong_b, evals_a)
    counts_wac = cat_counts(wrong_a_correct_b, evals_a)

    lines.append(f"- Correct in A, wrong in B: {len(correct_a_wrong_b)}")
    for cat in sorted(counts_cab):
        lines.append(f"  - {cat}: {counts_cab[cat]}")
    lines.append(f"- Wrong in A, correct in B: {len(wrong_a_correct_b)}")
    for cat in sorted(counts_wac):
        lines.append(f"  - {cat}: {counts_wac[cat]}")
    lines.append("")

    lines.append("| question_id | category | question | gold answer | A's answer (top_200) | B's answer (top_200) | trace (A) | trace (B) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    all_flips = [(qid, "correct_A_wrong_B") for qid in correct_a_wrong_b] + [
        (qid, "wrong_A_correct_B") for qid in wrong_a_correct_b
    ]
    all_flips.sort(key=lambda t: int(t[0].split("_q")[1]))
    for qid, _kind in all_flips:
        ea = evals_a[qid]
        eb = evals_b[qid]
        ans_a = cell(ea["cutoff_results"]["top_200"].get("generated_answer", "not recorded"))
        ans_b = cell(eb["cutoff_results"]["top_200"].get("generated_answer", "not recorded"))
        gold = cell(ea["ground_truth_answer"])
        question = cell(ea["question"])
        cat = cell(ea["category_name"])
        trace_a_rel = f"../{run_a.name}/trace_facts/{qid}.md"
        trace_b_rel = f"../{run_b.name}/trace_facts/{qid}.md"
        lines.append(
            f"| {qid} | {cat} | {question} | {gold} | {ans_a} | {ans_b} | "
            f"[{run_a.name}/trace_facts/{qid}.md]({trace_a_rel}) | [{run_b.name}/trace_facts/{qid}.md]({trace_b_rel}) |"
        )
    lines.append("")

    # ---- 3. Tokens ----
    lines.append("## 3. Tokens")
    lines.append("")
    enc = tiktoken.get_encoding("o200k_base")
    tok_a = token_stats(results_a["evaluations"], enc)
    tok_b = token_stats(results_b["evaluations"], enc)

    lines.append("Estimate of retrieved-memory context only (tiktoken o200k_base, memory texts of the first N search_results per cutoff); excludes prompts, answers and judge calls.")
    lines.append("")
    lines.append("| cutoff | mean_A | median_A | mean_B | median_B |")
    lines.append("|---|---|---|---|---|")
    for cutoff in CUTOFFS:
        a = tok_a[cutoff]
        b = tok_b[cutoff]
        lines.append(f"| {cutoff} | {a['mean']:.1f} | {a['median']:.1f} | {b['mean']:.1f} | {b['median']:.1f} |")
    lines.append("")

    n_a = len(results_a["evaluations"])
    n_b = len(results_b["evaluations"])
    ingestion_files_a = sorted(glob.glob(str(run_a / "predicted_*" / "_ingestion_*.json")))
    ingestion_files_b = sorted(glob.glob(str(run_b / "predicted_*" / "_ingestion_*.json")))
    chunks_a = sum(json.load(open(f))["total_chunks_processed"] for f in ingestion_files_a)
    chunks_b = sum(json.load(open(f))["total_chunks_processed"] for f in ingestion_files_b)

    lines.append("API calls by design:")
    lines.append("")
    lines.append("| call type | A | B | formula |")
    lines.append("|---|---|---|---|")
    lines.append(f"| answer calls | {n_a * len(CUTOFFS)} | {n_b * len(CUTOFFS)} | questions x 4 cutoffs |")
    lines.append(f"| judge calls | {n_a * len(CUTOFFS)} | {n_b * len(CUTOFFS)} | questions x 4 cutoffs |")
    lines.append(f"| Mem0 add requests | {chunks_a} | {chunks_b} | ingestion chunks processed |")
    lines.append("")

    lines.append("Billed tokens: not recorded by the benchmark.")
    lines.append("")
    mtime_a = results_mtime_utc(results_path_a)
    mtime_b = results_mtime_utc(results_path_b)
    lines.append(f"- A: check the OpenAI usage dashboard for the time window `{manifest_a['started_utc']}` to `{mtime_a}` (UTC).")
    lines.append(f"- B: check the OpenAI usage dashboard for the time window `{manifest_b['started_utc']}` to `{mtime_b}` (UTC).")
    lines.append("")

    # ---- 4. Latency ----
    lines.append("## 4. Latency")
    lines.append("")
    lat_a = [e["retrieval"]["search_latency_ms"] for e in results_a["evaluations"]]
    lat_b = [e["retrieval"]["search_latency_ms"] for e in results_b["evaluations"]]

    lines.append("Search latency per question (`retrieval.search_latency_ms`), milliseconds:")
    lines.append("")
    lines.append("| run | median | mean | p90 | max |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        f"| A | {statistics.median(lat_a):.1f} | {statistics.mean(lat_a):.1f} | "
        f"{percentile(lat_a, 90):.1f} | {max(lat_a):.1f} |"
    )
    lines.append(
        f"| B | {statistics.median(lat_b):.1f} | {statistics.mean(lat_b):.1f} | "
        f"{percentile(lat_b, 90):.1f} | {max(lat_b):.1f} |"
    )
    lines.append("")

    started_a = parse_started_utc(manifest_a)
    started_b = parse_started_utc(manifest_b)
    end_a = parse_mtime_utc(mtime_a)
    end_b = parse_mtime_utc(mtime_b)
    lines.append("Whole-run wall time (results file timestamp minus manifest `started_utc`):")
    lines.append("")
    lines.append(f"- A: `{manifest_a['started_utc']}` to `{mtime_a}` = {fmt_timedelta(end_a - started_a)}")
    lines.append(f"- B: `{manifest_b['started_utc']}` to `{mtime_b}` = {fmt_timedelta(end_b - started_b)}")
    lines.append("")

    ingest_a = final_progress_lines(console_a, "Ingest conv 0")
    ingest_b = final_progress_lines(console_b, "Ingest conv 0")
    questions_a = final_progress_lines(console_a, "Questions conv 0")
    questions_b = final_progress_lines(console_b, "Questions conv 0")

    if ingest_a or ingest_b or questions_a or questions_b:
        lines.append("Phase times, final progress line from console.log for each phase:")
        lines.append("")
        lines.append(f"- A, ingestion: `{ingest_a[-1] if ingest_a else 'not recorded'}`")
        lines.append(f"- A, evaluation: `{questions_a[-1] if questions_a else 'not recorded'}`")
        lines.append(f"- B, ingestion: `{ingest_b[-1] if ingest_b else 'not recorded'}`")
        lines.append(f"- B, evaluation: `{questions_b[-1] if questions_b else 'not recorded'}`")
    else:
        lines.append("Phase times: not recorded")
    lines.append("")
    lines.append("Only search latency is measured per query. Add, answer and judge calls are not timed individually.")
    lines.append("")

    # ---- 5. Storage ----
    lines.append("## 5. Storage")
    lines.append("")
    sp_a = parse_storage_profile(run_a)
    sp_b = parse_storage_profile(run_b)
    lines.append("| | A | B |")
    lines.append("|---|---|---|")
    lines.append(f"| Memories | {sp_a['memories']} | {sp_b['memories']} |")
    lines.append(f"| Entities | {sp_a['entities']} | {sp_b['entities']} |")
    lines.append(f"| Links per entity, median | {sp_a['links_median']} | {sp_b['links_median']} |")
    lines.append(f"| Links per entity, mean | {sp_a['links_mean']} | {sp_b['links_mean']} |")
    lines.append(f"| Links per entity, max | {sp_a['links_max']} | {sp_b['links_max']} |")
    lines.append("")

    # ---- 6. Fixed note ----
    lines.append("## 6. Note")
    lines.append("")
    lines.append(
        "Each run ingested conversation 0 separately with an LLM, so their stored memories differ "
        "(see Storage). A flip can come from the weight change or from a different stored memory; "
        "this comparison does not separate the two."
    )
    lines.append("")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
