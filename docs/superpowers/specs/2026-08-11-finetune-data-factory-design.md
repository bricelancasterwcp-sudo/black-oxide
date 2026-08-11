# The data factory — a training corpus disjoint from the eval

**Date:** 2026-08-11
**Track:** fine-tune (SPEC §32.4), **sub-project 1 of 4**.
**Status:** design approved in session; implementation plan follows.

This is the first of four specs for the fine-tune track. It covers the
**data factory only**: producing a compiler-verified, paired Black Oxide
and Rust training corpus on new tasks. Training infrastructure, the
token-matching methodology, and the experiment itself are separate
specs and are explicitly out of scope here.

## Why this is the critical path, not a preprocessing step

The direction memo describes the data factory as something the existing
harness largely provides — "triples.jsonl is the verified repair dataset
by design". Measured against what is actually on disk, that is not the
case. Scanning all 123 committed `triples.jsonl` files (22,587 attempts):

| arm | attempts | passing | **unique passing** | verified repair pairs |
|---|---|---|---|---|
| oxide | 8,154 | 436 | **158** | 63 |
| explicit | 8,373 | 384 | 129 | 97 |
| rust | 6,060 | 1,330 | 296 | 108 |

**158 unique passing Black Oxide programs** is not a fine-tuning corpus.
They are also unevenly spread across only 16 of the 20 tasks — t09, t11,
t12 and t14 have **zero** — with a long tail at 1–2 programs (t13: 1,
t10: 2, t15: 2) against t03's 25 and t19's 20.

The second problem is disqualifying rather than merely limiting. **All
158 are solutions to t01–t20, which is exactly what `v03c` measures.**
Training on them and evaluating on t01–t20 is train/test contamination,
and it would silently void the 1,800-session closing baseline that was
run specifically to be this track's comparison point.

So the factory's job is not to reshape existing data. It is to produce a
corpus that does not exist yet, on tasks the eval has never seen.

## Decisions taken, and why

**1. t01–t20 stays the held-out eval; training uses new tasks.**
The alternatives were splitting t01–t20 into halves (which halves the
eval to 10 tasks, raising SPEC §47's ±5pp resolution floor by about √2
to ±7pp, and strands `v03c`'s published 20-task rates) or authoring a fresh eval
corpus (which makes `v03c`, `g1c` and `g0c` all non-comparable and
forces a 1,800-session re-run before any fine-tune number means
anything). Keeping the eval fixed is the only option that preserves the
baseline already paid for.

**2. Hybrid sourcing: frontier authors tasks, the GPU amplifies
solutions.** These are two different needs met from two different
sources. Task *diversity* cannot come from the local models — a 7B model
asked to invent benchmark tasks produces narrow, repetitive prompts.
Solution *volume* is just GPU time on a harness that already exists.
Pure rejection sampling from the local models was rejected because it is
self-distillation bounded by what those models already do (~30% oxide
first-pass) and leaves task authoring unsolved. Grammar-directed
synthesis was rejected for two reasons given below.

**3. The base model is `qwen2.5-coder-7b`.** It is the strongest local
subject on the ladder and the only candidate with a measured baseline
already on disk (`v03c`: oxide 36.0 first-compile / 30.5 first-pass,
rust 56.5 first-pass). Fine-tuning it means the result is scored against
a measurement that exists, with no extra campaign. This binds the
factory in one way that matters here: the corpus must be a corpus that
model can be trained on, and the merged model will later have to be
re-quantized to **q8_0** and served through llama.cpp to match the
baseline's serving conditions (SPEC §48/§49) — a constraint recorded now
so the training spec inherits it rather than discovering it.

## The Rust arm must be idiomatic Rust

This is the constraint that rules out grammar-directed synthesis, and it
is worth stating on its own because getting it wrong is silent.

The experiment compares how well a model learns Black Oxide against how
well it learns Rust, per training token. If the Rust training data were
transpiler output — `__oxide_`-prefixed, mechanically generated from the
Oxide side — the Rust arm would be learning a dialect no Rust programmer
writes, and any Black Oxide advantage would be an artifact of having
handicapped the control. That is the same failure mode as the
matched-novelty control's whole design, inverted.

Therefore: **Rust reference solutions are authored independently and are
never derived from the Oxide solution.** A mechanical check rejects any
Rust training program containing the reserved `__oxide_` prefix (SPEC
§22). Synthesis was also rejected on a second ground — synthetic
programs carry no natural-language prompt, while the eval measures
prompt→program, so a synthetic corpus trains a different task than the
one being scored.

## What the factory produces

A new `eval/train/`, structurally separate from the eval corpus so the
two cannot be confused by a glob or a careless path:

| artifact | contents |
|---|---|
| `eval/train/tasks.jsonl` | new task prompts; same schema as `eval/tasks.jsonl` (`id`, `title`, `prompt`, `difficulty`, `expected_stdout`) |
| `eval/train/pairs/` | per task, the compiler-verified solutions in both arms |
| `eval/train/manifest.json` | provenance: authoring model, generation parameters, filter version, dedup counts, contamination-check result |

**Task ids are `n001…`, never `tNN`.** The prefix is the cheapest
possible guard against a training task being mistaken for an eval task
in a log, a filename, or a results table.

`expected_stdout` is captured by running the verified reference
solution — and the Oxide and Rust references must produce **identical**
stdout, which is a free cross-check that the two references implement
the same task.

## Stage A — frontier authoring

Agents author, per task: the prompt, one reference Oxide solution, one
reference Rust solution, and the expected stdout. Every reference passes
the same gate `eval/solutions/` already passes — transpile, compile,
run, stdout match — and a task whose references do not both pass is
discarded rather than repaired, so the corpus never contains a program
that was massaged into passing.

New tasks are authored against the same span t01–t20 covers: arithmetic
and loops, vectors, strings, structs and Options. This is what makes the
difficulty-comparability check below meaningful rather than decorative.

**A known limitation, recorded rather than solved.** The memo flags
single-author bias in t01–t20. A frontier-authored corpus is also
effectively single-author. Authoring in independent batches with
different domain seeds reduces near-duplicate prompts but does not make
the corpus multi-author, and this spec does not claim it does.

## Stage B — GPU amplification

The existing harness generates K solutions per task with the local
models on the **oxide and rust arms**, keeping only those that compile
**and** pass, deduplicated on normalised source. This is SPEC §32.4's
"compiler-filtered data factory" running on infrastructure that already
exists. The explicit dialect is not amplified — it is the eval's control
arm, not a training target.

### K is calibrated from `v03c`, not guessed

Measuring `v03c`'s oxide and rust arms per task at K = 30 (3 families ×
10 seeds), which is exactly what an amplification run looks like:

| arm | passing | unique | unique rate | per-task unique |
|---|---|---|---|---|
| oxide | 135 | 114 | **84%** | median 4.5, mean 5.7, **4 tasks at zero** |
| rust | 325 | 260 | 80% | median 16.0, mean 13.0, 4 tasks at zero |

Two corrections this produced to an earlier draft of this spec, recorded
because both would have mis-sized the run:

- **Uniqueness within one campaign is 84%, not 36%.** The 36% figure
  (158 unique of 436 passing) is *cross-campaign* — the same task solved
  the same way in `g0c`, `g1c` and `v03c` collapses to one program.
  Dedup still matters, but an amplification run is not two-thirds
  repetition; it is roughly one-sixth.
- **K = 30 is enough, not K = 60.** The earlier draft projected K = 60
  from the wrong dedup rate. At K = 30 the oxide arm already yields a
  mean of 5.7 unique programs per task.

The distribution is what actually constrains the design, and it is badly
skewed: `[0, 0, 0, 0, 1, 2, 2, 2, 2, 4, 5, 7, 7, 7, 8, 9, 11, 14, 16,
17]`. **A fifth of tasks yield nothing at all** — those are tasks the
local models cannot solve, and in a 400-task corpus roughly 80 would
contribute only their frontier reference pair. That is expected and
acceptable; it is stated so the corpus target is read as a mean over a
skewed distribution rather than a per-task guarantee.

Rust yields about three times more programs per task than oxide, which
is the opposite of a problem: token matching (a later spec) will need to
*discard* Rust programs to hit a matched token budget, so having surplus
is the comfortable direction.

## The contamination guard

A test, run in the suite, that **fails the build** if any t01–t20
content appears in the training corpus:

- exact match on normalised program text against every committed
  solution in `eval/solutions/{oxide,explicit,rust}/`
- an n-gram overlap threshold on prompt text against `eval/tasks.jsonl`

This one test is what protects the `v03c` comparison. Without it, the
track's headline is unfalsifiable — a fine-tune that had seen the eval
tasks would post a large gain regardless of whether Black Oxide is
easier to learn than Rust, which is the entire question.

## Difficulty comparability, made checkable

The train/eval split accepted a stated risk: if the new tasks are
systematically easier than t01–t20, the fine-tune posts a "gain" that is
really a difficulty artifact.

The check is empirical and costs nothing extra, because **Stage B's
amplification run is itself the measurement**. Those K attempts per task
are unmodified baseline models generating on the new corpus, so their
first-pass rates are directly comparable to `v03c`'s:

| family | `v03c` oxide first-pass | acceptance band |
|---|---|---|
| qwen | 30.5% | 20.5 – 40.5 |
| codegemma | 16.5% | 6.5 – 26.5 |
| granite | 9.5% | 0 – 19.5 |

±10pp. The relevant precision is that of the *difference* between two
measurements — `v03c` at n = 200 per family per arm and the pilot at
n = 400 (40 tasks × 10 seeds) — which is about 2 SE ≈ 7.2pp at these
rates, dominated by the smaller `v03c` side. A ±10pp band therefore sits
just outside the noise it has to survive, which is what a drift detector
wants; it is deliberately not a significance test.

A family landing outside its band means the corpus drifted in difficulty
and the authoring prompt needs constraining — a re-authoring trigger,
not a result to report. granite's band is asymmetric because its rate
sits near the floor; that is stated rather than hidden.

## The pilot gate

Author **40 tasks** and stop. Four endpoints, all pre-registered here
before any data exists:

| endpoint | threshold | what a miss means |
|---|---|---|
| frontier reference-pair yield | **≥ 90%** (36/40) both references passing the gate | the authoring prompt is producing tasks the language cannot express; constrain it |
| amplification yield | **mean ≥ 4.0** unique verified oxide solutions per task at K = 30 (3 families × 10 seeds, 0-shot, constrained) | raise K rather than lower the program target; report the K actually needed |
| zero-yield tasks | **≤ 30%** of tasks producing no verified oxide solution | the new tasks are harder than t01–t20 for the local models; re-author before scaling |
| difficulty band | all three families inside the bands above | re-author; do not proceed |

The yield thresholds are set below observed values on the eval corpus
(mean 5.7, zeros 20%) so that a pass means "comparable to t01–t20",
while leaving room for new tasks to be modestly harder without tripping
a re-author. The **mean** is the endpoint rather than the median because
the distribution is skewed and a median is unstable at n = 40.

**Each of these can read a value that fails.** That sentence is in this
spec deliberately: two endpoints pre-registered on the g3 branch turned
out to be vacuous — structurally incapable of reading anything but their
predicted value — and the rule learned there is to check falsifiability
*before* the run, not to discover it in the report.

**Pilot cost:** 40 tasks × 10 seeds × 3 families × 2 arms = **2,400
sessions**, comparable to `v03c`'s 1,800 and using the same harness,
grammars and pinned parameters.

Full-corpus target, contingent on the pilot: **~400 tasks at a mean of
~5.7 verified oxide solutions each ≈ 2,300 programs**, with a Rust set
roughly three times larger to be trimmed to a matched token budget. The
5.7 is measured on t01–t20 rather than guessed, but it is measured on
the *eval* corpus — whether new tasks yield the same is exactly what the
pilot tests, and the target adjusts to what the pilot finds rather than
the pilot being adjusted to hit the target.

## Out of scope

No training, no LoRA, no token matching, no evaluation of a fine-tuned
model. No changes to `eval/tasks.jsonl`, `eval/solutions/`, or any
committed campaign under `eval/results/`. The three later specs in this
track are: training infrastructure (a `uv`-managed Python 3.12 venv with
cu128 wheels for the RTX 5080's sm_120 — the project venv is Python
3.14, for which PyTorch ships no wheels); the token-matching
methodology; and the experiment with its own pre-registered endpoints.

## Follow-up this design creates

The deferred demand ledger (`if let`, type-based overloading, `2.to(n)`
ranges, `.set(i, v)`, `unwrap_or`) was recorded "for the fine-tune-era
corpus". Authoring 400 new tasks is the moment those gaps will bite, and
the pilot should report which ledger items its 40 tasks actually
demanded — evidence for v0.4 gathered at no extra cost.

SPEC §0 also notes that the natural moment to revisit the frozen
model-facing card strings is this track, "where the corpus regenerates".
The pilot does not regenerate the eval corpus and so does not reach that
boundary; the cards stay frozen for it.
