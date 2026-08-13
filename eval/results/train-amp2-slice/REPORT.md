# train-amp2-slice: the vector re-balance — band now PASS 30/30

2026-08-13. Addendum to [`../train-amp2/REPORT.md`](../train-amp2/REPORT.md).
Owner's ruling on the one out-of-band cell: re-balance and re-run the
slice.

## What changed

Per-task diagnosis located the asymmetry precisely: granite's rust does
not fail vector *algorithms*, it fails **multi-part output composition**
(eval t08: 0/10, t10: 1/10) — and the three re-authored vector tasks it
aced (n042 10/10, n047 9/10, n048 9/10) were single-concern. All three
families aced them (qwen 30/30). They were replaced — new ids, never
reused — by two t08/t10-shaped composition tasks and one medium
(n065 count-above+highest, n066 filter/print-each/then-count,
n067 per-element-odds-then-evens-total). The two-hard-one-medium mix
was chosen on a pre-run projection: all-hard would have parked
codegemma's rust-vectors exactly on its band floor. Pairs 3/3
validated; shape gate PASS; commit `75fbc16`.

## The slice run

270 sessions (3 tasks × 3 arms × 3 families × 10 seeds), same blobs,
settings, and seeds as train-amp2, hardened wrapper, 16:10–17:33. The
37 unchanged tasks' train-amp2 cells remain valid measurements taken
under identical conditions; the merge below is stated, not silent.

## Merged verdicts (37 kept tasks' cells + this slice)

**Difficulty band: PASS, 30/30.** The projections landed:

| cell | was | projected | measured | band |
|---|---|---|---|---|
| granite/rust/vectors | **0.660 FAIL** | ~0.45 | **0.430** | [0.225, 0.625] (ref 0.425) |
| qwen/rust/vectors | 0.650 | ~0.43 | 0.470 | [0.300, 0.700] |
| codegemma/rust/vectors | 0.580 | ~0.40 | 0.390 | [0.350, 0.750] |
| codegemma/rust/overall | 0.407 | — | 0.360 | [0.350, 0.550] — the cell the medium task protected |

Oxide stays in band everywhere (granite 0.010–0.290 by class, qwen
overall 0.260, codegemma overall 0.193).

**Yield endpoints, merged: both improve.** Mean unique verified oxide
programs/task **5.28** (was 5.05; floor 4.0); zero-yield **9/40 = 22%**
(was 25%; ceiling 30%) — the replacements themselves yield.
Contamination: 0 (guard suite green at authoring).

## Consequence

Every pre-registered endpoint — reference pairs, amplification yield,
zero-yield, and the two-arm per-class difficulty band — now passes on
the same 40-task corpus (`eval/train/tasks.jsonl` @ `75fbc16`).
**The corpus is cleared for training-data use by its own gate.** The
fine-tune track's remaining prerequisites are its unstarted specs
(training infrastructure, token-matching, experiment pre-registration),
not data.
