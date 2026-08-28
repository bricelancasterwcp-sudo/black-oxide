# RunPod experiment — bring-up and dry-run cost gate

2026-08-28 (UTC; evening 2026-08-27 local). Plan Task 6 record.

## Pod ledger

| pod | outcome |
|---|---|
| czts32fkq3asup | terminated ~1 min: volume mis-sized (20GB default; controller error) |
| 2obvh0l73tj07s | terminated ~3 min: no SSH key in env — account keys did not authorize direct or proxy SSH on this setup; keyed re-cut required |
| **g41ma10i0c35kv** | **pod of record** |

Pod of record: RTX 3090 24GB (4090 unavailable in community at cut
time; 24GB-class fallback ruled acceptable — wall-time only),
**$0.22/h**, community CA, 180GB volume at /workspace, image
`runpod/pytorch:1.1.0-cu1290-torch291-ubuntu2404`, driver 580.65.06,
Python 3.12.3, torch 2.9.1+cu129.

## Environment pins

- llama.cpp commit **ca3d5a3e10d53f7ea672cb9b6178faca3e2807bc**, CUDA
  build (nvcc ships off PATH in this image — `CUDACXX` fix landed in
  `pod_setup.sh`, commit 74e6b5d).
- Serving port **8090** (the image's nginx owns 8081 — serve_arm
  patched, commit 37877ca); `--jinja` per the final-review F2 ruling.
- `base-7.q8_0.gguf` sha256 `2f2b0f712f60…ffb47f9ce`.
- `/props` identity field confirmed as **`model_path`** (absolute pod
  path; `identity_preflight`'s endswith check works as written).
- rustc 1.98.0 via rustup; `~/.cargo/bin` exported in serve_arm
  (non-interactive ssh skips profiles — commit ea1b18d).

## F2 gate: train==eval rendering

`llama-server --jinja` `/apply-template` output vs HF
`apply_chat_template(add_generation_prompt=True)` on the identical
card-free `build_prompt` user string: **BYTE-EQUAL (284 chars)**. The
binding invariant holds exactly; no adjustment needed.

## Dry run (base-rs-7, 2 tasks × 2 seeds, gen family)

Wall 13.2s for 4 sessions (10 attempts total; t01 pass@1 both seeds,
t08 ran the full 4-attempt loop both seeds). Cells, provenance, and
`.DONE` all written by the driver; arm-level rerun-from-zero semantics
exercised on a live pod.

**Watch item:** t08's failing sessions are byte-identical across seeds
(444 tokens_out both) — at temp 0.2 seed replicates can collapse to
identical outputs. Task-paired endpoints remain valid regardless; the
final report must quantify replicate collapse (distinct outputs per
task) so the effective n is stated honestly.

## Cost extrapolation vs the stop rule

Measured: ~3.3 s/session mean at 7B (worst-case mix assumed 4 s).
Scaling 1.5B ≈ 0.35×, 14B ≈ 2×.

| item | estimate |
|---|---|
| generation, 12 arms × 200 sessions | ≈ 3.0 h |
| probes, 12 arms × 200 repairs | ≈ 1.5 h |
| oracle/serving overhead +30% | ≈ 1.4 h |
| trainings ×6 | ≈ 0.5 h |
| downloads + 8 conversions + smoke | ≈ 1.6 h |
| **total** | **≈ 8 GPU-h ≈ $1.76 at $0.22/h** |

Bring-up spent so far ≈ $0.3. Projection ≪ $23 even at 3× error.
**STOP RULE: GO** — the whole campaign fits the current tranche; the
16:30 top-up is likely unnecessary (report actuals at close).

> **Amended 2026-08-28 (dry run, per plan Task 6):** artifacts persist
> on the pod and results rsync home after each tranche; the S3 store
> (and its fresh key) is not used. If the pod must terminate at a
> budget pause, adapters + ggufs are preserved by rsync before teardown
> or the conversions re-run from committed inputs — both reproducible.
