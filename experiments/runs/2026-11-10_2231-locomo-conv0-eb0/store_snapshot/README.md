# Store snapshot

- Export date (UTC): 2026-11-11T16:57:50Z
- Qdrant collections read: memories, memories_entities
- User id: locomo_0_001bd360
- Memories exported: 770
- Entities exported: 383

## memories.jsonl fields

- id: the memory's point id in the "memories" Qdrant collection
- data: the fact's text, as stored by Mem0
- text_lemmatized: the fact's words in base form, used for BM25 keyword search
- created_at: timestamp the memory was first written
- updated_at: timestamp the memory was last updated (Mem0 v2 only adds, so this equals created_at)
- hash: Mem0's content hash of the fact text
- user_id: the Mem0 user id the memory belongs to
- attributed_to: who/what the fact is attributed to, only present when Mem0 set it
- embedding_dims: length of the dense embedding vector
- bm25_entries: number of entries in the sparse "bm25" vector, or null if the point has no bm25 vector

## entities.jsonl fields

- id: the entity's point id in the "memories_entities" Qdrant collection
- data: the entity's name/label
- entity_type: the entity's type as classified by Mem0
- linked_memory_ids: ids of memories (from the "memories" collection) linked to this entity

No vector values are written, only counts/lengths derived from them.
Read-only export (scroll/count), nothing in Qdrant was modified.
