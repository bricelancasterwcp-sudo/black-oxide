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

### AMENDED 2026-09-02 11:30 UTC, before any number exists: two pods, no measurement yet

- Pod `bf1mt4qibzo9tw` was provisioned at 02:15 UTC by the session that
  wrote this plan, and that session ended before running anything on it.
  Found at 11:21 UTC with an empty `/workspace`: **9.1 h idle, ≈$2.00 at
  $0.22/h, zero steps executed.**
- On that pod `nvidia-smi` listed the RTX 3090, and `cuInit` returned
  **999 (CUDA_ERROR_UNKNOWN)**; `torch.cuda.is_available()` was False.
  Stop 3 fires: terminated at 11:24 UTC before any hours were committed.
  Zero pods verified.
- Replacement `dv2nyotmwhyksp` created 11:24 UTC from the same spec.
- **How this reads against the stops, decided now.** No measurement was
  started, so nothing here is a re-roll: an infrastructure loss with no
  numbers read may be rerun from zero. The $1.00 spend stop bounds *the
  run*; its clock starts at the replacement pod's creation. The ≈$2.00
  idle loss is recorded in the report and in the program total as an
  ops loss, not netted against the stop. If the owner reads it
  otherwise the run is void. The reading is committed here so it is not
  chosen after seeing the number.
- Two carried ops rules gain a clause. (a) `nvidia-smi` succeeding is
  not evidence the GPU is usable; ask the driver (`cuInit`) before any
  other step, which `scripts/runpod/wave9_rescreen.sh` now does first.
  (b) A pod must never outlive the session that provisioned it without
  a detached run already on it: provision, verify, launch, *then* do
  anything else. This one was provisioned last.

### AMENDED 2026-09-02 11:55 UTC, before any number exists: the secondary endpoint's baseline was mis-transcribed

The plan above quotes wave 8's `OX0001` share as **73 of 191 ≈ 38%**.
Running the instrument that will read the re-screen
(`eval.wave8_screen.diagnostic_mix`) over the committed wave-8 cells
(`eval/results/v04-wave8-14b-screen/results-large/tune-ox-14/`) gives
**73 of 216 = 0.338**. The 191 is the sum of the four largest codes in
the wave-8 report's table (73 + 51 + 43 + 24) and omits the five smaller
ones (`OX0100` 20, `OX0400` 2, `OX0308` 1, `OX0205` 1, `OX0403` 1 — 25
attempts). All 216 first diagnostics are compiler codes; nothing was
excluded on purpose.

**Lens, stated exactly:** the denominator is every attempt of the arm —
first attempts and repair attempts alike, 238 in wave 8 — that carries
at least one diagnostic (216); the numerator is those whose *first*
diagnostic is `OX0001`. The baseline is **0.338**, and
`LEXER_SHARE_BASELINE` is now pinned to the committed cells by a
real-data test rather than typed in from a report.

The **15% threshold stands** as written. It was a chosen number, not one
derived from the baseline, and it is marked as chosen here; a share
below 0.15 against a baseline of 0.338 still says what the plan meant
it to say. Recorded before the pod has produced a cell, so the baseline
is not adjusted with the result in view.
