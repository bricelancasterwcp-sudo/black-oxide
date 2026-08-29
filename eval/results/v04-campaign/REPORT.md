# v0.4 efficiency cycle, wave 1 — full-loop report

2026-08-28. Spec: `docs/superpowers/specs/2026-08-28-v04-efficiency-wave1-design.md`.
This is the committed home of the wave's endpoint readings, guard
reads, uptake counts, and the feed-forward to wave 2. Metric
constructions are stated as computed. This report ends with the
feed-forward section — the cycle's output is the next cycle's input.

## What shipped (the design change under measurement)

Builtins `sort`, `min`, `max`, `sum`, `contains`, `unwrap_or` (census-
gated; spellings picked by measured model demand); the **builtin
shadowing rule** (user `fn` wins program-wide — deferred-demand
dossier 4, finally measured when our own frozen corpus collided with
the new vocabulary); card v0.4 (895→988 / 980→1082 words, mirrored);
`range(a,b)` found pre-existing and pinned by tests. Deferred with
counts: `..` ranges (292), `if let` (35→89 on the card arm, rising),
index assignment (28/0), strings vocabulary (4).

## Static endpoints (primary; reference pairs, pinned tokenizer)

Constructions: mean supervised tokens per hand-authored reference
program, oxide/rust, identical tasks and stdout; targets are chosen
design goals. After the bias-rule fix round (an n041 tightening was
caught by review and reverted — honest numbers below):

| class | wave-0 | wave-1 | target | verdict |
|---|---:|---:|---|---|
| arithmetic/loops | 1.04 | 1.038 | 1.04 ± 0.05 | HIT |
| structs/option | 0.92 | 0.923 | ≤ 1.00 | HIT |
| strings | 1.25 | 1.159 | (untouched expected) | improved via Option/vec vocab |
| vectors | 1.70 | **1.389** | ≤ 1.15 | **MISS** |
| overall | 1.22 | **1.121** | ≤ 1.10 | **MISS** |

Both misses are stated as misses. The strings improvement without
string vocabulary is a finding: class labels do not bound vocabulary
domains. Only 8 of 40 references qualified for substitution under the
bias rules; the vectors residual is characterized below.

## Dynamic loop (4090 pod, $0.34/h; 4 arms × [200 gen + 200 repair] on t01–t20)

Corpus caveat (recorded BEFORE reading results): the v0.4 re-amplified
pool yielded 74/98 unique verified programs (vs wave-0's 211/371 —
one family, one run, replicate collapse at temp 0.2), so matched-v2 ≈
7.4k supervised tokens/arm vs wave-0's 17k. Both tuned arms retrained
symmetrically on matched-v2 (the wave-0 rust adapter was lost to a
truncated backup — preservation failure recorded in the evidence;
symmetric retrain is the cleaner design regardless).

| arm | pass@1 | pass@10v | tok→green | censored | strict repair |
|---|---:|---:|---:|---:|---:|
| base-ox-7 (card v0.4) | 0.025 | 0.10 | 83.4 | 195 | 0.455 |
| base-rs-7 (control) | **0.565** | 0.65 | 65.7 | 87 | 0.895 |
| tune-ox-7-v2 | 0.420 | 0.70 | 81.5 | 97 | 0.530 |
| tune-rs-7-v2 | 0.885 | 0.95 | 72.3 | 18 | 0.705 |

- **Control: 0.565 — byte-exact across all three environments to date**
  (local Vulkan v03c, wave-0 3090, wave-1 4090). Band PASS.
- **G1 floor (tune-ox-7 ≥ 0.455): TRIPPED at 0.420 — diagnosed as a
  corpus-size artifact, not a language regression.** Evidence, in the
  pre-registered diagnosis order: the control is exact; tune-rs-7-v2
  reproduced wave-0's 0.885 to the digit on 43% of the data (the prior
  carries rust; corpus size barely matters for it); the oxide arm's
  train loss rose 0.199→0.360 (undertrained); pass@10-with-verifier
  held at wave-0's 0.70 and strict repair improved 0.455→0.530. The
  floor was derived against a 17k-token training run and compared
  against a 7.4k-token one — the comparison the floor imagined is not
  the one that ran. The corpus-size sensitivity asymmetry (novel
  language degrades, prior language doesn't) is itself a wave finding.
- **Token efficiency (the objective): tokens-to-green ratio 81.5/72.3
  = 1.13, down from wave-0's 1.24.** The dynamic read moved the same
  direction as the static one.

  > **ERRATUM, 2026-08-29 (wave 2).** The claim in this bullet does not
  > hold. The arithmetic above is correct, but each arm's mean is taken
  > over *its own* green sessions, and this wave's oxide arm solved
  > fewer and easier cells (pass@1 0.420 vs wave-0's 0.555) — so the
  > mean fell for a reason that is not efficiency. Under a construction
  > that controls composition (pair cells by (seed, task), keep only
  > cells green in both arms, restrict to the 67 cells green in every
  > wave), wave 1 was **worse** than wave 0, not better: **1.293 vs
  > 1.217**. The values above are left visible as published. See
  > `eval/results/v04-campaign2/REPORT.md` for the full three-wave
  > table and the replacement estimand wave 3 pre-registers.
- **G2 uptake: PASS — no dead vocabulary.** Card arm (re-amplification
  replies, per-file counts): sort 212, unwrap_or 120, min/max 90,
  contains 72, sum 40 — every construct used when taught. Tuned arm
  (campaign replies): ranges 121, sum 16, sort 10, minmax 5,
  unwrap_or 5 — all live at 7.4k training tokens. `if let` demand rose
  to 89 on the card arm (was 35), strengthening its wave-2 case.
- Known-defect attribution line (pre-registered): the Vec<Struct>
  derive gap (contains/sort/min/max on struct vectors can emit
  non-compiling Rust) fails closed and depresses only oxide arms; no
  campaign reply was observed to hit it, but any such failure is a
  language-surface defect, not model error.

## Spend

Wave-1 loop: ≈ $1.82 (5.26h × $0.34 + a stuck pod). Program total
across both waves ≈ **$3.40** of the $23 tranche.

## Feed-forward to wave 2

1. **Vectors residual (1.389 vs 1.15):** the remaining hand-rolled
   patterns are occurrence counting (4 tasks), removal/rebuild loops
   (needs `remove`/index assignment — deferred family, bracket
   spelling 28), and n044/n067 accumulation shapes. Candidate wave-2
   vec vocabulary: `count(v, x)`, `remove_at(v, i)` or index
   assignment, possibly `filter`-shaped iteration.
2. **Strings (1.159, now the second-largest class residual):** wave-2
   scope per the design spec; card-arm strings demand remains low
   (format 4) — census the strings-class hand-rolled patterns
   directly rather than reply demand.
3. **`if let`: demand rose 35 → 89** once the card taught more Option
   vocabulary; re-gate for wave 2.
4. **Census instrument upgrades (from this wave's gaps):** add a
   rejection cross-check (pattern presence ∩ compile-failure at the
   construct — the `range(a,b)` lesson) and a compound-assignment
   family (`+=` does not exist in the language and appears in failing
   replies; never censused).
5. **Amplification scale:** the 7.4k-token corpus undertrained the
   oxide arm. Wave 2's loop should amplify at K≥60 (more seeds and/or
   families) or pool waves' verified programs to restore ≥ wave-0
   corpus scale before the next tuned read; the G1 floor stays 0.455
   and should be met, not re-derived, at restored scale.
6. **Shadowing × §55 vec-literal desugar seam** recorded in SPEC §58.2
   (user `fn push`/`fn vec` capture desugared chains) — revisit only
   if census shows real demand for those names.
