#!/usr/bin/env bash
# One-time pod setup: repo, deps, llama.cpp CUDA build. Idempotent.
set -euo pipefail
cd /workspace
if [ ! -d oxide ]; then
  git clone https://github.com/bricelancasterwcp-sudo/black-oxide.git oxide
fi
# Conversion deps FIRST: llama.cpp's requirements file moves torch, and on
# the pytorch images that leaves a torchvision built for the OLD torch --
# which transformers imports, so every `from peft import ...` dies with a
# misleading "Could not import BloomPreTrainedModel". Nothing here needs
# vision. Order matters: pin transformers/peft AFTER the requirements file
# has had its way with them.
pip install --break-system-packages -q -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt || true
pip uninstall -y -q torchvision || true
pip install --break-system-packages -q transformers==5.5.0 accelerate==1.14.0 peft==0.20.0 bitsandbytes
# rustc is the harness oracle — the eval side of this pod needs it:
if ! command -v rustc >/dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
  source "$HOME/.cargo/env"
fi
if [ ! -d llama.cpp ]; then
  git clone https://github.com/ggml-org/llama.cpp.git
fi
if [ ! -x llama.cpp/build/bin/llama-server ]; then
  # the runpod/pytorch image ships nvcc off PATH (learned on pod g41ma10i0c35kv)
  export CUDACXX=/usr/local/cuda/bin/nvcc
  export PATH=/usr/local/cuda/bin:$PATH
  cmake -S llama.cpp -B llama.cpp/build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
  cmake --build llama.cpp/build -j "$(nproc)" --target llama-server llama-quantize
fi
git -C llama.cpp rev-parse HEAD > /workspace/llamacpp.commit
python -c "import torch; print(torch.__version__, torch.cuda.get_device_name(0))"
echo SETUP-OK
