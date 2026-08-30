# v0.4 efficiency cycle, wave 3 — full-loop report

2026-08-30. Spec: `docs/superpowers/specs/2026-08-29-v04-efficiency-wave3-design.md`.
Committed home of this wave's endpoint readings, guard reads, uptake
counts and feed-forward. Metric constructions are stated as computed.
The cycle's output is the next cycle's input; this report ends with that
hand-off, not a verdict.

## The wave in one line

**Black Oxide crossed below token parity with Rust on the static
estimand (1.0875 → 0.9863) while the dynamic estimand moved the other
way (1.0799 → 1.1315).** The language got shorter and the model did not
follow — because, per §6.1, the pipeline taught it the new vocabulary in
as few as 2 of 294 training examples. The gap between what the language
*can* express and what a model *does* express is now this project's
subject.

## 1. What the wave found before it built anything

Wave 2 closed by naming the vectors residual and guessing it needed a
closure surface. Reading the pairs said otherwise: the residual was
three tasks carrying +182 of +216, and two of them wanted trivial
builtins.

| task | ratio | surplus | what Rust had that Oxide lacked |
|---|---:|---:|---|
| n043 | 2.367 | +82 | `v.swap(0, last)` — Oxide rebuilt the vector in a 14-line loop |
| n050 | 2.395 | +60 | `v.sort(); v.reverse();` — Oxide did max-extract-and-rebuild |
| n045 | 1.976 | +40 | direct indexing — and Oxide's own `unwrap_or` was never applied here |

Vectors carried **+216 of a +204 net corpus surplus** — over 100%,
because structs/option runs negative. Any wave that did not move vectors
would not move the objective.

## 2. The method finding: two eyes, and they disagreed

`swap` and `reverse` have **zero** reply demand. The demand census has
no family for them, because a model cannot reach for a spelling it has
never seen. They ranked **1 and 2** by token cost.

Wave 2's gate, reading demand alone, had deferred index assignment
because campaign presence was 0 — while its absence was silently the
largest token gap in the corpus. That deferral is marked superseded in
SPEC §59.3 and deliberately left visible, because §60.3 indicts exactly
its reasoning.

| | measures | blind to |
|---|---|---|
| demand census | what models attempt to write | anything models were never taught |
| cost census | what correct programs cost | nothing in the corpus |

The general lesson, recorded because it will recur: **an instrument that
answers a question adjacent to your objective will be read as though it
answered the objective, until something forces the comparison.**

Wave 3's own results (§6) show the other edge of this: cost evidence
alone shipped two constructs the model then declined to use. Neither eye
is sufficient.

## 3. What shipped

- **`swap(v, i, j)`** — cost rank 1. n043: 142 → 60 tokens, parity with Rust.
- **`reverse(v)`** — cost rank 2. n050: 103 → 39.
- **`set(v, i, x)`** — demand 18/18 mechanical rejection; measured *not* to substitute for `swap` (n043 costs 99 with `set` alone).
- **Predicate literal `x -> expr` + `count_if`** — owner-directed, overriding the spec's "closures out of scope".

Out-of-range indices panic, matching the Rust control. Checked before
the claim reached SPEC: this is **not** a new category — integer
division already panicked on a computed zero divisor, undocumented,
since division existed (§60.2).

The predicate literal **cannot capture**; its body may reference only its
own parameter (`OX0205`). With no captures there is no ownership
question, so the construct never touches implicit linear ownership — the
collision that had put closures out of scope. That restriction is what
made the override cheap.

Comparison builtins (`count_lt`/`count_gt`) were measured first and
rejected despite saving 8 *more* tokens (0.9828 vs 0.9863): a
combinatorial family that generalises to nothing.

## 4. Static endpoints (reference pairs, pinned tokenizer) — all five HIT

| class | wave-3 start | after §60 | after §61 | target | verdict |
|---|---:|---:|---:|---|---|
| arithmetic/loops | 1.010 | 1.010 | 1.010 | ≤1.02 | HIT |
| strings | 1.064 | 1.061 | 1.061 | ≤1.07 | HIT |
| structs/option | 0.920 | 0.920 | 0.920 | ≤0.93 | HIT |
| vectors | 1.377 | 1.066 | **0.969** | ≤1.10 | HIT |
| **overall** | **1.0875** | 1.0103 | **0.9863** | ≤1.02 | **HIT** |

Oxide writes **2300** supervised tokens across the 40 reference programs
where Rust writes **2332** — surplus **−32**.

### Re-authoring, under the amended bias rule

The owner amended wave 2's rule, which had permitted a substitution only
where the Rust control used the analogous construct — making Oxide
pessimistic exactly where the languages diverge idiomatically. Each arm
is now written as well as its own language allows.

The sweep's **negatives** are recorded, because under the amended rule a
missed substitution is a defect: n007 and n009 want `/=`, never shipped;
n009's `out = out * 10 + n % 10` has an RHS larger than the construct
replaces; and **n064's `match get` is not admissible** — its `None`
branch is genuinely reachable (`get(v, 4)` on a 2-element vector) and
prints a different string, so `unwrap_or` would have changed stdout.

All 40 pairs green through the rustc/stdout oracle; every `rust.rs`
byte-identical.

## 5. Dynamic loop (community RTX 3090, $0.22/h; 4 arms × [200 gen + 200 repair])

Corpus: the **fresh pool alone cleared the gate** — 24,802 / 24,746
supervised tokens per arm against a 15k floor, no pooling needed. This
was pre-registered before any number existed, on the reasoning that
every committed pool predates this wave's vocabulary and would dilute
exactly the constructs G2 must measure. The manifest records
`counts_source.roots = "amp4-only"`.

A stale-verdict re-validation was also pre-registered (`collect_verified`
trusts the `passed` verdict recorded at generation time and never
re-checks against the current transpiler). It reported 0 drops — but it
never got to test an old program, because fresh-only passed. **It did not
fire; it was not exercised.** It stays armed for any wave that must pool.

| arm | pass@1 | pass@10v | tok→green | censored | strict repair |
|---|---:|---:|---:|---:|---:|
| base-ox-7 (card v0.6) | 0.070 | 0.15 | 96.1 | 186 | 0.450 |
| base-rs-7 (control) | **0.565** | 0.60 | 66.8 | 87 | 0.890 |
| tune-ox-7 | 0.595 | 0.75 | 85.7 | 80 | 0.645 |
| tune-rs-7 | 0.920 | 0.95 | 70.4 | 16 | 0.735 |

**G1 control: PASS**, 0.565 for a fifth environment. **A published claim
is narrowed here.** Wave 2 reported that *every* companion figure
reproduced to the digit; on this 3090 they do not. pass@1 (0.565) and
censored sessions (87) are exact, but pass@10v reads 0.60 vs 0.65,
tokens-to-green 66.8 vs 65.7, strict repair 0.890 vs 0.895. The likely
mechanism is that llama.cpp's CUDA kernels are not numerically identical
across GPU architectures, so a few sampling paths diverge at temperature
0.2. The honest claim is narrower than the published one: **pass@1 is
robust across five environments and three GPU architectures; the harness
is not bit-identical across them.** Wave 2's stronger phrasing held only
because both runs were on 4090s.

**G1 floor: MET** at 0.595 against 0.455 — but **down from wave 2's
0.755**, and the first candidate cause is a decision made in this report's
own protocol: fresh-only gave 24.8k tokens from one amplification run,
where wave 2 pooled 29.8k across four runs at two temperatures. Less
scale *and* less sampling diversity, accepted deliberately to keep the
vocabulary undiluted. Corpus-size sensitivity is established (wave 1:
7.4k → 0.420, 29.8k → 0.755). Strict repair moved the other way
(0.575 → 0.645), which cuts against a simple undertraining story. Not
re-run: the point estimate stands.

### Token efficiency — the objective, and it went backwards

Primary estimand per SPEC §59.7: pair cells by `(seed, task)`, require
green in both arms, restrict to cells green in **every** wave compared,
and report the set with the ratio.

| construction | wave-0 | wave-1 | wave-2 | wave-3 |
|---|---:|---:|---:|---:|
| unconditional mean | 1.24 | 1.13 | 1.198 | 1.217 |
| own paired set | 1.174 | 1.218 | 1.188 | 1.150 |
| **composition-controlled (61 common cells, 10 tasks)** | 1.2514 | 1.3545 | **1.0799** | **1.1315** |

**The dynamic ratio worsened, 1.0799 → 1.1315.** On identical cells
Oxide's own tokens *rose* 71.8 → 74.9 while the retrained Rust control
stayed flat (66.5 → 66.2), so this is not a scoring artifact of the
control moving.

Set arithmetic, stated because §59.7 exists to force it: wave 2 published
**1.067** on the *three-wave* common set of 67 cells. Adding wave 3
changes the common set to 61 cells, on which wave 2 reads 1.0799. Both
are correct on their own set. A ratio without its set is not a
measurement.

**The two estimands moved in opposite directions this wave** — static
1.0875 → 0.9863, dynamic 1.0799 → 1.1315. §6 explains why.

## 6. G2 uptake — the corpus barely taught most of the vocabulary

> **AMENDED 2026-08-30, same day.** This section was first published under
> the heading "the model declined most of the vocabulary", and that
> framing was an overclaim. §6.1 below measures how often each construct
> appears in the training corpus itself, which the original section never
> checked: `swap` appears in **2 of 294** training examples. A construct
> seen twice was not declined — it was never taught. The counts in the
> table below are unchanged and correct; the interpretation around them
> is corrected here, and §8's feed-forward is rewritten accordingly. The
> original heading is left visible in this note rather than deleted.

Per reply file, counted at most once each.

| construct | card arm (8,600 files) | tuned arm (441) | base-ox control (758) |
|---|---:|---:|---:|
| `reverse` | 209 | **50** | 58 |
| `set` | 105 | 8 | 8 |
| `swap` | 55 | **0** | 0 |
| `count_if` | 170 | **0** | 8 |
| `x -> expr` (shipped spelling) | 102 | **4** | 1 |
| `\|x\|` (rejected spelling) | 390 | **43** | 73 |

**The spelling ruling is falsified.** `x -> expr` was shipped over Rust's
`|x|` on the reasoning that an unfamiliar spelling would make the
no-capture restriction legible, accepting a possible uptake cost. The
tuned arm reaches for `|x|` over the arrow by roughly **10:1** (43 vs 4);
the card arm by 4:1 (390 vs 102). **Familiarity beat legibility.** The
instrument was built with both counters specifically so this ruling could
be convicted, and it was.

Guarded before the finding was trusted: the `\|\s*\w+\s*\|` pattern also
matches a chained boolean OR (`a || b || c` contains `| b |`). Classified
all 43 tuned-arm matches — **0 were OR-chains**; the samples are
unambiguous Rust closures.

**`swap` got zero tuned uptake** despite being the corpus's single
largest token gap. It shipped on cost evidence alone — but see §6.1
before reading that as a verdict on the construct.

### 6.1 Uptake tracks exposure × familiarity, and nothing shipped this wave got a fair test

How often each construct appears in the 294 oxide training examples the
tuned arm actually learned from, against the uptake it then showed:

| construct | % of training corpus | tuned uptake |
|---|---:|---:|
| `+=` | 24.1% | 194 |
| `range` | 24.1% | 150 |
| `unwrap_or` | 10.2% | 58 |
| `sort` | 5.1% | 10 |
| `count_if` | 2.4% | **0** |
| `x -> expr` | 2.4% | 4 |
| `reverse` | 1.7% | **50** |
| `set` | 1.7% | 8 |
| `swap` | 0.7% | **0** |
| `count` | 0.7% | 14 |

Uptake rises with corpus exposure, and the two anomalies separate a
second force. **`reverse` drew 50 uses from 1.7% exposure while
`count_if` drew 0 from more exposure (2.4%).** The difference is prior
familiarity: `reverse` is a name the model already knows from Rust and
Python; `count_if` is not Rust idiom. So **uptake ≈ exposure ×
familiarity** — `swap` failed on exposure (0.7%, a name the model does
know), `count_if` failed on familiarity.

Why exposure is so low is structural, not accidental. A new construct
reaches the training corpus by only two routes: the one to three
reference programs whose task shape needs it, and whatever the base model
happens to emit from the card and the oracle happens to pass. Both are
thin for anything new. **The pipeline systematically under-teaches its
own new vocabulary**, and this wave's adoption numbers are measurements
of that pipeline at least as much as of the constructs.

The honest status of every construct shipped this wave is therefore
*untested for adoption*, not *rejected*. The falsification of the
spelling ruling in the table above still stands on its own terms —
`x -> expr` and `|x|` were available to the model on equal footing, and
it chose `|x|` 10:1 — because that comparison is between two spellings
at the same exposure, not between a taught and an untaught construct.

**The most valuable result is the shape of what the model writes
instead.** The recurring form is:

```
argmax(items, |item| calculate_cos...)
```

The model is not reaching for a narrow counting builtin. It is inventing
**higher-order functions with Rust closure syntax**. The measured demand
is for a general `filter`/`max_by`/`argmax` surface spelled `|x|` — not
for `count_if` spelled `x ->`.

Wave-1 vocabulary remains live in the tuned arm: `range(a,b)` 150,
`unwrap_or` 58, `sort` 10, `min`/`max` 1; `+=` 194, `count` 14.

G2 lens, stated so the counts are reproducible: free-call guards
`(?<![.\w])<name>\s*\(` for `swap`/`reverse`/`set`/`count_if`;
`\w+\s*->\s*` for the predicate literal; `\|\s*\w+\s*\|` for the Rust
closure spelling; compound-assign from `demand_census.V2_FAMILIES`.

## 7. Spend

Wave-3 loop: **6.2 h × $0.22 = $1.36** on a community RTX 3090 — taken
over the authorised $0.74 secure 4090 when community capacity reappeared
minutes after an 8-hour poll expired empty (48/48 checks `Low`, zero
errors). Program total across four waves ≈ **$13.8** of the $23 tranche.

Amplification timings, measured: 1.5B 48 min, 7B 77 min, 14B 136 min.
Scaling is strongly sub-linear in model size because every session
carries a rustc compile — constant CPU work at 1,600 sessions per size,
dominating GPU time. Two wall-clock estimates were wrong before this was
measured.

## 8. Feed-forward to wave 4

1. **The gap between the estimands is now the subject.** Static says the
   language can express these tasks in fewer tokens than Rust; dynamic
   says the model does not. Wave 4's question is not "can we shorten the
   language further" — it is **"what makes a model actually use a
   construct?"** Every remaining item below is a probe of that.
2. **Ship `|x|` as the predicate spelling.** Measured 10:1 demand against
   the arrow. The no-capture restriction can be kept and taught by the
   diagnostic (`OX0205`) rather than by the syntax; the argument that an
   unfamiliar spelling would teach it is now falsified. Expect the
   re-spelling to be near-free statically (`|x|` costs 1 token more per
   use, ~2 tokens across the corpus).
3. **Build the higher-order surface the model already writes:**
   `filter`, `max_by`/`argmax`, `any`/`all` over a predicate. This is
   measured demand, in the model's own spelling, and it subsumes
   `count_if`.
4. **Fix the exposure hole before judging any construct.** Per §6.1 the
   pipeline under-teaches its own new vocabulary: `swap` reached the
   tuned model in 2 of 294 examples. Two levers, and wave 4 should
   pre-register which it pulls: author reference tasks whose shapes
   *need* the new constructs, and/or oversample training examples
   containing them. Then re-read uptake. The prediction is explicit and
   falsifiable — **if uptake tracks exposure, `swap` at ~10% of the
   corpus should move off zero; if it stays at zero, the construct
   really is one models do not reach for**, and that is worth knowing
   about `swap` specifically rather than about the pipeline.
5. **Prefer familiar names and spellings.** `reverse` outdrew `count_if`
   at lower exposure purely on prior familiarity. Where a Rust or Python
   name exists for an operation, use it; where it does not, expect to pay
   for the novelty in exposure. This is the same lesson the spelling
   ruling learned the hard way.
6. **Corpus scale vs vocabulary density.** The fresh-only choice cost
   pass@1 (0.755 → 0.595) and bought undiluted uptake measurement. Wave 4
   can have both: amplify fresh at more seeds, or pool and weight. Decide
   deliberately and pre-register it.

**A design principle this wave earned, worth stating above the item
list:** every win across three waves came from *removing* ceremony —
implicit linear ownership (structs 0.920, the only class that beats Rust
without any added vocabulary), no borrow annotations, no lifetimes —
while every *added* novel construct fought the model's priors. Wave 3
shipped four constructs, and the two that landed (`reverse`, `set`) are
the two with existing Rust namesakes. **Subtractive design wins;
additive design pays for novelty.** If that holds through wave 4, it
bounds how novel this language can usefully be, and that is a finding
about the premise rather than about any construct.
6. **Card-quality returns are diminishing:** 0.025 → 0.060 → 0.070 across
   v0.4 → v0.4.1 → v0.6. Scope any card cycle against +0.010, not +0.035.
7. **Standing debt:** `/=` (two concrete sites, n007 and n009); fold
   `count`/`swap`/`reverse`/`set`/`count_if` into the demand census
   families; brace-masking fix; split the 954-line `demand_census.py`;
   and SPEC §60.2's open question of whether a partial-operation category
   belongs in this language at all.
