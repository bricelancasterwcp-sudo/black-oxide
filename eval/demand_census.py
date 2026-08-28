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
from pathlib import Path

from eval.token_match import load_matched_inputs

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


if __name__ == "__main__":
    raise SystemExit(main())
