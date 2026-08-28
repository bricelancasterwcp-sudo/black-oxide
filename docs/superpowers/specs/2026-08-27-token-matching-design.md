# Token matching — matched supervised-token budgets from the paired factory corpus

**Date:** 2026-08-27
**Track:** fine-tune (SPEC §32.4 item 4), **sub-project 3 of 4, taken out
of order** — before training infrastructure, because this is the spec
that can kill the design. Per the 2026-08-27 session ruling ("approach
B"), the remaining two sub-projects (training infrastructure and the
experiment) merge into one following spec: the infrastructure is a
runbook adaptation, not a design problem.
**Status:** design approved in session (sections approved in chat,
2026-08-27); this document is the written record for review.

Two session rulings this spec inherits, recorded with their dates:

- **Pilot-scale now (2026-08-27).** The experiment trains on the
  40-task corpus as cleared by its own gate on 2026-08-13, not on the
  ~400-task full-corpus target. Corpus scale-up is a separate, gated
  follow-on decision, not an extension of this experiment.
- **Subjects are Qwen2.5-Coder 1.5B / 7B / 14B, all training and
  evaluation on RunPod (2026-08-27).** The 14B was added to probe the
  capability window's upper edge. The all-RunPod ruling means every
  arm, including untuned baselines, is re-measured in one pinned
  environment; committed local campaigns become historical context, not
  comparanda. Both facts bind the *experiment* spec; they appear here
  because the tokenizer decision below depends on the subject list.

## What exists, measured (2026-08-27)

The data factory produced a **paired** corpus: 40 tasks (10 per class),
each with an independently-authored idiomatic Rust reference (the
`__oxide_` guard enforces non-derivation) and a Black Oxide reference,
all validate_pair-green, plus amplified verified solutions in both
training arms. Merging `collect_verified` over `eval/results/train-amp2`
and `eval/results/train-amp2-slice`, restricted to the 40 kept tasks:

| class | oxide programs | rust programs |
|---|---|---|
| arithmetic/loops | 93 | 139 |
| strings | **10** | 67 |
| structs/option | 78 | **62** |
| vectors | 30 | 103 |
| **total** | **211** | **371** |

Character totals: oxide 47,792, rust 71,336 (1.49×). Reference pairs
alone: oxide 8,848, rust 7,181 (0.81× — the hand-authored Rust is
*smaller* than the oxide references).

Two measured facts reshape the design the factory spec sketched:

1. **The surplus direction varies by class.** The factory spec expected
   Rust to be uniformly ~3× and token matching to mean "discard Rust".
   Measured: rust is surplus in three classes but *deficit* in
   structs/option (62 vs 78). The matching rule below is therefore
   symmetric — per class, the smaller arm sets the budget and the
   larger arm trims, whichever arm that is.
2. **Oxide strings is nearly empty.** 10 amplified programs across 10
   tasks. Matching pulls rust strings down toward that level: the
   matched corpus is light on strings in both arms. That is the honest
   consequence of matched design — the corpus teaches what oxide's
   yield could produce — and it is stated rather than patched.

These numbers are recomputable from committed artifacts; the acceptance
test below pins them so collector drift cannot silently change the
corpus this spec was approved against.

## Decisions

**1. The matched unit is supervised tokens.** Training is standard
prompt-masked SFT; loss falls on completion tokens only. "How well does
the model learn per training token" therefore means per *loss-bearing*
token: the budget counts tokens of the program text (plus terminator),
not the prompt. Prompts are task text, identical across arms and
arm-neutral; their totals are reported descriptively in the manifest
but are not matched. (Matching total-sequence tokens instead would let
prompt repetition count as learning budget, which it is not.)

**2. One tokenizer, pinned by content hash.** All three subjects are
Qwen2.5-Coder, which share a tokenizer, so one matching is valid for
every size. The tokenizer is pinned by the SHA-256 of its
`tokenizer.json`, recorded in the manifest, and a **build-failing
assertion** checks at construction time that all three checkpoints'
tokenizer files hash identically. Adding a non-Qwen subject invalidates
the matching; that is a stated load-bearing constraint, not a footnote.

**3. Training text is normalized source, both arms.** Amplified
programs are already stored as `normalize_source` output (trailing
whitespace and blank lines stripped, indentation preserved); references
are normalized identically at construction so the arms are consistent.

**4. Training format is card-free, symmetric, generation-only.**
Examples are bare prompt→program in both arms — no language card. The
fine-tune's job is to move the language from a 900-word prompt tax into
the weights; tuned models are evaluated card-free, untuned baselines
keep their measured card condition (experiment-spec territory, recorded
here because the example format defines what gets counted). Training
data is generation pairs only; repair is still *evaluated*, and whether
repair capability transfers from generation-only training is a finding.
Building a seeded-defect training pipeline for both arms is scope this
track does not need yet — recorded as a limitation.

**5. Corpus composition: references plus amplified, references never
trimmed.** Each task contributes its reference solution and its
amplified verified programs, per arm. Trimming touches amplified
programs only, so every task keeps ≥1 example per arm by construction
— the no-task-emptied invariant needs no enforcement machinery.

**6. Per-class matched budgets, symmetric.** For each class *c*:
`budget_c = min(oxide_tokens_c, rust_tokens_c)` where the totals count
references plus amplified supervised tokens. The larger arm trims down
toward the budget. The corpus-level totals are then matched as a
derived consequence (sum of per-class budgets), reported, and carry no
separate knob. Total-only matching is rejected as the
aggregates-hide-compensating-drifts trap: rust could match overall
while being string-heavy exactly where oxide is starved.

**7. The trim rule is deterministic and blind.** Within a class, the
surplus arm's amplified programs are ordered by the ascending hex
digest of the SHA-256 of their normalized source; programs are dropped
from the front of that order until the arm's class total first falls to
or below the budget, then trimming stops. The other arm is never
trimmed in response, and the rule never iterates. No human or model
picks which programs survive. One edge fails closed: if a class's
*references alone* exceed its budget, no amount of trimming can reach
it — construction raises a build failure naming the class rather than
shipping a silently under-matched corpus, and the ruling escalates to
the owner. (Not reachable on the measured corpus; stated because
unreachable today is not unreachable after a re-author.)

**8. The tolerance is derived, not chosen.** Dropping whole programs
quantizes the achievable match: the residual gap per class is bounded
by the token length of the largest amplified program in that class —
the step size of the only knob the rule has. The manifest records, per
class: budget, kept tokens per arm, achieved gap, and the quantization
step that bounds it. There is no chosen threshold to sanity-check
because there is no chosen number.

**9. Epoch parity is an inherited invariant.** Both arms train with
identical hyperparameters and epoch counts; matched per-epoch
supervised tokens therefore give matched totals. The experiment spec
inherits this as an invariant, not a suggestion.

**10. The static token-efficiency estimand is measured here.** The
reference pairs are the clean instrument the session asked for:
independently-authored idiomatic solutions to identical tasks with
identical stdout. Report, under the pinned tokenizer, per class and
overall: tokens per program, oxide vs rust, references and amplified
programs separately (references compare authored solutions;
amplified compares what the models themselves emit). Descriptive
estimand, no threshold — it feeds the general-purpose-language
question, it gates nothing. The character totals above hint the two
comparisons may point in *opposite directions* (reference rust smaller,
amplified rust larger); characters are not tokens, and the tokenizer
decides. Both directions are reportable results.

## Artifacts

```
eval/train/matched/
├── oxide.jsonl     one record per kept example
├── rust.jsonl
└── manifest.json
```

Record schema: `{task, class, source: "reference"|"amplified", text,
sha256, sup_tokens}`. Manifest: tokenizer id + tokenizer.json SHA-256,
per-class table (budget, kept tokens and example counts per arm,
achieved gap, quantization step), prompt-token totals per arm
(descriptive), the **dropped list** (task, arm, sha256, sup_tokens —
named, never silently deleted), collector roots and source commit, and
the contamination result. An absent field is a build failure, not a
default: nothing in the manifest may look like a measurement it isn't.

## Guards on the matched output

- **Contamination guard re-runs on the matched files** (exact
  normalized match against every committed `eval/solutions/` program;
  n-gram overlap against `eval/tasks.jsonl` prompts) and fails the
  build on any hit. Matching only removes programs, so a pass is
  expected — the guard exists because "expected" is not "checked".
- The shape gate and difficulty band do **not** re-run: both judge task
  authorship and generation campaigns, and matching changes neither
  the tasks nor any generated program — it only selects among already
  verified ones. Stated so their absence reads as a decision, not an
  oversight.

## Tests (each mutation-tested before it counts)

1. **Determinism:** identical inputs produce byte-identical
   `matched/` outputs; reordering collector input does not change them.
2. **Budget invariant:** per class, kept supervised tokens of each arm
   differ by no more than the recorded quantization step; the surplus
   arm ends at or below budget.
3. **References survive:** every kept task has its reference example in
   both arms' output.
4. **Trim order is load-bearing:** perturbing the hash order changes
   which programs drop — a test that fails if the order stops being
   consulted.
5. **Manifest completeness:** every schema field present in the
   serialized payload; a new field cannot be silently dropped.
6. **Acceptance pin:** the collector, run over the committed amp2 +
   slice roots restricted to kept tasks, reproduces the counts table
   above (211/371, per-class as tabulated). Collector or corpus drift
   fails loudly against the numbers this spec was approved on.
7. **Tokenizer identity:** the three checkpoints' tokenizer hashes are
   equal, and equal to the manifest's pin.

## Honest limits

- **This is a small-data LoRA regime by design.** ~251 oxide examples
  (211 amplified + 40 references), supervised tokens on the order of
  tens of thousands. The pre-registered interpretation limit carries
  forward to the experiment spec: a null kills "language + *small*
  fine-tune", not the thesis. The per-token comparison stays internally
  valid because both arms are equally small and matched.
- The strings class is thin in both arms after matching; per-class
  eval readings on strings will be low-precision, and the experiment
  spec must size its per-class claims accordingly.
- Matching by discard means the rust arm's kept set is a hash-selected
  subsample, not the full measured distribution of what the models
  emit. The dropped list keeps the discard auditable.
- Supervised-token matching leaves prompt-exposure counts slightly
  unequal across arms (different example counts per task). Judged
  acceptable: prompts are arm-neutral task text; totals are reported.

## Out of scope

Training infrastructure, RunPod runbook, LoRA hyperparameters, eval
endpoints and thresholds, the budget stop rule ($23 + scheduled top-up
2026-08-28 16:30), and the decision mapping to the general-purpose
language question — all belong to the following experiment spec.
Repair-format training data and corpus scale-up are recorded
limitations, not deferred work items of this spec.
