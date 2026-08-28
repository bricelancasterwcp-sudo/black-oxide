#!/usr/bin/env bash
# Serve one gguf and run one campaign arm; SIGKILL + port-down teardown.
# usage: serve_arm.sh <gguf_path> <arm_name>
set -euo pipefail
GGUF="$1"; ARM="$2"; PORT=8081; ROOT=/workspace/results
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
python -m eval.exp_campaign --arm "$ARM" --host "http://127.0.0.1:$PORT" --root "$ROOT" \
  --gguf-sha "$SHA" --llamacpp-commit "$(cat /workspace/llamacpp.commit)"
kill -9 $SERVER 2>/dev/null || true
for i in $(seq 1 60); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || break
  sleep 1
done
echo "ARM-DONE $ARM"
