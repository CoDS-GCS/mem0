# LongMemEval monitor

Read-only web explorer for the LongMemEval dataset. It lets you SEE the benchmark —
questions, their haystack sessions on a date axis, and the exact (user, assistant)
turn-pairs that each become one `mem0.add()` — **before** running Mem0 on it.

It never runs the benchmark or starts the Mem0 server; it only reads the pinned dataset
JSON (indexed into SQLite).

## Run

```bash
experiments/monitor/run_monitor.sh      # builds the index if missing, serves 127.0.0.1:8020
```

Needs `experiments/data/longmemeval_s_cleaned.json` (see `experiments/data/README`) and a
Python env at `/shared_mnt/loubna/venv-analysis` (override with `LME_VENV`). FastAPI +
uvicorn are installed on first run.

## Pieces

- `build_index.py` — one-time: dataset JSON → `longmemeval.sqlite` (gitignored).
  Sessions are de-duped by `session_id` (their turns are invariant across haystacks —
  verified at build time); date / evidence / chronological position live on the
  question↔session **link**, because the same session sits in many haystacks with
  different dates.
- `app.py` — FastAPI JSON API + serves the static page. Binds `127.0.0.1:8020`.
- `static/` — one vanilla-JS page (no npm, no build, no CDN), hash-routed
  (`#/`, `#/type/<type>`, `#/q/<id>`, `#/s/<session>`), turns lazy-loaded per session.

## "add-unit"

One `mem0.add()` call = one non-empty (user, assistant) turn-pair, matching
`benchmarks/longmemeval/run.py` `pair_turns` (chunks of 2) and its empty-pair skip. The
timestamp an add would carry is the session's date **for that haystack**; it only reaches
Mem0 with `MEM0_FORWARD_TIMESTAMP=1` and a session-date mem0 build (plain v2.2.1 drops it).

## Future: run overlay

The API is shaped so a run overlay can be added later without changing these endpoints: a
future `/api/run/...` can return, per question, the predicted answer, judge verdict,
retrieved memories (with semantic/BM25/entity scores) and live progress, merged onto the
same question + session objects the page already renders.
