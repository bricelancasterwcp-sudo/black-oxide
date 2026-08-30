"""Runtime + diagnostic tests for the v0.4 wave-3 Vec builtins:
``swap``/``reverse``/``set``, gate-ruled by the COST census (Task 2 --
``swap`` and ``reverse`` have zero reply demand and rank 1-2 on token
surplus, which is why the wave added a second eye to the gate).

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
    result = transpile(src)
    rust_text = result[0] if isinstance(result, tuple) else result
    rs = tmp_path / "main.rs"
    rs.write_text(rust_text)
    out = tmp_path / "bin"
    proc = subprocess.run(
        [RUSTC, "--edition", "2021", str(rs), "-o", str(out)],
        capture_output=True,
        text=True,
    )
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
    after the call is a move-of-moved-value error (OX0400, the read-context
    code -- the same one tests/test_v04_builtins.py pins for sort), not a
    silent alias."""
    src = """fn main() {
    let v = vec(1, 2)
    let w = swap(v, 0, 1)
    print(len(v))
}
"""
    assert "OX0400" in codes(src)


def test_reverse_consumes_its_vector_too():
    src = """fn main() {
    let v = vec(1, 2)
    let w = reverse(v)
    print(len(v))
}
"""
    assert "OX0400" in codes(src)


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
