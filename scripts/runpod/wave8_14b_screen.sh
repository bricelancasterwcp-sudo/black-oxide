#!/usr/bin/env bash
# Wave 8 14B screen: 4 arms, 3 seeds, no training.
# Plan: docs/superpowers/plans/2026-09-01-v04-wave8-14b-screen-plan.md
#
# Convert straight to q8_0 rather than via bf16: the 14B bf16 intermediate
# is ~29.5GB and pushes peak disk past 120GB for no benefit here.
set -euo pipefail
export PATH="$HOME/.cargo/bin:/usr/local/cuda/bin:$PATH"
BASE_DIR=/workspace/base-14
GGUF=/workspace/gguf
ART=/workspace/artifacts
SEEDS=1,2,3
cd /workspace/oxide

step () { echo "=== $(date -u +%H:%M:%S) $* ==="; }

export PY="${PY:-python3.12}"
"$PY" -c "import sys; assert sys.version_info >= (3, 12), sys.version" \
  || { echo "NEED-PY312"; exit 1; }

df -h /workspace | tail -1

# ---------------------------------------------------------------- weights
if [ ! -d "$BASE_DIR" ]; then
  step "download base 14B"
  python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("Qwen/Qwen2.5-Coder-14B-Instruct",
                  local_dir="/workspace/base-14")
PY
fi

quant_direct () {  # <src_dir> <name>
  local src="$1" name="$2"
  python /workspace/llama.cpp/convert_hf_to_gguf.py "$src" \
    --outfile "$GGUF/$name.q8_0.gguf" --outtype q8_0
  sha256sum "$GGUF/$name.q8_0.gguf" | tee -a "$GGUF/SHAS.txt"
}

mkdir -p "$GGUF"
if [ ! -f "$GGUF/base-14.q8_0.gguf" ]; then
  step "convert base 14B -> q8_0 (direct, no bf16 intermediate)"
  quant_direct "$BASE_DIR" base-14
fi

for lang in ox rs; do
  if [ ! -f "$GGUF/tune-$lang-14.q8_0.gguf" ]; then
    step "merge + convert tune-$lang-14 (v5 adapter)"
    python scripts/runpod/merge_lora.py \
      --base "$BASE_DIR" \
      --adapter "$ART/adapters-v5/tune-$lang-14-v5" \
      --out "/workspace/merged-$lang-14"
    quant_direct "/workspace/merged-$lang-14" "tune-$lang-14"
    rm -rf "/workspace/merged-$lang-14"
    df -h /workspace | tail -1
  fi
done

# ------------------------------------------------------------------- arms
# Guards first: a bad environment or a bad merge invalidates everything
# after, and both are cheap to detect.
step "guard 1/2: base-rs-14 @ eval (anchor 0.5500 on seeds 1-3)"
ROOT=/workspace/results-small EXTRA_ARGS="--families gen --seeds $SEEDS" \
  bash scripts/runpod/serve_arm.sh "$GGUF/base-14.q8_0.gguf" base-rs-14

step "guard 2/2: tune-ox-14 @ eval (anchor 0.8000 on seeds 1-3)"
ROOT=/workspace/results-small EXTRA_ARGS="--families gen --seeds $SEEDS" \
  bash scripts/runpod/serve_arm.sh "$GGUF/tune-ox-14.q8_0.gguf" tune-ox-14

for lang in ox rs; do
  step "tune-$lang-14 @ large"
  ROOT=/workspace/results-large \
  EXTRA_ARGS="--families gen --seeds $SEEDS --tasks eval/tasks-large.jsonl" \
    bash scripts/runpod/serve_arm.sh "$GGUF/tune-$lang-14.q8_0.gguf" "tune-$lang-14"
done

step "ALL-ARMS-DONE"
