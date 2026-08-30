"""Semantic type representations (SPEC.md sections 14-15, 28).

Defines the type constructors (``TVar``/``TCon``/``TFn``), the error type
that unifies with everything, the Copy predicate, the canonical type
printer, the builtin function signatures, and the builtin generic enums
``Option``/``Result`` with their reserved variant names (Part V).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TVar:
    """A type metavariable (unification variable)."""

    id: int


@dataclass(frozen=True, slots=True)
class TCon:
    """A type constructor application, e.g. ``Int`` or ``Vec<Int>``."""

    name: str
    args: tuple = ()


@dataclass(frozen=True, slots=True)
class TFn:
    """A function type. Functions are second-class; this appears only in
    top-level signatures, never as the type of an expression."""

    params: tuple
    ret: object


Type = TVar | TCon | TFn

# The internal error sentinel. Its name is deliberately unnameable (no
# identifier can contain '<'), so a user struct named 'Error' is an
# ordinary nominal type and can never alias the sentinel's
# unify-with-everything behavior. It still renders as 'Error'.
ERROR_TYPE = TCon("<error>")

INT = TCon("Int")
FLOAT = TCon("Float")
BOOL = TCon("Bool")
STR = TCon("Str")
UNIT = TCon("Unit")

_COPY_NAMES = frozenset({"Int", "Float", "Bool", "Unit", ERROR_TYPE.name})


def is_copy(ty: object) -> bool:
    """True for Copy types: Int, Float, Bool, Unit, and the Error type.

    Str, Vec, all user structs, metavariables, and function types are
    linear (non-copy).
    """
    return isinstance(ty, TCon) and ty.name in _COPY_NAMES


def type_str(ty: object) -> str:
    """Canonical rendering: 'Int', 'Vec<Int>', 'fn(Int, Str) -> Unit', '?'."""
    match ty:
        case TVar():
            return "?"
        case TCon(name="<error>", args=()):
            return "Error"
        case TCon(name=name, args=()):
            return name
        case TCon(name=name, args=args):
            return f"{name}<{', '.join(type_str(a) for a in args)}>"
        case TFn(params=params, ret=ret):
            joined = ", ".join(type_str(p) for p in params)
            return f"fn({joined}) -> {type_str(ret)}"
        case _:
            raise TypeError(f"type_str: not a type: {ty!r}")


@dataclass(frozen=True, slots=True)
class BuiltinSig:
    """Signature of a builtin function.

    ``generics`` lists the placeholder TVars that must be instantiated
    with fresh metavariables at every use site.
    """

    params: tuple
    ret: object
    modes: tuple[str, ...]
    generics: tuple


_A = TVar(-1)  # generic placeholders; instantiated fresh per use
_B = TVar(-2)

BUILTINS: dict[str, BuiltinSig] = {
    "print": BuiltinSig(params=(_A,), ret=UNIT, modes=("read",), generics=(_A,)),
    "len": BuiltinSig(
        params=(TCon("Vec", (_A,)),), ret=INT, modes=("read",), generics=(_A,)
    ),
    "push": BuiltinSig(
        params=(TCon("Vec", (_A,)), _A),
        ret=TCon("Vec", (_A,)),
        modes=("own", "own"),
        generics=(_A,),
    ),
    "vec": BuiltinSig(params=(), ret=TCon("Vec", (_A,)), modes=(), generics=(_A,)),
    # ---- v0.2 builtins (SPEC.md section 28), modes pinned ----
    "clone": BuiltinSig(params=(_A,), ret=_A, modes=("read",), generics=(_A,)),
    "get": BuiltinSig(
        params=(TCon("Vec", (_A,)), INT),
        ret=TCon("Option", (_A,)),
        modes=("read", "read"),
        generics=(_A,),
    ),
    "range": BuiltinSig(
        params=(INT, INT), ret=TCon("Vec", (INT,)), modes=("read", "read"), generics=()
    ),
    "print_str": BuiltinSig(params=(STR,), ret=UNIT, modes=("read",), generics=()),
    "str_len": BuiltinSig(params=(STR,), ret=INT, modes=("read",), generics=()),
    "concat": BuiltinSig(params=(STR, STR), ret=STR, modes=("own", "own"), generics=()),
    "chars": BuiltinSig(
        params=(STR,), ret=TCon("Vec", (STR,)), modes=("read",), generics=()
    ),
    "int_to_str": BuiltinSig(params=(INT,), ret=STR, modes=("read",), generics=()),
    "parse_int": BuiltinSig(
        params=(STR,), ret=TCon("Option", (INT,)), modes=("read",), generics=()
    ),
    # ---- v0.2.1 builtins (SPEC.md section 36), modes pinned ----
    "to_float": BuiltinSig(params=(INT,), ret=FLOAT, modes=("read",), generics=()),
    "trunc": BuiltinSig(params=(FLOAT,), ret=INT, modes=("read",), generics=()),
    # ---- v0.3 builtins (SPEC.md section 57), modes pinned ----
    # An ALIAS of int_to_str, which stays. Models reach for the shorter
    # spelling untaught -- 85.7% of observed to_str sites are plain calls,
    # and 6 programs defined `fn to_str` themselves rather than use the
    # longer name. Int only: the language has no overloading.
    "to_str": BuiltinSig(params=(INT,), ret=STR, modes=("read",), generics=()),
    # ---- v0.4 builtins (Task 3 gate ruling), modes pinned ----
    # sort/set-style consuming vs min/max/sum/contains-style reading, mirroring
    # push and get/len respectively. `set` is CUT by the gate ruling (the
    # provisional slate listed it; the ruling struck it) and is not present.
    "sort": BuiltinSig(
        params=(TCon("Vec", (_A,)),),
        ret=TCon("Vec", (_A,)),
        modes=("own",),
        generics=(_A,),
    ),
    "min": BuiltinSig(
        params=(TCon("Vec", (_A,)),),
        ret=TCon("Option", (_A,)),
        modes=("read",),
        generics=(_A,),
    ),
    "max": BuiltinSig(
        params=(TCon("Vec", (_A,)),),
        ret=TCon("Option", (_A,)),
        modes=("read",),
        generics=(_A,),
    ),
    "sum": BuiltinSig(
        params=(TCon("Vec", (INT,)),), ret=INT, modes=("read",), generics=()
    ),
    # x's mode mirrors ==/!= (SPEC.md §14 EQ_OPS / eq_derive_types): equality
    # comparison never consumes its operands (BUILTIN_REF/`_binop_text` emit
    # ref-form for non-Copy operands on both sides), so `contains`'s searched
    # value is read, not moved -- consistent with `push`'s VALUE slot being
    # "own" only because it is being inserted (consumed), not compared.
    "contains": BuiltinSig(
        params=(TCon("Vec", (_A,)), _A),
        ret=BOOL,
        modes=("read", "read"),
        generics=(_A,),
    ),
    # ---- v0.4 wave-2 builtins (Task 3 census gate v2 ruling: slate of 2,
    # count(v, x) -> Int shipped; remove_at/first/last cut), modes pinned ----
    # count(v, x) -> Int: occurrences of x in v. Same reading modes as
    # contains -- it is contains's sibling (a filtered count instead of a
    # membership test), so both slots are "read" for the identical reason
    # given on BUILTINS["contains"] above: counting, like equality
    # comparison, never consumes its operands.
    "count": BuiltinSig(
        params=(TCon("Vec", (_A,)), _A),
        ret=INT,
        modes=("read", "read"),
        generics=(_A,),
    ),
    # ---- v0.4 wave-3 builtins (Task 2 TWO-EYED gate ruling: swap/reverse
    # ranked 1-2 by the COST census with zero reply demand; set on 18/18
    # mechanical rejection AND measured not to substitute for swap), modes
    # pinned ----
    # All three consume and return the vector, mirroring `sort`: they wrap
    # in-place Rust operations in this project's owned-in/owned-out
    # convention. The INT index slots are "read" for the same reason
    # `get`'s and `range`'s are -- an index is inspected, never consumed.
    # `set`'s VALUE slot is "own": like `push`'s inserted value, it is
    # genuinely transferred into the vector.
    # Out-of-range indices PANIC, matching the Rust control exactly (see
    # SPEC 60.2). This joins a pre-existing partial-operation category --
    # integer division already panics on a computed zero divisor -- it does
    # not open a new one.
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
    # ---- v0.4 builtins (Task 5 gate ruling), modes pinned ----
    # Both slots are "own": mirrors the language's two EXISTING ways of
    # reaching inside an Option -- match's scrutinee is a MOVE use (section
    # 28, cfg.py::_match) and '?''s operand is a MOVE use (section 36,
    # cfg.py::_expr's ast.Try case) -- neither treats "reading" an Option's
    # payload as a non-consuming borrow. unwrap_or's `o` mirrors that
    # established convention rather than get/min/max's read-mode Vec
    # param (those READ a Vec to PRODUCE an Option; there is no existing
    # precedent for reading an Option's payload without consuming it).
    # `d` is "own" because it may become the returned value verbatim on
    # the None path (T, potentially a non-Copy Vec<_>) -- mirroring why
    # push's inserted value is "own" (genuinely transferred), not read's
    # borrow-and-clone shape.
    "unwrap_or": BuiltinSig(
        params=(TCon("Option", (_A,)), _A),
        ret=_A,
        modes=("own", "own"),
        generics=(_A,),
    ),
}


@dataclass(frozen=True, slots=True)
class BuiltinEnum:
    """A builtin generic enum (SPEC.md section 28): ``Option``/``Result``.

    ``generics`` are placeholder TVars instantiated fresh (or mapped to a
    known instantiation's arguments) at every variant use; ``variants``
    pairs each variant name with its payload types over those placeholders.
    """

    name: str
    generics: tuple
    variants: tuple[tuple[str, tuple], ...]


BUILTIN_ENUMS: dict[str, BuiltinEnum] = {
    "Option": BuiltinEnum("Option", (_A,), (("Some", (_A,)), ("None", ()))),
    "Result": BuiltinEnum("Result", (_A, _B), (("Ok", (_A,)), ("Err", (_B,)))),
}

# Reserved variant names (user redefinition anywhere at top level -> OX0203),
# mapping each to its owning builtin enum.
BUILTIN_VARIANTS: dict[str, str] = {
    "Some": "Option",
    "None": "Option",
    "Ok": "Result",
    "Err": "Result",
}
