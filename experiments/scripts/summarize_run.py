#!/usr/bin/env python3
"""Summarize one benchmark run folder: facts and numbers for its README.

Usage:
    experiments/memory-benchmarks/.venv/bin/python experiments/scripts/summarize_run.py <run_dir>

Reads manifest.json, locomo_results_*.json and predicted_*/_ingestion_*.json
from <run_dir> and prints a JSON report. Nothing here is estimated: every
number is read directly from those files or computed from them (latency
stats, retrieved-memory token counts).
"""

import datetime
import glob
import json
import statistics
import sys
from pathlib import Path

import tiktoken

CUTOFFS = ["top_10", "top_20", "top_50", "top_200"]


def load_results(run_dir: Path) -> dict:
    files = sorted(glob.glob(str(run_dir / "locomo_results_*.json")))
    if not files:
        raise SystemExit(f"no locomo_results_*.json found in {run_dir}")
    results_path = Path(files[-1])
    return results_path, json.load(open(results_path))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <run_dir>")
    run_dir = Path(sys.argv[1])

    manifest = json.load(open(run_dir / "manifest.json"))
    results_path, results = load_results(run_dir)
    results_mtime_utc = datetime.datetime.fromtimestamp(
        results_path.stat().st_mtime, tz=datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    ingestion_files = sorted(glob.glob(str(run_dir / "predicted_*" / "_ingestion_*.json")))
    ingestion = [json.load(open(f)) for f in ingestion_files]
    chunks_processed = sum(i["total_chunks_processed"] for i in ingestion)
    chunks_failed = sum(i["total_chunks_failed"] for i in ingestion)

    metadata = results["metadata"]
    evaluations = results["evaluations"]
    n_questions = len(evaluations)

    latencies = [e["retrieval"]["search_latency_ms"] for e in evaluations]

    enc = tiktoken.get_encoding("o200k_base")

    token_stats = {}
    for cutoff in CUTOFFS:
        n = int(cutoff.split("_")[1])
        per_question_tokens = []
        for e in evaluations:
            memories = e["retrieval"]["search_results"][:n]
            text = "\n".join(m["memory"] for m in memories)
            per_question_tokens.append(len(enc.encode(text)))
        token_stats[cutoff] = {
            "mean": statistics.mean(per_question_tokens),
            "median": statistics.median(per_question_tokens),
        }

    calls_by_design = {
        "answer_calls": n_questions * len(CUTOFFS),
        "judge_calls": n_questions * len(CUTOFFS),
        "mem0_add_requests": chunks_processed,
    }

    report = {
        "manifest": manifest,
        "results_file": results_path.name,
        "results_file_mtime_utc": results_mtime_utc,
        "metadata": metadata,
        "metrics_by_cutoff": results["metrics_by_cutoff"],
        "n_questions": n_questions,
        "ingestion": {
            "chunks_processed": chunks_processed,
            "chunks_failed": chunks_failed,
        },
        "search_latency_ms": {
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
        },
        "calls_by_design": calls_by_design,
        "retrieved_memory_tokens_o200k_base": token_stats,
    }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
