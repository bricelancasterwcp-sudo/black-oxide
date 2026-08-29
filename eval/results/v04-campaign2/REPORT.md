# v0.4 efficiency cycle, wave 2 — full-loop report

2026-08-29. Spec: `docs/superpowers/specs/2026-08-28-v04-efficiency-wave2-design.md`,
including its 2026-08-29 owner-ruled amendment (amplification temperature).
This is the committed home of the wave's endpoint readings, guard reads,
uptake counts and feed-forward. Metric constructions are stated as
computed. The cycle's output is the next cycle's input; this report ends
with that hand-off, not a verdict.

## What shipped (the design change under measurement)

Slate of two, gated by the wave-2 demand census (rejection-crossed,
ranked — the gate reads counts, not opinions):

- **Compound assignment `+=` / `-=` / `*=`** — statement sugar, parsed
  and desugared to the existing `Assign`+`BinOp`. No new semantics, no
  new runtime surface, no new type rules. `Str +=` raises the same
  `OX0305` its hand-written twin raises; targets are identifier-only.
- **`count(v, x) -> Int` builtin** — occurrence counting over a vector,
  transpiled to a filter-count over `*e == x`.

Deferred **with their counts**, so the deferral is auditable: `if let`
(amp presence 68, below the 89 bar the wave-1 report pre-registered for
the re-gate — the bar was followed as written), bracket index assignment
(campaign presence 0; amp 18 present / 18 rejected), `remove_at`
(removal_rebuild: 2 references), strings vocabulary (string_build: 1/1),
`first`/`last` (no signal).

Two census results are findings in their own right:

- **`minmax_scan` = 0/0.** Zero hand-rolled min/max scans in either the
  reference or amplified corpus. This is absence of demand, not an
  instrument gap: wave-1's `min`/`max` builtins already absorbed the
  pattern. A census that can distinguish "we cannot see it" from "it is
  no longer there" is doing its job.
- **The strings residual is not pattern-shaped.** The five pinned
  hand-rolled structural patterns find essentially nothing in the
  strings class (string_build 1 reference, 1 amplified), yet strings
  carried a 1.159 ratio into this wave. Whatever costs tokens there is
  not a construct the census can name, which is why no strings
  vocabulary shipped and why wave 3 gets a different instrument (below).

### Demand proof for `+=` (the cleanest signal the census has produced)

On the wave-1 campaign the oxide base arm wrote `+=` in **64
first-attempt replies and all 64 failed to compile — 100% mechanical
rejection**. The Rust control wrote it 71 times with 0 rejections. The
amplification arms reproduced the shape at 1.5B (105/105) and 7B
(115/115). A construct the model reaches for reflexively, that the
language did not have, costing a compile every time.

The confirming read is in this wave's own campaign: the same base arm,
same tasks, now with `+=` in the language, wrote it in **248 replies
with zero mechanical rejections**.

## Static endpoints (primary; reference pairs, pinned tokenizer)

Construction unchanged from wave 1: mean supervised tokens per
hand-authored reference program, oxide/rust, identical tasks and
identical stdout. Targets are chosen design goals, amended at the gate
(non-silently, before any endpoint was read) to match the slate that
actually shipped.

| class | wave-0 | wave-1 | wave-2 | target | verdict |
|---|---:|---:|---:|---|---|
| arithmetic/loops | 1.04 | 1.038 | **1.010** | ≤ 1.02 | HIT |
| structs/option | 0.92 | 0.923 | **0.920** | hold ≤ 1.00 | HIT |
| strings | 1.25 | 1.159 | **1.064** | hold 1.159 ± 0.03 | below band (accepted) |
| vectors | 1.70 | 1.389 | **1.377** | ≤ 1.25 | **MISS** |
| overall | 1.22 | 1.121 | **1.087** | ≤ 1.09 | **HIT** |

Ruling recorded at the reading: strings came in *below* its hold band.
The deviation was accepted rather than reverted — the re-authoring was
rule-compliant and the movement is beneficial; the band was a
hold-expectation, not a floor. Recorded rather than quietly absorbed.

The vectors miss is a miss. `count(v, x)` reaches occurrence counting
and nothing else; the residual is predicate-count, keyed-max,
`enumerate`-shaped and push-rebuild loops.

## Corpus-scale gate (the wave's hard STOP, and what it cost)

The wave pre-registered a corpus-scale gate: **no tuned read below
15,000 supervised tokens per arm**, written because wave 1's dynamic
result was confounded by a 7.4k corpus. It fired twice.

| attempt | pooled unique verified (ox/rs) | supervised tokens/arm | gate |
|---|---|---:|---|
| amp2, 3 sizes × 20 seeds, temp 0.2 | 143 / 120 | 8.8k / 8.9k | **FAIL** |
| + escalation to 40 seeds (9,600 sessions) | 188 / 166 | 11.0k / 11.2k | **FAIL** |
| + amp3, 20 fresh seeds at temp 0.8 | **386 / 500** | **29.8k / 30.0k** | **PASS** |

The escalation's marginal-seed curve flattened (74 → 143 → 188 uniques):
more seeds of the same sampler produce replicates, not diversity. The
pre-registered STOP was honored — the run stopped and the owner ruled
among staged options rather than the controller quietly lowering the
bar. Owner ruling (a), recorded in the spec as a dated amendment:
**amplification re-runs at temperature 0.8, for corpus generation only.**
The measurement sampler stays pinned at 0.2 for every arm that produces
a number; amplified programs are oracle-guarded (rustc must accept them
and stdout must match), so a hotter corpus sampler cannot smuggle in a
wrong program — only more varied right ones. It worked: one temperature
change did what twice the seeds could not.

Final corpus: 29.8k / 30.0k tokens per arm — 2× the gate and 1.75× the
wave-0 scale. Per-class budgets: arithmetic 9,579, vectors 10,614,
structs 6,527, strings 3,254; all matched-pair gaps within one step.

Training on it produced the narrowest oxide/rust loss gap the project
has measured: **train_loss 0.1654 (oxide) vs 0.1261 (rust), +0.039**.
Wave 1's undertrained oxide arm sat at 0.360.

## Dynamic loop (secure 4090 pod, $0.74/h; 4 arms × [200 gen + 200 repair] on t01–t20)

| arm | pass@1 | pass@10v | tok→green | censored | strict repair |
|---|---:|---:|---:|---:|---:|
| base-ox-7 (card v0.4.1, untuned) | 0.060 | 0.15 | 91.5 | 188 | 0.440 |
| base-rs-7 (control) | **0.565** | 0.65 | 65.7 | 87 | 0.895 |
| tune-ox-7 (v3, 29.8k) | **0.755** | 0.85 | 86.0 | 49 | 0.575 |
| tune-rs-7 (v3, 30.0k) | 0.905 | 0.95 | 71.8 | 18 | 0.845 |

**G1 control: PASS.** base-rs-7 = 0.565 pass@1, byte-exact for the
**fourth** independent environment (local Vulkan v03c, wave-0 3090,
wave-1 4090, wave-2 secure 4090). Every companion figure reproduced to
the digit as well — pass@10v 0.65, tok→green 65.7, censored 87, strict
repair 0.895. The harness is deterministic across hardware.

**G1 floor: MET, not re-derived.** tune-ox-7 = 0.755 against the 0.455
floor. Wave 1 tripped this floor at 0.420 and diagnosed it as a
corpus-size artifact rather than a language regression. The diagnosis
is now confirmed by restoration rather than by argument: same recipe,
same seeds, corpus 7.4k → 29.8k, pass@1 0.420 → 0.755 (wave-0 was 0.555
at 17k, the reading the 0.455 floor was derived from). **The tuned oxide
arm now exceeds the untuned Rust control
(0.565) on the same tasks.**

**Repair-loop observation (unregistered, recorded because it is
load-bearing for wave 3):** tune-ox-7's final greens (151) exactly equal
its first-attempt greens (151) — the repair loop recovered nothing this
wave; tune-rs-7 recovered one. At this capability level failures are
hard failures, and `tokens_to_green` is therefore almost entirely
first-attempt generation length.

### Token efficiency — the objective function

**Pre-registered endpoint (tokens-to-green mean, ox/rs): 86.0 / 71.8 =
1.198, against wave-1's 1.13. This moved the wrong way, and that is the
endpoint of record.**

It is also, on inspection, partly a measurement of something other than
the language. Each arm's mean is taken over *its own* green sessions.
tune-ox-7 went 0.420 → 0.755, so this wave's oxide mean is computed over
a larger and harder set of tasks than wave 1's was — the two numbers are
not over comparable populations. This is the project's named bug class
(a value that looks like a measurement of the subject but is partly a
measurement of the instrument's inputs), caught this time before it
reached a headline.

Applying **one** construction to all three waves' committed cells —
pair cells by (seed, task), keep only cells green in **both** arms, and
then restrict to the 67 cells (11 tasks) that are paired-green in
**every** wave:

| construction | wave-0 | wave-1 | wave-2 |
|---|---:|---:|---:|
| unconditional mean (pre-registered) | 1.24 | 1.13 | **1.198** |
| paired, both arms green | 1.174 | 1.218 | 1.188 |
| **composition-controlled (67 common cells)** | 1.217 | 1.293 | **1.067** |

The construction is not a one-off script: it ships as
`eval.experiment_report.load_cells_keyed` / `green_pair_keys` /
`paired_tokens_to_green`, mutation-tested, with an acceptance test that
pins every number in the table above against the committed cells. A
headline this report rests on is reproducible by running the suite.

On the composition-controlled set the oxide arm's own token count fell
**86.3 → 73.4 (−15%)** while the symmetrically-retrained Rust control
*rose* 66.7 → 68.8. The move is therefore not "more training writes
shorter code" — the control had the same extra training and went the
other way.

**Erratum against wave 1's report (filed with this wave).** Wave 1
claimed "tokens-to-green ratio 81.5/72.3 = 1.13, down from wave-0's
1.24 — the dynamic read moved the same direction as the static one."
That claim does not survive the controlled construction: on the common
set wave 1 was **worse** than wave 0 (1.293 vs 1.217), not better. The
apparent improvement was set composition — wave 1's oxide arm solved
fewer, easier cells, so its mean fell. The prior value stays visible in
`eval/results/v04-campaign/REPORT.md` with a dated footnote and the
arithmetic that killed it.

What survives is narrower and better supported: **on identical cells,
wave 2's vocabulary cut oxide's generated tokens by 15% and took the
dynamic ratio to 1.067**, moving the same direction as the static
endpoint (1.121 → 1.087) for the first time under a construction that
controls what is being compared.

### G2 uptake — no dead vocabulary

Per reply file, counted at most once each.

| construct | card arm (amp3, 8,647 files) | tuned arm (347 files) | base-ox control (764 files) |
|---|---:|---:|---:|
| `+=` | 2,105 | 146 | 248 |
| `*=` | 306 | 0 | 0 |
| `-=` | 33 | 0 | 0 |
| `count` | 126 | 3 | 42 |

`+=` and `count` are live in every arm. **`-=` and `*=` show zero
tuned-arm uptake** — stated plainly rather than folded into a family
total. They are not dead vocabulary (the card arm uses them 306 and 33
times, and both were census-demanded), but at this corpus size the
tuned model has not adopted them. Wave 3 should re-read them rather
than assume the family carries.

Wave-1 vocabulary remains live in the tuned arm: `range(a,b)` 62,
`unwrap_or` 8, `sort` 10, `sum` 4, `min`/`max` 1, `?` 1.

G2 lens (recorded so the counts are reproducible): `compound_assign`
spellings come from `demand_census.V2_FAMILIES`; `count` has no
committed family yet and was matched with the same free-call guard the
census uses for `sort`/`min`/`max`/`sum` — `(?<![.\w])count\s*\(` —
at most once per reply file. Folding `count` into the committed census
is a wave-3 item.

## Provenance and artifacts

- `base-ox-7/ base-rs-7/ tune-ox-7/ tune-rs-7/` — this wave's campaign
  cells, triples and raw replies.
- `matched-v3/` — the token-matched training corpus actually trained on,
  with per-program sha256, so the corpus is pinned by hash independent
  of the raw pools.
- `eval/results/v04-amp2/`, `eval/results/v04-amp3/` — both
  amplification pools, landed in full. Ruling: the temperature amendment
  is this wave's most contestable decision, so both the temp-0.2 pool it
  replaced and the temp-0.8 pool it produced are committed, and anyone
  can check what the hotter sampler did to the corpus.
- Adapters `tune-ox-7-v3` / `tune-rs-7-v3` are preserved outside the
  repo (161 MB each) with sha256 recorded, after wave-0 and wave-1
  adapters were both lost to teardowns. They are the checkpoints the
  queued assay×oxide A/B needs.

## Spend

Wave-2 loop ≈ **$9.05** of its $10 cap: ≈$4.9 through the two
gate failures and one unusable pod (driver/CUDA mismatch, ~35 min
billed), then ≈5.6 h × $0.74 for the amp3 → rematch → retrain →
campaign chain. Program total across three waves ≈ **$12.4** of the $23
tranche.

## Feed-forward to wave 3

1. **The dynamic estimand is defective and gets replaced.** Wave 3
   pre-registers the composition-controlled construction as the primary
   dynamic endpoint: pair by (seed, task), require green in both arms,
   and report on the set common to the waves being compared. The
   unconditional mean stays as a reported secondary so the historical
   series remains readable. Without this, any pass-rate movement
   contaminates the efficiency number in either direction.
2. **Vectors residual (1.377 vs a 1.25 target).** `count` reached
   occurrence counting only. What remains, by shape: predicate-count
   (count where a condition holds), keyed-max (max by a field),
   `enumerate`-shaped index+value loops, and push-rebuild loops. A
   predicate-taking form is the obvious next candidate — but it needs a
   closure or block-argument surface the language does not yet have, so
   it is a design question, not a vocabulary addition.
3. **Strings needs a different instrument.** Pattern census finds
   nothing there (string_build 1/1) while the class carries 1.064.
   Wave 3's instrument: pairwise token-diff attribution over the 10
   strings reference pairs — align oxide against rust token by token
   and attribute the surplus to concrete syntax, rather than asking
   whether a named pattern is present.
4. **`-=` and `*=` uptake re-read.** Zero tuned-arm uptake at 30k
   tokens. Either corpus scale, or the training tasks do not contain the
   shapes. Check which before concluding anything about the constructs.
5. **`if let` re-gate.** 68 on this wave's census against the 89 the
   card-era reading showed. The bar was followed; the number is worth
   re-reading once more before the candidate is dropped or shipped.
6. **Census instrument debt:** fold `count` into the committed families;
   fix brace-masking in the hand-rolled pattern matcher; split the
   954-line `eval/demand_census.py` (flagged for Brice); note the `/=`
   spelling observed in n007 that no family currently matches.
7. **Card quality is itself a lever, unmeasured until now.** base-ox-7
   went 0.025 → 0.060 pass@1 on card text alone (v0.4 → v0.4.1), with no
   training and no language change. If the card is worth 2.4× on the
   untuned arm, card design deserves its own measured cycle rather than
   riding along as a side effect of vocabulary changes.
