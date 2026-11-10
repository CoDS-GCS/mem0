#!/usr/bin/env python3
"""Profile one run's Qdrant store snapshot (facts and candidate lists only).

Usage:
    /shared_mnt/loubna/venv-analysis/bin/python experiments/scripts/profile_storage.py <run_folder>

Reads ONLY <run_folder>/store_snapshot/{memories,entities}.jsonl (produced by
export_store.py). Writes <run_folder>/storage_profile.md.

All "candidates" sections are plain lists for a human to pick examples from;
this script makes no judgment about which entities or memories are good or
bad.
"""

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

PRONOUNS = {
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us",
    "them", "this", "that", "these", "those", "my", "your", "his", "its",
    "our", "their", "mine", "yours", "hers", "ours", "theirs",
}
TIME_WORDS = {
    "yesterday", "today", "tomorrow", "tonight", "week", "year", "month",
    "day", "weekend", "morning", "afternoon", "evening", "night",
}

LINK_BUCKETS = [("1", lambda n: n == 1), ("2-3", lambda n: 2 <= n <= 3),
                ("4-10", lambda n: 4 <= n <= 10), ("11-50", lambda n: 11 <= n <= 50),
                (">50", lambda n: n > 50)]


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def normalize_for_near_dup(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"'s\b", "", t)
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > 3 and t.endswith("s"):
        t = t[:-1]
    return t


def is_short_or_generic(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) <= 2:
        return True
    if stripped.replace(".", "", 1).replace(",", "").isdigit():
        return True
    low = stripped.lower()
    if low in PRONOUNS or low in TIME_WORDS:
        return True
    return False


def memory_texts_for(ids: list[str], memories_by_id: dict[str, dict], limit: int = 2) -> list[str]:
    out = []
    for mid in ids[:limit]:
        m = memories_by_id.get(mid)
        out.append(m["data"] if m else f"<missing memory id {mid}>")
    return out


def fmt_entity_line(e: dict, memories_by_id: dict[str, dict]) -> str:
    links = e["linked_memory_ids"]
    texts = memory_texts_for(links, memories_by_id)
    texts_str = "; ".join(f"\"{t}\"" for t in texts) if texts else "(no links)"
    return f"- \"{e['data']}\" ({e['entity_type']}, {len(links)} link(s)): {texts_str}"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <run_folder>")
    run_dir = Path(sys.argv[1])
    snap_dir = run_dir / "store_snapshot"

    memories = load_jsonl(snap_dir / "memories.jsonl")
    entities = load_jsonl(snap_dir / "entities.jsonl")
    memories_by_id = {m["id"]: m for m in memories}
    memory_ids = set(memories_by_id)

    n_memories = len(memories)
    n_entities = len(entities)

    by_type = Counter(e["entity_type"] for e in entities)

    link_counts = [len(e["linked_memory_ids"]) for e in entities]
    link_min = min(link_counts) if link_counts else 0
    link_max = max(link_counts) if link_counts else 0
    link_mean = statistics.mean(link_counts) if link_counts else 0.0
    link_median = statistics.median(link_counts) if link_counts else 0.0
    bucket_counts = {
        label: sum(1 for n in link_counts if test(n)) for label, test in LINK_BUCKETS
    }

    top20 = sorted(entities, key=lambda e: (-len(e["linked_memory_ids"]), e["data"] or ""))[:20]

    memory_entity_count = Counter()
    dangling_links = 0
    dangling_entities = 0
    for e in entities:
        has_dangling = False
        for mid in e["linked_memory_ids"]:
            if mid in memory_ids:
                memory_entity_count[mid] += 1
            else:
                dangling_links += 1
                has_dangling = True
        if has_dangling:
            dangling_entities += 1

    memories_with_entity = sum(1 for m in memories if memory_entity_count.get(m["id"], 0) > 0)
    memories_without_entity = n_memories - memories_with_entity
    mean_entities_per_memory = (
        sum(memory_entity_count.values()) / n_memories if n_memories else 0.0
    )

    text_groups = defaultdict(list)
    for m in memories:
        text_groups[m["data"]].append(m)
    dup_groups = {t: ms for t, ms in text_groups.items() if len(ms) > 1}
    dup_extra_records = sum(len(ms) - 1 for ms in dup_groups.values())

    # Candidates
    cand_proper = sorted(
        (e for e in entities if e["entity_type"] == "PROPER"),
        key=lambda e: (-len(e["linked_memory_ids"]), e["data"] or ""),
    )[:20]

    norm_groups = defaultdict(list)
    for e in entities:
        norm_groups[normalize_for_near_dup(e["data"] or "")].append(e)
    near_dup_groups = {
        k: v for k, v in norm_groups.items() if len({e["data"] for e in v}) > 1
    }

    cand_short = [e for e in entities if is_short_or_generic(e["data"] or "")]
    cand_long = [e for e in entities if len((e["data"] or "").split()) > 5]
    single_link_sorted = [e for e in entities if len(e["linked_memory_ids"]) == 1]
    cand_single_link_15 = single_link_sorted[:15]  # entities.jsonl is already sorted by data

    lines = []
    lines.append(f"# Storage profile: {run_dir.name}")
    lines.append("")
    lines.append("Source: store_snapshot/memories.jsonl and store_snapshot/entities.jsonl.")
    lines.append("")

    lines.append("## Counts")
    lines.append(f"- Memories: {n_memories}")
    lines.append(f"- Entities: {n_entities}")
    lines.append("- Entities by type:")
    for t in sorted(by_type):
        lines.append(f"  - {t}: {by_type[t]}")
    lines.append("")

    lines.append("## Links per entity")
    lines.append(f"- min: {link_min}")
    lines.append(f"- median: {link_median}")
    lines.append(f"- mean: {link_mean:.2f}")
    lines.append(f"- max: {link_max}")
    lines.append("- buckets:")
    for label, _ in LINK_BUCKETS:
        lines.append(f"  - {label}: {bucket_counts[label]}")
    lines.append("")

    lines.append("## Top 20 entities by number of links")
    for e in top20:
        lines.append(f"- \"{e['data']}\" ({e['entity_type']}): {len(e['linked_memory_ids'])} links")
    lines.append("")

    lines.append("## Memory <-> entity linkage")
    lines.append(f"- Memories linked to at least one entity: {memories_with_entity}")
    lines.append(f"- Memories linked to no entity: {memories_without_entity}")
    lines.append(f"- Mean entities per memory (all memories): {mean_entities_per_memory:.2f}")
    lines.append("")

    lines.append("## Exact duplicate memory texts")
    lines.append(f"- Distinct texts with duplicates: {len(dup_groups)}")
    lines.append(f"- Extra duplicate records (count - 1 per group, summed): {dup_extra_records}")
    if dup_groups:
        lines.append("- Up to 10 examples:")
        for text, ms in list(dup_groups.items())[:10]:
            ids = ", ".join(m["id"] for m in ms)
            lines.append(f"  - ({len(ms)}x) \"{text}\" [ids: {ids}]")
    lines.append("")

    lines.append("## Dangling links")
    lines.append(f"- Link entries pointing to a memory id missing from the snapshot: {dangling_links}")
    lines.append(f"- Entities with at least one dangling link: {dangling_entities}")
    lines.append("")

    lines.append("## Candidates (for the analyst to review; no verdicts)")
    lines.append("")
    lines.append("### a) Most-linked PROPER entities (candidates)")
    for e in cand_proper:
        lines.append(fmt_entity_line(e, memories_by_id))
    lines.append("")

    lines.append("### b) Possible near-duplicate entities (candidates)")
    lines.append("Grouped by text lowercased, punctuation removed, possessive 's and trailing plural s stripped.")
    for norm, group in sorted(near_dup_groups.items()):
        lines.append(f"- group \"{norm}\":")
        for e in sorted(group, key=lambda e: e["data"] or ""):
            lines.append(f"  {fmt_entity_line(e, memories_by_id)}")
    lines.append("")

    lines.append("### c) Very short or generic entities (candidates)")
    lines.append("<=2 characters, purely numeric, pronouns, or time words (yesterday/today/week/year/etc).")
    for e in cand_short:
        lines.append(fmt_entity_line(e, memories_by_id))
    lines.append("")

    lines.append("### d) Long entities, more than 5 words (candidates)")
    for e in cand_long:
        lines.append(fmt_entity_line(e, memories_by_id))
    lines.append("")

    lines.append("### e) 15 single-link entities (fixed sample, first 15 sorted by text)")
    for e in cand_single_link_15:
        lines.append(fmt_entity_line(e, memories_by_id))
    lines.append("")

    (run_dir / "storage_profile.md").write_text("\n".join(lines) + "\n")
    print(f"wrote: {run_dir / 'storage_profile.md'}")


if __name__ == "__main__":
    main()
