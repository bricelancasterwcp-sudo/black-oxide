"""Fix round (2026-08-28): builtin shadowing (deferred-demand dossier 4).

A top-level `fn` whose name matches a builtin now SHADOWS it program-wide
instead of clashing (OX0203): the user definition wins everywhere a free
call could reach it, and the builtin becomes entirely unreachable in that
program -- including its receiver-first method form (SPEC.md §53 method
syntax is builtins-only; a shadowed name used as a method reuses the
existing "unknown identifier" diagnostic (OX0200), not a new code).

Test 1's acceptance evidence is NOT in this file: it is
`tests/test_eval.py::test_reference_solution_compiles_and_passes[oxide-t14]`
and `[explicit-t14]` going green with `eval/solutions/` untouched (those
reference solutions define their own `fn contains`, which used to collide
with the v0.4 `contains` builtin).

Compile-and-run helper mirrors `tests/test_v04_builtins.py` (itself
mirroring `tests/test_v02_codegen.py`/`tests/test_v021_codegen.py`'s
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
# Fixture: a `fn contains` with behavior visibly, deterministically
# different from the builtin (`v.contains(x)` semantics) -- the builtin
# would silently return `true` for x=2 in vec(1, 2, 3) with no side
# effect; the user version below always prints a marker, echoes its
# arguments, and returns `false` regardless of membership.
# ---------------------------------------------------------------------------

SHADOW_SRC = (
    "fn contains(v: Vec<Int>, x: Int) -> Bool {\n"
    '    print_str("user contains")\n'
    "    print(x)\n"
    "    print(len(v))\n"
    "    false\n"
    "}\n"
)


# ---------------------------------------------------------------------------
# Test 2: free-call form dispatches to the user's shadowing fn.
# ---------------------------------------------------------------------------


@requires_rustc
def test_shadowing_fn_wins_the_free_call_form(tmp_path):
    source = SHADOW_SRC + (
        "fn main() {\n    print(contains(vec(1, 2, 3), 2))\n}\n"
    )
    # The builtin would print just "true\n" (2 IS in the vec, no side
    # effect). The user fn's marker line + echoed args + forced `false`
    # can only appear if the user's definition actually ran.
    assert compile_and_run(source, tmp_path) == "user contains\n2\n3\nfalse\n"


def test_shadowing_fn_wins_the_free_call_form_diagnostics_clean():
    source = SHADOW_SRC + (
        "fn main() {\n    print(contains(vec(1, 2, 3), 2))\n}\n"
    )
    assert codes(source) == []


# ---------------------------------------------------------------------------
# Test 3: method-form on a shadowed name is refused (builtins-only sugar),
# not silently retargeted to the user fn.
# ---------------------------------------------------------------------------


def test_shadowed_name_as_a_method_is_not_a_method():
    source = SHADOW_SRC + (
        "fn main() {\n"
        "    let v = vec(1, 2, 3)\n"
        "    print(v.contains(2))\n"
        "}\n"
    )
    assert codes(source) == ["OX0200"]


# ---------------------------------------------------------------------------
# Test 4: guard against over-shadowing -- a program that does NOT define
# `contains` still gets the builtin, in both call forms.
# ---------------------------------------------------------------------------


@requires_rustc
def test_no_shadow_still_reaches_the_builtin(tmp_path):
    source = (
        "fn main() {\n"
        "    let v = vec(1, 2, 3)\n"
        "    print(contains(v, 2))\n"
        "    print(v.contains(9))\n"
        "}\n"
    )
    assert compile_and_run(source, tmp_path) == "true\nfalse\n"


def test_no_shadow_still_reaches_the_builtin_diagnostics_clean():
    source = (
        "fn main() {\n"
        "    let v = vec(1, 2, 3)\n"
        "    print(contains(v, 2))\n"
        "    print(v.contains(9))\n"
        "}\n"
    )
    assert codes(source) == []
