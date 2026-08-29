# v0.4 — the efficiency cycle, wave 1 (vectors + Option)

**Date:** 2026-08-28
**Purpose (binding, per the owner's 2026-08-28 direction):** Black Oxide
is a design project — the point is a language LLMs can *use more
efficiently*, measured in tokens per solved task. Measurement feeds the
design loop; no cycle ends in a terminal verdict. This spec is wave 1
of that loop: the objective function is token efficiency, with pass
rates and construct uptake as guards. (The §53–§57 ergonomics cycles
are the procedural precedent; they optimized pass rates. This cycle
optimizes tokens.)
**Status:** design approved in session (sections approved in chat,
2026-08-28); this document is the written record for review.
**Branch note:** stacked on `finetune-experiment` (whose merge to main
is still the owner's open decision). Lesson on file: never merge a
stacked PR before its base is merged or retargeted.

## Baseline (measured 2026-08-28, the committed anchor)

From `eval/train/matched/manifest.json` (pinned tokenizer, mean
supervised tokens per program, hand-authored reference pairs to
identical tasks with identical stdout):

| class | oxide | rust | ox/rs |
|---|---|---|---|
| arithmetic/loops | 52.3 | 50.4 | 1.04 |
| strings | 72.5 | 57.8 | 1.25 |
| structs/option | 62.5 | 67.7 | **0.92** |
| vectors | 97.4 | 57.3 | **1.70** |
| overall | 71.2 | 58.3 | **1.22** |

Dynamic corroboration: tuned-model tokens-to-green ratios 1.24–1.40×;
worst single pair n041 at 4.34× (a hand-rolled selection sort where
Rust writes `v.sort()`). The mechanism that wins (structs 0.92× via
implicit ownership) and the mechanism that bleeds (missing stdlib
vocabulary) are both identified. Wave 1 attacks the bleed and extends
the win.

## Objective and pre-registered endpoints

All targets are **chosen** design goals (goals are not properties of
nature; there is nothing to derive them from). They are set before any
wave-1 work and may only be amended non-silently.

- **Primary (static):** after re-authoring, the reference-pair ratios
  measured by the committed token-efficiency estimand reach:
  overall **≤ 1.10** (from 1.22), vectors **≤ 1.15** (from 1.70),
  structs/option **≤ 1.00** (must not regress past parity; currently
  0.92), arithmetic within **±0.05** of its current 1.04. Strings is
  untouched this wave and expected ≈ 1.25 (wave 2's target). (The
  pair is arithmetic-consistent: at vectors 1.15 and today's other
  classes, overall computes to ≈ 1.09.) The program-level goal across
  waves remains overall ≤ 1.00.
- **Guard G1 (pass rates, dynamic):** on the wave-1 campaign (same
  serving stack, fresh pod): `base-rs-7` pass@1 within **±0.10** of
  0.565 (instrument control — last cross-pod reproduction was exact);
  re-tuned `tune-ox-7(v2)` pass@1 **≥ 0.455** (no-collapse floor: 10pp
  below the wave-0 tuned value; improvement is expected, the guard is
  against regression); `tune-rs-7` re-run on the same pod for the
  paired comparison.
- **Guard G2 (uptake):** every shipped construct is demand-counted in
  model outputs (card arm and tuned arm separately). A construct with
  zero uptake in the tuned arm's outputs is a **failed candidate** —
  recorded as a finding and ruled on next wave (fix the card, fix the
  surface, or withdraw); never silently kept as dead vocabulary.
- **Wave discipline:** the cycle's closing section feeds wave 2
  (strings, plus wave-1 failures). There is no "done".

## Task 1 — the demand census (precedes candidate finalization)

Candidates are finalized from measured demand, not from the provisional
slate below. Two censuses, one committed report:

1. **What models try to write:** mine the 4,800 raw replies in
   `eval/results/runpod-exp/*/gen-s*/raw/` (oxide arms) for
   constructs oxide rejects — range forms (`0..n`, `range(a,b)`,
   `.to(n)`), sort/min/max/sum spellings (method vs free), index
   assignment (`v[i] = x`, `.set`), Option idioms (`if let`,
   `unwrap_or`, `?`), string methods. Instrument: a new
   `eval/demand_census.py` with pinned pattern definitions per family,
   counts per (family, arm, construct-spelling), cross-checked against
   the diagnostics the same replies produced. This is §54's method at
   corpus scale: the census tells us not just *what* to add but *which
   surface spelling the prior reaches for* — and that spelling is the
   one we admit.
2. **What humans hand-roll:** the same pattern census over the 80
   reference solutions and 582 amplified programs — hand-rolled
   min/max/sum/sort/membership/index-set loops, counted per class.

Cap (chosen): wave 1 ships **at most 8 constructs**. The census ranks;
the cap cuts.

## Provisional slate (subject to census confirmation)

**Vec builtins** (all value-semantics-consistent with `push`: consume
and return; all get receiver-first method syntax per the §53 law):

| construct | signature | Rust transpile |
|---|---|---|
| `sort(v)` | `Vec<T> -> Vec<T>` | `{ let mut t = v; t.sort(); t }` |
| `min(v)` / `max(v)` | `Vec<T> -> Option<T>` (empty → None) | `v.iter().min().copied()` etc. |
| `sum(v)` | `Vec<Int> -> Int` | `v.iter().sum()` |
| `set(v, i, x)` | `Vec<T>, Int, T -> Vec<T>` (OOB = runtime panic, matching `get`'s contract — check `get`'s actual contract during implementation and mirror it) | `{ let mut t = v; t[i] = x; t }` |
| `contains(v, x)` | `Vec<T>, T -> Bool` | `v.contains(&x)` |

**Ranges** (syntax, not builtin): surface form decided by census —
expected `a..b` (the Rust prior) usable in `for` headers; grammar and
AST addition, desugared to an iterable. If the census shows a
different dominant spelling, the census wins.

**Option ergonomics** (extending the 0.92× mechanism):
`unwrap_or(o, d) -> T` (builtin; taxonomy dossier 5 already classed it
"small"); `if let Some(x) = e { }` (grammar) — ships wave 1 only if
the census shows material demand, else deferred with its count
recorded.

Every construct: new diagnostics fail closed; transpiled output must
keep the identical-stdout law; the transpiler's Rust must compile
warning-clean under the existing pipeline.

## Card amendment

SPEC §0 froze the model-facing card strings until "the corpus
regenerates" — wave 1 regenerates it, so the freeze lifts here,
non-silently: the card gains the new builtins/syntax section, versioned
(card-v0.4), with the old card retained in git history and the
change called out in SPEC. Card length stays within its current order
(the card is a measured instrument; a bloated card is its own
regression — record old/new word counts).

## Re-authoring rules (bias control)

- **Rust references are untouched.** Only oxide references change, and
  only by substituting a shipped construct for the hand-rolled pattern
  it replaces — no other tightening, no golfing. Every edit is
  reviewable as exactly that substitution.
- Both references stay `validate_pair`-green with identical stdout;
  contamination guard re-runs; the matched corpus is REBUILT by the
  committed builder (new manifest = the post-wave measurement; the
  wave-0 manifest values above are the frozen anchor).
- Eval-side `eval/solutions/` and t01–t20 stay frozen (they are the
  held-out instrument, not the design surface).

## The dynamic loop (RunPod, ~$3–5, chosen budget ceiling $10)

1. **Re-amplify** the training corpus with card-v0.4 (K=30, the
   committed amplification machinery): doubles as the card-arm G2
   uptake read — do carded models use the new vocabulary unprompted?
2. Re-match (committed builder), **re-tune `tune-ox-7` only** (the
   rust corpus is unchanged; the existing rust adapter re-serves).
3. Campaign, 4 arms on one fresh pod: `base-rs-7` (control),
   `base-ox-7` (card-v0.4), `tune-ox-7(v2)`, `tune-rs-7` (re-run for
   same-pod pairing). Existing exp_campaign/serving stack unchanged.
4. Read G1/G2 + tokens-to-green; feed everything to wave 2.

The 12-arm wave-0 results remain the committed anchor for their own
environment; wave-1 comparisons are within the wave-1 pod.

## Honest limits

- Targets are chosen goals; hitting them proves the design moved, not
  that the language is "best".
- The ratio is measured on this project's reference style and task
  distribution; a different task mix weights the classes differently.
- Re-authoring is done by the same agent lineage that designs the
  constructs — the bias-control rules above and the untouched Rust arm
  are the mitigation, and diffs are part of review.
- `tune-rs-7` is not retrained (unchanged corpus), so its wave-1
  re-run isolates pod drift for the paired read; if pod drift exceeds
  the control band, the dynamic read is voided and re-run, not
  reinterpreted.
- Uptake (G2) at n=1 tuning run per wave is coarse; a failed-uptake
  finding is a next-wave input, not a definitive kill.

## Out of scope (wave 1)

Strings vocabulary (wave 2, with wave-1 lessons); ownership semantics
(the v0.3 gate stands); the from-scratch matched-exposure learnability
experiment (recorded separately as the secondary question); grammar
files for constrained decoding (the project measures unconstrained);
any public write-up (owner-gated, and it now frames wave 0 as the
loop's instrumentation, not a verdict).
