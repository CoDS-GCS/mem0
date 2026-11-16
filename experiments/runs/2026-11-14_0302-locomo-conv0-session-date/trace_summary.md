# Trace summary

- server events: 10091; eval events: 1788
- add requests: 419; search requests: 195
- recorder errors: 0

## Counts per operation
- dedup.summary: 419
- embedder.embed: 614
- embedder.embed_batch: 928
- entity_store.insert: 232
- entity_store.list: 393
- entity_store.search: 215
- entity_store.search_batch: 393
- entity_store.update: 1283
- entry.add.request: 419
- entry.add.response: 419
- entry.search.request: 195
- entry.search.response: 141
- eval:answerer.generate: 608
- eval:judge.generate_structured: 608
- eval:mem0_client.add: 419
- eval:mem0_client.search: 152
- eval:recorder.installed: 1
- history_db.batch_add_history: 393
- history_db.get_last_messages: 419
- history_db.save_messages: 419
- llm.generate_response: 419
- recorder.installed: 1
- scoring.score_and_rank: 141
- spacy.extract_entities: 195
- spacy.extract_entities_batch: 393
- spacy.lemmatize_for_bm25: 966
- vector_store.insert: 393
- vector_store.keyword_search: 141
- vector_store.search: 560

## Totals
- memories stored: 771
- entity mentions found: 2091
- duplicates skipped: 6

## Current-Date leakage check
- extractor Current Date value(s) seen in prompts: ['2026-11-14']
- stored memories mentioning the Current Date or its year (['2026', '2026-11-14']): **0**
