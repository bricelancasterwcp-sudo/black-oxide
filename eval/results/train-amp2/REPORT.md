# train-amp2: amplification on the re-authored corpus — endpoints 3/3, band 29/30

2026-08-13. The first campaign run behind the full guard stack the pilot's
post-mortem called for: the corpus passed the pre-flight shape gate before
any GPU was spent, and the two-arm per-class difficulty band judged the
result. 3 families × 10 seeds × 40 tasks × 3 arms; 3,600 sessions,
30/30 run dirs complete at 120 cells.

## Endpoints (pre-registered in the data-factory design, as amended)

| endpoint | threshold | measured | verdict |
|---|---|---|---|
| reference-pair yield | ≥ 90% both arms passing | 40/40 (24 new pairs validated at authoring, 2026-08-12) | **PASS** |
| amplification yield | mean ≥ 4.0 unique verified oxide programs/task | **5.05** | **PASS** |
| zero-yield tasks | ≤ 30% | **10/40 = 25%** | **PASS** |
| difficulty band (two-arm, per-class — first live use) | all checks in band | **29/30** | **DRIFTED** (one cell) |

Contamination guard over every verified program including this campaign's:
**0 hits** (`tests/test_train_corpus.py` 23 green).

## What the re-authoring fixed, measured

The pilot's drift is gone. Oxide first-pass sits inside its band in
**every family at every granularity** — the classes that drifted +22.0
and +24.0pp on the pilot corpus are now at −3.0pp (qwen vectors, 0.020
vs reference 0.050) and +3.0pp (codegemma strings). Oxide overall:
qwen 24.2% (ref 30.5), codegemma 19.0% (ref 16.5), granite 11.3%
(ref 9.5) — the new corpus is difficulty-comparable to the eval on the
arm that matters most, leaning slightly *harder*, never easier.

Yield reflects the same honesty: 5.05 unique oxide programs/task
against the pilot's 6.95, with the ten zero-yield tasks concentrated
in the deliberately demanding new material (hand-rolled sorts n041/n050,
reversals n047/n053, multi-pass strings n052/n058/n060, enum iteration
n062). Harder-but-in-band is exactly what recommendation 2 asked for.

## The one failing cell, stated plainly

**granite/rust/class:vectors: 0.660 against band [0.225, 0.625]**
(reference 0.425, +23.5pp) — granite finds the new vector tasks
substantially easier *in Rust* than the eval's vector tasks. The other
two families' rust-vectors sit in band (+15.0pp qwen, +3.0pp
codegemma); every other granite check passes. The pilot could not have
seen this at all: its band covered one arm at one granularity, and this
cell needed both amendments (rust arm + per-class) to be visible.

Per the amended pre-registration, an out-of-band cell is **a
re-authoring trigger for that class, not a result to report** — the
protocol does not distinguish drifted-easy from drifted-hard, and this
report does not relitigate that. The decision on how to respond
(re-balance vector tasks' rust difficulty and re-run the affected
slice, or record a ruling that accepts the corpus with this cell
documented) is queued for the project owner. Until then, the corpus is
NOT cleared for training-data use by its own gate.

## Operations record

- qwen: 10/10 runs, 3h47m. codegemma: 10/10, 8h41m (the slow family).
  granite: 10/10, 3h13m.
- One infrastructure event, caught by the designed guard: this box's
  llama.cpp Vulkan `llama-server` **ignores SIGTERM**, so the first
  wrapper's family switch left qwen's server holding :8081; the
  driver's `--expect-model-path` stale-server guard refused codegemma
  and granite in three seconds instead of producing eight hours of
  mislabeled data. The hardened resume wrapper (SIGKILL sweep +
  wait-for-port-down + served-blob identity check before the driver
  starts) ran the remaining families cleanly. qwen's completed runs
  were unaffected (same weights, guard passed legitimately).
- Same model blobs as the pilot (digests asserted per run), llama.cpp
  Vulkan, ctx 8192/8192/4096, constrained on oxide/explicit, never
  rust, seeds 1–10, prefixes ampq/ampc/ampg.

## Provenance

Corpus: the re-authored `eval/train/tasks.jsonl` at commit `c5a3cf4`
(n001–n010, n031-kept ×6, n041–n064; shape gate PASS on all seven
axes). Band instrument: `eval/difficulty_band.py` (`2ddb5b5`).
Analysis inputs: 30 × `cells.jsonl` in this directory; endpoints
computed by `eval/train_corpus.collect_verified` and
`python -m eval.difficulty_band eval/results/train-amp2
--candidate-tasks eval/train/tasks.jsonl`.
