# experiments

LoCoMo conv0 runs of Mem0 OSS, plus the scripts, notes and traces that go with them.
The run index is [`RUNS.md`](RUNS.md); each run folder under [`runs/`](runs/) has its own `README.md`.

## Session date (Run C)

By default the benchmark sends a session timestamp on `add`, but the OSS server drops it, so the
extractor's Observation Date and each stored memory's `created_at` are the machine clock on the run
day (see [`notes/session_date_path.md`](notes/session_date_path.md)). The `code/session-date` Mem0
branch (commit `46c6add7`) accepts the `add` timestamp and uses the session datetime as the
extractor's **Observation Date** and as the stored memory's **`created_at`/`updated_at`**.

Switch it on by running with `MEM0_FORWARD_TIMESTAMP=1` and the `code/session-date` ref:

```
MEM0_FORWARD_TIMESTAMP=1 experiments/run_locomo_conv0.sh session-date code/session-date
```

Run C ([`runs/2026-11-14_0302-locomo-conv0-session-date/`](runs/2026-11-14_0302-locomo-conv0-session-date/README.md))
is Run A with this switch on. Path and intervention points: [`notes/session_date_path.md`](notes/session_date_path.md).

## Recorder (traces)

The operation recorder (`experiments/tracing/`) writes one JSON line per component boundary it
crosses:

- **ADD** (`Memory.add`): request, extraction prompt build, extraction LLM call (with token usage),
  fact parse, embeddings (vector lengths), hash dedup, BM25 lemmatization, vector-store inserts,
  history DB, spaCy entity extraction, entity-store lookups/updates/inserts.
- **SEARCH** (`Memory.search`): request, lemmatization, query entity extraction, query embed,
  semantic and BM25 search, entity boosts, `score_and_rank` (the full candidate pool incl. threshold
  drops), response.
- **EVALUATION** (benchmark side): client add/search + latency, `process_question`, the answerer
  prompt/answer/latency and tokens, and the judge prompt/verdict.

It is **off by default** (`MEM0_TRACE=0`) and changes nothing when off; vectors are replaced by their
length and no API keys, headers or environment are recorded. That the recorder does not change results
(stored payloads, search results, answers, verdicts) is checked by
[`tracing/selfcheck.py`](tracing/selfcheck.py) (the STEP 6 check), which runs the same input twice —
recorder off vs on — and diffs the outputs.

Switch it on with `MEM0_TRACE=1`; the server writes `mem0_trace.jsonl` and the benchmark writes
`eval_trace.jsonl` into the run folder:

```
MEM0_TRACE=1 experiments/run_locomo_conv0.sh <name> <ref>
```

Read the traces with `trace_view.py` (deterministic, no LLM/network):

```
experiments/scripts/trace_view.py --run <run_dir> --question conv0_q0   # one question end to end
experiments/scripts/trace_view.py --run <run_dir> --session 1           # add timeline for a session
experiments/scripts/trace_view.py --run <run_dir> --summary             # op counts + Current-Date check
experiments/scripts/trace_view.py --run <run_dir> --metrics             # cost & latency CSVs + summary
```

Wrap targets and what crosses each boundary: [`notes/trace_points.md`](notes/trace_points.md).
