"""
Eval-side operation recorder for the LoCoMo benchmark (STEP 3).

Loaded by ``benchmarks/locomo/run.py`` **only when ``MEM0_TRACE=1``**. It wraps the benchmark's
own calls at runtime (no logic rewrite) and writes one JSON object per line to
``<output_dir>/eval_trace.jsonl``. Together with the server-side ``mem0_trace.jsonl`` this holds
the whole evaluation stage: client add/search timing, the exact answer prompt + answer + answerer
tokens + latency, and the exact judge prompt + verdict.

Contract (same as the server recorder):
  * wrappers call the original once, return/raise unchanged;
  * recorder-internal failures are caught and counted, never breaking the call;
  * no API keys / headers / environment are ever written.

The benchmark runs single-threaded asyncio, so per-question correlation uses ``contextvars``
(task-local, copied per ``asyncio`` task). The answerer's token usage is captured by wrapping its
inner OpenAI client (``answerer._client.chat.completions.create``); the judge's client is left
untouched, so judge tokens are never recorded (by design).

Event schema: time, request_id, seq, endpoint="eval", user_id, component, operation,
inputs, outputs, duration_ms.
"""

from __future__ import annotations

import contextvars
import functools
import hashlib
import json
import os
import time
from datetime import datetime, timezone

_STATE = {"fh": None, "path": None, "events": 0, "errors": 0, "installed": False}
_SEQ = {"n": 0}

# per-task question context: {"question_id","category","cutoffs","answer_i","judge_i","user_id"}
_QCTX: contextvars.ContextVar = contextvars.ContextVar("mem0_eval_qctx", default=None)
# per-task sink the answerer.generate wrapper opens so the inner create wrapper can drop usage in
_USAGE: contextvars.ContextVar = contextvars.ContextVar("mem0_eval_usage", default=None)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _open_writer(output_dir: str) -> None:
    path = os.getenv("MEM0_EVAL_TRACE_FILE") or os.path.join(output_dir, "eval_trace.jsonl")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    _STATE["fh"] = open(path, "a", buffering=1, encoding="utf-8")
    _STATE["path"] = path


def _write(obj: dict) -> None:
    fh = _STATE["fh"]
    if fh is None:
        return
    fh.write(json.dumps(obj, default=str, ensure_ascii=False) + "\n")
    _STATE["events"] += 1


def _count_error(where: str = "") -> None:
    _STATE["errors"] += 1
    try:
        fh = _STATE["fh"]
        if fh is not None:
            fh.write(json.dumps({"time": _now_iso(), "component": "recorder",
                                 "operation": "error", "where": where}) + "\n")
    except Exception:
        pass


def _emit(component, operation, inputs=None, outputs=None, duration_ms=None,
          request_id=None, user_id=None) -> None:
    try:
        _SEQ["n"] += 1
        _write({
            "time": _now_iso(),
            "request_id": request_id,
            "seq": _SEQ["n"],
            "endpoint": "eval",
            "user_id": user_id,
            "component": component,
            "operation": operation,
            "inputs": inputs,
            "outputs": outputs,
            "duration_ms": None if duration_ms is None else round(duration_ms, 3),
        })
    except Exception:
        _count_error(f"{component}.{operation}")


def _sha1_messages(messages) -> str:
    try:
        return hashlib.sha1(json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    except Exception:
        return ""


def _usage(resp):
    u = getattr(resp, "usage", None)
    if u is None:
        return None
    return {"prompt_tokens": getattr(u, "prompt_tokens", None),
            "completion_tokens": getattr(u, "completion_tokens", None),
            "total_tokens": getattr(u, "total_tokens", None)}


def _qctx():
    return _QCTX.get()


import contextlib


@contextlib.contextmanager
def question_context(question_id, cutoffs, user_id=None, category=None):
    """Set the per-question context for answerer/judge events outside process_question.

    Used by the self-check harness (STEP 6), which drives answer/judge directly rather than
    through the benchmark's process_question. Harmless in real runs (never called there).
    """
    token = _QCTX.set({"question_id": question_id, "cutoffs": list(cutoffs or []),
                       "answer_i": 0, "judge_i": 0, "user_id": user_id, "category": category})
    try:
        yield
    finally:
        _QCTX.reset(token)


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

def install(output_dir, *, mem0_client, answerer, judge_llm, run_module=None) -> bool:
    """Wrap the benchmark's clients/functions. Returns True on success."""
    if _STATE["installed"]:
        return True
    try:
        _open_writer(output_dir)
    except Exception:
        _count_error("open_writer")
        return False

    # -- process_question: set the per-question contextvar --------------------------------
    if run_module is None:
        import sys
        run_module = sys.modules.get("__main__")
    try:
        _orig_pq = run_module.process_question

        @functools.wraps(_orig_pq)
        async def pq_wrap(*args, **kwargs):
            conv_idx = kwargs.get("conv_idx")
            qa_idx = kwargs.get("qa_idx")
            cutoffs = kwargs.get("cutoffs") or []
            user_id = kwargs.get("user_id")
            qid = f"conv{conv_idx}_q{qa_idx}"
            _QCTX.set({"question_id": qid, "cutoffs": list(cutoffs),
                       "answer_i": 0, "judge_i": 0, "user_id": user_id,
                       "category": (kwargs.get("qa") or {}).get("category")})
            return await _orig_pq(*args, **kwargs)
        run_module.process_question = pq_wrap
    except Exception:
        _count_error("patch.process_question")

    # -- Mem0Client.add / .search (client-side timing) ------------------------------------
    try:
        _orig_cadd = mem0_client.add

        @functools.wraps(_orig_cadd)
        async def cadd(messages, user_id, *a, **k):
            t0 = time.perf_counter()
            result = await _orig_cadd(messages, user_id, *a, **k)
            dur = (time.perf_counter() - t0) * 1000
            try:
                res_list = (result or {}).get("results", []) if isinstance(result, dict) else (result or [])
                _emit("mem0_client", "add",
                      inputs={"messages_sha1": _sha1_messages(messages),
                              "n_messages": len(messages) if messages else 0,
                              "timestamp": k.get("timestamp", a[1] if len(a) > 1 else None)},
                      outputs={"n_results": len(res_list)},
                      duration_ms=dur, request_id=f"add_{_sha1_messages(messages)[:12]}", user_id=user_id)
            except Exception:
                _count_error("mem0_client.add")
            return result
        mem0_client.add = cadd
    except Exception:
        _count_error("patch.mem0_client.add")

    try:
        _orig_csearch = mem0_client.search

        @functools.wraps(_orig_csearch)
        async def csearch(query, user_id, *a, **k):
            t0 = time.perf_counter()
            result = await _orig_csearch(query, user_id, *a, **k)
            dur = (time.perf_counter() - t0) * 1000
            try:
                q = _qctx() or {}
                _emit("mem0_client", "search",
                      inputs={"query": query, "top_k": k.get("top_k", a[0] if a else None)},
                      outputs={"n_results": len(result) if result else 0,
                               "ids": [r.get("id") for r in (result or [])]},
                      duration_ms=dur, request_id=q.get("question_id"), user_id=user_id)
            except Exception:
                _count_error("mem0_client.search")
            return result
        mem0_client.search = csearch
    except Exception:
        _count_error("patch.mem0_client.search")

    # -- answerer.generate (+ inner client usage) -----------------------------------------
    try:
        _orig_gen = answerer.generate

        @functools.wraps(_orig_gen)
        async def gen(system, user, *a, **k):
            token = _USAGE.set([])
            t0 = time.perf_counter()
            out = None
            try:
                out = await _orig_gen(system, user, *a, **k)
                return out
            finally:
                dur = (time.perf_counter() - t0) * 1000
                try:
                    q = _qctx() or {}
                    i = q.get("answer_i", 0)
                    cutoffs = q.get("cutoffs") or []
                    cutoff = cutoffs[i] if i < len(cutoffs) else None
                    if q:
                        q["answer_i"] = i + 1
                    sink = _USAGE.get() or []
                    _emit("answerer", "generate",
                          inputs={"question_id": q.get("question_id"), "cutoff": cutoff,
                                  "system": system, "user": user},
                          outputs={"answer": out, "token_usage": sink[-1] if sink else None},
                          duration_ms=dur, request_id=q.get("question_id"), user_id=q.get("user_id"))
                except Exception:
                    _count_error("answerer.generate")
                _USAGE.reset(token)
        answerer.generate = gen
    except Exception:
        _count_error("patch.answerer.generate")

    try:
        _ans_comp = answerer._client.chat.completions
        _orig_acreate = _ans_comp.create

        @functools.wraps(_orig_acreate)
        async def acreate(*a, **k):
            resp = await _orig_acreate(*a, **k)
            try:
                sink = _USAGE.get()
                if sink is not None:
                    sink.append(_usage(resp))
            except Exception:
                _count_error("answerer.usage")
            return resp
        _ans_comp.create = acreate
    except Exception:
        _count_error("patch.answerer.client")

    # -- judge.generate_structured (prompt + raw + verdict; no tokens) --------------------
    try:
        _orig_judge = judge_llm.generate_structured

        @functools.wraps(_orig_judge)
        async def judge(system, user, *a, **k):
            t0 = time.perf_counter()
            raw = await _orig_judge(system, user, *a, **k)
            dur = (time.perf_counter() - t0) * 1000
            try:
                q = _qctx() or {}
                i = q.get("judge_i", 0)
                cutoffs = q.get("cutoffs") or []
                cutoff = cutoffs[i] if i < len(cutoffs) else None
                if q:
                    q["judge_i"] = i + 1
                verdict = (raw.get("label", "").upper() if isinstance(raw, dict) else None)
                _emit("judge", "generate_structured",
                      inputs={"question_id": q.get("question_id"), "cutoff": cutoff,
                              "system": system, "user": user},
                      outputs={"raw": raw, "verdict": verdict},
                      duration_ms=dur, request_id=q.get("question_id"), user_id=q.get("user_id"))
            except Exception:
                _count_error("judge.generate_structured")
            return raw
        judge_llm.generate_structured = judge
    except Exception:
        _count_error("patch.judge.generate_structured")

    _STATE["installed"] = True
    _emit("recorder", "installed", outputs={"path": _STATE["path"]})
    return True


def stats() -> dict:
    return {"path": _STATE["path"], "events": _STATE["events"], "errors": _STATE["errors"],
            "installed": _STATE["installed"]}
