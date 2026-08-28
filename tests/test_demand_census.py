"""The census counts what the pinned patterns define — nothing else.

Synthetic fixtures pin each family's regex against positive AND
negative examples; the acceptance test pins one hand-verified count
from the committed campaign replies so pattern drift fails loudly.
"""
from pathlib import Path

from eval.demand_census import FAMILIES, census_replies


def test_families_cover_the_spec_slate():
    assert {"ranges", "sort", "minmax", "sum", "index_assign",
            "contains", "option", "strings"} <= set(FAMILIES)


def test_range_patterns_positive_and_negative(tmp_path):
    raw = tmp_path / "base-ox-7" / "gen-s1" / "raw"
    raw.mkdir(parents=True)
    # The second `range(0, 5)` is a deliberate duplicate (see Step 5
    # mutation-check #1 in the task report): with per-file counting the
    # duplicate must NOT push range_call above 1 for this file, but an
    # occurrence-counting mutant would double-count it to 2. Without a
    # repeated spelling in the fixture, that mutation is invisible.
    (raw / "t01.oxide.1.txt").write_text(
        "for i in 0..10 {\n}\nfor x in range(0, 5) {\n}\n"
        "for y in range(0, 5) {\n}\nlet y = a.to(n)\n",
        encoding="utf-8")
    (raw / "t02.oxide.1.txt").write_text(
        "let z = 1.5\nprint(z)\n", encoding="utf-8")  # a float is not a range
    counts = census_replies(tmp_path, ("base-ox-7",))
    assert counts["ranges"]["dotdot"]["base-ox-7"] == 1
    assert counts["ranges"]["range_call"]["base-ox-7"] == 1
    assert counts["ranges"]["to_method"]["base-ox-7"] == 1


def test_index_assign_excludes_comparison(tmp_path):
    raw = tmp_path / "a" / "gen-s1" / "raw"
    raw.mkdir(parents=True)
    (raw / "t01.oxide.1.txt").write_text(
        "v[i] = 5\nif v[i] == 5 {\n}\n", encoding="utf-8")
    # A second, comparison-ONLY file (Step 5 mutation-check #2 in the
    # task report): dropping the `[^=]` negative guard would make this
    # file ALSO count, moving the arm total from 1 to 2. Without a file
    # that has no genuine assignment, the guard's removal is invisible
    # here -- t01 already matches via its real `v[i] = 5` line.
    (raw / "t02.oxide.1.txt").write_text(
        "if v[i] == 5 {\n}\n", encoding="utf-8")
    counts = census_replies(tmp_path, ("a",))
    assert counts["index_assign"]["bracket"]["a"] == 1  # the == line must not count


def test_acceptance_pin_on_committed_replies():
    counts = census_replies(Path("eval/results/runpod-exp"),
                            ("base-ox-7",))
    # Hand-verified 2026-08-28:
    #   grep -rlE '\brange\s*\(' eval/results/runpod-exp/base-ox-7/*/raw | wc -l
    # -> 264 (773 raw files scanned; see task-1-report.md for the full
    # verification transcript, including a pure-Python cross-check that
    # reproduces the same number via census_replies' own glob).
    assert counts["ranges"]["range_call"]["base-ox-7"] == 264
