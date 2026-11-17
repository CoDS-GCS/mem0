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
TOP_K="${TOP_K:-200}"
CUTOFFS="${CUTOFFS:-200,50,20,10}"
export LLM_MODEL="$EXTRACTION_MODEL"
export MEM0_FORWARD_TIMESTAMP="${MEM0_FORWARD_TIMESTAMP:-0}"
export MEM0_TRACE="${MEM0_TRACE:-1}"

# Embedder. Default EMBEDDER=qwen matches Mem0's published OSS table ("Qwen 600M via
# SageMaker", README L242): the same model served locally with a TEI-compatible API.
# EMBEDDER=openai-3-small reverts to the repo default. The embedding service must be up
# (experiments/embedding_service/run_embedding_service.sh, kept in tmux) for the qwen path.
EMBEDDER="${EMBEDDER:-qwen}"
EMBED_HEALTH_URL="${EMBED_HEALTH_URL:-http://localhost:8099/health}"
EMBED_INFO_URL="${EMBED_INFO_URL:-http://localhost:8099/info}"
if [ "$EMBEDDER" = "openai-3-small" ] || [ "$EMBEDDER" = "openai" ]; then
  export EMBEDDER_PROVIDER="openai"
  export EMBEDDER_MODEL="text-embedding-3-small"
  EMBED_DIMS="1536"
  unset EMBEDDING_DIMS || true
  EMBEDDER_LABEL="OpenAI text-embedding-3-small (1536)"
  EMBEDDER_REVISION="n/a"; EMBEDDER_SERVING="OpenAI API"; EMBEDDER_DEVICE="n/a"
  EMBEDDER_NORMALIZE="api-default"; EMBEDDER_INSTRUCTION="none"
else
  # Qwen 600M via the local TEI-compatible service.
  export EMBEDDER_PROVIDER="tei_local"
  export EMBEDDER_MODEL="${QWEN_MODEL_ID:-Qwen/Qwen3-Embedding-0.6B}"
  # 768 dims by default — matches SageMakerEmbedding's `embedding_dims or 768` (:43);
  # README does not state dims. Configurable via EMBEDDING_DIMS.
  EMBED_DIMS="${EMBEDDING_DIMS:-768}"
  export EMBEDDING_DIMS="$EMBED_DIMS"
  export TEI_LOCAL_URL="${TEI_LOCAL_URL:-http://host.docker.internal:8099/embed}"
  EMBEDDER_REVISION="${QWEN_MODEL_REVISION:-97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3}"
  EMBEDDER_LABEL="$EMBEDDER_MODEL @ $EMBEDDER_REVISION (${EMBED_DIMS}d) via local TEI-compatible service"
  EMBEDDER_SERVING="host GPU service serve_qwen_tei.py (not Docker TEI: no nvidia Docker runtime + full / disk)"
  EMBEDDER_DEVICE="GPU"; EMBEDDER_NORMALIZE="l2_full_vector then [:${EMBED_DIMS}] (no renorm, as SageMaker)"
  EMBEDDER_INSTRUCTION="none (add and search embed identically)"
fi
# A ${EMBED_DIMS}-dim run must never reuse a 1536-dim collection: fresh, dims-tagged name.
export COLLECTION_NAME="${COLLECTION_NAME:-${NAME}_q${EMBED_DIMS}}"

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
  "embedder_provider": "$EMBEDDER_PROVIDER",
  "embedder_label": "$EMBEDDER_LABEL",
  "embedder_revision": "$EMBEDDER_REVISION",
  "embedding_dims": "$EMBED_DIMS",
  "embedder_serving": "$EMBEDDER_SERVING",
  "embedder_device": "$EMBEDDER_DEVICE",
  "embedder_normalize": "$EMBEDDER_NORMALIZE",
  "embedder_instruction": "$EMBEDDER_INSTRUCTION",
  "collection_name": "$COLLECTION_NAME",
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

# Docker stores images on / (per `docker info`), which is nearly full here. The wrapper
# rebuilds the mem0 image every run, so check headroom and propose a SAFE prune (dangling
# images + build cache only — never in-use images or other containers). Returns 1 if tight.
check_docker_disk() {
  local avail_kb avail_gb
  avail_kb=$(df -Pk /var/lib/docker 2>/dev/null | awk 'NR==2{print $4}')
  avail_gb=$(awk "BEGIN{printf \"%.2f\", ${avail_kb:-0}/1048576}")
  echo "docker data-root /var/lib/docker: ${avail_gb} GB free on its filesystem"
  docker system df 2>/dev/null | sed 's/^/  /' || true
  if [ "${avail_kb:-0}" -lt 2097152 ]; then
    echo "  WARNING: < 2 GB free where Docker stores images — 'docker compose build mem0' may fail."
    echo "  Safe reclaim (does NOT touch in-use images or other containers):"
    echo "      docker image prune -f      # dangling <none> images"
    echo "      docker builder prune -f    # build cache"
    return 1
  fi
  return 0
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
  echo "----- embedder -----"
  echo "provider:    $EMBEDDER_PROVIDER   dims: $EMBED_DIMS   collection: $COLLECTION_NAME"
  echo "model:       $EMBEDDER_LABEL"
  echo "serving:     $EMBEDDER_SERVING"
  echo "normalize:   $EMBEDDER_NORMALIZE   instruction: $EMBEDDER_INSTRUCTION"
  if [ "$EMBEDDER_PROVIDER" = "tei_local" ]; then
    if curl -sf "$EMBED_HEALTH_URL" >/dev/null 2>&1; then
      echo "health:      UP at $EMBED_HEALTH_URL"
    else
      echo "health:      DOWN at $EMBED_HEALTH_URL — a real run would refuse to start."
      echo "             start it: experiments/embedding_service/run_embedding_service.sh (keep in tmux)"
    fi
  fi
  echo
  echo "----- server rebuild + recreate -----"
  echo "cd \"$MB\" && LLM_MODEL=$EXTRACTION_MODEL EMBEDDER_PROVIDER=$EMBEDDER_PROVIDER EMBEDDING_DIMS=$EMBED_DIMS \\"
  echo "  EMBEDDER_MODEL=$EMBEDDER_MODEL TEI_LOCAL_URL=${TEI_LOCAL_URL:-n/a} COLLECTION_NAME=$COLLECTION_NAME \\"
  echo "  MEM0_FORWARD_TIMESTAMP=$MEM0_FORWARD_TIMESTAMP MEM0_TRACE=$MEM0_TRACE MEM0_TRACE_DIR=\"$RUN_DIR\" \\"
  echo "  docker compose build mem0 && docker compose up -d --force-recreate mem0 qdrant"
  echo
  echo "----- docker disk (mem0 image is rebuilt every run) -----"
  check_docker_disk || true
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

# Embedder health gate: the qwen path needs the local service up (kept in tmux).
if [ "$EMBEDDER_PROVIDER" = "tei_local" ]; then
  if ! curl -sf "$EMBED_HEALTH_URL" >/dev/null 2>&1; then
    echo "ERROR: embedding service DOWN at $EMBED_HEALTH_URL." >&2
    echo "       Start it first and keep it in tmux: experiments/embedding_service/run_embedding_service.sh" >&2
    exit 1
  fi
fi

# Docker-disk gate: a mem0 rebuild needs headroom on /. If tight, stop and let the user
# run the safe prune, rather than pruning automatically.
if ! check_docker_disk; then
  echo "ERROR: insufficient Docker disk for the mem0 rebuild. Run the safe prune above, then re-launch." >&2
  exit 1
fi

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
echo "Embedder:   $EMBEDDER_LABEL  [collection=$COLLECTION_NAME]"

# Point the server at the pinned commit, rebuild, (re)create server + Qdrant.
sed -i -E "s|^mem0ai @ git\+.*|mem0ai @ git+${FORK_URL}@${MEM0_SHA}|" "$REQ"
cd "$MB"
docker compose build mem0
docker compose up -d --force-recreate mem0 qdrant
# Each rebuild orphans the previous mem0 image as a dangling <none> layer; reclaim it now
# so / doesn't fill up over successive runs. Dangling-only + build cache — never touches
# the new in-use image, qdrant, or any other container.
docker image prune -f >/dev/null 2>&1 || true
docker builder prune -f >/dev/null 2>&1 || true
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
