# v0.4 wave 8 (Phase A) — the static advantage does not survive scale

2026-09-01. Spec: `docs/superpowers/specs/2026-08-31-v04-wave8-large-tasks-design.md`.
Authoring and static measurement, run entirely locally. **GPU cost: $0.**

## Result

| task set | programs | median oxide tokens | oxide/rust |
|---|---:|---:|---:|
| train references | 40 | 57 | 0.9871 |
| eval references (wave 7A) | 20 | 73 | 0.9462 |
| **large tier (this wave)** | **20** | **292.5** | **1.0622** |

**Oxide is below parity on 40–150 token programs and above parity on
200–600 token programs.** The pre-registered reading was that a rise
toward 1.00 would mean the advantage is a fixed prelude constant that
dilutes with size. The advantage does not merely dilute — it inverts.

Every prior static claim in this project was measured on programs about
a quarter this size. **They are scale-bound, and should be quoted that
way from now on.**

## The tier

20 tasks, both arms authored to the same discipline, all oracle-verified
against a committed `expected_stdout`. Sizes measured with the pinned
tokenizer, not estimated:

| arm | min | median | max |
|---|---:|---:|---:|
| oxide | 231 | 292.5 | 389 |
| rust | 201 | 276.5 | 346 |

All 40 programs land inside the 200–600 band. Contamination is **zero in
both directions** — against the held-out eval set, and against the
training corpus the v5 adapters were trained on. The second check is the
one that binds Phase B and `contamination_report` did not previously
perform it; it was run separately here and should be folded into the
instrument.

## Where the surplus sits

| class | ratio | surplus | small-tier (eval) |
|---|---:|---:|---:|
| structs/option | **0.9312** | −83 | 0.9187 |
| arithmetic/loops | 1.0222 | +31 | 0.9978 |
| vectors | 1.0825 | +145 | 0.7682 |
| **strings** | **1.2208** | **+248** | 1.0731 |

**Only structs/option survives the size change**, and it survives almost
exactly (0.9187 → 0.9312). That is the implicit-ownership win, and it is
a *per-declaration* saving: it does not decay as programs grow, because
larger programs declare more.

**Vectors is the reversal.** It was the project's proudest number —
1.377 at wave 3's open, 0.7682 on held-out eval tasks — and it reads
1.0825 here. Four waves of vector vocabulary genuinely transferred to
held-out *small* tasks. It did not transfer to large ones.

Ranked worst: `g17` +90 (ordered merge), `g02` +82 (word report),
`g10` +65 (phrase split), `g07` +63 (alphabet shift), `g20` +57 (sieve).
Best: `g18` −69 (settings revisions), `g05` −19, `g16` −18, `g06` −16.

## The strata split bought almost nothing

| stratum | ratio |
|---|---:|
| compositional (12 tasks) | 1.0718 |
| large-linear (8 tasks) | 1.0482 |

The spec pre-committed to publishing this split even if the two strata
read the same, and they nearly do — 2.3 points apart, both above parity.

**So the inversion is not about helper amortisation.** The hypothesis
that motivated the stratification — that Oxide looks bad only where the
model's factoring habit cannot pay off — is not what is happening. Large
linear programs, with no helper functions at all, are also above parity.
The stratification was my judgement call and it did not earn its place;
recorded so nobody re-derives it.

## What actually drives it

These are read off the authored pairs, not posited:

1. **Predicates cannot capture (`OX0205`).** `count_if(v, |x| x < 10)`
   is legal; `count_if(v, |r| r > average)` is not, because `average` is
   an enclosing binding. At 40 tokens thresholds are literals and the
   restriction is free. At 300 tokens they are computed, and each one
   costs a five-line explicit loop. **This is a scale-dependent language
   cost the small tiers structurally could not see.**
2. **No `map`, `max_by_key`, `any`, `all`.** Rust collapses a whole loop
   into a chain; Oxide writes the loop. `g03` pays this for
   `.map().sum()`, `g11` for `.all()`.
3. **Indexed access is `unwrap_or(get(v, i), 0)` against Rust's `v[i]`.**
   A per-access cost that scales with index density — which is why the
   three most index-heavy tasks (`g17`, `g20`, `g11`) rank near the top.
4. **No string `split` and no string `reverse`.** `g10` hand-rolls a
   12-line `split_words`; `g02` hand-rolls `rev_str`. Strings was already
   the worst class and this is why it degrades further.
5. **`vec().push(a).push(b)...` against `vec![a, b, ...]`.** Scales with
   the size of the literal data a program carries, and large programs
   carry more.

Items 1–4 are a design agenda. Item 5 is the cheapest thing on it.

## The re-review changed the answer, which is why it exists

The first measurement read **1.0766**. The symmetric re-review pass found
that six Oxide programs used a manual `while i < len(v) { ... i += 1 }`
where the Rust arm already had an idiomatic counted loop (`for i in
1..series.len()`), even though Oxide has `range`. Converting exactly
those six — and leaving every `while` whose Rust counterpart is also a
`while` — moved the ratio to **1.0622**.

**A 1.4-point authoring asymmetry against Oxide, found by a pass run
specifically because the result favoured the arm I did not author.** The
same pass earlier caught `g02` hand-rolling a vowel count that
`count_if` does.

## Stated limits

- **Both arms have one author, who has spent eight waves designing one
  of them.** The guards were: author the Rust arm first from the prompt
  alone, then Oxide; then re-review under a criterion fixed before
  looking. The re-review moved the number 1.4 points *toward* Oxide,
  which is evidence the guard has teeth, not proof the bias is gone.
- **Neither arm uses hash-based collections.** Oxide has none, and
  admitting `HashSet` to Rust alone would measure a data-structure gap
  rather than an expression gap. With it, the Rust arm would be shorter
  still — so **1.0622 is conservative in Oxide's favour.**
- **For the 8 linear tasks the oracle is two-arm agreement**, not
  independent hand-computation, since tracing a 30-round simulation by
  hand is not practical. `validate_pair` is built for exactly this. Of
  the 20, `g16` (digit-square chain), `g20` (25 primes below 100, sum
  1060), `g17` (merge, sum 132) and all 12 compositional tasks were also
  confirmed against independently computed values.

## A pre-registration defect, found before Phase B rather than after

The spec's three dynamic states are stated as bands on the *raw*
large-tier ratio: ≤1.05, 1.05–1.30, >1.30. Those thresholds were
calibrated when the reference ratio was assumed to sit near 0.94.

**It now sits at 1.0622, so a model that matched the references exactly
would score 1.0622 and land in "state 2: real, size-independent model
surplus" — while its actual surplus is zero.**

The endpoint must be the **surplus**: the model's oxide/rust ratio
divided by the references' ratio over the same green cells. That is how
wave 6's 28% was actually computed (1.1982 ÷ 0.9393 = 1.276), so this
restores the intended estimand rather than inventing one. The spec is
amended accordingly, before any Phase B run. **This is the same class of
error that cost waves 2 through 6: a comparison whose two halves were
not on the same footing.**

## Provenance

- **2026-09-02.** The training-corpus direction (feed-forward item 6) is
  now in the instrument rather than run by hand: `python -m
  eval.train_corpus --source large --train-corpus
  eval/results/v04-campaign4/matched-v5 --train-tasks
  eval/train/tasks.jsonl` reproduces both zeros — 40 subject programs and
  20 prompts against the v5 corpus's 661 programs and 40 prompts — and
  exits non-zero on any hit.

## Feed-forward

1. **Quote the static claim with its scale.** "Below parity" is true of
   40–150 token programs and false of 200–600 token ones. The published
   write-up must carry both numbers or neither.
2. **Predicate capture is now the top-ranked language gap**, and it is a
   design question the project has already circled twice (§62.2, wave 3's
   arrow-vs-bar). It was cheap to leave unsolved only because the
   benchmark was too small to bill for it.
3. **`vec![...]`-style literal construction is the cheapest item** on the
   agenda and has no design risk.
4. **structs/option holding at 0.9312 across a 4× size change is the
   result worth keeping.** It is the one mechanism shown to scale.
5. **Phase B is still worth running**, and is now more interesting: the
   reference arm crossing parity means the model and the language are no
   longer confounded in the same direction. Run it against the corrected
   surplus endpoint.
6. Fold the training-corpus direction into `contamination_report` so a
   future tier gets both checks by command.
