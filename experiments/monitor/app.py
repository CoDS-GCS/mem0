#!/usr/bin/env python3
"""
app.py — FastAPI monitor for the LongMemEval dataset (read-only explorer).

Serves a JSON API over longmemeval.sqlite (built by build_index.py) plus one static
vanilla-JS page (static/index.html). No npm, no build step, no CDN. Binds 127.0.0.1:8020.

It never runs the benchmark or talks to the Mem0 server — it only reads the SQLite index.

The data layer is deliberately shaped so a "run overlay" can be bolted on later without
touching these endpoints: a future /api/run/... can return, per question, the predicted
answer / judge verdict / retrieved memories (with semantic+BM25+entity scores) / live
progress, and the page can merge it onto the same question + session objects.

Run:
  uvicorn app:app --host 127.0.0.1 --port 8020        # from experiments/monitor/
  # or just: ./run_monitor.sh
"""

from __future__ import annotations

import os
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("LME_DB", os.path.join(_HERE, "longmemeval.sqlite"))
STATIC_DIR = os.path.join(_HERE, "static")

app = FastAPI(title="LongMemEval monitor", docs_url=None, redoc_url=None)


def db() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise HTTPException(503, f"Index not built: {DB_PATH}. Run build_index.py first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@app.get("/api/overview")
def overview() -> JSONResponse:
    conn = db()
    types = rows(conn.execute("""
        SELECT question_type AS type,
               COUNT(*)                       AS count,
               SUM(is_abstention)             AS abstention,
               AVG(n_sessions)                AS mean_sessions,
               AVG(n_evidence)                AS mean_evidence,
               AVG(n_add_units)               AS mean_add_units,
               SUM(n_add_units)               AS total_add_units
        FROM questions GROUP BY question_type ORDER BY question_type
    """))
    totals = dict(conn.execute("""
        SELECT COUNT(*) AS questions,
               SUM(is_abstention) AS abstention,
               SUM(n_add_units)   AS total_add_units,
               AVG(n_add_units)   AS mean_add_units,
               AVG(n_sessions)    AS mean_sessions
        FROM questions
    """).fetchone())
    overlap = dict(conn.execute("""
        SELECT COUNT(*)            AS unique_sessions,
               SUM(n_haystacks)    AS total_links,
               SUM(n_haystacks > 1) AS reused_sessions,
               MAX(n_haystacks)    AS max_reuse,
               AVG(n_haystacks)    AS mean_haystacks_per_session
        FROM sessions
    """).fetchone())
    meta = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM meta")}
    conn.close()
    return JSONResponse({"types": types, "totals": totals, "overlap": overlap, "meta": meta})


@app.get("/api/type/{qtype}")
def by_type(qtype: str) -> JSONResponse:
    conn = db()
    qs = rows(conn.execute("""
        SELECT question_id, question, answer, question_date, question_type,
               is_abstention, n_sessions, n_evidence, n_add_units
        FROM questions WHERE question_type = ? ORDER BY question_id
    """, (qtype,)))
    conn.close()
    if not qs:
        raise HTTPException(404, f"No questions for type {qtype!r}")
    return JSONResponse({"type": qtype, "questions": qs})


@app.get("/api/question/{qid}")
def question(qid: str) -> JSONResponse:
    conn = db()
    q = conn.execute("""
        SELECT question_id, question_type, question, answer, question_date,
               question_epoch, is_abstention, n_sessions, n_evidence, n_add_units
        FROM questions WHERE question_id = ?
    """, (qid,)).fetchone()
    if not q:
        conn.close()
        raise HTTPException(404, f"Unknown question {qid!r}")
    q = dict(q)
    sessions = rows(conn.execute("""
        SELECT l.session_id, l.position, l.date, l.epoch, l.is_evidence,
               s.n_turns, s.n_add_units, s.n_haystacks
        FROM links l JOIN sessions s ON s.session_id = l.session_id
        WHERE l.question_id = ? ORDER BY l.position
    """, (qid,)))
    qepoch = q["question_epoch"]
    for s in sessions:
        s["days_before"] = (
            round((qepoch - s["epoch"]) / 86400) if (qepoch and s["epoch"]) else None
        )
    conn.close()
    return JSONResponse({"question": q, "sessions": sessions})


@app.get("/api/session/{sid}/turns")
def session_turns(sid: str, question_id: str | None = Query(None)) -> JSONResponse:
    """Turns of a session, grouped into add-units.

    If question_id is given, the per-link date is attached as the timestamp each add-unit
    would carry for THAT haystack (the same session has different dates in different
    haystacks).
    """
    conn = db()
    meta = conn.execute(
        "SELECT session_id, n_turns, n_add_units, n_haystacks FROM sessions WHERE session_id = ?",
        (sid,),
    ).fetchone()
    if not meta:
        conn.close()
        raise HTTPException(404, f"Unknown session {sid!r}")
    link = None
    if question_id:
        link = conn.execute(
            "SELECT date, epoch, is_evidence, position FROM links WHERE question_id = ? AND session_id = ?",
            (question_id, sid),
        ).fetchone()
    turns = rows(conn.execute("""
        SELECT turn_idx, role, content, has_answer, pair_idx, add_no
        FROM turns WHERE session_id = ? ORDER BY turn_idx
    """, (sid,)))
    conn.close()

    # Group into add-units by pair_idx.
    units: dict[int, dict] = {}
    for t in turns:
        u = units.setdefault(t["pair_idx"], {
            "pair_idx": t["pair_idx"], "add_no": t["add_no"],
            "skipped": t["add_no"] is None, "turns": [],
        })
        u["turns"].append(t)
    unit_list = [units[k] for k in sorted(units)]

    out = {
        "session": dict(meta),
        "units": unit_list,
        "timestamp": None,
        "date": None,
        "is_evidence": None,
    }
    if link:
        out["date"] = link["date"]
        out["timestamp"] = link["epoch"]
        out["is_evidence"] = link["is_evidence"]
    return JSONResponse(out)


@app.get("/api/session/{sid}")
def session_detail(sid: str) -> JSONResponse:
    """A session plus every question whose haystack uses it (with that haystack's date)."""
    conn = db()
    meta = conn.execute(
        "SELECT session_id, n_turns, n_add_units, n_haystacks FROM sessions WHERE session_id = ?",
        (sid,),
    ).fetchone()
    if not meta:
        conn.close()
        raise HTTPException(404, f"Unknown session {sid!r}")
    used_by = rows(conn.execute("""
        SELECT l.question_id, l.date, l.epoch, l.is_evidence, l.position,
               q.question_type, q.question
        FROM links l JOIN questions q ON q.question_id = l.question_id
        WHERE l.session_id = ? ORDER BY l.epoch
    """, (sid,)))
    conn.close()
    return JSONResponse({"session": dict(meta), "used_by": used_by})


# ---------------------------------------------------------------------------
# Static page
# ---------------------------------------------------------------------------


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
