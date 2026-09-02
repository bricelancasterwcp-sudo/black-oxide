"""SPEC 65: `v[i]` element read.

Wave 8 measured this construct's absence as the single largest cause of
the large-task capability cliff -- 75.5% of the RUST arm's attempts on
200-600 token tasks index, and Oxide's lexer had no `[` at all, so the
model's attempts died at OX0001 before type checking ever ran.

Conventions follow tests/test_codegen_field_assign.py: golden assertions
on emitted text, plus a rustc compile check wherever the claim is "and
it compiles".
"""

import shutil
import subprocess

import pytest

from eval.rustc_adapter import find_rustc
from src.codegen.rust import transpile
from src.lexer.lexer import Lexer
from src.lexer.tokens import TokenKind
from src.parser import ast
from src.parser.parser import parse_source
from src.sema.analyze import analyze

RUSTC: str | None = shutil.which(find_rustc())
requires_rustc = pytest.mark.skipif(RUSTC is None, reason="rustc not available")


def codes(src: str) -> list[str]:
    return [d.code for d in analyze(src).diagnostics]


def run(tmp_path, src: str) -> str:
    rust, diags = transpile(src)
    assert diags == [], diags
    p = tmp_path / "program.rs"
    p.write_text(rust, encoding="utf-8")
    exe = tmp_path / "program"
    subprocess.run([RUSTC, "-O", "-o", str(exe), str(p)], check=True,
                   capture_output=True)
    return subprocess.run([str(exe)], capture_output=True, text=True,
                          timeout=10).stdout


# ---- lexer ----

def test_brackets_lex_as_their_own_tokens():
    kinds = [t.kind for t in Lexer("v[0]").tokenize()]
    assert TokenKind.LBRACKET in kinds
    assert TokenKind.RBRACKET in kinds


# ---- parser ----

def test_index_parses_as_a_postfix_form():
    prog = parse_source("fn main() { let v = vec()\n print(v[0]) }")[0]
    found = []

    def walk(node):
        if isinstance(node, ast.Index):
            found.append(node)
        for f in getattr(node, "__slots__", ()):
            child = getattr(node, f, None)
            if isinstance(child, tuple):
                for c in child:
                    walk(c)
            elif hasattr(child, "__slots__"):
                walk(child)

    walk(prog)
    assert len(found) == 1
    assert isinstance(found[0].obj, ast.Var)


def test_index_binds_tighter_than_arithmetic():
    """`v[0] + 1` is (v[0]) + 1, not v[0 + 1]. A postfix form at the call
    tier gets this for free, but it is the difference between two
    programs that both parse."""
    rust, diags = transpile(
        "fn main() { let v = vec().push(10).push(20)\n print(v[0] + 1) }"
    )
    assert diags == []
    assert "[(0) as usize] + 1" in rust


# ---- types ----

def test_index_yields_the_element_type_not_an_option():
    """SPEC 60.2's ruling: an Option that call sites unwrap away turns a
    bug into a plausible value, and taxes every in-range use. `v[i]` is
    T, so it composes directly with arithmetic."""
    assert codes("fn main() { let v = vec().push(1)\n print(v[0] + 1) }") == []


def test_indexing_a_non_vector_is_a_type_error():
    assert "OX0300" in codes('fn main() { let s = "abc"\n print(s[0]) }')


def test_a_non_integer_index_is_a_type_error():
    assert "OX0300" in codes('fn main() { let v = vec().push(1)\n print(v["x"]) }')


# ---- ownership ----

def test_indexing_does_not_consume_the_vector():
    """The commonest loop in the language reads `v[i]` under `len(v)`.
    If indexing moved the vector, that loop would fail on its second
    iteration -- so this is the property the construct lives or dies by."""
    src = (
        "fn main() {\n"
        "    let v = vec().push(1).push(2).push(3)\n"
        "    let total = 0\n"
        "    for i in range(0, len(v)) {\n"
        "        total += v[i]\n"
        "    }\n"
        "    print(total)\n"
        "    print(len(v))\n"
        "}"
    )
    assert codes(src) == []


def test_indexing_a_struct_field_leaves_the_struct_usable():
    src = (
        "struct R { label: Str, values: Vec<Int> }\n"
        "fn main() {\n"
        "    let r = R { label: \"lab\", values: vec().push(11).push(22) }\n"
        "    print(r.values[1])\n"
        "    print_str(r.label)\n"
        "}"
    )
    assert codes(src) == []


# ---- codegen ----

def test_the_index_is_parenthesised_before_the_cast():
    """Rust binds `as` tighter than arithmetic, so an unparenthesised
    cast turns `v[len(v) - 1]` into `v[len(v) - (1 as usize)]`, which
    does not compile. Found by the second-commonest index expression."""
    rust, diags = transpile(
        "fn main() { let v = vec().push(1).push(2)\n print(v[len(v) - 1]) }"
    )
    assert diags == []
    assert "[(len(&v) - 1) as usize]" in rust


def test_a_non_copy_element_is_cloned_out():
    """Section 36's rule for fields, for the same reason: the element is
    read out as a fresh owned value, so indexing never moves out of the
    vector.

    Asserted ON THE INDEX EXPRESSION, not merely somewhere in the file:
    a bare `".clone()" in rust` passes on clones emitted elsewhere in the
    program, which let a no-clone regression survive mutation."""
    rust, diags = transpile(
        'fn main() { let w = vec().push("a")\n print_str(w[0]) }'
    )
    assert diags == []
    assert "[(0) as usize].clone()" in rust


@requires_rustc
def test_indexing_a_string_vector_twice_compiles(tmp_path):
    """Without the clone this is rustc E0507, cannot move out of index --
    the failure the emitter exists to prevent, checked by compiling
    rather than by reading the text."""
    src = (
        'fn main() {\n'
        '    let w = vec().push("alpha").push("beta")\n'
        '    print_str(w[0])\n'
        '    print_str(w[1])\n'
        '    print(len(w))\n'
        '}'
    )
    assert run(tmp_path, src) == "alpha\nbeta\n2\n"


def test_a_copy_element_is_not_cloned():
    rust, _ = transpile("fn main() { let v = vec().push(1)\n print(v[0]) }")
    assert "[(0) as usize]" in rust
    assert "[(0) as usize].clone()" not in rust


# ---- end to end ----

@requires_rustc
def test_indexing_runs_and_prints_the_element(tmp_path):
    src = (
        "fn main() {\n"
        "    let v = vec().push(5).push(9).push(2).push(7)\n"
        "    let total = 0\n"
        "    for i in range(0, len(v)) {\n"
        "        total += v[i]\n"
        "    }\n"
        "    print(total)\n"
        "    print(v[len(v) - 1])\n"
        "    print(v[1 + 1])\n"
        "    print(-v[0])\n"
        "}"
    )
    assert run(tmp_path, src) == "23\n7\n2\n-5\n"


@requires_rustc
def test_string_elements_index_correctly(tmp_path):
    src = (
        'fn main() {\n'
        '    let w = vec().push("alpha").push("beta")\n'
        '    print_str(w[1])\n'
        '    print(str_len(w[0]))\n'
        '}'
    )
    assert run(tmp_path, src) == "beta\n5\n"


@requires_rustc
def test_out_of_range_panics_rather_than_returning_a_plausible_value(tmp_path):
    """SPEC 60.2's category, which `set` and `swap` already belong to.
    A clamp or a silent default here would be the quiet wrong answer the
    ruling rejects."""
    rust, diags = transpile(
        "fn main() { let v = vec().push(1).push(2)\n print(v[5]) }"
    )
    assert diags == []
    p = tmp_path / "program.rs"
    p.write_text(rust, encoding="utf-8")
    exe = tmp_path / "program"
    subprocess.run([RUSTC, "-O", "-o", str(exe), str(p)], check=True,
                   capture_output=True)
    done = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
    assert done.returncode != 0
    assert done.stdout == ""


def test_an_index_can_end_a_statement():
    """`]` must be in the lexer's TERMINATOR_SET or no NEWLINE is emitted
    after it, and the statement swallows the following line. Every index
    in the first test pass sat mid-line or inside a call, so none of them
    exercised this -- three large-tier references caught it at once."""
    src = (
        "fn main() {\n"
        "    let v = vec().push(1).push(2)\n"
        "    let a = v[0]\n"
        "    let b = v[1]\n"
        "    print(a + b)\n"
        "}"
    )
    assert codes(src) == []


def test_an_index_ending_a_block_still_parses():
    src = (
        "fn first(v: Vec<Int>) -> Int {\n"
        "    v[0]\n"
        "}\n"
        "fn main() { print(first(vec().push(7))) }"
    )
    assert codes(src) == []
