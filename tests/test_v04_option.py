"""Blind-ish runtime + diagnostic tests for `unwrap_or` (Task 5 of the v0.4
efficiency cycle, census gate ruling: `unwrap_or` ONLY -- `if let` is
DEFERRED to wave 2 and is not touched here).

Compile-and-run helper mirrors `tests/test_v04_builtins.py` (itself
mirroring `tests/test_v02_codegen.py`/`tests/test_v021_codegen.py`'s
per-wave-file pattern).

Ownership modes (recorded here, detailed in the task-5 report): both `o`
and `d` are "own" (consuming). `o` mirrors the language's two EXISTING
ways of reaching inside an Option -- match's scrutinee is a MOVE use
(section 28) and `?`'s operand is a MOVE use (section 36) -- neither
treats "reading" an Option's payload as a non-consuming borrow, so
`unwrap_or`'s `o` follows that convention rather than get/min/max's
read-mode Vec param (those READ a Vec to PRODUCE an Option; there is no
existing precedent for reading an Option's payload without consuming
it). `d` is "own" because it may become the returned value verbatim on
the None path.
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
# 1-3: runtime stdout cases (Some path, None path, method form).
# ---------------------------------------------------------------------------

CASES = [
    (
        "some_path_composes_with_min",
        "fn main() {\n    print(unwrap_or(min(vec(3, 1, 2)), 0))\n}\n",
        "1\n",
    ),
    (
        # min of an empty vec is None; unwrap_or's default (an Int literal)
        # supplies enough concrete type context on its own to resolve
        # vec()'s element type through the shared generic -- unlike Task
        # 3's standalone `min(e)` fixture, no `let e: Vec<Int> = ...`
        # annotation is needed here (verified directly: zero diagnostics).
        "none_path_prints_default",
        "fn main() {\n    print(unwrap_or(min(vec()), 42))\n}\n",
        "42\n",
    ),
    (
        "method_form",
        "fn main() {\n"
        "    let v = vec(4, 5, 1)\n"
        "    print(min(v).unwrap_or(99))\n"
        "}\n",
        "1\n",
    ),
]


@requires_rustc
@pytest.mark.parametrize(
    ("name", "source", "expected_stdout"),
    CASES,
    ids=[case[0] for case in CASES],
)
def test_unwrap_or_runtime_stdout(name, source, expected_stdout, tmp_path):
    assert compile_and_run(source, tmp_path) == expected_stdout


def test_unwrap_or_cases_diagnostics_clean():
    for _name, source, _expected in CASES:
        assert codes(source) == []


# ---------------------------------------------------------------------------
# 4-5: diagnostics (existing OX-code classes only, following
# tests/test_v04_builtins.py's DIAGNOSTIC_CASES pattern).
# ---------------------------------------------------------------------------

DIAGNOSTIC_CASES = [
    pytest.param(
        'fn main() {\n    print(unwrap_or(min(vec(1, 2, 3)), "x"))\n}\n',
        ["OX0300"],
        id="str-default-for-option-int-is-a-type-error",
    ),
    pytest.param(
        "fn main() {\n    print(unwrap_or(min(vec(1, 2, 3))))\n}\n",
        ["OX0303"],
        id="unwrap-or-arity-error",
    ),
]


@pytest.mark.parametrize(("source", "expected_codes"), DIAGNOSTIC_CASES)
def test_diagnostics(source, expected_codes):
    assert codes(source) == expected_codes


# ---------------------------------------------------------------------------
# 6: ownership-convention pins. Both `o` and `d` are "own" (consuming) --
# see the module docstring for why. Each fixture reuses the value after
# unwrap_or has consumed it and asserts the resulting use-after-move
# diagnostic, rather than asserting the value is "still usable" (which
# would be true only under the read/non-consuming convention this task
# determined does NOT hold).
# ---------------------------------------------------------------------------


def test_o_is_consumed_by_unwrap_or():
    """`o` is moved into unwrap_or; a later `match o` is a double-move
    (OX0401: match's own scrutinee use is itself a MOVE use, section 28) --
    the double-move code is itself further evidence unwrap_or's first slot
    is "own", not "read"."""
    source = (
        "fn main() {\n"
        "    let o = min(vec(1, 2, 3))\n"
        "    let r = unwrap_or(o, 0)\n"
        "    match o {\n"
        '        Some(m) => print(m),\n'
        '        None => print_str("none"),\n'
        "    }\n"
        "    print(r)\n"
        "}\n"
    )
    assert codes(source) == ["OX0401"]


def test_d_is_consumed_by_unwrap_or():
    """`d` is moved into unwrap_or (it may become the returned value
    verbatim on the None path); a later read of `d` is OX0400."""
    source = (
        "fn main() {\n"
        "    let vv = vec(vec(1, 2))\n"
        "    let d = vec(9, 9)\n"
        "    let r = unwrap_or(get(vv, 5), d)\n"
        "    print(len(d))\n"
        "}\n"
    )
    assert codes(source) == ["OX0400"]


# ---------------------------------------------------------------------------
# 7: shadowing -- a user `fn unwrap_or` wins over the builtin (mirrors
# tests/test_v04_shadowing.py's single-construct pattern).
# ---------------------------------------------------------------------------

SHADOW_SRC = (
    "fn unwrap_or(o: Option<Int>, d: Int) -> Int {\n"
    '    print_str("user unwrap_or")\n'
    "    print(d)\n"
    "    match o {\n"
    "        Some(_) => -1,\n"
    "        None => -2,\n"
    "    }\n"
    "}\n"
)


@requires_rustc
def test_shadowing_fn_wins_the_free_call_form(tmp_path):
    source = SHADOW_SRC + (
        "fn main() {\n    print(unwrap_or(min(vec(1, 2, 3)), 0))\n}\n"
    )
    # The builtin would print just "1\n" (min of [1,2,3] with no side
    # effect). The user fn's marker line, echoed d, and forced -1 return
    # can only appear if the user's definition actually ran.
    assert compile_and_run(source, tmp_path) == "user unwrap_or\n0\n-1\n"


def test_shadowing_fn_wins_the_free_call_form_diagnostics_clean():
    source = SHADOW_SRC + (
        "fn main() {\n    print(unwrap_or(min(vec(1, 2, 3)), 0))\n}\n"
    )
    assert codes(source) == []
