"""The v0.4 wave-4 re-spelling (`|x| expr`) and `filter`.

Wave 3 shipped the predicate literal as `x -> expr`, arguing an
unfamiliar spelling would make the no-capture restriction legible. At
equal corpus exposure the tuned model chose Rust's `|x|` about 10:1, so
SPEC 63.1 reverses that ruling on the evidence. Semantics are unchanged:
still no captures, still `Pred<T>`, still the same emitted closure.

`filter` ships alongside `count_if` so that efficiency and learnability
point at different constructs and the model picks (SPEC 63.2).
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


# --- Task 1: the re-spelling -------------------------------------------


@requires_rustc
def test_bar_predicate_counts_matching_elements(tmp_path):
    src = """fn main() {
    let v = vec(5, 12, 3, 18, 9)
    print(count_if(v, |x| x < 10))
}
"""
    assert run_oxide(src, tmp_path) == "3\n"


def test_bar_predicate_still_cannot_capture():
    """The restriction survives the re-spelling -- it is now taught by
    the diagnostic rather than by unfamiliar syntax."""
    src = """fn main() {
    let v = vec(1, 2, 3)
    let t = 2
    print(count_if(v, |x| x < t))
}
"""
    assert "OX0205" in codes(src)


def test_boolean_or_still_lexes_as_oror():
    """`||` must keep winning over a bare `|` (two-char-first, SPEC 3.6),
    or every disjunction in the corpus silently becomes a predicate."""
    src = """fn main() {
    let a = true
    let b = false
    if a || b {
        print(1)
    }
}
"""
    assert codes(src) == []


def test_arrow_form_is_gone():
    src = """fn main() {
    let v = vec(1, 2, 3)
    print(count_if(v, x -> x < 2))
}
"""
    assert codes(src) != []


# --- Task 2: filter ----------------------------------------------------


@requires_rustc
def test_filter_keeps_matching_elements(tmp_path):
    src = """fn main() {
    let v = vec(5, 12, 3, 18, 9)
    for x in filter(v, |x| x < 10) {
        print(x)
    }
}
"""
    assert run_oxide(src, tmp_path) == "5\n3\n9\n"


@requires_rustc
def test_len_of_filter_equals_count_if(tmp_path):
    """The SPEC 63.2 experiment's two spellings must agree numerically --
    they differ in token cost and familiarity, never in answer."""
    src = """fn main() {
    let v = vec(5, 12, 3, 18, 9)
    print(len(filter(v, |x| x < 10)))
    print(count_if(v, |x| x < 10))
}
"""
    assert run_oxide(src, tmp_path) == "3\n3\n"


@requires_rustc
def test_filter_reads_its_vector_so_the_source_stays_usable(tmp_path):
    src = """fn main() {
    let v = vec(5, 12, 3)
    print(len(filter(v, |x| x < 10)))
    print(len(v))
}
"""
    assert run_oxide(src, tmp_path) == "2\n3\n"


def test_filter_is_in_all_three_seams():
    from src.codegen.support import BUILTIN_REF
    from src.parser.expressions import BUILTIN_METHOD_NAMES
    from src.sema.types import BUILTINS

    assert "filter" in BUILTINS and "filter" in BUILTIN_REF
    assert "filter" in BUILTIN_METHOD_NAMES
