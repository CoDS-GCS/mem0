"""
trace_index.py — incremental, offset-based index over a run's live JSONL traces.

The problem it solves: ``mem0_trace.jsonl`` grows to many GB during a run. The old
reader re-read the whole file on every board poll and every question view, so the
Runs view stalled once a run got big. This module keeps a tiny per-question index in
``experiments/monitor/cache/<run>/`` that is updated incrementally — each call reads
only the bytes appended since the previous call — and records the byte offset of every
event the UI needs. The live board answers from the aggregates alone; a question panel
seeks straight to that question's events instead of scanning the file.

What is indexed, per question id:
  - aggregates: add.response count, searched flag, answerer/judge counts (board stage);
  - add-units: ordered (request_id, offsets of add.request / llm / add.response);
  - the offsets of its search.request + scoring event, and its eval answerer/judge events.
Plus one global extraction-health counter (llm calls / cut-offs / parse failures).

Everything is read-only. Offsets index the *plain* ``.jsonl`` that exists while a run is
live; once a run finishes and its trace is gzipped the offsets no longer apply, so
``supported()`` returns False and the caller falls back to the legacy full scan.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(_HERE, "cache")

# How often (seconds) to flush the in-memory index to disk. The in-memory copy serves
# all reads; the disk copy only lets a restarted process resume without rescanning from
# zero. Each flush writes a fully consistent snapshot, so throttling is safe — a restart
# just replays the handful of seconds appended since the last flush.
_PERSIST_EVERY = 15.0

_TRACES = (("mem0", "mem0_trace.jsonl"), ("eval", "eval_trace.jsonl"))

# Module-level caches, guarded per run_dir. _IDX holds the persistable index; _RID holds
# the in-memory {qid: {request_id: unit_index}} map used to attach llm/response offsets to
# the add-unit opened by the matching add.request (rebuilt from units on load).
_GLOBAL_LOCK = threading.Lock()
_LOCKS: dict[str, threading.Lock] = {}
_IDX: dict[str, dict] = {}
_RID: dict[str, dict] = {}
_LAST_PERSIST: dict[str, float] = {}


# --------------------------------------------------------------------------- user_id
def split_user_id(uid):
    """longmemeval_<qid>_<run_id> -> qid. run_id is always the final field."""
    if not uid or not uid.startswith("longmemeval_"):
        return None
    rest = uid[len("longmemeval_"):]
    qid, _, _run = rest.rpartition("_")
    return qid or None


# --------------------------------------------------------------------------- paths
def _plain_path(run_dir, base):
    p = os.path.join(run_dir, base)
    return p if os.path.exists(p) else None


def supported(run_dir):
    """True while the mem0 trace is a plain .jsonl we can index by byte offset.

    Once the run ends and the trace is gzipped, offsets are meaningless; the caller
    falls back to the legacy full-scan reader.
    """
    return _plain_path(run_dir, "mem0_trace.jsonl") is not None


def _cache_dir(run_dir):
    return os.path.join(CACHE_DIR, os.path.basename(os.path.normpath(run_dir)))


def _index_file(run_dir):
    return os.path.join(_cache_dir(run_dir), "index.json")


# --------------------------------------------------------------------------- index state
def _fresh():
    return {
        "version": 4,
        "mem0": {"offset": 0, "size": 0, "inode": None},
        "eval": {"offset": 0, "size": 0, "inode": None},
        # Global extraction health + measured token totals + whole-run time span.
        "extraction": {"calls": 0, "cutoffs": 0, "parse_fail": 0, "errors": 0,
                       "tok_in": 0, "tok_out": 0, "tok_total": 0,
                       "add_calls": 0, "add_resp": 0, "add_zero": 0, "mem_stored": 0,
                       "reasoning_recorded": False, "first": None, "last": None},
        # Distinct model names the API/gateway reports (JSON-serializable lists).
        "models_reported": {"extraction": [], "answerer": []},
        "qids": {},
    }


def _qentry(idx, run_dir, qid):
    q = idx["qids"].get(qid)
    if q is None:
        q = {"adds_done": 0, "searched": False, "answered": 0, "judged": 0,
             "units": [], "search_off": None, "scoring_off": None, "eval_offs": [],
             # measured, counted straight from the trace (never projected)
             "add_calls": 0, "add_resp": 0, "add_zero": 0, "mem_stored": 0,
             "tok_in": 0, "tok_out": 0, "tok_total": 0,
             "cutoffs": 0, "parse_fail": 0, "errors": 0,
             "search_ms": 0.0, "first": None, "last": None}
        idx["qids"][qid] = q
        _RID[run_dir][qid] = {}
    return q


def _unit_for(idx, run_dir, qid, rid):
    """Get-or-create the add-unit for (qid, request_id), preserving add.request order."""
    q = _qentry(idx, run_dir, qid)
    ridx = _RID[run_dir][qid]
    i = ridx.get(rid)
    if i is None:
        i = len(q["units"])
        ridx[rid] = i
        q["units"].append({"rid": rid, "req": None, "llm": None, "resp": None})
    return q, q["units"][i]


# --------------------------------------------------------------------------- disk
def _load_from_disk(run_dir):
    try:
        with open(_index_file(run_dir), encoding="utf-8") as fh:
            idx = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(idx, dict) or idx.get("version") != 4:
        return None
    # Rebuild the in-memory request_id -> unit_index map from the persisted units.
    _RID[run_dir] = {qid: {u["rid"]: i for i, u in enumerate(q["units"])}
                     for qid, q in idx.get("qids", {}).items()}
    return idx


def _persist(run_dir, idx):
    d = _cache_dir(run_dir)
    os.makedirs(d, exist_ok=True)
    tmp = _index_file(run_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(idx, fh)
    os.replace(tmp, _index_file(run_dir))
    _LAST_PERSIST[run_dir] = time.time()


# --------------------------------------------------------------------------- tail reader
def _process_new(path, start_off, on_event):
    """Call on_event(offset, obj) for every complete, newline-terminated JSON line from
    start_off onward. A trailing partial line (writer mid-append) is left unconsumed.
    Returns the offset just past the last complete line."""
    committed = start_off
    with open(path, "rb") as f:
        f.seek(start_off)
        while True:
            pos = f.tell()
            raw = f.readline()
            if not raw:
                break
            if not raw.endswith(b"\n"):
                break  # partial line at EOF; wait for the writer to finish it
            committed = pos + len(raw)
            try:
                obj = json.loads(raw)
            except ValueError:
                continue
            on_event(pos, obj)
    return committed


def _apply_mem0(idx, run_dir, pos, obj):
    comp, op = obj.get("component"), obj.get("operation")
    ex = idx["extraction"]
    t = obj.get("time")
    if t:
        if ex["first"] is None:
            ex["first"] = t
        ex["last"] = t
    out = obj.get("outputs") or {}
    cut = pf = er = False
    if comp == "llm" and op == "generate_response":
        tu = out.get("token_usage") or {}
        pi, co, to = tu.get("prompt_tokens") or 0, tu.get("completion_tokens") or 0, tu.get("total_tokens") or 0
        ex["calls"] += 1
        ex["tok_in"] += pi
        ex["tok_out"] += co
        ex["tok_total"] += to
        if any("reason" in k.lower() for k in tu):
            ex["reasoning_recorded"] = True
        cut = out.get("finish_reason") == "length"
        pf = out.get("parse_ok") is False
        er = bool(out.get("error"))
        if cut:
            ex["cutoffs"] += 1
        if pf:
            ex["parse_fail"] += 1
        if er:
            ex["errors"] += 1
        mr = out.get("model_reported")
        if mr:
            lst = idx["models_reported"]["extraction"]
            if mr not in lst:
                lst.append(mr)
    qid = split_user_id(obj.get("user_id") or "")
    if not qid:
        return
    rid = obj.get("request_id")
    q = _qentry(idx, run_dir, qid)
    if t:
        if q["first"] is None:
            q["first"] = t
        q["last"] = t
    if comp == "entry" and op == "add.request":
        ex["add_calls"] += 1
        q["add_calls"] += 1
        _, u = _unit_for(idx, run_dir, qid, rid)
        u["req"] = pos
    elif comp == "llm" and op == "generate_response":
        tu = out.get("token_usage") or {}
        q["tok_in"] += tu.get("prompt_tokens") or 0
        q["tok_out"] += tu.get("completion_tokens") or 0
        q["tok_total"] += tu.get("total_tokens") or 0
        q["cutoffs"] += 1 if cut else 0
        q["parse_fail"] += 1 if pf else 0
        q["errors"] += 1 if er else 0
        _, u = _unit_for(idx, run_dir, qid, rid)
        u["llm"] = pos
    elif comp == "entry" and op == "add.response":
        _, u = _unit_for(idx, run_dir, qid, rid)
        u["resp"] = pos
        q["adds_done"] += 1
        q["add_resp"] += 1
        ex["add_resp"] += 1
        n = len((out.get("results") or []))
        q["mem_stored"] += n
        ex["mem_stored"] += n
        if n == 0:                 # add stored 0 memories (silent empty extraction)
            q["add_zero"] += 1
            ex["add_zero"] += 1
    elif comp == "entry" and op == "search.request":
        q["search_off"] = pos
        q["searched"] = True
    elif comp == "entry" and op == "search.response":
        q["search_ms"] += obj.get("duration_ms") or 0.0
    elif comp == "scoring" and op == "score_and_rank":
        q["scoring_off"] = pos


def _apply_eval(idx, run_dir, pos, obj):
    comp, op = obj.get("component"), obj.get("operation")
    inp = obj.get("inputs") if isinstance(obj.get("inputs"), dict) else {}
    qid = inp.get("question_id") or split_user_id(obj.get("user_id") or "")
    if not qid:
        return
    q = _qentry(idx, run_dir, qid)
    if comp == "answerer":
        q["answered"] += 1
        q["eval_offs"].append(pos)
        mr = (obj.get("outputs") or {}).get("model_reported")
        if mr:
            lst = idx["models_reported"]["answerer"]
            if mr not in lst:
                lst.append(mr)
    elif comp == "judge":
        q["judged"] += 1
        q["eval_offs"].append(pos)
    elif comp == "mem0_client" and op == "search":
        q["searched"] = True


# --------------------------------------------------------------------------- update
def _lock(run_dir):
    with _GLOBAL_LOCK:
        return _LOCKS.setdefault(run_dir, threading.Lock())


def _needs_reset(idx, run_dir):
    """A trace was replaced or truncated (new inode, or shrunk below our offset)."""
    for key, base in _TRACES:
        p = _plain_path(run_dir, base)
        if not p:
            continue
        st = os.stat(p)
        meta = idx[key]
        if meta["inode"] is not None and st.st_ino != meta["inode"]:
            return True
        if st.st_size < meta["offset"]:
            return True
    return False


def update(run_dir):
    """Bring the index up to date by reading only the bytes appended since last time."""
    with _lock(run_dir):
        idx = _IDX.get(run_dir)
        if idx is None:
            idx = _load_from_disk(run_dir)
        if idx is None:
            idx = _fresh()
            _RID.setdefault(run_dir, {})
        _RID.setdefault(run_dir, {})

        if _needs_reset(idx, run_dir):
            idx = _fresh()
            _RID[run_dir] = {}

        changed = False
        appliers = {"mem0": _apply_mem0, "eval": _apply_eval}
        for key, base in _TRACES:
            p = _plain_path(run_dir, base)
            if not p:
                continue
            st = os.stat(p)
            meta = idx[key]
            if st.st_size > meta["offset"]:
                apply = appliers[key]
                new_off = _process_new(
                    p, meta["offset"], lambda pos, obj, a=apply: a(idx, run_dir, pos, obj))
                meta["offset"], meta["size"], meta["inode"] = new_off, st.st_size, st.st_ino
                changed = True
            elif meta["inode"] is None:
                meta["inode"], meta["size"] = st.st_ino, st.st_size

        _IDX[run_dir] = idx
        first = run_dir not in _LAST_PERSIST
        if changed and (first or time.time() - _LAST_PERSIST.get(run_dir, 0) >= _PERSIST_EVERY):
            try:
                _persist(run_dir, idx)
            except OSError:
                pass
        return idx


# --------------------------------------------------------------------------- board view
def _span_ms(a, b):
    try:
        return round((dt.datetime.fromisoformat(b) - dt.datetime.fromisoformat(a)).total_seconds() * 1000, 1)
    except (ValueError, TypeError):
        return None


def aggregate(run_dir):
    """Per-qid live progress + measured metrics, in run_reader._aggregate_traces's shape."""
    idx = update(run_dir)
    adds_done, searched, answered, judged, per_q = {}, {}, {}, {}, {}
    for qid, q in idx["qids"].items():
        if q["adds_done"]:
            adds_done[qid] = q["adds_done"]
        if q["searched"]:
            searched[qid] = True
        if q["answered"]:
            answered[qid] = q["answered"]
        if q["judged"]:
            judged[qid] = q["judged"]
        per_q[qid] = {
            "add_calls": q["add_calls"], "add_resp": q["add_resp"],
            "add_failed": max(0, q["add_calls"] - q["add_resp"]),
            "add_zero": q["add_zero"],
            "mem_stored": q["mem_stored"],
            "mem_per_add": round(q["mem_stored"] / q["add_resp"], 2) if q["add_resp"] else None,
            "tok_in": q["tok_in"], "tok_out": q["tok_out"], "tok_total": q["tok_total"],
            "cutoffs": q["cutoffs"], "parse_fail": q["parse_fail"], "errors": q["errors"],
            "search_ms": round(q["search_ms"], 1) if q["search_ms"] else None,
            "wall_ms": _span_ms(q["first"], q["last"]),
        }
    ex = dict(idx["extraction"])
    ex["add_failed"] = max(0, ex.get("add_calls", 0) - ex.get("add_resp", 0))
    ex["mem_per_add"] = (round(ex.get("mem_stored", 0) / ex["add_resp"], 2)
                         if ex.get("add_resp") else None)
    ex["wall_ms"] = _span_ms(ex.pop("first", None), ex.pop("last", None))
    mr = idx.get("models_reported") or {"extraction": [], "answerer": []}
    return {"adds_done": adds_done, "searched": searched, "answered": answered,
            "judged": judged, "extraction": ex, "per_q": per_q,
            "models_reported": {"extraction": sorted(mr.get("extraction", [])),
                                "answerer": sorted(mr.get("answerer", []))}}


# --------------------------------------------------------------------------- question view
def _read_at(path, offsets):
    """Read and parse the lines at the given byte offsets (None -> None)."""
    out = []
    with open(path, "rb") as f:
        for off in offsets:
            if off is None:
                out.append(None)
                continue
            f.seek(off)
            raw = f.readline()
            try:
                out.append(json.loads(raw))
            except ValueError:
                out.append(None)
    return out


def question_ops(run_dir, qid, page=0, page_size=25):
    """Read one question's events straight from its offsets — never the whole file.

    All (small) add.request + add.response lines are read so the SEARCH panel can tag
    every candidate memory with its session/evidence status; only the current page's
    (large) llm extraction lines are read. Returns the pieces run_reader needs plus
    pagination metadata.
    """
    idx = update(run_dir)
    q = idx["qids"].get(qid)
    if q is None:
        return None

    units = q["units"]
    total = len(units)
    page = max(0, int(page))
    page_size = max(1, int(page_size))
    start = page * page_size
    page_units = units[start:start + page_size]

    mp = _plain_path(run_dir, "mem0_trace.jsonl")
    ep = _plain_path(run_dir, "eval_trace.jsonl")

    requests = _read_at(mp, [u["req"] for u in units]) if mp else []
    responses = _read_at(mp, [u["resp"] for u in units]) if mp else []
    page_llm = _read_at(mp, [u["llm"] for u in page_units]) if mp else []
    extra = _read_at(mp, [q["search_off"], q["scoring_off"]]) if mp else [None, None]
    search_req, scoring = extra[0], extra[1]
    eval_objs = _read_at(ep, q["eval_offs"]) if ep else []

    req_by_rid = {u["rid"]: requests[i] for i, u in enumerate(units)}
    resp_by_rid = {u["rid"]: responses[i] for i, u in enumerate(units)}
    llm_by_rid = {u["rid"]: page_llm[i] for i, u in enumerate(page_units)}

    return {
        "order_all": [u["rid"] for u in units],
        "page_order": [u["rid"] for u in page_units],
        "requests": req_by_rid,
        "responses": resp_by_rid,
        "llm": llm_by_rid,
        "search_req": search_req,
        "scoring": scoring,
        "eval": [o for o in eval_objs if o is not None],
        "total_units": total,
        "page": page,
        "page_size": page_size,
    }
