# v0.4 Cost Census

Per-pair oxide/rust token surplus over the committed reference
pairs, ranked. The demand census counts what models attempt; this
counts what correct programs cost. Surplus is signed -- negative
means oxide wins -- and is never clipped.

Tokenizer: `eval/train/tokenizer/tokenizer.json` sha256 `c0382117ea329cdf...`

Dropped (unmeasured, named not zeroed): none

## Ranked by surplus

| task | class | oxide | rust | surplus | ratio |
|---|---|---:|---:|---:|---:|
| n043 | vectors | 142 | 60 | +82 | 2.367 |
| n050 | vectors | 103 | 43 | +60 | 2.395 |
| n045 | vectors | 81 | 41 | +40 | 1.976 |
| n065 | vectors | 81 | 56 | +25 | 1.446 |
| n046 | vectors | 90 | 68 | +22 | 1.324 |
| n054 | strings | 92 | 72 | +20 | 1.278 |
| n064 | structs/option | 73 | 58 | +15 | 1.259 |
| n053 | strings | 48 | 34 | +14 | 1.412 |
| n051 | strings | 49 | 41 | +8 | 1.195 |
| n057 | strings | 65 | 57 | +8 | 1.140 |
| n052 | strings | 46 | 39 | +7 | 1.179 |
| n059 | strings | 39 | 32 | +7 | 1.219 |
| n049 | vectors | 65 | 60 | +5 | 1.083 |
| n010 | arithmetic/loops | 67 | 63 | +4 | 1.063 |
| n001 | arithmetic/loops | 40 | 39 | +1 | 1.026 |
| n002 | arithmetic/loops | 36 | 35 | +1 | 1.029 |
| n003 | arithmetic/loops | 51 | 50 | +1 | 1.020 |
| n005 | arithmetic/loops | 49 | 48 | +1 | 1.021 |
| n008 | arithmetic/loops | 58 | 57 | +1 | 1.018 |
| n004 | arithmetic/loops | 57 | 57 | +0 | 1.000 |
| n007 | arithmetic/loops | 54 | 55 | -1 | 0.982 |
| n009 | arithmetic/loops | 60 | 61 | -1 | 0.984 |
| n006 | arithmetic/loops | 37 | 39 | -2 | 0.949 |
| n067 | vectors | 76 | 78 | -2 | 0.974 |
| n044 | vectors | 50 | 53 | -3 | 0.943 |
| n055 | strings | 50 | 53 | -3 | 0.943 |
| n060 | strings | 76 | 79 | -3 | 0.962 |
| n034 | structs/option | 65 | 69 | -4 | 0.942 |
| n038 | structs/option | 52 | 56 | -4 | 0.929 |
| n041 | vectors | 38 | 42 | -4 | 0.905 |
| n032 | structs/option | 56 | 61 | -5 | 0.918 |
| n037 | structs/option | 48 | 54 | -6 | 0.889 |
| n061 | structs/option | 54 | 60 | -6 | 0.900 |
| n056 | strings | 76 | 83 | -7 | 0.916 |
| n062 | structs/option | 60 | 68 | -8 | 0.882 |
| n066 | vectors | 63 | 72 | -9 | 0.875 |
| n035 | structs/option | 75 | 85 | -10 | 0.882 |
| n040 | structs/option | 61 | 74 | -13 | 0.824 |
| n063 | structs/option | 79 | 92 | -13 | 0.859 |
| n058 | strings | 74 | 88 | -14 | 0.841 |

## Class subtotals

| class | oxide | rust | surplus | ratio |
|---|---:|---:|---:|---:|
| arithmetic/loops | 509 | 504 | +5 | 1.0099 |
| strings | 615 | 578 | +37 | 1.0640 |
| structs/option | 623 | 677 | -54 | 0.9202 |
| vectors | 789 | 573 | +216 | 1.3770 |
| **overall** | **2536** | **2332** | **+204** | **1.0875** |
