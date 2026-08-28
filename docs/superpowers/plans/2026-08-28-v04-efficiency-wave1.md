# v0.4 Efficiency Cycle Wave 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the wave-1 vocabulary (vec builtins, ranges, Option
ergonomics — census-confirmed), re-author the oxide references, and
read the pre-registered token-efficiency endpoints with pass-rate and
uptake guards.

**Architecture:** A census instrument first (its committed report
finalizes the slate at a controller gate); then compiler work through
the established builtin/grammar seams (`BUILTINS` registry in
`src/sema/types.py:99`, support preamble + flags in
`src/codegen/support.py`, parser packages for syntax); then card,
re-authoring + corpus rebuild, the static endpoint read, and the
RunPod dynamic loop.

**Tech Stack:** Python 3.14 `.venv`, pytest (baseline **1552 passed,
3 deselected**), rustc as oracle; RunPod for Task 8 only.

**Spec:** `docs/superpowers/specs/2026-08-28-v04-efficiency-wave1-design.md`
(commit 77e4b6f). The plan argues from the spec; executors read both.
The spec's targets, guards, caps, and bias-control rules bind every
task below.

## Global Constraints

- Branch `v04-efficiency-wave1` (stacked on `finetune-experiment`);
  commit per task; push at task ends.
- `.venv/bin/pytest` from repo root; **mutation discipline** with the
  pyc preamble before every mutated AND restored run:
  `export PYTHONDONTWRITEBYTECODE=1` and
  `find . -name __pycache__ -type d -prune -exec rm -rf {} +`.
- Protected read-only: `eval/tasks.jsonl`, `eval/solutions/`,
  `eval/probes.jsonl`, everything under `eval/results/`. NOTE the
  difference from prior plans: `eval/train/pairs/*/oxide.ox` and the
  matched-corpus rebuild are THIS plan's designated work surface
  (Task 7 only); `eval/train/tasks.jsonl` and all `rust.rs` references
  remain read-only everywhere.
- Language changes must keep the identical-stdout law (oxide and rust
  references produce byte-identical output) and fail-closed
  diagnostics; transpiled Rust compiles warning-clean.
- Every new construct gets receiver-first method syntax for free via
  the existing builtin mechanism (§53) — verify per construct, do not
  reimplement.
- Wave cap: at most 8 shipped constructs. The census gate (Task 2)
  finalizes the slate; implementation tasks 3–5 build ONLY the
  gated slate.
- No terminal verdicts anywhere: reports end with feed-forward
  sections.

---

### Task 1: Demand census instrument and committed report

**Files:**
- Create: `eval/demand_census.py`
- Create: `tests/test_demand_census.py`
- Create (generated, committed): `eval/results/v04-census/REPORT.md` and `census.json`

**Interfaces:**
- Consumes: raw replies under `eval/results/runpod-exp/*/gen-s*/raw/*.txt`
  (filename shape `<task>.<arm>.<attempt>.txt`); reference/amplified
  program sources via `eval.train_corpus.load_train_programs` and
  `eval.token_match.load_matched_inputs`.
- Produces:

```python
FAMILIES: dict[str, dict[str, str]]
# {family: {spelling_name: regex}} — pinned pattern definitions, e.g.
# "ranges": {"dotdot": r"\bin\s+\w+\s*\.\.\s*\w+", "range_call": r"\brange\s*\(",
#            "to_method": r"\.\s*to\s*\(\s*\w+\s*\)"}
# "sort":   {"method": r"\.\s*sort\s*\(", "free": r"\bsort\s*\("}
# "minmax": {"method": r"\.\s*(min|max)\s*\(", "free": r"\b(min|max)\s*\("}
# "sum":    {"method": r"\.\s*sum\s*\(", "free": r"\bsum\s*\("}
# "index_assign": {"bracket": r"\w+\s*\[\s*\w+\s*\]\s*=[^=]", "set_method": r"\.\s*set\s*\("}
# "contains": {"method": r"\.\s*contains\s*\("}
# "option": {"if_let": r"\bif\s+let\s+Some", "unwrap_or": r"unwrap_or\s*\(", "question": r"\)\s*\?"}
# "strings": {"split": r"\.\s*split\s*\(", "join": r"\.\s*join\s*\(", "format": r"\bformat!\s*\("}
def census_replies(root: Path, arms: tuple[str, ...]) -> dict   # counts per (family, spelling, arm)
def census_programs() -> dict                                    # counts per (family, spelling, source: reference|amplified, class)
def main(argv=None) -> int    # writes census.json (sort_keys, no timestamps) + REPORT.md tables
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_demand_census.py
"""The census counts what the pinned patterns define — nothing else.

Synthetic fixtures pin each family's regex against positive AND
negative examples; the acceptance test pins one hand-verified count
from the committed campaign replies so pattern drift fails loudly.
"""
from pathlib import Path

from eval.demand_census import FAMILIES, census_replies


def test_families_cover_the_spec_slate():
    assert {"ranges", "sort", "minmax", "sum", "index_assign",
            "contains", "option", "strings"} <= set(FAMILIES)


def test_range_patterns_positive_and_negative(tmp_path):
    raw = tmp_path / "base-ox-7" / "gen-s1" / "raw"
    raw.mkdir(parents=True)
    (raw / "t01.oxide.1.txt").write_text(
        "for i in 0..10 {\n}\nfor x in range(0, 5) {\n}\nlet y = a.to(n)\n",
        encoding="utf-8")
    (raw / "t02.oxide.1.txt").write_text(
        "let z = 1.5\nprint(z)\n", encoding="utf-8")  # a float is not a range
    counts = census_replies(tmp_path, ("base-ox-7",))
    assert counts["ranges"]["dotdot"]["base-ox-7"] == 1
    assert counts["ranges"]["range_call"]["base-ox-7"] == 1
    assert counts["ranges"]["to_method"]["base-ox-7"] == 1


def test_index_assign_excludes_comparison(tmp_path):
    raw = tmp_path / "a" / "gen-s1" / "raw"
    raw.mkdir(parents=True)
    (raw / "t01.oxide.1.txt").write_text(
        "v[i] = 5\nif v[i] == 5 {\n}\n", encoding="utf-8")
    counts = census_replies(tmp_path, ("a",))
    assert counts["index_assign"]["bracket"]["a"] == 1  # the == line must not count


def test_acceptance_pin_on_committed_replies():
    counts = census_replies(Path("eval/results/runpod-exp"),
                            ("base-ox-7",))
    # Hand-verify ONE cell before pinning: grep the base-ox-7 raw dir for
    # the range_call pattern, count files by hand, and pin the number here.
    # The assertion below is a placeholder SHAPE — replace NNN with the
    # hand-verified count in Step 3 and record the verification command
    # in your report. A pin that was never hand-verified is not a pin.
    assert counts["ranges"]["range_call"]["base-ox-7"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_demand_census.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.demand_census'`

- [ ] **Step 3: Implement, then harden the acceptance pin**

Implement `eval/demand_census.py` per the interface block (counting is
per-file: a pattern family counts at most once per spelling per reply
file for replies, and once per program for program sources — burstiness
inside one reply must not inflate demand). Then hand-verify one
committed cell (`grep -rlE '<range_call regex>' eval/results/runpod-exp/base-ox-7/*/raw | wc -l`),
replace the `> 0` assertion with the exact count, and record the
verification command + count in your report.

`census_programs()` counts over reference and amplified sources from
`load_matched_inputs()` (read-only), tagged by task class. `main()`
writes `eval/results/v04-census/census.json` (sort_keys, no
timestamps) and a `REPORT.md` with: per-family spelling counts for
model replies (oxide arms only, per arm), per-class hand-rolled
pattern counts for programs, and a ranked table (family, total demand,
dominant spelling). No recommendations in the report — the ranking is
data; the gate (Task 2) decides.

- [ ] **Step 4: Run tests, run the census, commit**

Run: `.venv/bin/pytest tests/test_demand_census.py -v` (all PASS),
then `.venv/bin/python -m eval.demand_census`, sanity-read REPORT.md
(every family present; counts plausible against the Step-3 hand
check).

- [ ] **Step 5: Mutation-check** (pyc preamble each run)

1. Make per-file counting per-occurrence (count every match):
   `test_range_patterns_positive_and_negative` must FAIL (a file with
   one spelling twice would double-count — extend the fixture with a
   duplicate line first if needed to make the mutation visible).
2. Break the `index_assign` negative guard (drop the `[^=]`):
   `test_index_assign_excludes_comparison` must FAIL.
3. Change the pinned acceptance count by 1: acceptance test must FAIL.

- [ ] **Step 6: Commit**

```bash
git add eval/demand_census.py tests/test_demand_census.py eval/results/v04-census/
git commit -m "feat: v0.4 demand census — pinned patterns over campaign replies and corpus"
```

---

### Task 2: CENSUS GATE (controller, not a subagent)

The controller reads `eval/results/v04-census/REPORT.md` and rules,
in the ledger, for each provisional construct: SHIP (with the
census-dominant spelling), CUT (below-threshold demand), or DEFER
(recorded for wave 2). The slate must respect the spec's cap (≤ 8).
`if let` ships only on material demand per the spec. The ruling names
the exact surface spelling for ranges. Tasks 3–5 build only the gated
slate; their briefs get the gate's ruling pasted in as their slate.

---

### Task 3: Vec builtins (gated subset of: sort, min, max, sum, contains, set)

**Files:**
- Modify: `src/sema/types.py` (the `BUILTINS` dict at line 99 — one
  `BuiltinSig` per construct; read `push` at line 104 and `get`/`len`
  as the templates for consuming vs reading modes)
- Modify: `src/codegen/support.py` (support-function preamble — read
  `fn push<T>` at line 44 and the flags table at line 164; add one
  support fn + flags row per construct, mirroring the table's
  semantics for existing entries)
- Modify: `src/codegen/rust.py` only if a construct needs call-site
  emission beyond the generic builtin path (read how `push`/`get`
  emit first; expected: no change needed)
- Test: `tests/test_v04_builtins.py` (new)

**Interfaces:**
- Consumes: the Task 2 gate ruling (the slate + spellings).
- Produces: the shipped builtins, each accepting free-call AND
  receiver-first method form; ownership modes: `sort`/`set` consume
  and return (like `push`); `min`/`max`/`sum`/`contains` read (like
  `len`/`get`). Transpile mapping per the spec's table; `min`/`max`
  return `Option<T>` (empty → `None`); `set` mirrors `get`'s
  out-of-bounds contract exactly (read `get`'s support fn first and
  copy its behavior class).

- [ ] **Step 1: Write the failing tests** — verbatim programs, one
  compile-and-run stdout test per construct plus edge cases, following
  the pattern of
  `tests/test_codegen.py::test_variadic_vec_literal_runtime_stdout_matches_the_push_chain`
  (compile via the same helper that test uses; read it first):

```python
# tests/test_v04_builtins.py — programs are the spec; adjust ONLY
# spellings per the Task 2 gate ruling.
CASES = [
    # (name, oxide_source, expected_stdout)
    ("sort_basic",
     'fn main() {\n    let v = vec(9, 2, 7, 4)\n    let s = sort(v)\n    for x in s {\n        print(x)\n    }\n}\n',
     "2\n4\n7\n9\n"),
    ("sort_method_chain",
     'fn main() {\n    for x in vec(3, 1, 2).sort() {\n        print(x)\n    }\n}\n',
     "1\n2\n3\n"),
    ("min_some",
     'fn main() {\n    match min(vec(5, 3, 8)) {\n        Some(m) => print(m),\n        None => print_str("empty"),\n    }\n}\n',
     "3\n"),
    ("min_empty_is_none",
     'fn main() {\n    let v = vec()\n    let w = push(v, 1)\n    let e = vec()\n    match min(e) {\n        Some(m) => print(m),\n        None => print_str("empty"),\n    }\n    print(len(w))\n}\n',
     "empty\n1\n"),
    ("max_basic",
     'fn main() {\n    match max(vec(5, 3, 8)) {\n        Some(m) => print(m),\n        None => print_str("empty"),\n    }\n}\n',
     "8\n"),
    ("sum_basic",
     'fn main() {\n    print(sum(vec(1, 2, 3, 4)))\n}\n',
     "10\n"),
    ("sum_empty_is_zero",
     'fn main() {\n    let e = vec()\n    let f = push(e, 1)\n    print(len(f))\n    let g = vec()\n    print(sum(g))\n}\n',
     "1\n0\n"),
    ("contains_true_false",
     'fn main() {\n    let v = vec(1, 2, 3)\n    print(contains(v, 2))\n    print(v.contains(9))\n}\n',
     "true\nfalse\n"),
    ("set_replaces",
     'fn main() {\n    let v = vec(1, 2, 3)\n    let w = set(v, 1, 9)\n    for x in w {\n        print(x)\n    }\n}\n',
     "1\n9\n3\n"),
    ("set_consumes_receiver",
     # after set(v, ...) the original v is moved — using it again must
     # produce the ownership diagnostic, not compile. This case goes in
     # the DIAGNOSTIC list below, not here.
     None, None),
]
```

  Plus a diagnostics list (compile-must-fail with the expected OX code,
  following the existing diagnostic-test pattern in the suite — find
  one that asserts an OX0400-class code and mirror it): use-after-move
  of `sort`/`set` receivers; `sum` on a non-Int vec (type error);
  `contains` arity error. Plus one ownership-consistency test: sum/len
  style readers do NOT move their argument (call `sum(v)` then
  `len(v)` — compiles, runs).

  Empty-vec literals in fixtures may need usage context for inference
  (the card notes `vec()` "needs usage context to infer T") — the
  fixtures above thread a `push` after each bare `vec()` for exactly
  that reason. The `min_empty_is_none` fixture's `e` has only
  `min(e)` as context; if inference cannot bind `T` there, adapt the
  fixture using the codebase's established empty-vec idiom (see the
  inference tests in `tests/test_linear.py`, e.g. around
  `test_s1_both_vec_bindings_infer_vec_int`) and record the
  adaptation in your report — the assertion (empty → the None arm
  prints) must survive unchanged.

- [ ] **Step 2: Run to verify failures** (unknown-builtin diagnostics),
  **Step 3: implement** through the three seams (signatures → support
  fns + flags → verify method syntax needs no extra work),
  **Step 4: all tests green + full suite green**,
- [ ] **Step 5: Mutation-check** (pyc preamble): break each support
  fn's core line (e.g. `sort` → no-op, `min` → `max`, `set` ignores
  the index, `contains` returns `!result`, `sum` off-by-one init):
  the matching stdout test must FAIL; restore each. Break one
  ownership flag (make `sort` non-consuming): the use-after-move
  diagnostic test must FAIL.
- [ ] **Step 6: Commit** `feat: v0.4 vec builtins — <gated list>`

---

### Task 4: Ranges (gated spelling; provisional `a..b`)

**Files:**
- Modify: `src/lexer/tokens.py` + `src/lexer/lexer.py` (a `..` token —
  check interaction with float literals and the existing `.` method
  token; the lexer must keep `1.5` a float and `a..b` a range)
- Modify: `src/parser/expressions.py` / `src/parser/ast.py` (range
  expression node; precedence per the census spelling — read how
  existing binary operators register)
- Modify: `src/sema/` (type: `Int .. Int` yields an iterable-of-Int
  usable ONLY as a `for` header iterable this wave — a chosen scope
  limit; anywhere else → new diagnostic, fail closed, next free OX
  code in the parser/sema's numbering convention — read
  `src/diagnostics.py` for the allocation pattern)
- Modify: `src/codegen/rust.py` (emit `a..b` in the for-header
  position)
- Test: `tests/test_v04_ranges.py`

Test cases (verbatim; spelling adjusted only per the gate):

```python
CASES = [
    ("range_for",
     'fn main() {\n    for i in 0..4 {\n        print(i)\n    }\n}\n',
     "0\n1\n2\n3\n"),
    ("range_exprs_as_bounds",
     'fn main() {\n    let n = 3\n    for i in 1..n + 1 {\n        print(i)\n    }\n}\n',
     "1\n2\n3\n"),
    ("float_still_lexes",
     'fn main() {\n    print_str("ok")\n}\n',   # plus a lexer unit test asserting 1.5 lexes as one float token and 0..4 as Int, DOTDOT, Int
     "ok\n"),
]
```

Diagnostics: a range outside a for-header (e.g. `let r = 0..4`) must
produce the new fail-closed diagnostic; a non-Int bound must produce a
type diagnostic. Mutation checks: off-by-one the emitted upper bound →
`range_for` FAILS; drop the outside-for-header guard → its diagnostic
test FAILS. Commit `feat: v0.4 ranges — <spelling> in for headers`.

---

### Task 5: Option ergonomics (`unwrap_or`; `if let` only if gated in)

`unwrap_or(o, d) -> T` as a builtin through the same three seams
(reads its Option, returns the inner value or the default; transpile
`o.unwrap_or(d)`). Tests (same file pattern, `tests/test_v04_option.py`):
Some-path, None-path, method form, arity/type diagnostics, and a
non-consuming read check (`unwrap_or(o, 0)` then `match o` still
compiles — verify against how `get` treats its Option-producing reads;
if Option reads are consuming in the existing semantics, mirror the
existing convention and record which one holds in your report).

`if let` (ONLY if the Task 2 gate ships it): grammar sugar in
`src/parser/parser.py` desugaring to the existing single-arm `match`
AST — no new sema or codegen if the desugar is faithful; tests assert
byte-identical transpiled Rust between `if let` source and its
hand-written `match` equivalent (the §55 byte-identity pattern at
`tests/test_codegen.py:733`). Mutation: break the desugar's binding →
stdout test FAILS. Commit per the gate's slate.

---

### Task 6: Card v0.4 + SPEC amendment

**Files:** Modify `LANGUAGE_CARD.md` (new constructs in the Builtins
section + one Syntax essentials line for ranges, matching the card's
existing voice and brevity); append a dated amendment to `SPEC.md`
(the §0 card freeze lifts here, per the design spec; record old/new
card word counts); update `tests/test_cards.py` if it pins card
content (read it first — if it pins byte-hashes or word counts, update
the pins in the same commit, non-silently).

Steps: edit → `wc -w` before/after recorded in the SPEC amendment →
full suite green (card-dependent tests updated) → commit
`docs: card v0.4 — wave-1 vocabulary; SPEC freeze lift recorded`.

---

### Task 7: Re-author oxide references, rebuild the corpus, read the static endpoints

**Files:** Modify `eval/train/pairs/*/oxide.ox` ONLY (the designated
work surface; every `rust.rs` byte-identical); regenerate
`eval/train/matched/` via the committed builder; update
`tests/test_token_match_corpus.py` acceptance pins ONLY as the
non-silent re-pin this task's commit message documents (the counts
change because programs change — state old→new in the commit body).

- [ ] Re-author under the spec's bias rules: substitution-only edits
  where a shipped construct replaces its hand-rolled pattern (n041's
  selection sort → `sort`; hand-rolled min/max/sum scans; index
  rebuild loops → `set`; counter loops → ranges; Option matches with
  constant fallbacks → `unwrap_or`). Every pair re-validated
  (`validate_pair`), stdout byte-identical to before (the task's
  expected_stdout is frozen — a re-authored program that changes
  stdout is WRONG, fix it).
- [ ] Contamination guard green; `python -m eval.token_match` rebuild;
  amplified programs are unchanged inputs (they still validate — they
  don't use the new vocabulary; that asymmetry is measured, not
  hidden: the manifest's reference vs amplified efficiency sections
  will diverge and the wave report says why).
- [ ] **Static endpoint read** (the primary): recompute the reference
  ratios from the new manifest; compare against the spec's targets
  (overall ≤ 1.10, vectors ≤ 1.15, structs ≤ 1.00, arithmetic
  1.04 ± 0.05). **Whatever the numbers say, they are recorded and the
  task completes** — a missed target is a wave finding for the gate
  in Task 9's report, not a reason to iterate re-authoring past the
  bias rules. STOP only if a guard-rail broke (stdout drift,
  contamination hit, validate_pair failure).
- [ ] Full suite green; commit
  `feat: v0.4 re-authored references + rebuilt matched corpus — static endpoints read`
  with the per-class before→after table in the commit body.

---

### Task 8: EXECUTION — the dynamic loop on RunPod (controller-inline)

Procedure (budget ceiling $10, chosen in the spec; the runbook,
scripts, and ops gotchas from the wave-0 evidence file apply —
nvcc off PATH, nginx owns 8081, PUBLIC_KEY baked into pod env,
bracket-pattern pgrep):

1. Pod up (24GB class), setup, pull branch. Convert nothing — reuse
   wave-0 ggufs? NO: `base-7.q8_0.gguf` must be REBUILT only if the
   card changed affects nothing served (it does not — the card is
   prompt-side). Rebuild only `tune-ox-7(v2)`: re-amplify FIRST.
2. **Re-amplify** with card-v0.4 (the committed amplification
   machinery, K=30, qwen-7b family, oxide+rust arms, new run root
   `eval/results/v04-amp/`): the oxide outputs are the card-arm G2
   uptake read — run `eval/demand_census.py` patterns over them and
   record per-construct uptake counts.
3. Re-match (builder over the wave-1 corpus + v04-amp), **re-tune
   tune-ox-7 only** (train_lora, same recipe — epoch parity binds),
   merge/convert/quantize, smoke.
4. Campaign, 4 arms, fresh results root `eval/results/v04-campaign/`:
   `base-rs-7` (control band: pass@1 within ±0.10 of 0.565),
   `base-ox-7` (card-v0.4), `tune-ox-7-v2`, `tune-rs-7` (wave-0 gguf,
   re-served). G1 floor: tune-ox-7-v2 pass@1 ≥ 0.455. G2: census
   patterns over the tuned arm's raw replies — every shipped
   construct's uptake counted.
5. Rsync everything home; terminate pod; verify 0 pods twice; record
   spend. Control-band breach = infrastructure diagnosis first, per
   the wave-0 precedent (diagnose, rule, record — never reinterpret).

---

### Task 9: Wave-1 report and feed-forward

Write `eval/results/v04-campaign/REPORT.md` (numbers from the
manifest, ENDPOINTS-style computations for the 4 arms via
`eval.experiment_report.gen_metrics`/`strict_repair_rate` where the
layouts match — read only what exists; no interim machinery): the
static endpoint table (targets vs measured, per class), G1/G2 reads,
tokens-to-green ratios, uptake per construct (card arm and tuned arm),
spend, and a **Feed-forward to wave 2** section: strings-class census
ranking, wave-1 failed-uptake constructs with their counts, any target
misses with the mechanism as measured, and the re-amplified corpus's
reference-vs-amplified efficiency divergence. Full suite green;
commit; push. The report ends with the feed-forward section — by
construction there is no verdict paragraph to write.

---

## Self-Review Notes (for the executor)

- Task 1's acceptance pin starts as `> 0` and MUST be hardened to a
  hand-verified exact count in Step 3 — the plan says so twice
  because a soft pin is the instrument's licence going unearned.
- Tasks 3–5 give test programs verbatim but implementation by
  template (the `push`/`get`/§55 seams are named with line numbers)
  — the codebase's own conventions outrank any plan-invented shape,
  and the reviewer checks convention-fit as part of quality.
- Task 7's target read completes regardless of hitting targets; only
  guard-rail breaks stop it. This is the no-verdict discipline in
  plan form.
- Task 8 reuses wave-0 base ggufs (the card is prompt-side); only the
  oxide adapter retrains.
