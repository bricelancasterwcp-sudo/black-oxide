#!/usr/bin/env bash
# One-time pod setup: repo, deps, llama.cpp CUDA build. Idempotent.
set -euo pipefail
cd /workspace
if [ ! -d oxide ]; then
  git clone https://github.com/bricelancasterwcp-sudo/black-oxide.git oxide
fi
# The eval harness uses PEP 695 `type` syntax and needs python >= 3.12,
# but the pytorch images ship 3.11 with torch. Install 3.12 for the
# (stdlib-only) eval path and leave torch where it is.
if ! command -v python3.12 >/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get update -qq || true
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3.12 || true
fi
# cmake and a compiler are not on every image either.
if ! command -v cmake >/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq cmake build-essential || true
fi

pip install --break-system-packages -q transformers==5.5.0 accelerate==1.14.0 peft==0.20.0 bitsandbytes
# rustc is the harness oracle — the eval side of this pod needs it:
if ! command -v rustc >/dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
  source "$HOME/.cargo/env"
fi
# PINNED. The wave-9 re-screen's tuned-Oxide guard missed its seed-matched
# anchor by one cell because this clone tracked HEAD: the commit moved from
# b96806d (wave 8) to 0f3a71b (wave 9) and one generation on seed 3 came
# out differently with byte-identical weights, sampler and seed. A guard
# that tests the environment must not have the environment moving under it.
LLAMACPP_COMMIT="${LLAMACPP_COMMIT:-b96806d96061049a5b574269b049bf6241d63d46}"
if [ ! -d llama.cpp ]; then
  git clone https://github.com/ggml-org/llama.cpp.git
fi
git -C llama.cpp checkout -q "$LLAMACPP_COMMIT"
if [ ! -x llama.cpp/build/bin/llama-server ]; then
  # the runpod/pytorch image ships nvcc off PATH (learned on pod g41ma10i0c35kv)
  export CUDACXX=/usr/local/cuda/bin/nvcc
  export PATH=/usr/local/cuda/bin:$PATH
  cmake -S llama.cpp -B llama.cpp/build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
  cmake --build llama.cpp/build -j "$(nproc)" --target llama-server llama-quantize
fi
# Conversion deps, AFTER the llama.cpp clone -- an earlier version of this
# installed them first, when llama.cpp/ did not exist yet, and `|| true`
# swallowed the failure until convert_hf_to_gguf.py died mid-campaign.
#
# Install sentencepiece and llama.cpp's OWN gguf-py rather than its
# requirements file: that file moves torch, which strands a torchvision
# built for the old one, and transformers imports torchvision -- surfacing
# as a misleading "Could not import BloomPreTrainedModel". Installing only
# what is missing leaves the CUDA torch untouched.
pip install --break-system-packages -q sentencepiece
pip install --break-system-packages -q ./llama.cpp/gguf-py

git -C llama.cpp rev-parse HEAD > /workspace/llamacpp.commit
python -c "import torch; print(torch.__version__, torch.cuda.get_device_name(0))"
echo SETUP-OK
