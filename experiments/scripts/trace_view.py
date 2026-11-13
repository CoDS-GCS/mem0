#!/usr/bin/env python3
"""
trace_view.py — deterministic reader for the operation traces (STEP 4 + STEP 5).

No LLM, no network. Joins the server trace (mem0_trace.jsonl[.gz]), the eval trace
(eval_trace.jsonl[.gz]), the benchmark result files and the LoCoMo dataset **only on exact
ids or exact text**. When something does not match exactly it prints ``NO MATCH`` — it never
guesses.

Modes:
  --question <id>   e.g. conv0_q0 : evidence turns -> add request -> extraction prompt/response
                    -> stored memories -> search ranks/scores -> answer prompt/answer/judge.
  --session  <n>    the add timeline for one session.
  --summary         counts per operation, memories/entities/duplicates, and stored memories whose
                    text mentions the run's Current Date / its year (extractor used the wrong date).
  --metrics         write per_question_metrics.csv + per_session_metrics.csv and print a summary.

Output is markdown to stdout, or to --out <file>.
"""

from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import re
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _open_any(path):
    return gzip.open(path, "rt", encoding="utf-8") if path.endswith(".gz") else open(path, encoding="utf-8")


def _find(run_dir, base):
    for cand in (os.path.join(run_dir, base), os.path.join(run_dir, base + ".gz")):
        if os.path.exists(cand):
            return cand
    return None


def load_jsonl(path):
    out = []
    if not path or not os.path.exists(path):
        return out
    with _open_any(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def load_results(run_dir):
    """question_id -> result dict, from the unified results file (preferred) or predicted/*.json."""
    results = {}
    files = sorted(glob.glob(os.path.join(run_dir, "locomo_results_*.json")))
    if files:
        try:
            data = json.load(open(files[-1]))
            for ev in data.get("evaluations", data.get("results", [])):
                qid = ev.get("question_id")
                if qid:
                    results[qid] = ev
        except Exception:
            pass
    if not results:
        for p in glob.glob(os.path.join(run_dir, "predicted_*", "*.json")):
            if os.path.basename(p).startswith("_"):
                continue
            try:
                ev = json.load(open(p))
                qid = ev.get("question_id")
                if qid:
                    results[qid] = ev
            except Exception:
                pass
    return results


def load_dataset(path):
    return json.load(open(path))


# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------

def parse_locomo_date(s):
    for fmt in ("%I:%M %p on %d %B, %Y", "%I:%M %p on %d %b, %Y"):
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            continue
    return None


def session_epoch(date_str):
    d = parse_locomo_date(date_str)
    return int(d.replace(tzinfo=timezone.utc).timestamp()) if d else None


def conv_sessions(conv):
    """Return {session_num: (date_str, epoch, [turns])} and {dia_id: turn}."""
    sessions = {}
    dia = {}
    for key in conv:
        m = re.match(r"^session_(\d+)$", key)
        if not m:
            continue
        n = int(m.group(1))
        date_str = conv.get(f"{key}_date_time", "")
        turns = conv[key]
        sessions[n] = (date_str, session_epoch(date_str), turns)
        for t in turns:
            if t.get("dia_id"):
                dia[t["dia_id"]] = {**t, "session": n}
    return sessions, dia


# ---------------------------------------------------------------------------
# Trace indexing
# ---------------------------------------------------------------------------

class Trace:
    def __init__(self, run_dir):
        self.run_dir = run_dir
        self.server = load_jsonl(_find(run_dir, "mem0_trace.jsonl"))
        self.eval = load_jsonl(_find(run_dir, "eval_trace.jsonl"))
        # group server events by request_id, preserve order
        self.by_req = {}
        for ev in self.server:
            self.by_req.setdefault(ev.get("request_id"), []).append(ev)
        # classify add / search requests
        self.add_reqs = []     # (request_id, [events])
        self.search_reqs = []
        for rid, evs in self.by_req.items():
            ops = {(e.get("component"), e.get("operation")) for e in evs}
            if ("entry", "add.request") in ops:
                self.add_reqs.append((rid, evs))
            elif ("entry", "search.request") in ops:
                self.search_reqs.append((rid, evs))

    # -- server-side accessors ----------------------------------------------
    def add_request_event(self, evs):
        return _first(evs, "entry", "add.request")

    def add_timestamp(self, evs):
        e = self.add_request_event(evs)
        return (e.get("inputs") or {}).get("timestamp") if e else None

    def add_messages_text(self, evs):
        e = self.add_request_event(evs)
        msgs = (e.get("inputs") or {}).get("messages") if e else None
        if not msgs:
            return ""
        return "\n".join(m.get("content", "") for m in msgs if isinstance(m, dict))

    def stored_memories(self, evs):
        """List of {id, text, created_at, updated_at} inserted into the memories collection."""
        out = []
        for e in evs:
            if e.get("component") == "vector_store" and e.get("operation") == "insert":
                inp = e.get("inputs") or {}
                ids = inp.get("ids") or []
                payloads = inp.get("payloads") or []
                for i, p in enumerate(payloads):
                    if not isinstance(p, dict):
                        continue
                    out.append({
                        "id": str(ids[i]) if i < len(ids) else None,
                        "text": p.get("data"),
                        "text_lemmatized": p.get("text_lemmatized"),
                        "created_at": p.get("created_at"),
                        "updated_at": p.get("updated_at"),
                        "hash": p.get("hash"),
                    })
        return out

    def extraction(self, evs):
        e = _first(evs, "llm", "generate_response")
        if not e:
            return None
        return {"prompt": (e.get("inputs") or {}).get("messages"),
                "raw": (e.get("outputs") or {}).get("raw"),
                "parsed_facts": (e.get("outputs") or {}).get("parsed_facts"),
                "token_usage": (e.get("outputs") or {}).get("token_usage")}

    def dedup(self, evs):
        e = _first(evs, "dedup", "summary")
        return (e.get("outputs") or {}) if e else {}

    def entities(self, evs):
        e = _first(evs, "spacy", "extract_entities_batch")
        return (e.get("outputs") or {}).get("entities") if e else None

    def search_for_query(self, query):
        """Return the server search request events whose query matches exactly, else None."""
        for rid, evs in self.search_reqs:
            e = _first(evs, "entry", "search.request")
            if e and (e.get("inputs") or {}).get("query") == query:
                return rid, evs
        return None, None

    def scoring(self, evs):
        e = _first(evs, "scoring", "score_and_rank")
        return (e.get("inputs") or {}), (e.get("outputs") or {}) if e else ({}, {})

    # -- eval-side accessors -------------------------------------------------
    def eval_answers(self, qid):
        return [e for e in self.eval if e.get("component") == "answerer"
                and (e.get("inputs") or {}).get("question_id") == qid]

    def eval_judges(self, qid):
        return [e for e in self.eval if e.get("component") == "judge"
                and (e.get("inputs") or {}).get("question_id") == qid]

    def eval_search(self, qid):
        for e in self.eval:
            if e.get("component") == "mem0_client" and e.get("operation") == "search" \
                    and e.get("request_id") == qid:
                return e
        return None

    def eval_adds(self):
        return [e for e in self.eval if e.get("component") == "mem0_client" and e.get("operation") == "add"]


def _first(evs, component, operation):
    for e in evs:
        if e.get("component") == component and e.get("operation") == operation:
            return e
    return None


# ---------------------------------------------------------------------------
# Current Date (what the extractor was told "today" is)
# ---------------------------------------------------------------------------

def current_dates_in_trace(trace):
    """Set of '## Current Date' values found in extraction prompts."""
    dates = set()
    for rid, evs in trace.add_reqs:
        ext = trace.extraction(evs)
        if not ext or not ext.get("prompt"):
            continue
        for msg in ext["prompt"]:
            if isinstance(msg, dict):
                m = re.search(r"##\s*Current Date\s*\n\s*(\d{4}-\d{2}-\d{2})", msg.get("content", ""))
                if m:
                    dates.add(m.group(1))
    return dates


# ---------------------------------------------------------------------------
# Markdown emitter
# ---------------------------------------------------------------------------

class MD:
    def __init__(self):
        self.lines = []

    def __call__(self, s=""):
        self.lines.append(s)

    def text(self):
        return "\n".join(self.lines) + "\n"


def _short(s, n=200):
    if s is None:
        return "None"
    s = str(s).replace("\n", " ⏎ ")
    return s if len(s) <= n else s[:n] + " …"


# ---------------------------------------------------------------------------
# Mode: --question
# ---------------------------------------------------------------------------

def cmd_question(trace, dataset, qid, out):
    m = re.match(r"conv(\d+)_q(\d+)", qid)
    if not m:
        out(f"Bad question id '{qid}' (expected convN_qM)."); return
    conv_idx, qa_idx = int(m.group(1)), int(m.group(2))
    if conv_idx >= len(dataset):
        out(f"conv {conv_idx}: NO MATCH (dataset has {len(dataset)} conversations)."); return
    conv = dataset[conv_idx]["conversation"]
    qas = dataset[conv_idx]["qa"]
    if qa_idx >= len(qas):
        out(f"{qid}: NO MATCH (conversation has {len(qas)} questions)."); return
    qa = qas[qa_idx]
    sessions, dia = conv_sessions(conv)

    out(f"# {qid}")
    out()
    out(f"- **question**: {qa.get('question')}")
    out(f"- **gold answer**: {qa.get('answer')}")
    out(f"- **category**: {qa.get('category')}")
    out(f"- **evidence**: {qa.get('evidence')}")
    out()

    # evidence turns
    out("## Evidence turns")
    ev_turns = []
    for ref in qa.get("evidence", []):
        t = dia.get(ref)
        if t:
            ev_turns.append((ref, t))
            out(f"- `{ref}` (session {t['session']}) **{t.get('speaker')}**: {t.get('text')}")
        else:
            out(f"- `{ref}`: NO MATCH (dia_id not found in dataset)")
    out()

    # evidence turn -> add request (exact text match)
    out("## Add request(s) containing the evidence turns")
    matched_reqs = {}
    for ref, t in ev_turns:
        text = (t.get("text") or "").strip()
        hits = []
        for rid, evs in trace.add_reqs:
            if text and text in trace.add_messages_text(evs):
                hits.append((rid, evs))
        if not hits:
            out(f"- `{ref}`: NO MATCH (no add request's messages contain this turn text)")
        for rid, evs in hits:
            matched_reqs[rid] = evs
            ts = trace.add_timestamp(evs)
            out(f"- `{ref}` → add request `{rid}` (timestamp={ts})")
    out()

    if not matched_reqs:
        out("_No add requests matched; cannot trace extraction/storage._")
    for rid, evs in matched_reqs.items():
        out(f"### Add request `{rid}`")
        ext = trace.extraction(evs)
        if ext:
            prompt = ext.get("prompt") or []
            obs = cur = None
            for msg in prompt:
                if isinstance(msg, dict):
                    mo = re.search(r"##\s*Observation Date\s*\n\s*(\S+)", msg.get("content", ""))
                    mc = re.search(r"##\s*Current Date\s*\n\s*(\S+)", msg.get("content", ""))
                    obs = mo.group(1) if mo else obs
                    cur = mc.group(1) if mc else cur
            out(f"- extraction Observation Date: **{obs}**, Current Date: **{cur}**")
            out(f"- token usage: {ext.get('token_usage')}")
            out(f"- raw response: {_short(ext.get('raw'), 300)}")
            facts = ext.get("parsed_facts") or []
            out(f"- parsed facts ({len(facts)}):")
            for f in facts:
                out(f"    - {_short(f.get('text'), 160)}")
        else:
            out("- extraction: NO MATCH (no llm event in this request)")
        mems = trace.stored_memories(evs)
        out(f"- stored memories ({len(mems)}):")
        for mm in mems:
            out(f"    - `{mm['id']}` (created_at={mm['created_at']}) {_short(mm['text'], 160)}")
        ded = trace.dedup(evs)
        if ded.get("skipped"):
            out(f"- duplicates skipped ({ded.get('n_skipped')}): "
                + ", ".join(f"{_short(s.get('text'),60)} [{s.get('reason')}]" for s in ded["skipped"]))
        out()

    stored_ids = {mm["id"] for _, evs in matched_reqs.items() for mm in trace.stored_memories(evs)}

    # SEARCH
    out("## Search")
    rid, sevs = trace.search_for_query(qa.get("question"))
    if not sevs:
        out(f"- NO MATCH (no server search with query == question)")
    else:
        sin, sout = trace.scoring(sevs)
        ranked = sout.get("ranked") or []
        rank_by_id = {r["id"]: (i + 1, r) for i, r in enumerate(ranked)}
        sem_ids = {c["id"] for c in (sin.get("semantic_candidates") or [])}
        bm = sin.get("bm25_scores") or {}
        eb = sin.get("entity_boosts") or {}
        out(f"- server search request `{rid}`; threshold={sin.get('threshold')}, top_k={sin.get('top_k')}, "
            f"{len(ranked)} returned, {len(sem_ids)} semantic candidates")
        if not stored_ids:
            out("- (no stored memories from evidence add requests to locate)")
        for mid in stored_ids:
            if mid in rank_by_id:
                r, det = rank_by_id[mid]
                sd = det.get("score_details") or {}
                out(f"    - `{mid}`: **rank {r}**, combined={det.get('score')}, "
                    f"semantic={sd.get('semantic_score', sd.get('semantic'))}, "
                    f"bm25={sd.get('bm25_score', sd.get('bm25'))}, "
                    f"entity_boost={sd.get('entity_boost')}")
            elif mid in sem_ids or mid in bm or mid in eb:
                out(f"    - `{mid}`: candidate but **below threshold / not in top_k** "
                    f"(semantic={'yes' if mid in sem_ids else 'no'}, "
                    f"bm25={bm.get(mid, '-')}, entity_boost={eb.get(mid, '-')})")
            else:
                out(f"    - `{mid}`: **not a candidate**")
    out()

    # EVALUATION
    out("## Evaluation")
    answers = trace.eval_answers(qid)
    judges = trace.eval_judges(qid)
    if not answers:
        out("- answerer: NO MATCH (no eval answerer events for this question)")
    for a in answers:
        ain, aout = a.get("inputs") or {}, a.get("outputs") or {}
        out(f"- cutoff **{ain.get('cutoff')}**: answer latency {a.get('duration_ms')} ms, "
            f"tokens={aout.get('token_usage')}")
        out(f"    - answer: {_short(aout.get('answer'), 200)}")
        out(f"    - answer prompt (memories as the answerer saw them):")
        for ln in _memory_lines_from_prompt(ain.get("user", "")):
            out(f"        {ln}")
    for j in judges:
        jin, jout = j.get("inputs") or {}, j.get("outputs") or {}
        out(f"- judge cutoff **{jin.get('cutoff')}**: verdict **{jout.get('verdict')}** "
            f"(latency {j.get('duration_ms')} ms)")


def _memory_lines_from_prompt(prompt_text):
    """Extract the '(Date) memory' lines the answerer prompt shows (deterministic, no guessing)."""
    lines = []
    for ln in (prompt_text or "").splitlines():
        if re.match(r"^\((?:\w+, \w+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2})\)", ln.strip()):
            lines.append(ln.strip())
    return lines or ["(no dated memory lines found in prompt)"]


# ---------------------------------------------------------------------------
# Mode: --session
# ---------------------------------------------------------------------------

def cmd_session(trace, dataset, conv_idx, n, out):
    conv = dataset[conv_idx]["conversation"]
    sessions, dia = conv_sessions(conv)
    if n not in sessions:
        out(f"session {n}: NO MATCH (not in dataset)"); return
    date_str, epoch, turns = sessions[n]
    out(f"# conv{conv_idx} session {n}")
    out(f"- date: {date_str}  (epoch {epoch})")
    out(f"- turns in dataset: {len(turns)}")
    out()
    reqs = [(rid, evs) for rid, evs in trace.add_reqs if trace.add_timestamp(evs) == epoch]
    out(f"## Add timeline ({len(reqs)} add request(s) with this session's timestamp)")
    if not reqs:
        out("- NO MATCH (no add requests tagged with this session's epoch)")
    for i, (rid, evs) in enumerate(reqs, 1):
        req = trace.add_request_event(evs)
        n_msgs = len((req.get("inputs") or {}).get("messages") or []) if req else 0
        ext = trace.extraction(evs) or {}
        facts = ext.get("parsed_facts") or []
        mems = trace.stored_memories(evs)
        ded = trace.dedup(evs)
        ents = trace.entities(evs) or []
        resp = _first(evs, "entry", "add.response")
        dur = resp.get("duration_ms") if resp else None
        out(f"### {i}. `{rid}`  ({n_msgs} msgs, server add {dur} ms)")
        out(f"- facts extracted: {len(facts)}; stored: {len(mems)}; "
            f"skipped: {ded.get('n_skipped', 0)}; entity groups: {sum(len(e) for e in ents) if ents else 0}")
        for mm in mems:
            out(f"    - stored `{mm['id']}` (created_at={mm['created_at']}) {_short(mm['text'], 140)}")
        for s in (ded.get("skipped") or []):
            out(f"    - skipped [{s.get('reason')}] {_short(s.get('text'), 100)}")


# ---------------------------------------------------------------------------
# Mode: --summary
# ---------------------------------------------------------------------------

def cmd_summary(trace, dataset, out):
    out("# Trace summary")
    out()
    op_counts = {}
    for e in trace.server:
        op_counts[f"{e.get('component')}.{e.get('operation')}"] = op_counts.get(
            f"{e.get('component')}.{e.get('operation')}", 0) + 1
    for e in trace.eval:
        op_counts[f"eval:{e.get('component')}.{e.get('operation')}"] = op_counts.get(
            f"eval:{e.get('component')}.{e.get('operation')}", 0) + 1
    out(f"- server events: {len(trace.server)}; eval events: {len(trace.eval)}")
    out(f"- add requests: {len(trace.add_reqs)}; search requests: {len(trace.search_reqs)}")
    recorder_errors = sum(1 for e in trace.server + trace.eval
                          if e.get("component") == "recorder" and e.get("operation") == "error")
    out(f"- recorder errors: {recorder_errors}")
    out()
    out("## Counts per operation")
    for k in sorted(op_counts):
        out(f"- {k}: {op_counts[k]}")
    out()

    total_mems = 0
    total_entities = 0
    total_skipped = 0
    for rid, evs in trace.add_reqs:
        total_mems += len(trace.stored_memories(evs))
        total_skipped += trace.dedup(evs).get("n_skipped", 0) or 0
        ents = trace.entities(evs) or []
        total_entities += sum(len(e) for e in ents) if ents else 0
    out("## Totals")
    out(f"- memories stored: {total_mems}")
    out(f"- entity mentions found: {total_entities}")
    out(f"- duplicates skipped: {total_skipped}")
    out()

    # Current-Date leakage check
    cur_dates = current_dates_in_trace(trace)
    years = {d[:4] for d in cur_dates}
    out("## Current-Date leakage check")
    out(f"- extractor Current Date value(s) seen in prompts: {sorted(cur_dates) or 'n/a'}")
    needles = set(cur_dates) | years
    flagged = []
    for rid, evs in trace.add_reqs:
        for mm in trace.stored_memories(evs):
            text = mm.get("text") or ""
            hit = next((nd for nd in needles if nd and nd in text), None)
            if hit:
                flagged.append((rid, mm["id"], hit, text))
    if not needles:
        out("- no Current Date found in prompts → cannot check (n/a)")
    elif not flagged:
        out(f"- stored memories mentioning the Current Date or its year ({sorted(needles)}): **0**")
    else:
        out(f"- stored memories mentioning the Current Date or its year ({sorted(needles)}): "
            f"**{len(flagged)}**")
        for rid, mid, hit, text in flagged:
            out(f"    - `{mid}` (req `{rid}`) matched `{hit}`: {_short(text, 160)}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def default_dataset_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "memory-benchmarks", "datasets", "locomo", "locomo10.json")


def parse_args():
    p = argparse.ArgumentParser(description="Deterministic reader for Mem0 benchmark traces.")
    p.add_argument("--run", required=True, help="Run folder (contains the traces + result files).")
    p.add_argument("--dataset", default=None, help="LoCoMo dataset json (default: the bundled one).")
    p.add_argument("--question", help="Question id, e.g. conv0_q0")
    p.add_argument("--session", type=int, help="Session number (per the conversation)")
    p.add_argument("--conv", type=int, default=0, help="Conversation index for --session (default 0)")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--metrics", action="store_true")
    p.add_argument("--out", default=None, help="Write markdown here instead of stdout.")
    return p.parse_args()


def main():
    args = parse_args()
    dataset = load_dataset(args.dataset or default_dataset_path())
    trace = Trace(args.run)
    out = MD()

    if args.metrics:
        from trace_metrics import run_metrics  # STEP 5 (same directory)
        run_metrics(trace, dataset, args.run, out)
    elif args.question:
        cmd_question(trace, dataset, args.question, out)
    elif args.session is not None:
        cmd_session(trace, dataset, args.conv, args.session, out)
    elif args.summary:
        cmd_summary(trace, dataset, out)
    else:
        out("Nothing to do: pass --question, --session, --summary or --metrics.")

    text = out.text()
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
