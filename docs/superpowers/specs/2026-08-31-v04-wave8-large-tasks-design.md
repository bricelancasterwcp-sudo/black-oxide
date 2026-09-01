# v0.4 — wave 8: does any of this survive scale?

**Date:** 2026-08-31
**Branch:** `v04-wave8-large-tasks`, off `main` @ `f191e5ca`.
**Status:** prepared, awaiting go. Balance ≈ $7.2.

## 1. The question

Every number this project has published describes programs of 40–150
tokens. The eval references median 73 tokens; `t19` is a 30-token
program. Wave 7A found that **89% of the model's 28% token surplus is
helper-function definitions, 76% of them called exactly once**, and drew
the only honest conclusion available: on tasks this small, *any*
abstraction is overhead, so the dynamic ratio partly measures the
model's disposition to factor code rather than its token efficiency.

That bounds every dynamic claim the project makes. It also quietly
bounds the static ones: if Oxide wins by removing per-line ceremony, its
advantage should hold or grow with program size; if it wins by a fixed
constant, the advantage dilutes and **0.9462 is a toy-program number**.

Wave 8 builds the instrument that can tell the difference: a second eval
tier of large tasks, authored to the same discipline, measured with the
same estimands.

Two questions, in priority order:

1. **Does Oxide's static advantage survive scale?** Costs $0. Never
   asked. Potentially the more consequential of the two, because it
   bears on the project's headline claim rather than on the model's
   habits.
2. **Does the 28% model surplus survive when a helper can amortise?**

## 2. Pre-committed outcomes

The dynamic endpoint is the large-tier equivalent of wave 6's 1.1982.

**§59.7's construction needs restating for a fresh tier, and this is
exactly the kind of detail that cost four waves.** §59.7 pairs cells by
`(seed, task)` and restricts to those green in *every wave* — a
cross-wave intersection that does not exist for a task set measured for
the first time. The large-tier construction is therefore: **pair by
`(seed, task)`, keep cells green in both arms within this campaign, and
report the paired token ratio over that set.** It is the same defect fix
— never average each arm over its own green set — applied to a
single-campaign comparison. The small-tier re-run inside the same
campaign (§8) uses the full §59.7 form unchanged, since its history
exists.

**AMENDED 2026-09-01, after Phase A and before any Phase B run.** The
bands below are stated on the raw large-tier ratio, and were calibrated
when the reference ratio was assumed to sit near 0.94. Phase A measured
it at **1.0622**, so a model matching the references exactly would score
1.0622 and fall in state 2 while its true surplus is zero. **The endpoint
is therefore the SURPLUS — the model's oxide/rust ratio divided by the
references' ratio over the same green cells — and the three bands below
are read on that surplus scale.** This restores the estimand wave 6
actually used (1.1982 ÷ 0.9393 = 1.276) rather than inventing a new one.
The raw bands are left visible rather than rewritten, per house practice.

Three states, committed before the tier is authored, each changing what
gets built next:

| large-tier dynamic ratio | reading | consequence |
|---|---|---|
| **≤ 1.05** | the 28% was a benchmark artifact | the project's honest efficiency claim is the **static** one; publish that correction and stop designing against the dynamic surplus |
| **1.05 – 1.30** | real, largely size-independent model surplus | a live design target again; re-run wave 7A's attribution instrument on the large tier to find where it goes at this size |
| **> 1.30** | Oxide scales *worse* than Rust | a genuine language finding, the most consequential outcome available, and every prior claim needs a scale caveat attached |

The static endpoint is pre-registered separately and reported whichever
way it moves:

> **Large-tier static ratio vs the small-tier 0.9462.** A rise toward
> 1.00 means Oxide's advantage is a fixed prelude constant that dilutes
> with size. A hold or improvement means the advantage is per-line and
> generalises upward. Both are reported; neither is re-authored against.

**Nothing here is a null result.** That is the test of whether this wave
is worth funding, and it passes.

## 3. Two strata, or the answer is ambiguous

Twenty tasks authored in two strata, tagged in the task record:

- **12 compositional** — containing genuine repeated sub-computation
  used at least twice, where a helper function legitimately pays for
  itself.
- **8 large-linear** — large but with no natural factoring. Control.

The counts are exact as authored, not approximate. If oracle
verification drops a task (stop 1), the achieved per-stratum counts are
reported as achieved and the shortfall named; the split is never
rebalanced after seeing a result.

The stratification is what turns a yes/no into an attribution, at no
extra authoring cost. **If the surplus collapses on compositional tasks
and persists on linear ones, the model's habit is premature rather than
wrong** — a precise finding, and one that no single-stratum design could
produce.

The stratification is a judgement call, not forced by evidence. It is
recorded here so that it is falsifiable later: the per-stratum split is
published even if the two strata read the same, in which case the
stratification bought nothing and the spec says so.

**Sizing:** 200–600 tokens per reference program, verified with the
pinned tokenizer (`eval/tokenizer_pin.py`), never eyeballed. A tier
authored to a target it does not actually hit would reproduce wave 6's
failure at a larger size.

## 4. Authoring discipline — where this wave can go wrong

I have been designing Oxide for eight waves and would be authoring both
arms of its benchmark. That is the single largest threat to this wave's
validity, and wave 7A's guard — a criterion fixed before looking — is
necessary but not sufficient here, because wave 7A only *reviewed*
existing Rust; wave 8 *creates* it.

**The rule: for each task, author the Rust arm first, from the prompt
alone, idiomatically, before writing a line of Oxide.** Then author the
Oxide arm. This inverts the bias direction. A Rust reference written
after an Oxide solution tends to become a transliteration of an
Oxide-shaped approach; written first, it is simply Rust.

Supporting guards, all of which apply to both arms symmetrically:

- Both arms oracle-verified: Oxide through the transpiler and `rustc`
  with matching `expected_stdout`, Rust through `rustc` directly.
- `contamination_report` run against the new tier before any measurement.
- Every task's two programs published, so the pairing is auditable rather
  than asserted.
- Wave 7A's re-review criterion applied to the finished tier as a
  separate pass: *rewrite only where a reference hand-rolls something the
  standard library provides; style is not grounds.*

**A net Rust improvement from that final pass is the expected outcome,
not a failure.** Wave 7A's credibility came from finding a hit that moved
the ratio *against* Oxide.

## 5. Instrument work

`eval/cost_census.py` is hard-bound to `PAIRS_ROOT` via
`load_train_tasks()`. Wave 7A's eval-set census was therefore computed
ad-hoc rather than by committed code — a gap that should not be repeated
at a third task set.

**Parameterise the census over a pair root and task file**, shipped as
tested code with mutations killed, per house method. The train set, the
eval set and the large tier then all run through one instrument, and the
wave-7A numbers become reproducible by command rather than by narrative.

Everything else reuses existing instruments unchanged: the §59.7
composition-controlled dynamic estimand in `eval/experiment_report.py`,
`eval/harness.py`, and wave 7A's attribution categories.

## 6. Layout

New paths, chosen so that nothing existing shifts underneath the
measurement:

- `eval/tasks-large.jsonl` — the 20 task records, carrying `stratum`
- `eval/references-large/{oxide,rust}/` — both reference arms

**`eval/solutions/` stays frozen** — it is the contamination reference,
and wave 6 established that modernising it would shift that baseline
toward masking real leakage. **The existing 20 eval tasks stay
untouched** and are re-run inside the same campaign as the continuity
anchor.

## 7. Phase A — authoring and static measurement (local, **$0**)

1. Author 20 task records with prompts, `expected_stdout`, class and
   stratum.
2. Author the Rust arm first, then the Oxide arm, per §4.
3. Oracle-verify both arms; size-verify against the 200–600 token band.
4. Contamination report.
5. Parameterise the cost census (§5); run it on the large tier.
6. Report the static ratio, per-class and per-stratum, against the
   pre-registered 0.9462 baseline.

Phase A stands alone. If Phase B is never funded, wave 8 still delivers
a first answer on whether the static headline survives scale.

## 8. Phase B — dynamic measurement (pod, **gated on A**)

Arms, using the **preserved v5 adapters — no amplification, no
training**:

- `tune-ox-7-v5` and `tune-rs-7-v5` on the large tier
- card-only `base-ox-7`, for the untuned reading
- `base-rs-7` as the drift guard, which has read **0.565 byte-exact
  across seven environments**
- the existing 20 small tasks re-run in the same campaign, so a
  large-tier movement cannot be an environment artifact

### The confound, pre-registered rather than discovered

The v5 adapters were trained entirely on small-task corpora and have
never seen a large Oxide program. Phase B therefore measures
out-of-distribution behaviour in part.

**The Rust control is trained identically, so the confound is symmetric
and the ratio still reads.** But pass rates will likely fall on both
arms, and **that fall must not be reported as a capability finding.** It
is a distribution-shift artifact, stated here in advance so that it
cannot be re-narrated as a result later.

Removing the confound properly means retraining on a large-task corpus —
a separate, costed, approved wave, not a silent extension of this one.

## 9. Cost

| phase | GPU | estimate |
|---|---|---:|
| A — authoring + static | none | **$0** |
| B — 4 arms + small-tier re-run, 7B only, no training | community 3090 | ≈ **$1.00** |
| B extended to the 14B tier | 8 arms | ≈ **$1.50** |

Priced from measured runs, not projected: wave 5 was a card-only,
no-training campaign at **$0.36**, and wave 4's full eight-arm campaign
with training was **$1.61**. Phase B has more arms and larger programs
than wave 5 but no amplification and no training.

Against ≈$7.2 remaining, the worst case leaves ≈$5.7 — enough for a
wave 9 at 14B, which is where the interesting result would be if
Phase B lands in state 2 or 3.

## 10. Stops

1. **Fewer than 16 of 20 tasks reach oracle-green in both arms** → stop,
   report the tier as unbuildable at this size, and do not measure a
   partial set as though it were the design.
2. **Median size lands outside 200–600 tokens** → the tier does not test
   what it claims; re-author before measuring, never re-label the band.
3. **Contamination report non-zero** → stop and diagnose before any
   measurement.
4. **The final re-review pass raises the static ratio above 1.00** →
   report it, and stop claiming Oxide is below parity at scale, rather
   than re-authoring to recover the number.
5. **Phase B is never entered** without a fresh cost estimate and
   approval after A reports.

## 11. Out of scope

Retraining on a large-task corpus (§8). The exposure lever, still
unpulled since wave 3. Vocabulary shipped against the helper-function
surplus — wave 7A ruled that out and this wave does not reopen it. The
card struct-rebuild fix, which is evidenced and cheap but belongs with a
card cycle rather than an instrument cycle. Standing debt from wave 4's
feed-forward.
