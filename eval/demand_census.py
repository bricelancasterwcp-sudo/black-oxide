"""Demand census over committed campaign replies and the training corpus
(v0.4 efficiency wave 1, Task 1).

Mines the `eval/results/runpod-exp/` campaign replies (oxide arms only --
arm directory names containing ``-ox-``) and the matched training corpus
(``eval.token_match.load_matched_inputs``, read-only) for eight pinned
construct families: ranges, sort, minmax, sum, index_assign, contains,
option, strings. This module answers ONE question -- how often does each
surface spelling actually appear -- and answers nothing about whether
Oxide should gain a name for it. That decision belongs to Task 2's gate;
the committed REPORT.md carries the ranking as data, not a recommendation.

COUNTING RULE: a (family, spelling) counts AT MOST ONCE per reply file
and AT MOST ONCE per program. Burstiness inside a single generation (a
model that writes ``range(`` four times in one reply) must not inflate
demand beyond "this reply reached for range at least once" -- the same
per-program discipline ``eval/demand.py`` already established for the
builtin-shadowing counters, applied here to eight new pinned patterns.

DELIBERATELY TEXTUAL, NOT PARSE-BASED, for the same reason as
``eval/demand.py``: patterns match raw source text, so occurrences
inside comments, prose surrounding a markdown code fence, or string
literals count the same as genuine use. The counts are upper bounds on
genuine source occurrences, not exact counts -- documented rather than
filtered, because gating on a successful parse would discard exactly the
malformed-but-signal-carrying replies this census exists to measure.

PATTERN REFINEMENTS FROM THE BRIEF'S STARTING POINT. The brief's
FAMILIES regexes are a starting point, not a final pin; two families
misfired measurably against the real `runpod-exp` corpus (full
transcript in task-1-report.md):

* ``ranges``/``dotdot`` drops the brief's ``\\bin\\s+\\w+\\s*\\.\\.``
  anchor and accepts an optional ``=`` before the right-hand operand.
  The real corpus's dominant dotdot spelling is the iterator-expression
  form ``(1..n).filter(...)``, not only the for-loop ``in 0..10`` form,
  and Rust/Oxide's inclusive-range spelling ``1..=n`` is common in both
  the replies and the training corpus. The brief-literal anchored
  pattern captures 196/3478 oxide-arm reply files; dropping the anchor
  alone reaches 252; adding the inclusive-range spelling reaches 292 --
  a 49% recovery of dotdot demand the anchored pattern was silently
  discarding.
* ``sort``/``free``, ``minmax``/``free``, ``sum``/``free`` replace the
  brief's bare ``\\b`` with a ``(?<![.\\w])`` guard -- the same guard
  ``eval/demand.py``'s ``_CALL`` already uses for exactly this reason.
  A word boundary sits on BOTH sides of a dot (``.sort(`` has one right
  after the dot too), so the brief-literal "free" pattern silently
  re-counts every "method" spelling occurrence as free-function demand
  as well. Measured on the full oxide-arm corpus: naive ``sum`` "free"
  hit 106 files, of which 100 (94%) were actually ``.sum(`` method
  calls (true free-function demand: 6); naive ``minmax`` "free" hit 49,
  of which 20 (41%) were ``.min(``/``.max(``  (true: 29); naive
  ``sort`` "free" hit 212, of which 16 (8%) were ``.sort(`` (true: 196).

Every other spelling (range_call, to_method, index_assign/bracket,
index_assign/set_method, contains/method, option/if_let,
option/unwrap_or, option/question, strings/split, strings/join,
strings/format) was checked against the real corpus and left unchanged
-- see task-1-report.md for the verification transcript.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from eval.token_match import load_matched_inputs
from eval.train_corpus import (
    collect_verified,
    load_train_programs,
    load_train_tasks,
    normalize_source,
)

# Relative to the repo root (matching eval/token_match.py's AMP_ROOTS
# convention) so a committed `runpod_root` in census.json stays portable
# across checkouts instead of baking in one machine's absolute path.
RUNPOD_ROOT = Path("eval/results/runpod-exp")
OUT_DIR = Path("eval/results/v04-census")

# {family: {spelling_name: regex}} -- pinned pattern definitions. See the
# module docstring for what changed from the task brief's starting point
# and why.
FAMILIES: dict[str, dict[str, str]] = {
    "ranges": {
        "dotdot": r"\b\w+\s*\.\.=?\s*\w+",
        "range_call": r"\brange\s*\(",
        "to_method": r"\.\s*to\s*\(\s*\w+\s*\)",
    },
    "sort": {
        "method": r"\.\s*sort\s*\(",
        "free": r"(?<![.\w])sort\s*\(",
    },
    "minmax": {
        "method": r"\.\s*(?:min|max)\s*\(",
        "free": r"(?<![.\w])(?:min|max)\s*\(",
    },
    "sum": {
        "method": r"\.\s*sum\s*\(",
        "free": r"(?<![.\w])sum\s*\(",
    },
    "index_assign": {
        "bracket": r"\w+\s*\[\s*\w+\s*\]\s*=[^=]",
        "set_method": r"\.\s*set\s*\(",
    },
    "contains": {
        "method": r"\.\s*contains\s*\(",
    },
    "option": {
        "if_let": r"\bif\s+let\s+Some",
        "unwrap_or": r"unwrap_or\s*\(",
        "question": r"\)\s*\?",
    },
    "strings": {
        "split": r"\.\s*split\s*\(",
        "join": r"\.\s*join\s*\(",
        "format": r"\bformat!\s*\(",
    },
}

_COMPILED: dict[str, dict[str, re.Pattern[str]]] = {
    family: {spelling: re.compile(pattern) for spelling, pattern in spellings.items()}
    for family, spellings in FAMILIES.items()
}

# The two program-corpus sources census_programs() tags every count with.
PROGRAM_SOURCES: tuple[str, ...] = ("reference", "amplified")


# =========================================================================
# v0.4 wave-2 Task 1 addendum -- rejection-crossed demand, `+=` family,
# hand-rolled structural patterns.
#
# COMPOUND_FAMILY is a SEPARATE constant from FAMILIES, not merged into
# it -- FAMILIES (and every wave-1 function that reads it: census_replies,
# census_programs, main, build_census) stays byte-for-byte as wave-1 left
# it, so the wave-1 tests remain a valid regression net. "Folded into the
# census's family handling" means COMPOUND_FAMILY is matched through the
# SAME per-file/per-program at-most-once discipline FAMILIES already
# uses (see `_v2_matches` below, the wave-2 sibling of `_matches`), not
# that it is spliced into the wave-1 dict.
#
# The lookbehind guard on each spelling blocks a compound-assign match
# from firing on the TAIL of a longer punctuation run -- concretely, a
# model that slips into Python's `**=` (power-assign) while writing
# Oxide/Rust must not have that counted as Oxide `*=` demand: the `*`
# immediately before the `*=` sits in the guard's character class, so
# `(?<!\*)\*=` correctly declines the second half of `**=`. The same
# guard also keeps `<=`, `==`, and `!=` at zero for every compound
# spelling (tests/test_demand_census.py pins both the positive `+=`/
# `-=`/`*=` case and this negative).
COMPOUND_FAMILY: dict[str, dict[str, str]] = {
    "compound_assign": {
        "plus_eq": r"(?<![+\-*/=!<>])\+=",
        "minus_eq": r"(?<![+\-*/=!<>])-=",
        "times_eq": r"(?<![+\-*/=!<>])\*=",
    },
}

# The combined family set every wave-2 function matches against: the
# wave-1 eight plus compound_assign. Never used by wave-1 functions.
V2_FAMILIES: dict[str, dict[str, str]] = {**FAMILIES, **COMPOUND_FAMILY}

_V2_COMPILED: dict[str, dict[str, re.Pattern[str]]] = {
    family: {spelling: re.compile(pattern) for spelling, pattern in spellings.items()}
    for family, spellings in V2_FAMILIES.items()
}


def _v2_matches(text: str) -> list[tuple[str, str]]:
    """The wave-2 sibling of `_matches`: (family, spelling) pairs over
    V2_FAMILIES, same at-most-once-per-text discipline."""
    return [
        (family, spelling)
        for family, spellings in _V2_COMPILED.items()
        for spelling, pattern in spellings.items()
        if pattern.search(text)
    ]


# Five pinned structural patterns for constructs a model hand-rolls with
# a loop instead of reaching for a name the language already has (or
# will have): the DEMAND signal for min/max/sum/filter/build builtins,
# read off working programs rather than replies. Each is grounded in a
# real construct from the current (pre-re-author) `eval/train/pairs/`
# corpus except minmax_scan, which the corpus genuinely has zero of --
# min()/max() already exist as builtins, so no reference or amplified
# program needs to hand-roll a sentinel scan; that zero is the expected,
# reported finding, not a broken pattern (see task-1-report.md).
#
# Every regex is anchored with `[^{}]*` spans rather than `.*` so a
# single-level `for { ... }` or `if { ... }` body cannot silently swallow
# an unrelated sibling block on the other side of a `}` -- the same
# brace-discipline idea as the FAMILIES `(?<![.\w])` guards, adapted to
# structural (not lexical) patterns. This is still DELIBERATELY TEXTUAL,
# NOT PARSE-BASED (see the module docstring): a program with a *nested*
# if/else two levels deep before the accumulator update can slip past a
# pattern that only tolerates one un-nested if/else (n043's outer loop is
# a real, documented example -- task-1-report.md's fixture rationale
# section). Patterns are upper-bound-leaning heuristics, verified against
# the real corpus and pinned with constructed positive/negative fixtures,
# not exhaustive parsers.
HANDROLLED: dict[str, dict[str, str]] = {
    "occurrence_count": {
        "structural": (
            r"\bfor\s+\w+\s+in\b[^{}]*\{[^{}]*\bif\b[^{}]*==[^{}]*\{"
            r"[^{}]*\b(?P<occ_acc>\w+)\s*(?:\+=|=\s*(?P=occ_acc)\s*\+)"
        ),
    },
    "removal_rebuild": {
        "structural": (
            r"\b(?P<rr_acc>\w+)\s*=\s*vec\(\s*\)[^{}]*\bfor\s+\w+\s+in\b[^{}]*\{"
            r"[^{}]*\bif\b[^{}]*\{[^{}]*(?:\}[^{}]*\belse\b[^{}]*\{)?"
            r"[^{}]*\bpush\s*\(\s*(?P=rr_acc)\s*,"
        ),
    },
    "minmax_scan": {
        "structural": (
            r"\b(?P<mm_acc>\w+)\s*=\s*-?\d+\b[^{}]*\bfor\s+\w+\s+in\b[^{}]*\{"
            r"[^{}]*\bif\b[^{}]*[<>](?!=)[^{}]*\{"
            r"[^{}]*\b(?P=mm_acc)\s*=\s*(?!(?P=mm_acc)\b)\w+\b"
        ),
    },
    "sum_scan": {
        "structural": (
            r"\b(?P<sum_acc>\w+)\s*=\s*0\b[^{}]*\bfor\s+\w+\s+in\b[^{}]*\{"
            r"[^{}]*\b(?P=sum_acc)\s*(?:\+=|=\s*(?P=sum_acc)\s*\+)"
        ),
    },
    "string_build": {
        # Two alternatives because the corpus uses both orders: `chars(`
        # bound to a variable BEFORE the accumulator init (n053 reference:
        # `let cs = chars("drum")` then `let out = ""`), and `chars(`
        # called inline in the for's own iterable clause, AFTER the
        # accumulator init (n053's amplified pool: `let reversed = ""`
        # then `for c in chars(word)`). Both require the loop body to
        # reassign the SAME accumulator (backreference), so a `chars(`
        # call that is never looped over, or a loop that never touches
        # the accumulator, does not count.
        "structural": (
            r"(?:\bchars\s*\([^{}]*\b(?P<sb_acc1>\w+)\s*=\s*(?:\"\"|vec\(\s*\))"
            r"[^{}]*\bfor\s+\w+\s+in\b[^{}]*\{[^{}]*\b(?P=sb_acc1)\s*=)"
            r"|"
            r"(?:\b(?P<sb_acc2>\w+)\s*=\s*(?:\"\"|vec\(\s*\))"
            r"(?=[^{}]*\bchars\s*\()[^{}]*\bfor\s+\w+\s+in\b[^{}]*\{"
            r"[^{}]*\b(?P=sb_acc2)\s*=)"
        ),
    },
}

_HANDROLLED_COMPILED: dict[str, dict[str, re.Pattern[str]]] = {
    pattern: {spelling: re.compile(p) for spelling, p in spellings.items()}
    for pattern, spellings in HANDROLLED.items()
}


def _handrolled_matches(text: str) -> list[str]:
    """Pattern names (deduped) whose HANDROLLED regex matches `text` --
    at-most-once-per-program, same discipline as `_matches`/`_v2_matches`.
    """
    return [
        pattern
        for pattern, spellings in _HANDROLLED_COMPILED.items()
        if any(p.search(text) for p in spellings.values())
    ]


# Data roots for wave-2 (relative to repo root, matching RUNPOD_ROOT's
# convention -- functions accept overrides; these are just the defaults
# `main2` uses).
CAMPAIGN_ROOT = Path("eval/results/v04-campaign")
AMP_ROOT = Path("eval/results/v04-amp")
AMP_RAW_ROOT = AMP_ROOT / "raw"
OUT_DIR_V2 = Path("eval/results/v04-census2")


def _matches(text: str) -> list[tuple[str, str]]:
    """(family, spelling) pairs whose pattern matches `text`, each pair
    appearing at most once regardless of how many times it matches --
    the per-file/per-program counting rule the module docstring pins.
    """
    return [
        (family, spelling)
        for family, spellings in _COMPILED.items()
        for spelling, pattern in spellings.items()
        if pattern.search(text)
    ]


def oxide_arms(root: Path) -> tuple[str, ...]:
    """Experiment arm directory names carrying oxide-dialect replies --
    the ones whose name contains ``-ox-`` (base-ox-7, tune-ox-14, ...),
    never ``-rs-``. Sorted for a reproducible, order-independent scan.
    """
    root = Path(root)
    if not root.is_dir():
        return ()
    return tuple(sorted(p.name for p in root.iterdir() if p.is_dir() and "-ox-" in p.name))


def census_replies(root: Path, arms: tuple[str, ...]) -> dict:
    """Per-(family, spelling, arm) file counts over committed replies.

    Reads ``<root>/<arm>/gen-s*/raw/*.txt`` for each arm in `arms` --
    the shape every runpod-exp arm writes. Some campaign arms also carry
    sibling ``<arm>-gen-s*`` directories holding only ``triples.jsonl``
    (no ``raw/``); the glob's literal ``gen-s*`` segment already excludes
    those without special-casing, since ``<arm>-gen-s*`` does not match
    the pattern ``gen-s*``.
    """
    counts: dict[str, dict[str, Counter]] = {
        family: {spelling: Counter() for spelling in spellings}
        for family, spellings in FAMILIES.items()
    }
    for arm in arms:
        for path in sorted(Path(root).glob(f"{arm}/gen-s*/raw/*.txt")):
            text = path.read_text(encoding="utf-8", errors="replace")
            for family, spelling in _matches(text):
                counts[family][spelling][arm] += 1
    return {
        family: {spelling: dict(per_arm) for spelling, per_arm in spellings.items()}
        for family, spellings in counts.items()
    }


def census_programs() -> dict:
    """Per-(family, spelling, source, class) program counts over the
    matched training corpus (``eval.token_match.load_matched_inputs``,
    read-only): the reference program plus every verified amplified
    program for each (task, arm), pooled across BOTH the oxide and rust
    arms -- a construct's corpus base rate does not depend on which
    dialect wrote it, and both arms are matched pairs solving the same
    task. Counted pre-trim over the full verified corpus, matching
    ``token_efficiency``'s own "descriptive estimand" convention in
    ``eval/token_match.py`` (the estimand is about the languages, not
    the budget-trimmed training sample).
    """
    tasks, references, amplified = load_matched_inputs()
    counts: dict[str, dict[str, dict[str, Counter]]] = {
        family: {
            spelling: {source: Counter() for source in PROGRAM_SOURCES}
            for spelling in spellings
        }
        for family, spellings in FAMILIES.items()
    }
    for tid in sorted(tasks):
        cls = tasks[tid]["class"]
        for arm in ("oxide", "rust"):
            for family, spelling in _matches(references[(tid, arm)]):
                counts[family][spelling]["reference"][cls] += 1
            for text in sorted(amplified.get((tid, arm), ())):
                for family, spelling in _matches(text):
                    counts[family][spelling]["amplified"][cls] += 1
    return {
        family: {
            spelling: {source: dict(per_class) for source, per_class in sources.items()}
            for spelling, sources in spellings.items()
        }
        for family, spellings in counts.items()
    }


def _family_total(replies_family: dict[str, dict[str, int]]) -> int:
    """Sum of every spelling's counts, over every arm -- the ranked
    table's "total demand" for one family. A reply that reaches for two
    different spellings of the same family (e.g. both `range_call` and
    `dotdot` in different attempts) contributes to both; this is the
    combined reply-side signal across the family's whole spelling
    repertoire, not a per-file dedup across spellings.
    """
    return sum(
        count
        for per_arm in replies_family.values()
        for count in per_arm.values()
    )


def _dominant_spelling(replies_family: dict[str, dict[str, int]]) -> tuple[str, int]:
    """The spelling with the largest summed-over-arms count in one
    family, ties broken alphabetically for a reproducible report."""
    totals = {
        spelling: sum(per_arm.values())
        for spelling, per_arm in replies_family.items()
    }
    spelling = min(totals, key=lambda s: (-totals[s], s))
    return spelling, totals[spelling]


def ranked_table(replies: dict) -> list[tuple[str, int, str, int]]:
    """(family, total_demand, dominant_spelling, dominant_count), sorted
    by total_demand descending then family name -- data for Task 2's
    gate to read, not a recommendation. "Total demand" is the reply-side
    signal only (see `_family_total`): the training-corpus counts are a
    separate cross-check of what already appears in verified-working
    programs, not folded into this ranking, because the two answer
    different questions (what models reach for vs. what already works).
    """
    rows = []
    for family, spellings in replies.items():
        total = _family_total(spellings)
        dominant, dominant_count = _dominant_spelling(spellings)
        rows.append((family, total, dominant, dominant_count))
    return sorted(rows, key=lambda r: (-r[1], r[0]))


def _reply_table(family: str, spellings: dict[str, dict[str, int]], arms: tuple[str, ...]) -> list[str]:
    header = "| spelling | " + " | ".join(arms) + " | total |"
    sep = "|---|" + "---|" * (len(arms) + 1)
    lines = [f"### {family}", "", header, sep]
    for spelling in sorted(spellings):
        per_arm = spellings[spelling]
        cells = [str(per_arm.get(arm, 0)) for arm in arms]
        total = sum(per_arm.values())
        lines.append(f"| {spelling} | " + " | ".join(cells) + f" | {total} |")
    lines.append("")
    return lines


def _program_table(family: str, spellings: dict[str, dict[str, dict[str, int]]], classes: tuple[str, ...]) -> list[str]:
    lines = [f"### {family}", ""]
    for source in PROGRAM_SOURCES:
        header = "| spelling | " + " | ".join(classes) + " | total |"
        sep = "|---|" + "---|" * (len(classes) + 1)
        lines += [f"**{source}**", "", header, sep]
        for spelling in sorted(spellings):
            per_class = spellings[spelling][source]
            cells = [str(per_class.get(cls, 0)) for cls in classes]
            total = sum(per_class.values())
            lines.append(f"| {spelling} | " + " | ".join(cells) + f" | {total} |")
        lines.append("")
    return lines


def render_report(replies: dict, programs: dict, arms: tuple[str, ...], classes: tuple[str, ...]) -> str:
    """The committed REPORT.md: counts and a ranked table. No
    recommendations -- the ranking is data, the gate (Task 2) decides.
    """
    lines = [
        "# v0.4 Demand Census",
        "",
        "Construct demand mined from committed campaign replies "
        f"(`eval/results/runpod-exp/`, oxide arms only: {', '.join(arms)}) "
        "and the matched training corpus (`eval.token_match.load_matched_inputs`). "
        "Counts are per-file / per-program presence, not raw occurrences "
        "(see `eval/demand_census.py`'s module docstring for the pattern "
        "definitions and the refinements measured against this corpus).",
        "",
        "This report contains no recommendations. The ranked table is data "
        "for the wave's design-slate gate (Task 2) to read.",
        "",
        "## Model replies (oxide arms only, per arm)",
        "",
    ]
    for family in sorted(replies):
        lines += _reply_table(family, replies[family], arms)

    lines += ["## Training corpus (reference + amplified, pooled oxide+rust arms, per class)", ""]
    for family in sorted(programs):
        lines += _program_table(family, programs[family], classes)

    lines += [
        "## Ranked demand (replies, summed over arms and spellings)",
        "",
        "| family | total demand | dominant spelling | dominant count |",
        "|---|---|---|---|",
    ]
    for family, total, dominant, dominant_count in ranked_table(replies):
        lines.append(f"| {family} | {total} | {dominant} | {dominant_count} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def build_census(root: Path = RUNPOD_ROOT) -> dict:
    """The full census.json payload: pinned patterns, replies, programs,
    and enough scan metadata to audit the numbers -- no timestamps."""
    arms = oxide_arms(root)
    replies = census_replies(root, arms)
    programs = census_programs()
    tasks, _, _ = load_matched_inputs()
    classes = tuple(sorted({t["class"] for t in tasks.values()}))
    reply_files = sum(
        1 for arm in arms for _ in Path(root).glob(f"{arm}/gen-s*/raw/*.txt")
    )
    return {
        "families": FAMILIES,
        "replies": replies,
        "programs": programs,
        "meta": {
            "runpod_root": str(root),
            "oxide_arms": list(arms),
            "reply_files_scanned": reply_files,
            "program_classes": list(classes),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.demand_census")
    parser.add_argument("--root", type=Path, default=RUNPOD_ROOT)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    census = build_census(args.root)
    arms = tuple(census["meta"]["oxide_arms"])
    classes = tuple(census["meta"]["program_classes"])

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "census.json").write_text(
        json.dumps(census, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = render_report(census["replies"], census["programs"], arms, classes)
    (args.out / "REPORT.md").write_text(report, encoding="utf-8")
    print(f"wrote {args.out / 'census.json'} and {args.out / 'REPORT.md'}")
    print(f"scanned {census['meta']['reply_files_scanned']} reply files "
          f"across {len(arms)} oxide arm(s): {', '.join(arms)}")
    return 0


# =========================================================================
# v0.4 wave-2 Task 1 addendum, continued -- the rejection-crossed join and
# main2.
#
# THE JOIN, both layouts. A campaign/amp run writes one reply file per
# (task, seed, attempt): `<task>.<harness-arm>.<attempt>.txt` under
# `<arm>/gen-s<seed>/raw/`. Attempt 1 is the session's FIRST attempt --
# the one attempt every arm's verdict source describes on its own
# ("first_compiled" in v04-campaign's cells.jsonl; the attempt-1 row's
# "compiled" in v04-amp's triples.jsonl). Joining on (task, seed) between
# that one reply file and that one verdict is therefore unambiguous: no
# aggregation, no picking among several attempts, no guessing which
# verdict a multi-attempt session's reply belongs to.
#
# RELIABILITY, checked before writing a single line of join code (STOP
# condition in the task brief): every `gen-s<seed>/raw/*.1.txt` file
# across all 4 v04-campaign arms x 10 seeds has an exact-match cells.jsonl
# row for its task in that seed, and vice versa -- 800/800 both
# directions, zero orphans either side. The same check across all 6
# v04-amp raw arm-dirs (1.5-ox/rs, 7-ox/rs, 14-ox/rs) x 10 seeds against
# their runs-<size>/amp-<short>-s<seed>/triples.jsonl attempt-1 rows is
# 2400/2400, zero orphans. (Verification script + counts transcribed in
# task-1-report.md.) The join is reliable on every committed cell; the
# STOP condition never fired.
#
# TWO LAYOUTS, ONE CORE, TWO THIN ADAPTERS. v04-campaign's verdict file
# (cells.jsonl) sits INSIDE the same `gen-s<seed>` directory as the reply
# `raw/`; it is one row per task, already aggregated, with a boolean
# `first_compiled`. v04-amp's verdict file (triples.jsonl) lives under a
# DIFFERENT root entirely (`runs-<size>/amp-<short>-s<seed>/`, derived
# from the raw arm-dir name `<size>-<short>` by a path transform, not a
# sibling lookup) and is one row per ATTEMPT, requiring an attempt==1
# filter before reading `compiled`. Because locating the verdict file is
# genuinely layout-specific but everything downstream of "here is the set
# of rejected task ids for this (arm, seed)" is identical, the shared
# logic lives in ONE core (`_rejection_crossed_core`) parameterized by a
# `rejected_tasks` callable, and each layout gets a thin adapter
# (`_campaign_rejected_tasks`, `_amp_rejected_tasks`) that only knows how
# to find and parse its own verdict file. `census_rejection_crossed` and
# `census_rejection_crossed_amp` are those two adapters wired to the
# core -- satisfying the brief's "one function with a verdict-lookup
# parameter, or two thin adapters" as both at once: the core takes the
# parameter, the two public names are the thin adapters.
#
# Both "present" and "rejected" come from the SAME per-file scan and the
# SAME join, in the same pass -- there is no separate presence-only scan
# that could drift from the rejection numbers. This is deliberate: a
# mutant that makes the join ignore the verdict (rejected := present, or
# rejected := 0 always) is only catchable if presence and rejection are
# read from one shared code path, which is why `census_rejection_crossed`
# returns both together rather than exposing a v2 presence-only sibling.


def _first_attempt_tasks(raw_dir: Path) -> dict[str, Path]:
    """task -> its `<task>.<harness-arm>.1.txt` reply path, for one
    `gen-s<seed>/raw` directory -- the session's first attempt, the only
    attempt either verdict source (first_compiled / attempt-1 compiled)
    describes."""
    out: dict[str, Path] = {}
    for path in sorted(Path(raw_dir).glob("*.1.txt")):
        task = path.name.split(".")[0]
        out[task] = path
    return out


def campaign_arms(root: Path) -> tuple[str, ...]:
    """v04-campaign's arm directory names -- every top-level directory
    holding at least one `gen-s*/cells.jsonl` (excludes `matched-v2/` and
    `REPORT.md`, which are not arm directories). Sorted for reproducible
    scans; unlike wave-1's `oxide_arms`, this does NOT filter to oxide-
    only, because v04-campaign's rejection cross-check is deliberately a
    4-arm (both dialects, both models) comparison -- see the task brief's
    "Data roots ... (4 arms)"."""
    root = Path(root)
    if not root.is_dir():
        return ()
    return tuple(sorted(
        p.name for p in root.iterdir()
        if p.is_dir() and any(p.glob("gen-s*/cells.jsonl"))
    ))


def amp_arms(raw_root: Path) -> tuple[str, ...]:
    """v04-amp's raw arm directory names (`<size>-ox`, `<size>-rs`, ...)
    under `eval/results/v04-amp/raw`. Sorted for reproducible scans."""
    raw_root = Path(raw_root)
    if not raw_root.is_dir():
        return ()
    return tuple(sorted(p.name for p in raw_root.iterdir() if p.is_dir()))


def _rejection_crossed_core(
    raw_root: Path,
    arms: tuple[str, ...],
    rejected_tasks: Callable[[Path, str, str], set[str] | None],
) -> dict:
    """Shared walk+join+count for both layouts. Walks
    `<raw_root>/<arm>/gen-s<seed>/raw/*.1.txt` for each arm in `arms`;
    for each (arm, seed) whose `raw/` directory exists, asks
    `rejected_tasks(raw_root, arm, seed)` for the set of task ids whose
    first attempt was rejected in that seed (None if that seed has no
    verdict source at all -- skipped rather than silently counted as
    zero rejections, so a missing verdict file cannot masquerade as "all
    accepted"). Every (family, spelling) V2_FAMILIES match in a reply
    file increments that arm's "present"; it additionally increments
    "rejected" iff the file's task is in the rejected set for that seed.
    """
    counts: dict[str, dict[str, dict[str, dict[str, int]]]] = {
        family: {
            spelling: {arm: {"present": 0, "rejected": 0} for arm in arms}
            for spelling in spellings
        }
        for family, spellings in V2_FAMILIES.items()
    }
    raw_root = Path(raw_root)
    for arm in arms:
        for seed_dir in sorted(raw_root.glob(f"{arm}/gen-s*")):
            raw_dir = seed_dir / "raw"
            if not raw_dir.is_dir():
                continue
            seed = seed_dir.name.removeprefix("gen-s")
            rejected = rejected_tasks(raw_root, arm, seed)
            if rejected is None:
                continue
            for task, path in sorted(_first_attempt_tasks(raw_dir).items()):
                text = path.read_text(encoding="utf-8", errors="replace")
                is_rejected = task in rejected
                for family, spelling in _v2_matches(text):
                    counts[family][spelling][arm]["present"] += 1
                    if is_rejected:
                        counts[family][spelling][arm]["rejected"] += 1
    return {
        family: {spelling: dict(per_arm) for spelling, per_arm in spellings.items()}
        for family, spellings in counts.items()
    }


def _campaign_rejected_tasks(campaign_root: Path, arm: str, seed: str) -> set[str] | None:
    """v04-campaign adapter: `<campaign_root>/<arm>/gen-s<seed>/cells.jsonl`,
    one row per task, `first_compiled` False -> rejected."""
    cells_path = Path(campaign_root) / arm / f"gen-s{seed}" / "cells.jsonl"
    if not cells_path.is_file():
        return None
    rejected: set[str] = set()
    for line in cells_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("first_compiled") is False:
            rejected.add(row["task"])
    return rejected


def census_rejection_crossed(campaign_root: Path, arms: tuple[str, ...]) -> dict:
    """Per (family, spelling, arm) file counts over v04-campaign's
    committed replies, crossed against whether each file's task was
    rejected (cells.jsonl `first_compiled` False) on its first attempt in
    that seed: `{"present": n_files, "rejected": n_files}`. See the
    module-level "THE JOIN" comment above `_first_attempt_tasks` for the
    join's shape and reliability evidence."""
    return _rejection_crossed_core(Path(campaign_root), arms, _campaign_rejected_tasks)


def _amp_rejected_tasks(amp_raw_root: Path, arm: str, seed: str) -> set[str] | None:
    """v04-amp adapter: `<amp_raw_root>`'s arm name `<size>-<short>` maps
    to the verdict file `<amp_raw_root's parent>/runs-<size>/amp-<short>-
    s<seed>/triples.jsonl` -- a path TRANSFORM, not a sibling lookup,
    because triples.jsonl lives under a differently-shaped `runs-<size>/`
    root next to (not inside) `raw/`. One row per ATTEMPT; only the
    attempt-1 row's `compiled` describes the session's first attempt --
    `collect_verified` (eval/train_corpus.py) reads the same triples.jsonl
    rows for its own (different) purpose, which is where this row shape
    is confirmed."""
    size, _, short = arm.partition("-")
    triples_path = (
        Path(amp_raw_root).parent / f"runs-{size}" / f"amp-{short}-s{seed}" / "triples.jsonl"
    )
    if not triples_path.is_file():
        return None
    rejected: set[str] = set()
    for line in triples_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("attempt") == 1 and row.get("compiled") is False:
            rejected.add(row["task"])
    return rejected


def census_rejection_crossed_amp(amp_raw_root: Path, arms: tuple[str, ...]) -> dict:
    """The v04-amp sibling of `census_rejection_crossed`: same per
    (family, spelling, arm) `{"present", "rejected"}` shape, joined
    against `runs-<size>/amp-<short>-s<seed>/triples.jsonl`'s attempt-1
    `compiled` instead of cells.jsonl's `first_compiled`."""
    return _rejection_crossed_core(Path(amp_raw_root), arms, _amp_rejected_tasks)


def _amp_verified_pool(amp_root: Path = AMP_ROOT) -> dict[tuple[str, str], set[str]]:
    """Merges `collect_verified` over every committed `runs-<size>/`
    directory under `amp_root` -- the amplified half of
    `census_handrolled_programs`'s pool (3 model sizes: 1.5, 7, 14)."""
    merged: dict[tuple[str, str], set[str]] = {}
    for runs_dir in sorted(Path(amp_root).glob("runs-*")):
        for key, progs in collect_verified(runs_dir).items():
            merged.setdefault(key, set()).update(progs)
    return merged


def census_handrolled_programs(
    references: dict[str, str] | None = None,
    amplified: dict[tuple[str, str], set[str]] | None = None,
) -> dict:
    """Per (pattern, source, class) program counts for the five
    HANDROLLED structural patterns, matched over `normalize_source`'d
    text (the brief's "pin each as a regex over normalized source").

    `references` defaults to `load_train_programs()` -- every committed
    file under `eval/train/pairs/`, i.e. the CURRENT, pre-re-author
    corpus (Task 7 re-authors it and reruns this census; the brief's
    "(current, re-authored)" names that before/after, not a third source
    tag here). `amplified` defaults to `_amp_verified_pool()`, the merged
    v04-amp verified pool. Both parameters exist so tests can inject
    synthetic programs (keyed by real task ids, so `load_train_tasks()`
    resolves a class) without touching the committed corpus; `main2`
    calls this with no arguments, matching the brief's signature.
    """
    if references is None:
        references = load_train_programs()
    if amplified is None:
        amplified = _amp_verified_pool()
    tasks = load_train_tasks()
    counts: dict[str, dict[str, Counter]] = {
        pattern: {source: Counter() for source in PROGRAM_SOURCES}
        for pattern in HANDROLLED
    }
    for path, text in sorted(references.items()):
        tid = path.split("/")[0]
        cls = tasks[tid]["class"]
        for pattern in _handrolled_matches(normalize_source(text)):
            counts[pattern]["reference"][cls] += 1
    for (tid, arm), progs in sorted(amplified.items()):
        cls = tasks[tid]["class"]
        for text in sorted(progs):
            for pattern in _handrolled_matches(normalize_source(text)):
                counts[pattern]["amplified"][cls] += 1
    return {
        pattern: {source: dict(per_class) for source, per_class in sources.items()}
        for pattern, sources in counts.items()
    }


def _family_rejected_total(family_data: dict) -> int:
    """Sum of "rejected" over every spelling and arm in one family --
    the REJECTION-CROSSED ranking key (not presence; see `ranked_table_v2`).
    """
    return sum(
        counts["rejected"]
        for per_arm in family_data.values()
        for counts in per_arm.values()
    )


def _family_present_total(family_data: dict) -> int:
    """Sum of "present" over every spelling and arm in one family --
    reported alongside the rejection total, never used to rank."""
    return sum(
        counts["present"]
        for per_arm in family_data.values()
        for counts in per_arm.values()
    )


def ranked_table_v2(rejection_crossed: dict) -> list[tuple[str, int, int]]:
    """(family, total_rejected, total_present), sorted by total_rejected
    descending then family name -- REJECTION-CROSSED demand, per the
    brief's "ranked by REJECTION-CROSSED demand", not presence. Total
    present is carried alongside so the ranking's denominator is legible
    in the same table, not a separate lookup."""
    rows = [
        (family, _family_rejected_total(spellings), _family_present_total(spellings))
        for family, spellings in rejection_crossed.items()
    ]
    return sorted(rows, key=lambda r: (-r[1], r[0]))


def _rejection_table(source_label: str, data: dict, arms: tuple[str, ...]) -> list[str]:
    """One markdown section: a table per family with present AND
    rejected side by side for every arm -- the brief's "presence AND
    rejection-crossed columns side by side"."""
    lines = [f"## {source_label}: presence vs rejection-crossed (per arm)", ""]
    for family in sorted(data):
        header_cells = []
        for arm in arms:
            header_cells += [f"{arm} present", f"{arm} rejected"]
        header = "| spelling | " + " | ".join(header_cells) + " |"
        sep = "|---|" + "---|" * len(header_cells)
        lines += [f"### {family}", "", header, sep]
        for spelling in sorted(data[family]):
            per_arm = data[family][spelling]
            cells: list[str] = []
            for arm in arms:
                arm_counts = per_arm.get(arm, {"present": 0, "rejected": 0})
                cells += [str(arm_counts["present"]), str(arm_counts["rejected"])]
            lines.append(f"| {spelling} | " + " | ".join(cells) + " |")
        lines.append("")
    return lines


def _handrolled_table(pattern: str, sources: dict, classes: tuple[str, ...]) -> list[str]:
    lines = [f"### {pattern}", ""]
    for source in PROGRAM_SOURCES:
        header = "| class | count |"
        sep = "|---|---|"
        lines += [f"**{source}**", "", header, sep]
        per_class = sources[source]
        for cls in classes:
            lines.append(f"| {cls} | {per_class.get(cls, 0)} |")
        total = sum(per_class.values())
        lines.append(f"| **total** | **{total}** |")
        lines.append("")
    return lines


def render_report2(
    rejection_crossed: dict,
    handrolled: dict,
    campaign_arms_: tuple[str, ...],
    amp_arms_: tuple[str, ...],
    classes: tuple[str, ...],
) -> str:
    """The committed v04-census2/REPORT.md: no recommendations, ranked by
    REJECTION-CROSSED demand (not presence) per the brief."""
    lines = [
        "# v0.4 Demand Census v2",
        "",
        "Extends `eval/demand_census.py` (wave-1 Task 1) with the "
        "`+=`/`-=`/`*=` compound-assign family (`COMPOUND_FAMILY`), five "
        "pinned hand-rolled structural patterns (`HANDROLLED`), and a "
        "rejection cross-check that joins each first-attempt reply to "
        "whether that session's first attempt compiled -- "
        "`eval/demand_census.py`'s module comments document the join's "
        "shape, the two committed layouts it reads, and the reliability "
        "check performed before any join code was written.",
        "",
        "This report contains no recommendations. The rankings are data "
        "for the wave's design-slate gate to read.",
        "",
    ]
    lines += _rejection_table("v04-campaign", rejection_crossed["campaign"], campaign_arms_)
    lines += _rejection_table("v04-amp", rejection_crossed["amp"], amp_arms_)

    lines += ["## Hand-rolled structural patterns (reference + amplified, per class)", ""]
    for pattern in sorted(handrolled):
        lines += _handrolled_table(pattern, handrolled[pattern], classes)

    for label, key in (("v04-campaign", "campaign"), ("v04-amp", "amp")):
        lines += [
            f"## Ranked demand ({label}, REJECTION-CROSSED)",
            "",
            "| family | total rejected | total present |",
            "|---|---|---|",
        ]
        for family, total_rejected, total_present in ranked_table_v2(rejection_crossed[key]):
            lines.append(f"| {family} | {total_rejected} | {total_present} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def build_census2(
    campaign_root: Path = CAMPAIGN_ROOT,
    amp_raw_root: Path = AMP_RAW_ROOT,
) -> dict:
    """The full census2.json payload -- pinned patterns, both layouts'
    rejection-crossed data, hand-rolled program counts, and scan metadata;
    no timestamps."""
    c_arms = campaign_arms(campaign_root)
    a_arms = amp_arms(amp_raw_root)
    rejection_crossed = {
        "campaign": census_rejection_crossed(campaign_root, c_arms),
        "amp": census_rejection_crossed_amp(amp_raw_root, a_arms),
    }
    handrolled = census_handrolled_programs()
    tasks = load_train_tasks()
    classes = tuple(sorted({t["class"] for t in tasks.values()}))
    return {
        "families": V2_FAMILIES,
        "handrolled_patterns": HANDROLLED,
        "rejection_crossed": rejection_crossed,
        "handrolled_programs": handrolled,
        "meta": {
            "campaign_root": str(campaign_root),
            "campaign_arms": list(c_arms),
            "amp_raw_root": str(amp_raw_root),
            "amp_arms": list(a_arms),
            "program_classes": list(classes),
        },
    }


def main2(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.demand_census --v2")
    parser.add_argument("--campaign-root", type=Path, default=CAMPAIGN_ROOT)
    parser.add_argument("--amp-root", type=Path, default=AMP_ROOT)
    parser.add_argument("--out", type=Path, default=OUT_DIR_V2)
    args = parser.parse_args(argv)

    amp_raw_root = Path(args.amp_root) / "raw"
    census = build_census2(args.campaign_root, amp_raw_root)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "census2.json").write_text(
        json.dumps(census, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = render_report2(
        census["rejection_crossed"],
        census["handrolled_programs"],
        tuple(census["meta"]["campaign_arms"]),
        tuple(census["meta"]["amp_arms"]),
        tuple(census["meta"]["program_classes"]),
    )
    (args.out / "REPORT.md").write_text(report, encoding="utf-8")
    print(f"wrote {args.out / 'census2.json'} and {args.out / 'REPORT.md'}")
    print(f"v04-campaign arms: {', '.join(census['meta']['campaign_arms'])}; "
          f"v04-amp arms: {', '.join(census['meta']['amp_arms'])}")
    return 0


if __name__ == "__main__":
    import sys

    if "--v2" in sys.argv[1:]:
        raise SystemExit(main2([a for a in sys.argv[1:] if a != "--v2"]))
    raise SystemExit(main())
