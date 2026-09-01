# Wave 8 — 14B screen: is the cliff a 7B property or a language property?

**Date:** 2026-09-01. Branch `v04-wave8-phaseb`.
**Written and committed BEFORE the pod is provisioned.**
Phase B report: `eval/results/v04-wave8-phaseb/REPORT.md`.

## The question

Phase B measured a capability cliff: `tune-ox-7` produces **compiling**
Oxide 5.5% of the time on 200–600 token tasks against **81.5%** for the
symmetrically-trained Rust arm — a compile-rate ratio of **0.067**.

Wave 4 found the opposite direction at 14B on *small* tasks: untuned
Oxide beat Rust with a verifier (pass@10v 0.75 vs 0.55), and tuned Oxide
scaled 0.645 → 0.745 while the ox/rs gap narrowed. **So scale has
previously rescued Oxide, and nobody has asked whether it rescues this.**

This is a **screen**, not a full protocol: 3 seeds, 4 arms. The cliff is
defined by a compile rate of 5.5% against 81.5%; 3 seeds × 20 tasks = 60
attempts per arm separates those with enormous margin. Escalate to the
full ten-seed protocol only if the result lands in the ambiguity band.

## Pre-registered endpoint

**Primary: the large-tier compile-rate ratio, oxide ÷ rust.** A ratio
rather than an absolute, so a 14B that is simply better at everything
does not read as a rescue. At 7B it is **0.067**.

| ratio | reading | consequence |
|---|---|---|
| **≥ 0.50** | the cliff is a **7B property** | scale rescues it; the language gaps are survivable and efficiency returns to being the subject |
| **≤ 0.20** | the cliff is a **language property** | indexing and the missing stdlib are fatal regardless of model size, and become THE priority over everything else queued |
| 0.20 – 0.50 | ambiguous | **escalate to ten seeds before concluding anything** |

Secondary, reported but not gating: absolute compile rates, pass@1,
green counts, and the diagnostic-code distribution (does `unexpected
character '['` still dominate at 14B?).

## Arms

Four, each load-bearing. All at **seeds 1,2,3**.

| # | arm | task set | why |
|---|---|---|---|
| 1 | `base-rs-14` | eval (small) | drift guard |
| 2 | `tune-ox-14` | eval (small) | adapter/merge health |
| 3 | `tune-ox-14` | large | the measurement |
| 4 | `tune-rs-14` | large | the control |

Adapters `adapters-v5/tune-{ox,rs}-14-v5`, both present and sha256-
verified against `SHAS.txt`. No training.

## The anchors are seed-matched, and this is not a detail

A three-seed run **cannot** reproduce a published ten-seed figure, and
comparing them would be the wave-6 estimand defect again. The anchors
below are wave 4's own committed cells restricted to seeds 1–3:

| arm | published (10 seeds) | **anchor (seeds 1–3)** |
|---|---:|---:|
| `base-rs-14` | 0.7450 → n/a; pass@1 0.5500 | **0.5500** (33/60) |
| `tune-ox-14` | pass@1 0.7450 | **0.8000** (48/60) |

**`tune-ox-14` reads 0.745 over ten seeds and 0.800 over seeds 1–3.**
Screening against the published 0.745 would have shown 0.80 and invited
reading a sampling artifact as a finding. `base-rs-7`'s famous 0.565
likewise becomes 0.5500 on seeds 1–3.

`--seeds` is shipped as tested code (4 mutations killed) and records
`seeds_subset` in `provenance.json`, so no later reader can mistake a
subset run for a full one.

## Pre-registered stops

1. **`base-rs-14` @ small ≠ 0.5500 on seeds 1–3** → environment not
   comparable; report the drift, publish no ratio against prior waves.
2. **`tune-ox-14` @ small materially below 0.8000** → the merge or
   adapter is suspect, not the language. Stop and diagnose. (This is the
   check that saved Phase B: `tune-ox-7` reading exactly 0.645 is what
   made the large-tier collapse credible.)
3. **Spend reaches $1.50** → stop and report what completed.
4. **`torch.cuda` unavailable or wrong GPU** → terminate before hours.

## Cost

Estimated **≈$0.50** at $0.22/h community 3090 (~2.25 h: 36 min setup,
34 min weights, 65 min arms). Priced from Phase B's measured timings
scaled 2× for the model size. Balance ≈$6.4.

## Two configuration traps that would waste the run

- **Disk: request ≥150 GB.** Phase B's 80 GB volume will not fit 14B.
  With the bf16 intermediate the peak is ~120 GB; the run would die
  mid-merge after paying for the download. Storage cost is negligible.
- **RAM: request ≥100 GB.** `merge_lora` merges on CPU; 14B bf16 is
  ~29.5 GB and the merge peak is ~60 GB. Phase B's pod had 62 GB, which
  is too tight to rely on.

Both are configuration, not budget.

## Carried ops rules

Community 3090 with a single `gpuTypeIds` pin and `PUBLIC_KEY` in env;
verify `torch.cuda` before committing hours; liveness = SSH, never the
`runtime` field; count-verify transfers by FILE COUNT; terminate then
verify zero pods twice. `pod_setup.sh` now installs the conversion
requirements and drops `torchvision` — Phase B lost ~20 minutes to that.
