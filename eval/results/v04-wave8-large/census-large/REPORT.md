# v0.4 Cost Census

Per-pair oxide/rust token surplus over the committed reference
pairs, ranked. The demand census counts what models attempt; this
counts what correct programs cost. Surplus is signed -- negative
means oxide wins -- and is never clipped.

Source: `large`

Tokenizer: `eval/train/tokenizer/tokenizer.json` sha256 `c0382117ea329cdf...`

Dropped (unmeasured, named not zeroed): none

## Ranked by surplus

| task | class | oxide | rust | surplus | ratio |
|---|---|---:|---:|---:|---:|
| g17 | vectors | 389 | 299 | +90 | 1.301 |
| g02 | strings | 284 | 202 | +82 | 1.406 |
| g10 | strings | 293 | 228 | +65 | 1.285 |
| g07 | strings | 264 | 201 | +63 | 1.313 |
| g20 | arithmetic/loops | 305 | 248 | +57 | 1.230 |
| g08 | vectors | 331 | 308 | +23 | 1.075 |
| g14 | vectors | 304 | 283 | +21 | 1.074 |
| g19 | strings | 272 | 251 | +21 | 1.084 |
| g11 | vectors | 295 | 275 | +20 | 1.073 |
| g03 | structs/option | 364 | 346 | +18 | 1.052 |
| g15 | strings | 258 | 241 | +17 | 1.071 |
| g04 | arithmetic/loops | 249 | 237 | +12 | 1.051 |
| g01 | vectors | 272 | 265 | +7 | 1.026 |
| g09 | arithmetic/loops | 308 | 316 | -8 | 0.975 |
| g13 | arithmetic/loops | 303 | 315 | -12 | 0.962 |
| g12 | structs/option | 231 | 244 | -13 | 0.947 |
| g06 | vectors | 312 | 328 | -16 | 0.951 |
| g16 | arithmetic/loops | 260 | 278 | -18 | 0.935 |
| g05 | structs/option | 292 | 311 | -19 | 0.939 |
| g18 | structs/option | 237 | 306 | -69 | 0.775 |

## Class subtotals

| class | oxide | rust | surplus | ratio |
|---|---:|---:|---:|---:|
| arithmetic/loops | 1425 | 1394 | +31 | 1.0222 |
| strings | 1371 | 1123 | +248 | 1.2208 |
| structs/option | 1124 | 1207 | -83 | 0.9312 |
| vectors | 1903 | 1758 | +145 | 1.0825 |
| **overall** | **5823** | **5482** | **+341** | **1.0622** |

## Stratum subtotals

| stratum | oxide | rust | surplus | ratio |
|---|---:|---:|---:|---:|
| compositional | 3495 | 3261 | +234 | 1.0718 |
| linear | 2328 | 2221 | +107 | 1.0482 |
