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

## 7. Storage profile

Key numbers from `storage_profile.md` (source: `store_snapshot/memories.jsonl`, `store_snapshot/entities.jsonl`):

- Memories: 770.
- Entities: 383 (PROPER: 32, QUOTED: 4, TOPIC: 347).
- Links per entity: median 1, mean 5.48, max 570.

Full profile: [`storage_profile.md`](storage_profile.md).

## 8. Trace facts

[`trace_facts/INDEX.md`](trace_facts/INDEX.md) — 48 files: 44 questions judged WRONG at top_200, plus 4 questions flipped vs Run A (wrong in A, correct in B: `conv0_q40`, `conv0_q73`, `conv0_q142`, `conv0_q148`).

## 9. Comparison with Run A (default settings)

Output of `compare_runs.py` for A (`2026-11-10_1447-locomo-conv0-default`) vs B (`2026-11-10_2231-locomo-conv0-eb0`, this run):

### J

J = % of questions the judge model labelled CORRECT.

| cutoff | J_A (%) | J_B (%) | diff (pts, B-A) | correct_A/total | correct_B/total | diff (questions, B-A) |
|---|---|---|---|---|---|---|
| top_10 | 67.1 | 66.4 | -0.7 | 102/152 | 101/152 | -1 |
| top_20 | 69.1 | 69.1 | +0.0 | 105/152 | 105/152 | +0 |
| top_50 | 71.7 | 69.1 | -2.6 | 109/152 | 105/152 | -4 |
| top_200 | 71.7 | 71.1 | -0.7 | 109/152 | 108/152 | -1 |

Per-category at top_200:

| category | correct_A/total | correct_B/total | diff (questions, B-A) |
|---|---|---|---|
| multi-hop | 27/32 | 27/32 | +0 |
| open-domain | 13/13 | 12/13 | -1 |
| single-hop | 63/70 | 64/70 | +1 |
| temporal | 6/37 | 5/37 | -1 |

### Flips at top_200 (match by question_id)

- Correct in A, wrong in B: 5
  - multi-hop: 1
  - open-domain: 1
  - single-hop: 1
  - temporal: 2
- Wrong in A, correct in B: 4
  - multi-hop: 1
  - single-hop: 2
  - temporal: 1

| question_id | category | question | gold answer | A's answer (top_200) | B's answer (top_200) | trace (A) | trace (B) |
|---|---|---|---|---|---|---|---|
| conv0_q1 | temporal | When did Melanie paint a sunrise? | 2022 | Last year — she painted a lake sunrise that holds special significance for her. | She didn't—none of the memories mention Melanie painting a sunrise. They only mention her painting sunsets (e.g., a sunset over a lake and other sunset-themed pieces). | [../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q1.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q1.md) | [trace_facts/conv0_q1.md](trace_facts/conv0_q1.md) |
| conv0_q33 | temporal | When did Caroline go to a pride parade during the summer? | The week before 3 July 2023 | Last summer — at last year's Pride festival. | Last year (at the Pride festival). | [../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q33.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q33.md) | [trace_facts/conv0_q33.md](trace_facts/conv0_q33.md) |
| conv0_q34 | multi-hop | What events has Caroline participated in to help children? | Mentoring program, school speech | - Spoke at a school event to share her story and encourage students' involvement in the LGBTQ community. - Attended an adoption council meeting supporting efforts to create loving homes for children. - Helped organize a talent show for kids at the LGBTQ+ youth center. - Participated in an LGBT pride event with her transgender teen mentee to build confidence and show support. - Attended an adoption advice and assistance group meeting to further her goal of providing a home for children. |  | [../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q34.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q34.md) | [trace_facts/conv0_q34.md](trace_facts/conv0_q34.md) |
| conv0_q40 | multi-hop | How many times has Melanie gone to the beach in 2023? | 2 | 1 | Once or twice. | [../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q40.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q40.md) | [trace_facts/conv0_q40.md](trace_facts/conv0_q40.md) |
| conv0_q73 | temporal | When did Melanie get hurt? | September 2023 | October 2026. | September 2023. | [../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q73.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q73.md) | [trace_facts/conv0_q73.md](trace_facts/conv0_q73.md) |
| conv0_q77 | open-domain | Would Melanie go on another roadtrip soon? | Likely no; since this one went badly | Likely not soon. | Yes. Despite the scary car accident on her Nov 5-6 road trip, she was back out on a family camping trip around Nov 10 and already has another camping trip planned for December 2026, so she's continuing to travel and would likely go on another road trip soon. | [../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q77.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q77.md) | [trace_facts/conv0_q77.md](trace_facts/conv0_q77.md) |
| conv0_q113 | single-hop | What did Caroline see at the council meeting for adoption? | many people wanting to create loving homes for children in need | Many people expressing a desire to adopt and create loving homes for children in need. | She saw an inspiring and emotional adoption council meeting that strengthened her determination to adopt. | [../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q113.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q113.md) | [trace_facts/conv0_q113.md](trace_facts/conv0_q113.md) |
| conv0_q142 | single-hop | How do Melanie and Caroline describe their journey through life together? | An ongoing adventure of learning and growing. | They describe it as walking side by side—motivating and helping each other, tackling life's challenges together, and making a real impact together. | As a shared, supportive adventure—learning and growing together, tackling life's challenges side by side, making memories, and using their bond to make a difference. | [../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q142.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q142.md) | [trace_facts/conv0_q142.md](trace_facts/conv0_q142.md) |
| conv0_q148 | single-hop | What was Melanie's reaction to her children enjoying the Grand Canyon? | She was happy and thankful | She responded by sharing a photo of her two children at the Grand Canyon and noted that her family enjoyed the visit. | She happily shared a photo of her kids at the Grand Canyon and said her family enjoyed the visit. | [../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q148.md](../2026-11-10_1447-locomo-conv0-default/trace_facts/conv0_q148.md) | [trace_facts/conv0_q148.md](trace_facts/conv0_q148.md) |

### Tokens

Estimate of retrieved-memory context only (tiktoken o200k_base, memory texts of the first N search_results per cutoff); excludes prompts, answers and judge calls.

| cutoff | mean_A | median_A | mean_B | median_B |
|---|---|---|---|---|
| top_10 | 280.8 | 281.0 | 280.9 | 286.0 |
| top_20 | 558.1 | 554.0 | 555.6 | 553.0 |
| top_50 | 1375.9 | 1386.5 | 1367.3 | 1375.5 |
| top_200 | 5315.2 | 5242.5 | 5282.1 | 5240.0 |

API calls by design:

| call type | A | B | formula |
|---|---|---|---|
| answer calls | 608 | 608 | questions x 4 cutoffs |
| judge calls | 608 | 608 | questions x 4 cutoffs |
| Mem0 add requests | 419 | 419 | ingestion chunks processed |

Billed tokens: not recorded by the benchmark.

- A: check the OpenAI usage dashboard for the time window `2026-11-10T14:47:50Z` to `2026-11-10T19:29:53Z` (UTC).
- B: check the OpenAI usage dashboard for the time window `2026-11-10T22:32:46Z` to `2026-11-11T02:29:22Z` (UTC).

### Latency

Search latency per question (`retrieval.search_latency_ms`), milliseconds:

| run | median | mean | p90 | max |
|---|---|---|---|---|
| A | 702.1 | 725.2 | 922.3 | 3002.7 |
| B | 750.2 | 814.0 | 1190.6 | 1687.7 |

Whole-run wall time (results file timestamp minus manifest `started_utc`):

- A: `2026-11-10T14:47:50Z` to `2026-11-10T19:29:53Z` = 4h42m03s (16923s)
- B: `2026-11-10T22:32:46Z` to `2026-11-11T02:29:22Z` = 3h56m36s (14196s)

Phase times, final progress line from console.log for each phase:

- A, ingestion: `Ingest conv 0: 100%|██████████| 419/419 [20:33<00:00,  2.94s/it]`
- A, evaluation: `Questions conv 0: 100%|██████████| 152/152 [4:21:27<00:00, 103.21s/it]`
- B, ingestion: `Ingest conv 0: 100%|██████████| 419/419 [15:46<00:00,  2.26s/it]`
- B, evaluation: `Questions conv 0: 100%|██████████| 152/152 [3:40:48<00:00, 87.16s/it]`

Only search latency is measured per query. Add, answer and judge calls are not timed individually.

### Storage

| | A | B |
|---|---|---|
| Memories | 736 | 770 |
| Entities | 371 | 383 |
| Links per entity, median | 1.0 | 1.0 |
| Links per entity, mean | 5.36 | 5.48 |
| Links per entity, max | 538 | 570 |

### Note

Each run ingested conversation 0 separately with an LLM, so their stored memories differ (see Storage). A flip can come from the weight change or from a different stored memory; this comparison does not separate the two.

Generated by:

```
experiments/memory-benchmarks/.venv/bin/python experiments/scripts/compare_runs.py experiments/runs/2026-11-10_1447-locomo-conv0-default/ experiments/runs/2026-11-10_2231-locomo-conv0-eb0/
```

## 10. Derived outputs

| Output | Script | Command |
|---|---|---|
| `store_snapshot/memories.jsonl`, `store_snapshot/entities.jsonl`, `store_snapshot/README.md` | `experiments/scripts/export_store.py` | `experiments/scripts/export_store.py experiments/runs/2026-11-10_2231-locomo-conv0-eb0/` |
| `storage_profile.md` | `experiments/scripts/profile_storage.py` | `experiments/scripts/profile_storage.py experiments/runs/2026-11-10_2231-locomo-conv0-eb0/` |
| `trace_facts/<question_id>.md` (44 files, all questions judged WRONG at top_200) and `trace_facts/INDEX.md` | `experiments/scripts/trace_question.py` | `experiments/scripts/trace_question.py experiments/runs/2026-11-10_2231-locomo-conv0-eb0/ --all-failures` |
| `trace_facts/conv0_q40.md`, `trace_facts/conv0_q73.md`, `trace_facts/conv0_q142.md`, `trace_facts/conv0_q148.md` (4 files, flipped vs Run A: wrong in A, correct in B) | `experiments/scripts/trace_question.py` | `experiments/scripts/trace_question.py experiments/runs/2026-11-10_2231-locomo-conv0-eb0/ conv0_q142 conv0_q148 conv0_q40 conv0_q73` |
| `## 9. Comparison with Run A` (this section) | `experiments/scripts/compare_runs.py` | `experiments/memory-benchmarks/.venv/bin/python experiments/scripts/compare_runs.py experiments/runs/2026-11-10_1447-locomo-conv0-default/ experiments/runs/2026-11-10_2231-locomo-conv0-eb0/` |

`export_store.py` and `profile_storage.py` were run with `/shared_mnt/loubna/venv-analysis/bin/python` (a venv outside the repo, not `experiments/memory-benchmarks/.venv`). `trace_question.py` likewise. `compare_runs.py` was run with `experiments/memory-benchmarks/.venv/bin/python` (needs `tiktoken`).

## 11. See also

Default settings (`ENTITY_BOOST_WEIGHT = 0.5`, Mem0 `v2.2.1`): [`experiments/runs/2026-11-10_1447-locomo-conv0-default/README.md`](../2026-11-10_1447-locomo-conv0-default/README.md).
