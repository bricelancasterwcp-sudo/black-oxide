# v0.4 Cost Census

Per-pair oxide/rust token surplus over the committed reference
pairs, ranked. The demand census counts what models attempt; this
counts what correct programs cost. Surplus is signed -- negative
means oxide wins -- and is never clipped.

Source: `eval`

Tokenizer: `eval/train/tokenizer/tokenizer.json` sha256 `c0382117ea329cdf...`

Dropped (unmeasured, named not zeroed): none

## Ranked by surplus

| task | class | oxide | rust | surplus | ratio |
|---|---|---:|---:|---:|---:|
| t13 | strings | 83 | 61 | +22 | 1.361 |
| t16 | structs/option | 122 | 106 | +16 | 1.151 |
| t12 | strings | 42 | 31 | +11 | 1.355 |
| t06 | arithmetic/loops | 73 | 68 | +5 | 1.074 |
| t01 | arithmetic/loops | 41 | 38 | +3 | 1.079 |
| t04 | arithmetic/loops | 97 | 94 | +3 | 1.032 |
| t05 | arithmetic/loops | 67 | 65 | +2 | 1.031 |
| t17 | structs/option | 51 | 53 | -2 | 0.962 |
| t02 | arithmetic/loops | 77 | 80 | -3 | 0.963 |
| t03 | arithmetic/loops | 55 | 58 | -3 | 0.948 |
| t15 | strings | 81 | 85 | -4 | 0.953 |
| t07 | arithmetic/loops | 42 | 50 | -8 | 0.840 |
| t09 | vectors | 34 | 43 | -9 | 0.791 |
| t19 | structs/option | 53 | 62 | -9 | 0.855 |
| t14 | strings | 73 | 83 | -10 | 0.880 |
| t11 | vectors | 37 | 48 | -11 | 0.771 |
| t08 | vectors | 52 | 67 | -15 | 0.776 |
| t10 | vectors | 56 | 75 | -19 | 0.747 |
| t18 | structs/option | 115 | 138 | -23 | 0.833 |
| t20 | structs/option | 156 | 182 | -26 | 0.857 |

## Class subtotals

| class | oxide | rust | surplus | ratio |
|---|---:|---:|---:|---:|
| arithmetic/loops | 452 | 453 | -1 | 0.9978 |
| strings | 279 | 260 | +19 | 1.0731 |
| structs/option | 497 | 541 | -44 | 0.9187 |
| vectors | 179 | 233 | -54 | 0.7682 |
| **overall** | **1407** | **1487** | **-80** | **0.9462** |
