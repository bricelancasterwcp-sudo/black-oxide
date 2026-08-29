"""Blind-ish runtime + diagnostic tests for `range` (Task 4 of the v0.4
efficiency cycle).

The census gate RE-SCOPED this task, overriding the brief's grammar/lexer
approach: ranges ship as a BUILTIN (`range(a, b)`), not as `..` syntax.
The census measured models writing `range(a, b)` calls 773-to-292 over
`a..b` in oxide contexts, and the §54 admit-what-they-write law picks the
spelling.

Investigation finding, load-bearing for this file's scope: `range` is NOT
new. It has shipped as a v0.2 builtin (SPEC.md section 28) since the
repository's very first commit --

    "range": BuiltinSig(params=(INT, INT), ret=TCon("Vec", (INT,)),
                         modes=("read", "read"), generics=())

-- with its prelude fn (`fn range(a: i64, b: i64) -> Vec<i64> {
(a..b).collect() }`), its `BUILTIN_REF` entry (`(False, False)`, Int is
Copy-class, mirroring `get`'s index argument), and its
`BUILTIN_METHOD_NAMES` entry (receiver-first method form) already in
place. Task 3's builtin-shadowing mechanism (commit 6e52a73) is driven
generically off `BUILTINS`/`res.resolve.fns`, so it already covers
`range` with no additional code. This file exists to pin the construct
down with the tests this wave's process requires (including the required
mutation checks against the pre-existing implementation) -- no
src/ changes were needed to satisfy Task 4's construct.

Compile-and-run helper mirrors ``tests/test_v04_builtins.py`` (itself
mirroring ``tests/test_v02_codegen.py``/``tests/test_v021_codegen.py``'s
per-wave-file pattern).
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
# CASES (task's six intents, verbatim in spirit; spelling is `range(a, b)`
# per the gate ruling, not `a..b`).
# ---------------------------------------------------------------------------

CASES = [
    (
        "range_for",
        "fn main() {\n"
        "    for i in range(0, 4) {\n"
        "        print(i)\n"
        "    }\n"
        "}\n",
        "0\n1\n2\n3\n",
    ),
    (
        "range_exprs_as_bounds",
        "fn main() {\n"
        "    let n = 3\n"
        "    for i in range(1, n + 1) {\n"
        "        print(i)\n"
        "    }\n"
        "}\n",
        "1\n2\n3\n",
    ),
    (
        "range_empty_iterates_nothing",
        "fn main() {\n"
        "    for i in range(3, 3) {\n"
        "        print(i)\n"
        "    }\n"
        "    print_str(\"done\")\n"
        "}\n",
        "done\n",
    ),
    (
        "range_empty_when_a_gte_b_not_a_panic",
        "fn main() {\n    print(len(range(5, 2)))\n}\n",
        "0\n",
    ),
    (
        "range_as_plain_vec_value_composes_with_sum",
        "fn main() {\n    let v = range(0, 3)\n    print(sum(v))\n}\n",
        "3\n",
    ),
    (
        "range_method_form_chain",
        "fn main() {\n    print(range(0, 5).contains(3))\n}\n",
        "true\n",
    ),
]


@requires_rustc
@pytest.mark.parametrize(
    ("name", "source", "expected_stdout"),
    CASES,
    ids=[case[0] for case in CASES],
)
def test_range_runtime_stdout(name, source, expected_stdout, tmp_path):
    assert compile_and_run(source, tmp_path) == expected_stdout


# ---------------------------------------------------------------------------
# Diagnostics (existing OX-code classes only, following
# tests/test_v04_builtins.py's / tests/test_sema_types.py's `codes(...)`
# pattern).
# ---------------------------------------------------------------------------

DIAGNOSTIC_CASES = [
    pytest.param(
        'fn main() {\n    for i in range("a", "b") {\n        print(i)\n    }\n}\n',
        ["OX0300", "OX0300"],
        id="range-non-int-arguments-is-a-type-error",
    ),
    pytest.param(
        "fn main() {\n    print(len(range(1)))\n}\n",
        ["OX0303"],
        id="range-arity-error-too-few",
    ),
    pytest.param(
        "fn main() {\n    print(len(range(1, 2, 3)))\n}\n",
        ["OX0303"],
        id="range-arity-error-too-many",
    ),
]


@pytest.mark.parametrize(("source", "expected_codes"), DIAGNOSTIC_CASES)
def test_diagnostics(source, expected_codes):
    assert codes(source) == expected_codes


# ---------------------------------------------------------------------------
# Shadowing (Task 3's mechanism, generic over BUILTINS -- one test mirroring
# tests/test_v04_shadowing.py's pattern, per the task's requirement).
# ---------------------------------------------------------------------------

SHADOW_SRC = (
    "fn range(a: Int, b: Int) -> Int {\n"
    "    a + b\n"
    "}\n"
)


@requires_rustc
def test_shadowing_fn_wins_the_free_call_form(tmp_path):
    source = SHADOW_SRC + "fn main() {\n    print(range(2, 3))\n}\n"
    # The builtin would produce a Vec and fail to type-check against
    # `print`'s generic slot the same way -- but more to the point, the
    # builtin's `range(2, 3)` is never itself printable as "5"; only the
    # user fn's `a + b` can produce that scalar sum.
    assert compile_and_run(source, tmp_path) == "5\n"


def test_shadowing_fn_wins_the_free_call_form_diagnostics_clean():
    source = SHADOW_SRC + "fn main() {\n    print(range(2, 3))\n}\n"
    assert codes(source) == []
