"""Learnability: uptake per unit corpus exposure (SPEC §62.1).

The project's third objective is ease of use and learning for an LLM,
and until wave 4 it had no instrument. Wave 3 showed why one is needed:
`reverse` drew 50 uses from 1.7% corpus exposure while `count_if` drew 0
from 2.4%. Read as raw uptake those say "reverse won"; read as a ratio
they say something sharper -- `reverse` is *learnable* and `count_if` is
not, and the difference is familiarity, not teaching.

The estimand is deliberately a ratio, and deliberately reports both of
its terms. A construct is never called "rejected" on an uptake count
whose exposure nobody looked at; that is precisely the mistake the
wave-3 report had to amend.
"""
from __future__ import annotations

from collections.abc import Mapping


def learnability(
    uptake: Mapping[str, int],
    exposure: Mapping[str, float],
) -> dict[str, dict]:
    """Per-construct learnability rows.

    `uptake` is a count of replies using the construct; `exposure` is the
    fraction of training examples containing it (0.0-1.0).

    A construct with **zero exposure** gets `ratio: None`, not infinity
    and not zero: the corpus never taught it, so there is no learnability
    reading to report. A construct with real exposure and zero uptake
    gets a measured `0.0` -- that one IS a reading, and a damning one.
    Both terms ride along in every row so a ratio can never be quoted
    without the numbers that produced it.
    """
    rows: dict[str, dict] = {}
    for name in sorted(set(uptake) | set(exposure)):
        used = uptake.get(name, 0)
        seen = exposure.get(name)
        if seen is None or seen <= 0.0:
            ratio = None
        else:
            ratio = used / seen
        rows[name] = {"uptake": used, "exposure": seen, "ratio": ratio}
    return rows


def rank(rows: Mapping[str, dict]) -> list[tuple[str, dict]]:
    """Most learnable first; unmeasured (`ratio is None`) always last.

    Ties break on construct name so the ranking is reproducible rather
    than dependent on dict insertion order.
    """
    return sorted(
        rows.items(),
        key=lambda kv: (
            kv[1]["ratio"] is None,
            -(kv[1]["ratio"] or 0.0),
            kv[0],
        ),
    )


def unmeasured(rows: Mapping[str, dict]) -> list[str]:
    """Constructs with no learnability reading, named rather than hidden."""
    return sorted(k for k, v in rows.items() if v["ratio"] is None)


def render(rows: Mapping[str, dict]) -> str:
    """Markdown table, both terms beside every ratio."""
    lines = [
        "| construct | uptake | corpus exposure | learnability |",
        "|---|---:|---:|---:|",
    ]
    for name, row in rank(rows):
        seen = "—" if row["exposure"] is None else f"{100 * row['exposure']:.1f}%"
        ratio = "unmeasured" if row["ratio"] is None else f"{row['ratio']:.0f}"
        lines.append(f"| `{name}` | {row['uptake']} | {seen} | {ratio} |")
    return "\n".join(lines)
