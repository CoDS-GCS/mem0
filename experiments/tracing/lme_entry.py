#!/usr/bin/env python3
"""
lme_entry.py — run the LongMemEval benchmark with the eval recorder installed, WITHOUT
editing benchmarks/longmemeval/run.py (which is upstream).

LoCoMo activates the recorder from inside its own run.py; LongMemEval's run.py must stay
untouched, so this launcher applies the hook from the outside: it imports the run module,
installs eval_trace's LongMemEval wrappers on its process_question_* functions, then calls
run.main() exactly as `python -m benchmarks.longmemeval.run` would.

When MEM0_TRACE is off this is a transparent pass-through (no patching, identical behaviour).

Invoked by experiments/run_longmemeval.sh. Must run with the memory-benchmarks dir on the
path (the wrapper sets cwd + PYTHONPATH):

    MEM0_TRACE=1 MEM0_TRACE_DIR=<run folder> \
      python experiments/tracing/lme_entry.py --project-name ... [run.py args]
"""

import importlib
import os
import sys


def main() -> None:
    # Make `benchmarks...` importable even when launched as a file (sys.path[0] is this dir).
    sys.path.insert(0, os.getcwd())

    run_mod = importlib.import_module("benchmarks.longmemeval.run")

    if os.getenv("MEM0_TRACE", "0").strip().lower() in ("1", "true", "yes", "on"):
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import eval_trace
            out = os.getenv("MEM0_TRACE_DIR") or "."
            eval_trace.install_longmemeval(out, run_mod)
            print(f"[lme_entry] MEM0_TRACE on: eval recorder -> {eval_trace.stats().get('path')}",
                  file=sys.stderr)
        except Exception as exc:  # never block the run on tracing
            print(f"[lme_entry] eval recorder failed to install (continuing untraced): {exc}",
                  file=sys.stderr)

    run_mod.main()


if __name__ == "__main__":
    main()
