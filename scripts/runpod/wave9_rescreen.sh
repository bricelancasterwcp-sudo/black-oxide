#!/usr/bin/env bash
# Wave 9 re-screen: the wave-8 14B screen pipeline, UNCHANGED, run against
# the v04-wave9-index-syntax transpiler. Only the language moved.
# Plan: docs/superpowers/plans/2026-09-02-v04-wave9-rescreen-plan.md
#
# Runs ON THE POD, OS-detached (setsid nohup). Terminal states are
# distinguishable: /workspace/.DONE on success, /workspace/.FAILED on any
# non-zero exit, neither while running. A watcher on the workstation
# polls marker-or-death; silence is never read as success.
#
# Prerequisites placed by the workstation before launch:
#   /workspace/pod_setup.sh              (from scripts/runpod/, main == branch)
#   /workspace/artifacts/adapters-v5/tune-{ox,rs}-14-v5/   (tar over ssh)
#   /workspace/artifacts/SHAS-v5-14.txt  (the two expected content hashes)
set -euo pipefail
EXPECT_COMMIT="${EXPECT_COMMIT:?set to the pushed head of the wave-9 branch}"
BRANCH=v04-wave9-index-syntax
trap 'rc=$?; if [ "$rc" -ne 0 ]; then echo "FAILED rc=$rc at $(date -u +%H:%M:%S)"; touch /workspace/.FAILED; fi' EXIT
cd /workspace

echo "=== $(date -u +%H:%M:%S) cuda driver check (stop 3 of the plan) ==="
# nvidia-smi working is NOT evidence: pod bf1mt4qibzo9tw listed the GPU and
# returned CUDA_ERROR_UNKNOWN (999) from cuInit. Ask the driver directly.
python - <<'PY'
import ctypes, sys
lib = ctypes.CDLL("libcuda.so.1")
rc = lib.cuInit(0)
print("cuInit ->", rc)
sys.exit(0 if rc == 0 else 1)
PY

echo "=== $(date -u +%H:%M:%S) pod setup ==="
bash /workspace/pod_setup.sh

echo "=== $(date -u +%H:%M:%S) checkout $BRANCH ==="
cd /workspace/oxide
git fetch -q origin "$BRANCH"
git checkout -q "$BRANCH"
git reset -q --hard "origin/$BRANCH"
HEAD=$(git rev-parse HEAD)
[ "$HEAD" = "$EXPECT_COMMIT" ] || { echo "WRONG-COMMIT $HEAD != $EXPECT_COMMIT"; exit 1; }
echo "at $HEAD"

echo "=== $(date -u +%H:%M:%S) adapter content hashes (count-verify is not sufficient) ==="
(cd /workspace/artifacts && sha256sum -c SHAS-v5-14.txt)

echo "=== $(date -u +%H:%M:%S) screen (wave-8 pipeline verbatim) ==="
bash scripts/runpod/wave8_14b_screen.sh

touch /workspace/.DONE
echo "=== $(date -u +%H:%M:%S) DONE ==="
