# v0.4 Efficiency Cycle Wave 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Census v2 (rejection-crossed + hand-rolled patterns), the
gated wave-2 vocabulary (vectors residual, strings, possible `if let`
and `+=`), re-authoring, and the dynamic loop at restored corpus scale.

**Architecture:** identical rhythm to wave 1, whose artifacts are now
the templates: `eval/demand_census.py` extends, the three-seam builtin
mechanism and `tests/test_v04_builtins.py` / `test_v04_shadowing.py` /
`test_v04_option.py` are the concrete precedents implementers read
first. Syntax sugar (`if let`, `+=`, bracket assignment — whichever the
gate ships) desugars to existing AST with byte-identity tests against
hand-written equivalents (the §55 pattern at tests/test_codegen.py:733).

**Tech Stack / Spec:** as wave 1;
`docs/superpowers/specs/2026-08-28-v04-efficiency-wave2-design.md`
(commit 19e0736c) binds. Suite baseline **1595 passed, 3 deselected**.

## Global Constraints

Same as the wave-1 plan (branch `v04-efficiency-wave1`, pyc mutation
discipline, protected paths with `eval/train/pairs/*/oxide.ox` +
`eval/train/matched/` as Task-7-only work surfaces, identical-stdout
law, ≤ 8 shipped constructs, no verdicts) — plus:
- **Corpus-scale gate:** Task 8's tuned read runs only at ≥ 15k
  supervised tokens per arm in the wave-2 matched corpus.
- Count-verified rsyncs (file counts, never du) for every pod
  preservation step.
- New committed data roots this wave: `eval/results/v04-census2/`,
  `eval/results/v04-amp2/`, `eval/results/v04-campaign2/`.

---

### Task 1: Census v2 — rejection cross-check, `+=` family, hand-rolled patterns

**Files:**
- Modify: `eval/demand_census.py` (extend; existing FAMILIES and
  per-file counting stay byte-compatible — existing tests must pass
  unchanged)
- Modify: `tests/test_demand_census.py` (append)
- Create (generated, committed): `eval/results/v04-census2/REPORT.md` + `census2.json`

**Interfaces (produces):**

```python
COMPOUND_FAMILY = {"compound_assign": {"plus_eq": r"(?<![+\-*/=!<>])\+=", "minus_eq": r"(?<![+\-*/=!<>])-=", "times_eq": r"(?<![+\-*/=!<>])\*="}}
HANDROLLED: dict[str, dict[str, str]]   # pinned structural patterns:
#  "occurrence_count": accumulator += / counter increment inside a for over a vec with an if == guard
#  "removal_rebuild": vec() init + push-in-loop with a skip condition
#  "minmax_scan": sentinel init + comparative reassignment in a for
#  "sum_scan": zero init + additive reassignment in a for
#  "string_build": "" or vec() init + per-char loop over chars(s)
# (pin each as a regex over normalized source; positive+negative fixtures required)
def census_rejection_crossed(campaign_root: Path, arms: tuple[str, ...]) -> dict
#  per (family, spelling, arm): {"present": n_files, "rejected": n_files_where_first_attempt_failed}
#  join: reply file <task>.<harness-arm>.1.txt ↔ the arm's gen-s<seed>/cells.jsonl row for that task
#  (first_compiled False ⇒ rejected). Count file-level, both numbers.
def census_handrolled_programs() -> dict   # per (pattern, class, source): references (current, re-authored) + v04-amp verified pool
def main2(argv=None) -> int  # writes census2.json + REPORT.md: presence AND rejection-crossed columns side by side; hand-rolled tables; ranked by REJECTION-CROSSED demand; no recommendations
```

Data roots: replies + cells from `eval/results/v04-campaign/` (4 arms)
and `eval/results/v04-amp/raw` + `eval/results/v04-amp/runs-*`
(joinable the same way — amp raw layout is `<size>-ox/gen-s<seed>/raw`
with triples under `runs-<size>/amp-<short>-s<seed>/`; read
`collect_verified`'s row shape for pass/fail). References via
`eval.train_corpus.load_train_programs`; amplified pool via
`collect_verified` over the committed `eval/results/v04-amp/runs-*`.

- [ ] Steps follow the wave-1 Task-1 shape exactly: failing tests
  first (positive AND negative fixtures per new pattern; a
  rejection-cross fixture with a synthetic cells.jsonl proving the
  join uses first_compiled; an acceptance pin on ONE hand-verified
  committed cell — hand-verify with grep + a python recount and pin
  the exact number); implement; run
  `.venv/bin/python -m eval.demand_census --v2` (or `main2` CLI —
  match the module's existing CLI convention); mutation checks
  (per-occurrence flip, join-ignores-cells mutation → rejection ==
  presence, pin off-by-one); full suite green; commit
  `feat: census v2 — rejection-crossed demand + hand-rolled patterns`.

**STOP condition:** if the reply↔cells join cannot be made reliable
(e.g. cells lack the linkage), report BLOCKED with the evidence — do
not ship presence-only numbers labeled as rejection-crossed.

---

### Task 2: CENSUS GATE v2 (controller)

Controller reads census2 REPORT and rules the slate (≤ 8): vectors
residual surface (builtin `remove_at`/`count` vs bracket-assign syntax
— rejection-crossed bracket demand decides), strings builtins (top
hand-rolled patterns only), `if let` (ships iff rejection-crossed
demand sustains the 89-level signal), `+=` family (iff
rejection-crossed confirms). Spellings by dominant measured form.
Ruling pasted into Tasks 3–5 dispatches; ledgered with counts.

---

### Task 3: Gated vec builtins (`count`, `remove_at`, possibly `first`/`last`)

Mirror `tests/test_v04_builtins.py` + the three seams exactly (read
Task-3-wave-1's shipped code as the template — it is IN the tree).
Modes: `count`/`first`/`last` read; `remove_at` consumes (own), OOB
mirrors `get`'s contract. Transpiles in the preamble style. Method
forms + BUILTIN_METHOD_NAMES + parser-sync test. Shadowing tests per
construct. Stdout CASES with hand-computed expectations + diagnostics
(existing OX codes) + mutation checks (core-line breaks; ownership
flag flip caught by use-after-move test). Full suite green; commit.

### Task 4: Gated syntax sugar (`+=` / `if let` / bracket-assign — whichever ships)

Each is parser-level sugar desugaring to existing AST (`x += e` →
`x = x + e`; `if let Some(p) = e {A}` → `match e { Some(p) => {A},
None => {} }` — check the parser's existing match-AST shape and any
else-branch requirement first; bracket-assign `v[i] = x` →
`v = set(v, i, x)` ONLY if the gate shipped a `set` builtin this wave,
else bracket-assign cannot ship — the gate ruling must be internally
consistent and Task 2 enforces that). For each shipped sugar:
byte-identity test transpiling the sugar and its hand-written
desugared twin to identical Rust (the §55 pattern); stdout tests;
diagnostics for malformed forms using existing codes where the
machinery allows; mutation checks (desugar binding broken → stdout
test fails; byte-identity broken → identity test fails). Lexer changes
(`+=` token) must include the lexer unit tests distinguishing `+=`
from `+` and `=`. Full suite green; commit per construct or as one
batch commit — implementer's call, disclosed.

### Task 5: Gated strings builtins

Same three-seam mechanism; Str is not linear (read how existing Str
builtins declare modes — `str_len`/`chars`/`concat` are the
templates). Transpile via support fns on the codebase's Str
representation. Tests mirror wave-1 Option/builtin test files: stdout
CASES incl. empty-string and empty-separator edges (pin the chosen
semantics in the tests and record them — e.g. `split("", ",")`,
`join(vec(), ",")`), diagnostics, shadowing, mutations. Full suite
green; commit.

### Task 6: Card v0.4.1 + SPEC §59

Mirror wave-1 Task 6 exactly: both cards, matched-length tolerance
unwidened, `wc -w` before/after recorded; SPEC gains a dated §59
amendment (new constructs table, sugar desugar rules, census-v2
deferral counts, corpus-scale gate record); stale-text sweeps for
anything the sugar contradicts (grep for "no compound assignment" /
"if let" mentions in SPEC and the taxonomy docs; amend non-silently).
test_cards pins re-pinned non-silently if tripped. Full suite; commit.

### Task 7: Re-author references + rebuild + static endpoints

Same bias rules and procedure as wave-1 Task 7 (substitution-only,
Rust untouched, stdout frozen, validate_pair + contamination +
`python -m eval.token_match` rebuild, amplified pins may not move).
Now includes strings-class string-vocabulary substitutions and the
vectors-residual constructs. Endpoint read against the wave-2 targets
(overall ≤ 1.05, vectors ≤ 1.15, strings ≤ 1.08, arithmetic ≤ 1.02
iff `+=` shipped else 1.038 ± 0.02, structs ≤ 1.00). Record
hit/miss; complete regardless; STOP only on guard-rail breaks. The
hand-rolled census (Task 1's instrument) re-runs over the re-authored
references and its scan counts land in the commit body (expected ≈ 0
for substituted patterns — the census proves the re-author). Commit
with the per-class table.

### Task 8: EXECUTION — dynamic loop at restored scale (controller-inline)

Pod runbook as wave 1 (all recorded lessons; count-verified rsyncs).
Sequence: bases + ggufs → **fresh amplification with card v0.4.1 at 3
sizes × 20 seeds** into `/workspace/v04-amp2` → pool with the
committed `eval/results/v04-amp` verified programs → re-match →
**CORPUS-SCALE GATE: proceed to training only at ≥ 15k supervised
tokens/arm** (else raise seeds and re-amplify; if still short after
+20 more seeds, STOP and report) → retrain both 7B arms → 4-arm
campaign (base-ox-7 card-v0.4.1, base-rs-7 control, tune-ox-7-v2b,
tune-rs-7-v2b) → G1 (control ±0.10 of 0.565; tune-ox floor 0.455 MET)
→ G2 uptake censuses (card arm from amp2 raw; tuned arm from campaign
raw; rejection-crossed variants too) → count-verified rsync → teardown
→ zero-pods ×2 → spend. Budget ceiling $10.

### Task 9: Wave-2 report + feed-forward

`eval/results/v04-campaign2/REPORT.md`: full endpoint tables (static
vs targets with HIT/MISS; G1 with the floor met-or-diagnosed; G2 per
construct incl. rejection-crossed; efficiency ratio vs 1.13; corpus
scale achieved; spend), the hand-rolled-census proof of re-authoring,
and the feed-forward (wave-3 candidates, instrument gaps, cross-wave
goal distance). Full suite; commit; push.

---

## Self-Review Notes

- Task 4's bracket-assign consistency rule (needs a `set` builtin in
  the same slate) is enforced at the Task 2 gate, restated in Task 4.
- Census v2 keeps wave-1 functions byte-compatible; wave-1 tests are
  the regression net.
- The corpus-scale gate is the wave's one hard STOP besides guard-rail
  breaks; everything else records and continues.
