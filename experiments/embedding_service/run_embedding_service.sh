#!/usr/bin/env bash
# run_embedding_service.sh — start the local Qwen3-Embedding-0.6B TEI-compatible service.
#
# Keep this running in tmux; run_longmemeval.sh health-checks it before a run and refuses
# to start if it is down. Everything (venv, pip cache, HF weights, tmp) lives on /shared_mnt
# because / has < 1 GB free. Binds an internal port only; Docker reaches it via host-gateway.
#
#   experiments/embedding_service/run_embedding_service.sh
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Caches + venv on /shared_mnt (root disk is full).
export HF_HOME="${HF_HOME:-/shared_mnt/loubna/embed-cache/hf}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/shared_mnt/loubna/embed-cache/pip}"
export TMPDIR="${TMPDIR:-/shared_mnt/loubna/embed-cache/tmp}"
export HF_HUB_DISABLE_TELEMETRY=1
mkdir -p "$HF_HOME" "$PIP_CACHE_DIR" "$TMPDIR"

VENV="${EMBED_VENV:-/shared_mnt/loubna/venv-embed}"
PY="$VENV/bin/python"
HOST="${EMBED_HOST:-0.0.0.0}"     # reachable by the mem0 container via host-gateway; VM-internal
PORT="${EMBED_PORT:-8099}"

export QWEN_MODEL_ID="${QWEN_MODEL_ID:-Qwen/Qwen3-Embedding-0.6B}"
export QWEN_MODEL_REVISION="${QWEN_MODEL_REVISION:-97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3}"
export QWEN_DEVICE="${QWEN_DEVICE:-cuda}"

if [ ! -x "$PY" ]; then
  echo "Embed venv not found at $VENV (set EMBED_VENV). Create it and install:" >&2
  echo "  python3 -m venv $VENV && PIP_CACHE_DIR=$PIP_CACHE_DIR $VENV/bin/pip install torch transformers sentence-transformers fastapi uvicorn huggingface_hub" >&2
  exit 1
fi

echo "Qwen embedding service (TEI-compatible)"
echo "  model:    $QWEN_MODEL_ID @ $QWEN_MODEL_REVISION"
echo "  device:   $QWEN_DEVICE   |   bind: http://$HOST:$PORT   (internal)"
echo "  HF_HOME:  $HF_HOME"
cd "$HERE"
exec "$VENV/bin/uvicorn" serve_qwen_tei:app --host "$HOST" --port "$PORT"
