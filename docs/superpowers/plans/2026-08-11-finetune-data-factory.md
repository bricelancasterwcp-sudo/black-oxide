# Data Factory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the tooling for a compiler-verified Black Oxide + Rust
training corpus on new tasks, then run the 40-task pilot and score its
four pre-registered endpoints.

**Architecture:** One new module (`eval/train_corpus.py`) holding the
corpus loader, the contamination guard, and the Stage A reference-pair
gate. One five-line change to `eval/driver.py` exposing the
already-threaded `tasks_path` as a CLI flag. Then two execution tasks:
author 40 tasks, and run the amplification grid against them.

**Tech Stack:** Python 3.14 (`.venv`), pytest, the existing
`eval.harness` / `eval.driver` / `eval.llamacpp` stack, llama.cpp Vulkan
build `b1-4988f6e`.

**Source spec:** `docs/superpowers/specs/2026-08-11-finetune-data-factory-design.md`

## Global Constraints

- **Frozen surfaces must not be edited:** `LANGUAGE_CARD.md`,
  `LANGUAGE_CARD_EXPLICIT.md`, the `OX0306` suggestion string, the
  `ARMS`/`arm` data keys, the `__oxide_` codegen prefix, `.ox`,
  `eval/grammar/oxide.gbnf`. Editing a card retokenizes every prompt and
  breaks comparability with `v03c`, which this whole track is measured
  against.
- **`eval/tasks.jsonl` and `eval/solutions/` are read-only here.** They
  are the held-out eval. A task that seems to need editing them is a
  BLOCKED report, not a judgment call.
- **Nothing under `eval/results/` may be modified.** Adding a new run
  root is permitted.
- **Training task ids are `n001`…`n040`**, never `tNN`.
- **Rust training programs must never contain `__oxide_`.** A Rust arm
  trained on transpiler output is a strawman and voids the experiment.
- **Never run `git add -A` or `git add .`** Two untracked directories,
  `eval/results/g0-generation-baseline/{constrained,unconstrained}/samples/`,
  predate this work and must stay untracked. Stage explicit paths only.
- Commit messages carry **no Claude/AI attribution**; conventional
  commits.
- Use `.venv/bin/python` and `.venv/bin/pytest`. The suite is **1446
  passed, 3 deselected** at branch point; every task must leave it green.

## What already exists (do not rebuild)

`tasks_path` is **already threaded through the entire driver and
harness** — `harness.load_tasks`, `_get_task`, `build_prompt`,
`run_task`, `new_session`, and `driver.run_grid`,
`driver.preflight_environment`, `driver._run_cell` all accept it. The
only gap is that `driver.main()` never sets it. Task 2 is therefore a
flag and two call-site edits, not a refactor. Do not add a parallel
task-loading path.

`harness.run_file(arm, path, expected_stdout) -> dict` already
transpiles, compiles, runs and compares stdout for all three arms. Task 3
composes it; it does not reimplement it.

## File Structure

| file | responsibility |
|---|---|
| `eval/train_corpus.py` (new) | corpus paths, `normalize_source`, contamination guard, Stage A pair gate |
| `tests/test_train_corpus.py` (new) | all tests for the above, including the guard's boundary cases |
| `eval/driver.py` (modify, ~5 lines) | `--tasks` CLI flag threaded to preflight and `run_grid` |
| `tests/test_6a.py` (modify) | one test that the flag reaches the grid |
| `eval/train/tasks.jsonl` (new, Task 4) | the 40 pilot tasks |
| `eval/train/pairs/` (new, Task 4/5) | verified solutions per task per arm |
| `eval/train/manifest.json` (new, Task 5) | provenance and dedup counts |

---

### Task 1: Corpus module and the contamination guard

**Files:**
- Create: `eval/train_corpus.py`
- Test: `tests/test_train_corpus.py`

**Interfaces:**
- Consumes: `eval.harness.load_tasks` for reading task files.
- Produces: `TRAIN_TASKS_PATH`, `TRAIN_ROOT`, `normalize_source(text)
  -> str`, `Contamination` (frozen dataclass), `contamination_report(
  train_tasks: dict[str, dict], train_programs: dict[str, str]) ->
  tuple[Contamination, ...]`. Tasks 3 and 5 both import from here.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_train_corpus.py
from pathlib import Path

import pytest

from eval import train_corpus as tc

EVAL_T01_OXIDE = Path("eval/solutions/oxide/t01.ox").read_text(encoding="utf-8")


def test_normalize_source_ignores_trailing_space_and_blank_lines():
    a = tc.normalize_source("fn main() {\n\n    print(1)   \n}\n")
    b = tc.normalize_source("fn main() {\n    print(1)\n}")
    assert a == b


def test_clean_corpus_reports_no_contamination():
    tasks = {"n001": {"id": "n001", "prompt": "Print the number of vowels in a fixed word."}}
    programs = {"n001": "fn main() {\n    print(3)\n}\n"}
    assert tc.contamination_report(tasks, programs) == ()


def test_program_identical_to_an_eval_solution_is_flagged():
    tasks = {"n001": {"id": "n001", "prompt": "Something entirely unrelated here."}}
    programs = {"n001": EVAL_T01_OXIDE}
    found = tc.contamination_report(tasks, programs)
    assert [c.kind for c in found] == ["solution"]
    assert found[0].eval_id == "t01"


def test_reformatted_eval_solution_is_still_flagged():
    """The guard must survive cosmetic edits, or it guards nothing."""
    reformatted = "\n\n".join(line + "   " for line in EVAL_T01_OXIDE.split("\n"))
    tasks = {"n001": {"id": "n001", "prompt": "Something entirely unrelated here."}}
    found = tc.contamination_report(tasks, {"n001": reformatted})
    assert [c.kind for c in found] == ["solution"]


def test_prompt_sharing_twelve_words_with_an_eval_task_is_flagged():
    shared = "Print the sum of the squares of the integers 0 through 9."
    assert len(shared.split()) == 12
    found = tc.contamination_report({"n001": {"id": "n001", "prompt": shared}}, {})
    assert [c.kind for c in found] == ["prompt"]
    assert found[0].eval_id == "t01"


def test_prompt_sharing_eleven_words_is_not_flagged():
    """Pins the threshold. Eleven words of overlap is ordinary English."""
    shared = "the sum of the squares of the integers 0 through 9."
    assert len(shared.split()) == 11
    assert tc.contamination_report({"n001": {"id": "n001", "prompt": shared}}, {}) == ()


def test_committed_training_corpus_is_clean():
    """Runs against the real corpus once it exists; skips before Task 4."""
    if not tc.TRAIN_TASKS_PATH.exists():
        pytest.skip("training corpus not authored yet")
    assert tc.contamination_report(tc.load_train_tasks(), tc.load_train_programs()) == ()
```

- [ ] **Step 2: Run them and watch every one fail**

Run: `.venv/bin/pytest tests/test_train_corpus.py -v`
Expected: collection error or 7 failures — `eval.train_corpus` does not exist.

- [ ] **Step 3: Implement the module**

```python
# eval/train_corpus.py
"""Training-corpus loading and the contamination guard.

The guard is what protects the v03c comparison. If any t01-t20 content
reaches the training corpus, a model fine-tuned on it and evaluated on
t01-t20 posts a gain whether or not Black Oxide is easier to learn than
Rust -- which is the entire question the fine-tune track exists to ask.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from eval import harness

_REPO_ROOT = Path(__file__).resolve().parents[1]
TRAIN_ROOT = _REPO_ROOT / "eval" / "train"
TRAIN_TASKS_PATH = TRAIN_ROOT / "tasks.jsonl"
PAIRS_ROOT = TRAIN_ROOT / "pairs"
SOLUTIONS_ROOT = _REPO_ROOT / "eval" / "solutions"

# A shared span this long between a training prompt and an eval prompt is
# copying, not coincidence. Eleven words of overlap is ordinary English;
# tests/test_train_corpus.py pins both sides of this boundary.
NGRAM_WORDS = 12

_SOLUTION_GLOBS = (("oxide", "*.ox"), ("explicit", "*.ox"), ("rust", "*.rs"))


def normalize_source(text: str) -> str:
    """Whitespace-insensitive form used for exact-match comparison."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(line for line in lines if line.strip())


def _word_ngrams(text: str, n: int) -> set[tuple[str, ...]]:
    words = text.split()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


@dataclass(frozen=True, slots=True)
class Contamination:
    train_id: str
    kind: str  # "solution" | "prompt"
    eval_id: str
    detail: str


def _eval_solutions() -> dict[str, str]:
    """Normalised eval solution text -> the task id it solves."""
    found: dict[str, str] = {}
    for arm, pattern in _SOLUTION_GLOBS:
        for path in sorted((SOLUTIONS_ROOT / arm).glob(pattern)):
            found[normalize_source(path.read_text(encoding="utf-8"))] = path.stem
    return found


def contamination_report(
    train_tasks: dict[str, dict],
    train_programs: dict[str, str],
) -> tuple[Contamination, ...]:
    """Every way the training corpus overlaps the held-out eval corpus."""
    hits: list[Contamination] = []
    solutions = _eval_solutions()
    for train_id, source in sorted(train_programs.items()):
        eval_id = solutions.get(normalize_source(source))
        if eval_id is not None:
            hits.append(Contamination(train_id, "solution", eval_id,
                                      "program matches a committed eval solution"))
    eval_tasks = harness.load_tasks()
    eval_ngrams = {tid: _word_ngrams(t["prompt"], NGRAM_WORDS)
                   for tid, t in eval_tasks.items()}
    for train_id, task in sorted(train_tasks.items()):
        mine = _word_ngrams(task["prompt"], NGRAM_WORDS)
        for eval_id, theirs in sorted(eval_ngrams.items()):
            shared = mine & theirs
            if shared:
                hits.append(Contamination(
                    train_id, "prompt", eval_id,
                    f"shares a {NGRAM_WORDS}-word span: "
                    f"{' '.join(sorted(shared)[0])!r}"))
                break
    return tuple(hits)


def load_train_tasks() -> dict[str, dict]:
    return harness.load_tasks(TRAIN_TASKS_PATH)


def load_train_programs() -> dict[str, str]:
    """Every committed training program, keyed by '<task>/<arm>/<file>'."""
    programs: dict[str, str] = {}
    if not PAIRS_ROOT.exists():
        return programs
    for path in sorted(PAIRS_ROOT.rglob("*")):
        if path.is_file() and path.suffix in (".ox", ".rs"):
            programs[str(path.relative_to(PAIRS_ROOT))] = path.read_text(encoding="utf-8")
    return programs
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_train_corpus.py -v`
Expected: 6 passed, 1 skipped (the real-corpus test skips until Task 4).

- [ ] **Step 5: Mutation-verify the guard**

The guard is the one piece of this plan whose failure is silent, so a
passing test is not enough — the g2 branch found eight tests that passed
against deliberately broken implementations. Break it three ways and
confirm a test dies each time:

1. Make `normalize_source` return `text` unchanged →
   `test_reformatted_eval_solution_is_still_flagged` must fail.
2. Set `NGRAM_WORDS = 13` →
   `test_prompt_sharing_twelve_words_with_an_eval_task_is_flagged` must fail.
3. Set `NGRAM_WORDS = 11` →
   `test_prompt_sharing_eleven_words_is_not_flagged` must fail.

Revert each mutation before the next. If any mutation leaves the suite
green, the test that should have caught it is decorative — fix the test,
not the mutation, and record it in the task report.

- [ ] **Step 6: Run the full suite and commit**

```bash
.venv/bin/pytest -q            # green, with 6 new tests passing and 1 skipped
git add eval/train_corpus.py tests/test_train_corpus.py
git commit -m "feat: training-corpus module and the contamination guard

The guard protects the v03c comparison: a fine-tune that had seen t01-t20
would post a gain regardless of whether Black Oxide is easier to learn
than Rust. Exact match on normalised program text against every committed
eval solution, plus a 12-word shared-span check on prompts, with both
sides of that boundary pinned by test.

Mutation-verified: defeating normalisation or moving the threshold one
word in either direction each kills a specific test."
```

---

### Task 2: `--tasks` flag on the driver

**Files:**
- Modify: `eval/driver.py` (`main`, around lines 638-651 and 709-726)
- Test: `tests/test_6a.py`

**Interfaces:**
- Consumes: `driver.run_grid(..., tasks_path=...)` and
  `driver.preflight_environment(shot_counts, tasks_path)`, both of which
  already accept the parameter.
- Produces: `python -m eval.driver --tasks eval/train/tasks.jsonl`,
  used by Task 5.

- [ ] **Step 1: Write the failing test**

```python
def test_driver_tasks_flag_reaches_the_grid(tmp_path, monkeypatch):
    """--tasks must thread to run_grid, or an amplification run would
    silently generate against the held-out eval corpus instead."""
    corpus = tmp_path / "train.jsonl"
    corpus.write_text(
        '{"id": "n001", "title": "T", "difficulty": "intro", '
        '"prompt": "P", "expected_stdout": "1\\n"}\n',
        encoding="utf-8",
    )
    seen = {}

    def fake_run_grid(*args, **kwargs):
        seen["tasks_path"] = kwargs.get("tasks_path")
        return {}

    monkeypatch.setattr(driver, "run_grid", fake_run_grid)
    monkeypatch.setattr(driver, "preflight_environment", lambda *a, **k: [])
    monkeypatch.setattr(driver, "make_arm_clients", lambda *a, **k: _stub_clients())
    driver.main(["--models", "qwen7b", "--seeds", "1", "--shots", "0",
                 "--tasks", str(corpus)])
    assert seen["tasks_path"] == corpus
```

Reuse whatever client stub `tests/test_6a.py` already uses for
`make_arm_clients`; do not invent a new one.

- [ ] **Step 2: Run it and verify it fails**

Run: `.venv/bin/pytest tests/test_6a.py::test_driver_tasks_flag_reaches_the_grid -v`
Expected: FAIL — `unrecognized arguments: --tasks`.

- [ ] **Step 3: Add the flag**

In `main`'s parser, beside `--results-root`:

```python
    parser.add_argument("--tasks", default=None,
                        help="task corpus path (default: eval/tasks.jsonl)")
```

After `args = parser.parse_args(argv)`:

```python
    tasks_path = Path(args.tasks) if args.tasks else None
```

Then pass `tasks_path` to the existing `preflight_environment(...)` call
and add `tasks_path=tasks_path` to the existing `run_grid(...)` call.
Change nothing else — both functions already accept it.

- [ ] **Step 4: Verify, run the suite, commit**

```bash
.venv/bin/pytest tests/test_6a.py -q && .venv/bin/pytest -q
git add eval/driver.py tests/test_6a.py
git commit -m "feat: --tasks flag on the eval driver

tasks_path was already threaded through run_grid, preflight_environment,
new_session and build_prompt; only main() never set it. Without the flag
an amplification run would generate against the held-out eval corpus."
```

---

### Task 3: Stage A reference-pair gate

**Files:**
- Modify: `eval/train_corpus.py`
- Test: `tests/test_train_corpus.py`

**Interfaces:**
- Consumes: `harness.run_file(arm, path, expected_stdout) -> dict` (the
  returned dict's `passed` key is the verdict), and `normalize_source`
  from Task 1.
- Produces: `validate_pair(task, oxide_path, rust_path) -> dict` with
  keys `ok: bool`, `reasons: tuple[str, ...]`. Task 4 gates on it.

- [ ] **Step 1: Write the failing tests**

```python
def test_validate_pair_accepts_agreeing_references(tmp_path):
    task = {"id": "n001", "expected_stdout": "3\n"}
    ox = tmp_path / "n001.ox"; ox.write_text("fn main() {\n    print(3)\n}\n")
    rs = tmp_path / "n001.rs"; rs.write_text("fn main() {\n    println!(\"3\");\n}\n")
    assert tc.validate_pair(task, ox, rs)["ok"] is True


def test_validate_pair_rejects_rust_containing_the_oxide_prefix(tmp_path):
    """Transpiler output as Rust training data makes the control a
    strawman; this is the check that makes that impossible."""
    task = {"id": "n001", "expected_stdout": "3\n"}
    ox = tmp_path / "n001.ox"; ox.write_text("fn main() {\n    print(3)\n}\n")
    rs = tmp_path / "n001.rs"
    rs.write_text("fn __oxide_helper() {}\nfn main() {\n    println!(\"3\");\n}\n")
    result = tc.validate_pair(task, ox, rs)
    assert result["ok"] is False
    assert any("__oxide_" in r for r in result["reasons"])


def test_validate_pair_rejects_arms_that_disagree(tmp_path):
    task = {"id": "n001", "expected_stdout": "3\n"}
    ox = tmp_path / "n001.ox"; ox.write_text("fn main() {\n    print(3)\n}\n")
    rs = tmp_path / "n001.rs"; rs.write_text("fn main() {\n    println!(\"4\");\n}\n")
    result = tc.validate_pair(task, ox, rs)
    assert result["ok"] is False
```

Note for the implementer: Black Oxide's `print()` quotes strings, so
`print(3)` emits `3\n` while `print("3")` emits `"3"\n`. Use integer
prints in these fixtures.

- [ ] **Step 2: Run and verify failure**

Run: `.venv/bin/pytest tests/test_train_corpus.py -k validate_pair -v`
Expected: 3 failures — `validate_pair` does not exist.

- [ ] **Step 3: Implement**

```python
OXIDE_PREFIX = "__oxide_"


def validate_pair(task: dict, oxide_path: Path, rust_path: Path) -> dict:
    """Gate one Stage A reference pair.

    Both arms must compile, run, and match the task's expected_stdout --
    which also proves they agree with each other. The Rust reference must
    not contain the reserved codegen prefix: a Rust arm trained on
    transpiler output is a handicapped control, and the Black Oxide
    advantage it would produce is an artifact.
    """
    reasons: list[str] = []
    rust_text = rust_path.read_text(encoding="utf-8")
    if OXIDE_PREFIX in rust_text:
        reasons.append(f"rust reference contains the reserved {OXIDE_PREFIX!r} "
                       f"prefix -- transpiler output is not idiomatic Rust")
    expected = task["expected_stdout"]
    for arm, path in (("oxide", oxide_path), ("rust", rust_path)):
        verdict = harness.run_file(arm, path, expected)
        if not verdict.get("passed"):
            reasons.append(f"{arm} reference did not pass: "
                           f"{verdict.get('stage') or verdict.get('error') or 'output mismatch'}")
    return {"ok": not reasons, "reasons": tuple(reasons)}
```

Check `harness.run_file`'s actual return keys before finalising the
failure message; use what it really returns, not what this snippet
guesses.

- [ ] **Step 4: Verify, run the suite, commit**

```bash
.venv/bin/pytest tests/test_train_corpus.py -q && .venv/bin/pytest -q
git add eval/train_corpus.py tests/test_train_corpus.py
git commit -m "feat: Stage A reference-pair gate

Both arms must compile, run and match expected_stdout, which also proves
they agree. Rust references containing __oxide_ are rejected outright."
```

---

### Task 4: Author the 40-task pilot corpus

**Files:**
- Create: `eval/train/tasks.jsonl` (40 records, ids `n001`…`n040`)
- Create: `eval/train/pairs/<task>/oxide.ox`, `.../rust.rs`

**Interfaces:**
- Consumes: `train_corpus.validate_pair`, `train_corpus.contamination_report`.
- Produces: the corpus Task 5 amplifies.

- [ ] **Step 1: Author in four independent batches of ten**

Batch separately, with different domain seeds, so prompts do not
converge on one phrasing — this reduces near-duplicates but does **not**
make the corpus multi-author, and the report must not claim it does.

Cover the same span t01–t20 covers: arithmetic and loops, vectors,
strings, structs and Options. Black Oxide has **no** generics, traits,
closures, modules, tuples, indexing syntax, or sized integer types — a
task requiring any of those cannot be expressed and must not be authored.

Each record: `{"id": "n0NN", "title": ..., "difficulty": ...,
"prompt": ..., "expected_stdout": ...}` — the same schema as
`eval/tasks.jsonl`.

- [ ] **Step 2: Gate every pair, discard failures**

```bash
.venv/bin/python -c "
from pathlib import Path
from eval import train_corpus as tc
tasks = tc.load_train_tasks()
bad = []
for tid, task in sorted(tasks.items()):
    d = tc.PAIRS_ROOT / tid
    r = tc.validate_pair(task, d / 'oxide.ox', d / 'rust.rs')
    if not r['ok']:
        bad.append((tid, r['reasons']))
print(f'{len(tasks) - len(bad)}/{len(tasks)} pairs pass')
for tid, reasons in bad: print(' ', tid, reasons)
"
```

**Discard a failing task; do not repair it into passing.** A massaged
task is a task the language could not express, kept anyway.

- [ ] **Step 3: Verify the contamination guard on the real corpus**

Run: `.venv/bin/pytest tests/test_train_corpus.py::test_committed_training_corpus_is_clean -v`
Expected: PASS, no longer skipped. If it fails, the named task must be
re-authored — this is not overridable.

- [ ] **Step 4: Record endpoint 1 and commit**

Endpoint 1 is **reference-pair yield ≥ 90%** (36 of 40). Record the
actual figure in the commit message whether it passes or misses.

```bash
git add eval/train/tasks.jsonl eval/train/pairs
git commit -m "feat: 40-task pilot training corpus

Authored in four independent batches over the span t01-t20 covers.
Reference-pair yield: <N>/40. Contamination guard clean."
```

---

### Task 5: Amplification run and dedup

**Files:**
- Create: `eval/train/manifest.json`
- Create: `eval/results/train-pilot-amp/` (run root)
- Modify: `eval/train_corpus.py` (add `collect_verified`)

**Interfaces:**
- Consumes: the `--tasks` flag from Task 2, the corpus from Task 4.
- Produces: deduplicated verified programs under `eval/train/pairs/`,
  and the counts Task 6 scores.

- [ ] **Step 1: Preflight the GPU**

`ollama ps` must be empty and at least **13,500 MiB** free before
starting — a stale ollama model silently holding VRAM has caused
`ErrorOutOfDeviceMemory` on this machine before. Verify the server's own
PID is alive and that `preflight.model_path` matches the slug's weights;
a stale llama-server answers health checks from the wrong model.

Do **not** monitor with `pgrep -f "eval.driver"` — it matches its own
command line and reports the driver alive forever. Anchor on
`bin/llama-server` or check the port.

- [ ] **Step 2: Run K = 30 per task, both arms**

Three families × 10 seeds, 0-shot, constrained, per family's own pinned
`num_ctx` (granite 4096, SPEC §48). One invocation per slug — llama.cpp
serves one model per server:

```bash
.venv/bin/python -m eval.driver \
  --models qwen7b --backend llamacpp --constrained \
  --tasks eval/train/tasks.jsonl \
  --seeds 1-10 --shots 0 \
  --run-prefix ampq --results-root eval/results/train-pilot-amp \
  --expect-model-path "$GGUF"
```

Resolve `$GGUF` from ollama's own store rather than guessing a path —
read
`/mnt/extra/ollama-models/manifests/registry.ollama.ai/library/<model>/<tag>`
and take the digest of the layer whose `mediaType` contains `model`; the
blob lives at `/mnt/extra/ollama-models/blobs/sha256-<digest>`. The
pinned tags are `qwen2.5-coder:7b-instruct-q8_0`,
`codegemma:7b-instruct-q8_0`, `granite-code:8b-instruct-q8_0`.

Repeat for `codegemma7b` and `granite8b`, each against a server started
on its own weights, with `--run-prefix ampc` and `ampg` respectively.
The GPU throws intermittent `vk::DeviceLostError` under sustained load,
so check for a partially-written run root before restarting a family
rather than assuming a clean slate.

- [ ] **Step 3: Collect and deduplicate**

Add to `eval/train_corpus.py`:

```python
def collect_verified(results_root: Path, arms: tuple[str, ...] = ("oxide", "rust")) -> dict:
    """Deduplicated passing programs per (task, arm) from an amplification run.

    Deduplication is on normalised source: within one campaign roughly 84%
    of passing programs are already unique, so this removes about a sixth,
    not two-thirds -- the larger figure is a cross-campaign artifact.
    """
    import json as _json
    found: dict[tuple[str, str], set[str]] = {}
    for path in sorted(results_root.rglob("triples.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = _json.loads(line)
            if rec["passed"] and rec["arm"] in arms:
                found.setdefault((rec["task"], rec["arm"]), set()).add(
                    normalize_source(rec["code"]))
    return found
```

Write the deduplicated programs under `eval/train/pairs/<task>/<arm>/`
and record counts, generation parameters, and the contamination-check
result in `eval/train/manifest.json`.

- [ ] **Step 4: Re-run the contamination guard, run the suite, commit**

The guard must pass over the amplified corpus too — a model can
reproduce an eval solution from memory.

```bash
.venv/bin/pytest -q
git add eval/train/pairs eval/train/manifest.json eval/train_corpus.py \
        eval/results/train-pilot-amp
git commit -m "feat: pilot amplification run, K=30, both arms

<N> verified oxide and <M> verified rust programs after dedup.
Contamination guard clean over the amplified corpus."
```

---

### Task 6: Pilot REPORT

**Files:**
- Create: `eval/results/train-pilot-amp/REPORT.md`

- [ ] **Step 1: Score all four pre-registered endpoints**

Quote them verbatim from the spec, then score each — including any that
miss. A miss is the result; do not reinterpret it as a partial success.

| endpoint | threshold |
|---|---|
| reference-pair yield | ≥ 90% (36/40) |
| amplification yield | mean ≥ 4.0 unique verified oxide per task at K = 30 |
| zero-yield tasks | ≤ 30% of tasks producing no verified oxide solution |
| difficulty band | qwen 20.5–40.5, codegemma 6.5–26.5, granite 0–19.5 first-pass |

- [ ] **Step 2: Report the difficulty check against `v03c`**

The amplification run's own first-pass rates are the measurement. Compare
per family to `v03c` (qwen 30.5, codegemma 16.5, granite 9.5) and state
whether each lands in its band. Out-of-band is a **re-authoring trigger,
not a result**.

- [ ] **Step 3: Report the deferred-ledger demand**

Which of `if let`, type-based overloading, `2.to(n)` ranges,
`.set(i, v)`, `unwrap_or` did the 40 new tasks actually demand? This is
v0.4 evidence gathered at no extra cost. Count **distinct programs**,
never raw occurrences — occurrence counts have twice produced figures
that collapsed to a single degenerate program.

- [ ] **Step 4: State what the pilot does not show**

Single-author bias is reduced, not solved. The corpus is 40 tasks. The
yield figures are measured on frontier-authored tasks and may not hold
for the next 360. Whether any of this trains a better model is untested —
that is the next spec.

- [ ] **Step 5: Commit and recommend**

```bash
git add eval/results/train-pilot-amp/REPORT.md
git commit -m "docs: pilot REPORT — four endpoints scored

<one line per endpoint: CONFIRMED or MISSED with the figure>"
```

State plainly whether the pilot supports scaling to ~400 tasks, and if
the yield fell short, give the K the data actually requires rather than
lowering the program target to fit.

---

## After the tasks

Use superpowers:finishing-a-development-branch. The three remaining
specs in this track — training infrastructure, token matching, and the
experiment — each get their own brainstorm and plan. Do **not** start
training in this branch.
