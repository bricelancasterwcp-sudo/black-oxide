# v0.4 Efficiency Cycle, Wave 3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the vectors token gap — the entire net surplus of the reference corpus — by shipping the three Vec builtins the cost census ranks first, and build the cost census that found them.

**Architecture:** A new `eval/cost_census.py` measures per-pair oxide/rust token surplus and ranks it; a two-eyed gate reads it beside the existing demand census; three builtins (`swap`, `reverse`, `set`) land through the project's established three-seam mechanism; references are re-authored under the amended bias rule; the wave closes with a dynamic loop on a rented GPU and a committed report.

**Tech Stack:** Python 3.14 (stdlib + `tokenizers` for the pinned Qwen counter), pytest, rustc as the correctness oracle, llama.cpp on a rented RunPod GPU for the dynamic arms.

**Spec:** `docs/superpowers/specs/2026-08-29-v04-efficiency-wave3-design.md`

## Global Constraints

- Branch: `v04-efficiency-wave3` (already created off `main` @ `a9cabe51`; the spec is committed there at `5f510d06`).
- Run everything in the venv: `.venv/bin/python -m pytest`. Bare `python3` lacks `tokenizers` and `pytest`.
- **pyc discipline, mandatory for every mutation check:** `export PYTHONDONTWRITEBYTECODE=1` and purge `__pycache__` before EVERY run, mutated and restored alike. A same-length mutation restored within the same second otherwise leaves the interpreter running the mutant while the source reads clean.
- **Protected, read-only:** `eval/tasks.jsonl`, `eval/solutions/`, `eval/train/tasks.jsonl`, `eval/train/pairs/*/rust.rs`, `eval/probes.jsonl`, and every committed `eval/results/*` directory except the new ones this plan creates.
- **Identical-stdout law:** every re-authored oxide reference must produce byte-identical stdout to the frozen `expected_stdout`. `validate_pair` green on all 40 pairs, contamination guard 0 hits.
- Suite baseline entering this wave: **1642 passed, 3 deselected.**
- Amended bias rule (spec §4): each arm written as well as its own language allows; substitutions use only shipped vocabulary and must not restructure beyond what the construct replaces; every admissible substitution must be applied; every changed pair is oracle-verified and diffed with its token delta.
- Static baseline to beat, measured 2026-08-29 with the pinned tokenizer: arithmetic 509/504 = 1.010, strings 615/578 = 1.064, structs 623/677 = 0.920, vectors 789/573 = 1.377, **overall 2536/2332 = 1.0875**.
- Targets: overall **≤ 1.02**, vectors **≤ 1.10**, strings hold **≤ 1.07**, arithmetic hold **≤ 1.02**, structs hold **≤ 0.93**.

---

## File Structure

| File | Responsibility |
|---|---|
| `eval/cost_census.py` (new) | Per-pair token-surplus census, ranking, report rendering, CLI. Deliberately a NEW module: `eval/demand_census.py` is 954 lines and already flagged for a split. |
| `tests/test_cost_census.py` (new) | Unit tests on synthetic costs + an acceptance test pinning the committed corpus numbers. |
| `src/sema/types.py` | `BUILTINS` entries for `swap`, `reverse`, `set` (types + linearity modes). |
| `src/codegen/support.py` | `_PRELUDE_FNS` Rust definitions + `BUILTIN_REF` ref-form tuples. |
| `src/parser/expressions.py` | `BUILTIN_METHOD_NAMES` entries (method-form sugar; `tests/test_parser.py:551` asserts this set equals `set(BUILTINS)`). |
| `tests/test_v04_wave3.py` (new) | Runtime + diagnostic tests for the three builtins. |
| `SPEC.md` | §60: the three constructs, the panic ruling, the cost-census record, the bias-rule amendment. |
| `LANGUAGE_CARD.md`, `LANGUAGE_CARD_EXPLICIT.md` | Card v0.5, both voices, mirrored. |
| `eval/train/pairs/*/oxide.ox` | Re-authored references (rust.rs never touched). |
| `eval/results/v04-cost-census/` (new) | `cost_census.json` + `REPORT.md`. |
| `eval/results/v04-campaign3/` (new) | Campaign arms, matched corpus, wave report. |

---

## Task 1: Cost census instrument

**Files:**
- Create: `eval/cost_census.py`
- Create: `tests/test_cost_census.py`
- Create: `eval/results/v04-cost-census/cost_census.json`, `eval/results/v04-cost-census/REPORT.md`

**Interfaces:**
- Consumes: `eval.token_match.qwen_counter() -> Callable[[str], int]`; `eval.train_corpus.load_train_tasks() -> dict[str, dict]` (keyed by task id, each with a `"class"` key); `eval.train_corpus.PAIRS_ROOT` (a `Path`; each pair is `PAIRS_ROOT/<task>/oxide.ox` and `.../rust.rs`); `eval.tokenizer_pin.TOKENIZER_FILE`.
- Produces: `PairCost` (frozen dataclass: `task: str`, `cls: str`, `oxide_tokens: int`, `rust_tokens: int`, with `.surplus -> int` and `.ratio -> float | None`); `pair_costs(count) -> tuple[list[PairCost], list[str]]`; `rank_by_surplus(costs) -> list[PairCost]`; `class_subtotals(costs) -> dict[str, dict]`; `build_cost_census() -> dict`; `render_report(census) -> str`; `main(argv=None) -> int`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cost_census.py`:

```python
"""The cost census: where the oxide/rust token surplus actually sits.

Synthetic fixtures exercise the arithmetic; the acceptance test pins the
instrument against the committed corpus (the 2026-08-29 measured numbers
the wave-3 spec was approved on). If the acceptance test fails, either
the corpus moved or the instrument drifted -- both must be loud.
"""
from eval.cost_census import (
    PairCost,
    build_cost_census,
    class_subtotals,
    pair_costs,
    rank_by_surplus,
)
from eval.token_match import qwen_counter


def test_surplus_is_signed_never_clipped():
    """structs/option runs NEGATIVE in the real corpus and that is
    load-bearing for the whole-corpus ratio -- a census that clipped at
    zero would silently inflate the total."""
    win = PairCost("n001", "structs/option", oxide_tokens=40, rust_tokens=55)
    lose = PairCost("n002", "vectors", oxide_tokens=90, rust_tokens=60)
    assert win.surplus == -15
    assert lose.surplus == +30


def test_ratio_is_none_rather_than_a_fabricated_number():
    empty = PairCost("n003", "vectors", oxide_tokens=10, rust_tokens=0)
    assert empty.ratio is None


def test_rank_by_surplus_orders_most_expensive_first():
    costs = [
        PairCost("a", "vectors", 70, 60),
        PairCost("b", "vectors", 142, 60),
        PairCost("c", "vectors", 40, 50),
    ]
    assert [c.task for c in rank_by_surplus(costs)] == ["b", "a", "c"]


def test_class_subtotals_sum_both_arms_and_ratio_the_totals():
    costs = [
        PairCost("a", "vectors", 100, 50),
        PairCost("b", "vectors", 50, 50),
        PairCost("c", "strings", 30, 30),
    ]
    subs = class_subtotals(costs)
    assert subs["vectors"]["oxide"] == 150
    assert subs["vectors"]["rust"] == 100
    assert subs["vectors"]["surplus"] == 50
    assert subs["vectors"]["ratio"] == 1.5
    assert subs["strings"]["surplus"] == 0


def test_pair_costs_names_unreadable_pairs_instead_of_scoring_them_zero(monkeypatch):
    import eval.cost_census as cc
    monkeypatch.setattr(cc, "load_train_tasks", lambda: {
        "nXX": {"class": "vectors"}, "n001": {"class": "arithmetic/loops"}})
    costs, dropped = cc.pair_costs(lambda s: len(s.split()))
    assert "nXX" in dropped
    assert all(c.task != "nXX" for c in costs)


def test_acceptance_pins_the_committed_corpus_numbers():
    """The 2026-08-29 figures the wave-3 spec argues from."""
    costs, dropped = pair_costs(qwen_counter())
    assert dropped == []
    subs = class_subtotals(costs)
    assert (subs["vectors"]["oxide"], subs["vectors"]["rust"]) == (789, 573)
    assert (subs["strings"]["oxide"], subs["strings"]["rust"]) == (615, 578)
    assert (subs["structs/option"]["oxide"], subs["structs/option"]["rust"]) == (623, 677)
    assert (subs["arithmetic/loops"]["oxide"], subs["arithmetic/loops"]["rust"]) == (509, 504)
    top = rank_by_surplus(costs)[:3]
    assert [c.task for c in top] == ["n043", "n050", "n045"]
    assert [c.surplus for c in top] == [82, 60, 40]


def test_census_payload_carries_its_lens():
    census = build_cost_census()
    assert census["tokenizer"]["sha256"]
    assert census["dropped"] == []
    assert census["overall"]["oxide"] == 2536
    assert census["overall"]["rust"] == 2332
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
export PYTHONDONTWRITEBYTECODE=1
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
.venv/bin/python -m pytest tests/test_cost_census.py -q
```

Expected: collection error — `ModuleNotFoundError: No module named 'eval.cost_census'`.

- [ ] **Step 3: Write the implementation**

Create `eval/cost_census.py`:

```python
"""Cost census: where the oxide/rust token surplus actually sits.

The demand census (``eval/demand_census.py``) counts what models ATTEMPT
to write. This module counts what correct programs COST. Wave 2 proved
the two disagree: ``swap`` and index assignment had near-zero reply
demand and carried the single largest token surplus in the corpus, so a
slate gated on demand alone deferred the most expensive gap in the
language. Wave 3 gates on both.

A separate module rather than another section of ``demand_census.py``:
that file is already 954 lines and flagged for a split.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from eval.token_match import qwen_counter
from eval.tokenizer_pin import TOKENIZER_FILE
from eval.train_corpus import PAIRS_ROOT, load_train_tasks

RESULTS_DIR = Path("eval/results/v04-cost-census")


@dataclass(frozen=True)
class PairCost:
    """One reference pair's token cost in both arms."""

    task: str
    cls: str
    oxide_tokens: int
    rust_tokens: int

    @property
    def surplus(self) -> int:
        """Signed: NEGATIVE where oxide wins. Never clipped at zero --
        structs/option runs negative in the real corpus and cancels most
        of the strings surplus, so clipping would inflate the total."""
        return self.oxide_tokens - self.rust_tokens

    @property
    def ratio(self) -> float | None:
        """None rather than a fabricated number if a rust side is empty."""
        if self.rust_tokens == 0:
            return None
        return self.oxide_tokens / self.rust_tokens


def pair_costs(count: Callable[[str], int]) -> tuple[list[PairCost], list[str]]:
    """Every reference pair's cost, plus the ids of pairs that could not
    be measured. An unreadable pair is DROPPED and named -- never scored
    zero, which would read as "this pair costs nothing"."""
    tasks = load_train_tasks()
    costs: list[PairCost] = []
    dropped: list[str] = []
    for tid in sorted(tasks):
        try:
            oxide = (PAIRS_ROOT / tid / "oxide.ox").read_text(encoding="utf-8")
            rust = (PAIRS_ROOT / tid / "rust.rs").read_text(encoding="utf-8")
        except OSError:
            dropped.append(tid)
            continue
        costs.append(PairCost(tid, tasks[tid]["class"], count(oxide), count(rust)))
    return costs, dropped


def rank_by_surplus(costs: list[PairCost]) -> list[PairCost]:
    """Most expensive first. Ties break on task id so the ranking is
    reproducible rather than input-order dependent."""
    return sorted(costs, key=lambda c: (-c.surplus, c.task))


def class_subtotals(costs: list[PairCost]) -> dict[str, dict]:
    subs: dict[str, dict] = {}
    for c in costs:
        entry = subs.setdefault(c.cls, {"oxide": 0, "rust": 0})
        entry["oxide"] += c.oxide_tokens
        entry["rust"] += c.rust_tokens
    for entry in subs.values():
        entry["surplus"] = entry["oxide"] - entry["rust"]
        entry["ratio"] = (
            None if entry["rust"] == 0 else entry["oxide"] / entry["rust"]
        )
    return subs


def build_cost_census() -> dict:
    costs, dropped = pair_costs(qwen_counter())
    subs = class_subtotals(costs)
    overall_ox = sum(c.oxide_tokens for c in costs)
    overall_rs = sum(c.rust_tokens for c in costs)
    return {
        "tokenizer": {
            "path": str(TOKENIZER_FILE),
            "sha256": _tokenizer_sha256(),
        },
        "dropped": dropped,
        "pairs": [
            {
                "task": c.task,
                "class": c.cls,
                "oxide": c.oxide_tokens,
                "rust": c.rust_tokens,
                "surplus": c.surplus,
                "ratio": c.ratio,
            }
            for c in rank_by_surplus(costs)
        ],
        "classes": subs,
        "overall": {
            "oxide": overall_ox,
            "rust": overall_rs,
            "surplus": overall_ox - overall_rs,
            "ratio": None if overall_rs == 0 else overall_ox / overall_rs,
        },
    }


def _tokenizer_sha256() -> str:
    import hashlib

    return hashlib.sha256(Path(TOKENIZER_FILE).read_bytes()).hexdigest()


def render_report(census: dict) -> str:
    lines = [
        "# v0.4 Cost Census",
        "",
        "Per-pair oxide/rust token surplus over the 40 committed reference",
        "pairs, ranked. The demand census counts what models attempt; this",
        "counts what correct programs cost. Surplus is signed -- negative",
        "means oxide wins -- and is never clipped.",
        "",
        f"Tokenizer: `{census['tokenizer']['path']}` "
        f"sha256 `{census['tokenizer']['sha256'][:16]}...`",
        f"Dropped (unmeasured, named not zeroed): {census['dropped'] or 'none'}",
        "",
        "## Ranked by surplus",
        "",
        "| task | class | oxide | rust | surplus | ratio |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for p in census["pairs"]:
        ratio = "n/a" if p["ratio"] is None else f"{p['ratio']:.3f}"
        lines.append(
            f"| {p['task']} | {p['class']} | {p['oxide']} | {p['rust']} "
            f"| {p['surplus']:+d} | {ratio} |"
        )
    lines += ["", "## Class subtotals", "",
              "| class | oxide | rust | surplus | ratio |", "|---|---:|---:|---:|---:|"]
    for cls in sorted(census["classes"]):
        e = census["classes"][cls]
        ratio = "n/a" if e["ratio"] is None else f"{e['ratio']:.4f}"
        lines.append(
            f"| {cls} | {e['oxide']} | {e['rust']} | {e['surplus']:+d} | {ratio} |")
    o = census["overall"]
    ratio = "n/a" if o["ratio"] is None else f"{o['ratio']:.4f}"
    lines += [f"| **overall** | **{o['oxide']}** | **{o['rust']}** "
              f"| **{o['surplus']:+d}** | **{ratio}** |", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.cost_census")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR)
    args = parser.parse_args(argv)
    census = build_cost_census()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cost_census.json").write_text(
        json.dumps(census, indent=2) + "\n", encoding="utf-8")
    (args.out / "REPORT.md").write_text(render_report(census), encoding="utf-8")
    print(f"cost census written to {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
export PYTHONDONTWRITEBYTECODE=1
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
.venv/bin/python -m pytest tests/test_cost_census.py -q
```

Expected: 7 passed.

- [ ] **Step 5: Mutation-check the three load-bearing behaviours**

For each mutation: apply it, purge `__pycache__`, run the tests, confirm a FAILURE, restore, purge again, confirm green. A mutation that survives is a defect in the test, not a pass.

1. In `PairCost.surplus`, change `self.oxide_tokens - self.rust_tokens` to `max(0, self.oxide_tokens - self.rust_tokens)` → `test_surplus_is_signed_never_clipped` and the acceptance test must FAIL.
2. In `rank_by_surplus`, change `-c.surplus` to `c.surplus` → `test_rank_by_surplus_orders_most_expensive_first` and the acceptance test must FAIL.
3. In `pair_costs`, replace the `except OSError: dropped.append(tid); continue` block with `except OSError: costs.append(PairCost(tid, tasks[tid]["class"], 0, 0)); continue` → `test_pair_costs_names_unreadable_pairs_instead_of_scoring_them_zero` must FAIL.

- [ ] **Step 6: Generate the committed artifact**

```bash
.venv/bin/python -m eval.cost_census
head -20 eval/results/v04-cost-census/REPORT.md
```

Expected: the ranked table leads with n043 (+82), n050 (+60), n045 (+40); overall row reads 2536 / 2332 / +204 / 1.0875.

- [ ] **Step 7: Commit**

```bash
git add eval/cost_census.py tests/test_cost_census.py eval/results/v04-cost-census/
git commit -m "feat: cost census — per-pair token-surplus attribution

The demand census counts what models attempt; this counts what correct
programs cost. Wave 2 proved they disagree: swap and index assignment
had near-zero reply demand and carried the corpus's largest surplus.

Surplus is signed and never clipped -- structs/option runs negative and
cancels most of the strings surplus, so clipping would inflate the
total. Unmeasurable pairs are named in a dropped list, never scored 0."
```

---

## Task 2: Two-eyed gate ruling (controller, inline — not a subagent task)

The controller reads `eval/results/v04-cost-census/REPORT.md` beside `eval/results/v04-census2/REPORT.md`, records the ruling in the ledger, and states which constructs ship.

**Expected ruling, from the evidence already in hand** (restate it against the freshly generated census rather than assuming):
- **SHIP `swap(v, i, j)`** — cost rank 1 (n043, +82; projected 142 → 60 tokens, exact parity with Rust).
- **SHIP `reverse(v)`** — cost rank 2 (n050, +60; projected 103 → 39).
- **SHIP `set(v, i, x)`** — demand 18 present / 18 rejected on the amp arms; cost-general. Measured NOT to substitute for `swap` (n043 with `set` alone is 99 tokens vs 60 with `swap`).
- **DEFER with counts:** closures/predicate surface (worth ~41 tokens across n046 + n065, against ~146 for the two builtins — see spec §8); `if let` (68 vs the 89 bar); strings vocabulary (class at 1.064, residual not pattern-shaped).

If the regenerated cost census ranks differently, the gate follows the census, not this paragraph, and the divergence is recorded.

---

## Task 3: The three Vec builtins

**Files:**
- Modify: `src/sema/types.py` (`BUILTINS` dict, after the `"count"` entry)
- Modify: `src/codegen/support.py` (`_PRELUDE_FNS` tuple and `BUILTIN_REF` dict)
- Modify: `src/parser/expressions.py` (`BUILTIN_METHOD_NAMES` frozenset)
- Create: `tests/test_v04_wave3.py`

**Interfaces:**
- Consumes: `BuiltinSig(params, ret, modes, generics)` from `src/sema/types.py`; type constructors `TCon("Vec", (_A,))`, `INT`, `_A` already in scope in that module.
- Produces: three callable builtins usable as `swap(v, i, j)`, `reverse(v)`, `set(v, i, x)`, each consuming and returning the vector (`v = swap(v, 0, last)`), matching `sort`'s existing convention.

**Design ruling to record in SPEC §60 before writing code — out-of-range behaviour:** `set` and `swap` transpile to Rust's own panicking operations (`v[i] = x`, `v.swap(i, j)`), so an out-of-range index panics exactly as the Rust control does. Rationale: returning `Option<Vec<T>>` would cost tokens at every in-range call site to serve a case the type system cannot check, defeating the construct's purpose; a silent no-op is rejected outright as a value that looks like a successful operation and is not. This makes `set`/`swap` the first Oxide constructs that can panic, and the identical-stdout law is preserved because both arms panic identically.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_v04_wave3.py`:

```python
"""Runtime + diagnostic tests for the v0.4 wave-3 Vec builtins:
``swap``/``reverse``/``set``, gate-ruled by the cost census (Task 2).

Compile-and-run helper mirrors ``tests/test_v04_builtins.py``.
"""
from __future__ import annotations

import os
import subprocess

import pytest

from eval.rustc_adapter import find_rustc
from src.codegen.rust import transpile
from src.sema.analyze import analyze, diag_codes

_rustc_candidate = find_rustc()
RUSTC = _rustc_candidate if os.path.exists(_rustc_candidate) else None
requires_rustc = pytest.mark.skipif(RUSTC is None, reason="rustc not available")


def codes(src: str) -> list[str]:
    return diag_codes(analyze(src))


def run_oxide(src: str, tmp_path) -> str:
    rust_text = transpile(src)
    rs = tmp_path / "main.rs"
    rs.write_text(rust_text)
    out = tmp_path / "bin"
    proc = subprocess.run(
        [RUSTC, "--edition", "2021", str(rs), "-o", str(out)],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return subprocess.run([str(out)], capture_output=True, text=True).stdout


@requires_rustc
def test_swap_exchanges_two_positions(tmp_path):
    src = """fn main() {
    let v = vec(1, 2, 3, 4, 5)
    let last = len(v) - 1
    v = swap(v, 0, last)
    for x in v {
        print(x)
    }
}
"""
    assert run_oxide(src, tmp_path) == "5\n2\n3\n4\n1\n"


@requires_rustc
def test_reverse_reverses_and_composes_with_sort(tmp_path):
    src = """fn main() {
    let v = vec(2, 9, 5)
    v = reverse(sort(v))
    for x in v {
        print(x)
    }
}
"""
    assert run_oxide(src, tmp_path) == "9\n5\n2\n"


@requires_rustc
def test_set_replaces_one_element(tmp_path):
    src = """fn main() {
    let v = vec(7, 8)
    v = set(v, 1, 99)
    for x in v {
        print(x)
    }
}
"""
    assert run_oxide(src, tmp_path) == "7\n99\n"


@requires_rustc
def test_set_works_on_non_copy_elements(tmp_path):
    """The VALUE slot is "own" -- a Str is genuinely moved in."""
    src = """fn main() {
    let v = vec("a", "b")
    v = set(v, 0, "z")
    for s in v {
        print_str(s)
    }
}
"""
    assert run_oxide(src, tmp_path) == "z\nb\n"


def test_swapped_vector_is_consumed_not_aliased():
    """swap consumes its vector like sort does: using the OLD binding
    after the call is a linearity error, not a silent alias."""
    src = """fn main() {
    let v = vec(1, 2)
    let w = swap(v, 0, 1)
    print(len(v))
}
"""
    assert "OX0101" in codes(src)


def test_method_form_sugar_accepts_the_new_builtins():
    src = """fn main() {
    let v = vec(3, 1, 2)
    v = v.reverse()
    print(len(v))
}
"""
    assert codes(src) == []


def test_builtin_method_names_stays_in_sync_with_builtins():
    """tests/test_parser.py pins this too; restated here so a wave-3
    seam miss fails in the wave's own file."""
    from src.parser.expressions import BUILTIN_METHOD_NAMES
    from src.sema.types import BUILTINS

    for name in ("swap", "reverse", "set"):
        assert name in BUILTINS
        assert name in BUILTIN_METHOD_NAMES
```

The `vec("a", "b")` shape was verified to analyze cleanly (zero diagnostics) before this plan was written — string literals are `Str` directly, there is no constructor call.

- [ ] **Step 2: Run to verify failure**

```bash
export PYTHONDONTWRITEBYTECODE=1
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
.venv/bin/python -m pytest tests/test_v04_wave3.py -q
```

Expected: failures naming `swap`/`reverse`/`set` as unknown functions.

- [ ] **Step 3: Add the type signatures**

In `src/sema/types.py`, immediately after the `"count"` entry in `BUILTINS`:

```python
    # ---- v0.4 wave-3 builtins (Task 2 two-eyed gate ruling: swap/reverse/
    # set, ranked by the COST census -- see eval/cost_census.py), modes
    # pinned ----
    # All three consume and return the vector, mirroring `sort`: they are
    # in-place Rust operations wrapped in the project's owned-in/owned-out
    # convention. The INT index slots are "read" for the same reason
    # `get`'s and `range`'s are -- an index is inspected, never consumed.
    # `set`'s VALUE slot is "own": like `push`'s inserted value, it is
    # genuinely transferred into the vector.
    "swap": BuiltinSig(
        params=(TCon("Vec", (_A,)), INT, INT),
        ret=TCon("Vec", (_A,)),
        modes=("own", "read", "read"),
        generics=(_A,),
    ),
    "reverse": BuiltinSig(
        params=(TCon("Vec", (_A,)),),
        ret=TCon("Vec", (_A,)),
        modes=("own",),
        generics=(_A,),
    ),
    "set": BuiltinSig(
        params=(TCon("Vec", (_A,)), INT, _A),
        ret=TCon("Vec", (_A,)),
        modes=("own", "read", "own"),
        generics=(_A,),
    ),
```

- [ ] **Step 4: Add the prelude functions and ref-form tuples**

In `src/codegen/support.py`, append to `_PRELUDE_FNS` (these three were rustc-verified before this plan was written — they compile and produce `5 2 3 4 1` / `9 5 2` / `7 99`):

```python
        (
            "swap",
            "fn swap<T>(mut v: Vec<T>, i: i64, j: i64) -> Vec<T> {\n"
            "    v.swap(i as usize, j as usize);\n"
            "    v\n"
            "}",
        ),
        (
            "reverse",
            "fn reverse<T>(mut v: Vec<T>) -> Vec<T> {\n"
            "    v.reverse();\n"
            "    v\n"
            "}",
        ),
        (
            "set",
            "fn set<T>(mut v: Vec<T>, i: i64, x: T) -> Vec<T> {\n"
            "    v[i as usize] = x;\n"
            "    v\n"
            "}",
        ),
```

In the same file, add to `BUILTIN_REF`:

```python
    # v0.4 wave-3 (Task 3): all slots by value -- the vector is consumed
    # (like `sort`), the indices are Copy i64, and `set`'s value is moved
    # in (like `push`'s). No slot takes ref-form.
    "swap": (False, False, False),
    "reverse": (False,),
    "set": (False, False, False),
```

- [ ] **Step 5: Add the method-form names**

In `src/parser/expressions.py`, add `"reverse"`, `"set"`, and `"swap"` to the `BUILTIN_METHOD_NAMES` frozenset, keeping the set alphabetically sorted as the existing entries are. `tests/test_parser.py:551` asserts `BUILTIN_METHOD_NAMES == set(BUILTINS)`; omitting any of the three fails that test.

- [ ] **Step 6: Run the wave-3 tests and the full suite**

```bash
export PYTHONDONTWRITEBYTECODE=1
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
.venv/bin/python -m pytest tests/test_v04_wave3.py -q
.venv/bin/python -m pytest -q
```

Expected: wave-3 tests pass; full suite ≥ 1642 + the new tests, 3 deselected, zero failures.

- [ ] **Step 7: Mutation-check the linearity modes**

Change `"swap"`'s first mode from `"own"` to `"read"`, purge `__pycache__`, run `tests/test_v04_wave3.py::test_swapped_vector_is_consumed_not_aliased` — it must FAIL. Restore, purge, confirm green. A mode that can be flipped without a test noticing is unpinned.

- [ ] **Step 8: Commit**

```bash
git add src/sema/types.py src/codegen/support.py src/parser/expressions.py tests/test_v04_wave3.py
git commit -m "feat: swap/reverse/set Vec builtins — the cost census's top-ranked gaps

swap and reverse were invisible to the demand census (models do not
attempt constructs they have not been taught) while carrying +142 of the
corpus's +204 net surplus between them. set ships on demand evidence
(18/18 mechanical rejections on the amp arms) and is measured NOT to
substitute for swap: n043 costs 99 tokens with set alone, 60 with swap.

All three consume and return the vector, mirroring sort. Out-of-range
indices panic exactly as the Rust control does -- see SPEC 60."
```

---

## Task 4: SPEC §60 and card v0.5

**Files:**
- Modify: `SPEC.md` (append §60)
- Modify: `LANGUAGE_CARD.md`, `LANGUAGE_CARD_EXPLICIT.md`
- Modify: `tests/test_cards.py` (only if the word limit must move)

**Interfaces:**
- Consumes: the three builtins from Task 3, spelled exactly `swap(v, i, j)`, `reverse(v)`, `set(v, i, x)`.

- [ ] **Step 1: Append SPEC §60**

Write these subsections:
- **60.1 `swap`, `reverse`, `set`** — signatures, linearity modes with the reasoning (mirroring how §59.1 documents `count`), and the owned-in/owned-out convention.
- **60.2 Out-of-range behaviour** — the panic ruling and its rationale verbatim from Task 3's design ruling above; note explicitly that these are the first Oxide constructs that can panic, and that the identical-stdout law survives because both arms panic identically.
- **60.3 Cost-census record** — what the census is, the ranked top three, and the method finding: demand and cost are different quantities, and wave 2's gate read only demand while deferring the corpus's most expensive gap.
- **60.4 Bias-rule amendment** — the amended rule from spec §4, verbatim, with the withdrawn per-statement Rust gate marked as superseded (never deleted), following §58.2's convention for amending in place.
- **60.5 Card update** — what changed in both cards.
- **60.6 Stale-text sweep** — grep `SPEC.md` and `docs/superpowers/specs/2026-08-09-v03-taxonomy.md` for any claim that Oxide has no index assignment, no `swap`, or no panicking construct; amend every hit in place, old text struck through, never deleted. Record "no hits" explicitly if there are none.

- [ ] **Step 2: Update both cards**

Add the three builtins to `LANGUAGE_CARD.md` and `LANGUAGE_CARD_EXPLICIT.md`, in each card's own voice, placed beside the existing Vec vocabulary (`sort`/`min`/`max`/`sum`/`contains`/`count`). Include the owned-in/owned-out spelling (`v = swap(v, 0, last)`) since that is the shape models must reproduce.

- [ ] **Step 3: Run the card tests**

```bash
export PYTHONDONTWRITEBYTECODE=1
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
.venv/bin/python -m pytest tests/test_cards.py -q
```

The core card was 1059 words against a `CORE_WORD_LIMIT` of 1100, so three builtins may cross it. If `test_core_card_under_1100_words` fails, raise `CORE_WORD_LIMIT` **non-silently**: change the constant, and state the new value and the reason in SPEC §60.5. Do not trim card content to duck the limit without saying so. Then re-verify the pin still bites by temporarily setting the limit below the current count and confirming the test fails.

`test_card_word_counts_within_ten_percent` requires the two cards stay within 10% of each other — add comparable content to both.

- [ ] **Step 4: Commit**

```bash
git add SPEC.md LANGUAGE_CARD.md LANGUAGE_CARD_EXPLICIT.md tests/test_cards.py
git commit -m "docs: SPEC 60 + card v0.5 — swap/reverse/set, panic ruling, bias amendment"
```

---

## Task 5: Re-author references under the amended bias rule, and read the static endpoints

**Files:**
- Modify: `eval/train/pairs/*/oxide.ox` (only; `rust.rs` is protected)
- Regenerate: `eval/train/matched/` via `python -m eval.token_match`

**Interfaces:**
- Consumes: the three builtins (Task 3) and the amended bias rule (Global Constraints).

- [ ] **Step 1: Apply the four measured substitutions**

These were counted before the plan was written; the token deltas are the expected result, not a target to hit by other means.

`eval/train/pairs/n043/oxide.ox` (142 → 60 tokens):

```
fn main() {
    let v = vec(1, 2, 3, 4, 5)
    let last = len(v) - 1
    v = swap(v, 0, last)
    for x in v {
        print(x)
    }
}
```

`eval/train/pairs/n050/oxide.ox` (103 → 39):

```
fn main() {
    let v = vec(2, 9, 5)
    v = reverse(sort(v))
    for x in v {
        print(x)
    }
}
```

`eval/train/pairs/n045/oxide.ox` (81 → 55, using `unwrap_or`, shipped in wave 1 and never applied here):

```
fn main() {
    let v = vec(6, 7, 8, 9)
    print(unwrap_or(get(v, 0), 0))
    print(unwrap_or(get(v, len(v) - 1), 0))
}
```

`eval/train/pairs/n046/oxide.ox` (90 → 86) and `eval/train/pairs/n065/oxide.ox` (81 → 79): replace `under = under + 1`, `over = over + 1`, and `above = above + 1` with `under += 1`, `over += 1`, `above += 1`. Under wave 2's withdrawn gate these were forbidden because the Rust control uses `.iter().filter(...).count()`; the amended rule permits them.

- [ ] **Step 2: Sweep the remaining 35 pairs for missed substitutions**

For every pair not touched above, check whether any *shipped* construct (`sort`, `min`, `max`, `sum`, `contains`, `count`, `unwrap_or`, `range`, `+=`/`-=`/`*=`, `swap`, `reverse`, `set`) would replace a hand-rolled mechanism without restructuring the program. Apply every admissible one — under the amended rule a missed substitution is a defect. Record each change with its token delta; record explicitly that a pair was checked and needed nothing.

- [ ] **Step 3: Verify every changed pair against the oracle**

```bash
.venv/bin/python -m pytest tests/test_token_match_corpus.py -q
.venv/bin/python -c "
from eval.train_corpus import PAIRS_ROOT, load_train_tasks, validate_pair
tasks = load_train_tasks()
bad = []
for tid in sorted(tasks):
    r = validate_pair(tasks[tid], PAIRS_ROOT/tid/'oxide.ox', PAIRS_ROOT/tid/'rust.rs')
    if not r.get('ok', False):
        bad.append((tid, r))
print('FAILURES:', bad if bad else 'none — all 40 pairs green')
"
git diff --stat eval/train/pairs/
git diff --exit-code eval/train/pairs/*/rust.rs && echo 'rust.rs untouched — correct'
```

Expected: all 40 pairs green, byte-identical stdout, and an empty diff on every `rust.rs`.

- [ ] **Step 4: Rebuild the matched corpus and read the static endpoints**

```bash
.venv/bin/python -m eval.token_match
.venv/bin/python -m eval.cost_census
sed -n '/## Class subtotals/,$p' eval/results/v04-cost-census/REPORT.md
```

Record the per-class and overall ratios against the targets: overall ≤ 1.02, vectors ≤ 1.10, strings ≤ 1.07, arithmetic ≤ 1.02, structs ≤ 0.93. Projected from the four measured substitutions alone: overall ≈ 1.011, vectors ≈ 1.08. **Report each endpoint as HIT or MISS. A miss is reported as a miss** — never re-authored toward the target after seeing the number.

- [ ] **Step 5: Commit**

```bash
git add eval/train/pairs/ eval/train/matched/ eval/results/v04-cost-census/
git commit -m "feat: wave-3 re-authored references under the amended bias rule

<per-pair token deltas here, one line each>

rust.rs byte-identical everywhere; validate_pair green on all 40 pairs;
stdout byte-identical to frozen expected_stdout; contamination 0 hits."
```

---

## Task 6: Dynamic loop (controller, inline — rented GPU)

Runs only when the capacity poll signals community GPU availability. Sequence, unchanged from wave 2 except where noted:

1. Boot the pod; **verify `torch.cuda` works BEFORE committing hours** (the wave-2 driver-mismatch lesson); pin `allowedCudaVersions` in the spec JSON.
2. Upload the repo at the Task-5 commit; run `scripts/runpod/pod_setup.sh`, then the model downloads and base conversions.
3. Amplify with card v0.5 at 3 sizes × 20 seeds, **temperature 0.8 for corpus generation only** (measurement arms stay pinned at 0.2).
4. Pooled rematch against the committed amp pools; **corpus-scale gate ≥ 15k supervised tokens per arm** — a hard STOP, not a target to negotiate.
5. Retrain both arms symmetrically; merge and convert to q8_0.
6. Four-arm campaign: `base-ox-7`, `base-rs-7`, `tune-ox-7`, `tune-rs-7`.
7. Read G1 (control within ±0.10 of 0.565; tune-ox floor 0.455 met), G2 uptake per spelling, and the **composition-controlled paired ratio** via `eval.experiment_report.paired_tokens_to_green` (SPEC §59.7 binds this as primary; the unconditional mean is secondary and binds nothing).
8. **Count-verified rsync home of results, matched corpus, amp pool, train logs, and ADAPTERS** — verify by file count, never by `du`. Adapter preservation is mandatory.
9. Terminate the pod; verify zero pods twice; record spend.

---

## Task 7: Report, artifacts, and close (controller, inline)

- [ ] Land `eval/results/v04-campaign3/` (four arms + matched corpus) and the amplification pool.
- [ ] Write `eval/results/v04-campaign3/REPORT.md`: what shipped and why (both censuses' counts), static endpoint table with HIT/MISS per class, the corpus-scale gate outcome, the dynamic table, G1 and G2 reads, the composition-controlled ratio against wave 2's 1.067, spend, and a feed-forward section ending the report.
- [ ] Feed-forward must carry at minimum: whether below-1.00 is now within reach and what it would cost (the predicate-count shapes in n046/n065, ~41 tokens); the `-=`/`*=` uptake re-read; whatever the cost census ranks next; and the census debt (fold `count`/`swap`/`reverse`/`set` into the demand census families, brace-masking fix, `/=` unmatched, split the 954-line `demand_census.py`).
- [ ] Full suite green; commit; push; verify `origin` in sync.
- [ ] Close the ledger, delete the SDD workspace, update memory, and report to the owner with every `Ruling:` line collected.

---

## Self-Review

**Spec coverage.** §1 baseline → Task 1's acceptance test pins it. §2 finding → Task 1 + SPEC §60.3. §3 cost census → Task 1. §4 bias amendment → Global Constraints + Task 5 + SPEC §60.4. §5 slate → Tasks 2, 3. §5's open out-of-range question → answered in Task 3's design ruling and recorded in SPEC §60.2. §6 endpoints → Task 5 step 4 (static), Task 6 step 7 (dynamic, G1, G2, corpus gate). §7 mechanics → Tasks 6, 7. §8 out of scope → Task 2's deferral list. §9 authorization → Task 6's trigger. No gaps.

**Placeholder scan.** One deliberate fill-in remains: the per-pair token deltas in Task 5's commit message, which cannot be known before the sweep runs. Everything else is verbatim. Before this plan was written, the three prelude functions were compiled and run under rustc (output `5 2 3 4 1` / `9 5 2` / `7 99`), `validate_pair`'s `{"ok", "reasons"}` return shape was read, and the `vec("a", "b")` test shape was analyzed clean — so an implementer transcribing this plan faithfully is transcribing verified code, which is the wave-2 lesson about plans that carry code.

**Type consistency.** `PairCost(task, cls, oxide_tokens, rust_tokens)` is constructed identically in the tests and the implementation; `pair_costs` returns `(list[PairCost], list[str])` everywhere it appears; `class_subtotals` keys (`oxide`, `rust`, `surplus`, `ratio`) match between the implementation, the tests, and `render_report`. The three builtins are spelled `swap(v, i, j)` / `reverse(v)` / `set(v, i, x)` identically in the sema entries, prelude, tests, card, and re-authored references.
