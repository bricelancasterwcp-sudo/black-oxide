# Familiarity is the lever

*Black Oxide findings series — 2026-09-02. All numbers are reproducible
from this repository; sources are linked inline. Paths are relative to
`eval/results/` unless stated.*

## The claim

When a construct is added to a notation a small model must write, what
decides whether the model uses it is not how much it saves but **how
familiar it already is**: uptake tracks corpus exposure multiplied by
prior familiarity, a Rust spelling beat a novel spelling of the same
construct 10:1 on equal footing, and the more familiar *and more
expensive* of two builtins won 11–0. The complement holds too:
documenting something the model already knows changes nothing, so the
language card saturated as a lever after one revision. Every gain across
nine waves came from deleting ceremony or from spelling a construct the
way Rust or Python already spells it. Novelty is a cost on the
ease-of-learning objective (SPEC §62), never a goal.

## A design ruling, falsified by the instrument built to convict it

Wave 3 shipped a predicate literal spelled `x -> expr`, over Rust's
`|x| expr`, on the reasoning that an unfamiliar spelling would make its
no-capture restriction legible. Both spellings were counted per reply
file, at most once each
([`v04-campaign3/REPORT.md`](../../eval/results/v04-campaign3/REPORT.md) §6):

| spelling | card arm (8,600 files) | tuned arm (441) | base-ox control (758) |
|---|---:|---:|---:|
| `x -> expr` (shipped) | 102 | **4** | 1 |
| `\|x\|` (rejected) | 390 | **43** | 73 |

The tuned arm reached for Rust's spelling over the shipped one by about
**10:1**; the card arm by 4:1. Guarded before it was trusted: the bar
pattern also matches a chained boolean OR, so all 43 tuned-arm matches
were classified — 0 were OR-chains. **Familiarity beat legibility**, and
the comparison is clean because both spellings sat at the same exposure.

Wave 4 re-spelled the construct to `|x|` (SPEC §63.1) and pre-registered
the falsification condition: if uptake does not move, familiarity is not
the lever and §62.2's ordering is wrong
([`v04-campaign4/REPORT.md`](../../eval/results/v04-campaign4/REPORT.md) §5.1):

| | wave 3 (`x ->`) | wave 4 (`\|x\|`) |
|---|---:|---:|
| tuned 7B uptake | 4 | **19** |
| tuned 14B uptake | — | **24** |
| corpus exposure | 2.4% | 3.9% |

Uptake moved 4 → 19 / 24 for a spelling change, with zero arrow uses
remaining. The re-spelling cost exactly the 2 static tokens predicted
(2300 → 2302 across the 40 references). Exposure was higher in wave 4
(3.9% against 2.4%), so the raw 5–6× overstates the per-exposure effect;
on the learnability ratio below the bar reads 487 against the arrow's
167 (4 ÷ 2.4%, computed here from wave 3's row). The ordering stands
either way.

## Uptake ≈ exposure × familiarity

The same wave's G2 read had first been published as "the model declined
most of the vocabulary" and was amended the same day, because nobody had
measured how often each construct appeared in the corpus the tuned arm
learned from. Over the 294 oxide training examples
([`v04-campaign3/REPORT.md`](../../eval/results/v04-campaign3/REPORT.md) §6.1):

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

Uptake rises with exposure, and the two anomalies separate a second
force. **`reverse` drew 50 uses from 1.7% exposure while `count_if` drew
0 from 2.4%.** `reverse` is a name the model knows from Rust and Python;
`count_if` is not Rust idiom. `swap` — the corpus's single largest token
gap, shipped on cost evidence — reached the model in **2 of 294**
examples and drew 0: it failed on exposure, `count_if` on familiarity.

Why exposure is so low is structural. A new construct reaches training
only through the one to three reference programs whose shape needs it,
plus whatever the base model emits from the card that the oracle passes.
**The pipeline systematically under-teaches its own new vocabulary**, so
the honest status of a construct at 0.7% exposure is *untested for
adoption*, not *rejected*. That lever — a second reference corpus, or a
matching scheme that survives oversampling — was never pulled; `swap`
and `set` remain untested.

SPEC §63.3 promoted the ratio to an estimand: **learnability = uptake ÷
corpus exposure**, both terms carried in every row, zero exposure
yielding `None` rather than a flattering infinity or a convicting zero
(wave 4, 282 training examples):

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

Raw uptake calls `+=` dominant at 174 uses; it needed 13× the exposure
of `reverse` to get there. `count` and `reverse` — names the model
already knows — are the genuinely learnable constructs, and only the
ratio shows it.

### `filter` vs `count_if`: the familiar, more expensive spelling won

Wave 4 shipped `filter(v, |x| ...)` alongside `count_if` deliberately, so
efficiency and learnability pointed at different constructs and the
model broke the tie. At 7B it chose `filter` **11 to 0** — the more
verbose form, because it is the one Rust has. (At 14B the counts invert
weakly, 2 to 0 for `count_if`, which at those magnitudes is noise and is
reported as such.)

## Documentation is not capability

The card-only untuned 7B, pass@1 across five card versions
([`v04-wave5-card/REPORT.md`](../../eval/results/v04-wave5-card/REPORT.md)):

| card | v0.4 | v0.4.1 | v0.6 | v0.7 | v0.8 |
|---|---:|---:|---:|---:|---:|
| base-ox-7 pass@1 | 0.025 | 0.060 | 0.070 | 0.075 | 0.060 |

The first revision was worth 2.4×; everything after it is flat. Card
v0.8 was the sharpest test. During wave 4 a frontier probe — Claude
Sonnet given card v0.7 and the 20 eval prompts, barred from the
repository, no compiler, `expected_stdout` withheld — wrote 20 programs
in one pass and **all 20 passed the real oracle**, then reported that the
card documents no operator set. Confirmed: `==`, `!=`, `%`, `<=`, `>=`,
`&&`, `||`, `!` appear zero times in every card the project had ever
measured (SPEC §63.6). It scored 20/20 by assuming Rust's operators and
being right.

The worry that followed — that every untuned Oxide arm in project history
had been measuring a documentation gap — was tested as a single-variable
experiment with predictions registered in advance. Every prediction was
falsified:

| arm | v0.7 | v0.8 | predicted | verdict |
|---|---:|---:|---|---|
| base-ox-1.5 | 0.000 | 0.000 | > 0.000 | falsified |
| base-ox-7 | 0.075 | 0.060 | ≥ 0.150 | falsified |
| base-ox-14 | 0.525 | 0.500 | ≥ 0.525 | falsified |
| base-rs-7 (drift guard) | 0.565 | 0.565 | 0.565 ± 0.010 | pass |

The mechanism check explains the null: across `base-ox-7`'s 764 reply
files under the *old* card, `==` appeared in 160, `!` in 190, `%` in 136
and `/` in 120 (SPEC §63.6, amendment). **The model was already using
the operators.** The card lacked the documentation; the model never
lacked the knowledge, because its Rust prior supplied it — exactly as it
did for Sonnet, whose 20/20 is therefore a capability datum, not
evidence about the card. The one real effect was conciseness: the table
made `base-ox-14` 12% shorter (tokens-to-green 134.7 → 118.0) without
making it more correct. The card was kept because a spec should document
its own language; as a *lever* it is measured-saturated.

Related: the 1.5B reads 0.000 under every card ever measured and 0.485
when fine-tuned (wave 0). It cannot learn the language from a card and
can learn it from a corpus — which is a finding about cards. SPEC §64
drops it from card-only arms because an arm that can only report zero
cannot discriminate, and keeps it in tuned arms and in amplification.

## The four quadrants

SPEC §62.2 orders every possible addition by what it costs a model to
learn, and the record above fills each cell:

1. **Ceremony removed entirely.** Implicit ownership: the model writes no
   annotations and never has to learn not to. structs/option is the only
   class that beats Rust with no vocabulary added — 0.920 on the train
   references, 0.9187 on the held-out eval set, 0.9312 on the large tier.
   Wins on all three objectives; look here first.
2. **Familiar spelling for a familiar concept.** `reverse`, `+=`,
   `range`, `unwrap_or`, `sort`, `filter`, `v[i]`. Near-zero learning
   cost. Every construct that landed is in this cell, and the two wave-3
   constructs that landed (`reverse`, `set`) are the two with Rust
   namesakes.
3. **Novel spelling for a familiar concept.** `x -> expr`, `count_if`.
   Pure cost against ease of learning; measured at 10:1 and 11–0
   against. Avoid.
4. **Novel concept requiring novel spelling.** Justified only by an
   efficiency win no familiar spelling can deliver, and then only with
   the exposure to teach it — which the pipeline does not supply.

The principle wave 3 earned and the later waves confirmed: **subtractive
design wins; additive design pays for novelty.** And the most useful
thing the uptake counters produced was not a number but a shape — the
recurring `argmax(items, |item| ...)` the model wrote instead of anything
it was offered. The model invents higher-order functions in Rust's
closure syntax. That output is the specification of what it wants; the
demand census exists to read it.

## Honest limits

- Every tuned-arm uptake count is one model family (Qwen2.5-Coder 7B and
  14B) on 40–150 token tasks, with corpora of 24–30k supervised tokens
  per arm and constructs at 0.7–4% exposure. Learnability ratios at these
  exposures are read against each other, not as absolute rates.
- The exposure lever was never pulled, so `swap` and `set` are untested
  for adoption rather than rejected, and the prediction that `swap`
  moves off zero at ~10% exposure stands unmeasured.
- The wave-5 report labels its operator-count table "under v0.8" while
  SPEC §63.6's amendment says "under v0.7"; the `==` file count is 160 in
  both arms' committed replies, so the mechanism claim holds under
  either reading. Noted rather than silently resolved.
- The 14B `filter`/`count_if` inversion (0 vs 2) is inside noise and is
  reported as noise.
- These are small-task results. Whether familiarity behaves the same at
  200–600 tokens is not measured here; what the large tier showed is
  that the model reaches for Rust syntax the language lacks — the same
  force, binding earlier.
