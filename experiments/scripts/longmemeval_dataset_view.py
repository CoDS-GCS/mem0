#!/usr/bin/env python3
"""
longmemeval_dataset_view.py — static-HTML viewer for the LongMemEval dataset.

Read-only sibling of trace_view.py. It reads the pinned LongMemEval JSON
(longmemeval_s_cleaned.json) and writes self-contained HTML pages so you can SEE the
benchmark BEFORE running Mem0 on it: each question, its haystack sessions in
chronological order, and — crucially — the exact (user, assistant) turn-pairs that the
runner turns into one mem0.add() call.

It does NOT run the benchmark, start the Mem0 server, or import run.py. It only reads
the dataset JSON on disk.

The "add unit" shown here matches the runner exactly:
  - benchmarks/longmemeval/run.py:412  pairs = pair_turns(session)
  - benchmarks/longmemeval/run.py:314  pair_turns() chunks turns in groups of 2
  - benchmarks/longmemeval/run.py:422  for pair_idx, messages in enumerate(pairs)
  - benchmarks/longmemeval/run.py:451  await mem0.add(messages, user_id, timestamp=...)
  - benchmarks/longmemeval/run.py:439  pairs with empty/whitespace content are SKIPPED
So mem0.add() fires once per non-empty turn-pair, NOT once per session; the session
timestamp is shared by every pair in that session.

Usage:
  # default: one question per type, seed 0
  python experiments/scripts/longmemeval_dataset_view.py

  # a specific question
  python experiments/scripts/longmemeval_dataset_view.py --question-id gpt4_c7f8...

  # N questions per type with a given seed
  python experiments/scripts/longmemeval_dataset_view.py --per-type 3 --seed 42

  # every question (500 pages)
  python experiments/scripts/longmemeval_dataset_view.py --all

Then open the printed index.html path in a browser.
The index stats are always computed over the FULL dataset; the per-question pages are
only the sampled subset.
"""

from __future__ import annotations

import argparse
import html
import os
import random
import re
import statistics
import sys
from datetime import datetime, timezone

try:
    import json
except ImportError:  # pragma: no cover
    sys.exit("json module unavailable")

# Resolve repo-relative defaults from this file's location (experiments/scripts/).
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_EXPERIMENTS_DIR = os.path.dirname(_SCRIPTS_DIR)
DEFAULT_DATASET = os.path.join(_EXPERIMENTS_DIR, "data", "longmemeval_s_cleaned.json")
DEFAULT_OUT_DIR = os.path.join(_EXPERIMENTS_DIR, "longmemeval_view")

QUESTION_TYPES = [
    "temporal-reasoning",
    "multi-session",
    "knowledge-update",
    "single-session-user",
    "single-session-assistant",
    "single-session-preference",
]


# ---------------------------------------------------------------------------
# Dataset logic — mirrors run.py exactly (no import of run.py)
# ---------------------------------------------------------------------------


def parse_longmemeval_date(date_str: str) -> int | None:
    """'2023/05/01 (Mon) 21:05' -> unix epoch int (UTC). Mirror of run.py."""
    try:
        cleaned = re.sub(r"\s*\([A-Za-z]+\)\s*", " ", date_str).strip()
        dt = datetime.strptime(cleaned, "%Y/%m/%d %H:%M").replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except (ValueError, TypeError):
        return None


def sort_sessions_chronologically(question: dict) -> list[tuple[str, str, list[dict]]]:
    """Return (session_id, date_str, session_turns) sorted by date. Mirror of run.py."""
    sessions = question.get("haystack_sessions", [])
    dates = question.get("haystack_dates", [])
    session_ids = question.get("haystack_session_ids", [])
    paired = list(zip(session_ids, dates, sessions))

    def sort_key(item: tuple) -> tuple:
        parsed = parse_longmemeval_date(item[1])
        if parsed is not None:
            return (0, parsed, item[1])
        return (1, 0, item[1])

    paired.sort(key=sort_key)
    return paired


def pair_turns(session: list[dict]) -> list[list[dict]]:
    """Pair consecutive turns in groups of 2. Mirror of run.py:314-324."""
    cleaned = [{"role": t.get("role", ""), "content": t.get("content", ""),
                "has_answer": t.get("has_answer", False)} for t in session]
    return [cleaned[i:i + 2] for i in range(0, len(cleaned), 2)]


def pair_is_skipped(pair: list[dict]) -> bool:
    """A pair is NOT added if any message has empty/whitespace content (run.py:439)."""
    return any(not msg.get("content", "").strip() for msg in pair)


def add_unit_count(question: dict) -> int:
    """Number of mem0.add() calls the runner would make for this question."""
    n = 0
    for _sid, _date, session in sort_sessions_chronologically(question):
        if not session:
            continue
        for pair in pair_turns(session):
            if not pair_is_skipped(pair):
                n += 1
    return n


def evidence_session_ids(question: dict) -> set[str]:
    return set(question.get("answer_session_ids", []) or [])


def is_evidence(session_id: str, answer_ids: set[str]) -> bool:
    """Match the runner's evidence check: direct membership or stripped 'answer_'."""
    if session_id in answer_ids:
        return True
    return any(aid.replace("answer_", "") in session_id for aid in answer_ids)


def is_abstention(question_id: str) -> bool:
    return question_id.endswith("_abs")


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


def sample_questions(questions: list[dict], per_type: int, seed: int) -> list[dict]:
    """Stratified by question_type — same shape as run.py:sample_questions_stratified."""
    groups: dict[str, list[dict]] = {}
    for q in questions:
        groups.setdefault(q.get("question_type", "unknown"), []).append(q)
    for qtype in groups:
        groups[qtype].sort(key=lambda q: q.get("question_id", ""))
    rng = random.Random(seed)
    sampled: list[dict] = []
    for qtype in sorted(groups.keys()):
        group = groups[qtype]
        n = min(per_type, len(group))
        sampled.extend(rng.sample(group, n))
    sampled.sort(key=lambda q: q.get("question_id", ""))
    return sampled


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font: 15px/1.5 -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
       margin: 0; padding: 0 0 4rem; background: #f6f7f9; color: #1a1d21; }
.wrap { max-width: 980px; margin: 0 auto; padding: 1.5rem; }
a { color: #2155cd; }
h1 { font-size: 1.4rem; margin: 0 0 .25rem; }
h2 { font-size: 1.05rem; margin: 2rem 0 .5rem; }
.muted { color: #6b7280; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.badge { display: inline-block; font-size: .72rem; font-weight: 700; letter-spacing: .03em;
         padding: .1rem .45rem; border-radius: .35rem; vertical-align: middle; margin-left: .4rem; }
.badge.abs { background: #ffe0e0; color: #a31212; }
.badge.evidence { background: #fde68a; color: #7a4e00; }
.badge.type { background: #e0e7ff; color: #3730a3; }
.badge.needle { background: #fde68a; color: #7a4e00; margin-left: 0; margin-right: .4rem; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: .6rem;
        padding: 1rem 1.2rem; margin: 1rem 0; box-shadow: 0 1px 2px rgba(0,0,0,.03); }
.qbox { background: #fff; border: 1px solid #e5e7eb; border-radius: .6rem; padding: 1.2rem; }
.kv { margin: .15rem 0; }
.kv b { display: inline-block; min-width: 130px; color: #6b7280; font-weight: 600; }
.answer { background: #ecfdf5; border-left: 4px solid #10b981; padding: .6rem .8rem;
          border-radius: .3rem; margin-top: .6rem; }
.caption { background: #fff7ed; border: 1px solid #fed7aa; color: #7c2d12;
           border-radius: .5rem; padding: .6rem .8rem; font-size: .85rem; margin: 1rem 0; }
.session { border: 1px solid #e5e7eb; border-radius: .6rem; margin: 1rem 0; overflow: hidden;
           background: #fff; }
.session.evidence { border-color: #f59e0b; box-shadow: 0 0 0 2px #fde68a inset; }
.session > .shead { padding: .6rem .9rem; background: #f3f4f6; border-bottom: 1px solid #e5e7eb;
                    display: flex; flex-wrap: wrap; gap: .5rem; align-items: baseline; }
.session.evidence > .shead { background: #fffbeb; }
.shead .sid { font-weight: 700; }
.unit { border: 1px dashed #c7cdd6; border-radius: .5rem; margin: .7rem .9rem; padding: .3rem .6rem .6rem; }
.unit.skipped { opacity: .55; border-style: dotted; }
.unit-head { font-size: .78rem; color: #6b7280; margin: .2rem 0 .4rem; }
.unit-head .addno { font-weight: 700; color: #2155cd; }
.turn { padding: .4rem .6rem; border-radius: .4rem; margin: .3rem 0; white-space: pre-wrap;
        word-wrap: break-word; }
.turn.user { background: #eff6ff; border-left: 3px solid #3b82f6; }
.turn.assistant { background: #f5f3ff; border-left: 3px solid #8b5cf6; }
.turn .role { font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
              color: #6b7280; display: block; margin-bottom: .2rem; }
table { border-collapse: collapse; width: 100%; background: #fff; border: 1px solid #e5e7eb;
        border-radius: .6rem; overflow: hidden; }
th, td { text-align: left; padding: .5rem .7rem; border-bottom: 1px solid #eef0f3; }
th { background: #f3f4f6; font-size: .8rem; color: #374151; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
tr:last-child td { border-bottom: none; }
.statline { font-size: 1.05rem; margin: .5rem 0 1.5rem; }
.statline b { font-size: 1.3rem; }
"""


def esc(s: object) -> str:
    return html.escape(str(s if s is not None else ""))


def render_turn(turn: dict) -> str:
    role = turn.get("role", "")
    cls = "user" if role == "user" else "assistant"
    needle = '<span class="badge needle">needle</span>' if turn.get("has_answer") else ""
    content = esc(turn.get("content", ""))
    return (f'<div class="turn {cls}"><span class="role">{needle}{esc(role)}</span>{content}</div>')


def render_question_page(question: dict) -> str:
    qid = question.get("question_id", "")
    qtype = question.get("question_type", "unknown")
    qdate = question.get("question_date", "")
    answer_ids = evidence_session_ids(question)
    sorted_sessions = sort_sessions_chronologically(question)
    n_sessions = len(sorted_sessions)
    n_evidence = sum(1 for sid, _d, _s in sorted_sessions if is_evidence(sid, answer_ids))
    n_adds = add_unit_count(question)

    abs_badge = '<span class="badge abs">ABSTENTION</span>' if is_abstention(qid) else ""

    parts: list[str] = []
    parts.append(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(qid)} — LongMemEval</title><style>{CSS}</style></head><body><div class="wrap">
<p class="muted"><a href="index.html">&larr; index</a></p>
<div class="qbox">
<h1><span class="mono">{esc(qid)}</span>{abs_badge}<span class="badge type">{esc(qtype)}</span></h1>
<div class="kv"><b>question_date</b> <span class="mono">{esc(qdate)}</span></div>
<div class="kv"><b>question</b> {esc(question.get("question", ""))}</div>
<div class="answer"><b>gold answer:</b> {esc(question.get("answer", ""))}</div>
<p class="muted" style="margin-top:.8rem">
  {n_sessions} haystack sessions &nbsp;·&nbsp; {n_evidence} evidence session(s) &nbsp;·&nbsp;
  <b>{n_adds} add-units</b> (= mem0.add() calls the runner would make)</p>
</div>

<div class="caption">
Each dashed box below is one <b>mem0.add()</b> call: a (user, assistant) turn-pair with the
session timestamp shown. That timestamp only reaches Mem0 when the server runs with
<span class="mono">MEM0_FORWARD_TIMESTAMP=1</span> and a session-date mem0 build; plain
v2.2.1 drops it. Pairs with empty content are skipped (not added), matching run.py.
</div>

<h2>Haystack — {n_sessions} sessions, chronological order</h2>
""")

    for idx, (sid, date_str, session) in enumerate(sorted_sessions):
        ev = is_evidence(sid, answer_ids)
        ev_badge = '<span class="badge evidence">EVIDENCE</span>' if ev else ""
        epoch = parse_longmemeval_date(date_str)
        epoch_txt = str(epoch) if epoch is not None else "unparseable"
        parts.append(f'<div class="session{" evidence" if ev else ""}">')
        parts.append(
            f'<div class="shead"><span class="sid mono">#{idx} · {esc(sid)}</span>'
            f'<span class="muted">{esc(date_str)}</span>'
            f'<span class="muted mono">(ts={esc(epoch_txt)})</span>{ev_badge}</div>'
        )
        if not session:
            parts.append('<p class="muted" style="padding:.6rem .9rem">(empty session)</p>')
        else:
            add_no = 0
            for pair in pair_turns(session):
                skipped = pair_is_skipped(pair)
                if skipped:
                    head = '<span class="muted">skipped — empty content, not added</span>'
                    unit_cls = "unit skipped"
                else:
                    add_no += 1
                    head = (f'<span class="addno">add #{add_no}</span> · '
                            f'timestamp=<span class="mono">{esc(epoch_txt)}</span> '
                            f'<span class="muted">({esc(date_str)})</span>')
                    unit_cls = "unit"
                turns_html = "".join(render_turn(t) for t in pair)
                parts.append(f'<div class="{unit_cls}"><div class="unit-head">{head}</div>{turns_html}</div>')
        parts.append("</div>")

    parts.append("</div></body></html>")
    return "".join(parts)


def render_index(questions: list[dict], sampled: list[dict]) -> str:
    """Index stats over the FULL dataset; links to the sampled pages."""
    total = len(questions)

    # Per-type aggregates over the full dataset.
    per_type: dict[str, dict] = {}
    all_adds: list[int] = []
    for q in questions:
        qtype = q.get("question_type", "unknown")
        n_sessions = len(q.get("haystack_sessions", []))
        n_adds = add_unit_count(q)
        all_adds.append(n_adds)
        bucket = per_type.setdefault(qtype, {"sessions": [], "adds": [], "count": 0})
        bucket["count"] += 1
        bucket["sessions"].append(n_sessions)
        bucket["adds"].append(n_adds)

    n_abs = sum(1 for q in questions if is_abstention(q.get("question_id", "")))
    overall_mean_adds = statistics.mean(all_adds) if all_adds else 0
    total_adds = sum(all_adds)

    rows = []
    for qtype in sorted(per_type.keys()):
        b = per_type[qtype]
        rows.append(
            "<tr>"
            f"<td>{esc(qtype)}</td>"
            f'<td class="num">{b["count"]}</td>'
            f'<td class="num">{statistics.mean(b["sessions"]):.1f}</td>'
            f'<td class="num">{statistics.median(b["sessions"]):.0f}</td>'
            f'<td class="num">{statistics.mean(b["adds"]):.1f}</td>'
            f'<td class="num">{sum(b["adds"])}</td>'
            "</tr>"
        )

    link_rows = []
    for q in sampled:
        qid = q.get("question_id", "")
        abs_mark = ' <span class="badge abs">ABS</span>' if is_abstention(qid) else ""
        link_rows.append(
            "<tr>"
            f'<td><a href="{esc(qid)}.html" class="mono">{esc(qid)}</a>{abs_mark}</td>'
            f'<td>{esc(q.get("question_type", ""))}</td>'
            f'<td class="num">{len(q.get("haystack_sessions", []))}</td>'
            f'<td class="num">{add_unit_count(q)}</td>'
            "</tr>"
        )

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LongMemEval dataset</title><style>{CSS}</style></head><body><div class="wrap">
<h1>LongMemEval dataset <span class="muted" style="font-size:1rem">(longmemeval_s_cleaned)</span></h1>
<p class="statline">
  <b>{total}</b> questions &nbsp;·&nbsp; <b>{n_abs}</b> abstention &nbsp;·&nbsp;
  overall mean <b>{overall_mean_adds:.1f}</b> add-units/question &nbsp;·&nbsp;
  <b>{total_adds:,}</b> total add-units if the whole set is ingested
</p>

<h2>Per question type (full dataset)</h2>
<table>
<thead><tr><th>question_type</th><th>count</th><th>mean sessions</th><th>median sessions</th>
<th>mean add-units</th><th>total add-units</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<p class="muted">add-units = mem0.add() calls (one per non-empty user/assistant turn-pair).</p>

<h2>Pages generated this run ({len(sampled)})</h2>
<table>
<thead><tr><th>question_id</th><th>type</th><th>sessions</th><th>add-units</th></tr></thead>
<tbody>{''.join(link_rows)}</tbody>
</table>
</div></body></html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Static-HTML viewer for the LongMemEval dataset (read-only).")
    p.add_argument("--dataset-path", default=DEFAULT_DATASET, help="Path to longmemeval_s_cleaned.json")
    sel = p.add_mutually_exclusive_group()
    sel.add_argument("--question-id", help="Render a single question by id")
    sel.add_argument("--all", action="store_true", help="Render every question")
    p.add_argument("--per-type", type=int, default=1, help="Questions per type (default 1)")
    p.add_argument("--seed", type=int, default=0, help="Sampling seed (default 0)")
    p.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Output directory")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if not os.path.exists(args.dataset_path):
        sys.exit(
            f"Dataset not found: {args.dataset_path}\n"
            "Fetch it first (see experiments/data/README)."
        )

    with open(args.dataset_path, "r", encoding="utf-8") as fh:
        questions = json.load(fh)
    if not isinstance(questions, list):
        sys.exit("Unexpected dataset format: expected a list of questions.")

    # Choose the subset of pages to render.
    if args.question_id:
        sampled = [q for q in questions if q.get("question_id") == args.question_id]
        if not sampled:
            sys.exit(f"question_id not found: {args.question_id}")
    elif args.all:
        sampled = list(questions)
    else:
        sampled = sample_questions(questions, args.per_type, args.seed)

    os.makedirs(args.out_dir, exist_ok=True)

    for q in sampled:
        qid = q.get("question_id", "unknown")
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", qid)
        path = os.path.join(args.out_dir, f"{safe}.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render_question_page(q))

    index_path = os.path.join(args.out_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write(render_index(questions, sampled))

    print(f"Rendered {len(sampled)} question page(s) + index.")
    print(f"Index : {index_path}")
    if sampled:
        first = re.sub(r"[^A-Za-z0-9_.-]", "_", sampled[0].get("question_id", "unknown"))
        print(f"Sample: {os.path.join(args.out_dir, first + '.html')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
