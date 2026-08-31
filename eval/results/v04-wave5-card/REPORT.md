# v0.4 wave 5 (A) — the operator table does nothing

2026-08-31. Spec: `docs/superpowers/specs/2026-08-31-v04-wave5-card-operators-design.md`.
A single-variable experiment with predictions registered before the run.
**Every prediction was falsified.** This report says so plainly, which is
what the spec committed to.

## The question

Wave 4's Sonnet probe found the language card had **never** documented
its operator set — `==`, `!=`, `%`, `<=`, `>=`, `&&`, `||`, `!` appear
zero times in the card at waves 2, 3 and 4 (SPEC §63.6). A frontier
model scored 20/20 from that card anyway by assuming Rust's operators.

The worry that followed: smaller models have weaker priors, so **every
untuned Oxide arm in project history might have been measuring a
documentation gap rather than the language.** Card v0.8 added the table.
This wave asked whether it changes anything.

## Result — falsified at every tier

One variable: card v0.7 → v0.8. Same checkpoints, same 20 tasks, same
harness, same sampler, same one-attempt construction, same hardware
class. No amplification and no training, because card-only arms use the
untuned base model.

| arm | v0.7 | v0.8 | pre-registered prediction | verdict |
|---|---:|---:|---|---|
| base-ox-1.5 | 0.000 | 0.000 | > 0.000 | **falsified** |
| base-ox-7 | 0.075 | 0.060 | ≥ 0.150 (a doubling) | **falsified** |
| base-ox-14 | 0.525 | 0.500 | ≥ 0.525 | **falsified** |
| base-rs-7 (drift guard) | 0.565 | **0.565** | 0.565 ± 0.010 | **PASS** |

All three treatment arms moved slightly *down*, every movement inside
noise (14B: 105 → 100 successes of 200; 7B: 15 → 12). The honest
statement is **no detectable effect at any tier**.

**The drift guard is clean**, and matters: the Rust arms never read the
Oxide card, so `base-rs-7` had to be still. It reads 0.565 with every
companion figure matching wave 4 exactly (pass@10v 0.60, tok→green 66.8,
censored 87, strict repair 0.890). The falsification therefore stands on
a valid run rather than on drift. That is also a **seventh** environment
reproducing 0.565.

## Why — the mechanism check answers it

The spec required a mechanism read: capability should move *because*
operator use moves, or the causal story is wrong. Operator presence
across `base-ox-7`'s 764 reply files under v0.8:

| `==` | `!` | `%` | `/` | `<=` | `\|\|` | `&&` | `>=` |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 160 | 190 | 136 | 120 | 72 | 4 | 0 | 0 |

**The model was already using the operators heavily.** There was no
behavioural gap for the table to fill. The card lacked the
documentation; the model did not lack the knowledge, because its Rust
prior supplied it — exactly as it did for Sonnet. Documenting something a
model already does changes nothing.

## What this kills, and what it re-frames

**Killed:** SPEC §63.6's instrument concern. The claim that "every
untuned Oxide arm in project history may have been depressed by a
documentation gap" is **wrong**. Those readings were real measurements.
`base-ox-7` at 0.075 measures the 7B, not the card's incompleteness.
§63.6 is amended accordingly.

**Re-framed:** the Sonnet result. It was read as a frontier model
papering over a defect that smaller models could not. But the defect
does not bind at *any* tier, so Sonnet was not gap-filling — it is simply
that much better at the task. The card was adequate all along; capability
is the variable. The 20/20 stands as a capability datum, not as evidence
about the card.

**Surviving, and unaffected:** SPEC §62's familiarity thesis. Wave 4
tested it directly — the `|x|` re-spelling drew 5–6× the arrow's uptake
at equal exposure — and this null result says nothing about it either
way. Familiarity in *spelling a construct the model must use* is a
different claim from *documenting operators the model already uses*.

**One real improvement, not capability:** `base-ox-14`'s tokens-to-green
fell 134.7 → **118.0**, about 12%. The table made the model more concise
without making it more correct — consistent with trimming exploratory
output rather than unlocking anything. Card v0.8 is kept for that reason
and because a spec should document its own language.

## Tier note

`base-ox-1.5` read 0.000 under both cards, as it has under every card
ever measured, with strict repair 0.110. Per SPEC §64 (owner ruling,
this wave) the 1.5B is **dropped from card-only arms** — an arm that can
only report zero cannot discriminate — while being **retained in
amplification** (138 of 759 verified programs, ~18% of corpus, ~$0.15)
and **in tuned arms** (wave 0's `tune-ox-1.5` reached 0.485). The rule
recorded: drop an arm when it cannot discriminate, not when it scores
badly.

## Spend

**1.63h × $0.22 = $0.36**, against a $1.00 cap and a $0.35 estimate.
Program total ≈ **$15.8** of the $23 tranche.

The experiment cost about a quarter of a dollar and closed off a
hypothesis before anything was built on it. That is the cheapest useful
outcome available, and it is why the wave was scoped to one variable.

## Feed-forward

1. **Stop looking at the card for the untuned 7B's failure.** Two card
   revisions (v0.6→v0.7→v0.8) moved it 0.070 → 0.075 → 0.060: flat.
   Whatever limits card-only Oxide at 7B is not documentation. The tier
   evidence says it is capability, and the 14B's 0.500–0.525 says the
   same boundary sits between 7B and 14B.
2. **The static/dynamic divergence remains the subject** (wave 4 §9.3),
   untouched by this wave.
3. **The exposure lever remains unpulled** (wave 4 §9.2); `swap` and
   `set` are still untested for adoption.
4. **Card returns are now measured as saturated, not merely suspected:**
   0.025 → 0.060 → 0.070 → 0.075 → 0.060 across five card versions. The
   card is done as a lever at this tier.
