#!/usr/bin/env bash
# One LongMemEval run: ingest haystacks -> search -> answer -> judge, per question.
#
# Usage:   experiments/run_longmemeval.sh <run-name> <mem0-git-ref> [runner args]
# Examples:
#   experiments/run_longmemeval.sh lme_check_1q 94c3fe9 --per-type 1 --question-types temporal-reasoning --seed 42
#   experiments/run_longmemeval.sh lme_A_default_gpt5_30q 94c3fe9 --per-type 5 --seed 42
#   experiments/run_longmemeval.sh lme_A_default_gpt5_30q 94c3fe9 --per-type 5 --seed 42 --dry-run
#
# Decisions baked in (override via env): GPT-5 (OpenAI) as Mem0's extraction LLM, the
# answerer and the judge; embedder = the repo docker default (text-embedding-3-small);
# MEM0_FORWARD_TIMESTAMP off; top-k 200, cutoffs 200/50/20/10; answerer mode. MEM0_TRACE=1.
#
# Each question ingests under its own user_id (longmemeval_<qid>_<run_id>), so runs never
# share memories. Output goes to experiments/runs/<run-name>/ and the script REFUSES to
# start if that folder already exists (a new run must never reuse old results).
#
# "--dry-run" anywhere in the args: print the manifest + the exact commands and exit
# without touching Docker, the dataset, or the server.
set -euo pipefail

NAME="${1:?give a run name, e.g. lme_A_default_gpt5_30q}"
REF="${2:?give a mem0 git ref, e.g. 94c3fe9}"
shift 2

# Detect --dry-run anywhere in the remaining args (and strip it from the runner args).
DRY_RUN=0
RUNNER_ARGS=()
for a in "$@"; do
  if [ "$a" = "--dry-run" ]; then DRY_RUN=1; else RUNNER_ARGS+=("$a"); fi
done

EXP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # .../mem0/experiments
MB="$EXP/memory-benchmarks"
REQ="$MB/docker/mem0/requirements.txt"
PY="$MB/.venv/bin/python"
DATASET="${LME_DATASET:-$EXP/data/longmemeval_s_cleaned.json}"
ENTRY="$EXP/tracing/lme_entry.py"

# Settings (keys, ports, host) from memory-benchmarks/.env
set -a; source "$MB/.env"; set +a
MEM0_HOST="${MEM0_HOST:-http://localhost:8888}"

# Models per role (override via env). Mem0's extraction LLM is set through LLM_MODEL,
# which docker-compose passes into the server; the benchmark answerer/judge are CLI flags.
EXTRACTION_MODEL="${EXTRACTION_MODEL:-gpt-5}"
ANSWERER_MODEL="${ANSWERER_MODEL:-gpt-5}"
JUDGE_MODEL="${JUDGE_MODEL:-gpt-5}"
PROVIDER="${PROVIDER:-openai}"
EMBEDDER_MODEL="${EMBEDDER_MODEL:-text-embedding-3-small}"
TOP_K="${TOP_K:-200}"
CUTOFFS="${CUTOFFS:-200,50,20,10}"
export LLM_MODEL="$EXTRACTION_MODEL"
export EMBEDDER_MODEL
export MEM0_FORWARD_TIMESTAMP="${MEM0_FORWARD_TIMESTAMP:-0}"
export MEM0_TRACE="${MEM0_TRACE:-1}"

# gpt-5 is a reasoning model: Mem0 (>=94c3fe9) auto-omits temperature/max_tokens and sends
# no reasoning_effort, so OpenAI uses its default effort. Record that for the manifest.
REASONING_EFFORT="${REASONING_EFFORT:-default (medium)}"

RUN_DIR="$EXP/runs/$NAME"
OUT_DIR="$RUN_DIR"                          # runner writes predicted_<project>/ + unified json here
PROJECT="$NAME"

# Pin the ref to one commit (dry-run resolves it too; it just won't verify the fork).
MEM0_SHA="$(git -C "$EXP" rev-parse --verify "${REF}^{commit}")"
EXPERIMENTS_COMMIT="$(git -C "$EXP" rev-parse HEAD)"
BENCH_UPSTREAM="$(git -C "$EXP" log -1 --format=%b --grep='git-subtree-dir: experiments/memory-benchmarks' | sed -n 's/^git-subtree-split: //p')"
FORK_URL="$(git -C "$EXP" remote get-url origin | sed -E 's#^git@github.com:#https://github.com/#')"
DATASET_SHA="$( [ -f "$DATASET" ] && sha256sum "$DATASET" | awk '{print $1}' || echo "MISSING:$DATASET" )"

# The exact runner invocation (shared by dry-run and the real run).
runner_cmd() {
  cat <<CMD
cd "$MB"
PYTHONPATH="$MB" MEM0_TRACE=$MEM0_TRACE MEM0_TRACE_DIR="$RUN_DIR" \\
"$PY" "$ENTRY" \\
  --project-name "$PROJECT" \\
  --backend oss --mode answerer \\
  --answerer-model "$ANSWERER_MODEL" --judge-model "$JUDGE_MODEL" --provider "$PROVIDER" \\
  --top-k $TOP_K --top-k-cutoffs "$CUTOFFS" \\
  --score-debug \\
  --mem0-host "$MEM0_HOST" \\
  --dataset-path "$DATASET" \\
  --output-dir "$RUN_DIR" \\
  ${RUNNER_ARGS[*]+${RUNNER_ARGS[*]}}
CMD
}

# The manifest (shared by dry-run and the real run).
manifest_json() {
  cat <<EOF
{
  "run_name": "$NAME",
  "benchmark": "longmemeval",
  "mem0_ref": "$REF",
  "mem0_commit": "$MEM0_SHA",
  "experiments_commit": "$EXPERIMENTS_COMMIT",
  "benchmarks_upstream_commit": "$BENCH_UPSTREAM",
  "extraction_llm": "$EXTRACTION_MODEL",
  "answerer_model": "$ANSWERER_MODEL",
  "judge_model": "$JUDGE_MODEL",
  "provider": "$PROVIDER",
  "reasoning_effort": "$REASONING_EFFORT",
  "embedder": "$EMBEDDER_MODEL",
  "top_k": "$TOP_K",
  "top_k_cutoffs": "$CUTOFFS",
  "forward_timestamp": "$MEM0_FORWARD_TIMESTAMP",
  "trace_enabled": "$MEM0_TRACE",
  "dataset_path": "$DATASET",
  "dataset_sha256": "$DATASET_SHA",
  "sample_args": "${RUNNER_ARGS[*]+${RUNNER_ARGS[*]}}",
  "mem0_host": "$MEM0_HOST",
  "started_utc": "__START__"
}
EOF
}

# -------------------------------------------------------------------------- dry-run
if [ "$DRY_RUN" = "1" ]; then
  echo "===== DRY RUN (nothing launched) ====="
  echo "Run folder (would be created): $RUN_DIR"
  [ -d "$RUN_DIR" ] && echo "WARNING: $RUN_DIR already exists — a real run would refuse to start."
  echo
  echo "----- manifest.json -----"
  manifest_json | sed 's/__START__/<utc at launch>/'
  echo
  echo "----- server pin (docker/mem0/requirements.txt) -----"
  echo "mem0ai @ git+${FORK_URL}@${MEM0_SHA}"
  echo
  echo "----- server rebuild + recreate -----"
  echo "cd \"$MB\" && LLM_MODEL=$EXTRACTION_MODEL EMBEDDER_MODEL=$EMBEDDER_MODEL \\"
  echo "  MEM0_FORWARD_TIMESTAMP=$MEM0_FORWARD_TIMESTAMP MEM0_TRACE=$MEM0_TRACE MEM0_TRACE_DIR=\"$RUN_DIR\" \\"
  echo "  docker compose build mem0 && docker compose up -d --force-recreate mem0 qdrant"
  echo
  echo "----- benchmark run -----"
  runner_cmd
  echo
  echo "----- dataset -----"
  echo "path:   $DATASET"
  echo "sha256: $DATASET_SHA"
  exit 0
fi

# -------------------------------------------------------------------------- real run
[ -d "$RUN_DIR" ] && { echo "ERROR: $RUN_DIR already exists. Pick a new run name (runs never reuse results)." >&2; exit 1; }
[ -f "$DATASET" ] || { echo "ERROR: dataset missing: $DATASET (see experiments/data/README)." >&2; exit 1; }
[ -x "$PY" ] || { echo "ERROR: benchmark venv python not found: $PY" >&2; exit 1; }

# The Docker image installs Mem0 from the fork on GitHub, so the commit must be pushed.
git -C "$EXP" fetch -q origin || true
if ! git -C "$EXP" branch -r --contains "$MEM0_SHA" | grep -q "origin/"; then
  echo "ERROR: commit $MEM0_SHA ($REF) is not pushed to your fork yet. Push it first." >&2
  exit 1
fi

mkdir -p "$RUN_DIR"
export MEM0_TRACE_DIR="$RUN_DIR"
echo "Run folder: $RUN_DIR"
echo "Mem0 code:  $REF = $MEM0_SHA"
echo "Models:     extraction=$EXTRACTION_MODEL answerer=$ANSWERER_MODEL judge=$JUDGE_MODEL (provider=$PROVIDER)"

# Point the server at the pinned commit, rebuild, (re)create server + Qdrant.
sed -i -E "s|^mem0ai @ git\+.*|mem0ai @ git+${FORK_URL}@${MEM0_SHA}|" "$REQ"
cd "$MB"
docker compose build mem0
docker compose up -d --force-recreate mem0 qdrant
echo -n "Waiting for Mem0 server"
for _ in $(seq 1 90); do
  curl -sf "$MEM0_HOST/health" >/dev/null 2>&1 && break
  echo -n "."; sleep 2
done
echo
curl -sf "$MEM0_HOST/health" >/dev/null || { echo "ERROR: server not healthy at $MEM0_HOST" >&2; exit 1; }
START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_EPOCH="$(date +%s)"

# Record exactly what this run uses.
manifest_json | sed "s/__START__/$START/" > "$RUN_DIR/manifest.json"
cp "$REQ" "$RUN_DIR/server_requirements.txt"
docker compose images > "$RUN_DIR/docker_images.txt" 2>/dev/null || true

# The run itself (eval recorder installed by lme_entry.py when MEM0_TRACE=1).
set +e
PYTHONPATH="$MB" MEM0_TRACE="$MEM0_TRACE" MEM0_TRACE_DIR="$RUN_DIR" \
"$PY" "$ENTRY" \
  --project-name "$PROJECT" \
  --backend oss --mode answerer \
  --answerer-model "$ANSWERER_MODEL" --judge-model "$JUDGE_MODEL" --provider "$PROVIDER" \
  --top-k "$TOP_K" --top-k-cutoffs "$CUTOFFS" \
  --score-debug \
  --mem0-host "$MEM0_HOST" \
  --dataset-path "$DATASET" \
  --output-dir "$RUN_DIR" \
  "${RUNNER_ARGS[@]}" 2>&1 | tee "$RUN_DIR/console.log"
STATUS=${PIPESTATUS[0]}
set -e
END_EPOCH="$(date +%s)"

# Keep the server log, finalize traces, and print the scoreboard.
docker compose logs --no-color --since "$START" mem0 > "$RUN_DIR/server.log" 2>&1 || true

"$PY" - "$RUN_DIR" "$START_EPOCH" "$END_EPOCH" <<'EOF'
import glob, gzip, json, os, sys
run, start, end = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

# J score (overall + per type) at each cutoff.
files = sorted(glob.glob(os.path.join(run, "longmemeval_results_*.json")))
if files:
    m = json.load(open(files[-1])).get("metrics_by_cutoff", {})
    for cut in ("top_200", "top_50", "top_20", "top_10"):
        if cut in m:
            o = m[cut]["overall"]
            print(f"J @ {cut}: {o.get('accuracy'):.1f}  ({o.get('correct')}/{o.get('total')})")
            for t, c in (m[cut].get("by_question_type") or {}).items():
                print(f"    {t:<26} {c['accuracy']:.1f}  ({c['correct']}/{c['total']})")
else:
    print("No unified results file (run failed or interrupted).")

# Wall time.
wall = end - start
print(f"\nWall time: {wall//60}m {wall%60}s")

# Tokens per question (extraction from server trace + answerer from eval trace).
def _open(p):
    return gzip.open(p, "rt", encoding="utf-8") if p.endswith(".gz") else open(p, encoding="utf-8")
def _find(base):
    for c in (os.path.join(run, base), os.path.join(run, base + ".gz")):
        if os.path.exists(c):
            return c
    return None

tok = {"extraction": 0, "answerer": 0}
mp = _find("mem0_trace.jsonl")
if mp:
    with _open(mp) as fh:
        for line in fh:
            try: o = json.loads(line)
            except Exception: continue
            if o.get("component") == "llm" and o.get("operation") == "generate_response":
                u = (o.get("outputs") or {}).get("token_usage") or {}
                tok["extraction"] += u.get("total_tokens") or 0
ep = _find("eval_trace.jsonl")
if ep:
    with _open(ep) as fh:
        for line in fh:
            try: o = json.loads(line)
            except Exception: continue
            if o.get("component") == "answerer":
                u = (o.get("outputs") or {}).get("token_usage") or {}
                tok["answerer"] += u.get("total_tokens") or 0

n_q = len(glob.glob(os.path.join(run, "predicted_*", "*.json")))
n_q = max(n_q, 1)
tot = tok["extraction"] + tok["answerer"]
print(f"Tokens: extraction={tok['extraction']:,} answerer={tok['answerer']:,} "
      f"total={tot:,}  (~{tot//n_q:,}/question over {n_q} questions)")
EOF

# Finalize traces: count events, gzip, record sizes in manifest.json.
"$PY" - "$RUN_DIR" <<'EOF'
import gzip, json, os, sys
run = sys.argv[1]
mpath = os.path.join(run, "manifest.json")
try: manifest = json.load(open(mpath))
except Exception: manifest = {}
trace = {}
for name in ("mem0_trace.jsonl", "eval_trace.jsonl"):
    path = os.path.join(run, name)
    info = {"present": False}
    if os.path.exists(path):
        events = errors = 0
        with open(path, "rb") as fh:
            for line in fh:
                events += 1
                if b'"component": "recorder"' in line and b'"operation": "error"' in line:
                    errors += 1
        raw = os.path.getsize(path)
        gz = path + ".gz"
        try:
            with open(path, "rb") as fi, gzip.open(gz, "wb") as fo:
                fo.writelines(fi)
            os.remove(path); fname = name + ".gz"; gz_bytes = os.path.getsize(gz)
        except Exception as e:
            fname = name; gz_bytes = None
            print(f"WARNING: could not gzip {name}: {e}", file=sys.stderr)
        info = {"present": True, "file": fname, "events": events,
                "recorder_errors": errors, "raw_bytes": raw, "gz_bytes": gz_bytes}
    trace[name.split(".")[0]] = info
manifest["trace"] = {"enabled": os.getenv("MEM0_TRACE", "0"), **trace}
json.dump(manifest, open(mpath, "w"), indent=2)
print("Trace: " + json.dumps(manifest["trace"]))
EOF

echo
echo "Watch it in the tracer: experiments/monitor/run_monitor.sh  ->  http://127.0.0.1:8020  (Runs tab)"
echo "Then commit: git add experiments && git commit -m \"run: longmemeval $NAME (mem0 ${MEM0_SHA:0:7})\""
exit "$STATUS"
