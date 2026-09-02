# Wave 8 — 14B screen: the cliff is a property of the language

2026-09-02. Plan:
`docs/superpowers/plans/2026-09-01-v04-wave8-14b-screen-plan.md`.
Four arms, 3 seeds, no training. Community RTX 3090, ~1.25 h,
**≈$0.28** of a $1.50 stop.

## Verdict

| | 7B | 14B |
|---|---:|---:|
| `tune-ox` large-tier compile rate | 5.5% | **5.0%** |
| `tune-rs` large-tier compile rate | 81.5% | **76.7%** |
| **compile-rate ratio ox/rs** | **0.067** | **0.0652** |

**Pre-registered band ≤0.20 = language property. The ratio moved by
0.002 across a doubling of model size.**

Scale does not rescue it. This is not a 7B limitation.

## The guards make it credible

Both reproduced their seed-matched anchors **on every metric**, not just
the gating one:

| arm | metric | anchor (wave 4, seeds 1–3) | measured |
|---|---|---:|---:|
| `base-rs-14` | pass@1 | 0.550 | **0.550** |
| | pass@10v | 0.550 | **0.550** |
| | tokens-to-green | 75.4 | **75.4** |
| | censored | 27 | **27** |
| `tune-ox-14` | pass@1 | 0.800 | **0.800** |
| | pass@10v | 0.900 | **0.900** |
| | tokens-to-green | 97.3 | **97.3** |
| | censored | 7 | **7** |

Eight of eight, exactly. The environment is comparable and the 14B
adapters and merges are healthy.

**The anchors had to be seed-matched or this would have misread.**
`tune-ox-14`'s *published* figure is pass@1 0.745 over ten seeds; over
seeds 1–3 it is 0.800. Screening a healthy adapter against the published
number would have shown a 5.5-point "anomaly" that was pure sampling.

**A methodological side result:** this run converted straight to q8_0
(to bound disk) rather than via bf16, so the base GGUF is `d5473be2…`
against the artifact's `662ea1eb…`. **Different bytes, byte-identical
behaviour** across all four guard metrics. The conversion paths are
behaviourally equivalent; the hash difference is a pipeline artifact.

## The mechanism, and it is not subtle

| large tier | attempts containing `[` | compile rate |
|---|---:|---:|
| `tune-rs-14` | **75.5%** | 76.7% |
| `tune-ox-14` | 29.0% | 5.0% |

**Three quarters of the Rust arm's attempts index.** At 200–600 tokens
indexing is not an occasional convenience — it is the dominant idiom for
this kind of work. Oxide has no syntax for it, and `[` is a lexer error.

The Oxide arm's failures are dominated by `OX0001` (lexer, 73) and
`OX0101` (parse, 51). The Rust arm's are ordinary type errors (`E0308`,
20). One arm is getting programs slightly wrong; the other cannot state
them at all.

**And scale makes the pressure worse, not better.** The `[` rate in
Oxide attempts rose 16.8% (7B) → **29.0%** (14B). A more capable model
writes more sophisticated code, and sophisticated code indexes. *Being
better at programming makes a model worse at this language.*

## The cliff, stated cleanly

`tune-ox-14` writes compiling Oxide **83.3%** of the time on 40–150
token tasks and **5.0%** of the time on 200–600 token tasks — a 16.7×
collapse in the same model, same session, same weights, zero truncated
generations. Its first-attempt pass rate on the large tier is **0.000**.

## What this settles

1. **The design agenda outranks everything else queued.** Indexing
   syntax is first, and it is a lexer-level gap, not a stdlib one. Then
   the stdlib the model asks for by name: `split`, `slice`, `map`,
   `floor`.
2. **Scale is no longer a lever for this problem.** Wave 4 found scale
   rescuing Oxide on small tasks (untuned Oxide beat Rust at 14B with a
   verifier). It does not rescue this, and the reason is that no amount
   of capability substitutes for syntax the language does not have.
3. **Efficiency work is premature.** Phase A measured the language at
   ~6% more tokens than Rust at scale. That is the smaller problem, and
   optimising it while the model cannot produce compiling programs would
   be building on sand.
4. **The large tier is now the project's primary instrument.** Every
   finding here was invisible at 40–150 tokens, and three waves of
   small-task measurement could not have surfaced any of it.

## Provenance

- 4 arms × 20 tasks × seeds {1,2,3} = 60 cells per arm, `.DONE` on all
  four, 884 files transferred and count-verified.
- `seeds_subset: [1,2,3]` recorded in every `provenance.json`, so no
  reader can mistake this for a ten-seed run.
- GGUF sha256 per arm: base `d5473be2…`, ox `fb7c0bde…`, rs `88ca8607…`
  — all three distinct, so both merges demonstrably applied.
- Adapters content-hash verified against `SHAS.txt` **after** a
  truncated transfer passed the file-count check (`tune-rs-14-v5` read
  `1bf2b8b7…` against the expected `57b32260…`). Had that gone
  unnoticed, the control arm would have run on corrupt weights and the
  ratio would have been meaningless while looking plausible.
- Pod terminated, zero pods verified twice.
