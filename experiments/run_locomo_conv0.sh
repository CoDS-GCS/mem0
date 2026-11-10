#!/usr/bin/env bash
# One full LoCoMo run on conversation 0: add -> search -> answer -> judge.
#
# Usage:   experiments/run_locomo_conv0.sh <run-name> <mem0-git-ref> [extra benchmark args]
# Examples:
#   experiments/run_locomo_conv0.sh default v2.2.1
#   experiments/run_locomo_conv0.sh eb0     code/entity-boost-0
#   experiments/run_locomo_conv0.sh smoke   v2.2.1 --max-questions 3
#
# Every run ingests the conversation from scratch under its own user id,
# so runs never share memories. Results go to experiments/runs/<date>-locomo-conv0-<name>/.
set -euo pipefail

NAME="${1:?give a run name, e.g. default}"
REF="${2:?give a mem0 git ref, e.g. v2.2.1}"
shift 2

EXP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # .../mem0/experiments
MB="$EXP/memory-benchmarks"
REQ="$MB/docker/mem0/requirements.txt"
PY="$MB/.venv/bin/python"

# Settings (models, ports, keys) come from memory-benchmarks/.env
set -a; source "$MB/.env"; set +a
MEM0_HOST="${MEM0_HOST:-http://localhost:8888}"
ANSWERER_MODEL="${ANSWERER_MODEL:-gpt-5}"
JUDGE_MODEL="${JUDGE_MODEL:-gpt-5}"

# 1. Pin: turn the ref into one exact commit, and make sure GitHub has it
#    (the Docker image installs Mem0 from your fork on GitHub)
MEM0_SHA="$(git -C "$EXP" rev-parse --verify "${REF}^{commit}")"
git -C "$EXP" fetch -q origin
if ! git -C "$EXP" branch -r --contains "$MEM0_SHA" | grep -q "origin/"; then
  echo "ERROR: commit $MEM0_SHA ($REF) is not pushed to your fork yet. Push it first." >&2
  exit 1
fi
FORK_URL="$(git -C "$EXP" remote get-url origin | sed -E 's#^git@github.com:#https://github.com/#')"

RUN_DIR="$EXP/runs/$(date +%Y-%m-%d_%H%M)-locomo-conv0-$NAME"
mkdir -p "$RUN_DIR"
echo "Run folder: $RUN_DIR"
echo "Mem0 code:  $REF = $MEM0_SHA"

# 2. Point the Mem0 server at that commit, rebuild, start
sed -i -E "s|^mem0ai @ git\+.*|mem0ai @ git+${FORK_URL}@${MEM0_SHA}|" "$REQ"
cd "$MB"
docker compose build mem0
docker compose up -d
echo -n "Waiting for Mem0 server"
for _ in $(seq 1 90); do
  curl -sf "$MEM0_HOST/health" >/dev/null 2>&1 && break
  echo -n "."; sleep 2
done
echo
curl -sf "$MEM0_HOST/health" >/dev/null || { echo "ERROR: server not healthy at $MEM0_HOST" >&2; exit 1; }
START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 3. Record exactly what this run uses
cat > "$RUN_DIR/manifest.json" <<EOF
{
  "run_name": "$NAME",
  "benchmark": "locomo",
  "conversations": "0",
  "mem0_ref": "$REF",
  "mem0_commit": "$MEM0_SHA",
  "experiments_commit": "$(git -C "$EXP" rev-parse HEAD)",
  "benchmarks_upstream_commit": "$(git -C "$EXP" log -1 --format=%b --grep='git-subtree-dir: experiments/memory-benchmarks' | sed -n 's/^git-subtree-split: //p')",
  "extraction_llm": "${LLM_MODEL:-gpt-4o-mini}",
  "embedder": "${EMBEDDER_MODEL:-text-embedding-3-small}",
  "answerer_model": "$ANSWERER_MODEL",
  "judge_model": "$JUDGE_MODEL",
  "extra_args": "$*",
  "started_utc": "$START"
}
EOF
cp "$REQ" "$RUN_DIR/server_requirements.txt"
docker compose images > "$RUN_DIR/docker_images.txt"

# 4. The run itself
set +e
"$PY" -m benchmarks.locomo.run \
  --project-name "locomo-conv0-$NAME" \
  --conversations 0 \
  --score-debug \
  --answerer-model "$ANSWERER_MODEL" \
  --judge-model "$JUDGE_MODEL" \
  --mem0-host "$MEM0_HOST" \
  --output-dir "$RUN_DIR" \
  "$@" 2>&1 | tee "$RUN_DIR/console.log"
STATUS=${PIPESTATUS[0]}
set -e

# 5. Keep the server log and check for silent problems
docker compose logs --no-color --since "$START" mem0 > "$RUN_DIR/server.log" 2>&1 || true
grep -q "BM25 keyword search disabled" "$RUN_DIR/server.log" && echo "WARNING: BM25 was OFF in this run (fastembed missing)."
grep -q "BM25 encoder loaded" "$RUN_DIR/server.log" && echo "OK: BM25 was on."
N_FAIL=$(grep -c "search() failed\|add() failed" "$RUN_DIR/server.log" || true)
[ "$N_FAIL" -gt 0 ] && echo "WARNING: $N_FAIL failed add/search calls - see server.log"

# 6. Print the J score
"$PY" - "$RUN_DIR" <<'EOF'
import glob, json, sys
files = sorted(glob.glob(f"{sys.argv[1]}/locomo_results_*.json"))
if not files:
    print("No results file (run failed or --predict-only)."); sys.exit()
m = json.load(open(files[-1]))["metrics_by_cutoff"]
for cut in ("top_200", "top_50", "top_20", "top_10"):
    if cut in m:
        o = m[cut]["overall"]
        print(f"J @ {cut}: {o['accuracy']:.1f}  ({o['correct']}/{o['total']})")
        if cut == "top_200":
            for cat, c in m[cut]["by_category"].items():
                print(f"    {cat:<14} {c['accuracy']:.1f}  ({c['correct']}/{c['total']})")
EOF

echo
echo "Next: add a row to experiments/RUNS.md, then commit:"
echo "  git add experiments && git commit -m \"run: locomo conv0 $NAME (mem0 ${MEM0_SHA:0:7})\" && git push"
exit "$STATUS"
