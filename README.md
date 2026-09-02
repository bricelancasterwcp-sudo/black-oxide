# Black Oxide

**A findings-and-benchmark record: what happened when a language was
designed, wave by wave, for small LLMs to use more efficiently than Rust.**

Black Oxide is a Rust-like language with **implicit linear types**:
ownership works like Rust's, but there is no borrow syntax. The compiler
infers moves, borrows, and destruction points; types are fully inferred.
It transpiles to Rust, and `rustc` is the oracle — any program Black
Oxide accepts that `rustc` rejects is a compiler bug.

```oxide
struct Reading { label: Str, values: Vec<Int> }

fn first_big(v: Vec<Int>) -> Int {
    let found = -1
    for x in v {
        if x > 10 {
            found = x
            break
        }
    }
    found
}

fn main() {
    let r = Reading { label: "lab", values: push(push(vec(), 3), 42) }
    print(first_big(r.values))        // field access copies; r stays usable
    let r2 = Reading { label: "lab2", ..r }
    print(str_len(r2.label))
}
```

It was a **design project**: design a language small models can use
more efficiently than Rust (SPEC §62 states the three objectives —
usefulness, efficiency, ease of learning for an LLM — and novelty is not
among them), and run a measure → redesign loop where every wave's
measurement feeds the next wave's design. The loop ran nine waves between
2026-08-27 and 2026-09-02, on top of the v0.2–v0.3 repair-probe work
before it, at a total GPU cost of about $19 (including a $2.00 idle-pod loss the
last wave's plan records). It reached convergence, and
**the design loop is closed as of 2026-09-02.** The repository is now a
findings-and-benchmark record, the status its sibling
[robigo](https://github.com/bricelancasterwcp-sudo/robigo) took: the
language, the instruments, every raw model output, every pre-registration
and every withdrawn claim stay public and reproducible.

## The finding

A language designed for LLMs converges to the language they already know,
minus the ceremony they cannot handle. Every gain the loop found came from
one of two moves: deleting ceremony (implicit ownership, the one durable
win, worth about 8% fewer tokens on struct-heavy code at every program
size measured) or spelling a construct the way Rust or Python already
spells it. Every construct that fought the pretraining prior lost, and
the model's prior grows with its capability: a 14B model reaches for
indexing syntax in 29% of its attempts where a 7B does so in 17%, so
**being better at programming makes a model worse at a novel notation.**
At the program sizes where any of this matters, the model could not
produce compiling Black Oxide at all, and doubling model size did not
change that.

## The ledger

Every number carries the program-size tier it was measured on and the
instrument that produced it. Small tiers are 40–150 token programs (the
20 eval tasks, `eval/tasks.jsonl`, and the 40 train references); the
large tier is 200–600 tokens (`eval/tasks-large.jsonl`). Static ratios
are oxide ÷ rust supervised tokens over hand-authored, oracle-verified
reference pairs under a pinned tokenizer; dynamic ratios are
composition-controlled per SPEC §59.7. Sources are under `eval/results/`
unless stated.

| What the instruments established | Measurement | Tier · instrument | Source |
|---|---|---|---|
| **Implicit ownership is the one durable win** | structs/option 0.920 on the 40 train refs, 0.9187 on the 20 held-out eval refs, **0.9312 on the large tier** — a per-declaration saving that holds across a 4× size change while every other class inverts | small + large · static | `v04-campaign4/`, `v04-wave7-attribution/`, `v04-wave8-large/` |
| Ownership is ≈+10pp of the repair advantage | implicit vs explicit ownership: **+59.0 / +35.0 / +9.5pp** on qwen2.5-coder-7b / codegemma-7b / granite-code-8b, 600 repairs each; granite, untouched by every ergonomic fix, isolates ownership at +9.5pp; **0.0pp** at frontier (11/12 vs 11/12) | one seeded defect + diagnostic · ownership probe | [docs/HISTORY.md](docs/HISTORY.md), `ownership-probe-*/` |
| **Familiarity is the lever** | with both spellings available, the tuned 7B chose Rust's `\|x\|` over the shipped `x ->` **43 : 4**; after re-spelling, uptake went 4 → **19** (7B) / **24** (14B) at 3.9% exposure vs the arrow's 2.4%; `filter` beat `count_if` **11–0** — the familiar *and more expensive* spelling won | small · G2 uptake per reply file, learnability = uptake ÷ exposure | `v04-campaign3/` §6, `v04-campaign4/` §5 |
| Uptake ≈ exposure × familiarity | `reverse` drew 50 tuned uses from 1.7% corpus exposure; `count_if` drew 0 from 2.4%; `swap` reached the model in 2 of 294 training examples and drew 0 — the pipeline under-teaches its own vocabulary | small · corpus census vs uptake | `v04-campaign3/` §6.1 |
| **Documentation is not capability** | card-only base-ox-7 pass@1 **0.025 / 0.060 / 0.070 / 0.075 / 0.060** across five card versions; adding the never-documented operator table moved nothing at any tier (1.5B 0.000→0.000, 7B 0.075→0.060, 14B 0.525→0.500) because the model already used `==` in 160, `!` in 190, `%` in 136 reply files under the old card; Claude Sonnet scored 20/20 from that card by assuming Rust's operators | small · single-variable card swap, drift guard clean | `v04-wave5-card/`, SPEC §63.6 |
| On small tasks the *language* is below parity and the *model* is not | eval-set static **0.9462** with both arms reviewed, against a model surplus over the references of **1.242–1.276** on the same 20 tasks; **89%** of the surplus is helper-function definitions, **76%** of them called exactly once — a teaching problem, not a language gap | small · static + composition-controlled surplus | `eval/references-v04/`, `v04-wave7-attribution/`, `v04-wave8-phaseb/` |
| **The static advantage inverts at scale** | 40 train refs **0.9871** (median 57 tokens) → 20 eval refs **0.9462** (73) → 20 large refs **1.0622** (292.5); the strata split bought nothing (compositional 1.0718 vs linear 1.0482); indexing `v[i]` (wave 9) takes the large tier to **1.0259** | large · static | `v04-wave8-large/`, `v04-wave9-index/` |
| **Usefulness fails first at scale** | the same tuned 7B produces *compiling* Oxide **5.5%** of the time on large tasks vs **81.5%** for the symmetrically-trained Rust arm; pass@1 **0.645 → 0.035** on one adapter across the two tiers; 0 truncated generations; the top failure is `unexpected character '['` | large · first-attempt compile rate, symmetric control | `v04-wave8-phaseb/` |
| Scale does not rescue it | 14B: **5.0% vs 76.7%**, compile-rate ratio **0.067 → 0.0652** across a doubling of model size (pre-registered ≤0.20 = language property); `[` appears in **16.8%** of 7B attempts and **29.0%** of 14B attempts, and is a lexer error | large · 3-seed screen, 8/8 seed-matched guards reproduced | `v04-wave8-14b-screen/` |
| The fine-tune, waves 0–4 | `tune-ox-7` **0.555** at 17k supervised tokens (wave 0) → **0.755** at 29.8k (wave 2), above the untuned Rust control's 0.565; corpus 7.4k → 0.420 (wave 1) shows the sensitivity; untuned Oxide beat Rust at 14B with a verifier, pass@10v **0.75 vs 0.55**; the tuned ox↔rs gap narrowed 0.225@7B → 0.175@14B where wave 0 had it widening 0.330 → 0.445 | small · pass@1, pass@10-with-verifier, 200 sessions/arm | `runpod-exp/`, `v04-campaign2/`, `v04-campaign4/` |
| The drift guard | untuned `base-rs-7` pass@1 = **0.565** in eight environments across three GPU architectures; pass@1 is invariant across architectures, secondary metrics invariant within one | small · same 20 tasks, same sampler | `v04-wave8-phaseb/` provenance |
| The instruments' own defects, caught | own-green-set means (wave 2 → SPEC §59.7); static on train refs vs dynamic on frozen eval refs (wave 6); raw-ratio bands vs surplus (wave 8A, before Phase B); seed-matched anchors, 0.745 over ten seeds reads 0.800 over three (wave 8 screen); count-verified transfer with a wrong hash; a baseline denominator summed from a report table instead of computed from the cells (wave 9 plan, caught before the run) | — | [check the estimand](docs/findings/2026-09-02-check-the-estimand-before-naming-a-finding.md) |

### The wave-9 re-screen

Wave 9 shipped indexing (`v[i]`, SPEC §65), the top-ranked gap from wave
8, and measured its static effect above. Whether the model can now
*compile* programs at scale is the pre-registered re-screen
(`docs/superpowers/plans/2026-09-02-v04-wave9-rescreen-plan.md`): same
four 14B arms, same seeds, primary endpoint the large-tier compile-rate
ratio against 0.0652, secondary the `OX0001` lexer share against **0.338**
(73 of 216 under the instrument's own lens; the plan first quoted 73 of
191, a denominator summed from a report table and corrected before the
run — see the estimand write-up, §7).

**Re-screen result (2026-09-02):** the tuned-Oxide small-tier guard
missed its seed-matched anchor by one cell (0.7833 vs 0.8000), because
`pod_setup.sh` cloned llama.cpp at HEAD and the commit had moved since
wave 8 — weights, sampler and seeds were identical. Per the plan no
ratio is published against wave 8. Within the run, Oxide compiled
**3 of 60** large-tier attempts, the same count as wave 8, while the
`OX0001` lexer share fell **0.338 → 0.019** and two byte-identical
programs that died at `[` in wave 8 compile and pass. Clearing the
lexer moved the attempts to the next fatal layers: **tuples** (types,
`for (i, x)` patterns, destructuring) and the string stdlib (`split`,
`str_from_chars`, `insert`). Under the plan's own consequence table
that is the "removing one barrier exposes the next" row. Full report:
`eval/results/v04-wave9-rescreen/REPORT.md`.

## Design principles earned

Each is a measured result in this repository, not taste. SPEC §62 states
the objectives and the four-quadrant ordering they imply.

1. **Subtractive beats additive.** The only class that beat Rust with no
   vocabulary added is the one where ceremony was deleted (structs/option
   0.92–0.93 at every size). Every added construct that landed had a Rust
   or Python namesake; every novel spelling lost.
2. **Spell it the way the model already writes it.** `|x|` over `x ->`
   by 10:1 at equal footing; `filter` over `count_if` 11–0. Novelty is a
   cost on the ease-of-learning objective, never a goal.
3. **Gate on demand × cost, and trust neither eye alone.** Demand read
   off model failures (`+=`: 64 of 64 first-attempt uses rejected before
   it existed) finds what models reach for; cost read off references
   finds what they were never taught (`swap`, `reverse`). Cost alone
   shipped `swap`, which drew zero uptake.
4. **Measure at the size you will deploy.** Every small-task claim
   inverted or collapsed at 200–600 tokens. A lexer-level gap is fatal;
   a stdlib gap is merely verbose.
5. **Documentation is not capability.** Document what the model does
   not already know; the card saturated after one revision.
6. **The verifier-in-the-loop repair step is where a notation's
   advantage shows**, not free generation — and it vanishes at frontier
   capability. State the capability window in every claim.

## The write-ups

Self-contained documents, each with its numbers, method, controls and
limits, verifiable from the committed artifacts they name:

- **[Usefulness fails first at scale](docs/findings/2026-09-02-usefulness-fails-first-at-scale.md)**
  — the static advantage inverts on 200–600 token programs, the tuned
  model compiles 5% of its attempts there against 77–82% for Rust, and
  doubling model size does not move the ratio.
- **[Familiarity is the lever](docs/findings/2026-09-02-familiarity-is-the-lever.md)**
  — uptake tracks exposure × prior familiarity, a falsified spelling
  ruling, the card saturating, and the four quadrants.
- **[Check the estimand before naming a finding](docs/findings/2026-09-02-check-the-estimand-before-naming-a-finding.md)**
  — seven instrument defects, each caught by asking whether two numbers
  were measured on the same thing; one of them cost four waves.
- **[Most of the win was ergonomics, not ownership](docs/findings/2026-08-12-ergonomics-beat-ownership.md)**
  — the +59pp repair headline decomposes to ≈+10pp ownership and up to
  +42pp surface ergonomics under a matched-novelty control.
- **[Constrained decoding deforms rather than rejects](docs/findings/2026-08-12-constrained-decoding-deforms.md)**
  — a grammar steers generation to the nearest legal string and
  manufactures programs the model did not write; corroborated by
  [robigo](https://github.com/bricelancasterwcp-sudo/robigo) and
  [assay](https://github.com/bricelancasterwcp-sudo/assay).

## What was built from it

Three things carry the lessons forward, none of them another construct:

- **[flux](https://github.com/bricelancasterwcp-sudo/flux)** — a
  pre-registered experiment on this repository's Rust arms: apply rustc's
  machine-applicable suggestions in a loop *before* a small model sees a
  diagnostic, and measure what is left of the deficit. Its $0 census over
  the committed cells already bounds the lever; the spec says so first.
- **[caliper](https://github.com/bricelancasterwcp-sudo/caliper)** — an
  inventory and extraction brief for the measurement bench under `eval/`
  (paired arms, oracle-verified references, symmetric controls,
  composition-controlled ratios, learnability, censuses, drift guards),
  so the next "how do models use notation X vs Y" question does not start
  from zero.
- A notation-design playbook, the design-side sibling of the measurement
  discipline, kept as a local skill: subtractive first, familiar spelling,
  demand × cost, measure at deployment size, documentation ≠ capability,
  and a collision check for familiar spellings with house meanings.

## The v0.2–v0.3 record

Before the design loop, the project measured **repair**: hand a model a
correct program with one seeded ownership defect and the compiler's
diagnostic, and score the fix. Implicit ownership was repaired far better
than explicit ownership by three 7–8B families, most of the effect turned
out to be surface ergonomics, and the whole effect was 0.0pp for a
frontier model. Three headline claims from that era were withdrawn when
they failed to replicate; the arithmetic that killed each is preserved.
The README as it stood at the end of that era is kept verbatim in
[docs/HISTORY.md](docs/HISTORY.md).

## Quick start

Requires Python 3.14 and a Rust toolchain. No third-party Python
dependencies.

```bash
python3 -m venv .venv && .venv/bin/pip install pytest pytest-cov
.venv/bin/pytest tests/ -q                 # 1767 tests (3 live-only, deselected by default)
```

```bash
python3 main.py program.ox                 # emit Rust to stdout
python3 main.py --check program.ox         # type/ownership check only
python3 main.py --json program.ox          # machine-readable diagnostics
python3 main.py --dialect=explicit p.ox    # the explicit-ownership control
```

Evaluation harness:

```bash
python3 -m eval.harness prompt --arm oxide --task t01
python3 -m eval.harness run --arm oxide --file solution.ox --task t01
python3 -m eval.probe --help               # the ownership probe

# static cost census over a reference set (train / eval / large)
python3 -m eval.cost_census --help
# the wave-8/9 screen: compile-rate ratio, seed-matched guards, diagnostic mix
python3 -m eval.wave8_screen --help
# the §56 deformation signature over a run root's oxide arm, per family
python3 -m eval.deformation eval/results/g0-generation-baseline/constrained
```

Live-model tests are marked and deselected by default; run them with
`-m live`. The RunPod pipeline that produced every tuned arm is under
`scripts/runpod/`, and every campaign directory carries a
`provenance.json` with the served GGUF's sha256, the llama.cpp commit,
the sampler and the seeds.

## Layout

| Path | |
|---|---|
| `SPEC.md` | the binding contract — every phase a numbered normative Part; §58–§65 are the design record of waves 1–9 |
| `src/` | lexer, parser, semantic analysis, Rust codegen, CLI |
| `src/explicit/` | the explicit-ownership control dialect |
| `eval/` | harness, task corpora, ownership probe, grammars, model clients, censuses, estimands |
| `eval/tasks.jsonl` · `eval/tasks-large.jsonl` | the 20 small (40–150 token) and 20 large (200–600 token) eval tasks |
| `eval/solutions/` | the frozen contamination reference — deliberately never modernised |
| `eval/references-v04/` | the measurement references for the eval set, both arms reviewed |
| `eval/results/` | every run, with raw model outputs verbatim and a `REPORT.md` per wave |
| `scripts/runpod/` | pod setup, LoRA training and merge, arm serving, the wave-8/9 screen drivers |
| `LANGUAGE_CARD.md` | what a model is given — compiler-validated |
| `docs/findings/` | the standalone write-ups |
| `docs/HISTORY.md` | the v0.2–v0.3 README, verbatim |
| `docs/superpowers/specs/` · `plans/` | design documents and pre-registrations, one per wave |

## Status and honest limits

Black Oxide is a research vehicle, not a usable language. It has
indexing (`v[i]`, since wave 9) but no generics, traits, closures that
capture, modules, tuples, character literals, string `split`, or sized
integer types. It is a strict subset of what it compiles to.

The design loop is closed. Nothing here says the next construct would
not help; what the record says is that each one re-derives a piece of
Rust the model already knows, and that the binding constraint at the
sizes that matter is the model's pretraining prior, not the language.

Every tuned-arm result is one model family (Qwen2.5-Coder 1.5B/7B/14B)
at q8_0, one QLoRA recipe, and corpora of 17k–30k supervised tokens per
arm. The large tier is 20 tasks authored by one person for both arms,
with the guards stated in its report. The 14B screen is three seeds.
Every `REPORT.md` under `eval/results/` states its own limits, including
which conclusions its data does *not* support.

## License

MIT — see [LICENSE](LICENSE).
