"""The v0.4 wave-3 predicate literal (`|x| expr`) and `count_if`.

Ships to cross the corpus below 1.0 (SPEC 61). The literal is
deliberately NOT a closure: it cannot capture, which is exactly what
keeps it clear of implicit linear ownership -- the collision that kept
closures out of the wave-3 spec's scope. Wave 3 spelled it `x -> expr` to avoid promising capture semantics;
wave 4 re-spelled it to `|x|` after the model chose the bar form about
10:1 at equal exposure. The no-capture rule is now taught by OX0205.
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
def test_count_if_counts_matching_elements(tmp_path):
    src = """fn main() {
    let v = vec(5, 12, 3, 18, 9)
    print(count_if(v, |x| x < 10))
}
"""
    assert run_oxide(src, tmp_path) == "3\n"


@requires_rustc
def test_count_if_reads_its_vector_so_it_stays_usable(tmp_path):
    """The n046 shape: count, then use the same vector again."""
    src = """fn main() {
    let v = vec(5, 12, 3, 18, 9)
    let under = count_if(v, |x| x < 10)
    print(under)
    print(len(v) - under)
}
"""
    assert run_oxide(src, tmp_path) == "3\n2\n"


@requires_rustc
def test_count_if_works_on_non_copy_elements(tmp_path):
    src = """fn main() {
    let v = vec("aa", "b", "b")
    print(count_if(v, |s| s == "b"))
}
"""
    assert run_oxide(src, tmp_path) == "2\n"


def test_predicate_cannot_capture_an_outer_binding():
    """The whole point of the restriction: no captures means no
    ownership question, so the construct never touches linearity."""
    src = """fn main() {
    let v = vec(1, 2, 3)
    let threshold = 2
    print(count_if(v, |x| x < threshold))
}
"""
    assert "OX0205" in codes(src)


def test_predicate_body_must_be_bool():
    src = """fn main() {
    let v = vec(1, 2, 3)
    print(count_if(v, |x| x + 1))
}
"""
    assert "OX0300" in codes(src)


def test_predicate_param_is_not_in_scope_outside_the_predicate():
    src = """fn main() {
    let v = vec(1, 2, 3)
    print(count_if(v, |x| x < 2))
    print(x)
}
"""
    assert codes(src) != []


def test_predicate_param_may_shadow_nothing_and_still_resolves():
    src = """fn main() {
    let v = vec(1, 2, 3)
    print(count_if(v, |x| x < 2))
}
"""
    assert codes(src) == []


@requires_rustc
def test_method_form_works(tmp_path):
    """n065's shape: 6, 11, 14 and 9 all exceed five, so the answer is 4
    -- the value n065's frozen expected_stdout already pins."""
    src = """fn main() {
    let v = vec(6, 11, 3, 14, 9)
    print(v.count_if(|x| x > 5))
}
"""
    assert run_oxide(src, tmp_path) == "4\n"


def test_count_if_is_in_all_three_seams():
    from src.parser.expressions import BUILTIN_METHOD_NAMES
    from src.codegen.support import BUILTIN_REF
    from src.sema.types import BUILTINS

    assert "count_if" in BUILTINS
    assert "count_if" in BUILTIN_REF
    assert "count_if" in BUILTIN_METHOD_NAMES
