#!/usr/bin/env python3
"""Export one run's memories and entities from Qdrant to a JSON-lines snapshot.

Usage:
    /shared_mnt/loubna/venv-analysis/bin/python experiments/scripts/export_store.py <run_folder>

Read-only: only scroll/count calls are made against Qdrant, nothing is
written, updated or deleted. The run's Mem0 user id is read from
<run_folder>/predicted_*/_ingestion_*.json ("user_id"). Qdrant host/port
come from QDRANT_PORT in experiments/memory-benchmarks/.env (host is always
localhost here); no other variables are read from that file.

Writes, under <run_folder>/store_snapshot/:
    memories.jsonl  - id, data, created_at, user_id (sorted by created_at, then id)
    entities.jsonl  - id, data, entity_type, linked_memory_ids (sorted by data)
    README.md       - export date, collections, user id, record counts
"""

import datetime
import glob
import json
import sys
from pathlib import Path

from qdrant_client import QdrantClient, models

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / "experiments" / "memory-benchmarks" / ".env"
COLLECTIONS = ["memories", "memories_entities"]


def read_qdrant_port() -> int:
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("QDRANT_PORT="):
            return int(line.split("=", 1)[1].strip())
    raise SystemExit(f"QDRANT_PORT not found in {ENV_FILE}")


def find_user_id(run_dir: Path) -> str:
    files = sorted(glob.glob(str(run_dir / "predicted_*" / "_ingestion_*.json")))
    if not files:
        raise SystemExit(f"no predicted_*/_ingestion_*.json found in {run_dir}")
    user_ids = {json.load(open(f))["user_id"] for f in files}
    if len(user_ids) != 1:
        raise SystemExit(f"expected one user_id across ingestion files, found {user_ids}")
    return user_ids.pop()


def scroll_all(client: QdrantClient, collection: str, user_id: str) -> list[dict]:
    flt = models.Filter(
        must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))]
    )
    points = []
    offset = None
    while True:
        batch, offset = client.scroll(
            collection_name=collection,
            scroll_filter=flt,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points.extend(batch)
        if offset is None:
            break
    return points


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <run_folder>")
    run_dir = Path(sys.argv[1])
    user_id = find_user_id(run_dir)
    port = read_qdrant_port()

    client = QdrantClient(host="localhost", port=port)

    memory_points = scroll_all(client, "memories", user_id)
    entity_points = scroll_all(client, "memories_entities", user_id)

    memories = [
        {
            "id": str(p.id),
            "data": p.payload.get("data"),
            "created_at": p.payload.get("created_at"),
            "user_id": p.payload.get("user_id"),
        }
        for p in memory_points
    ]
    memories.sort(key=lambda m: (m["created_at"] or "", m["id"]))

    entities = [
        {
            "id": str(p.id),
            "data": p.payload.get("data"),
            "entity_type": p.payload.get("entity_type"),
            "linked_memory_ids": p.payload.get("linked_memory_ids") or [],
        }
        for p in entity_points
    ]
    entities.sort(key=lambda e: e["data"] or "")

    out_dir = run_dir / "store_snapshot"
    out_dir.mkdir(exist_ok=True)

    with open(out_dir / "memories.jsonl", "w") as f:
        for m in memories:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    with open(out_dir / "entities.jsonl", "w") as f:
        for e in entities:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    export_date = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    readme = f"""# Store snapshot

- Export date (UTC): {export_date}
- Qdrant collections read: {", ".join(COLLECTIONS)}
- User id: {user_id}
- Memories exported: {len(memories)}
- Entities exported: {len(entities)}

Text and links only; no vectors. Read-only export (scroll/count), nothing
in Qdrant was modified.
"""
    (out_dir / "README.md").write_text(readme)

    print(f"user_id: {user_id}")
    print(f"memories: {len(memories)}")
    print(f"entities: {len(entities)}")
    print(f"wrote: {out_dir}")


if __name__ == "__main__":
    main()
