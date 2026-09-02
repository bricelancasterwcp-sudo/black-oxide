#!/usr/bin/env bash
# Serve one gguf and run one campaign arm; SIGKILL + port-down teardown.
# usage: serve_arm.sh <gguf_path> <arm_name>
set -euo pipefail
#   ROOT / EXTRA_ARGS may be overridden from the environment. Wave 8 needs
#   a separate results root per task set (the same arm name is run against
#   two of them) and passes --tasks/--families through EXTRA_ARGS. Both
#   default to the pre-wave-8 behaviour, so earlier callers are unaffected.
GGUF="$1"; ARM="$2"; PORT=8090; ROOT="${ROOT:-/workspace/results}"
EXTRA_ARGS="${EXTRA_ARGS:-}"
# The harness uses PEP 695 `type` syntax, so it needs python >= 3.12.
# The runpod pytorch images ship 3.11 with torch; merge/convert stay on
# that interpreter, and only the (stdlib-only) eval path moves.
PY="${PY:-python}"
# non-interactive ssh skips ~/.profile: put the oracle and cuda on PATH
export PATH="$HOME/.cargo/bin:/usr/local/cuda/bin:$PATH"
cd /workspace/oxide
SHA=$(sha256sum "$GGUF" | cut -d' ' -f1)
/workspace/llama.cpp/build/bin/llama-server -m "$GGUF" -c 8192 -ngl 99 \
  --jinja --port "$PORT" --host 127.0.0.1 >"/workspace/serve-$ARM.log" 2>&1 &
SERVER=$!
trap 'kill -9 $SERVER 2>/dev/null || true' EXIT
for i in $(seq 1 120); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
  sleep 5
  if [ "$i" = 120 ]; then echo "SERVER-NEVER-HEALTHY" >&2; exit 1; fi
done
"$PY" -m eval.exp_campaign --arm "$ARM" --host "http://127.0.0.1:$PORT" --root "$ROOT" \
  --gguf-sha "$SHA" --llamacpp-commit "$(cat /workspace/llamacpp.commit)" $EXTRA_ARGS
kill -9 $SERVER 2>/dev/null || true
for i in $(seq 1 60); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || break
  sleep 1
done
echo "ARM-DONE $ARM"
