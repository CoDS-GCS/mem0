# Trace points: component boundaries in Mem0 add()/search() and in the LoCoMo benchmark

Read-only map for the recorder (STEP 1). It lists every place data crosses between components,
the **object/method to wrap**, and what crosses. The recorder wraps **by name** (class/instance
method or module-level function), so the exact line numbers below are only for reading the code —
they do not affect the wrappers.

Line numbers are for the current tree = **Mem0 v2.2.1** (`mem0/` is identical to `94c3fe9`).
On **`code/session-date`** the same objects/methods exist with identical signatures; only line
numbers in `mem0/memory/main.py` shift (the branch inserts `_session_datetime_from_timestamp`
and threads a `session_dt`/`timestamp=` argument). Where the add path changed, the session-date
delta is noted. Because every wrap target is name-based, both versions are covered unchanged.

## Which code actually runs

- **Server (in-process with `Memory`)**: the benchmark Mem0 server (`docker/mem0/main.py`) builds a
  single `mem0.Memory` via `Memory.from_config` and calls the **sync** `mem.add(...)` / `mem.search(...)`
  from FastAPI endpoints `add_memories` / `search_memories`. → We trace the **sync** `Memory` path only.
  (`AsyncMemory` is never used by this server.)
- **Benchmark client (separate process)**: `benchmarks/locomo/run.py` talks to the server over HTTP via
  the **async** `Mem0Client` (aiohttp), and calls the answerer/judge via the async `LLMClient` (OpenAI SDK).

---

## A. Mem0 server side — `Memory.add()` (sync)

Entry: `mem0/memory/main.py:760` `Memory.add(...)` → `:881` `_add_to_vector_store(...)`.
(session-date: `add` ~`:760`→ unchanged name; `_add_to_vector_store` gains `session_dt=None`.)

| # | Component | Object / method to wrap | File:line (v2.2.1) | What crosses |
|---|-----------|-------------------------|--------------------|--------------|
| A0 | **Entry point** | `Memory.add` | `main.py:760` | request: `messages`, `user_id`/filters, `metadata`, `timestamp` (session-date). Emit request event, open a `request_id`. |
| A1 | Embedder (query embed for existing-memory retrieval) | `self.embedding_model.embed(text,"search")` | `main.py:927` | input text (parsed messages) → dense vector (record **length**, not values). |
| A2 | Vector store — memories collection (existing retrieval) | `self.vector_store.search(query,vectors,top_k,filters)` | `main.py:928` | top-10 existing memories (ids + payloads). |
| A3 | **Extraction prompt build** | `generate_additive_extraction_prompt(...)` (imported into `main`) | call `main.py:950`; def `configs/prompts.py:1016` | the exact user prompt string (incl. `## Observation Date` / `## Current Date`). |
| A4 | **Extraction LLM** | `self.llm.generate_response(messages,response_format=...)` | call `main.py:958`; def `llms/openai.py:85` | system+user prompt in, raw completion out, **token usage** (`resp.usage`). |
| A5 | Fact parse (CPU, no boundary) | — (inline `json.loads`) | `main.py:974-986` | facts list parsed from the raw response (record parsed facts). |
| A6 | Embedder (batch embed extracted facts) | `self.embedding_model.embed_batch(texts,"add")` (+ `embed` fallback) | `main.py:996` / `1003` | fact texts → vectors (record **lengths**). |
| A7 | Hash dedup (CPU) | — (inline `hashlib.md5`) | `main.py:1022-1026` | duplicates skipped by hash (record skipped text + hash). |
| A8 | BM25 lemmatization (spaCy) | `lemmatize_for_bm25(text)` (imported into `main`) | call `main.py:1028`; def `utils/lemmatization.py:22` | fact text → `text_lemmatized`. |
| A9 | Vector store — memories collection (persist) | `self.vector_store.insert(vectors,ids,payloads)` | `main.py:1057` / fallback `1067` | each stored memory: id, payload (`data`, `text_lemmatized`, `hash`, `created_at`, `updated_at`, metadata); vector → **length**. |
| A10 | **History DB (SQLite)** | `self.db.batch_add_history(records)` / `add_history(...)` | call `main.py:1091` / `1096`; def `memory/storage.py:193` / `150` | ADD history rows (`memory_id`, `new_memory`, `event`, `created_at`). |
| A11 | **spaCy entity extraction** | `extract_entities_batch(texts)` (imported into `main`) | call `main.py:1103`; def `utils/entity_extraction.py:761` | per-memory entities `(text, type)`. |
| A12 | Embedder (batch embed entities) | `self.embedding_model.embed_batch(entity_texts,"add")` (+ `embed` fallback) | `main.py:1130` / `1136` | entity texts → vectors (record **lengths**). |
| A13 | Entity store — `memories_entities` collection (lookup) | `self.entity_store.search_batch(queries,vectors_list,top_k,filters)`; also `_existing_entities_by_text` → `self.entity_store.list(...)` | `main.py:1152`; `list` `:589` | existing-entity matches + similarity score (`match.score`). |
| A14 | Entity store — update (merge) | `self.entity_store.update(vector_id,vector,payload)` | `main.py:1175` | matched/merged entity: new `linked_memory_ids`, similarity, match id. |
| A15 | Entity store — insert (new) | `self.entity_store.insert(vectors,ids,payloads)` | `main.py:1196` | new entity: id, `data`, `entity_type`, `linked_memory_ids`; vector → **length**. |
| A16 | History DB — save raw messages | `self.db.save_messages(messages,session_scope)` | call `main.py:1207` / (also `990`,`1044`); def `storage.py:257` | conversation messages saved for the session. |

Notes:
- `self.entity_store` (`main.py:559` property) is the **same class** as `self.vector_store` (Qdrant) but a
  **separate collection** `{collection}_entities` (`_entity_collection_name` `main.py:422`), created lazily.
  Wrapping the Qdrant **class** methods covers both; the collection is told apart by `self.collection_name`.
- BM25 **sparse encoder** (`fastembed Qdrant/bm25`) lives inside Qdrant (`qdrant.py:93 _get_bm25_encoder`,
  `:111 _encode_bm25`), used only inside `insert`/`keyword_search`. Its boundary for tracing is those methods.

## B. Mem0 server side — `Memory.search()` (sync)

Entry: `mem0/memory/main.py:1393` `Memory.search(...)` → `:1642` `_search_vector_store(...)`.
Server always calls with `explain=True` (`docker/mem0/main.py:238`).

| # | Component | Object / method to wrap | File:line | What crosses |
|---|-----------|-------------------------|-----------|--------------|
| B0 | **Entry point** | `Memory.search` | `main.py:1393` | query, filters (`user_id`), `top_k`, `threshold`, `explain`. Open `request_id`; record server wall-time. |
| B1 | BM25 lemmatization (spaCy) | `lemmatize_for_bm25(query)` | call `main.py:1648` | query → `query_lemmatized`. |
| B2 | spaCy entity extraction (query) | `extract_entities(query)` | call `main.py:1649`; def `utils/entity_extraction.py:758` | query entities `(text,type)`. |
| B3 | Embedder (query embed) | `self.embedding_model.embed(query,"search")` | `main.py:1652` | query → dense vector (**length**). |
| B4 | Vector store — semantic search (over-fetch) | `self.vector_store.search(query,vectors,top_k=max(limit*4,60),filters)` | `main.py:1656` | candidate ids + **semantic score** (`mem.score`) + payloads. |
| B5 | Vector store — keyword/BM25 search | `self.vector_store.keyword_search(query_lemmatized,top_k,filters)` | call `main.py:1661`; def `qdrant.py:454` | candidate ids + raw BM25 score → normalized (`normalize_bm25`, `scoring.py`). |
| B6 | Entity boost (entity store) | `self._compute_entity_boosts(...)` → `self.entity_store.search(...)` | `main.py:1678` → `:1788` | per-memory entity-boost contributions. |
| B7 | **Scoring + threshold + rank** | `score_and_rank(semantic_results,bm25_scores,entity_boosts,threshold,top_k,explain)` (imported into `main`) | call `main.py:1694`; def `utils/scoring.py` | per-candidate semantic / bm25 / entity_boost / **combined** score, threshold drops, final ranked list. |
| B8 | Expired filter (CPU) | — (`_payload_is_expired`) | `main.py:1684` | candidates dropped as expired. |

The three sub-scores + combined score are exactly what `explain=True` puts in `score_details`
(`main.py:1740`), which the server renames to `score_breakdown` (`docker/mem0/main.py:245-252`).
So wrapping `score_and_rank` captures the full candidate pool **including threshold drops** (which
never reach the HTTP response).

## C. Entry-point summary (what opens a `request_id`)

- `Memory.add` (`main.py:760`), `Memory.search` (`main.py:1393`) — one HTTP request each. FastAPI runs these
  sync endpoints in a worker thread, so a **thread-local** request context (request_id, endpoint, user_id,
  seq counter) set at these entry points is seen by every nested component wrapper in the same call.

---

## D. Benchmark side — `benchmarks/locomo/`

### D1. Where /add and /search are called
- **/add**: `run.py:340` `await mem0.add(messages, user_id, timestamp=session_epoch)` inside
  `ingest_conversation` (`run.py:238`). Client: `Mem0Client.add` → `_add_oss` POST `/memories`
  (`mem0_client.py:117` / `:135`, POST `:159`). **No client-side add latency is measured today.**
- **/search**: `run.py:417` `await mem0.search(question, user_id, top_k=top_k, score_debug=...)` inside
  `process_question` (`run.py:389`). Client: `Mem0Client.search` → `_search_oss` POST `/search`
  (`mem0_client.py:241` / `:255`, POST `:269`). **Client search latency IS measured** at `run.py:416-418`
  and saved as `retrieval.search_latency_ms`.

### D2. Where the answer prompt is built / answerer called
- Prompt: `run.py:465` `get_answer_generation_prompt(question, sliced, reference_date=..., user_profile=...)`
  (def `benchmarks/locomo/prompts.py:143`). `sliced = formatted[:c]` are the memories **as the answerer sees
  them**, each rendered `(<human date of created_at>) <memory>` (`prompts.py:172-179`).
- Answerer: `run.py:466` `await answerer.generate(system="", user=gen_prompt)`
  (def `common/llm_client.py:136` → `_generate_openai:158`). **Returns only the text**; `resp.usage`
  (tokens) is read at `llm_client.py:176` but **discarded** — to capture answerer tokens we must wrap the
  inner `answerer._client.chat.completions.create` (`llm_client.py:168`).
- One answer call **per cutoff**: `for c in cutoffs` (`run.py:460`), awaited sequentially within a question.

### D3. Where the judge is called
- Judge prompt: `run.py:471-474` `get_judge_prompt[_with_evidence](...)` (def `prompts.py`).
- Judge: `run.py:476` `await judge_llm.generate_structured(system=JUDGE_SYSTEM_PROMPT, user=judge_prompt)`
  (def `llm_client.py:225`). Verdict parsed at `run.py:480-482` (`label == "CORRECT"`).
- `answerer` (`run.py:757`) and `judge_llm` (`run.py:759`) are **separate `LLMClient` instances** (even when
  the model string is the same), so wrapping `answerer._client` isolates answerer tokens from the judge.

### D4. Wrap targets (eval side; async, correlate via `contextvars` = task-local)
- `Mem0Client.add` — client add request + latency (sent → response).
- `Mem0Client.search` — client search request/response + latency (reuse `run.py` number; also record).
- `process_question` (`run.py:389`) — set a task-local {question_id, cutoffs, call index} so answer/judge
  events can be labelled with their `question_id` and cutoff.
- `answerer.generate` — exact prompt (`user`), raw answer, latency; tokens from the inner-client wrapper.
- `answerer._client.chat.completions.create` — `resp.usage` (prompt/completion/total tokens) for the answerer.
- `judge_llm.generate_structured` — exact judge prompt, raw response, parsed verdict. (No judge tokens.)

### D5. What the result files already save (`locomo_results_*.json`, per question)
From `process_question` (`run.py:422-497`) + `compute_locomo_metrics`:
- `retrieval.search_query`, `retrieval.search_results` (each: `memory`, `score`, `id`, `created_at`,
  `updated_at`, and `score_debug` = {combined, semantic, bm25, entity_boost} — OSS always returns it because
  the server forces `explain=True`), `retrieval.search_latency_ms` (**client search latency**),
  `retrieval.total_results`, optional `retrieval.query_debug`.
- `cutoff_results[label]`: `judgment` (CORRECT/WRONG), `score`, `generated_answer`, `memories_evaluated`,
  `reason` (judge reasoning). Top-level: `question_id`, `category`, `question`, `ground_truth_answer`,
  `evidence`, `user_id`, `reference_date`, optional `user_profile`. Plus `metrics_by_cutoff`.
- **Not saved anywhere today**: the answer prompt, the judge prompt, **answerer token counts**,
  **answer latency**, **add latency**, and the **extraction prompt / extraction tokens** (server side).
  These are exactly what the recorder must add.

---

## E. Recorder wrap-target cheat-sheet (used by STEP 2 / STEP 3)

**Server (`experiments/tracing/mem0_trace.py`, loaded by `docker/mem0/main.py` when `MEM0_TRACE=1`):**
patch, by name, on the running `Memory` instance / classes —
`Memory.add`, `Memory.search` (entry + request_id);
`memory.llm.generate_response`;
`memory.embedding_model.embed`, `.embed_batch`;
Qdrant class `insert`, `search`, `keyword_search`, `search_batch`, `list`, `update`, `delete`, `get`
(covers both `memories` and `memories_entities`, told apart by `collection_name`);
`memory.db.add_history`, `.batch_add_history`, `.save_messages`, `.get_last_messages`;
module fns in `mem0.memory.main`: `generate_additive_extraction_prompt`, `lemmatize_for_bm25`,
`extract_entities`, `extract_entities_batch`, `score_and_rank`.

**Eval (`experiments/tracing/eval_trace.py`, loaded by `run.py` when `MEM0_TRACE=1`):**
`Mem0Client.add`, `Mem0Client.search`, `run.process_question`,
`answerer.generate`, `answerer._client.chat.completions.create`, `judge_llm.generate_structured`.

Every event is one JSON line: `time`, `request_id`, `seq`, `endpoint` (add/search/eval), `user_id`,
`component`, `operation`, `inputs`, `outputs`, `duration_ms`. Vectors are replaced by their length.
No API keys, headers, or environment are ever recorded.
