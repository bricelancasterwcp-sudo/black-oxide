# v0.4 — wave 7: where the 28% goes

**Date:** 2026-08-31
**Branch:** `v04-wave7-attribution`, off `main` @ `f76f2fd9`.
**Status:** prepared, awaiting go. Balance ≈ $7.2.

## 1. The question, now well-posed

Wave 6 removed a task-set confound and left a clean quantity: on the 20
eval tasks, the language expresses the work at **0.9393** of Rust's
tokens and the tuned 7B writes it at **1.1982** — a **~28% surplus
attributable to the model**, not to the language.

Five waves have improved what the language *permits*. None has measured
what the model actually *does* with the difference. Wave 7 measures it.

## 2. Phase A — diagnostic (local, **$0**)

No pod. Wave 4's `tune-ox-7` already carries **132 green cells across
15/20 eval tasks** and 408 reply files, committed under
`eval/results/v04-campaign4/`. The comparison set exists.

**A1 — Symmetric Rust re-review.** Wave 6 modernised only the Oxide
side, so 0.9393 is not yet an endpoint. The Rust eval references get the
same treatment, under a criterion fixed *before* looking, applied
mechanically, with every delta reported including those that hurt Oxide:

> A Rust reference is rewritten only where it hand-rolls something the
> standard library provides, or repeats a pattern the language has a
> direct form for. Style preferences are not grounds. Every change is
> listed with its token delta and the specific std facility it adopts.

The bias risk is real and named: I authored the Oxide side and would be
marking my own homework. The guard is that the criterion is stated
first, the diff is published per-file, and **a net Rust improvement is
the expected outcome, not a failure** — if the ratio rises from 0.9393,
that is the honest number.

**A2 — Eval-set cost census.** Run the existing `eval/cost_census.py`
against the modernised eval pairs. Produces the per-task surplus ranking
for the eval set, the instrument that found `swap` and `reverse` on the
train set. The 12 eval references that needed no change in wave 6 are
the interesting rows: their surplus, if any, is unreachable with current
vocabulary and is where the next language gap hides.

**A3 — The attribution instrument.** For each eval task, diff the
modernised reference against the model's green output and classify the
surplus into named categories, counted per task:

- *hand-rolled where a builtin exists* — the model writes a loop for
  something `sort`/`filter`/`count_if`/`sum` already does
- *redundant bindings* — intermediate `let`s the reference does without
- *verbose construction* — `push` chains where `vec(...)` exists
- *defensive scaffolding* — `match` where `unwrap_or` suffices
- *unattributed* — everything the categories do not explain, reported
  as its own number and never folded into the others

**The unattributed bucket is the honesty check.** If it dominates, the
categories are wrong and the instrument says so rather than producing a
confident decomposition of nothing.

## 3. Phase B — implementation (pod, **only if A warrants it**)

Phase A ends in one of three states, and the spec commits to each:

1. **The surplus is mostly hand-rolling of existing builtins.** Then it
   is a *teaching* problem, not a language gap — the constructs exist
   and the model does not reach for them. Phase B is a card or corpus
   change, and the exposure lever (still unpulled since wave 3) becomes
   the right instrument.
2. **The surplus is mostly shapes with no current construct.** Then it
   is a language gap, the cost census ranks it, and Phase B ships
   vocabulary and measures uptake — the wave 3/4 loop, which is known to
   work.
3. **The surplus is mostly unattributed.** Then no Phase B. Report the
   negative, and the next wave builds a better instrument rather than
   shipping against a decomposition nobody trusts.

**No Phase B is authorised in advance.** It gets scoped, costed and
approved after A reports, because what to build is exactly what A is
for.

## 4. Cost

| phase | GPU | estimate |
|---|---|---:|
| A (diagnostic) | none — runs on committed data | **$0** |
| B, if state 1 or 2 | 4 arms, 7B only | ≈ **$1.20** |
| B, if the 14B tier is wanted | 8 arms | ≈ **$1.65** |

Wave 4's full eight-arm campaign cost $1.61 measured, so Phase B is
priced from a real run rather than a projection. Against ≈$7.2
remaining, the worst case leaves ≈$5.5.

**Phase A is free, and it is the part that answers the question.** The
project has spent five waves improving what the language permits; this
one costs nothing and finds out why that has not reached the model.

## 5. Stops

1. Unattributed surplus > 50% → no Phase B, report the negative.
2. A1's Rust re-review raising the ratio above 1.00 → report it and stop
   claiming the eval set is below parity, rather than re-authoring
   further to recover the number.
3. Phase B is never entered without a fresh cost estimate and approval.

## 6. Out of scope

The exposure lever (unless A lands in state 1), the 1.5B tier for
card-only work (SPEC §64), and the standing debt from wave 4's
feed-forward.
