# Token-Matched Training Corpus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `eval/train/matched/` — two supervised-token-matched
training files (oxide.jsonl, rust.jsonl) plus a manifest — from the
paired factory corpus, per the approved spec.

**Architecture:** A pure matching core (`build_matched`) with an
injectable token counter, so all invariants are unit-testable without
the real tokenizer; a thin loader over the existing `collect_verified`;
a deterministic serializer; a hash-pinned Qwen tokenizer fetched once
and committed; a CLI that wires them together and fails closed on
contamination or pin mismatch.

**Tech Stack:** Python 3.14 (`.venv`), pytest, stdlib everywhere except
the `tokenizers` package (Task 5 only, for real token counts).

**Spec:** `docs/superpowers/specs/2026-08-27-token-matching-design.md`
(committed 5847569). The plan argues from the spec; read both.

## Global Constraints

- Work on branch `finetune-data-factory`; commit per task; push at the end.
- Run tests as `.venv/bin/pytest` (pytest.ini already deselects `live`).
- Suite baseline at plan time: **1501 selected / 1504 collected**. The
  final task requires the full suite green with every new test included.
- **Mutation discipline (house rule + pyc gotcha):** every functional
  test must be shown to fail under a targeted mutation before it
  counts. Every mutation run uses this exact preamble, both before the
  mutated run AND before the restored run:

  ```bash
  export PYTHONDONTWRITEBYTECODE=1
  find . -name __pycache__ -type d -prune -exec rm -rf {} +
  ```

- Do NOT modify `eval/tasks.jsonl`, `eval/solutions/`, `eval/train/tasks.jsonl`,
  `eval/train/pairs/`, or anything under `eval/results/`.
- No timestamps in any generated artifact — byte-identical rebuilds are
  a tested invariant.
- House style: frozen slotted dataclasses, no mutation of inputs, files
  under 800 lines, no bare excepts.
- The `class` key is `cls` in Python (reserved word), `"class"` in JSON.

---

### Task 1: Tokenizer pin — fetch, three-way assert, commit

**Files:**
- Create: `eval/tokenizer_pin.py`
- Create: `tests/test_tokenizer_pin.py`
- Create (generated, committed): `eval/train/tokenizer/tokenizer.json`, `eval/train/tokenizer/provenance.json`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `TOKENIZER_DIR = Path("eval/train/tokenizer")`,
  `TOKENIZER_FILE = TOKENIZER_DIR / "tokenizer.json"`,
  `PROVENANCE_FILE = TOKENIZER_DIR / "provenance.json"`,
  `def committed_pin() -> str` (returns the committed file's sha256 hex
  after asserting it equals every provenance hash; raises `PinError` on
  any mismatch). Task 5's CLI calls `committed_pin()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tokenizer_pin.py
"""The committed tokenizer file must match every recorded source hash.

Hermetic: reads only committed files, never the network. The one-time
three-way live assertion happened at fetch time and is recorded in
provenance.json; this test keeps it true forever.
"""
import hashlib
import json

from eval.tokenizer_pin import PROVENANCE_FILE, TOKENIZER_FILE, QWEN_REPOS, committed_pin


def test_tokenizer_identity_pin():
    file_hash = hashlib.sha256(TOKENIZER_FILE.read_bytes()).hexdigest()
    prov = json.loads(PROVENANCE_FILE.read_text(encoding="utf-8"))
    entries = prov["repos"]
    assert len(entries) == 3
    assert {e["repo"] for e in entries} == set(QWEN_REPOS)
    for e in entries:
        assert e["sha256"] == file_hash, e["repo"]
        assert e["revision"]  # resolved commit, never a branch name
    assert committed_pin() == file_hash
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_tokenizer_pin.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.tokenizer_pin'`

- [ ] **Step 3: Write the module**

```python
# eval/tokenizer_pin.py
"""One tokenizer, pinned by content hash, attested from three checkpoints.

The spec requires all three Qwen2.5-Coder sizes to share a tokenizer.
`fetch()` downloads tokenizer.json from each repo at its resolved
revision, asserts the three files are byte-identical, and commits ONE
copy plus a provenance record. Everything afterwards (tests, the
builder CLI) trusts only the committed pair via `committed_pin()`.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

QWEN_REPOS = (
    "Qwen/Qwen2.5-Coder-1.5B",
    "Qwen/Qwen2.5-Coder-7B",
    "Qwen/Qwen2.5-Coder-14B",
)
TOKENIZER_DIR = Path("eval/train/tokenizer")
TOKENIZER_FILE = TOKENIZER_DIR / "tokenizer.json"
PROVENANCE_FILE = TOKENIZER_DIR / "provenance.json"
_API = "https://huggingface.co/api/models/{repo}"
_RESOLVE = "https://huggingface.co/{repo}/resolve/{rev}/tokenizer.json"


class PinError(RuntimeError):
    """The tokenizer pin does not hold; nothing downstream may run."""


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as resp:
        return resp.read()


def fetch(repos: tuple[str, ...] = QWEN_REPOS, dest: Path = TOKENIZER_DIR) -> dict:
    """Download, three-way assert, and write the committed pin files."""
    entries = []
    blobs = []
    for repo in repos:
        info = json.loads(_get(_API.format(repo=repo)))
        rev = info["sha"]
        blob = _get(_RESOLVE.format(repo=repo, rev=rev))
        entries.append(
            {"repo": repo, "revision": rev,
             "sha256": hashlib.sha256(blob).hexdigest()}
        )
        blobs.append(blob)
    hashes = {e["sha256"] for e in entries}
    if len(hashes) != 1:
        raise PinError(f"tokenizers differ across checkpoints: {entries}")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "tokenizer.json").write_bytes(blobs[0])
    provenance = {"file": "tokenizer.json", "repos": entries}
    (dest / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return provenance


def committed_pin() -> str:
    """The pinned sha256, after re-asserting file-vs-provenance agreement."""
    file_hash = hashlib.sha256(TOKENIZER_FILE.read_bytes()).hexdigest()
    prov = json.loads(PROVENANCE_FILE.read_text(encoding="utf-8"))
    for e in prov["repos"]:
        if e["sha256"] != file_hash:
            raise PinError(
                f"committed tokenizer.json does not match {e['repo']} "
                f"({e['sha256']} != {file_hash})"
            )
    return file_hash


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=2, sort_keys=True))
```

- [ ] **Step 4: Run the one-time fetch**

Run: `cd ~/workspace/oxide && .venv/bin/python -m eval.tokenizer_pin`
Expected: JSON with 3 entries, identical `sha256` values, distinct
`revision` commit hashes. Downloads ~7MB × 3; needs network. If any
repo 404s or the hashes differ, STOP and report — do not work around.

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_tokenizer_pin.py -v`
Expected: PASS

- [ ] **Step 6: Mutation-check the test**

With the pyc preamble before each run:
1. Edit `eval/train/tokenizer/provenance.json`: change one hex char of
   one `sha256`. Run the test → must FAIL. Restore with
   `git checkout -- eval/train/tokenizer/provenance.json`... the file is
   not yet committed, so instead restore by re-running
   `.venv/bin/python -m eval.tokenizer_pin` (idempotent rewrite).
2. In `eval/tokenizer_pin.py`, make `committed_pin` return `file_hash`
   without the loop (delete the `for` block). Run → must FAIL
   (the test tampers nothing here, so ALSO re-apply mutation 1 while
   this one is active to prove the loop is load-bearing: with both
   mutations, test must FAIL on the entry-hash assert). Restore both.

- [ ] **Step 7: Commit**

```bash
git add eval/tokenizer_pin.py tests/test_tokenizer_pin.py eval/train/tokenizer/
git commit -m "feat: tokenizer pin — one committed Qwen tokenizer attested from three checkpoints"
```

---

### Task 2: Matching core — `build_matched` with injectable counter

**Files:**
- Create: `eval/token_match.py`
- Create: `tests/test_token_match.py`

**Interfaces:**
- Consumes: `normalize_source` from `eval.train_corpus`.
- Produces (Tasks 3–5 rely on these exact names):

```python
ARMS = ("oxide", "rust")
_SOURCE_RANK = {"reference": 0, "amplified": 1}

class MatchError(ValueError): ...

@dataclass(frozen=True, slots=True)
class Example:
    task: str; cls: str; source: str; text: str; sha256: str; sup_tokens: int

@dataclass(frozen=True, slots=True)
class Dropped:
    task: str; arm: str; cls: str; sha256: str; sup_tokens: int

@dataclass(frozen=True, slots=True)
class ClassBudget:
    cls: str; budget: int
    kept_tokens: dict[str, int]; kept_examples: dict[str, int]
    gap: int; quantization_step: int

@dataclass(frozen=True, slots=True)
class MatchResult:
    kept: dict[str, tuple[Example, ...]]
    dropped: tuple[Dropped, ...]
    budgets: tuple[ClassBudget, ...]
    prompt_tokens: dict[str, int]

def sha256_hex(text: str) -> str: ...
def build_matched(tasks, references, amplified, count_tokens) -> MatchResult: ...
```

  `tasks: dict[str, dict]` (each dict has `"class"` and `"prompt"`),
  `references: dict[tuple[str, str], str]` keyed `(task, arm)` (raw
  text; normalized inside), `amplified: dict[tuple[str, str], set[str]]`
  (already-normalized texts, `collect_verified` shape),
  `count_tokens: Callable[[str], int]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_token_match.py
"""Invariants of the matched-corpus builder (spec 2026-08-27).

All tests use a word-count token counter so the core is exercised
without the real tokenizer; Task 5 adds the real-counter path.
"""
import pytest

from eval.token_match import (
    ARMS,
    Example,
    MatchError,
    build_matched,
)


def words(text: str) -> int:
    return len(text.split()) + 1  # +1 mirrors the real counter's terminator


def corpus():
    """Two classes; rust surplus in 'alpha', oxide surplus in 'beta'."""
    tasks = {
        "n001": {"class": "alpha", "prompt": "add two numbers"},
        "n002": {"class": "alpha", "prompt": "sum a vector"},
        "n003": {"class": "beta", "prompt": "greet a name"},
    }
    references = {
        ("n001", "oxide"): "fn main() { a }",
        ("n001", "rust"): "fn main() { a }",
        ("n002", "oxide"): "fn main() { b }",
        ("n002", "rust"): "fn main() { b }",
        ("n003", "oxide"): "fn main() { c }",
        ("n003", "rust"): "fn main() { c }",
    }
    amplified = {
        ("n001", "oxide"): {"one two three"},
        ("n001", "rust"): {"one two three four", "five six seven eight nine"},
        ("n002", "rust"): {"ten eleven twelve thirteen"},
        ("n003", "oxide"): {"a b c d e f g h", "i j k l m n"},
        ("n003", "rust"): {"o p q"},
    }
    return tasks, references, amplified


def test_budget_invariant_and_symmetric_surplus():
    tasks, references, amplified = corpus()
    result = build_matched(tasks, references, amplified, words)
    for b in result.budgets:
        # the budget-setting arm keeps everything (== budget); the
        # trimmed arm ends at or below it
        assert max(b.kept_tokens.values()) == b.budget
        assert min(b.kept_tokens.values()) <= b.budget
        assert b.gap == b.budget - min(b.kept_tokens.values())
        assert b.gap <= b.quantization_step
    # surplus direction differs by class: alpha trims rust, beta trims oxide
    dropped_arms = {(d.cls, d.arm) for d in result.dropped}
    assert ("alpha", "rust") in dropped_arms
    assert ("beta", "oxide") in dropped_arms


def test_references_survive_every_task_both_arms():
    tasks, references, amplified = corpus()
    result = build_matched(tasks, references, amplified, words)
    for arm in ARMS:
        ref_tasks = {e.task for e in result.kept[arm] if e.source == "reference"}
        assert ref_tasks == set(tasks)


def test_determinism_under_input_reordering():
    tasks, references, amplified = corpus()
    a = build_matched(tasks, references, amplified, words)
    reordered_tasks = dict(reversed(list(tasks.items())))
    reordered_amp = {k: set(sorted(v, reverse=True)) for k, v in reversed(list(amplified.items()))}
    b = build_matched(reordered_tasks, dict(reversed(list(references.items()))), reordered_amp, words)
    assert a == b


def test_trim_order_is_hash_order():
    tasks, references, amplified = corpus()
    result = build_matched(tasks, references, amplified, words)
    for cls in {"alpha", "beta"}:
        drops = [d for d in result.dropped if d.cls == cls]
        assert drops == sorted(drops, key=lambda d: (d.sha256, d.task))


def test_missing_reference_fails_closed():
    tasks, references, amplified = corpus()
    del references[("n002", "rust")]
    with pytest.raises(MatchError, match="n002"):
        build_matched(tasks, references, amplified, words)


def test_references_exceeding_budget_fail_closed():
    tasks = {"n009": {"class": "gamma", "prompt": "p"}}
    references = {
        ("n009", "oxide"): "tiny",
        ("n009", "rust"): "very long reference " * 20,
    }
    with pytest.raises(MatchError, match="gamma"):
        build_matched(tasks, references, {}, words)


def test_prompt_tokens_reported_per_arm():
    tasks, references, amplified = corpus()
    result = build_matched(tasks, references, amplified, words)
    for arm in ARMS:
        expected = sum(words(tasks[e.task]["prompt"]) for e in result.kept[arm])
        assert result.prompt_tokens[arm] == expected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_token_match.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.token_match'`

- [ ] **Step 3: Write the implementation**

```python
# eval/token_match.py
"""Matched supervised-token training corpora from the paired factory output.

Implements docs/superpowers/specs/2026-08-27-token-matching-design.md.
Per class the smaller arm sets the budget; the surplus arm's AMPLIFIED
programs are dropped in ascending (sha256, task) order until its total
first reaches the budget or below; references are never trimmed. All
token counts flow through an injected counter so the core is testable
without the real tokenizer (Task 5 supplies the pinned Qwen counter).
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

from eval.train_corpus import normalize_source

ARMS = ("oxide", "rust")
_SOURCE_RANK = {"reference": 0, "amplified": 1}


class MatchError(ValueError):
    """Construction cannot satisfy the spec; fail closed."""


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Example:
    task: str
    cls: str
    source: str  # "reference" | "amplified"
    text: str
    sha256: str
    sup_tokens: int


@dataclass(frozen=True, slots=True)
class Dropped:
    task: str
    arm: str
    cls: str
    sha256: str
    sup_tokens: int


@dataclass(frozen=True, slots=True)
class ClassBudget:
    cls: str
    budget: int
    kept_tokens: dict[str, int]
    kept_examples: dict[str, int]
    gap: int
    quantization_step: int


@dataclass(frozen=True, slots=True)
class MatchResult:
    kept: dict[str, tuple[Example, ...]]
    dropped: tuple[Dropped, ...]
    budgets: tuple[ClassBudget, ...]
    prompt_tokens: dict[str, int]


def _class_examples(
    tasks: dict[str, dict],
    references: dict[tuple[str, str], str],
    amplified: dict[tuple[str, str], set[str]],
    count_tokens: Callable[[str], int],
) -> dict[tuple[str, str], list[Example]]:
    out: dict[tuple[str, str], list[Example]] = {}
    for tid in sorted(tasks):
        cls = tasks[tid]["class"]
        for arm in ARMS:
            ref = references.get((tid, arm))
            if ref is None:
                raise MatchError(f"missing {arm} reference for {tid}")
            norm = normalize_source(ref)
            items = [Example(tid, cls, "reference", norm, sha256_hex(norm), count_tokens(norm))]
            for text in sorted(amplified.get((tid, arm), set())):
                items.append(Example(tid, cls, "amplified", text, sha256_hex(text), count_tokens(text)))
            out.setdefault((cls, arm), []).extend(items)
    return out


def build_matched(
    tasks: dict[str, dict],
    references: dict[tuple[str, str], str],
    amplified: dict[tuple[str, str], set[str]],
    count_tokens: Callable[[str], int],
) -> MatchResult:
    by_class = _class_examples(tasks, references, amplified, count_tokens)
    classes = sorted({cls for cls, _ in by_class})

    kept: dict[str, list[Example]] = {arm: [] for arm in ARMS}
    dropped: list[Dropped] = []
    budgets: list[ClassBudget] = []
    for cls in classes:
        totals = {
            arm: sum(e.sup_tokens for e in by_class.get((cls, arm), ())) for arm in ARMS
        }
        budget = min(totals.values())
        surplus_arm = max(ARMS, key=lambda a: totals[a])
        surplus = by_class.get((cls, surplus_arm), [])
        ref_tokens = sum(e.sup_tokens for e in surplus if e.source == "reference")
        if ref_tokens > budget:
            raise MatchError(
                f"references alone exceed budget in class {cls!r} "
                f"({ref_tokens} > {budget}); re-author before matching"
            )
        candidates = sorted(
            (e for e in surplus if e.source == "amplified"),
            key=lambda e: (e.sha256, e.task),
        )
        step = max((e.sup_tokens for e in candidates), default=0)
        total = totals[surplus_arm]
        removed: set[tuple[str, str]] = set()
        for e in candidates:
            if total <= budget:
                break
            total -= e.sup_tokens
            removed.add((e.task, e.sha256))
            dropped.append(Dropped(e.task, surplus_arm, cls, e.sha256, e.sup_tokens))
        kept_tokens: dict[str, int] = {}
        kept_examples: dict[str, int] = {}
        for arm in ARMS:
            arm_kept = [
                e
                for e in by_class.get((cls, arm), ())
                if not (arm == surplus_arm and (e.task, e.sha256) in removed)
            ]
            kept[arm].extend(arm_kept)
            kept_tokens[arm] = sum(e.sup_tokens for e in arm_kept)
            kept_examples[arm] = len(arm_kept)
        budgets.append(
            ClassBudget(
                cls,
                budget,
                kept_tokens,
                kept_examples,
                max(kept_tokens.values()) - min(kept_tokens.values()),
                step,
            )
        )

    def sort_key(e: Example) -> tuple:
        return (e.cls, e.task, _SOURCE_RANK[e.source], e.sha256)

    kept_sorted = {arm: tuple(sorted(kept[arm], key=sort_key)) for arm in ARMS}
    prompt_tokens = {
        arm: sum(count_tokens(tasks[e.task]["prompt"]) for e in kept_sorted[arm])
        for arm in ARMS
    }
    return MatchResult(
        kept=kept_sorted,
        dropped=tuple(sorted(dropped, key=lambda d: (d.cls, d.arm, d.sha256, d.task))),
        budgets=tuple(budgets),
        prompt_tokens=prompt_tokens,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_token_match.py -v`
Expected: 7 PASS

- [ ] **Step 5: Mutation-check every test** (pyc preamble before every run)

1. `budget = min(...)` → `max(...)`: budget/surplus tests must FAIL.
2. Delete the `if ref_tokens > budget` block: `test_references_exceeding_budget_fail_closed` must FAIL.
3. `key=lambda e: (e.sha256, e.task)` → `(e.task, e.sha256)`:
   `test_trim_order_is_hash_order` must FAIL. If it happens to pass on
   the small fixture, enlarge the fixture until the orders diverge —
   a mutation the fixture cannot see is a fixture defect.
4. **Paired ordering mutation.** Ordering is deliberately
   double-layered (sorted task iteration in `_class_examples` AND the
   final `sort_key` sort), so a single-layer mutation is absorbed by
   the surviving layer — that redundancy is intended, not a vacuous
   test. Apply BOTH: `for tid in sorted(tasks)` → `for tid in tasks`,
   and `sort_key`'s body → `return ("",)`. With both layers gone, dict
   insertion order leaks into `kept`, and
   `test_determinism_under_input_reordering` must FAIL. Restore both.
5. Remove `"reference"` filtering by trimming candidates from all
   sources (`e for e in surplus`): `test_references_survive...` must FAIL.
6. `prompt_tokens` computed over `tasks` instead of kept examples:
   `test_prompt_tokens_reported_per_arm` must FAIL.

Restore after each; every run under the pyc preamble.

- [ ] **Step 6: Commit**

```bash
git add eval/token_match.py tests/test_token_match.py
git commit -m "feat: matching core — per-class budgets, hash-ordered trim, fail-closed edges"
```

---

### Task 3: Deterministic serialization + manifest completeness

**Files:**
- Modify: `eval/token_match.py` (append)
- Modify: `tests/test_token_match.py` (append)

**Interfaces:**
- Consumes: `MatchResult`, `Example`, `Dropped`, `ClassBudget`, `ARMS` (Task 2).
- Produces:

```python
MANIFEST_KEYS = frozenset({
    "tokenizer", "classes", "totals", "prompt_tokens",
    "dropped", "counts_source", "contamination", "token_efficiency",
})
def write_matched(out_dir: Path, result: MatchResult, *, tokenizer: dict,
                  counts_source: dict, contamination: dict,
                  token_efficiency: dict) -> None
```

  Writes `out_dir/oxide.jsonl`, `out_dir/rust.jsonl`,
  `out_dir/manifest.json`. JSONL record keys: `task, class, source,
  text, sha256, sup_tokens`. Manifest `classes` rows: `class, budget,
  kept_tokens, kept_examples, gap, quantization_step`; `dropped` rows:
  `task, arm, class, sha256, sup_tokens`; `totals`:
  `{"kept_tokens": {arm: int}, "kept_examples": {arm: int}}`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_token_match.py`)

```python
import json

from eval.token_match import MANIFEST_KEYS, write_matched


def build_and_write(tmp_path):
    tasks, references, amplified = corpus()
    result = build_matched(tasks, references, amplified, words)
    write_matched(
        tmp_path,
        result,
        tokenizer={"id": "test", "sha256": "0" * 64},
        counts_source={"roots": ["r1"], "commit": "abc"},
        contamination={"hits": 0, "programs_checked": 9},
        token_efficiency={"references": {}, "amplified": {}},
    )
    return result


def test_write_is_byte_deterministic(tmp_path):
    a_dir, b_dir = tmp_path / "a", tmp_path / "b"
    a_dir.mkdir(); b_dir.mkdir()
    tasks, references, amplified = corpus()
    kwargs = dict(
        tokenizer={"id": "test", "sha256": "0" * 64},
        counts_source={"roots": ["r1"], "commit": "abc"},
        contamination={"hits": 0, "programs_checked": 9},
        token_efficiency={"references": {}, "amplified": {}},
    )
    write_matched(a_dir, build_matched(tasks, references, amplified, words), **kwargs)
    write_matched(b_dir, build_matched(
        dict(reversed(list(tasks.items()))), references, amplified, words), **kwargs)
    for name in ("oxide.jsonl", "rust.jsonl", "manifest.json"):
        assert (a_dir / name).read_bytes() == (b_dir / name).read_bytes()


def test_manifest_completeness(tmp_path):
    build_and_write(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == set(MANIFEST_KEYS)
    for row in manifest["classes"]:
        assert set(row) == {"class", "budget", "kept_tokens",
                            "kept_examples", "gap", "quantization_step"}
    for row in manifest["dropped"]:
        assert set(row) == {"task", "arm", "class", "sha256", "sup_tokens"}
    assert set(manifest["totals"]) == {"kept_tokens", "kept_examples"}


def test_jsonl_round_trip_matches_result(tmp_path):
    result = build_and_write(tmp_path)
    for arm in ARMS:
        rows = [json.loads(line) for line in
                (tmp_path / f"{arm}.jsonl").read_text(encoding="utf-8").splitlines()]
        assert [
            (r["task"], r["class"], r["source"], r["text"], r["sha256"], r["sup_tokens"])
            for r in rows
        ] == [
            (e.task, e.cls, e.source, e.text, e.sha256, e.sup_tokens)
            for e in result.kept[arm]
        ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_token_match.py -v -k "write or manifest or round_trip"`
Expected: FAIL — `ImportError: cannot import name 'MANIFEST_KEYS'`

- [ ] **Step 3: Write the implementation** (append to `eval/token_match.py`)

```python
import json
from pathlib import Path

MANIFEST_KEYS = frozenset({
    "tokenizer", "classes", "totals", "prompt_tokens",
    "dropped", "counts_source", "contamination", "token_efficiency",
})


def _example_row(e: Example) -> dict:
    return {"task": e.task, "class": e.cls, "source": e.source,
            "text": e.text, "sha256": e.sha256, "sup_tokens": e.sup_tokens}


def write_matched(
    out_dir: Path,
    result: MatchResult,
    *,
    tokenizer: dict,
    counts_source: dict,
    contamination: dict,
    token_efficiency: dict,
) -> None:
    """Serialize a MatchResult; byte-identical for equal inputs, no timestamps."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for arm in ARMS:
        lines = [json.dumps(_example_row(e), ensure_ascii=False, sort_keys=True)
                 for e in result.kept[arm]]
        (out_dir / f"{arm}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "tokenizer": tokenizer,
        "classes": [
            {"class": b.cls, "budget": b.budget, "kept_tokens": b.kept_tokens,
             "kept_examples": b.kept_examples, "gap": b.gap,
             "quantization_step": b.quantization_step}
            for b in result.budgets
        ],
        "totals": {
            "kept_tokens": {arm: sum(e.sup_tokens for e in result.kept[arm]) for arm in ARMS},
            "kept_examples": {arm: len(result.kept[arm]) for arm in ARMS},
        },
        "prompt_tokens": result.prompt_tokens,
        "dropped": [
            {"task": d.task, "arm": d.arm, "class": d.cls,
             "sha256": d.sha256, "sup_tokens": d.sup_tokens}
            for d in result.dropped
        ],
        "counts_source": counts_source,
        "contamination": contamination,
        "token_efficiency": token_efficiency,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
```

(Move the `import json` / `from pathlib import Path` lines up into the
module's import block rather than leaving them mid-file.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_token_match.py -v`
Expected: 10 PASS

- [ ] **Step 5: Mutation-check** (pyc preamble each run)

1. Delete `"prompt_tokens": result.prompt_tokens,` from the manifest:
   `test_manifest_completeness` must FAIL.
2. Apply Task 2's paired ordering mutation (unsorted task iteration +
   constant `sort_key`): `test_write_is_byte_deterministic` must FAIL
   on its reordered-tasks build. Restore both edits.
3. Truncate the dropped list (`result.dropped[:1]`) in the manifest:
   `test_manifest_completeness` passes (keys intact) — add no new
   test; Task 5's committed-artifact budget audit covers dropped-list
   integrity end-to-end. Record this as a known single-mutation gap in
   the task's commit message body.

- [ ] **Step 6: Commit**

```bash
git add eval/token_match.py tests/test_token_match.py
git commit -m "feat: deterministic matched-corpus serialization + manifest completeness"
```

---

### Task 4: Input loading + acceptance pin on the measured corpus

**Files:**
- Modify: `eval/token_match.py` (append)
- Create: `tests/test_token_match_corpus.py`

**Interfaces:**
- Consumes: `collect_verified`, `load_train_tasks`, `PAIRS_ROOT` from
  `eval.train_corpus`; `build_matched` (Task 2).
- Produces:

```python
AMP_ROOTS = (Path("eval/results/train-amp2"), Path("eval/results/train-amp2-slice"))
def load_matched_inputs() -> tuple[
    dict[str, dict],
    dict[tuple[str, str], str],
    dict[tuple[str, str], set[str]],
]
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_token_match_corpus.py
"""Acceptance pin: the collector reproduces the counts the spec was approved on.

These are the 2026-08-27 measured numbers (spec, 'What exists'). If this
test fails, the corpus or collector drifted — that voids the approval,
so the failure must be loud, never accommodated by editing the numbers
without a spec amendment.
"""
from eval.token_match import load_matched_inputs

APPROVED_COUNTS = {
    "oxide": {"arithmetic/loops": 93, "strings": 10, "structs/option": 78, "vectors": 30},
    "rust": {"arithmetic/loops": 139, "strings": 67, "structs/option": 62, "vectors": 103},
}


def test_amplified_counts_match_spec_approval():
    tasks, references, amplified = load_matched_inputs()
    counts = {"oxide": {}, "rust": {}}
    for (task, arm), progs in amplified.items():
        cls = tasks[task]["class"]
        counts[arm][cls] = counts[arm].get(cls, 0) + len(progs)
    assert counts == APPROVED_COUNTS
    assert sum(counts["oxide"].values()) == 211
    assert sum(counts["rust"].values()) == 371


def test_references_present_for_all_40_tasks():
    tasks, references, amplified = load_matched_inputs()
    assert len(tasks) == 40
    for tid in tasks:
        assert (tid, "oxide") in references
        assert (tid, "rust") in references
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_token_match_corpus.py -v`
Expected: FAIL — `ImportError: cannot import name 'load_matched_inputs'`

- [ ] **Step 3: Write the implementation** (append to `eval/token_match.py`)

```python
from eval.train_corpus import PAIRS_ROOT, collect_verified, load_train_tasks

AMP_ROOTS = (
    Path("eval/results/train-amp2"),
    Path("eval/results/train-amp2-slice"),
)


def load_matched_inputs() -> tuple[
    dict[str, dict],
    dict[tuple[str, str], str],
    dict[tuple[str, str], set[str]],
]:
    """Tasks, references, and merged amplified programs for kept tasks only.

    Merging the amp2 and slice roots and restricting to the live
    tasks.jsonl reproduces the corpus the difficulty band cleared on
    2026-08-13 (slice REPORT: merged band PASS 30/30).
    """
    tasks = load_train_tasks()
    references = {}
    for tid in tasks:
        for arm, fname in (("oxide", "oxide.ox"), ("rust", "rust.rs")):
            references[(tid, arm)] = (PAIRS_ROOT / tid / fname).read_text(encoding="utf-8")
    amplified: dict[tuple[str, str], set[str]] = {}
    for root in AMP_ROOTS:
        for (task, arm), progs in collect_verified(root).items():
            if task in tasks:
                amplified.setdefault((task, arm), set()).update(progs)
    return tasks, references, amplified
```

(Fold the new import into the existing `from eval.train_corpus import
normalize_source` line: `from eval.train_corpus import PAIRS_ROOT,
collect_verified, load_train_tasks, normalize_source`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_token_match_corpus.py -v`
Expected: 2 PASS (takes a few seconds — it scans both results trees)

- [ ] **Step 5: Mutation-check** (pyc preamble each run)

1. Drop the slice root from `AMP_ROOTS`:
   `test_amplified_counts_match_spec_approval` must FAIL (the slice
   replaced three vector tasks; counts move).
2. Remove the `if task in tasks` filter: must FAIL (amp2 still holds
   the three replaced tasks' programs).

- [ ] **Step 6: Commit**

```bash
git add eval/token_match.py tests/test_token_match_corpus.py
git commit -m "feat: matched-corpus input loader + acceptance pin on approved counts"
```

---

### Task 5: Real tokenizer, token efficiency, contamination guard, CLI, build

**Files:**
- Modify: `eval/token_match.py` (append)
- Modify: `tests/test_token_match_corpus.py` (append)
- Create (generated, committed): `eval/train/matched/oxide.jsonl`,
  `eval/train/matched/rust.jsonl`, `eval/train/matched/manifest.json`

**Interfaces:**
- Consumes: `committed_pin`, `TOKENIZER_FILE` (Task 1); everything above.
- Produces:

```python
def qwen_counter() -> Callable[[str], int]      # real counter; +1 terminator
def token_efficiency(tasks, references, amplified, count_tokens) -> dict
def main(argv: list[str] | None = None) -> int  # python -m eval.token_match
MATCHED_DIR = Path("eval/train/matched")
```

- [ ] **Step 1: Preflight the dependency**

Run: `cd ~/workspace/oxide && .venv/bin/pip install tokenizers && .venv/bin/python -c "from tokenizers import Tokenizer; t = Tokenizer.from_file('eval/train/tokenizer/tokenizer.json'); print(len(t.encode('fn main() {}').ids))"`
Expected: an integer. If the install fails (no cp314 wheel), STOP the
task and report the blocker — do not substitute another tokenizer
implementation.

- [ ] **Step 2: Write the failing tests** (append to `tests/test_token_match_corpus.py`)

```python
import hashlib
import json

from eval.token_match import (
    ARMS,
    MATCHED_DIR,
    load_matched_inputs,
    qwen_counter,
    token_efficiency,
)
from eval.tokenizer_pin import TOKENIZER_FILE
from eval.train_corpus import contamination_report, load_train_tasks


def _manifest():
    return json.loads((MATCHED_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_qwen_counter_includes_terminator():
    count = qwen_counter()
    base = count("fn main() {}")
    assert base >= 2  # at least one content token + the terminator
    assert count("") == 1  # terminator only


def test_token_efficiency_covers_both_sources_and_overall():
    tasks, references, amplified = load_matched_inputs()
    eff = token_efficiency(tasks, references, amplified, lambda s: len(s.split()) + 1)
    for section in ("references", "amplified"):
        assert "overall" in eff[section]
        for cls in {t["class"] for t in tasks.values()} | {"overall"}:
            for arm in ARMS:
                cell = eff[section][cls][arm]
                assert set(cell) == {"n", "mean_sup_tokens"}
                assert cell["n"] > 0 or section == "amplified"


def test_committed_manifest_pin_matches_provenance():
    manifest = _manifest()
    file_hash = hashlib.sha256(TOKENIZER_FILE.read_bytes()).hexdigest()
    assert manifest["tokenizer"]["sha256"] == file_hash


def test_committed_matched_corpus_is_uncontaminated():
    tasks = load_train_tasks()
    programs = {}
    for arm in ARMS:
        for line in (MATCHED_DIR / f"{arm}.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            programs[f"{arm}/{row['task']}/{row['sha256'][:12]}"] = row["text"]
    assert contamination_report(tasks, programs) == ()
    assert _manifest()["contamination"]["hits"] == 0
    assert _manifest()["contamination"]["programs_checked"] == len(programs)


def test_committed_budgets_hold():
    manifest = _manifest()
    for row in manifest["classes"]:
        kept = row["kept_tokens"]
        assert max(kept.values()) == row["budget"]
        assert row["gap"] == max(kept.values()) - min(kept.values())
        assert row["gap"] <= row["quantization_step"]
    # dropped-list integrity: dropped + kept tokens reconstruct the
    # surplus arm's pre-trim totals per class, cross-checked from inputs
    tasks, references, amplified = load_matched_inputs()
    count = qwen_counter()
    from eval.token_match import build_matched
    rebuilt = build_matched(tasks, references, amplified, count)
    assert [
        {"class": b.cls, "budget": b.budget, "kept_tokens": b.kept_tokens,
         "kept_examples": b.kept_examples, "gap": b.gap,
         "quantization_step": b.quantization_step}
        for b in rebuilt.budgets
    ] == manifest["classes"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_token_match_corpus.py -v`
Expected: new tests FAIL — `ImportError: cannot import name 'qwen_counter'`

- [ ] **Step 4: Write the implementation** (append to `eval/token_match.py`)

```python
import argparse
import subprocess

from eval.tokenizer_pin import TOKENIZER_FILE, committed_pin
from eval.train_corpus import contamination_report

MATCHED_DIR = Path("eval/train/matched")


def qwen_counter() -> Callable[[str], int]:
    """Supervised-token counter under the pinned tokenizer: ids + terminator."""
    from tokenizers import Tokenizer  # deferred: heavy, Task-5-only dependency

    tok = Tokenizer.from_file(str(TOKENIZER_FILE))
    return lambda text: len(tok.encode(text).ids) + 1


def token_efficiency(
    tasks: dict[str, dict],
    references: dict[tuple[str, str], str],
    amplified: dict[tuple[str, str], set[str]],
    count_tokens: Callable[[str], int],
) -> dict:
    """Descriptive estimand, computed PRE-trim over the full verified corpus.

    The spec's decision 10: tokens per program, per class and overall,
    references and amplified separately. Measured before trimming
    because the estimand is about the languages, not the kept sample.
    """
    from eval.train_corpus import normalize_source as _norm

    sections: dict[str, dict] = {"references": {}, "amplified": {}}
    pools: dict[str, dict[tuple[str, str], list[int]]] = {"references": {}, "amplified": {}}
    for tid, task in tasks.items():
        cls = task["class"]
        for arm in ARMS:
            pools["references"].setdefault((cls, arm), []).append(
                count_tokens(_norm(references[(tid, arm)]))
            )
            for text in sorted(amplified.get((tid, arm), set())):
                pools["amplified"].setdefault((cls, arm), []).append(count_tokens(text))
    classes = sorted({t["class"] for t in tasks.values()})
    for section, by_key in pools.items():
        table: dict[str, dict] = {}
        for cls in classes + ["overall"]:
            table[cls] = {}
            for arm in ARMS:
                values = (
                    [v for (c, a), vs in by_key.items() if a == arm for v in vs]
                    if cls == "overall"
                    else by_key.get((cls, arm), [])
                )
                mean = round(sum(values) / len(values), 2) if values else 0.0
                table[cls][arm] = {"n": len(values), "mean_sup_tokens": mean}
        sections[section] = table
    return sections


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the matched training corpus.")
    parser.add_argument("--out", type=Path, default=MATCHED_DIR)
    args = parser.parse_args(argv)

    pin = committed_pin()  # raises PinError on any mismatch — fail closed
    tasks, references, amplified = load_matched_inputs()
    count = qwen_counter()
    result = build_matched(tasks, references, amplified, count)

    programs = {
        f"{arm}/{e.task}/{e.sha256[:12]}": e.text
        for arm in ARMS
        for e in result.kept[arm]
    }
    hits = contamination_report(tasks, programs)
    if hits:
        raise MatchError(f"matched corpus is contaminated: {hits}")

    write_matched(
        args.out,
        result,
        tokenizer={"id": "Qwen/Qwen2.5-Coder (shared, see provenance)", "sha256": pin},
        counts_source={"roots": [str(r) for r in AMP_ROOTS], "commit": _git_head()},
        contamination={"hits": 0, "programs_checked": len(programs)},
        token_efficiency=token_efficiency(tasks, references, amplified, count),
    )
    for b in result.budgets:
        print(f"{b.cls}: budget={b.budget} kept={b.kept_tokens} gap={b.gap} step={b.quantization_step}")
    print(f"dropped={len(result.dropped)} examples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

(Again fold the new imports into the module's import block.)

Note `counts_source.commit` records HEAD at build time — rebuild at a
different commit changes only that manifest field. The byte-determinism
test (Task 3) injects a fixed value, so it stays valid.

- [ ] **Step 5: Build the corpus**

Run: `cd ~/workspace/oxide && .venv/bin/python -m eval.token_match`
Expected: four budget lines + dropped count; `eval/train/matched/`
gains the three files. Sanity-read the printed budgets: every gap must
be at or below its step, and strings should show the small numbers the
spec predicts.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_token_match_corpus.py tests/test_token_match.py -v`
Expected: all PASS (the committed-artifact tests now read real files)

- [ ] **Step 7: Mutation-check** (pyc preamble each run)

1. In `qwen_counter`, drop the `+ 1`: `test_qwen_counter_includes_terminator`
   must FAIL (`count("") == 1` becomes 0).
2. Edit the committed `manifest.json` by hand: set `"hits": 1`.
   `test_committed_matched_corpus_is_uncontaminated` must FAIL (its
   independent recomputation is the guard; the manifest assert pins the
   record). Restore by rebuilding (Step 5). Note `main`'s own
   contamination raise is deliberately NOT single-mutation-killable —
   the committed test recomputes the same report, which is the
   defense-in-depth the spec's guard section asks for.
3. In `token_efficiency`, compute over kept examples by passing
   `result.kept`-derived amplified sets — simpler equivalent mutation:
   change `classes + ["overall"]` to `classes`:
   `test_token_efficiency_covers_both_sources_and_overall` must FAIL.
4. Edit committed `manifest.json`: change one class's `budget` by 1.
   `test_committed_budgets_hold` must FAIL (rebuilt-vs-manifest
   mismatch). Restore by rebuilding.

- [ ] **Step 8: Commit**

```bash
git add eval/token_match.py tests/test_token_match_corpus.py eval/train/matched/
git commit -m "feat: build the matched corpus — pinned tokenizer, contamination-guarded, token-efficiency estimand"
```

---

### Task 6: Report, full suite, push

**Files:**
- Create: `eval/train/matched/REPORT.md` (hand-written from the manifest)

**Interfaces:**
- Consumes: `eval/train/matched/manifest.json` (Task 5).
- Produces: the human-readable record; nothing programmatic.

- [ ] **Step 1: Write REPORT.md from the built manifest**

Structure (fill every number from `manifest.json` — no placeholders):

```markdown
# Matched training corpus — build record

2026-08-XX (build date). Spec:
docs/superpowers/specs/2026-08-27-token-matching-design.md. Built by
`python -m eval.token_match` at commit <counts_source.commit>.

## Budgets

| class | budget (sup tokens) | oxide kept (tok / n) | rust kept (tok / n) | gap | step |
|---|---|---|---|---|---|
<one row per manifest class, plus a totals row>

Dropped: <N> examples (<N_oxide> oxide, <N_rust> rust) — full list in
manifest.json, named not deleted.

## Token efficiency (pre-trim estimand, pinned Qwen tokenizer)

| class | refs oxide | refs rust | amplified oxide | amplified rust |
|---|---|---|---|---|
<mean_sup_tokens (n=...) per cell, plus overall row>

<2-4 sentences reading the direction honestly: do the reference and
amplified comparisons agree or point in opposite directions, per the
spec's prediction that they may differ? No causal claims.>

## Guards

Contamination: 0 hits over <programs_checked> kept programs.
Tokenizer pin: <sha256 first 12 chars>, attested from 3 checkpoints
(eval/train/tokenizer/provenance.json).
```

- [ ] **Step 2: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: **0 failures**, count ≥ 1501 + the ~14 tests this plan added.
Any failure in a pre-existing test is a STOP-and-report, not a fix-here.

- [ ] **Step 3: Commit and push**

```bash
git add eval/train/matched/REPORT.md
git commit -m "docs: matched-corpus build record — budgets, token efficiency, guards"
git push
git status -sb   # must show branch in sync with origin
```

---

## Self-Review Notes (kept for the executor)

- Spec decision 4 (card-free format) and decision 9 (epoch parity) bind
  the *experiment* spec; nothing in this plan implements them, by design.
- Spec's test 4 ("trim order is load-bearing") is implemented as
  `test_trim_order_is_hash_order` plus mutation 3 of Task 2 — the
  mutation, not the assertion alone, is what proves load-bearing.
- The Task 3 mutation notes record one accepted single-mutation gap
  (manifest dropped-list truncation), closed end-to-end by Task 5's
  `test_committed_budgets_hold` rebuild cross-check.
