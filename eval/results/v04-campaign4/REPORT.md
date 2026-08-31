# v0.4 efficiency cycle, wave 4 — full-loop report

2026-08-31. Spec: `docs/superpowers/specs/2026-08-30-v04-efficiency-wave4-design.md`.
Committed home of this wave's endpoint readings, guard reads, uptake
counts, learnability ratios and feed-forward. Metric constructions are
stated as computed. The cycle's output is the next cycle's input; this
report ends with that hand-off, not a verdict.

## The wave in one line

**Familiarity is a lever — the `|x|` re-spelling drew 5–6× the uptake of
wave 3's arrow at equal exposure — and wave 0's most discouraging
result, that Oxide's disadvantage grows with model size, is reversed.**
Dynamic token efficiency still moved the wrong way, and that gap is now
the project's central open problem.

## 1. What shipped

- **The predicate literal re-spelled `x -> expr` → `|x| expr`** (SPEC
  §63.1), reversing a wave-3 ruling on measured evidence. Semantics
  unchanged: still no captures (`OX0205`), still `Pred<T>`, same emitted
  closure. A `PIPE` token was added; `||` is matched by the two-char
  table first, and a dedicated mutation test proves that guard bites —
  the one way this change could have silently turned every disjunction
  in the corpus into a predicate.
- **`filter(v, |x| ...)` alongside `count_if`** (§63.2), deliberately,
  so efficiency and learnability point at different constructs and the
  model breaks the tie.
- **The learnability estimand** (§63.3): uptake ÷ corpus exposure, with
  both terms carried in every row.
- **The 14B quartet**, the first scale read since wave 0.

## 2. Static endpoints — all five HIT

| class | wave-3 close | wave 4 | target | verdict |
|---|---:|---:|---|---|
| arithmetic/loops | 1.010 | 1.010 | ≤1.02 | HIT |
| strings | 1.061 | 1.061 | ≤1.07 | HIT |
| structs/option | 0.920 | 0.920 | ≤0.93 | HIT |
| vectors | 0.969 | 0.972 | ≤1.00 | HIT |
| **overall** | 0.9863 | **0.9871** | ≤0.99 | **HIT** |

The re-spelling cost **exactly the 2 tokens §63.1 predicted** (2300 →
2302). Parity survives the project's first deliberate trade of
efficiency for learnability.

Re-authoring sweep found one `filter` candidate and **rejected** it:
n058 interleaves a side effect with accumulation and its predicate would
need to capture `reported`, which mutates during iteration — impossible
by design. Recorded because under the amended bias rule a missed
substitution is a defect, so the negatives must be auditable. All 40
pairs green through the oracle; every `rust.rs` byte-identical.

## 3. Dynamic loop — eight arms (community RTX 3090, $0.22/h)

Corpus: fresh pool alone cleared the gate at **24,080 / 24,103** tokens
per arm against the 15k floor (`counts_source: amp5-only`,
contamination 0 of 661). The stale-verdict re-validation again reported
0 drops and again was **not exercised**, because fresh-only passed.

| arm | pass@1 | pass@10v | tok→green | censored | strict repair |
|---|---:|---:|---:|---:|---:|
| base-ox-7 (card v0.7) | 0.075 | 0.15 | 106.1 | 185 | 0.450 |
| base-rs-7 (control) | **0.565** | 0.60 | 66.8 | 87 | 0.890 |
| tune-ox-7 | 0.645 | 0.75 | 88.0 | 68 | 0.650 |
| tune-rs-7 | 0.870 | 0.90 | 63.1 | 26 | 0.735 |
| base-ox-14 | 0.525 | **0.75** | 134.7 | 70 | 0.805 |
| base-rs-14 | 0.550 | 0.55 | 74.5 | 90 | 0.950 |
| tune-ox-14 | **0.745** | 0.95 | 91.2 | 38 | 0.875 |
| tune-rs-14 | 0.920 | 1.00 | 69.4 | 15 | 0.750 |

**G1 control: PASS** — `base-rs-7` = 0.565 for a **sixth** environment,
and this time every companion figure matches wave 3 exactly. That
sharpens wave 3's narrowed claim into something better specified:
**pass@1 is invariant across GPU architectures; the secondary metrics
are invariant *within* an architecture and drift slightly across them**
(wave 2 was a 4090; waves 3 and 4 were 3090s and agree to the digit).
Consistent with llama.cpp's CUDA kernels differing between Ampere and
Ada.

**G1 floor: MET** at 0.645, up from wave 3's 0.595 on a slightly smaller
corpus. Two things changed at once this wave, so that +0.050 cannot be
attributed to the re-spelling alone.

## 4. The scale result — wave 0's trend reverses

| tuned ox↔rs gap | 7B | 14B | direction |
|---|---:|---:|---|
| wave 0 | 0.330 | 0.445 | **widening** |
| wave 4 | 0.225 | **0.175** | **narrowing** |

Wave 0's finding — that fine-tuning saturated Oxide at ~0.55 regardless
of size while tuned Rust ran to 0.990 — does not hold on the current
language. Tuned Oxide now **scales with size** (0.645 → 0.745) where it
was previously flat (0.555 → 0.545), and `tune-ox-14` is **+0.200** on
the same arm in wave 0.

Two further readings:

- **Untuned at 14B is near parity: 0.525 vs 0.550**, against wave 0's
  0.170 gap. `base-rs-14` reads **exactly 0.550 in both waves**, so the
  control confirms the entire movement is on the Oxide side (+0.145),
  which is what waves 1–4 built.
- **With a verifier, untuned Oxide beats Rust at 14B: pass@10v 0.75 vs
  0.55.** The first capability win for Oxide at any tier in the
  project's history.

**No cross-size claim was pre-registered** (spec §4) and none is made
here beyond the within-wave comparison. This is the first 14B read since
wave 0; its job was to generate a hypothesis, and it did.

## 5. Learnability — the estimand earns its place immediately

Corpus exposure measured over the 282 oxide training examples actually
used; uptake counted per reply file, at most once each.

| construct | uptake (7B) | exposure | learnability |
|---|---:|---:|---:|
| `count` | 36 | 1.1% | **3384** |
| `reverse` | 50 | 1.8% | 2820 |
| `filter` | 11 | 1.4% | 776 |
| `+=` | 174 | 23.8% | 732 |
| `\|x\|` predicate | 19 | 3.9% | 487 |
| `range` | 98 | 23.8% | 412 |
| `unwrap_or` | 17 | 9.9% | 171 |
| `count_if` | 0 | 2.1% | 0 |
| `set` | 0 | 1.4% | 0 |
| `swap` | 0 | 0.7% | 0 |

Raw uptake would call `+=` the dominant construct at 174 uses. It needed
**13× the exposure** of `reverse` to get there. `count` and `reverse` —
both names the model already knows — are the genuinely learnable ones.
Only the ratio shows that, which is why §62.1 made it an estimand.

### 5.1 The wave's central prediction: CONFIRMED

| | wave 3 (`x ->`) | wave 4 (`\|x\|`) |
|---|---:|---:|
| tuned 7B uptake | 4 | **19** |
| tuned 14B uptake | — | **24** |
| corpus exposure | 2.4% | 3.9% |

**5–6× the uptake for a spelling change alone**, with zero arrow uses
remaining. The spec's falsification condition was "if uptake does not
move, familiarity is not the lever §62 claims and §62.2's quadrant
ordering is wrong." Uptake moved. The ordering stands.

### 5.2 `filter` vs `count_if`: learnability beat efficiency

At 7B the model chose `filter` **11 to 0** — the more familiar, *more
expensive* spelling — resolving §63.2's experiment in favour of
learnability. At 14B the counts invert weakly (`count_if` 2, `filter` 0),
which at these magnitudes is noise rather than a contrary result, and is
reported as such.

### 5.3 `swap` and `set` remain at zero, now with exposure stated

0.7% and 1.4% corpus exposure. Per wave 3's §6.1 amendment these are
**untested for adoption, not rejected**. The exposure lever is still
unpulled (spec §2 explains why it could not be pulled cheaply this wave).

## 6. Token efficiency — the honest counterweight

Primary estimand per SPEC §59.7: pair by `(seed, task)`, green in both
arms, restricted to cells green in **every** wave compared.

**7B, 59 cells / 9 tasks common to all five waves:**

| wave-0 | wave-1 | wave-2 | wave-3 | wave-4 |
|---:|---:|---:|---:|---:|
| 1.2683 | 1.3710 | 1.0858 | 1.1411 | **1.1982** |

**14B, 110 cells / 14 tasks common to wave-0 and wave-4:** 1.1369 →
**1.1575**.

**Dynamic efficiency moved the wrong way at both tiers**, while the
static estimand sits at 0.9871. Some of the 7B movement is *bought* — the
re-spelling costs 2 tokens statically and `filter` is deliberately more
verbose than `count_if` — but not all of it, and the report does not
claim otherwise.

The 14B reading is the sharper one: from wave 0 to wave 4 the controlled
ratio barely moved (1.1369 → 1.1575) while capability moved hugely
(0.545 → 0.745). **This wave's language work bought capability, not
dynamic tokens.**

The static/dynamic divergence is now four waves old and is the project's
central open problem: the language can express these tasks in fewer
tokens than Rust, and models do not.

## 7. The card never documented its operators

A frontier-model probe run during the campaign exposed a defect present
in **every card the project has measured** (SPEC §63.6). Claude Sonnet,
given card v0.7 and the 20 eval prompts, barred from this repository, no
compiler, `expected_stdout` withheld, wrote 20 programs in one pass:
**all 20 passed the real oracle** (transpile, rustc, execute,
byte-compare). Programs committed under `sonnet-probe/`.

It reported that the card documents no operator set. Confirmed: `==`,
`!=`, `%`, `<=`, `>=`, `&&`, `||`, `!` appear **zero times** in the card,
and at wave 2's, wave 3's and wave 4's cards too. It scored 20/20 by
assuming Rust's operators and being right.

- **For §62's thesis:** the strongest available validation. The card did
  not need to be complete because a Rust prior filled the hole.
- **For the instrument:** smaller models cannot fill that hole.
  `base-ox-7` reads 0.075 and `base-ox-1.5` read 0.000. Every untuned
  Oxide arm in project history may have been depressed by a
  documentation gap rather than by the language.

Card v0.8 adds the operator table, transcribed from the implementation
rather than assumed. **It is not what wave 4 measured** — this campaign
ran v0.7 from a pod clone pinned at `7769c2f0`, and none of these
numbers change.

**Lens note:** the probe ran under a different harness (agentic
scaffolding, different sampler, freedom to revise within a turn) against
arms that take one attempt at temperature 0.2. It generates a hypothesis
about the tier curve — 1.5B 0.000 · 7B 0.075 · 14B 0.525 · frontier
20/20 — it does not extend it.

## 8. Spend

Wave-4 loop: **7.3h × $0.22 = $1.61**, inside the $3.00 cap, against a
$1.85 estimate. Program total across five waves ≈ **$15.4** of the $23
tranche. Amplification 217 min (1.5B 40 / 7B 71 / 14B ~106), four
symmetric trainings, eight campaign arms.

Train losses, same corpus and config: ox 7B 0.1953 / 14B **0.1821**;
rs 7B 0.1284 / 14B 0.1303. The 14B fits Oxide better than the 7B does
while Rust stays flat — a within-wave comparison, and weak evidence on
its own, but pointing the same way as §4.

## 9. Feed-forward to wave 5

1. **Re-measure the card-only arms against v0.8** — `base-ox-7` and
   `base-ox-14`, changing nothing else. The cheapest high-value
   experiment on the board. If the untuned arms move, four waves of
   card-only readings were partly measuring documentation, and §7's
   instrument concern is confirmed.
2. **Pull the exposure lever, properly designed.** `swap` (0.7%) and
   `set` (1.4%) remain untested for adoption. Spec §2 records why it
   could not be done cheaply: new reference tasks break comparability
   with waves 1–4, and oversampling breaks the token-matching. It needs
   either a second reference corpus or a matching scheme that survives
   weighting. Pre-register the prediction: at ~10% exposure `swap`
   should move off zero, and if it does not, that is a real finding
   about `swap`.
3. **The static/dynamic divergence is the subject now.** Four waves of
   static improvement (1.22 → 0.9871) have not moved the controlled
   dynamic ratio, which sits between 1.09 and 1.20 throughout. Wave 5
   should stop assuming the static estimand predicts the dynamic one and
   start measuring *why* it does not — a per-construct token-diff
   between what references write and what tuned models write would say
   where the surplus actually goes.
4. **Scale looks like the strongest lever available.** Every capability
   comparison improves at 14B, and the untuned 14B is at parity. If the
   project's question is "can a model use this language well," the
   answer is materially different at 14B than at 7B, and every claim in
   waves 1–3 was a 7B claim.
5. **Card returns are saturating:** 0.025 → 0.060 → 0.070 → 0.075 across
   v0.4 → v0.4.1 → v0.6 → v0.7. Increments halving each time. Scope any
   card cycle against +0.005, not the +0.035 of the first jump — though
   §7 means v0.8 may break that pattern, which is itself worth knowing.
6. **Standing debt:** `/=` (two concrete sites); fold the wave-3/4
   constructs into the demand-census families; brace-masking fix; split
   the 954-line `demand_census.py`; SPEC §60.2's unresolved question of
   whether a partial-operation category belongs in this language.
