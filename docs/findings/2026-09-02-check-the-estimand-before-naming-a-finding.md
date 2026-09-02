# Check the estimand before naming a finding

*Black Oxide findings series — 2026-09-02. All numbers are reproducible
from this repository; sources are linked inline. Paths are relative to
`eval/results/` unless stated.*

## The claim

Five waves of this project compared two ratios and named their
difference a finding — "the language got shorter and the model did not
follow" — without anyone asking whether the two ratios were measured on
the same tasks. They were not. The check took one command, and running
it changed the size of the problem rather than dissolving it. The same
shape of error — two numbers put side by side that were not measured on
the same footing — recurred seven times in nine waves, each time in a
different disguise, and each time the fix was the same question. This
document records the seven so the question gets asked earlier next time.
It is the project's standing bug class, named in the first wave and
never retired: **a value that looks like a measurement of the subject
but is partly a measurement of the instrument's inputs.**

## 1. Means over each arm's own green set (wave 2)

The dynamic token-efficiency endpoint from wave 0 was
`tokens_to_green_mean(oxide) / tokens_to_green_mean(rust)`, each mean
taken over *that arm's own* green sessions. Those sets change size and
difficulty whenever pass@1 moves. Wave 1's report read 1.13 against
wave 0's 1.24 and called it an improvement; wave 2's read 1.198 and
called it a regression. Neither was measuring efficiency
([`v04-campaign2/REPORT.md`](../../eval/results/v04-campaign2/REPORT.md)):

| construction | wave-0 | wave-1 | wave-2 |
|---|---:|---:|---:|
| unconditional mean (as pre-registered) | 1.24 | 1.13 | 1.198 |
| paired, both arms green | 1.174 | 1.218 | 1.188 |
| **composition-controlled, 67 cells green in every wave** | 1.217 | **1.293** | **1.067** |

Under one construction applied to all three waves' committed cells, wave
1 was *worse* than wave 0, not better: its oxide arm had solved fewer,
easier cells (pass@1 0.420 against 0.555), so its mean fell for a reason
that was not the language. An erratum was filed against wave 1's report
with the prior value left visible. SPEC §59.7 binds the correction: pair
cells by `(seed, task)`, keep only pairs green in both arms, restrict to
the set green in every wave compared, and report the set's size beside
the ratio.

The set matters as much as the rule. Wave 2 reads 1.067 on the three-wave
common set of 67 cells, 1.0799 on the four-wave set of 61, and 1.0858 on
the five-wave set of 59 — all correct on their own set. **A ratio without
its set is not a measurement.**

## 2. Two task sets (wave 6, and it cost four waves)

From wave 1 to wave 4 the static ratio fell 1.22 → 0.9871 while the
composition-controlled dynamic ratio sat between 1.07 and 1.20, and the
divergence became "the project's central open problem". Before building
the attribution instrument proposed to explain it, the two estimands
were checked for comparability
([`eval/references-v04/REPORT.md`](../../eval/references-v04/REPORT.md)):

| estimand | task set | references |
|---|---|---|
| static (0.9871) | the 40 **train** references | re-authored every wave |
| dynamic (1.1982) | the 20 **eval** tasks | frozen since the first commit, 2026-08-07 |

`eval/solutions/` contained zero uses of `sort`, `unwrap_or`, `+=`,
`swap`, `set`, `count_if` or `filter` — every construct waves 1–4
shipped. Four waves of static improvement were measured only on the
tasks that had been re-authored; the dynamic campaign ran on tasks never
touched.

Correcting it made the problem bigger. The eval-set static ratio under
the frozen references is 1.1796 (the wave-0 state); under current
vocabulary it is 0.9393; after the symmetric Rust review of wave 7
(one hit in twenty, `t17` 64 → 53 tokens) it is **0.9462**. Against the
model's 1.1982 on the same 20 tasks, the surplus is 27.6% — the central
problem stated without a confound for the first time. The frozen
references were deliberately left frozen: they are the contamination
reference, and modernising them would move that baseline in the
direction that masks leakage.

## 3. Bands on the raw ratio instead of the surplus (wave 8A)

Wave 8's spec stated its three dynamic outcomes as bands on the raw
large-tier ratio — ≤1.05, 1.05–1.30, >1.30 — calibrated when the
reference ratio was assumed to sit near 0.94. The reference ratio came
in at **1.0622**. A model matching the references exactly would then
have scored 1.0622 and landed in "real, size-independent model surplus"
while its true surplus was zero
([`v04-wave8-large/REPORT.md`](../../eval/results/v04-wave8-large/REPORT.md)).

The endpoint was amended to the **surplus** — the model's oxide/rust
ratio divided by the references' ratio over the same green cells — which
is how wave 6's 28% had actually been computed (1.1982 ÷ 0.9393 = 1.276).
Amended before Phase B ran, not after. Phase B then reported the small
tier at surplus 1.242 on 120 pairs across 13 tasks, and the large tier
at 0.798 on **3 pairs across 1 task** — below the floor of 5 fixed in the
plan, so printed for the record and not an endpoint
([`v04-wave8-phaseb/REPORT.md`](../../eval/results/v04-wave8-phaseb/REPORT.md)).

## 4. Seed-matched anchors (the 14B screen)

A three-seed screen cannot reproduce a ten-seed figure. `tune-ox-14`
publishes pass@1 0.745 over seeds 1–10 and reads **0.800 over seeds
1–3**; `base-rs-14` reads 0.550 in both. Screening a healthy adapter
against the published number would have shown a 5.5-point anomaly that
was pure sampling
([`v04-wave8-14b-screen/REPORT.md`](../../eval/results/v04-wave8-14b-screen/REPORT.md)).
The anchors were computed from wave 4's committed cells restricted to
seeds 1–3, `--seeds` shipped as tested code recording `seeds_subset` in
provenance, and both guards then reproduced on all four metrics each —
eight of eight, exactly.

The drift guard's own published claim had already been narrowed once by
the same logic. Wave 2 reported that every companion figure of
`base-rs-7` reproduced to the digit across environments; wave 3, on a
different GPU architecture, found pass@1 and censored sessions exact but
pass@10v, tokens-to-green and strict repair drifting slightly. The claim
that survives is narrower: pass@1 is invariant across architectures;
secondary metrics are invariant within one. Wave 2's stronger phrasing
held only because both runs were on 4090s
([`v04-campaign3/REPORT.md`](../../eval/results/v04-campaign3/REPORT.md) §5).

## 5. The symmetric pass, run because the result favoured the other arm

Both arms of every reference set were authored by the person who
designed one of them. Two rules came out of that:

- **Wave 7's Rust re-review.** Wave 6 had modernised only the Oxide
  side, so 0.9393 was not claimed as an endpoint. The symmetric review
  of the Rust references, under a criterion fixed before looking, found
  one hit in twenty and moved the ratio *against* Oxide to 0.9462. Small,
  and that is the point: a review finding nothing wrong with the arm the
  reviewer did not author would have been worthless
  ([`v04-wave7-attribution/REPORT.md`](../../eval/results/v04-wave7-attribution/REPORT.md)).
- **Wave 8's large tier.** The first measurement read 1.0766. The
  symmetric pass found six Oxide programs using a manual `while` loop
  where the Rust arm had an idiomatic counted loop and Oxide has
  `range`; converting exactly those six gave **1.0622**. A 1.4-point
  authoring asymmetry against the arm the author did not design, found
  only because the number favoured Rust. The rule recorded: run the
  symmetric pass whenever the result favours the other arm.

## 6. Count-verified is not content-verified (the 14B screen)

The rule since wave 0 — verify every transfer by file count, never by
`du` — was bought when a timeout-truncated backup lost the rust adapters
with a pod. The 14B screen truncated a transfer that **passed the file
count**: `tune-rs-14-v5` had its correct four files, and its
`adapter_model.safetensors` hashed `1bf2b8b7…` against the expected
`57b32260…`. That is the control arm; had it run on corrupt weights the
compile-rate ratio would have been meaningless while looking plausible.
The rule was upgraded to content hashes against the preserved
`SHAS.txt`. The same run also showed that a pipeline change can hide
inside a guard: converting straight to q8_0 rather than via bf16 gave a
base GGUF with a different hash (`d5473be2…` vs `662ea1eb…`), so the
drift guard was pre-committed to test two things at once, and it read
byte-identical behaviour across all four metrics.

## 7. A denominator summed from a table (the wave-9 plan, caught before the run)

The wave-9 re-screen plan quoted wave 8's `OX0001` share as **73 of
191**, about 38%, and the reader module carried
`LEXER_SHARE_BASELINE = 73 / 191`, typed in from the report. Running the
instrument that would read the re-screen —
`eval.wave8_screen.diagnostic_mix` — over the committed wave-8 cells
gives **73 of 216**. The 191 is the sum of the four largest codes in the
wave-8 report's table (73 + 51 + 43 + 24) and omits the five smaller
ones, 25 attempts. Nothing had been excluded on purpose; a denominator
had been read off a table instead of computed.

The baseline is **0.338** under the instrument's stated lens (every
attempt, first or repair, that carries at least one diagnostic; the
numerator is those whose *first* diagnostic is `OX0001`). The constant
is now pinned to the committed cells by a real-data test, and the plan
was amended at 11:55 UTC on 2026-09-02, before the pod had produced a
cell. Found afterwards, a measured share of 0.20 would have read as a
fall from 0.382 rather than from 0.338, and the chosen 15% threshold
would have been judged against the wrong distance.

Sources: `docs/superpowers/plans/2026-09-02-v04-wave9-rescreen-plan.md`
(the 11:55 UTC amendment), `eval/wave8_screen.py`,
`tests/test_wave9_rescreen.py`.

## The question, and a checklist

All six reduce to one question, asked before the difference between two
numbers is named a finding: **were they measured on the same thing?**
Same task set, same green set, same seeds, same reference footing, same
weights. When the answer is no, the difference is a property of the
instrument until shown otherwise.

Before quoting `A − B` or `A ÷ B`:

1. Name the population each number was computed over; if either is a
   model-dependent subset (an arm's own greens), pair and intersect.
2. Name the task set, and check the references on both sides carry the
   same vocabulary.
3. If one number is a reference and the other a model, report the
   *surplus* — model ÷ reference on identical cells — not the raw ratio.
4. If seed counts differ, recompute the anchor on the seed subset.
5. If one arm's authorship could favour the other, run the symmetric
   pass, and run it *especially* when the result comes out the way you
   expected.
6. Verify artifacts by content hash; a count cannot see a truncated
   final file.

Pre-registration does not prevent any of these. Five of the six were
pre-registered endpoints that measured the wrong thing while measuring
it exactly as written. What caught them was the comparability check, and
the discipline to file the erratum, amend the spec non-silently, and
leave the prior value visible.

## Honest limits

- These are one project's defects, found in its own instruments; the
  checklist is the one it needed, not a general theory of measurement.
- Two of the six (the surplus bands, the seed-matched anchors) were
  caught before the number existed; the other four were caught after
  a value had been published and required an erratum. The record
  distinguishes the two.
- The pre-registration and instrument-honesty side of the same
  discipline is written up from the systems angle in the sibling
  project's
  [the instrument fails first](https://github.com/bricelancasterwcp-sudo/robigo/blob/master/docs/findings/2026-08-12-the-instrument-fails-first.md);
  this document covers only the comparability defects.
