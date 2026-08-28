#!/usr/bin/env bash
# One-time pod setup: repo, deps, llama.cpp CUDA build. Idempotent.
set -euo pipefail
cd /workspace
if [ ! -d oxide ]; then
  git clone https://github.com/bricelancasterwcp-sudo/black-oxide.git oxide
fi
pip install --break-system-packages -q peft==0.20.0 bitsandbytes accelerate
# rustc is the harness oracle — the eval side of this pod needs it:
if ! command -v rustc >/dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
  source "$HOME/.cargo/env"
fi
if [ ! -d llama.cpp ]; then
  git clone https://github.com/ggml-org/llama.cpp.git
  cmake -S llama.cpp -B llama.cpp/build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
  cmake --build llama.cpp/build -j "$(nproc)" --target llama-server llama-quantize
fi
git -C llama.cpp rev-parse HEAD > /workspace/llamacpp.commit
python -c "import torch; print(torch.__version__, torch.cuda.get_device_name(0))"
echo SETUP-OK
