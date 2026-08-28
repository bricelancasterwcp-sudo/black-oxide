# Matched training corpus — build record

2026-08-27 (build date). Spec:
docs/superpowers/specs/2026-08-27-token-matching-design.md. Built by
`python -m eval.token_match` at commit
a17199f018638c522c05814478c932336a03434f.

## Budgets

| class | budget (sup tokens) | oxide kept (tok / n) | rust kept (tok / n) | gap | step |
|---|---|---|---|---|---|
| arithmetic/loops | 7074 | 7074 / 103 | 7033 / 135 | 41 | 104 |
| strings | 1566 | 1566 / 20 | 1498 / 25 | 68 | 162 |
| structs/option | 4814 | 4727 / 65 | 4814 / 72 | 87 | 145 |
| vectors | 3802 | 3802 / 40 | 3735 / 59 | 67 | 202 |
| **total** | **17256** | **17169 / 228** | **17080 / 291** | 263 (sum) | — |

Dropped: 141 examples (22 oxide, 119 rust) — full list in
manifest.json, named not deleted. By class: arithmetic/loops 14 (all
rust), strings 51 (all rust), structs/option 22 (all oxide), vectors
54 (all rust).

## Token efficiency (pre-trim estimand, pinned Qwen tokenizer)

| class | refs oxide | refs rust | amplified oxide | amplified rust |
|---|---|---|---|---|
| arithmetic/loops | 52.3 (n=10) | 50.4 (n=10) | 70.44 (n=93) | 52.84 (n=139) |
| strings | 72.5 (n=10) | 57.8 (n=10) | 84.1 (n=10) | 52.39 (n=67) |
| structs/option | 62.5 (n=10) | 67.7 (n=10) | 73.29 (n=78) | 66.73 (n=62) |
| vectors | 97.4 (n=10) | 57.3 (n=10) | 94.27 (n=30) | 65.21 (n=103) |
| **overall** | **71.17 (n=40)** | **58.3 (n=40)** | **75.53 (n=211)** | **58.51 (n=371)** |

The references and amplified comparisons agree in direction rather
than opposing: rust programs use fewer supervised tokens than oxide
programs on average in both sets (71.17 vs 58.3 references, 75.53 vs
58.51 amplified), so the character-count-derived hint that they might
point opposite ways (spec decision 10) did not hold at the token
level. The gap is somewhat wider under amplification than in the
hand-authored references — oxide runs about 22% larger than rust in
references versus about 29% larger in amplified — driven mostly by
vectors and strings, where oxide's amplified mean rises while rust's
falls relative to their own references. One class inverts the overall
pattern: structs/option has oxide smaller than rust in references
(62.5 vs 67.7) but oxide larger than rust in amplified (73.29 vs
66.73), the only class where direction flips between the two sections.

## Guards

Contamination: 0 hits over 519 kept programs.
Tokenizer pin: c0382117ea32, attested from 3 checkpoints
(eval/train/tokenizer/provenance.json).
