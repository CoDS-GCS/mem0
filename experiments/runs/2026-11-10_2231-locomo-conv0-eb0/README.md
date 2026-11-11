# LoCoMo conv0, Mem0 branch code/entity-boost-0, ENTITY_BOOST_WEIGHT = 0 ("Run B")

## 1. Setup

- Mem0: `code/entity-boost-0`, commit `c91d87884a8801750d34e992349e776e8031d5c9`.
- Code change vs `v2.2.1`: `mem0/utils/scoring.py` line 57, `ENTITY_BOOST_WEIGHT` changed from `0.5` to `0.0`. `git diff v2.2.1 code/entity-boost-0 -- mem0/`:

```diff
--- a/mem0/utils/scoring.py
+++ b/mem0/utils/scoring.py
@@ -54,7 +54,7 @@ def normalize_bm25(raw_score: float, midpoint: float, steepness: float) -> float
     return 1.0 / (1.0 + math.exp(-steepness * (raw_score - midpoint)))


-ENTITY_BOOST_WEIGHT = 0.5
+ENTITY_BOOST_WEIGHT = 0.0


 def score_and_rank(
```

- All other settings are the same defaults as Run A (`experiments/runs/2026-11-10_1447-locomo-conv0-default/`):
  - Models: extraction `gpt-4o-mini`, embedder `text-embedding-3-small`, answerer `gpt-5`, judge `gpt-5`.
  - Scope: LoCoMo conversation 0, categories `multi-hop`, `open-domain`, `single-hop`, `temporal`.
  - `top_k`: 200, evaluated at cutoffs `top_10`, `top_20`, `top_50`, `top_200`.
  - Benchmark repo (`experiments/memory-benchmarks`, upstream `mem0ai/memory-benchmarks`): commit `4b61c5d31b9c668a12b4f5e78064248a02c82d2b`.
  - The benchmark server (`experiments/memory-benchmarks/docker/mem0/main.py`) carries the same Mem0 v2.x `search()` fix as Run A: entity ids (`user_id`/`agent_id`/`run_id`) moved inside `filters`, the result-count parameter renamed to `top_k`, and `explain=True` added so score breakdowns are available (commit `b0828fdb`).
  - `fastembed` is in `requirements.txt` so BM25 is on.

## 2. Results

J = % of questions the judge model (`gpt-5`) labelled CORRECT.

| cutoff | J (%) | correct / total |
|---|---|---|
| top_200 | 71.1 | 108/152 |
| top_50 | 69.1 | 105/152 |
| top_20 | 69.1 | 105/152 |
| top_10 | 66.4 | 101/152 |

Per-category at top_200:

| category | correct / total | accuracy (%) |
|---|---|---|
| open-domain | 12/13 | 92.3 |
| single-hop | 64/70 | 91.4 |
| multi-hop | 27/32 | 84.4 |
| temporal | 5/37 | 13.5 |

## 3. Verification

Over all retrieved results of all questions (`retrieval.search_results[*].score_debug.entity_boost`), counted across the full results file (152 questions, 30400 retrieved results total):

- Results with `entity_boost > 0`: 0 (expected: 0).
- Max `entity_boost` value: 0.0 (expected: 0).

## 4. Run facts

- Questions: 152.
- Ingestion chunks: 419 processed, 0 failed.
- Start time (`manifest.json` `started_utc`, UTC): `2026-11-10T22:32:46Z`.
- Results file timestamp (file mtime, UTC): `2026-11-11T02:29:22Z`.
- Search latency: median 750.2 ms, mean 814.0 ms.

## 5. Tokens

**a) Billed API tokens:** not recorded by the benchmark. Read them from the OpenAI usage dashboard for the time window `2026-11-10T22:32:46Z` to `2026-11-11T02:29:22Z` (UTC).

**b) API calls by design** (computed from the files, not measured):

| call type | count | formula |
|---|---|---|
| answer calls | 608 | 152 questions x 4 cutoffs |
| judge calls | 608 | 152 questions x 4 cutoffs |
| Mem0 add requests | 419 | ingestion chunks processed |

**c) Retrieved-memory tokens per question** (o200k_base encoding, tiktoken, of the memory texts passed to the answerer: first N `search_results` for cutoff N). Labelled: estimate of retrieved-memory context only; excludes prompts, answers and judge calls.

| cutoff | mean tokens | median tokens |
|---|---|---|
| top_10 | 280.9 | 286.0 |
| top_20 | 555.6 | 553.0 |
| top_50 | 1367.3 | 1375.5 |
| top_200 | 5282.1 | 5240.0 |

## 6. How to reproduce

```
experiments/run_locomo_conv0.sh eb0 code/entity-boost-0
```

## 7. See also

Default settings (`ENTITY_BOOST_WEIGHT = 0.5`, Mem0 `v2.2.1`): [`experiments/runs/2026-11-10_1447-locomo-conv0-default/README.md`](../2026-11-10_1447-locomo-conv0-default/README.md).
