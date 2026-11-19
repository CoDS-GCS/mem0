# Provenance of every fact in trace_facts/conv0_q0.md

Scope: Run A, `experiments/runs/2026-11-10_1447-locomo-conv0-default/`, question `conv0_q0`.
Everything below was read from files in this repo/run folder or retrieved read-only from Qdrant.
No LLM calls were made to produce this report, and nothing was written to Qdrant.

---

## 1. The chain of files

### `locomo_results_20261110_192953.json` and `predicted_locomo-conv0-default/conv0_q0.json`

Written by `experiments/memory-benchmarks/benchmarks/locomo/run.py`, invoked via
`experiments/run_locomo_conv0.sh` step 4 (`"$PY" -m benchmarks.locomo.run ... --output-dir "$RUN_DIR"`).

- Per-question file `predicted_locomo-conv0-default/conv0_q0.json`: written at
  `run.py:933-934`:
  ```python
  result_path = os.path.join(output_dir, f"{qid}.json")
  save_result_json(result_path, result)
  ```
  `output_dir = os.path.join(args.output_dir, f"predicted_{args.project_name}")` (`run.py:735`),
  and `args.project_name = "locomo-conv0-default"` was passed by `run_locomo_conv0.sh` as
  `--project-name "locomo-conv0-$NAME"`.
  The `result` dict is built field-by-field in `process_question()` (`run.py:389-498`, see §2 for
  per-field line numbers) and the `cutoff_results` key is attached at `run.py:497`.

- Unified results file `locomo_results_20261110_192953.json`: written at `run.py:953-954`:
  ```python
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  unified_path = os.path.join(args.output_dir, f"locomo_results_{timestamp}.json")
  save_result_json(unified_path, {...})
  ```
  (the branch taken for this run, since it was a plain run — not `--evaluate-only`). It bundles
  every per-question `result` dict (including conv0_q0's) into the `"evaluations"` list.

- Both are written through `save_result_json()`, defined in
  `experiments/memory-benchmarks/benchmarks/common/utils.py:283-287`:
  ```python
  def save_result_json(path: str, data: dict) -> None:
      os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
      with open(path, "w", encoding="utf-8") as f:
          json.dump(data, f, indent=2, ensure_ascii=False, default=str)
  ```

### `manifest.json`, `console.log`, `server.log`

Written by `experiments/run_locomo_conv0.sh`, not by `run.py`:
- `manifest.json`: written by the heredoc at `run_locomo_conv0.sh` step 3 (`cat > "$RUN_DIR/manifest.json" <<EOF ... EOF`), before Mem0 ever runs. Records `mem0_ref`, `mem0_commit`, `experiments_commit`, model names, etc.
- `console.log`: written by the `tee` in step 4: `... "$@" 2>&1 | tee "$RUN_DIR/console.log"`. This captures `run.py`'s stdout/stderr (progress bars, per-cutoff metric summary) — it does not capture any Mem0-server-internal log lines.
- `server.log`: written by step 5: `docker compose logs --no-color --since "$START" mem0 > "$RUN_DIR/server.log" 2>&1`. This is the Mem0 Docker container's own log (FastAPI/uvicorn request lines, Mem0 internal INFO/WARNING lines), pulled after the run completes.

### `store_snapshot/memories.jsonl`

Written by `experiments/scripts/export_store.py`, run manually/separately after `run_locomo_conv0.sh` finished (it is not called by the shell script). Steps:
- `find_user_id()` (`export_store.py:45-52`) reads the user id out of `predicted_*/_ingestion_*.json`.
- `scroll_all()` (`export_store.py:55-75`) does a read-only Qdrant `.scroll()` over collection `memories` filtered to that `user_id`.
- The per-memory dict (`id`, `data`, `text_lemmatized`, `created_at`, `updated_at`, `hash`, `user_id`, `attributed_to`, `embedding_dims`, `bm25_entries`) is assembled at `export_store.py:95-108`.
- The file is written at `export_store.py:125-127`:
  ```python
  with open(out_dir / "memories.jsonl", "w") as f:
      for m in memories:
          f.write(json.dumps(m, ensure_ascii=False) + "\n")
  ```

### `trace_facts/conv0_q0.md`

Written by `experiments/scripts/trace_question.py`, invoked as
`trace_question.py <run_folder> conv0_q0 ...`. It:
- Loads `locomo_results_*.json` (`load_results`, `trace_question.py:42-46`), takes the newest file by name sort — in this run folder there is only one, `locomo_results_20261110_192953.json`.
- Loads `store_snapshot/memories.jsonl` (`load_memories`, `trace_question.py:49-59`).
- Loads the LoCoMo dataset `experiments/memory-benchmarks/datasets/locomo/locomo10.json` (`load_dataset`, `trace_question.py:62-63`).
- Builds the per-turn index for conversation 0 (`build_turn_index`, `trace_question.py:73-87`).
- Renders the markdown for `conv0_q0` via `render_trace()` (`trace_question.py:121-200`) and writes it at `trace_question.py:239-240`:
  ```python
  path = out_dir / f"{evaluation['question_id']}.md"
  path.write_text(content)
  ```

---

## 2. Fact by fact

Sources used below: `locomo_results_20261110_192953.json` (the `conv0_q0` element of `"evaluations"`), `predicted_locomo-conv0-default/conv0_q0.json`, `store_snapshot/memories.jsonl`, and `experiments/memory-benchmarks/datasets/locomo/locomo10.json` (element `[0]`, `conversation.session_1`, turn `D1:3`, `session_1_date_time`). **`conv0_q0.json` and the `conv0_q0` record inside the results JSON were diffed programmatically (`json.loads` + equality check) and are byte-for-byte identical** — every row below holds for both files simultaneously; "source file" lists both since they agree.

| Fact | Value in `trace_facts/conv0_q0.md` | Source file | Exact path/line | Raw value there | Equal? |
|---|---|---|---|---|---|
| question | "When did Caroline go to the LGBTQ support group?" | results JSON / conv0_q0.json | `evaluations[].question` (written at `run.py:427`, from `qa["question"]` at `run.py:411`) | `"When did Caroline go to the LGBTQ support group?"` | yes |
| question (dataset origin) | same | `locomo10.json` | `[0]["qa"][0]["question"]` | `"When did Caroline go to the LGBTQ support group?"` | yes |
| gold answer | "7 May 2023" | results JSON / conv0_q0.json | `evaluations[].ground_truth_answer` (`run.py:428`, from `qa["answer"]` at `run.py:413`) | `"7 May 2023"` | yes |
| gold answer (dataset origin) | same | `locomo10.json` | `[0]["qa"][0]["answer"]` | `"7 May 2023"` | yes |
| reference_date | "9:55 am on 22 October, 2023" | results JSON / conv0_q0.json | `evaluations[].reference_date` (`run.py:431`, from `sorted_sessions[-1][1]` at `run.py:891`) | `"9:55 am on 22 October, 2023"` | yes |
| reference_date (dataset origin) | same | `locomo10.json` | `[0]["conversation"]["session_19_date_time"]` — session 19 is the last chronologically of conv0's 19 sessions | `"9:55 am on 22 October, 2023"` | yes |
| evidence id | D1:3 | results JSON / conv0_q0.json | `evaluations[].evidence` (`run.py:429`, from `qa.get("evidence", [])` at `run.py:429`) | `["D1:3"]` | yes |
| evidence id (dataset origin) | same | `locomo10.json` | `[0]["qa"][0]["evidence"]` | `["D1:3"]` | yes |
| evidence text | "I went to a LGBTQ support group yesterday and it was so powerful." | `locomo10.json` (via `trace_question.py` `build_turn_index`, `trace_question.py:73-87`) | `[0]["conversation"]["session_1"][2]` (`dia_id == "D1:3"`) `.text` | `"I went to a LGBTQ support group yesterday and it was so powerful."` | yes |
| evidence speaker | Caroline | `locomo10.json` | same turn, `.speaker` | `"Caroline"` | yes |
| evidence session date | "1:56 pm on 8 May, 2023" | `locomo10.json` | `[0]["conversation"]["session_1_date_time"]` | `"1:56 pm on 8 May, 2023"` | yes |
| candidate 1 (rank 1) text | "Caroline attended an LGBTQ support group on November 9, 2026, and found it to be a powerful experience." | `store_snapshot/memories.jsonl` | line with `"id": "376d6d0a-101f-40b4-8b9e-8b7911637514"`, field `data` | identical string | yes |
| candidate 1 created_at | 2026-11-10T14:47:59.359256+00:00 | `store_snapshot/memories.jsonl` | same line, field `created_at` | identical | yes |
| candidate 1 overlap | 0.67 | computed by `trace_question.py` itself (`overlap_score`, `trace_question.py:95-100`), not read from any JSON | recomputed independently in §5: 4/6 = 0.6667 → rounds to 0.67 | matches | yes |
| candidate 1 rank/scores | rank 1, combined 0.9350, semantic 0.8396, bm25 0.9999, entity_boost 0.4980 | results JSON / conv0_q0.json | `evaluations[].retrieval.search_results[0]` and `.score_debug` | `score=0.9349954596541507`, `score_debug={"combined_score":0.9349954596541507,"semantic_score":0.8396004,"bm25_score":0.9998804602907552,"entity_boost":0.4980077888446215}` | yes (rounded to 4 d.p. by `fmt_score`, `trace_question.py:117-118`) |
| candidate 2 (overlap 0.50, "transgender stories...") | rank 3, combined 0.8747, semantic 0.6888, bm25 0.9999, entity_boost 0.4980 | results JSON | `search_results` entry id `134cbf35-d55b-4147-936f-10cdd7028c6f` | `score=0.8746691987394934`, `semantic_score=0.6887624`, `bm25_score=0.999902808004112`, `entity_boost=0.4980077888446215` | yes |
| candidate 3 (overlap 0.50, "gained the courage...") | rank 2, combined 0.9104, semantic 0.7781, bm25 0.9999, entity_boost 0.4980 | results JSON | `search_results` entry id `6e15e624-8dea-4364-ab0e-5d1e8e3522fb` | `score=0.9104144196541506`, `semantic_score=0.7781478`, `bm25_score=0.9998804602907552`, `entity_boost=0.4980077888446215` | yes |
| top-5 retrieved (ranks 1-5, text/created_at/scores) | see `trace_facts/conv0_q0.md` lines 20-24 | results JSON | `evaluations[].retrieval.search_results[0:5]` | all 5 entries checked — ids `376d6d0a...`, `6e15e624...`, `134cbf35...`, `5f313912...`, `ce9b65bd...` with matching scores (dumped in full in the fact-gathering step, see §3 for two of them) | yes |
| top_10 verdict | WRONG, "November 9, 2026.", reason as quoted | results JSON / conv0_q0.json | `evaluations[].cutoff_results.top_10` | `{"judgment":"WRONG","score":0.0,"generated_answer":"November 9, 2026.","memories_evaluated":10,"reason":"The generated date (November 9, 2026) does not match the gold date (May 7, 2023) and is not within the 14-day tolerance."}` | yes |
| top_20 verdict | WRONG, "November 9, 2026.", reason as quoted | results JSON / conv0_q0.json | `evaluations[].cutoff_results.top_20` | matches verbatim | yes |
| top_50 verdict | WRONG, "November 9, 2026.", reason as quoted | results JSON / conv0_q0.json | `evaluations[].cutoff_results.top_50` | matches verbatim | yes |
| top_200 verdict | WRONG, "November 9, 2026.", reason as quoted | results JSON / conv0_q0.json | `evaluations[].cutoff_results.top_200` | matches verbatim | yes |

Every row checked out equal. There were no discrepancies between `trace_facts/conv0_q0.md`, the results JSON, `conv0_q0.json`, the dataset, or the store snapshot.

---

## 3. The stored memory in Qdrant (rank-1 memory, live retrieval)

Qdrant host: `localhost`; port read from `QDRANT_PORT` in `experiments/memory-benchmarks/.env` (`QDRANT_PORT=6340`). No API key printed (none was needed/used — this is a local, unauthenticated Qdrant instance). Retrieved read-only via `QdrantClient(host="localhost", port=6340).retrieve(collection_name="memories", ids=[...], with_payload=True, with_vectors=False)` — a single-point fetch by id, no write/update/delete call made.

Rank-1 memory id: `376d6d0a-101f-40b4-8b9e-8b7911637514`

| Field | Live Qdrant value | `store_snapshot/memories.jsonl` value | Match? |
|---|---|---|---|
| `data` | "Caroline attended an LGBTQ support group on November 9, 2026, and found it to be a powerful experience." | same | yes |
| `created_at` | 2026-11-10T14:47:59.359256+00:00 | same | yes |
| `updated_at` | 2026-11-10T14:47:59.359256+00:00 | same | yes |
| `text_lemmatized` | "caroline attend lgbtq support group november 9 2026 find powerful experience" | same | yes |
| `user_id` | locomo_0_0ff46ffe | same | yes |
| `hash` | 8c627cfe9d87362ff72e0ff1b5e0e86d | same | yes |
| `attributed_to` | "user" | same | yes |

Live Qdrant state matches the exported snapshot exactly — the snapshot was not stale and nothing in Qdrant has changed since export.

---

## 4. Where the scores come from

Pipeline (search → score → format), in call order:

1. **`experiments/memory-benchmarks/docker/mem0/main.py:229-256`** — `/search` endpoint of the self-hosted server. It hardcodes `explain=True` when calling `mem.search()`:
   ```python
   # main.py:238
   params: dict[str, Any] = {"top_k": req.limit, "filters": filters, "explain": True}
   ...
   # main.py:242-243
   result = mem.search(req.query, **params)
   ```
   Then it renames Mem0's native field `score_details` to `score_breakdown` (`main.py:244-252`):
   ```python
   for item in result.get("results", []):
       details = item.get("score_details")
       if details:
           item["score_breakdown"] = {
               "semantic": details.get("semantic_score", 0),
               "bm25": details.get("bm25_score", 0),
               "entity_boost": details.get("entity_boost", 0),
           }
   ```
   **Note:** `explain=True` is unconditional here — it does not depend on the benchmark's `--score-debug` CLI flag at all; the server always asks Mem0 for score details.

2. **`experiments/memory-benchmarks/benchmarks/common/mem0_client.py:255-305`** (`Mem0Client._search_oss`) posts to `/search` and remaps `score_breakdown` → `score_debug` for the benchmark's own output schema (`mem0_client.py:293-301`):
   ```python
   breakdown = r.get("score_breakdown") or r.get("score_debug")
   if breakdown:
       entry["score_debug"] = {
           "combined_score": r.get("score", 0),
           "semantic_score": breakdown.get("semantic", 0),
           "bm25_score": breakdown.get("bm25", 0),
           "entity_boost": breakdown.get("entity_boost", 0),
       }
   ```
   **Note:** `Mem0Client.search()` (`mem0_client.py:241-253`) calls `self._search_oss(query, user_id, top_k, rerank)` — it does **not** pass `score_debug` into `_search_oss` at all (that parameter only matters for `_search_cloud`, `mem0_client.py:315-325`). In OSS mode the score breakdown is present or absent purely because of the server's unconditional `explain=True` from step 1, independent of `run.py`'s `--score-debug` flag.

3. **Mem0 v2.2.1, `mem0/memory/main.py:1642-1745`** (`Memory._search_vector_store`, sync; the async twin is `3330-3433` and is structurally identical) computes the three raw signals:
   - Semantic: `vector_store.search()` over-fetches `internal_limit = max(limit*4, 60)` candidates (`main.py:1654-1658`).
   - BM25: `vector_store.keyword_search()` then `normalize_bm25(raw_score, midpoint, steepness)` (`main.py:1660-1673`), with `midpoint`/`steepness` from `get_bm25_params()`.
   - Entity boost: `_compute_entity_boosts(query_entities, filters)` (`main.py:1676-1678`), only if the query itself contains named entities.
   These three are handed to `score_and_rank(...)` (`main.py:1694-1701`), and if `explain=True`, each scored result's `score_details` dict is attached to the formatted `MemoryItem` at `main.py:1740-1741`.

4. **`mem0/utils/scoring.py:60-139`** (`score_and_rank`) is where `score_details` is actually assembled:
   ```python
   # scoring.py:118-135
   raw_combined = semantic_score + bm25_score + entity_boost
   combined = min(raw_combined / max_possible, 1.0)
   scored_result = {"id": mem_id_str, "score": combined, "payload": result.get("payload")}
   if explain:
       scored_result["score_details"] = {
           "semantic_score": semantic_score,
           "bm25_score": bm25_score,
           "entity_boost": entity_boost,
           "raw_score": raw_combined,
           "max_possible_score": max_possible,
           "final_score": combined,
           "threshold": threshold,
       }
   ```
   `max_possible` depends on which signals are active for this query (`scoring.py:94-101`): 1.0 (semantic only), 2.0 (+bm25), 2.5 (+bm25 +entity), or 1.5 (+entity, no bm25). For q0 all three signals were active (bm25 and entity_boost are both non-zero for every retrieved memory), so `max_possible = 2.5`. Sanity check on rank 1: `(0.8396004 + 0.9998804602907552 + 0.4980077888446215) / 2.5 = 0.9349954...` — matches the reported `combined`/`score` of `0.9349954596541507` exactly.

---

## 5. The overlap score — our helper metric, not a Mem0 score

**This "overlap" number does not come from Mem0 at all.** It is computed entirely inside `experiments/scripts/trace_question.py` as a crude lexical-overlap heuristic used only to pick which stored memories to show as "candidates" for a given evidence turn — Mem0 itself has no concept of "overlap" and never sees or returns this value.

Code (`trace_question.py:90-100`):
```python
def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w for w in words if w not in STOPWORDS]

def overlap_score(evidence_words: list[str], memory_text: str) -> float:
    if not evidence_words:
        return 0.0
    mem_words = set(tokenize(memory_text))
    shared = set(evidence_words) & mem_words
    return len(shared) / len(evidence_words)
```
Called per-candidate at `trace_question.py:153-156`, with `words = evidence_words_by_turn[dia_id]` built by `tokenize(turn["text"])` at `trace_question.py:143`.

Step-by-step recomputation for q0's rank-1 candidate (evidence D1:3 vs. memory id `376d6d0a-...`):

1. Evidence text: `"I went to a LGBTQ support group yesterday and it was so powerful."`
2. Lowercase + regex-tokenize (`[a-z0-9']+`), then drop stopwords (`i`, `to`, `a`, `and`, `it`, `was`, `so` are all in `STOPWORDS`):
   `evidence_words = ["went", "lgbtq", "support", "group", "yesterday", "powerful"]` → **6 words** (list, not deduplicated — `len(evidence_words)` is 6 even though all 6 happen to be distinct here).
3. Memory text: `"Caroline attended an LGBTQ support group on November 9, 2026, and found it to be a powerful experience."`
4. Tokenize + drop stopwords, as a **set**: `mem_words = {"caroline","attended","lgbtq","support","group","november","9","2026","found","powerful","experience"}`.
5. Intersection: `shared = {"lgbtq","support","group","powerful"}` → **4 words**.
6. `overlap = len(shared) / len(evidence_words) = 4 / 6 = 0.6667` → displayed rounded to 2 d.p. as **0.67**, matching `trace_facts/conv0_q0.md` exactly.

Again: this is purely a diagnostic word-overlap ratio written by our own script to help a human find the right stored memory by eye. It has no bearing on Mem0's actual `semantic_score`, `bm25_score`, `entity_boost`, or `combined` score shown alongside it, and Mem0's search/ranking code never computes or uses it.

---

## 6. The logs

Searched `console.log` (41 lines total) and `server.log` (8,424 lines total) for the question text ("LGBTQ support group", "When did Caroline"), the question id ("conv0_q0"), and the rank-1 memory's id (`376d6d0a-101f-40b4-8b9e-8b7911637514`).

- **`console.log`**: contains only tqdm progress-bar lines for ingestion (419 chunks) and questions (152 questions), plus the aggregate per-cutoff metrics table printed by `display_results()` (`run.py:659-669`) and the final "Results saved to: ..." line. **Not recorded in logs** — no per-question text, ids, or search payloads appear anywhere in `console.log`.
- **`server.log`**: contains FastAPI/uvicorn startup lines, PostHog/HF warnings, "BM25 encoder loaded" lines, and one generic `INFO: <client-ip>:<port> - "POST /search HTTP/1.1" 200 OK` line per search request (152 total — one per question in this conv0 run), e.g. line 5889. None of these request-log lines include the query text, the question id, or the memory ids returned, so **it is not possible to isolate which of the 152 generic `POST /search` lines corresponds to conv0_q0 specifically** from `server.log` alone. No `ERROR`, `search() failed`, or `add() failed` lines were found anywhere in `server.log` — no errors were recorded for this run.

Conclusion: beyond confirming that 152 search requests happened and none errored, **nothing specific to conv0_q0 is recorded in either log file.**
