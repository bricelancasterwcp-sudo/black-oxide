# Wave 8 Phase B — run plan

**Date:** 2026-09-01. Branch `v04-wave8-phaseb`, off `main` @ `12f07a1c`.
**Written and committed BEFORE the pod is provisioned.**
Spec: `docs/superpowers/specs/2026-08-31-v04-wave8-large-tasks-design.md`
(§2 as amended 2026-09-01). Phase A report:
`eval/results/v04-wave8-large/REPORT.md`.

## The endpoint

**surplus = (model oxide/rust, paired by `(seed, task)` and green in
both) ÷ (reference oxide/rust over the tasks that paired).**

Shipped as tested code: `eval.experiment_report.model_surplus`, six
mutations killed. Phase A measured the large-tier reference ratio at
**1.0622**; the small (eval) tier reads **0.9462**.

## Arms

Five runs, chosen so every one of them is load-bearing:

| # | arm | task set | why it is here |
|---|---|---|---|
| 1 | `tune-ox-7` | large | endpoint numerator |
| 2 | `tune-rs-7` | large | endpoint numerator |
| 3 | `tune-ox-7` | eval (small) | small-vs-large contrast, same environment |
| 4 | `tune-rs-7` | eval (small) | as above |
| 5 | `base-rs-7` | eval (small) | drift guard: must reproduce 0.565 |

Runs 3 and 4 exist so the small/large comparison is **within one
environment**. Comparing the large tier against wave 6's 1.1982, measured
on other hardware in another wave, would reintroduce exactly the kind of
cross-set comparison Phase A was written to kill.

Adapters: `adapters-v5/tune-{ox,rs}-7-v5`, sha256 in
`~/workspace/oxide-runpod-artifacts/SHAS.txt`, verified after transfer.

### Dropped in advance, with the reason

**`base-ox-7` card-only is NOT part of the endpoint.** It reads 0.075
pass@1 on the small tier; on 200–600 token programs it will read at or
near 0.000 and cannot discriminate. SPEC §64's rule is to drop an arm
that cannot discriminate, not one that scores badly. If the five arms
finish comfortably inside budget it may be run last as an **exploratory**
arm, reported separately and never folded into the endpoint.

## Pre-registered stops

1. **`base-rs-7` does not reproduce pass@1 0.565 on the eval tier** →
   the environment is not comparable with waves 0–7. Report the drift;
   do NOT publish a large-tier surplus against prior waves' numbers.
2. **Spend reaches $2.50** → stop, report whatever completed. (Estimate
   ≈$1.00–1.45: ~1h setup plus ~4h generation at $0.22/h community 3090.
   Balance before this wave: ≈$7.2.)
3. **Fewer than 5 paired green cells on the large tier** → the surplus
   rests on too small a sample. `model_surplus` already returns `None`
   below one pair; the report must state `n_pairs` beside any ratio and
   must not present a ratio the sample cannot carry.
4. **`torch.cuda` unavailable or the wrong GPU** → terminate before
   committing hours (a driver-570 pod cost $0.43 in wave 5).

## Expected shape of the answer

Phase A found the *language* crosses parity at scale (0.9462 → 1.0622).
Phase B asks whether the *model's* surplus over the language moves too.
Wave 6 measured that surplus at 1.276 on small tasks. Under the amended
endpoint:

- **surplus ≈ 1.0** — the model spends what the language requires; the
  28% was a small-task artifact, and the remaining problem is entirely
  the language's scale behaviour that Phase A found.
- **surplus ≈ 1.28** — the model's overhead is size-independent and
  stacks on top of the language's inversion. Worst case for the project,
  and the most useful to know.
- **surplus > 1.28** — the model degrades faster than the language does.

## Ops rules carried forward

- Community RTX 3090, single `gpuTypeIds` pin, `allowedCudaVersions`
  `["12.9","13.0"]`, `PUBLIC_KEY` baked into pod env.
- Liveness = SSH to the thing, never the `runtime` field.
- Verify `torch.cuda` before committing hours.
- Count-verify every rsync by FILE COUNT, never `du`.
- Terminate, then verify zero pods TWICE.
