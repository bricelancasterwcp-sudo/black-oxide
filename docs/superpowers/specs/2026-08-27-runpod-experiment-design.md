# The fine-tune experiment — token-matched Black Oxide vs Rust on RunPod

**Date:** 2026-08-27
**Track:** fine-tune (SPEC §32.4 item 4), **final sub-project** — the
experiment itself, with training infrastructure folded in per the
2026-08-27 "approach B" ruling (the infrastructure is a runbook
adaptation, not a design problem).
**Status:** design approved in session (sections approved in chat,
2026-08-27); this document is the written record for review.
**Inherits:** the token-matching spec
(`2026-08-27-token-matching-design.md`) and its committed corpus at
`eval/train/matched/` (merged to main 4629ce8: 17,225 / 17,119
supervised tokens, 40 references per arm, contamination 0). Binding
invariants inherited: epoch parity (identical hyperparameters and epoch
counts in both arms), card-free symmetric training examples, the
pinned tokenizer (sha `c0382117…`), and the interpretation limit — a
null at this corpus scale kills "language + *small* fine-tune", not the
thesis.

Session rulings incorporated: subjects 1.5B/7B/14B (14B added to probe
the capability window's upper edge); ALL measurement on RunPod in one
pinned environment; token efficiency pre-registered; budget $23 now
plus a top-up at 16:30 on 2026-08-28; pilot-scale corpus as-is.

## What this experiment answers

Whether the repair-and-generation advantage of a purpose-built language
survives when pretraining exposure is equalised by a token-matched
fine-tune — the open question the ergonomics write-up names — and, via
the added 14B row, whether fine-tuning extends the capability window
upward. It is also the pre-registered gate for the general-purpose
LLM-language idea (decision mapping below).

## The matrix

Subjects: **Qwen2.5-Coder-Instruct 1.5B / 7B / 14B** (instruct rather
than base: every measured baseline in this project was served in
instruct shape; the harness's prompt format is checked against the
checkpoint's chat template at implementation time and recorded).

Six trainings: per size, one LoRA on the matched oxide arm and one on
the matched rust arm.

Twelve eval arms, all measured identically on the held-out t01–t20:

| arm | model | language | card |
|---|---|---|---|
| base-ox-{1.5,7,14} | untuned | Black Oxide | yes (frozen card) |
| base-rs-{1.5,7,14} | untuned | Rust | no |
| tune-ox-{1.5,7,14} | oxide-tuned | Black Oxide | **no** |
| tune-rs-{1.5,7,14} | rust-tuned | Rust | no |

Tuned arms are card-free by design: the fine-tune's job is to move the
language from a 900-word prompt tax into the weights. The untuned
oxide baseline keeps the card because that is its measured condition.

## Training protocol

- **QLoRA, identical in every run** (epoch parity): 4-bit NF4 base,
  LoRA r=16 / alpha=32 on attention+MLP projections, lr 1e-4 cosine,
  3 epochs, max sequence 1024, same seed, loss masked to the
  completion (the matched supervised tokens). These are conventional
  values chosen once for ALL six runs before any result is seen; the
  design's control is the *between-arm identity* of the recipe, not
  the recipe itself. Recorded as chosen, not derived.
- **Training example** = the matched corpus record rendered as the
  checkpoint's chat template with the task prompt as the user turn and
  the program as the assistant turn — the same rendering the eval
  harness uses, so train and eval agree on format.
- **Tokenizer attestation extension (preflight gate, fail-closed):**
  the token-matching pin was attested from the BASE repos. Before any
  training, fetch the three **-Instruct** repos' `tokenizer.json` and
  assert they hash to the same pinned `c0382117…`. A mismatch stops
  the experiment — the matching was computed under that tokenizer —
  and escalates to the owner rather than being worked around.
- **Artifact pipeline:** adapter → merge into bf16 base → GGUF
  convert → **q8_0** quantize (the serving condition inherited from
  the data-factory spec) → sha256 recorded → S3 (fresh key, not the
  bloomery key pending rotation). Every eval serves a q8_0 GGUF
  through llama.cpp; nothing is ever evaluated through the training
  stack.

## Serving and environment

- One pod class for the whole campaign: 4090-class 24GB CUDA (fits
  14B q8_0 with headroom). Pod image, llama.cpp commit, GGUF sha,
  and sampler are recorded in every run's provenance.
- **Sampler pinned: temperature 0.2**, 10 fixed seeds (1–10) — the
  house standard the committed campaigns used.
- **Identity guards** (the oxide-amp2 lessons, verbatim): the wrapper
  asserts the served model path/sha equals the intended one before any
  session is scored; teardown is SIGKILL + wait-for-port-DOWN before
  the next model starts; runs are OS-detached (`setsid nohup`) with
  pid files and `.DONE` markers, and a watcher distinguishes silence
  from success.
- All committed local campaigns (v03c, g0c, g1c, amp2) are historical
  context. Every comparison in this experiment is within-environment.

## Evaluation protocol

All decoding is **unconstrained**, validated after the fact by the
compiler/verifier so failure is loud — per this project's own
constrained-decoding-deforms finding. No grammar touches the payload.

**Generation** (per arm: 20 tasks × 10 seeds = 200 sessions):

- `pass@1`: fraction of the 200 attempts that transpile/compile and
  match expected stdout (`--check` verifier). Attempt-level, the
  primary resolution (2 SE ≈ 7pp at mid rates).
- `pass@10-with-verifier`: fraction of the 20 tasks where ≥1 of the
  10 seeded attempts passes the verifier. Task-level, honest width
  reported (n=20 is coarse; 2 SE up to ≈ 22pp) — descriptive, never
  primary.
- `tokens-to-green` (generation): per task, attempts in seed order;
  the sum of completion tokens up to and including the first passing
  attempt. Tasks that never pass are **censored, named, and excluded
  from the mean** — a censored task is not a number (None-vs-zero).
  Prompt tokens reported separately.

**Repair** (per arm: the 20 seeded-defect classes × 10 seeds = 200
sessions, the committed studies' machinery):

- `strict repair rate`: single-proposal repair given program +
  diagnostic, verifier-judged — directly comparable in *form* to the
  published +59pp/+35pp/+9.5pp rows.
- `iterations-to-green`: a NEW loop driver — up to **K=4** rounds,
  each feeding back the current compiler diagnostic; metric is rounds
  until green, censored at 4 and named. K=4 is chosen (one initial
  attempt + three corrections), recorded as chosen.
- `tokens-to-green` (repair): completion tokens summed across loop
  rounds to green, censored as above.

Tuned arms get card-free prompts in both families; the untuned oxide
arm keeps its card. Everything else about the prompt rendering is
identical across arms.

## Endpoints and decision rules (pre-registered)

The write-up may report anything; only what is listed here may be
*claimed*. "Wins" always means the 2-SE interval excludes zero in the
stated direction, on the pre-registered comparison, computed once.

1. **Primary, per size s:** paired per-task delta
   `Δ_s = pass@1(tune-ox_s) − pass@1(tune-rs_s)`, 2-SE via the
   paired machinery the ownership studies used (n=200 per side).
   Same construction for strict repair rate as co-primary — the two
   families answer different halves of the question (authorship vs
   the loop) and are reported side by side, never pooled.
2. **Headline:** `pass@1(tune-ox-7) vs pass@1(base-rs-14)` — small
   model + purpose-built language against raw scale on the prior's
   home language. Unpaired Welch-style 2-SE. Same comparison on
   strict repair.
3. **Capability window:** the trend of Δ_s across 1.5B → 7B → 14B,
   both families. Monotone shrinking toward 14B = the window closing
   from above (frontier-0.0pp shape); growing = fine-tuning extends
   the window. Descriptive trend over three points — stated as such,
   no trend test.
4. **Token efficiency:** ratio of mean tokens-to-green,
   tune-ox vs tune-rs per size, both families, censoring counts
   alongside. Descriptive. Joins the static estimand already in the
   matched-corpus manifest.
5. **Sanity bounds, chosen and flagged as such** (infra tripwires,
   not endpoints): base-rs-7 pass@1 in [0.30, 0.80]; base-ox-7
   (card) pass@1 in [0.05, 0.60]; every session's server identity
   check green. A breach halts the campaign for infrastructure
   diagnosis before any further arm runs — it is never a result.

**No extension, no re-run, no corpus change after a number is read.**
An infrastructure kill (identity mismatch, missing stats, pod death)
voids the affected arm with nothing read, and that arm reruns from
zero; a completed arm is never re-rolled. No partial-arm data is ever
spliced.

## Budget and phasing

- **Stop rule:** $23 now; top-up at 16:30 2026-08-28. Spend is
  extrapolated from a dry run (below) before the campaign commits;
  if projected spend exceeds available budget, the campaign waits at
  a whole-arm boundary rather than trimming n.
- **Order:** pod bring-up + preflights → dry run (1 task × 2 seeds
  through one baseline arm end-to-end, cost extrapolated ×
  arms/tasks/seeds) → 6 trainings → 12 eval arms, baselines first,
  smallest models first. Only **whole arms** complete per tranche.
- **The tranche boundary is an infrastructure pause, not an interim
  analysis.** No endpoint is computed until all twelve arms are done.
  Raw run dirs accumulate; the analysis script runs once, at the end.

## Decision mapping (written before any number exists)

- **Tuned-oxide wins on generation** (primary 1, any size, and the
  headline direction holds): the general-purpose-language idea earns
  its next gate — corpus scale-up as its own brainstorm→spec cycle.
- **Wins on repair only:** the language-for-repair niche stands;
  GP ambition stays parked; findings published as the repair-niche
  result.
- **Null or rust-tuned wins:** the pretraining prior holds under
  matched small-scale fine-tuning; the GP idea is parked, and the
  null is published with the same care as a win (the robigo
  precedent).

Whatever the outcome, the result is written up as a findings doc in
this repo's series, with the withdrawn-claims discipline in force.

## New components this spec creates

| component | what |
|---|---|
| `eval/repair_loop.py` | K-round repair loop driver (K=4), censoring semantics as above |
| `eval/tokens_to_green.py` (or folded into rollup) | tokens-to-green computation over run dirs, censoring named |
| `scripts/runpod/` runbook | pod bring-up, preflight (VRAM floor, identity, digests), wrapper with pid/.DONE/watcher, teardown |
| training script | one QLoRA recipe, parameterized only by (size, arm); emits adapter + provenance |
| analysis script | computes ONLY the pre-registered endpoints from completed run dirs; refuses to run unless all 12 arms have `.DONE` |
| instruct-tokenizer attestation | extends `eval/tokenizer_pin.py` provenance with the three -Instruct repos, asserting the same hash |

Every new instrument follows the house test discipline (mutation-tested
tests, real-data acceptance pins where committed data exists).

## Honest limits

- Pilot-scale corpus: ~17k supervised tokens per arm. The
  interpretation limit is inherited and binding — a null kills
  "language + small fine-tune" only.
- One eval corpus (t01–t20), single-author; one defect distribution;
  one environment, one pod class, one quantization (q8_0).
- Task-level pass@10 on 20 tasks is coarse and is never a primary.
- The QLoRA recipe and K=4 are chosen values, recorded as such; the
  design controls arm identity, not recipe optimality.
- Instruct checkpoints assumed tokenizer-identical to base — asserted
  by a fail-closed preflight, not assumed silently.
- The strings class is thin in the training corpus (both arms, by
  matching); per-class eval reads on strings are low-precision.

## Out of scope

Corpus scale-up; repair-format training data; constrained-decoding
arms; any non-Qwen subject; serving quantizations other than q8_0;
the robigo 14B benchmark run (separate instrument); VTT wiring.
