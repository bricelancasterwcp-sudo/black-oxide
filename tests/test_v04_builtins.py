"""Blind-ish runtime + diagnostic tests for the v0.4 Vec builtins (Task 3 of
the v0.4 efficiency cycle): the gate-ruled slate ``sort``/``min``/``max``/
``sum``/``contains``. ``set`` was CUT by the census gate ruling and is not
implemented or tested here.

Compile-and-run helper mirrors ``tests/test_v02_codegen.py`` /
``tests/test_v021_codegen.py`` (each codegen-wave test file carries its own
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
# CASES (brief's programs verbatim, minus the two `set` cases the census
# gate cut; `min_empty_is_none`'s `e` binding is adapted per the brief's
# own caveat -- see the comment on that case below).
# ---------------------------------------------------------------------------

CASES = [
    (
        "sort_basic",
        "fn main() {\n"
        "    let v = vec(9, 2, 7, 4)\n"
        "    let s = sort(v)\n"
        "    for x in s {\n"
        "        print(x)\n"
        "    }\n"
        "}\n",
        "2\n4\n7\n9\n",
    ),
    (
        "sort_method_chain",
        "fn main() {\n"
        "    for x in vec(3, 1, 2).sort() {\n"
        "        print(x)\n"
        "    }\n"
        "}\n",
        "1\n2\n3\n",
    ),
    (
        "min_some",
        "fn main() {\n"
        "    match min(vec(5, 3, 8)) {\n"
        "        Some(m) => print(m),\n"
        "        None => print_str(\"empty\"),\n"
        "    }\n"
        "}\n",
        "3\n",
    ),
    (
        # Brief's fixture had `let e = vec()` with only `min(e)` as usage
        # context. `min`'s param is generic (Vec<T> -> Option<T>) and its
        # result only ever reaches `print(m)` (also fully generic), so no
        # concrete type is ever forced onto e's element metavariable --
        # `_finalize` (src/sema/infer.py) reports OX0302 "ambiguous type"
        # for it. Adapted via the codebase's established empty-vec
        # disambiguation idiom (`let x: Vec<Int> = vec()`, exercised by
        # tests/test_sema_types.py's `let x: Vec<Int> = vec()` cases and
        # surfaced verbatim in the CLI's own OX0302 help text) rather than
        # the push-then-context idiom used for `v`/`w` in this same
        # fixture -- pushing into `e` would populate it, defeating the
        # empty-vec assertion. `v`/`w` are unchanged: push already
        # supplies concrete context for them, exactly like S1's `v`/`v2`.
        "min_empty_is_none",
        "fn main() {\n"
        "    let v = vec()\n"
        "    let w = push(v, 1)\n"
        "    let e: Vec<Int> = vec()\n"
        "    match min(e) {\n"
        "        Some(m) => print(m),\n"
        "        None => print_str(\"empty\"),\n"
        "    }\n"
        "    print(len(w))\n"
        "}\n",
        "empty\n1\n",
    ),
    (
        "max_basic",
        "fn main() {\n"
        "    match max(vec(5, 3, 8)) {\n"
        "        Some(m) => print(m),\n"
        "        None => print_str(\"empty\"),\n"
        "    }\n"
        "}\n",
        "8\n",
    ),
    (
        "sum_basic",
        "fn main() {\n    print(sum(vec(1, 2, 3, 4)))\n}\n",
        "10\n",
    ),
    (
        "sum_empty_is_zero",
        "fn main() {\n"
        "    let e = vec()\n"
        "    let f = push(e, 1)\n"
        "    print(len(f))\n"
        "    let g = vec()\n"
        "    print(sum(g))\n"
        "}\n",
        "1\n0\n",
    ),
    (
        "contains_true_false",
        "fn main() {\n"
        "    let v = vec(1, 2, 3)\n"
        "    print(contains(v, 2))\n"
        "    print(v.contains(9))\n"
        "}\n",
        "true\nfalse\n",
    ),
]


@requires_rustc
@pytest.mark.parametrize(
    ("name", "source", "expected_stdout"),
    CASES,
    ids=[case[0] for case in CASES],
)
def test_builtin_runtime_stdout(name, source, expected_stdout, tmp_path):
    assert compile_and_run(source, tmp_path) == expected_stdout


# ---------------------------------------------------------------------------
# Ownership-consistency: sum/len-style readers do NOT move their argument.
# ---------------------------------------------------------------------------


@requires_rustc
def test_sum_then_len_reader_does_not_move_its_argument(tmp_path):
    source = "fn main() {\n    let v = vec(1, 2, 3)\n    print(sum(v))\n    print(len(v))\n}\n"
    assert compile_and_run(source, tmp_path) == "6\n3\n"


def test_sum_then_len_compiles_with_no_diagnostics():
    source = "fn main() {\n    let v = vec(1, 2, 3)\n    print(sum(v))\n    print(len(v))\n}\n"
    assert codes(source) == []


# ---------------------------------------------------------------------------
# Diagnostics (brief's list minus the `set` case; existing OX-code classes
# only, following tests/test_sema_types.py's `codes(...)` pattern).
# ---------------------------------------------------------------------------

DIAGNOSTIC_CASES = [
    pytest.param(
        "fn main() {\n"
        "    let v = vec(1, 2, 3)\n"
        "    let s = sort(v)\n"
        "    print(len(v))\n"
        "}\n",
        ["OX0400"],
        id="sort-receiver-use-after-move",
    ),
    pytest.param(
        'fn main() {\n    print(sum(vec("a", "b")))\n}\n',
        ["OX0300"],
        id="sum-on-non-int-vec-is-a-type-error",
    ),
    pytest.param(
        "fn main() {\n    let v = vec(1, 2, 3)\n    print(contains(v))\n}\n",
        ["OX0303"],
        id="contains-arity-error",
    ),
]


@pytest.mark.parametrize(("source", "expected_codes"), DIAGNOSTIC_CASES)
def test_diagnostics(source, expected_codes):
    assert codes(source) == expected_codes
