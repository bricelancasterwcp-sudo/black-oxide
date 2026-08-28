# Matched training corpus — build record

2026-08-27 (build date). Spec:
docs/superpowers/specs/2026-08-27-token-matching-design.md. Built by
`python -m eval.token_match` at commit
9c899da4e9fad78a24b074977233cec44fd7f405.

Rebuilt 2026-08-27 as part of a fix wave (finding F1): the kept-filter
in `build_matched` removed rows by `(task, sha256)` membership in the
dropped-amplified set without checking `source`, so whenever an
amplified program was byte-identical to its own task's reference
(same normalized text, hence same sha256), the filter struck the
reference too — silently, in violation of spec decision 5
("references never trimmed"). This had happened twice in the prior
committed corpus: oxide task n032 (structs/option) and rust task n052
(strings) each carried 39 reference rows instead of 40. The filter now
additionally requires `source == "amplified"`; both references are
restored below.

## Budgets

| class | budget (sup tokens) | oxide kept (tok / n) | rust kept (tok / n) | gap | step |
|---|---|---|---|---|---|
| arithmetic/loops | 7074 | 7074 / 103 | 7033 / 135 | 41 | 104 |
| strings | 1566 | 1566 / 20 | 1537 / 26 | 29 | 162 |
| structs/option | 4814 | 4783 / 66 | 4814 / 72 | 31 | 145 |
| vectors | 3802 | 3802 / 40 | 3735 / 59 | 67 | 202 |
| **total** | **17256** | **17225 / 229** | **17119 / 292** | — | — |

The totals row omits a single "gap" cell on purpose. The four
per-class gaps sum to 168 tokens (41+29+31+67), but that sum is not a
corpus-level measurement — it adds four independent per-class
quantization artifacts as if they pointed the same way. They don't:
rust is the short arm in three classes (arithmetic/loops, strings,
vectors) and oxide is the short arm in the fourth (structs/option), so
at the corpus level the shortfalls partly cancel rather than
accumulate. The actual corpus-level kept-token difference is
|17225 − 17119| = **106 tokens**, distinct from and smaller than the
168-token sum of per-class gaps. Neither number is wrong; they answer
different questions (worst-case per-class quantization loss added up,
versus the net token count the two arms actually differ by), and only
the second is a real aggregate.

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
references versus about 29% larger in amplified — concentrated in
vectors and strings, where oxide's amplified mean rises while rust's
falls relative to their own references. One class inverts the overall
pattern: structs/option has oxide smaller than rust in references
(62.5 vs 67.7) but oxide larger than rust in amplified (73.29 vs
66.73), the only class where direction flips between the two sections.

## Guards

Contamination: 0 hits over 521 kept programs.
Tokenizer pin: c0382117ea32, attested from 3 checkpoints
(eval/train/tokenizer/provenance.json).

`counts_source.commit` in manifest.json records the git HEAD at build
time — the code state that produced this corpus — not the commit that
ships this corpus. It cannot record the latter: that commit does not
exist yet when the build runs, so the field structurally always trails
by one commit for a build-then-commit workflow (F3, noted rather than
engineered around).
