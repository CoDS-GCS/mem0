# LoCoMo conv0, Mem0 branch code/session-date, session date forwarded + recorder on ("Run C")

## 1. What Run C changes vs Run A

Run C is Run A (`experiments/runs/2026-11-10_1447-locomo-conv0-default/`) with one behavioural
change: each session's date reaches Mem0. The benchmark forwards the session timestamp on `add`
(`MEM0_FORWARD_TIMESTAMP=1`), and the `code/session-date` Mem0 branch accepts that timestamp and
uses the session datetime as the extractor's Observation Date and as the stored memory's
`created_at`/`updated_at` (see [`../../notes/session_date_path.md`](../../notes/session_date_path.md)).
Run C is also the first run with the operation recorder on (`MEM0_TRACE=1`); Run A and Run B were
not traced.

Exact command:

```
MEM0_TRACE=1 MEM0_FORWARD_TIMESTAMP=1 experiments/run_locomo_conv0.sh session-date code/session-date
```

Commits involved (SHAs from `git log`):

| Role | Ref | Commit | Subject |
|---|---|---|---|
| Mem0 code | `code/session-date` | `46c6add7` | feat(memory): accept add() timestamp as session date (OSS) |
| Benchmark server forward | `experiments` | `145bb12a` | run: forward session timestamp to Mem0 server behind MEM0_FORWARD_TIMESTAMP |
| Recorder | `experiments` | `a9421be3` | trace: operation recorder for ADD/SEARCH/eval (opt-in MEM0_TRACE) |
| Reader / metrics | `experiments` | `971aff77` | trace: deterministic reader + system cost/latency metrics |

## 2. Settings

From `manifest.json`:

- Mem0: `code/session-date`, commit `46c6add7633cc4a4a04f9120b675c00cc1114a74`.
- Models: extraction `gpt-4o-mini`, embedder `text-embedding-3-small`, answerer `gpt-5`, judge `gpt-5`.
- Benchmark repo (`experiments/memory-benchmarks`, upstream `mem0ai/memory-benchmarks`): commit `4b61c5d31b9c668a12b4f5e78064248a02c82d2b`.
- `experiments` commit at run time: `971aff77d72986f6af3a9aeb9be1fd46e2080f11`.
- `forward_timestamp`: `1`. `trace_enabled`: `1`.
- Scope: LoCoMo conversation 0, categories `multi-hop`, `open-domain`, `single-hop`, `temporal`.
- `top_k`: 200, evaluated at cutoffs `top_10`, `top_20`, `top_50`, `top_200`.
- Start time (`started_utc`, UTC): `2026-11-14T03:02:35Z`.

## 3. Results

J = % of questions the judge model (`gpt-5`) labelled CORRECT. Source: `summary.md` (`metrics_by_cutoff`,
from `locomo_results_20261114_060432.json`).

| cutoff | J (%) | correct / total |
|---|---|---|
| top_200 | 85.5 | 130/152 |
| top_50 | 84.2 | 128/152 |
| top_20 | 80.3 | 122/152 |
| top_10 | 80.3 | 122/152 |

Per-category at top_200 (source: `summary.md`):

| category | correct / total | accuracy (%) |
|---|---|---|
| open-domain | 13/13 | 100.0 |
| temporal | 36/37 | 97.3 |
| multi-hop | 27/32 | 84.4 |
| single-hop | 54/70 | 77.1 |

## 4. Run A vs Run C

Source: `compare_A_vs_C.md` (output of `compare_runs.py`; it labels Run A as **A** and Run C as **B**).

### J

| cutoff | J_A (%) | J_C (%) | diff (pts, C-A) | correct_A/total | correct_C/total | diff (questions, C-A) |
|---|---|---|---|---|---|---|
| top_10 | 67.1 | 80.3 | +13.2 | 102/152 | 122/152 | +20 |
| top_20 | 69.1 | 80.3 | +11.2 | 105/152 | 122/152 | +17 |
| top_50 | 71.7 | 84.2 | +12.5 | 109/152 | 128/152 | +19 |
| top_200 | 71.7 | 85.5 | +13.8 | 109/152 | 130/152 | +21 |

Per-category at top_200:

| category | correct_A/total | correct_C/total | diff (questions, C-A) |
|---|---|---|---|
| multi-hop | 27/32 | 27/32 | +0 |
| open-domain | 13/13 | 13/13 | +0 |
| single-hop | 63/70 | 54/70 | -9 |
| temporal | 6/37 | 36/37 | +30 |

### Flipped questions at top_200 (source: `compare_A_vs_C.md` §2)

Counts: correct in A / wrong in C = 11 (multi-hop 1, single-hop 9, temporal 1); wrong in A / correct in C = 32 (multi-hop 1, temporal 31).

Correct in A → wrong in C (11):

| question_id | category |
|---|---|
| conv0_q26 | temporal |
| conv0_q32 | multi-hop |
| conv0_q94 | single-hop |
| conv0_q141 | single-hop |
| conv0_q143 | single-hop |
| conv0_q145 | single-hop |
| conv0_q146 | single-hop |
| conv0_q147 | single-hop |
| conv0_q149 | single-hop |
| conv0_q150 | single-hop |
| conv0_q151 | single-hop |

Wrong in A → correct in C (32):

| question_id | category |
|---|---|
| conv0_q0 | temporal |
| conv0_q5 | temporal |
| conv0_q6 | temporal |
| conv0_q8 | temporal |
| conv0_q9 | temporal |
| conv0_q16 | temporal |
| conv0_q17 | temporal |
| conv0_q20 | temporal |
| conv0_q21 | temporal |
| conv0_q25 | temporal |
| conv0_q28 | temporal |
| conv0_q29 | temporal |
| conv0_q31 | temporal |
| conv0_q35 | temporal |
| conv0_q36 | temporal |
| conv0_q41 | temporal |
| conv0_q44 | temporal |
| conv0_q45 | temporal |
| conv0_q49 | temporal |
| conv0_q53 | temporal |
| conv0_q54 | temporal |
| conv0_q57 | temporal |
| conv0_q58 | temporal |
| conv0_q62 | temporal |
| conv0_q63 | temporal |
| conv0_q67 | temporal |
| conv0_q68 | temporal |
| conv0_q73 | temporal |
| conv0_q74 | temporal |
| conv0_q76 | multi-hop |
| conv0_q79 | temporal |
| conv0_q80 | temporal |

Per-question answers and trace links for every flip: `compare_A_vs_C.md` §2.

## 5. Dates

Source: `trace_summary.md` (Current-Date leakage check).

- Extractor Current Date value seen in the extraction prompts: `2026-11-14`.
- Stored memories whose text mentions the run's Current Date (`2026-11-14`) or its year (`2026`): **0**.

See [`trace_summary.md`](trace_summary.md).

## 6. System cost and latency

These exist only for Run C: Run A and Run B were not traced (`MEM0_TRACE=0`), so no latency or token
telemetry was recorded for them. The judge's cost is intentionally not measured. Source:
`metrics_summary.md`, `per_question_metrics.csv`, `per_session_metrics.csv` (from `trace_view.py --metrics`).
Per-question values are at the largest cutoff the answerer ran (top_200). `total_latency` = search latency +
answer latency.

Overall (per question):

| metric | n | mean | p50 | p95 |
|---|---|---|---|---|
| search_latency_ms | 152 | 4778.4 | 580.45 | 58134.43 |
| total_latency_ms | 152 | 15538.81 | 8754.48 | 86140.24 |
| memory_tokens | 141 | 6716.63 | 6661.0 | 7301.0 |

Per category:

| category | search mean / p50 / p95 (ms) | total mean / p50 / p95 (ms) | memory_tokens mean / p50 / p95 |
|---|---|---|---|
| multi-hop | 616.51 / 559.0 / 807.34 | 13449.09 / 12135.75 / 25683.42 | 6671.12 / 6570.5 / 7281.85 |
| open-domain | 624.26 / 581.3 / 875.0 | 11323.12 / 11466.77 / 15222.71 | 6645.23 / 6646.0 / 6985.0 |
| single-hop | 9658.33 / 580.2 / 58525.73 | 21093.06 / 8560.11 / 86552.04 | 6665.66 / 6636.0 / 7269.0 |
| temporal | 605.11 / 593.4 / 755.22 | 8319.28 / 7712.59 / 11709.54 | 6862.35 / 6869.0 / 7370.0 |

Memory building (conversation totals, source: `metrics_summary.md` / `per_session_metrics.csv`):

- Add requests: 419; memories stored: 771.
- Total extraction tokens: prompt 3,540,698, completion 39,787, total 3,580,485.
- Total add time (client): 1,443,558.4 ms over 419 measured adds.

`memory_tokens` has n=141 (not 152): 11 questions have no top_200 memory-block tokens recorded in the trace.
See §8.

## 7. The 10 traced questions

The 10 questions traced in Run A (conv0_q0 plus the nine questions that flipped between Run A and Run B),
read with the deterministic reader `trace_view.py --question`. Verdicts at top_200. Source:
`traces/INDEX.md` (read from each run's `locomo_results_*.json`).

| question_id | category | question | Run A → Run C | trace |
|---|---|---|---|---|
| conv0_q0 | temporal | When did Caroline go to the LGBTQ support group? | WRONG → CORRECT | [traces/conv0_q0.md](traces/conv0_q0.md) |
| conv0_q1 | temporal | When did Melanie paint a sunrise? | CORRECT → CORRECT | [traces/conv0_q1.md](traces/conv0_q1.md) |
| conv0_q33 | temporal | When did Caroline go to a pride parade during the summer? | CORRECT → CORRECT | [traces/conv0_q33.md](traces/conv0_q33.md) |
| conv0_q34 | multi-hop | What events has Caroline participated in to help children? | CORRECT → CORRECT | [traces/conv0_q34.md](traces/conv0_q34.md) |
| conv0_q40 | multi-hop | How many times has Melanie gone to the beach in 2023? | WRONG → WRONG | [traces/conv0_q40.md](traces/conv0_q40.md) |
| conv0_q73 | temporal | When did Melanie get hurt? | WRONG → CORRECT | [traces/conv0_q73.md](traces/conv0_q73.md) |
| conv0_q77 | open-domain | Would Melanie go on another roadtrip soon? | CORRECT → CORRECT | [traces/conv0_q77.md](traces/conv0_q77.md) |
| conv0_q113 | single-hop | What did Caroline see at the council meeting for adoption? | CORRECT → CORRECT | [traces/conv0_q113.md](traces/conv0_q113.md) |
| conv0_q142 | single-hop | How do Melanie and Caroline describe their journey through life together? | WRONG → WRONG | not generated (see §8) |
| conv0_q148 | single-hop | What was Melanie's reaction to her children enjoying the Grand Canyon? | WRONG → WRONG | not generated (see §8) |

Index: [`traces/INDEX.md`](traces/INDEX.md).

`traces/conv0_q142.md` and `traces/conv0_q148.md` were not generated: `trace_view.py --question` raised
`AttributeError` in `scoring()` (`trace_view.py:216`). For both questions the matched server search request
recorded only `entry.search.request → spacy.lemmatize_for_bm25 → spacy.extract_entities → embedder.embed` and
no `scoring.score_and_rank` or `entry.search.response` event (54 of 195 server search requests have no
`scoring.score_and_rank` event; the eval side still answered at all four cutoffs). `scoring()` reads
`e.get("inputs")` before its `if e else` guard, so it raises instead of returning empty when the scoring event
is missing. The script was left unchanged.

## 8. Trace files

Source: `manifest.json` (`trace` block) and file sizes on disk.

| file | gz bytes | raw bytes | events | recorder errors | in git |
|---|---|---|---|---|---|
| `mem0_trace.jsonl.gz` | 25,482,830 | 80,805,123 | 10,091 | 0 | yes |
| `eval_trace.jsonl.gz` | 2,678,906 | 14,763,792 | 1,788 | 0 | yes |

Both are under 50 MB gzipped, so they are committed to git.

View commands (run with `/shared_mnt/loubna/venv-analysis/bin/python`):

```
# one question (evidence → add/extraction/storage → search → answer/judge)
experiments/scripts/trace_view.py --run <run_dir> --question conv0_q0

# add timeline for one session
experiments/scripts/trace_view.py --run <run_dir> --session 1

# operation counts, memories/entities/duplicates, Current-Date leakage check
experiments/scripts/trace_view.py --run <run_dir> --summary

# per-question / per-session cost & latency CSVs + summary
experiments/scripts/trace_view.py --run <run_dir> --metrics
```

## 9. Derived outputs

All run with `/shared_mnt/loubna/venv-analysis/bin/python`.

| Output | Script | Command |
|---|---|---|
| `summary.md` | `summarize_run.py` | `summarize_run.py experiments/runs/2026-11-14_0302-locomo-conv0-session-date/` |
| `trace_summary.md` | `trace_view.py --summary` | `trace_view.py --run <run_dir> --summary --out <run_dir>/trace_summary.md` |
| `per_question_metrics.csv`, `per_session_metrics.csv`, `metrics_summary.md` | `trace_view.py --metrics` | `trace_view.py --run <run_dir> --metrics --out <run_dir>/metrics_summary.md` |
| `store_snapshot/*`, `storage_profile.md` | `export_store.py`, `profile_storage.py` | `export_store.py <run_dir>` then `profile_storage.py <run_dir>` |
| `trace_facts/<question_id>.md` (43 flipped questions vs Run A) | `trace_question.py` | `trace_question.py <run_dir> conv0_q0 conv0_q5 … conv0_q151` |
| `compare_A_vs_C.md` | `compare_runs.py` | `compare_runs.py experiments/runs/2026-11-10_1447-locomo-conv0-default/ experiments/runs/2026-11-14_0302-locomo-conv0-session-date/` |
| `traces/<question_id>.md` (8 of 10; see §7), `traces/INDEX.md` | `trace_view.py --question` | `trace_view.py --run <run_dir> --question conv0_q0 --out <run_dir>/traces/conv0_q0.md` |

## 10. See also

- Run A (default, Mem0 `v2.2.1`): [`../2026-11-10_1447-locomo-conv0-default/README.md`](../2026-11-10_1447-locomo-conv0-default/README.md).
- Run B (`ENTITY_BOOST_WEIGHT = 0`): [`../2026-11-10_2231-locomo-conv0-eb0/README.md`](../2026-11-10_2231-locomo-conv0-eb0/README.md).
- Session-date path: [`../../notes/session_date_path.md`](../../notes/session_date_path.md).
- Trace points: [`../../notes/trace_points.md`](../../notes/trace_points.md).
