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
| g02 | strings | 284 | 202 | +82 | 1.406 |
| g10 | strings | 293 | 228 | +65 | 1.285 |
| g07 | strings | 259 | 201 | +58 | 1.289 |
| g19 | strings | 272 | 251 | +21 | 1.084 |
| g03 | structs/option | 364 | 346 | +18 | 1.052 |
| g17 | vectors | 315 | 299 | +16 | 1.054 |
| g11 | vectors | 288 | 275 | +13 | 1.047 |
| g20 | arithmetic/loops | 261 | 248 | +13 | 1.052 |
| g08 | vectors | 317 | 308 | +9 | 1.029 |
| g01 | vectors | 272 | 265 | +7 | 1.026 |
| g04 | arithmetic/loops | 241 | 237 | +4 | 1.017 |
| g14 | vectors | 283 | 283 | +0 | 1.000 |
| g09 | arithmetic/loops | 308 | 316 | -8 | 0.975 |
| g15 | strings | 232 | 241 | -9 | 0.963 |
| g13 | arithmetic/loops | 303 | 315 | -12 | 0.962 |
| g12 | structs/option | 231 | 244 | -13 | 0.947 |
| g06 | vectors | 312 | 328 | -16 | 0.951 |
| g16 | arithmetic/loops | 260 | 278 | -18 | 0.935 |
| g05 | structs/option | 292 | 311 | -19 | 0.939 |
| g18 | structs/option | 237 | 306 | -69 | 0.775 |

## Class subtotals

| class | oxide | rust | surplus | ratio |
|---|---:|---:|---:|---:|
| arithmetic/loops | 1373 | 1394 | -21 | 0.9849 |
| strings | 1340 | 1123 | +217 | 1.1932 |
| structs/option | 1124 | 1207 | -83 | 0.9312 |
| vectors | 1787 | 1758 | +29 | 1.0165 |
| **overall** | **5624** | **5482** | **+142** | **1.0259** |

## Stratum subtotals

| stratum | oxide | rust | surplus | ratio |
|---|---:|---:|---:|---:|
| compositional | 3461 | 3261 | +200 | 1.0613 |
| linear | 2163 | 2221 | -58 | 0.9739 |
