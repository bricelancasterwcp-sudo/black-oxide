# Wave 9 — re-screen: shipping `[` cleared the lexer and moved nothing

2026-09-02. Plan: `docs/superpowers/plans/2026-09-02-v04-wave9-rescreen-plan.md`
(pre-registered, with two dated amendments before the run). Four arms,
seeds 1–3, no training, weights byte-identical to wave 8's by sha256.
Community RTX 3090 `dv2nyotmwhyksp`, 11:24 → 13:05 UTC, **≈$0.37** of a
$1.00 stop. Reader: `python -m eval.wave9_rescreen` → `rescreen.json`,
`SCREEN.md`.

## Stop 1 fired, and the cause is identified

| guard | anchor (wave 4, seeds 1–3) | wave 8 | **wave 9** |
|---|---:|---:|---:|
| `base-rs-14` @ small, pass@1 | 0.5500 | 0.5500 | **0.5500** |
| `tune-ox-14` @ small, pass@1 | 0.8000 | 0.8000 | **0.7833** (47/60) |

The tuned-Oxide guard missed by one cell. Per the plan, **no ratio from
this run is published as movement against wave 8.** The reader prints
`GUARDS-MISSED` and `delta: None`; the numbers below are for the record
and for the one comparison that does not depend on the environment.

**Cause, read off the cells.** The missed cell is seed 3, task `t20`.
Its first-attempt program is a *different sample* from wave 8's — the
same `vec(...)` laid out across different lines, then a divergent body.
Weights are hash-identical (`base d5473be2…`, `ox fb7c0bde…`,
`rs 88ca8607…`, all three equal to wave 8's), the sampler and seed are
pinned, and the prompt is the same. What moved is **llama.cpp**:
`pod_setup.sh` cloned HEAD, which went from `b96806d` (wave 8) to
`0f3a71b` (wave 9). Across the four arms, 6 / 1 / 25 / 16 of 60
first-attempt texts differ from wave 8's on the same seed. The base
guard survived its six because none changed a verdict; the tuned guard
lost one of one.

So the guard did its job — it caught an environment that was not the
same environment — and the thing it caught was an **unpinned ambient
variable** in the pipeline, not the merge and not the language.
`pod_setup.sh` now pins the commit (default `b96806d`, overridable), and
`llamacpp_commit` was already in every `provenance.json`, which is how
this was diagnosed in minutes rather than re-run.

The project's standing claim was "pass@1 is invariant across GPU
architectures". It still is, at a fixed llama.cpp. It is **not**
invariant across llama.cpp commits, by one cell in sixty on one arm; the
claim is narrowed accordingly.

## What the run measured (within one environment)

| large tier | compiled | n | rate |
|---|---:|---:|---:|
| `tune-ox-14` | **3** | 60 | 0.050 |
| `tune-rs-14` | 43 | 60 | 0.717 |

Within-run compile-rate ratio **0.0698**. Wave 8 read 0.0652 in its own
environment; the plan's bands put anything below 0.12 at
*next-barrier*, and this reading lands there **for the record only** —
stop 1 bars quoting it as a change from wave 8. Oxide compiled exactly
**3 of 60 in both waves.**

**The comparison that survives the guard.** Two cells have
byte-identical first-attempt programs in wave 8 and wave 9 — `g17` on
seeds 2 and 3, both containing `[`. In wave 8 each died at the lexer
(`OX0001 unexpected character '['`, 31 diagnostics each). In wave 9
each **compiles and passes**. Same text, same weights, same seed; only
the language changed. That is the construct working exactly as SPEC §65
specified, on the model's own output, without any cross-environment
inference.

## The mechanism check, and it is unambiguous

| first diagnostic of a failing attempt | wave 8 | **wave 9** |
|---|---:|---:|
| `OX0001` lexer | 73 of 216 = **0.338** | **4 of 213 = 0.019** |

`[` was the lexer barrier: with it legal, the lexer share fell below the
pre-registered 15% by a factor of eight. Attempts containing `[` were
**58 of 229 (25.3%)**, and 54 of those got past the lexer for the first
time. The wave-8 attribution was right.

Where they went instead — the next barriers, named from the model's
own output:

| first diagnostic | count | what it is |
|---|---:|---|
| `OX0200` unknown identifier | 54 | `str_from_chars` 8, `insert` 8, `split` 7, `str_split` 7, `slice` 5, `all` 4, `is_alpha` 4 — **strings, again** |
| `OX0103` expected type, found `(` | 32 | **tuple types** |
| `OX0100` expected expression, found `=` / `OX0101` … found `EQ` | 31 | index-assign `v[i] = x` and tuple destructuring |
| `OX0101` expected loop variable, found `(` | 21 | **tuple patterns**: `for (i, x) in …` — the enumerate idiom |
| `OX0101` other parse | 44 | mixed |

Two of the five are one gap: **tuples** (types, patterns, destructuring)
account for at least 53 first diagnostics. The other is the string
stdlib the census has ranked since wave 8. Clearing the lexer moved the
model from a fatal layer to two more fatal-at-this-size layers, and the
compile count stayed at 3.

## Reading

The plan pre-stated that clearing the lexer would move an attempt to its
*next* error and that a rise into 10–20% was the honest expectation. The
measured result is below even that: **no rise at all.** Under the plan's
own consequence table this is the `< 0.12` row — *one construct at a
time does not work; ship the ranked slate together, or accept that the
gap is not closable by vocabulary.*

Combined with the owner's decision of the same day to close the design
loop, the reading is the second: the record now shows that removing the
single largest, lexer-level, measured-by-demand gap left the compile rate
at scale exactly where it was, and named two further fatal layers behind
it, each of which re-derives a piece of Rust the model already knows.

## What is NOT claimed

- Any change in the compile-rate ratio from wave 8 (stop 1).
- Anything about pass@1 at the large tier from three seeds.
- That tuples or `split` would, if shipped, move the compile rate — the
  same reasoning predicted `[` would, and the mechanism was right while
  the total did not move.

## Provenance

- 4 arms × 20 tasks × seeds {1,2,3}; `.DONE` on all four; **876 result
  files transferred and verified by content hash** against a manifest
  computed on the pod (the wave-8 lesson, applied).
- Adapters `tune-{ox,rs}-14-v5` content-hash verified against
  `SHAS.txt` before launch; both `OK`.
- GGUF sha256: base `d5473be2…`, ox `fb7c0bde…`, rs `88ca8607…` — each
  identical to the wave-8 screen's artifact of the same name
  (`pod-gguf-shas.txt`).
- llama.cpp `0f3a71be…` (wave 8: `b96806d9…`); rustc 1.98.0
  (2026-08-18); harness at `521f602f` (the branch head the pod was told
  to expect, checked before any arm ran).
- The lexer-share baseline was corrected from 73/191 to 73/216 in the
  plan's 11:55 UTC amendment, before the pod produced a cell; the reader
  pins both baselines to the committed wave-8 cells by test.
- Pod terminated, zero pods verified twice.
- **Cost:** this run ≈$0.37. Separately, the pod provisioned with the
  plan by the previous session (`bf1mt4qibzo9tw`) idled 9.1 h with
  nothing on it (≈$2.00) and its GPU then failed `cuInit` with 999; both
  are recorded in the plan's 11:30 UTC amendment. Program ≈**$19.3 of
  $23**, computed (the billing endpoint returns nothing).

## Instrument changes shipped with this report

1. `scripts/runpod/pod_setup.sh` pins the llama.cpp commit.
2. `eval/wave9_rescreen.py` — the pre-registered reading, with the
   wave-8 band verdict renamed so it cannot be mistaken for this run's,
   and `delta: None` on a missed guard (9 mutations killed).
3. `LEXER_SHARE_BASELINE` corrected and pinned to the record.
4. `scripts/runpod/wave9_rescreen.sh` — `cuInit` before anything else,
   `DONE`/`FAILED` markers, expected-commit check.

## Feed-forward, recorded for whoever reopens the loop

1. Re-run the two guards at the pinned llama.cpp before reading any
   cross-wave number again; the anchors may need re-basing to the pinned
   commit.
2. Tuples are the next lexer/parser-level gap (types, `for (i, x)`,
   destructuring), then the string stdlib (`split`, `str_from_chars`,
   `insert`), then index-assign. The plan's own consequence says they
   would have to ship together.
3. Record the rustc version in `provenance.json`; it is only in the
   setup log today.
