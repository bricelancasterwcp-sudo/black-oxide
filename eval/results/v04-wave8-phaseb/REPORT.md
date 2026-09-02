# v0.4 wave 8 (Phase B) — the model cannot write the language at scale

2026-09-01. Plan: `docs/superpowers/plans/2026-09-01-v04-wave8-phaseb-plan.md`.
Five arms, no training, no amplification. Community RTX 3090, 3h40m,
**≈$0.81** of a $2.50 stop.

## The pre-registered endpoint did not measure

| tier | model ox/rs | reference ox/rs | surplus | n_pairs | n_tasks | attempts ox/rs |
|---|---:|---:|---:|---:|---:|---:|
| eval (small) | 1.217 | 0.980 | **1.242** | 120 | 13 | 1.02 / 1.00 |
| large | 0.840 | 1.052 | *0.798* | **3** | **1** | 1.00 / 1.67 |

**The large-tier surplus rests on 3 paired green cells on a single task.**
That is below the plan's stop 3 floor of 5, so *0.798* is printed for the
record and **is not an endpoint**. The threshold was fixed before the run
and has not been moved to accommodate the number.

**The small tier did measure, and it reproduces the project's prior
result inside this environment: surplus 1.242** against wave 6's 1.276,
on 120 pairs across 13 tasks. Repair attempts are 1.02 vs 1.00, so that
surplus is about expression, not about one arm needing more repair —
which is why that column exists.

## Why it did not measure

| tier | arm | compiles | pass@1 | pass@10v | green tasks |
|---|---|---:|---:|---:|---:|
| small | base-rs-7 | 99.5% | 0.565 | 0.600 | 12 |
| small | tune-ox-7 | 70.5% | 0.645 | 0.750 | 15 |
| small | tune-rs-7 | 95.0% | 0.870 | 0.900 | 18 |
| large | **tune-ox-7** | **5.5%** | **0.035** | 0.200 | 4 |
| large | tune-rs-7 | 81.5% | 0.200 | 0.450 | 9 |

**The tuned 7B produces compiling Oxide 5.5% of the time on 200–600 token
tasks, against 81.5% for Rust.** Not correct — *compiling*. Pass@1 falls
0.645 → 0.035, an 18× drop, where the Rust arm falls 0.870 → 0.200, a
4.4× drop.

Three alternative explanations were checked and none survives:

- **Truncation:** 0 truncated generations in either arm on either tier.
  Median output 1165 tokens against a 2048 cap.
- **A broken adapter or merge:** `tune-ox-7` reads **0.645** pass@1 on the
  small tier — wave 4's published figure for this adapter on this task
  set, to the digit. The weights are healthy.
- **Distribution shift:** the pre-registered confound. Both arms were
  trained identically on small-task corpora and are equally
  out-of-distribution. It does not explain a 15× gap in compile rate.
  **This is exactly what the symmetric control was for.**

## The mechanism, read off the model's own output

Every failing attempt's first diagnostic, tallied:

| tier | lexer (OX0001) | unknown identifier (OX0200) | parse (OX01xx) |
|---|---:|---:|---:|
| small | 5.1% | 24.8% | 42.7% |
| large | **27.6%** | **28.5%** | 30.0% |

The large tier's top two messages are **`unexpected character '['`
(126)** and **`unexpected character "'"` (56)**.

**Oxide has no indexing syntax and no character literals, and at this
program size the model cannot avoid reaching for them.**

| | small | large |
|---|---:|---:|
| first attempts containing `[` | 0.5% | **17.0%** |
| attempts containing a char literal | 2.0% | 7.7% |

A **34× increase** in reaching for a construct the lexer cannot even
tokenise. Short programs iterate (`for x in v`); long ones index. The
small tiers structurally could not see this, in the same way they could
not see the no-capture cost Phase A found.

And the identifiers the model asks for, ranked:

| small tier | large tier |
|---|---|
| divide 25, div 13, join 6, map 4, argmax 4 | **split 44, slice 39, map 32, floor 27**, div 13, reverse_str 9, insert 7, join 6 |

## The two phases converge on one list

Phase A recorded what *I* hit authoring 20 large programs by hand. Phase B
recorded what the *model* hit writing 776 attempts at the same tasks. They
are the same list, discovered independently:

| Phase A (my authoring) | Phase B (model failures) |
|---|---|
| indexing is `unwrap_or(get(v, i), 0)` vs `v[i]` | `unexpected character '['` — 126, the top failure |
| no string `split` (g10 hand-rolls 12 lines) | `unknown identifier 'split'` — 44 |
| no `map` / `max_by_key` | `unknown identifier 'map'` — 32 |
| no string `reverse` (g02 hand-rolls `rev_str`) | `unknown identifier 'reverse_str'` — 9 |
| predicates cannot capture a computed threshold | `|x| x > floor(avg(v))` — OX0205 |

Two independent instruments, one design agenda. That convergence is the
most useful thing this wave produced.

## What this does to the project's framing

Phase A: at scale the **language** needs ~6% more tokens than Rust
(0.9462 → 1.0622).
Phase B: at scale the **model** can barely write the language at all.

**The efficiency gap is the smaller problem.** "How many tokens does a
correct Oxide program cost" cannot be asked at a size where correct Oxide
programs are 4.5% of attempts. Objective 2 (efficiency) is downstream of
objective 1 (usefulness), and objective 1 fails first at scale.

It also sharpens objective 3, ease of learning. The fine-tune taught the
model Oxide well enough for 40–150 token programs and **not at all** for
200–600 token ones. That learning does not generalise along the size
axis, and no previous wave could have discovered it, because every
previous wave measured only the size where it holds.

## Provenance

- Drift guard `base-rs-7` **reproduced exactly**: pass@1 0.565, pass@10v
  0.600, tokens-to-green 66.8, censored 87, n=200 — an eighth
  environment, every companion figure to the digit. Also reconfirms the
  documented architecture split (wave 2 on a 4090 read 0.650/65.7; every
  3090 reads 0.600/66.8).
- Base GGUF sha256 `2f2b0f71…` is **byte-identical** to the artifact
  preserved from earlier waves: the download → convert → quantise
  pipeline is deterministic across pods.
- `eval/tasks.jsonl` unchanged since 2026-08-12, so the small-tier arms
  ran the same 20 tasks as every prior wave.
- **Arm names are reused across waves while weights differ by adapter
  version.** This wave's `tune-ox-7` is the **v5** adapter merged
  (`bac79623…`), not wave 0's `tune-ox-7.q8_0.gguf` (`ddeaaca3…`).
  `provenance.json` records the served sha256 in every arm directory.
- Contamination zero in both directions, including against the training
  corpus the v5 adapters saw.

## Feed-forward

1. **Indexing syntax is now the top-ranked item on the design agenda**,
   evidenced from two directions. It is not a stdlib gap — it is a lexer
   gap, and it is fatal rather than merely verbose.
2. **`split`, `slice`, `map`, `floor`** are the stdlib the model asks for
   by name, ranked by its own demand at the size where it matters.
3. **Re-run this tier after those land.** The large tier is now a
   permanent instrument: it is where the language's problems become
   visible, and small-task measurement demonstrably cannot substitute.
4. **Do not quote the large-tier surplus.** 3 pairs on one task.
5. **A 14B arm on the large tier is the obvious next question** — wave 4
   found untuned Oxide beats Rust at 14B with a verifier on small tasks.
   Whether the cliff is a 7B property or a language property is
   unanswered and cheap to answer.
6. The small-tier surplus reproducing at 1.242 (wave 6: 1.276) inside a
   fresh environment is a quiet win for the estimand's stability.
