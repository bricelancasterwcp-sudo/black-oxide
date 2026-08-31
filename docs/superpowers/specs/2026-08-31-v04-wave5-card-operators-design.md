# v0.4 — wave 5 (A): does the operator table move the card-only arms?

**Date:** 2026-08-31
**Branch:** `v04-wave5-card-operators`, off `main` @ `b5665eff`.
**Status:** owner-approved. Balance ≈ $7.6; this experiment is estimated
at **≈$0.35** and capped at **$1.00**.

## 1. The question

Wave 4's Sonnet probe found that the language card has **never**
documented its operator set — `==`, `!=`, `%`, `<=`, `>=`, `&&`, `||`,
`!` appear zero times in the card at waves 2, 3 and 4 (SPEC §63.6). A
frontier model scored 20/20 from that card anyway, by assuming Rust's
operators and being right.

Small models have weaker priors. `base-ox-7` reads 0.075 and
`base-ox-1.5` read 0.000. **If the missing operator table is
load-bearing, every untuned Oxide arm in project history has been
measuring a documentation gap rather than the language.**

Card v0.8 adds the table (transcribed from `src/lexer/lexer.py` and
`_BINARY_BP`, not assumed). This wave asks whether that changes
anything.

## 2. Design — one variable

Re-run the **card-only** arms against card v0.8. Nothing else changes:
same base checkpoints, same 20 eval tasks, same harness, same sampler
(temperature 0.2), same one-attempt-per-cell construction, same
community RTX 3090 class.

No amplification and no training are needed — card-only arms use the
untuned base model — which is why this costs ~1.3 pod-hours instead of
a wave's ~7.

**Arms:** `base-ox-1.5`, `base-ox-7`, `base-ox-14` (the treatment), plus
**`base-rs-7` as a drift guard** (the Rust arms do not read the Oxide
card, so this must not move; if it does, something other than the card
changed and the treatment reads are void).

## 3. Pre-registered predictions

Stated before the run, falsifiable in both directions:

| arm | card v0.7 (wave 4) | prediction under v0.8 |
|---|---:|---|
| base-ox-1.5 | 0.000 | **> 0.000** if the gap was load-bearing |
| base-ox-7 | 0.075 | **≥ 0.150** (a doubling) if the gap was load-bearing |
| base-ox-14 | 0.525 | ≥ 0.525, but the smallest movement — a 14B has the strongest priors and least need of the table |
| base-rs-7 | 0.565 | **0.565 ± 0.010** — drift guard, must not move |

**If `base-ox-7` does not clear 0.150, the operator gap was not
load-bearing at that tier** and §63.6's instrument concern is answered in
the negative. That is a real and useful outcome, and it will be reported
as plainly as the alternative.

The point estimate decides. No re-runs, no card edits after seeing
numbers, no extension of the arm set.

**Expected direction of the tier effect:** the *benefit* of the table
should be largest where the prior is weakest, so 1.5B > 7B > 14B in
proportional terms. If instead the 14B moves most, the table is doing
something other than filling a prior gap and that needs explaining
before it is believed.

## 4. Secondary read (free, no extra pod time)

Per-construct uptake on the treatment arms for the operators themselves
(`==`, `%`, `/`, `!`, `&&`, `||`), against v0.7's counts. Uptake of an
operator the card newly documents is the mechanism check: capability
should move *because* operator use moves, or the causal story is wrong.

## 5. Stops

1. `base-rs-7` outside 0.565 ± 0.010 → the run is void, not a finding;
   diagnose before reading anything else.
2. Projected spend above the $1.00 cap.
3. Any infrastructure failure is diagnosed as infrastructure, never
   scored as a model result.

## 6. Out of scope

The exposure lever, the static/dynamic divergence instrument, and the
standing debt from wave 4's feed-forward. This wave answers one question
with one variable.
