#!/usr/bin/env python3
"""Write fact sheets for individual LoCoMo questions in a run.

Usage:
    /shared_mnt/loubna/venv-analysis/bin/python experiments/scripts/trace_question.py <run_folder> [question_id ...] [--all-failures]

Reads the run's locomo_results_*.json, its store_snapshot/memories.jsonl
(from export_store.py) and the LoCoMo dataset
(experiments/memory-benchmarks/datasets/locomo/locomo10.json). For each
requested question writes <run_folder>/trace_facts/<question_id>.md.

This script states facts only (question, evidence, stored-memory candidates
by word overlap, retrieved memories, judge verdicts). It draws no
conclusions about why a question succeeded or failed.

With --all-failures: writes a trace file for every question judged WRONG at
top_200, plus an INDEX.md grouping them by category.
"""

import glob
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "experiments" / "memory-benchmarks" / "datasets" / "locomo" / "locomo10.json"
CUTOFFS = ["top_10", "top_20", "top_50", "top_200"]

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "of", "to", "in", "on", "at",
    "for", "with", "about", "as", "is", "are", "was", "were", "be", "been",
    "being", "it", "its", "this", "that", "these", "those", "i", "you", "he",
    "she", "we", "they", "them", "his", "her", "their", "my", "your", "our",
    "me", "him", "us", "do", "does", "did", "has", "have", "had", "will",
    "would", "can", "could", "should", "so", "than", "then", "there", "here",
    "what", "who", "when", "where", "why", "how", "not", "no", "yes", "up",
    "out", "all", "from", "by", "into", "also", "very", "just", "over",
}


def load_results(run_dir: Path) -> dict:
    files = sorted(glob.glob(str(run_dir / "locomo_results_*.json")))
    if not files:
        raise SystemExit(f"no locomo_results_*.json found in {run_dir}")
    return json.load(open(files[-1]))


def load_memories(run_dir: Path) -> dict[str, dict]:
    path = run_dir / "store_snapshot" / "memories.jsonl"
    if not path.exists():
        raise SystemExit(f"missing {path}; run export_store.py first")
    memories = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                m = json.loads(line)
                memories[m["id"]] = m
    return memories


def load_dataset() -> list:
    return json.load(open(DATASET_PATH))


def conv_index_from_qid(question_id: str) -> int:
    m = re.match(r"conv(\d+)_q", question_id)
    if not m:
        raise SystemExit(f"cannot parse conversation index from question_id {question_id!r}")
    return int(m.group(1))


def build_turn_index(conv_entry: dict) -> dict[str, dict]:
    conversation = conv_entry["conversation"]
    turns = {}
    i = 1
    while f"session_{i}" in conversation:
        date = conversation.get(f"session_{i}_date_time", "not recorded")
        for turn in conversation[f"session_{i}"]:
            turns[turn["dia_id"]] = {
                "speaker": turn["speaker"],
                "text": turn["text"],
                "session": i,
                "session_date": date,
            }
        i += 1
    return turns


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w for w in words if w not in STOPWORDS]


def overlap_score(evidence_words: list[str], memory_text: str) -> float:
    if not evidence_words:
        return 0.0
    mem_words = set(tokenize(memory_text))
    shared = set(evidence_words) & mem_words
    return len(shared) / len(evidence_words)


def find_in_retrieved(memory_id: str, search_results: list[dict]) -> dict | None:
    for i, r in enumerate(search_results):
        if r.get("id") == memory_id:
            debug = r.get("score_debug") or {}
            return {
                "rank": i + 1,
                "combined": debug.get("combined_score", r.get("score")),
                "semantic": debug.get("semantic_score"),
                "bm25": debug.get("bm25_score"),
                "entity_boost": debug.get("entity_boost"),
            }
    return None


def fmt_score(v) -> str:
    return "not recorded" if v is None else f"{v:.4f}" if isinstance(v, float) else str(v)


def render_trace(evaluation: dict, memories: dict[str, dict], turns: dict[str, dict]) -> str:
    qid = evaluation["question_id"]
    search_results = evaluation["retrieval"]["search_results"]

    lines = [f"# {qid}", ""]
    lines.append(f"- Question: {evaluation['question']}")
    lines.append(f"- Category: {evaluation['category_name']}")
    lines.append(f"- Gold answer: {evaluation['ground_truth_answer']}")
    lines.append(f"- Reference date: {evaluation.get('reference_date', 'not recorded')}")
    lines.append("")

    lines.append("## Evidence turns")
    evidence_words_by_turn = {}
    for dia_id in evaluation.get("evidence", []):
        turn = turns.get(dia_id)
        if turn is None:
            lines.append(f"- {dia_id}: not recorded (dia_id not found in dataset)")
            continue
        lines.append(
            f"- {dia_id} (session {turn['session']}, {turn['session_date']}), "
            f"{turn['speaker']}: \"{turn['text']}\""
        )
        evidence_words_by_turn[dia_id] = tokenize(turn["text"])
    lines.append("")

    lines.append("## Stored memory candidates")
    lines.append(
        "Candidates by word overlap; whether the needed memory was stored is for the analyst to decide."
    )
    for dia_id, words in evidence_words_by_turn.items():
        lines.append(f"")
        lines.append(f"### candidates for {dia_id}")
        scored = sorted(
            ((overlap_score(words, m["data"]), m) for m in memories.values()),
            key=lambda t: (-t[0], t[1]["created_at"] or "", t[1]["id"]),
        )
        top3 = [t for t in scored if t[0] > 0][:3]
        if not top3:
            lines.append("- not recorded (no stored memory shares any evidence word)")
        for score, m in top3:
            hit = find_in_retrieved(m["id"], search_results)
            if hit:
                scores_str = (
                    f"rank {hit['rank']}, combined {fmt_score(hit['combined'])}, "
                    f"semantic {fmt_score(hit['semantic'])}, bm25 {fmt_score(hit['bm25'])}, "
                    f"entity_boost {fmt_score(hit['entity_boost'])}"
                )
            else:
                scores_str = "not retrieved"
            lines.append(
                f"- overlap {score:.2f}; memory: \"{m['data']}\"; created_at: {m['created_at']}; {scores_str}"
            )
    lines.append("")

    lines.append("## Top 5 retrieved memories")
    for i, r in enumerate(search_results[:5]):
        debug = r.get("score_debug") or {}
        lines.append(
            f"- rank {i + 1}: \"{r.get('memory')}\"; created_at: {r.get('created_at', 'not recorded')}; "
            f"combined {fmt_score(debug.get('combined_score', r.get('score')))}, "
            f"semantic {fmt_score(debug.get('semantic_score'))}, "
            f"bm25 {fmt_score(debug.get('bm25_score'))}, "
            f"entity_boost {fmt_score(debug.get('entity_boost'))}"
        )
    lines.append("")

    lines.append("## Cutoff results")
    for cutoff in CUTOFFS:
        cr = evaluation["cutoff_results"].get(cutoff)
        if not cr:
            lines.append(f"- {cutoff}: not recorded")
            continue
        lines.append(
            f"- {cutoff}: judgment={cr.get('judgment', 'not recorded')}; "
            f"generated_answer=\"{cr.get('generated_answer', 'not recorded')}\"; "
            f"reason=\"{cr.get('reason', 'not recorded')}\""
        )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        raise SystemExit(f"usage: {sys.argv[0]} <run_folder> [question_id ...] [--all-failures]")
    run_dir = Path(args[0])
    rest = args[1:]
    all_failures = "--all-failures" in rest
    question_ids = [a for a in rest if a != "--all-failures"]

    results = load_results(run_dir)
    memories = load_memories(run_dir)
    dataset = load_dataset()

    evaluations_by_qid = {e["question_id"]: e for e in results["evaluations"]}

    if all_failures:
        targets = [
            e for e in results["evaluations"]
            if e["cutoff_results"].get("top_200", {}).get("judgment") == "WRONG"
        ]
    else:
        missing = [qid for qid in question_ids if qid not in evaluations_by_qid]
        if missing:
            raise SystemExit(f"question_id(s) not found in results: {missing}")
        targets = [evaluations_by_qid[qid] for qid in question_ids]

    out_dir = run_dir / "trace_facts"
    out_dir.mkdir(exist_ok=True)

    turns_by_conv: dict[int, dict] = {}
    written = []
    for evaluation in targets:
        conv_idx = conv_index_from_qid(evaluation["question_id"])
        if conv_idx not in turns_by_conv:
            turns_by_conv[conv_idx] = build_turn_index(dataset[conv_idx])
        content = render_trace(evaluation, memories, turns_by_conv[conv_idx])
        path = out_dir / f"{evaluation['question_id']}.md"
        path.write_text(content)
        written.append(evaluation)

    if all_failures:
        by_category: dict[str, list[dict]] = {}
        for e in written:
            by_category.setdefault(e["category_name"], []).append(e)
        lines = ["# Failures at top_200 (judgment == WRONG)", ""]
        lines.append(f"Total: {len(written)}")
        lines.append("")
        for category in sorted(by_category):
            evs = by_category[category]
            lines.append(f"## {category} ({len(evs)})")
            for e in sorted(evs, key=lambda e: e["question_id"]):
                lines.append(
                    f"- [{e['question_id']}]({e['question_id']}.md): {e['question']} "
                    f"-- gold: {e['ground_truth_answer']}"
                )
            lines.append("")
        (out_dir / "INDEX.md").write_text("\n".join(lines))
        print(f"wrote {len(written)} trace file(s) and INDEX.md to {out_dir}")
    else:
        print(f"wrote {len(written)} trace file(s) to {out_dir}")


if __name__ == "__main__":
    main()
