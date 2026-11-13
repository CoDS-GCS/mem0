"""
Server-side operation recorder for the Mem0 OSS benchmark server (STEP 2).

Loaded by ``docker/mem0/main.py`` at startup **only when ``MEM0_TRACE=1``**. It monkeypatches
Mem0's component boundaries at runtime (no edits to Mem0 files) and writes one JSON object per
line describing every ADD and SEARCH operation. See ``experiments/notes/trace_points.md`` for the
boundary map this implements.

Guarantees (contract):
  * Each wrapper calls the original exactly once and returns its result unchanged.
  * Exceptions from the original propagate unchanged.
  * A failure *inside the recorder* never breaks the call: it is caught and counted
    (emitted as a ``{"component":"recorder","operation":"error"}`` line, best-effort).
  * Vectors are never stored as values, only as their length.
  * API keys, request headers and environment variables are never recorded.

Event schema (one JSON object per line):
  time, request_id, seq, endpoint (add|search), user_id, component, operation,
  inputs, outputs, duration_ms
"""

from __future__ import annotations

import functools
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Writer + per-request (thread-local) context
# ---------------------------------------------------------------------------

_LOCK = threading.Lock()
_CTX = threading.local()
_STATE = {"fh": None, "path": None, "events": 0, "errors": 0, "installed": False}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trace_path() -> str:
    p = os.getenv("MEM0_TRACE_FILE")
    if p:
        return p
    d = os.getenv("MEM0_TRACE_DIR", "/app/trace")
    return os.path.join(d, "mem0_trace.jsonl")


def _open_writer() -> None:
    path = _trace_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Line-buffered append so a crash still leaves complete lines on disk.
    _STATE["fh"] = open(path, "a", buffering=1, encoding="utf-8")
    _STATE["path"] = path


def _write(obj: dict) -> None:
    with _LOCK:
        fh = _STATE["fh"]
        if fh is None:
            return
        fh.write(json.dumps(obj, default=str, ensure_ascii=False) + "\n")
        _STATE["events"] += 1


def _count_error(where: str = "") -> None:
    """Record a recorder-internal failure without ever raising."""
    _STATE["errors"] += 1
    try:
        with _LOCK:
            fh = _STATE["fh"]
            if fh is not None:
                fh.write(json.dumps({
                    "time": _now_iso(),
                    "request_id": getattr(_CTX, "request_id", None),
                    "component": "recorder",
                    "operation": "error",
                    "where": where,
                }) + "\n")
    except Exception:
        pass  # give up silently; the real call is unaffected


def _ctx_get(name, default=None):
    return getattr(_CTX, name, default)


def _new_request(endpoint: str, user_id) -> None:
    _CTX.request_id = uuid.uuid4().hex
    _CTX.endpoint = endpoint
    _CTX.user_id = user_id
    _CTX.seq = 0
    # per-request scratch for derived dedup/summary events
    _CTX.parsed_facts = []
    _CTX.inserted = []
    _CTX.existing_hashes = []
    _CTX.llm_usage = None


def _emit(component: str, operation: str, inputs=None, outputs=None, duration_ms=None) -> None:
    try:
        seq = getattr(_CTX, "seq", 0)
        _CTX.seq = seq + 1
        _write({
            "time": _now_iso(),
            "request_id": getattr(_CTX, "request_id", None),
            "seq": seq,
            "endpoint": getattr(_CTX, "endpoint", None),
            "user_id": getattr(_CTX, "user_id", None),
            "component": component,
            "operation": operation,
            "inputs": inputs,
            "outputs": outputs,
            "duration_ms": None if duration_ms is None else round(duration_ms, 3),
        })
    except Exception:
        _count_error(f"{component}.{operation}")


# ---------------------------------------------------------------------------
# Value summarisers (keep vectors out, keep payloads/text in)
# ---------------------------------------------------------------------------

def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_vector(x) -> bool:
    return isinstance(x, (list, tuple)) and len(x) > 0 and _is_number(x[0])


def _vec(x):
    if _is_vector(x):
        return {"_vec_len": len(x)}
    return x


def _vecs(xs):
    if isinstance(xs, (list, tuple)):
        n = len(xs)
        dim = len(xs[0]) if (n and _is_vector(xs[0])) else None
        return {"_n_vecs": n, "_vec_len": dim}
    return _vec(xs)


def _res_obj(r):
    """Summarise a vector-store result object (qdrant OutputData) to plain dict."""
    try:
        rid = getattr(r, "id", None) if not isinstance(r, dict) else r.get("id")
        score = getattr(r, "score", None) if not isinstance(r, dict) else r.get("score")
        payload = getattr(r, "payload", None) if not isinstance(r, dict) else r.get("payload")
        return {"id": str(rid) if rid is not None else None,
                "score": score,
                "payload": payload}
    except Exception:
        return {"id": None, "score": None, "payload": None}


def _collection_of(store) -> str:
    return getattr(store, "collection_name", "") or ""


def _store_component(store) -> str:
    return "entity_store" if _collection_of(store).endswith("entities") else "vector_store"


# ---------------------------------------------------------------------------
# Generic wrapper factory
# ---------------------------------------------------------------------------

def _wrap(orig, recorder):
    """Return a wrapper that times ``orig``, calls it once, and records via ``recorder``.

    ``recorder(args, kwargs, result, duration_ms, error)`` must never raise (it is called
    inside try/except here regardless). The original's result/exception is passed through.
    """
    @functools.wraps(orig)
    def inner(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            result = orig(*args, **kwargs)
        except Exception as exc:  # original failed: record (safe) then re-raise unchanged
            try:
                recorder(args, kwargs, None, (time.perf_counter() - t0) * 1000, exc)
            except Exception:
                _count_error("wrap/except")
            raise
        dur = (time.perf_counter() - t0) * 1000
        try:
            recorder(args, kwargs, result, dur, None)
        except Exception:
            _count_error("wrap/record")
        return result
    return inner


# ---------------------------------------------------------------------------
# install(): monkeypatch the running Memory instance + classes + module fns
# ---------------------------------------------------------------------------

def install(memory) -> bool:
    """Patch all boundaries around the given ``Memory`` instance. Returns True on success."""
    if _STATE["installed"]:
        return True
    try:
        _open_writer()
    except Exception:
        _count_error("open_writer")
        return False

    import mem0.memory.main as mm

    # -- Entry points (instance-level): open a request_id, record request/response -----------
    _orig_add = memory.add
    _orig_search = memory.search

    def add_entry(messages, *args, **kwargs):
        _new_request("add", kwargs.get("user_id"))
        _emit("entry", "add.request", inputs={
            "messages": messages,
            "timestamp": kwargs.get("timestamp"),
            "user_id": kwargs.get("user_id"),
            "agent_id": kwargs.get("agent_id"),
            "run_id": kwargs.get("run_id"),
            "metadata": kwargs.get("metadata"),
        })
        t0 = time.perf_counter()
        result = _orig_add(messages, *args, **kwargs)
        dur = (time.perf_counter() - t0) * 1000
        try:
            _emit_dedup_summary()
            res_list = result.get("results", result) if isinstance(result, dict) else result
            _emit("entry", "add.response", outputs={"results": res_list}, duration_ms=dur)
        except Exception:
            _count_error("add.response")
        return result

    def search_entry(query, *args, **kwargs):
        filters = kwargs.get("filters") or {}
        _new_request("search", filters.get("user_id"))
        _emit("entry", "search.request", inputs={
            "query": query,
            "top_k": kwargs.get("top_k"),
            "threshold": kwargs.get("threshold"),
            "explain": kwargs.get("explain"),
            "filters": filters,
        })
        t0 = time.perf_counter()
        result = _orig_search(query, *args, **kwargs)
        dur = (time.perf_counter() - t0) * 1000
        try:
            res_list = result.get("results", result) if isinstance(result, dict) else result
            _emit("entry", "search.response",
                  outputs={"n_results": len(res_list) if res_list is not None else 0,
                           "ids": [r.get("id") for r in res_list] if res_list else []},
                  duration_ms=dur)
        except Exception:
            _count_error("search.response")
        return result

    memory.add = add_entry
    memory.search = search_entry

    # -- Extraction LLM: generate_response (prompt + raw response + parsed facts) -------------
    def rec_llm(args, kwargs, result, dur, exc):
        messages = args[1] if len(args) > 1 else kwargs.get("messages")
        parsed = _parse_facts(result)
        try:
            _CTX.parsed_facts = parsed
        except Exception:
            pass
        _emit("llm", "generate_response",
              inputs={"messages": messages, "response_format": kwargs.get("response_format")},
              outputs={"raw": result, "parsed_facts": parsed,
                       "token_usage": getattr(_CTX, "llm_usage", None), "error": bool(exc)},
              duration_ms=dur)
    memory.llm.generate_response = _wrap(memory.llm.generate_response, rec_llm)

    # -- Extraction LLM inner client: capture token usage (no prompt/keys) --------------------
    try:
        _comp = memory.llm.client.chat.completions
        _orig_create = _comp.create

        @functools.wraps(_orig_create)
        def create_wrap(*a, **k):
            resp = _orig_create(*a, **k)
            try:
                _CTX.llm_usage = _usage(resp)
            except Exception:
                _count_error("llm.usage")
            return resp
        _comp.create = create_wrap
    except Exception:
        _count_error("llm.client.patch")

    # -- Embedder ------------------------------------------------------------------------------
    def rec_embed(args, kwargs, result, dur, exc):
        text = args[1] if len(args) > 1 else kwargs.get("text")
        action = args[2] if len(args) > 2 else kwargs.get("memory_action")
        _emit("embedder", "embed",
              inputs={"text": text, "action": action},
              outputs={"vector": _vec(result), "error": bool(exc)}, duration_ms=dur)

    def rec_embed_batch(args, kwargs, result, dur, exc):
        texts = args[1] if len(args) > 1 else kwargs.get("texts")
        action = args[2] if len(args) > 2 else kwargs.get("memory_action")
        _emit("embedder", "embed_batch",
              inputs={"texts": texts, "action": action, "n": len(texts) if texts else 0},
              outputs={"vectors": _vecs(result), "error": bool(exc)}, duration_ms=dur)
    memory.embedding_model.embed = _wrap(memory.embedding_model.embed, rec_embed)
    memory.embedding_model.embed_batch = _wrap(memory.embedding_model.embed_batch, rec_embed_batch)

    # -- Vector store + entity store (class-level: covers both collections) -------------------
    vs_cls = type(memory.vector_store)
    _patch_store_class(vs_cls)

    # -- History DB (instance-level) ----------------------------------------------------------
    def rec_batch_hist(args, kwargs, result, dur, exc):
        records = args[1] if len(args) > 1 else kwargs.get("records")
        _emit("history_db", "batch_add_history", inputs={"records": records}, duration_ms=dur)

    def rec_add_hist(args, kwargs, result, dur, exc):
        _emit("history_db", "add_history",
              inputs={"memory_id": _arg(args, kwargs, 1, "memory_id"),
                      "event": _arg(args, kwargs, 4, "event"),
                      "created_at": kwargs.get("created_at")}, duration_ms=dur)

    def rec_save_msgs(args, kwargs, result, dur, exc):
        msgs = args[1] if len(args) > 1 else kwargs.get("messages")
        _emit("history_db", "save_messages",
              inputs={"n_messages": len(msgs) if msgs else 0,
                      "session_scope": _arg(args, kwargs, 2, "session_scope")}, duration_ms=dur)

    def rec_get_last(args, kwargs, result, dur, exc):
        _emit("history_db", "get_last_messages",
              inputs={"session_scope": _arg(args, kwargs, 1, "session_scope"),
                      "limit": kwargs.get("limit")},
              outputs={"n": len(result) if result else 0}, duration_ms=dur)
    memory.db.batch_add_history = _wrap(memory.db.batch_add_history, rec_batch_hist)
    memory.db.add_history = _wrap(memory.db.add_history, rec_add_hist)
    memory.db.save_messages = _wrap(memory.db.save_messages, rec_save_msgs)
    memory.db.get_last_messages = _wrap(memory.db.get_last_messages, rec_get_last)

    # -- Module-level functions in mem0.memory.main -------------------------------------------
    def rec_lemma(args, kwargs, result, dur, exc):
        _emit("spacy", "lemmatize_for_bm25",
              inputs={"text": _arg(args, kwargs, 0, "text")},
              outputs={"lemmatized": result}, duration_ms=dur)

    def rec_entities(args, kwargs, result, dur, exc):
        _emit("spacy", "extract_entities",
              inputs={"text": _arg(args, kwargs, 0, "text")},
              outputs={"entities": result}, duration_ms=dur)

    def rec_entities_batch(args, kwargs, result, dur, exc):
        _emit("spacy", "extract_entities_batch",
              inputs={"n_texts": len(_arg(args, kwargs, 0, "texts") or [])},
              outputs={"entities": result}, duration_ms=dur)

    def rec_score(args, kwargs, result, dur, exc):
        sem = kwargs.get("semantic_results", args[0] if args else None)
        _emit("scoring", "score_and_rank",
              inputs={
                  "semantic_candidates": [{"id": str(_res_obj(c)["id"]), "semantic": _res_obj(c)["score"]}
                                          for c in (sem or [])],
                  "bm25_scores": kwargs.get("bm25_scores"),
                  "entity_boosts": kwargs.get("entity_boosts"),
                  "threshold": kwargs.get("threshold"),
                  "top_k": kwargs.get("top_k"),
              },
              outputs={"ranked": [{"id": str(s.get("id")), "score": s.get("score"),
                                   "score_details": s.get("score_details")} for s in (result or [])]},
              duration_ms=dur)

    mm.lemmatize_for_bm25 = _wrap(mm.lemmatize_for_bm25, rec_lemma)
    mm.extract_entities = _wrap(mm.extract_entities, rec_entities)
    mm.extract_entities_batch = _wrap(mm.extract_entities_batch, rec_entities_batch)
    mm.score_and_rank = _wrap(mm.score_and_rank, rec_score)

    _STATE["installed"] = True
    _emit("recorder", "installed", outputs={"path": _STATE["path"]})
    return True


# ---------------------------------------------------------------------------
# Vector store class patch (one wrapper per method; tags collection via self)
# ---------------------------------------------------------------------------

def _patch_store_class(cls) -> None:
    if getattr(cls, "_mem0_traced", False):
        return

    def rec_insert(args, kwargs, result, dur, exc):
        self = args[0]
        comp = _store_component(self)
        vectors = _arg(args, kwargs, 1, "vectors")
        ids = _arg(args, kwargs, 3, "ids")
        payloads = _arg(args, kwargs, 2, "payloads")
        if comp == "vector_store" and _ctx_get("endpoint") == "add":
            try:
                for p in (payloads or []):
                    h = p.get("hash") if isinstance(p, dict) else None
                    if h:
                        _CTX.inserted.append({"hash": h, "text": p.get("data")})
            except Exception:
                _count_error("track.inserted")
        _emit(comp, "insert",
              inputs={"ids": ids, "payloads": payloads, "vectors": _vecs(vectors),
                      "collection": _collection_of(self)}, duration_ms=dur)

    def rec_search(args, kwargs, result, dur, exc):
        self = args[0]
        comp = _store_component(self)
        q = _arg(args, kwargs, 1, "query")
        summ = [{"id": str(_res_obj(r)["id"]), "score": _res_obj(r)["score"],
                 "hash": (_res_obj(r)["payload"] or {}).get("hash")} for r in (result or [])]
        if comp == "vector_store" and _ctx_get("endpoint") == "add":
            try:
                _CTX.existing_hashes = [s["hash"] for s in summ if s.get("hash")]
            except Exception:
                _count_error("track.existing")
        _emit(comp, "search",
              inputs={"query": q, "top_k": _arg(args, kwargs, 3, "top_k"),
                      "filters": _arg(args, kwargs, 4, "filters"),
                      "collection": _collection_of(self)},
              outputs={"results": summ}, duration_ms=dur)

    def rec_keyword(args, kwargs, result, dur, exc):
        self = args[0]
        summ = [{"id": str(_res_obj(r)["id"]), "score": _res_obj(r)["score"]} for r in (result or [])]
        _emit(_store_component(self), "keyword_search",
              inputs={"query": _arg(args, kwargs, 1, "query"), "top_k": _arg(args, kwargs, 2, "top_k"),
                      "collection": _collection_of(self)},
              outputs={"results": summ, "supported": result is not None}, duration_ms=dur)

    def rec_search_batch(args, kwargs, result, dur, exc):
        self = args[0]
        queries = _arg(args, kwargs, 1, "queries")
        out = []
        for per_query in (result or []):
            out.append([{"id": str(_res_obj(r)["id"]), "score": _res_obj(r)["score"],
                         "data": (_res_obj(r)["payload"] or {}).get("data"),
                         "linked_memory_ids": (_res_obj(r)["payload"] or {}).get("linked_memory_ids")}
                        for r in (per_query or [])])
        _emit(_store_component(self), "search_batch",
              inputs={"queries": queries, "top_k": _arg(args, kwargs, 3, "top_k"),
                      "collection": _collection_of(self)},
              outputs={"results": out}, duration_ms=dur)

    def rec_update(args, kwargs, result, dur, exc):
        self = args[0]
        _emit(_store_component(self), "update",
              inputs={"vector_id": _arg(args, kwargs, 1, "vector_id"),
                      "payload": _arg(args, kwargs, 3, "payload"),
                      "collection": _collection_of(self)}, duration_ms=dur)

    def rec_delete(args, kwargs, result, dur, exc):
        self = args[0]
        _emit(_store_component(self), "delete",
              inputs={"vector_id": _arg(args, kwargs, 1, "vector_id"),
                      "collection": _collection_of(self)}, duration_ms=dur)

    def rec_list(args, kwargs, result, dur, exc):
        self = args[0]
        _emit(_store_component(self), "list",
              inputs={"filters": kwargs.get("filters"), "top_k": kwargs.get("top_k"),
                      "collection": _collection_of(self)},
              outputs={"n": _list_len(result)}, duration_ms=dur)

    for name, rec in (("insert", rec_insert), ("search", rec_search),
                      ("keyword_search", rec_keyword), ("search_batch", rec_search_batch),
                      ("update", rec_update), ("delete", rec_delete), ("list", rec_list)):
        if hasattr(cls, name):
            setattr(cls, name, _wrap(getattr(cls, name), rec))
    cls._mem0_traced = True


# ---------------------------------------------------------------------------
# Derived events + small helpers
# ---------------------------------------------------------------------------

def _emit_dedup_summary() -> None:
    """At end of add(): classify parsed facts into stored vs skipped-by-hash."""
    parsed = getattr(_CTX, "parsed_facts", []) or []
    inserted = getattr(_CTX, "inserted", []) or []
    existing = set(getattr(_CTX, "existing_hashes", []) or [])
    inserted_hashes = {i["hash"] for i in inserted if i.get("hash")}
    skipped = []
    seen = set()
    for f in parsed:
        h = f.get("hash")
        if h in inserted_hashes:
            continue
        reason = "duplicate_of_existing" if h in existing else ("duplicate_in_batch" if h in seen else "not_stored")
        skipped.append({"text": f.get("text"), "hash": h, "reason": reason})
        seen.add(h)
    _emit("dedup", "summary",
          outputs={"n_parsed": len(parsed), "n_stored": len(inserted),
                   "n_skipped": len(skipped), "skipped": skipped})


def _parse_facts(raw):
    """Deterministically parse facts from the extraction LLM's raw response (best-effort)."""
    import hashlib
    import re
    if not raw or not isinstance(raw, str):
        return []
    text = raw.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        data = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except Exception:
            return []
    facts = []
    for item in (data.get("memory", []) if isinstance(data, dict) else []):
        t = item.get("text") if isinstance(item, dict) else None
        if not t:
            continue
        facts.append({"text": t, "hash": hashlib.md5(t.encode()).hexdigest(),
                      "attributed_to": item.get("attributed_to") if isinstance(item, dict) else None})
    return facts


def _usage(resp):
    u = getattr(resp, "usage", None)
    if u is None:
        return None
    return {"prompt_tokens": getattr(u, "prompt_tokens", None),
            "completion_tokens": getattr(u, "completion_tokens", None),
            "total_tokens": getattr(u, "total_tokens", None)}


def _arg(args, kwargs, pos, name, default=None):
    if name in kwargs:
        return kwargs[name]
    if len(args) > pos:
        return args[pos]
    return default


def _list_len(result):
    try:
        if result is None:
            return 0
        if isinstance(result, tuple) and result and isinstance(result[0], list):
            return len(result[0])
        return len(result)
    except Exception:
        return None


def stats() -> dict:
    return {"path": _STATE["path"], "events": _STATE["events"], "errors": _STATE["errors"],
            "installed": _STATE["installed"]}
