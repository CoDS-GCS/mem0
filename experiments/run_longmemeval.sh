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
export MEM0_FORWARD_TIMESTAMP="${MEM0_FORWARD_TIMESTAMP:-0}"
export MEM0_TRACE="${MEM0_TRACE:-1}"

# Extraction routing. Default: gpt-5 on OpenAI direct (reasoning model; mem0 omits
# temperature/max_tokens and sends no reasoning_effort). EXTRACTION_MODEL=gpt-oss-120b routes
# extraction through OpenRouter PINNED to one provider with no fallbacks — Parasail, the
# provider Mem0 used for their GPT-OSS-120B row — and raises the completion budget, because
# GPT-OSS reasoning tokens count against max_tokens and the mem0 default (2000) cuts off
# (finish_reason=length, empty JSON). answerer/judge always run host-side on OpenAI.
EXTRACTION_PROVIDER_PIN="n/a (OpenAI direct)"
EXTRACTION_MAX_TOKENS="mem0 default (2000)"
EXTRACTION_ENDPOINT="official OpenAI API"
case "$EXTRACTION_MODEL" in
  gpt-6-luna|sub2api/gpt-6-luna)
    # GPT-6 Luna via a Sub2API subscription-backed gateway (OpenAI-compatible), pointed at
    # through SERVER CONFIG only (main.py -> llm config openai_base_url/api_key), never mem0
    # code. The gateway reports model "gpt-6-luna"; a single test call accepted mem0's params
    # (temperature/top_p/max_tokens/response_format), finish_reason=stop, valid JSON.
    export LLM_MODEL="gpt-6-luna"
    : "${SUB2API_BASE_URL:?set SUB2API_BASE_URL in memory-benchmarks/.env for gpt-6-luna}"
    : "${SUB2API_API_KEY:?set SUB2API_API_KEY in memory-benchmarks/.env for gpt-6-luna}"
    # Key reaches the container ONLY through these wrapper-controlled MEM0_LLM_* vars; never
    # printed. The OpenRouter key must NOT be bridged on this path.
    export MEM0_LLM_BASE_URL="$SUB2API_BASE_URL"
    export MEM0_LLM_API_KEY="$SUB2API_API_KEY"
    unset MEM0_OPENROUTER_API_KEY MEM0_OPENROUTER_PROVIDER 2>/dev/null || true
    # Luna reports reasoning tokens inside completion_tokens; raise the budget so default-
    # reasoning extraction never truncates. Same rule as gpt-oss-120b.
    export LLM_MAX_TOKENS="${LLM_MAX_TOKENS:-16000}"
    REASONING_EFFORT="${REASONING_EFFORT:-default (mem0 sends none; gateway/model default)}"
    EXTRACTION_PROVIDER_PIN="Sub2API subscription gateway (OpenAI-compatible), model gpt-6-luna"
    EXTRACTION_MAX_TOKENS="$LLM_MAX_TOKENS (raised; Luna reasoning tokens count within completion)"
    EXTRACTION_ENDPOINT="Sub2API subscription-backed gateway (OpenAI-compatible), NOT the official OpenAI API"
    ;;
  gpt-oss-120b|openai/gpt-oss-120b)
    export LLM_MODEL="openai/gpt-oss-120b"
    # Bridge the OpenRouter key from .env to the mem0 container ONLY on this path, via the
    # wrapper-controlled MEM0_OPENROUTER_* vars (compose reads those, never .env directly, so
    # default OpenAI runs never receive the key). Key value is never printed.
    : "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY in memory-benchmarks/.env for gpt-oss-120b}"
    export MEM0_OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
    export MEM0_OPENROUTER_PROVIDER="${OPENROUTER_PROVIDER:-Parasail}"
    # Generous budget so default-reasoning GPT-OSS extraction never truncates (one call
    # measured ~2.8k completion tokens at 16000; finish_reason=stop).
    export LLM_MAX_TOKENS="${LLM_MAX_TOKENS:-16000}"
    REASONING_EFFORT="${REASONING_EFFORT:-default (mem0 sends none; GPT-OSS/OpenRouter default)}"
    EXTRACTION_PROVIDER_PIN="$MEM0_OPENROUTER_PROVIDER via OpenRouter (allow_fallbacks=false)"
    EXTRACTION_MAX_TOKENS="$LLM_MAX_TOKENS (raised; GPT-OSS reasoning counts against it)"
    ;;
  *)
    export LLM_MODEL="$EXTRACTION_MODEL"
    REASONING_EFFORT="${REASONING_EFFORT:-default (medium)}"
    ;;
esac

# Answerer + judge endpoint (selectable). Default: official OpenAI (host-side; OPENAI_API_KEY
# from .env). ANSWERER_ENDPOINT=sub2api routes them through the same gateway by pointing the
# host OpenAI client at it — run.py's LLMClient reads OPENAI_BASE_URL/OPENAI_API_KEY from env,
# so no upstream run.py edit is needed. This run uses official OpenAI.
ANSWERER_ENDPOINT="${ANSWERER_ENDPOINT:-openai}"
case "$ANSWERER_ENDPOINT" in
  sub2api)
    : "${SUB2API_BASE_URL:?set SUB2API_BASE_URL in .env for ANSWERER_ENDPOINT=sub2api}"
    : "${SUB2API_API_KEY:?set SUB2API_API_KEY in .env for ANSWERER_ENDPOINT=sub2api}"
    export OPENAI_BASE_URL="$SUB2API_BASE_URL"
    export OPENAI_API_KEY="$SUB2API_API_KEY"
    ANSWERER_ENDPOINT_LABEL="Sub2API gateway (OpenAI-compatible)"
    ;;
  openai|*)
    unset OPENAI_BASE_URL 2>/dev/null || true   # official endpoint; OPENAI_API_KEY stays the .env official key
    ANSWERER_ENDPOINT_LABEL="official OpenAI API"
    ;;
esac

# Embedder. Default EMBEDDER=qwen matches Mem0's published OSS table ("Qwen 600M via
# SageMaker", README L242): the same model + revision, now served by real HuggingFace TEI
# as the `qwen-tei` docker-compose service on the GPU. EMBEDDER=openai-3-small reverts to
# the repo default. No separate start step — `docker compose up` below brings TEI up and
# mem0 waits for it to be healthy.
EMBEDDER="${EMBEDDER:-qwen}"
EMBED_HEALTH_URL="${EMBED_HEALTH_URL:-http://localhost:${EMBED_PORT:-8099}/health}"
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
  export TEI_LOCAL_URL="${TEI_LOCAL_URL:-http://qwen-tei:80/embed}"
  EMBEDDER_REVISION="${QWEN_MODEL_REVISION:-97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3}"
  EMBEDDER_LABEL="$EMBEDDER_MODEL @ $EMBEDDER_REVISION (${EMBED_DIMS}d) via real HuggingFace TEI"
  EMBEDDER_SERVING="qwen-tei docker-compose service: HF TEI (hopper/H100 image) on the GPU, reached by mem0 as http://qwen-tei:80/embed"
  EMBEDDER_DEVICE="GPU"; EMBEDDER_NORMALIZE="l2_full_vector then [:${EMBED_DIMS}] (no renorm, as SageMaker)"
  EMBEDDER_INSTRUCTION="none (add and search embed identically)"
fi
# A ${EMBED_DIMS}-dim run must never reuse a 1536-dim collection: fresh, dims-tagged name.
export COLLECTION_NAME="${COLLECTION_NAME:-${NAME}_q${EMBED_DIMS}}"

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
  "extraction_model_id": "$LLM_MODEL",
  "extraction_provider_pin": "$EXTRACTION_PROVIDER_PIN",
  "extraction_max_tokens": "$EXTRACTION_MAX_TOKENS",
  "answerer_model": "$ANSWERER_MODEL",
  "judge_model": "$JUDGE_MODEL",
  "provider": "$PROVIDER",
  "extraction_endpoint": "$EXTRACTION_ENDPOINT",
  "answerer_endpoint": "$ANSWERER_ENDPOINT_LABEL",
  "endpoint_note": "Extraction endpoint: $EXTRACTION_ENDPOINT. Answerer/judge endpoint: $ANSWERER_ENDPOINT_LABEL.",
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
  local root avail_kb avail_gb
  # Docker's storage was moved to /shared_mnt (data-root), so check the real root dir, not
  # the default /var/lib/docker (which lives on the near-full / filesystem here).
  root=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || echo /var/lib/docker)
  avail_kb=$(df -Pk "$root" 2>/dev/null | awk 'NR==2{print $4}')
  avail_gb=$(awk "BEGIN{printf \"%.2f\", ${avail_kb:-0}/1048576}")
  echo "docker data-root $root: ${avail_gb} GB free on its filesystem"
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

# Monitor: always available for a run. Start experiments/monitor/run_monitor.sh in the
# background if it isn't already serving, print the URL, and leave it running after the run.
MONITOR_HOST="${LME_HOST:-127.0.0.1}"
MONITOR_PORT="${LME_PORT:-8020}"
MONITOR_URL="http://${MONITOR_HOST}:${MONITOR_PORT}"
ensure_monitor() {
  if curl -sf "$MONITOR_URL/" >/dev/null 2>&1; then
    echo "Monitor already running -> $MONITOR_URL  (Runs tab)"
    return 0
  fi
  echo "Starting monitor in background -> $MONITOR_URL  (Runs tab)"
  LME_HOST="$MONITOR_HOST" LME_PORT="$MONITOR_PORT" \
    nohup "$EXP/monitor/run_monitor.sh" > "$EXP/monitor/monitor.out" 2>&1 &
  disown 2>/dev/null || true
  for _ in $(seq 1 20); do
    curl -sf "$MONITOR_URL/" >/dev/null 2>&1 && break
    sleep 1
  done
  curl -sf "$MONITOR_URL/" >/dev/null 2>&1 \
    || echo "  (monitor not up yet; see $EXP/monitor/monitor.out)"
}

# Show which questions the sampler will pick (deterministic: same seed/per-type/types as the
# runner) and how many turn-pairs each has. Replicates sample_questions_stratified exactly.
show_selected_questions() {
  "$PY" - "$DATASET" "${RUNNER_ARGS[@]}" <<'PYEOF'
import argparse, json, random, sys
dataset = sys.argv[1]
p = argparse.ArgumentParser()
p.add_argument("--per-type", type=int, default=5)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--question-types", default=None)
p.add_argument("--all-questions", action="store_true")
args, _ = p.parse_known_args(sys.argv[2:])
qs = json.load(open(dataset))
types = [t.strip() for t in args.question_types.split(",")] if args.question_types else None
tf = set(types) if types else None
groups = {}
for q in qs:
    if tf is None or q["question_type"] in tf:
        groups.setdefault(q["question_type"], []).append(q)
for t in groups:
    groups[t].sort(key=lambda q: q["question_id"])
rng = random.Random(args.seed)
sampled = []
for t in sorted(groups):
    g = groups[t]
    sampled += rng.sample(g, min(args.per_type, len(g)))
sampled.sort(key=lambda q: q["question_id"])
print(f"seed={args.seed} per-type={args.per_type} types={types or 'ALL'} -> {len(sampled)} question(s)")
for q in sampled:
    sess = q["haystack_sessions"]
    pairs = sum((len(s) + 1) // 2 for s in sess)   # pair_turns(): ceil(len/2) per session
    print(f"  {q['question_id']}  type={q['question_type']}  sessions={len(sess)}  turn_pairs={pairs}")
PYEOF
}

# Confirm this run's deterministic sample equals another run's question_ids (SAME questions).
# Reads the reference run's unified results JSON for its question_ids.
check_same_questions() {
  "$PY" - "$DATASET" "$1" "${RUNNER_ARGS[@]}" <<'PYEOF'
import argparse, glob, json, os, random, sys
dataset, ref = sys.argv[1], sys.argv[2]
p = argparse.ArgumentParser()
p.add_argument("--per-type", type=int, default=5)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--question-types", default=None)
p.add_argument("--all-questions", action="store_true")
args, _ = p.parse_known_args(sys.argv[3:])
qs = json.load(open(dataset))
tf = set(t.strip() for t in args.question_types.split(",")) if args.question_types else None
groups = {}
for q in qs:
    if tf is None or q["question_type"] in tf:
        groups.setdefault(q["question_type"], []).append(q)
for t in groups:
    groups[t].sort(key=lambda q: q["question_id"])
rng = random.Random(args.seed)
samp = []
for t in sorted(groups):
    g = groups[t]
    samp += rng.sample(g, min(args.per_type, len(g)))
sample_ids = sorted(q["question_id"] for q in samp)
refs = sorted(glob.glob(os.path.join(ref, "longmemeval_results_*.json")))
if not refs:
    print(f"reference run {os.path.basename(ref)} has no unified results JSON — cannot compare")
    sys.exit(0)
ref_ids = sorted(e["question_id"] for e in json.load(open(refs[-1]))["evaluations"])
print(f"this run sample:  {len(sample_ids)} question_ids")
print(f"reference run:    {len(ref_ids)} question_ids ({os.path.basename(ref)})")
if sample_ids == ref_ids:
    print(f"MATCH: identical {len(sample_ids)} question_ids ✓")
else:
    only_here = sorted(set(sample_ids) - set(ref_ids))
    only_ref = sorted(set(ref_ids) - set(sample_ids))
    print("MISMATCH ✗")
    if only_here: print("  only in this run:", only_here[:12])
    if only_ref:  print("  only in reference:", only_ref[:12])
PYEOF
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
      echo "health:      UP at $EMBED_HEALTH_URL (qwen-tei compose service)"
    else
      echo "health:      DOWN at $EMBED_HEALTH_URL — 'docker compose up' below will start it;"
      echo "             mem0 waits for qwen-tei to be healthy (depends_on) before it starts."
    fi
  fi
  echo
  echo "----- extraction LLM -----"
  echo "EXTRACTION_MODEL: $EXTRACTION_MODEL   ->   mem0 model_id: $LLM_MODEL"
  echo "endpoint:         $EXTRACTION_ENDPOINT"
  echo "provider pin:     $EXTRACTION_PROVIDER_PIN"
  echo "max_tokens:       $EXTRACTION_MAX_TOKENS"
  echo "reasoning:        $REASONING_EFFORT   (temperature/top_p: as mem0 sends)"
  if [ -n "${MEM0_LLM_BASE_URL:-}" ]; then
    echo "gateway host:     $(printf '%s' "$MEM0_LLM_BASE_URL" | sed -E 's#^[a-zA-Z]+://([^/]+).*#\1#')   (OpenAI-compatible; set on llm config via server config)"
    echo "gateway key:      present (from .env SUB2API_API_KEY; to container via MEM0_LLM_API_KEY, never printed)"
    echo "openrouter key:   NOT passed to the container on this path"
  fi
  if [ -n "${MEM0_OPENROUTER_API_KEY:-}" ]; then
    echo "openrouter key:   present (from .env; passed to mem0 container, never printed)"
  fi
  echo "answerer/judge:   $ANSWERER_ENDPOINT_LABEL  (models: answerer=$ANSWERER_MODEL judge=$JUDGE_MODEL)"
  echo
  echo "----- selected questions (deterministic sample) -----"
  show_selected_questions || echo "(could not compute sample)"
  echo
  echo "----- same-questions check vs lme_A_default_oss120b_60q -----"
  check_same_questions "$EXP/runs/lme_A_default_oss120b_60q" || echo "(could not compare question sets)"
  echo
  echo "----- monitor -----"
  if curl -sf "$MONITOR_URL/" >/dev/null 2>&1; then
    echo "already running -> $MONITOR_URL  (a real run leaves it up)"
  else
    echo "not running — a real run starts experiments/monitor/run_monitor.sh in the background -> $MONITOR_URL"
  fi
  echo
  echo "----- compose bring-up (embedder + qdrant, then rebuild mem0) -----"
  echo "cd \"$MB\" && docker compose up -d qwen-tei qdrant"
  echo "LLM_MODEL=$EXTRACTION_MODEL EMBEDDER_PROVIDER=$EMBEDDER_PROVIDER EMBEDDING_DIMS=$EMBED_DIMS \\"
  echo "  EMBEDDER_MODEL=$EMBEDDER_MODEL TEI_LOCAL_URL=${TEI_LOCAL_URL:-n/a} COLLECTION_NAME=$COLLECTION_NAME \\"
  echo "  MEM0_FORWARD_TIMESTAMP=$MEM0_FORWARD_TIMESTAMP MEM0_TRACE=$MEM0_TRACE MEM0_TRACE_DIR=\"$RUN_DIR\" \\"
  echo "  docker compose build mem0 && docker compose up -d --force-recreate mem0"
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
echo "Extraction: $LLM_MODEL  pin=$EXTRACTION_PROVIDER_PIN  max_tokens=$EXTRACTION_MAX_TOKENS"
echo "Embedder:   $EMBEDDER_LABEL  [collection=$COLLECTION_NAME]"

# Monitor up for the run (and kept running afterwards).
ensure_monitor

# Point the server at the pinned commit, rebuild, (re)create server + Qdrant.
sed -i -E "s|^mem0ai @ git\+.*|mem0ai @ git+${FORK_URL}@${MEM0_SHA}|" "$REQ"
cd "$MB"
# Bring up the embedder (real HF TEI on the GPU) and Qdrant first — one compose, no separate
# start step for the embedder. qwen-tei is idempotent; only mem0 is force-recreated.
docker compose up -d qwen-tei qdrant
# Confirm the embedder is serving before the (slow) mem0 rebuild (qwen path only).
if [ "$EMBEDDER_PROVIDER" = "tei_local" ]; then
  echo -n "Waiting for qwen-tei embedder"
  for _ in $(seq 1 60); do
    curl -sf "$EMBED_HEALTH_URL" >/dev/null 2>&1 && break
    echo -n "."; sleep 2
  done
  echo
  curl -sf "$EMBED_HEALTH_URL" >/dev/null 2>&1 || {
    echo "ERROR: qwen-tei embedder not healthy at $EMBED_HEALTH_URL." >&2
    echo "       Check: docker compose logs qwen-tei" >&2
    exit 1
  }
fi
docker compose build mem0
# mem0 depends_on qwen-tei + qdrant (service_healthy), so compose waits for TEI's weights to
# load on the GPU before the server starts.
docker compose up -d --force-recreate mem0
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
n_extract = cutoffs = parse_fail = llm_err = 0
add_req = add_resp = 0
ex_models, ans_models = set(), set()
add_zero = mem_stored = 0
mp = _find("mem0_trace.jsonl")
if mp:
    with _open(mp) as fh:
        for line in fh:
            try: o = json.loads(line)
            except Exception: continue
            comp, op = o.get("component"), o.get("operation")
            if comp == "llm" and op == "generate_response":
                out = o.get("outputs") or {}
                u = out.get("token_usage") or {}
                tok["extraction"] += u.get("total_tokens") or 0
                n_extract += 1
                if out.get("finish_reason") == "length":   # hit max_tokens -> cut off
                    cutoffs += 1
                if out.get("parse_ok") is False:           # extraction output not valid JSON
                    parse_fail += 1
                if out.get("error"):
                    llm_err += 1
                if out.get("model_reported"):
                    ex_models.add(out["model_reported"])
            elif comp == "entry" and op == "add.request":
                add_req += 1
            elif comp == "entry" and op == "add.response":
                add_resp += 1
                res = (o.get("outputs") or {}).get("results") or []
                mem_stored += len(res)
                if not res:                                # add stored 0 memories
                    add_zero += 1
ep = _find("eval_trace.jsonl")
if ep:
    with _open(ep) as fh:
        for line in fh:
            try: o = json.loads(line)
            except Exception: continue
            if o.get("component") == "answerer":
                out = o.get("outputs") or {}
                u = out.get("token_usage") or {}
                tok["answerer"] += u.get("total_tokens") or 0
                if out.get("model_reported"):
                    ans_models.add(out["model_reported"])

# Failed adds (rate-limit / quota / gateway errors): an add whose request has no response,
# plus the ingestion harness's own per-question failed-pair count.
add_failed = max(0, add_req - add_resp)
ing_failed = 0
for p in glob.glob(os.path.join(run, "predicted_*", "_ingestion_*.json")):
    try:
        ing_failed += int(json.load(open(p)).get("total_pairs_failed") or 0)
    except Exception:
        pass

# Count DISTINCT question IDs, not files: predicted_*/ holds both {qid}.json and
# _progress_{qid}.json, so counting files double-counts (the old "over 2 questions" bug).
qids = set()
for p in glob.glob(os.path.join(run, "predicted_*", "*.json")):
    try:
        qids.add(json.load(open(p)).get("question_id") or os.path.basename(p))
    except Exception:
        qids.add(os.path.basename(p))
n_q = max(len(qids), 1)
tot = tok["extraction"] + tok["answerer"]
print(f"Tokens: extraction={tok['extraction']:,} answerer={tok['answerer']:,} "
      f"total={tot:,}  (~{tot//n_q:,}/question over {n_q} question(s))")
print(f"Extraction calls: {n_extract}  |  cut off (finish_reason=length): {cutoffs}"
      f"  |  JSON parse failures: {parse_fail}  |  LLM errors: {llm_err}")
print(f"Adds: calls={add_req}  ok={add_resp}  "
      f"failed (no response — rate-limit/quota/gateway): {add_failed}  |  "
      f"ingestion-reported failed pairs: {ing_failed}")
_zpct = (100 * add_zero / add_resp) if add_resp else 0
_mpa = (mem_stored / add_resp) if add_resp else 0
print(f"Memories: stored={mem_stored:,}  per-add={_mpa:.2f}  |  "
      f"adds that stored 0 memories: {add_zero} ({_zpct:.1f}% — a silent empty extraction shows up here)")
print(f"Reported models: extraction={sorted(ex_models) or 'n/a (older trace)'}  "
      f"answerer={sorted(ans_models) or 'n/a'}")
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
# Monitor was started at run begin and is left running.
ensure_monitor
echo "Watch it in the tracer: $MONITOR_URL  (Runs tab)"
echo "Then commit: git add experiments && git commit -m \"run: longmemeval $NAME (mem0 ${MEM0_SHA:0:7})\""
exit "$STATUS"
