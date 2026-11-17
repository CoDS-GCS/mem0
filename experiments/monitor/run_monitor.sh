#!/usr/bin/env bash
# run_monitor.sh — build the LongMemEval index if missing, then start the monitor.
# Read-only: never runs the benchmark or the Mem0 server.
#
#   ./run_monitor.sh            # http://127.0.0.1:8020
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${LME_VENV:-/shared_mnt/loubna/venv-analysis}"
PY="$VENV/bin/python"
HOST="${LME_HOST:-127.0.0.1}"
PORT="${LME_PORT:-8020}"
DB="$HERE/longmemeval.sqlite"
DATASET="${LME_DATASET:-$HERE/../data/longmemeval_s_cleaned.json}"

if [ ! -x "$PY" ]; then
  echo "Python venv not found at $VENV (set LME_VENV)." >&2
  exit 1
fi

# Dependencies.
if ! "$PY" -c "import fastapi, uvicorn" 2>/dev/null; then
  echo "Installing fastapi + uvicorn into $VENV ..."
  "$VENV/bin/pip" install -q fastapi uvicorn
fi

# Index.
if [ ! -f "$DB" ]; then
  if [ ! -f "$DATASET" ]; then
    echo "Dataset missing: $DATASET (see experiments/data/README to fetch it)." >&2
    exit 1
  fi
  echo "Building index (one-time) ..."
  "$PY" "$HERE/build_index.py" --dataset-path "$DATASET" --db "$DB"
fi

echo "LongMemEval monitor → http://$HOST:$PORT"
cd "$HERE"
exec "$VENV/bin/uvicorn" app:app --host "$HOST" --port "$PORT"
