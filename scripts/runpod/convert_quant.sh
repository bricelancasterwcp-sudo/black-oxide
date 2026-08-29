#!/usr/bin/env bash
# merged HF dir -> bf16 gguf -> q8_0 gguf, sha recorded.
# usage: convert_quant.sh <merged_dir> <out_name>   (writes /workspace/gguf/<out_name>.q8_0.gguf)
set -euo pipefail
MERGED="$1"; NAME="$2"; OUT=/workspace/gguf
mkdir -p "$OUT"
python /workspace/llama.cpp/convert_hf_to_gguf.py "$MERGED" \
  --outfile "$OUT/$NAME.bf16.gguf" --outtype bf16
/workspace/llama.cpp/build/bin/llama-quantize \
  "$OUT/$NAME.bf16.gguf" "$OUT/$NAME.q8_0.gguf" q8_0
rm "$OUT/$NAME.bf16.gguf"
sha256sum "$OUT/$NAME.q8_0.gguf" | tee -a "$OUT/SHAS.txt"
