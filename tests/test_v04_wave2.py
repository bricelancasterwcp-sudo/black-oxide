"""Blind-ish runtime + diagnostic tests for the v0.4 wave-2 constructs.

Wave-2 constructs accumulate in this file (mirroring the per-wave-file
pattern of ``tests/test_v04_builtins.py``/``tests/test_v04_ranges.py``,
themselves mirroring ``tests/test_v02_codegen.py``/
``tests/test_v021_codegen.py``).

Task 3 (this file's first construct): ``count(v, x) -> Int`` -- occurrences
of ``x`` in ``v``. The census gate v2 ruling (see
``.superpowers/sdd/2026-08-28-v04-efficiency-wave2/progress.md``) shipped
``count`` alone from the provisional Task-3 slate (``remove_at``/
``first``/``last`` were cut: no demand signal or below the amp-presence
bar). ``count`` is ``contains``'s sibling -- same reading modes for both
arguments (``BUILTINS["contains"]``'s mode note applies verbatim: counting,
like equality comparison, never consumes its operands), same generic-T
shape, same ``BUILTIN_REF`` ref-form-in-both-slots table entry.

Compile-and-run helper mirrors ``tests/test_v04_builtins.py`` /
``tests/test_v04_ranges.py`` (each codegen-wave test file carries its own
copy of the same rustc-invocation shape used by
``tests/test_codegen.py::test_variadic_vec_literal_runtime_stdout_matches_the_push_chain``).
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def codes(src: str) -> list[str]:
    """Run the full pipeline and return the diagnostic code list."""
    return diag_codes(analyze(src))


def compile_rust(rust_text: str, tmp_path) -> object:
    src = tmp_path / "main.rs"
    src.write_text(rust_text)
    out = tmp_path / "oxide_bin"
    proc = subprocess.run(
        [RUSTC, "--edition", "2021", str(src), "-o", str(out)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"rustc failed:\n{proc.stderr}"
    # Identical-stdout law (task constraints): warning-clean compiles.
    assert "warning:" not in proc.stderr, f"rustc emitted warnings:\n{proc.stderr}"
    return out


def compile_and_run(source: str, tmp_path) -> str:
    rust, diags = transpile(source)
    assert diags == [], f"unexpected diagnostics: {[d.code for d in diags]}"
    assert rust is not None
    binary = compile_rust(rust, tmp_path)
    proc = subprocess.run([str(binary)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


# ---------------------------------------------------------------------------
# CASES: count present, count absent, method-form chained with wave-1
# vocabulary (`range`), and an empty vec via the established
# push-then-context idiom (test_v04_builtins.py's `sum_empty_is_zero`
# shape: a throwaway `e`/`f` pair demonstrates push-supplies-context, then
# the bare `g` actually exercises the empty-vec path -- here `g`'s element
# type is pinned by `count`'s own second argument, not by a push, so no
# explicit `Vec<Int>` annotation is needed the way `min_empty_is_none`'s
# `e` required one: `count`'s x parameter shares v's element metavariable
# and is concrete (`5`) at every one of this file's call sites).
# ---------------------------------------------------------------------------

CASES = [
    (
        # Asymmetric on purpose (3 matches out of 5, not an even split):
        # a filter-inverted mutant (counting NON-matches) would report 2
        # here, not 3, so this case alone -- not just the absent case --
        # catches that mutation; an always-0 mutant is caught here too
        # since the expectation is nonzero.
        "count_present",
        "fn main() {\n"
        "    let v = vec(2, 2, 2, 1, 3)\n"
        "    print(count(v, 2))\n"
        "}\n",
        "3\n",
    ),
    (
        "count_absent",
        "fn main() {\n"
        "    let v = vec(1, 2, 2, 3)\n"
        "    print(count(v, 9))\n"
        "}\n",
        "0\n",
    ),
    (
        "count_method_form_chain",
        "fn main() {\n    print(range(0, 5).count(3))\n}\n",
        "1\n",
    ),
    (
        "count_empty_vec",
        "fn main() {\n"
        "    let e = vec()\n"
        "    let f = push(e, 1)\n"
        "    print(len(f))\n"
        "    let g = vec()\n"
        "    print(count(g, 5))\n"
        "}\n",
        "1\n0\n",
    ),
]


@requires_rustc
@pytest.mark.parametrize(
    ("name", "source", "expected_stdout"),
    CASES,
    ids=[case[0] for case in CASES],
)
def test_count_runtime_stdout(name, source, expected_stdout, tmp_path):
    assert compile_and_run(source, tmp_path) == expected_stdout


# ---------------------------------------------------------------------------
# Ownership-consistency: count is a reader (mirrors contains/min/max/sum) --
# it does NOT move its Vec argument.
# ---------------------------------------------------------------------------


@requires_rustc
def test_count_then_len_reader_does_not_move_its_argument(tmp_path):
    source = (
        "fn main() {\n"
        "    let v = vec(1, 2, 2, 3)\n"
        "    print(count(v, 2))\n"
        "    print(len(v))\n"
        "}\n"
    )
    assert compile_and_run(source, tmp_path) == "2\n4\n"


def test_count_then_len_compiles_with_no_diagnostics():
    source = (
        "fn main() {\n"
        "    let v = vec(1, 2, 2, 3)\n"
        "    print(count(v, 2))\n"
        "    print(len(v))\n"
        "}\n"
    )
    assert codes(source) == []


# ---------------------------------------------------------------------------
# Diagnostics (existing OX-code classes only, following
# tests/test_v04_builtins.py's / tests/test_v04_ranges.py's `codes(...)`
# pattern).
# ---------------------------------------------------------------------------

DIAGNOSTIC_CASES = [
    pytest.param(
        "fn main() {\n    let v = vec(1, 2, 3)\n    print(count(v))\n}\n",
        ["OX0303"],
        id="count-arity-error",
    ),
    pytest.param(
        'fn main() {\n    print(count(vec(1, 2, 3), "a"))\n}\n',
        ["OX0300"],
        id="count-type-mismatch-x-vs-element",
    ),
]


@pytest.mark.parametrize(("source", "expected_codes"), DIAGNOSTIC_CASES)
def test_diagnostics(source, expected_codes):
    assert codes(source) == expected_codes


# ---------------------------------------------------------------------------
# Shadowing (Task 3's mechanism, generic over BUILTINS -- one test mirroring
# tests/test_v04_shadowing.py's / tests/test_v04_ranges.py's pattern, per
# the task's requirement).
# ---------------------------------------------------------------------------

SHADOW_SRC = (
    "fn count(v: Vec<Int>, x: Int) -> Int {\n"
    '    print_str("user count")\n'
    "    print(x)\n"
    "    print(len(v))\n"
    "    0\n"
    "}\n"
)


@requires_rustc
def test_shadowing_fn_wins_the_free_call_form(tmp_path):
    source = SHADOW_SRC + "fn main() {\n    print(count(vec(1, 2, 2, 3), 2))\n}\n"
    # The builtin would print just "2\n" (2 occurs twice in the vec, no
    # side effect). The user fn's marker line + echoed args + forced 0
    # can only appear if the user's definition actually ran.
    assert compile_and_run(source, tmp_path) == "user count\n2\n4\n0\n"


def test_shadowing_fn_wins_the_free_call_form_diagnostics_clean():
    source = SHADOW_SRC + "fn main() {\n    print(count(vec(1, 2, 2, 3), 2))\n}\n"
    assert codes(source) == []
