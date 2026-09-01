#!/usr/bin/env bash
# Wave 8 Phase B: five arms, no training, no amplification.
# Plan: docs/superpowers/plans/2026-09-01-v04-wave8-phaseb-plan.md
#
# Reuses the preserved v5 adapters. Each stage is skipped if its output
# already exists, so a dropped ssh session resumes rather than restarts.
set -euo pipefail
export PATH="$HOME/.cargo/bin:/usr/local/cuda/bin:$PATH"
BASE_DIR=/workspace/base-7
GGUF=/workspace/gguf
ART=/workspace/artifacts
cd /workspace/oxide

step () { echo "=== $(date -u +%H:%M:%S) $* ==="; }

# ---------------------------------------------------------------- weights
# The base is fetched ONCE to a local dir and used both for its own GGUF
# and as merge_lora's --base. Passing the HF id to merge_lora instead
# would pull the same ~15GB a second time.
if [ ! -d "$BASE_DIR" ]; then
  step "download base 7B"
  python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("Qwen/Qwen2.5-Coder-7B-Instruct",
                  local_dir="/workspace/base-7")
PY
fi
if [ ! -f "$GGUF/base-7.q8_0.gguf" ]; then
  step "convert base 7B"
  bash scripts/runpod/convert_quant.sh "$BASE_DIR" base-7
fi

for lang in ox rs; do
  if [ ! -f "$GGUF/tune-$lang-7.q8_0.gguf" ]; then
    step "merge + convert tune-$lang-7 (v5 adapter)"
    python scripts/runpod/merge_lora.py \
      --base "$BASE_DIR" \
      --adapter "$ART/adapters-v5/tune-$lang-7-v5" \
      --out "/workspace/merged-$lang-7"
    bash scripts/runpod/convert_quant.sh "/workspace/merged-$lang-7" "tune-$lang-7"
    rm -rf "/workspace/merged-$lang-7"
  fi
done

# ------------------------------------------------------------------- arms
# Order matters: the drift guard runs FIRST. If base-rs-7 misses 0.565 the
# environment is not comparable and nothing after it is worth paying for.
step "arm 5/5 first: base-rs-7 @ eval (drift guard)"
ROOT=/workspace/results-small EXTRA_ARGS="--families gen" \
  bash scripts/runpod/serve_arm.sh "$GGUF/base-7.q8_0.gguf" base-rs-7

for lang in ox rs; do
  step "tune-$lang-7 @ large"
  ROOT=/workspace/results-large \
  EXTRA_ARGS="--families gen --tasks eval/tasks-large.jsonl" \
    bash scripts/runpod/serve_arm.sh "$GGUF/tune-$lang-7.q8_0.gguf" "tune-$lang-7"
done

for lang in ox rs; do
  step "tune-$lang-7 @ eval (small)"
  ROOT=/workspace/results-small EXTRA_ARGS="--families gen" \
    bash scripts/runpod/serve_arm.sh "$GGUF/tune-$lang-7.q8_0.gguf" "tune-$lang-7"
done

step "ALL-ARMS-DONE"
