# Wave 9 re-screen — does shipping `[` move the compile rate?

**Date:** 2026-09-02. Branch `v04-wave9-index-syntax`.
**Written and committed BEFORE the pod is provisioned.**
Baseline: `eval/results/v04-wave8-14b-screen/REPORT.md`.
Construct: SPEC 65, `eval/results/v04-wave9-index/REPORT.md`.

## The design is unusually clean

**The model is fixed and only the language moved.** The v5 adapters are
unchanged and were trained on a corpus with no `[` at all; the tuned
arms are card-free (`include_lead=False`), so they never see the updated
card either. The model writes `[` because Rust and Python taught it to,
not because Oxide did — 29.0% of its large-tier attempts contained one,
and every such attempt died at `OX0001` before type checking ran.

So this run changes exactly one thing: whether those attempts get past
the lexer. Nothing else about the arms, seeds, anchors, weights, or
prompts differs from the wave-8 screen.

## Arms

Identical to the wave-8 screen, so the comparison is like-for-like:
`base-rs-14` @ small (guard, anchor **0.5500**), `tune-ox-14` @ small
(guard, anchor **0.8000**), `tune-ox-14` @ large, `tune-rs-14` @ large.
Seeds **1,2,3**. No training.

## Pre-registered endpoint

**Primary: the large-tier compile-rate ratio, oxide ÷ rust.**
Wave 8 measured **0.0652** (5.0% vs 76.7%).

| ratio | reading | consequence |
|---|---|---|
| **≥ 0.20** | indexing was a real binding constraint | keep shipping the ranked stdlib one construct at a time — the method works |
| 0.12 – 0.20 | partial | the barrier was real but shallow; re-rank against the new diagnostic distribution before the next construct |
| **< 0.12** | removing one barrier merely exposed the next | **one-construct-at-a-time will not work.** Ship the ranked slate together, or accept that the gap is not closable by vocabulary |

**Secondary, and the mechanism check: the `OX0001` share of first
diagnostics.** Wave 8: **73 of 191 ≈ 38%**. If `[` was the dominant
lexer cause, this should fall below 15%. If `OX0001` stays high after
`[` is legal, the lexer barrier was something else and the wave-8
attribution was wrong.

Both are reported whichever way they move.

## Why the compile rate will NOT jump to 29%

Stated in advance so a modest rise is not read as a disappointment and a
large one is not read as a miracle. 29.0% of attempts contained `[`, but
those attempts also contain everything else the model gets wrong:
`OX0200` (unknown identifier — `split` 44, `slice` 39, `map` 32,
`floor` 27 across the 7B data) was already 43 of the 14B first
diagnostics. Clearing the lexer moves an attempt to its *next* error,
which for many will be an unknown identifier. **A rise into the 10–20%
band is the honest expectation.**

## Pre-registered stops

1. Either guard misses its seed-matched anchor → environment or merge
   suspect; report the drift, publish no ratio against wave 8.
2. Spend reaches $1.00 → stop and report what completed.
3. `torch.cuda` unavailable or wrong GPU → terminate before hours.

## Cost

≈**$0.30** at $0.22/h community 3090, ~1.25 h, priced from the wave-8
screen's measured timings — the pipeline is identical and the weights
are rebuilt the same way. Balance ≈$6.1.

## Carried ops rules

Verify capacity on the MACHINE, never the API's fields (`memoryInGb`
read 41 GB against an actual 251 GB last run). Verify transfers by
CONTENT HASH against `SHAS.txt`, not file count — a truncated tar passed
the count check last run and would have corrupted the control arm.
Request ≥150 GB disk. Terminate then verify zero pods twice.
