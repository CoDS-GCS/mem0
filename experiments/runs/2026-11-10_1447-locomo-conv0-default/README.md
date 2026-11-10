# LoCoMo conv0, Mem0 OSS v2.2.1, default settings ("Run A")

## 1. Setup

- Mem0: `v2.2.1`, commit `94c3fe9f238f3dbf29c9ce98643bd71eb13077cd`.
- Benchmark repo (`experiments/memory-benchmarks`, upstream `mem0ai/memory-benchmarks`): commit `4b61c5d31b9c668a12b4f5e78064248a02c82d2b`.
- Models: extraction `gpt-4o-mini`, embedder `text-embedding-3-small`, answerer `gpt-5`, judge `gpt-5`.
- Scope: LoCoMo conversation 0, categories `multi-hop`, `open-domain`, `single-hop`, `temporal`.
- `top_k`: 200, evaluated at cutoffs `top_10`, `top_20`, `top_50`, `top_200`.

## 2. Results

J = % of questions the judge model (`gpt-5`) labelled CORRECT.

| cutoff | J (%) | correct / total |
|---|---|---|
| top_200 | 71.7 | 109/152 |
| top_50 | 71.7 | 109/152 |
| top_20 | 69.1 | 105/152 |
| top_10 | 67.1 | 102/152 |

Per-category at top_200:

| category | correct / total | accuracy (%) |
|---|---|---|
| open-domain | 13/13 | 100.0 |
| single-hop | 63/70 | 90.0 |
| multi-hop | 27/32 | 84.4 |
| temporal | 6/37 | 16.2 |

## 3. Run facts

- Questions: 152.
- Ingestion chunks: 419 processed, 0 failed.
- Start time (`manifest.json` `started_utc`, UTC): `2026-11-10T14:47:50Z`.
- Results file timestamp (file mtime, UTC): `2026-11-10T19:29:53Z`.
- Search latency: median 702.1 ms, mean 725.2 ms.

## 4. Tokens

**a) Billed API tokens:** not recorded by the benchmark. Read them from the OpenAI usage dashboard for the time window `2026-11-10T14:47:50Z` to `2026-11-10T19:29:53Z` (UTC).

**b) API calls by design** (computed from the files, not measured):

| call type | count | formula |
|---|---|---|
| answer calls | 608 | 152 questions x 4 cutoffs |
| judge calls | 608 | 152 questions x 4 cutoffs |
| Mem0 add requests | 419 | ingestion chunks processed |

**c) Retrieved-memory tokens per question** (o200k_base encoding, tiktoken, of the memory texts passed to the answerer: first N `search_results` for cutoff N). Labelled: estimate of retrieved-memory context only; excludes prompts, answers and judge calls.

| cutoff | mean tokens | median tokens |
|---|---|---|
| top_10 | 280.8 | 281.0 |
| top_20 | 558.1 | 554.0 |
| top_50 | 1375.9 | 1386.5 |
| top_200 | 5315.2 | 5242.5 |

## 5. Setup notes

- The benchmark server (`experiments/memory-benchmarks/docker/mem0/main.py`) was patched for Mem0 v2.x `search()`: entity ids (`user_id`/`agent_id`/`run_id`) moved inside `filters`, the result-count parameter renamed to `top_k`, and `explain=True` added so score breakdowns are available. `fastembed` was added to `requirements.txt` so BM25 is on. See commit `b0828fdb` (`setup: fix search for mem0 v2.x, enable BM25, add run script`).
- The benchmark sends a session timestamp on add (`AddRequest.observation_date`), but the OSS server does not pass it through to `mem.add()` (`main.py`, `add_memories`). Message text itself has no dates.

## 6. How to reproduce

```
experiments/run_locomo_conv0.sh default v2.2.1
```

## 7. Derived outputs

Snapshot taken from the live Qdrant store on 2026-11-10T20:52:30Z (UTC), filtered to this run's user id (`locomo_0_0ff46ffe`), read-only (scroll/count only, no writes).

| Output | Script | Command |
|---|---|---|
| `store_snapshot/memories.jsonl`, `store_snapshot/entities.jsonl`, `store_snapshot/README.md` | `experiments/scripts/export_store.py` | `experiments/scripts/export_store.py experiments/runs/2026-11-10_1447-locomo-conv0-default/` |
| `storage_profile.md` | `experiments/scripts/profile_storage.py` | `experiments/scripts/profile_storage.py experiments/runs/2026-11-10_1447-locomo-conv0-default/` |
| `trace_facts/<question_id>.md` (43 files, all questions judged WRONG at top_200) and `trace_facts/INDEX.md` | `experiments/scripts/trace_question.py` | `experiments/scripts/trace_question.py experiments/runs/2026-11-10_1447-locomo-conv0-default/ --all-failures` |

All three were run with `/shared_mnt/loubna/venv-analysis/bin/python` (a venv outside the repo, not `experiments/memory-benchmarks/.venv`).
