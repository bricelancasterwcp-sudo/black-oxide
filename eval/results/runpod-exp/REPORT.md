# RunPod fine-tune experiment — 12 arms, pre-registered endpoints

2026-08-28. Spec: `docs/superpowers/specs/2026-08-27-runpod-experiment-design.md`
(as amended). Endpoints computed ONCE by `python -m eval.experiment_report`
after all 12 arms carried `.DONE`; every number below traces to
`ENDPOINTS.json` in this directory.

## Environment

Pod g41ma10i0c35kv: RTX 3090 24GB (community, $0.22/h), image
runpod/pytorch:1.1.0-cu1290-torch291-ubuntu2404, driver 580.65.06;
llama.cpp ca3d5a3e (CUDA), served q8_0 via `/v1/chat/completions` with
`--jinja` (train==eval rendering verified BYTE-EQUAL pre-campaign);
sampler temp 0.2 / top_p 0.95, seeds 1–10, num_ctx 8192, num_predict
2048, unconstrained (grammar=None) with post-hoc verification.
Tokenizer pin c0382117… attested across base AND instruct checkpoints.
GGUF shas: `~/workspace/oxide-runpod-artifacts/SHAS.txt` (9 models).
QLoRA recipe (chosen, identical all six runs): r16/α32, lr 1e-4
cosine, 3 epochs, seq 1024, seed 17; final train losses — oxide arms
0.217/0.199/0.199, rust arms 0.162/0.151/0.155 (1.5/7/14B).

## The twelve arms

Generation (200 sessions/arm; metric constructions as computed:
`pass@1` = first-attempt verifier pass over all 200 sessions;
`pass@10-with-verifier` = share of the 20 tasks where ≥1 of 10 seeded
SESSIONS reached green within the 4-attempt loop; `iterations-` and
`tokens-to-green` are per-green-SESSION means, tokens summed through
the passing attempt, censored sessions excluded and counted):

| arm | pass@1 | pass@10v | iters→green | tok→green | censored |
|---|---|---|---|---|---|
| base-ox-1.5 | 0.000 | 0.00 | — | — | 200 |
| base-rs-1.5 | 0.190 | 0.35 | 1.24 | 72.2 | 150 |
| tune-ox-1.5 | 0.485 | 0.75 | 1.14 | 86.1 | 88 |
| tune-rs-1.5 | 0.750 | 0.90 | 1.06 | 67.0 | 43 |
| base-ox-7 | 0.045 | 0.10 | 1.0 | 83.9 | 191 |
| base-rs-7 | 0.565 | 0.60 | 1.0 | 66.8 | 87 |
| tune-ox-7 | 0.555 | 0.70 | 1.1 | 85.6 | 77 |
| tune-rs-7 | 0.885 | 0.90 | 1.0 | 69.1 | 23 |
| base-ox-14 | 0.380 | 0.80 | 1.31 | 157.5 | 104 |
| base-rs-14 | 0.550 | 0.55 | 1.0 | 74.5 | 90 |
| tune-ox-14 | 0.545 | 0.75 | 1.17 | 98.6 | 73 |
| tune-rs-14 | 0.990 | 1.00 | 1.01 | 70.3 | 1 |

Strict repair (200 seeded-defect sessions/arm, single proposal):

| size | base-ox (card) | base-rs | tune-ox | tune-rs |
|---|---|---|---|---|
| 1.5B | 0.110 | 0.785 | 0.655 | 0.695 |
| 7B | 0.475 | 0.890 | 0.455 | 0.830 |
| 14B | 0.805 | 0.950 | 0.760 | 0.755 |

## Pre-registered endpoint readings

**Primary (paired per-task, tune-ox − tune-rs, 2-SE):**

| size | generation | strict repair (paired per-class) |
|---|---|---|
| 1.5B | −26.5pp ± 28.9 (not decided) | −4.0pp ± 26.1 (not decided) |
| 7B | **−33.0pp ± 26.2 (rust-tuned wins)** | **−37.5pp ± 21.4 (rust-tuned wins)** |
| 14B | **−44.5pp ± 21.4 (rust-tuned wins)** | +0.5pp ± 24.7 (not decided) |

**Headline (tune-ox-7 vs base-rs-14, unpaired 2-SE):** generation
+0.5pp ± 9.9 — **statistical parity**: the oxide-tuned 7B (0.555)
matches the untuned 14B on Rust (0.550). Strict repair −49.5pp ± 7.7 —
the untuned 14B on Rust is decisively better at repair.

**Capability-window trend (gen Δ across 1.5→7→14B):** −26.5 → −33.0 →
−44.5pp — monotone AGAINST the purpose-built language as scale grows;
larger models extract more from rust fine-tuning (tune-rs-14 reaches
0.990), not less.

**Token efficiency (gen tokens-to-green ratio, tune-ox/tune-rs):**
1.29 / 1.24 / 1.40 (1.5/7/14B) — the oxide arms also spend more tokens
per solved task. (The repair-family ratio was registered but is not
computed by the analysis and is therefore not claimed.)

**Sanity tripwires:** base-rs-7 0.565 in [0.30, 0.80] — and byte-exact
to the committed local v03c rust rate; base-ox-7 0.045 against the
amended floor [0.02, 0.60] (original chosen floor 0.05 was calibrated
on the grammar-CONSTRAINED historical 30.5%; the breach, diagnosis,
and non-silent amendment are recorded in
`docs/superpowers/evidence/2026-08-27-runpod-dryrun.md`).

## Decision mapping (spec, quoted): the result lands on branch three

> "Null or rust-tuned wins: the pretraining prior holds under matched
> small-scale fine-tuning; the GP idea is parked, and the null is
> published with the same care as a win."

Rust-tuned wins the generation primary at 7B and 14B (and the repair
primary at 7B); no pre-registered comparison shows the oxide arm
winning. **The general-purpose-language idea is parked per the
pre-registration.** Two observations the write-up should carry, stated
as observations, not endpoint claims:

1. **The fine-tune crushes the card**: tune-ox-7 card-free 0.555 vs
   base-ox-7 with-card 0.045 (+51pp from ~17k supervised tokens), and
   the headline parity means purpose-built-language-plus-tiny-tune
   matched 2× scale on the prior's home language for *generation* —
   while losing repair by 49.5pp, consistent with generation-only
   training (the recorded limitation).
2. **The constrained-era baseline was grammar-assisted**: removing the
   grammar dropped the card-only oxide baseline from the historical
   constrained 30.5% to 4.5% under otherwise-healthy serving — the
   constrained-decoding-deforms thesis measured on our own baseline.

## Honest limits (inherited + measured)

- Pilot-scale corpus (~17k supervised tokens/arm): this null kills
  "language + SMALL fine-tune" only — the pre-registered
  interpretation limit.
- Seed replicates partially collapse at temp 0.2: mean distinct
  first-attempt outputs per task ranges 2.35 (base-rs-14) to 5.55
  (base-ox-1.5) of 10 seeds; effective replicate n sits between 20
  tasks and 200 sessions. The paired-per-task/per-class constructions
  are the honest primaries for exactly this reason.
- tune-rs-14 sits at 0.990 pass@1 — near-ceiling; its comparisons are
  ceiling-compressed.
- One environment, one GPU class (3090), one quantization (q8_0),
  single eval corpus t01–t20.

## Cost

Pod $0.22/h; bring-up + trainings + campaign ran well under the $23
tranche (final spend recorded at teardown in the session ledger; order
of $2). The 16:30 top-up was not needed.
