#!/usr/bin/env python3
"""
build_index.py — one-time indexer: pinned LongMemEval JSON -> SQLite.

Read-only over the dataset. Builds experiments/monitor/longmemeval.sqlite (gitignored)
so the web monitor can serve the 277 MB dataset quickly without re-parsing JSON.

Schema (the key modelling decision):
  - A session_id's TURNS are invariant across every haystack it appears in (verified at
    build time; 0 conflicts in longmemeval_s). So sessions are de-duped by session_id and
    their turns stored once.
  - A session's DATE and EVIDENCE status are NOT invariant: the same session sits in many
    questions' haystacks with different dates and is evidence only for the question whose
    answer_session_ids lists it. So date / is_evidence / chronological position live on the
    question<->session LINK, not on the session.

  questions(question_id PK, question_type, question, answer, question_date, question_epoch,
            is_abstention, n_sessions, n_evidence, n_add_units)
  sessions(session_id PK, n_turns, n_add_units, content_hash, n_haystacks)
  turns(session_id, turn_idx, role, content, has_answer, pair_idx, add_no)
        add_no = 1-based add-unit within the session, or NULL if the pair is skipped
  links(question_id, session_id, position, date, epoch, is_evidence)
        position = chronological index of the session within that question's haystack

"add-unit" = one mem0.add() call = one non-empty (user, assistant) turn-pair, matching
benchmarks/longmemeval/run.py:314-324 (pair_turns) and run.py:439 (empty pairs skipped).

Usage:
  python experiments/monitor/build_index.py            # uses pinned dataset + default db
  python experiments/monitor/build_index.py --force    # rebuild even if db exists
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXPERIMENTS = os.path.dirname(_HERE)
DEFAULT_DATASET = os.path.join(_EXPERIMENTS, "data", "longmemeval_s_cleaned.json")
DEFAULT_DB = os.path.join(_HERE, "longmemeval.sqlite")


def parse_epoch(date_str: str) -> int | None:
    """'2023/05/01 (Mon) 21:05' -> unix epoch int (UTC). Mirror of run.py."""
    try:
        cleaned = re.sub(r"\s*\([A-Za-z]+\)\s*", " ", date_str).strip()
        dt = datetime.strptime(cleaned, "%Y/%m/%d %H:%M").replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except (ValueError, TypeError):
        return None


def turns_hash(turns: list[dict]) -> str:
    payload = [[t.get("role"), t.get("content")] for t in turns]
    return hashlib.sha1(json.dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()


def pair_rows(turns: list[dict]) -> list[dict]:
    """Group turns into add-units exactly as run.py pair_turns does (chunks of 2).

    Returns one row per turn with: turn_idx, role, content, has_answer, pair_idx, add_no
    (add_no is NULL/None when the pair is skipped because a message is empty).
    """
    rows: list[dict] = []
    add_no = 0
    for pair_idx, i in enumerate(range(0, len(turns), 2)):
        pair = turns[i:i + 2]
        skipped = any(not (t.get("content") or "").strip() for t in pair)
        if not skipped:
            add_no += 1
        this_add = None if skipped else add_no
        for off, t in enumerate(pair):
            rows.append({
                "turn_idx": i + off,
                "role": t.get("role", ""),
                "content": t.get("content", ""),
                "has_answer": 1 if t.get("has_answer") else 0,
                "pair_idx": pair_idx,
                "add_no": this_add,
            })
    return rows


SCHEMA = """
PRAGMA journal_mode = WAL;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS turns;
DROP TABLE IF EXISTS links;
DROP TABLE IF EXISTS meta;

CREATE TABLE questions (
    question_id   TEXT PRIMARY KEY,
    question_type TEXT,
    question      TEXT,
    answer        TEXT,
    question_date TEXT,
    question_epoch INTEGER,
    is_abstention INTEGER,
    n_sessions    INTEGER,
    n_evidence    INTEGER,
    n_add_units   INTEGER
);
CREATE TABLE sessions (
    session_id   TEXT PRIMARY KEY,
    n_turns      INTEGER,
    n_add_units  INTEGER,
    content_hash TEXT,
    n_haystacks  INTEGER
);
CREATE TABLE turns (
    session_id TEXT,
    turn_idx   INTEGER,
    role       TEXT,
    content    TEXT,
    has_answer INTEGER,
    pair_idx   INTEGER,
    add_no     INTEGER
);
CREATE TABLE links (
    question_id TEXT,
    session_id  TEXT,
    position    INTEGER,
    date        TEXT,
    epoch       INTEGER,
    is_evidence INTEGER
);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);

CREATE INDEX idx_q_type ON questions(question_type);
CREATE INDEX idx_turns_session ON turns(session_id);
CREATE INDEX idx_links_question ON links(question_id);
CREATE INDEX idx_links_session ON links(session_id);
"""


def build(dataset_path: str, db_path: str) -> dict:
    with open(dataset_path, "r", encoding="utf-8") as fh:
        questions = json.load(fh)
    if not isinstance(questions, list):
        sys.exit("Unexpected dataset format: expected a list of questions.")

    # First pass: collect unique sessions, verify the turns-invariant, count reuse.
    session_turns: dict[str, list[dict]] = {}
    session_hashes: dict[str, set[str]] = {}
    session_haystacks: dict[str, int] = {}
    conflicts: list[str] = []

    for q in questions:
        sids = q.get("haystack_session_ids", [])
        sessions = q.get("haystack_sessions", [])
        for sid, turns in zip(sids, sessions):
            h = turns_hash(turns)
            session_hashes.setdefault(sid, set()).add(h)
            session_haystacks[sid] = session_haystacks.get(sid, 0) + 1
            if sid not in session_turns:
                session_turns[sid] = turns
    for sid, hs in session_hashes.items():
        if len(hs) > 1:
            conflicts.append(sid)

    if conflicts:
        # Invariant broken — fall back to content-hash keying rather than silently drop data.
        sys.exit(
            f"session_id turns-invariant BROKEN for {len(conflicts)} ids (e.g. {conflicts[:3]}).\n"
            "Re-key sessions by content hash before deduping."
        )

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    cur = conn.cursor()

    # Sessions + turns (once per unique session).
    session_add_units: dict[str, int] = {}
    session_n_turns: dict[str, int] = {}
    turn_batch: list[tuple] = []
    sess_batch: list[tuple] = []
    for sid, turns in session_turns.items():
        rows = pair_rows(turns)
        n_add = max([r["add_no"] for r in rows if r["add_no"] is not None], default=0)
        session_add_units[sid] = n_add
        session_n_turns[sid] = len(turns)
        sess_batch.append((sid, len(turns), n_add,
                           next(iter(session_hashes[sid])), session_haystacks[sid]))
        for r in rows:
            turn_batch.append((sid, r["turn_idx"], r["role"], r["content"],
                               r["has_answer"], r["pair_idx"], r["add_no"]))
    cur.executemany("INSERT INTO sessions VALUES (?,?,?,?,?)", sess_batch)
    cur.executemany("INSERT INTO turns VALUES (?,?,?,?,?,?,?)", turn_batch)

    # Questions + links.
    q_batch: list[tuple] = []
    link_batch: list[tuple] = []
    for q in questions:
        qid = q["question_id"]
        qepoch = parse_epoch(q.get("question_date", ""))
        evidence = set(q.get("answer_session_ids", []) or [])

        sids = q.get("haystack_session_ids", [])
        dates = q.get("haystack_dates", [])

        # Chronological order within this haystack (mirror run.py sort_key).
        order = sorted(
            range(len(sids)),
            key=lambda i: (0, parse_epoch(dates[i]), dates[i])
            if parse_epoch(dates[i]) is not None else (1, 0, dates[i]),
        )
        pos_of = {i: pos for pos, i in enumerate(order)}

        n_evidence = 0
        n_add_units = 0
        for i, sid in enumerate(sids):
            is_ev = 1 if (sid in evidence or any(a.replace("answer_", "") in sid for a in evidence)) else 0
            n_evidence += is_ev
            n_add_units += session_add_units.get(sid, 0)
            link_batch.append((qid, sid, pos_of[i], dates[i], parse_epoch(dates[i]), is_ev))

        q_batch.append((
            qid, q.get("question_type", "unknown"), q.get("question", ""),
            str(q.get("answer", "")), q.get("question_date", ""), qepoch,
            1 if qid.endswith("_abs") else 0, len(sids), n_evidence, n_add_units,
        ))
    cur.executemany("INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?,?)", q_batch)
    cur.executemany("INSERT INTO links VALUES (?,?,?,?,?,?)", link_batch)

    stats = {
        "questions": len(questions),
        "unique_sessions": len(session_turns),
        "links": len(link_batch),
        "reused_sessions": sum(1 for c in session_haystacks.values() if c > 1),
        "max_reuse": max(session_haystacks.values()) if session_haystacks else 0,
        "total_add_units": sum(r[9] for r in q_batch),
        "abstention": sum(r[6] for r in q_batch),
        "dataset_path": os.path.abspath(dataset_path),
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    cur.executemany("INSERT INTO meta VALUES (?,?)", [(k, str(v)) for k, v in stats.items()])
    conn.commit()
    conn.close()
    return stats


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Index the LongMemEval dataset into SQLite (read-only over JSON).")
    p.add_argument("--dataset-path", default=DEFAULT_DATASET)
    p.add_argument("--db", default=DEFAULT_DB)
    p.add_argument("--force", action="store_true", help="Rebuild even if the db already exists")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if os.path.exists(args.db) and not args.force:
        print(f"Index already exists: {args.db} (use --force to rebuild)")
        return 0
    if not os.path.exists(args.dataset_path):
        sys.exit(f"Dataset not found: {args.dataset_path}\nFetch it first (see experiments/data/README).")
    if os.path.exists(args.db):
        os.remove(args.db)
    stats = build(args.dataset_path, args.db)
    print(f"Built {args.db}")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
