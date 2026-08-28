"""The census counts what the pinned patterns define — nothing else.

Synthetic fixtures pin each family's regex against positive AND
negative examples; the acceptance test pins one hand-verified count
from the committed campaign replies so pattern drift fails loudly.
"""
import json
from pathlib import Path

from eval.demand_census import (
    COMPOUND_FAMILY,
    FAMILIES,
    HANDROLLED,
    V2_FAMILIES,
    amp_arms,
    campaign_arms,
    census_handrolled_programs,
    census_rejection_crossed,
    census_rejection_crossed_amp,
    census_replies,
)


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


# ==========================================================================
# v0.4 wave-2 Task 1: COMPOUND_FAMILY, HANDROLLED, and the rejection
# cross-check. FAMILIES/census_replies/census_programs/main stay exactly
# as wave-1 left them (proven by every test above still passing
# unchanged) -- everything below exercises the NEW v2 surface only.


def test_compound_family_is_separate_from_wave1_families():
    """COMPOUND_FAMILY is "folded into the census's family handling" via
    V2_FAMILIES (used by census_rejection_crossed and its amp sibling),
    NOT spliced into wave-1's FAMILIES -- byte-compatibility depends on
    FAMILIES never gaining a ninth key."""
    assert "compound_assign" not in FAMILIES
    assert set(V2_FAMILIES) == set(FAMILIES) | set(COMPOUND_FAMILY)


def _write_cells(seed_dir: Path, rows: list[dict]) -> None:
    seed_dir.mkdir(parents=True, exist_ok=True)
    (seed_dir / "cells.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_compound_assign_positive_and_negative(tmp_path):
    arm = "base-ox-7"
    seed_dir = tmp_path / arm / "gen-s1"
    raw = seed_dir / "raw"
    raw.mkdir(parents=True)
    # t01: two genuine `+=` occurrences plus one genuine `-=` and one
    # genuine `*=`, all in ONE file -- the duplicate `+=` is the
    # per-occurrence-flip mutation check (Step-5 style, wave-1's own
    # test_range_patterns_positive_and_negative precedent): per-file
    # counting must hold this file's contribution to plus_eq at 1, not 2.
    (raw / "t01.oxide.1.txt").write_text(
        "score += 1\ncount += 2\nscale -= 1\ntotal *= 2\n", encoding="utf-8")
    # t02: comparison operators only -- must never register any
    # compound_assign spelling ("+="/"-="/"*=" yes; "<="/"=="/"!=" never).
    (raw / "t02.oxide.1.txt").write_text(
        "if a <= b { }\nif a == b { }\nif a != b { }\n", encoding="utf-8")
    # t03: adjacent-operator text where a DROPPED lookbehind guard would
    # misread the tail of a longer punctuation run as a genuine spelling:
    # "=+=" and "=-=" tail a "+="/"-=" right after another "=" (guarded);
    # "**=" tails a "*=" right after another "*" -- the Python
    # power-assign leak the module docstring names as the guard's real
    # motivating case. If the lookbehind is dropped, this file's matches
    # push plus_eq/minus_eq/times_eq's t01-only count of 1 up to 2.
    (raw / "t03.oxide.1.txt").write_text(
        "level =+= 1\nscale =-= 1\ncount **= 2\n", encoding="utf-8")
    _write_cells(seed_dir, [
        {"task": "t01", "first_compiled": True},
        {"task": "t02", "first_compiled": True},
        {"task": "t03", "first_compiled": True},
    ])

    counts = census_rejection_crossed(tmp_path, (arm,))
    assert counts["compound_assign"]["plus_eq"][arm] == {"present": 1, "rejected": 0}
    assert counts["compound_assign"]["minus_eq"][arm] == {"present": 1, "rejected": 0}
    assert counts["compound_assign"]["times_eq"][arm] == {"present": 1, "rejected": 0}


def test_rejection_cross_fixture_reads_first_compiled(tmp_path):
    """A synthetic cells.jsonl proves the join reads `first_compiled`,
    not a stand-in like "always rejected" or "never rejected": present=3
    (three files reach for `+=`), rejected=2 (two of those three sessions
    failed to compile on their first attempt). A join that ignores the
    verdict entirely (rejected := present, or rejected := 0 always)
    cannot reproduce 2 -- it can only reproduce 3 or 0."""
    arm = "base-ox-7"
    seed_dir = tmp_path / arm / "gen-s1"
    raw = seed_dir / "raw"
    raw.mkdir(parents=True)
    (raw / "t01.oxide.1.txt").write_text("score += 1\n", encoding="utf-8")
    (raw / "t02.oxide.1.txt").write_text("count += 1\n", encoding="utf-8")
    (raw / "t03.oxide.1.txt").write_text("total += 1\n", encoding="utf-8")
    (raw / "t04.oxide.1.txt").write_text("print(total)\n", encoding="utf-8")  # no match at all
    _write_cells(seed_dir, [
        {"task": "t01", "first_compiled": False},
        {"task": "t02", "first_compiled": False},
        {"task": "t03", "first_compiled": True},
        {"task": "t04", "first_compiled": False},
    ])

    counts = census_rejection_crossed(tmp_path, (arm,))
    assert counts["compound_assign"]["plus_eq"][arm] == {"present": 3, "rejected": 2}


def test_rejection_cross_ignores_missing_verdict_seed(tmp_path):
    """A `gen-s<seed>/raw` with no cells.jsonl is skipped, not silently
    scored as zero rejections for its files -- a missing verdict source
    must not masquerade as "everything accepted"."""
    arm = "base-ox-7"
    raw = tmp_path / arm / "gen-s1" / "raw"
    raw.mkdir(parents=True)
    (raw / "t01.oxide.1.txt").write_text("score += 1\n", encoding="utf-8")
    # No cells.jsonl written for gen-s1.

    counts = census_rejection_crossed(tmp_path, (arm,))
    assert counts["compound_assign"]["plus_eq"][arm] == {"present": 0, "rejected": 0}


def test_amp_layout_rejection_crossed(tmp_path):
    """A synthetic v04-amp-shaped fixture proves the triples.jsonl
    adapter joins on the attempt-1 row specifically: n001's attempt-2 row
    (compiled True) must be IGNORED -- only its attempt-1 row (compiled
    False) decides rejection, or this fixture's rejected=1 would drift to
    0."""
    amp_raw_root = tmp_path / "raw"
    arm = "7-ox"
    raw = amp_raw_root / arm / "gen-s3" / "raw"
    raw.mkdir(parents=True)
    (raw / "n001.oxide.1.txt").write_text("score += 1\n", encoding="utf-8")
    (raw / "n002.oxide.1.txt").write_text("count += 1\n", encoding="utf-8")
    triples_dir = tmp_path / "runs-7" / "amp-ox-s3"
    triples_dir.mkdir(parents=True)
    rows = [
        {"task": "n001", "arm": "oxide", "attempt": 1, "compiled": False, "passed": False},
        {"task": "n001", "arm": "oxide", "attempt": 2, "compiled": True, "passed": True},
        {"task": "n002", "arm": "oxide", "attempt": 1, "compiled": True, "passed": True},
    ]
    (triples_dir / "triples.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    counts = census_rejection_crossed_amp(amp_raw_root, (arm,))
    assert counts["compound_assign"]["plus_eq"][arm] == {"present": 2, "rejected": 1}


def test_campaign_arms_excludes_non_arm_directories():
    arms = campaign_arms(Path("eval/results/v04-campaign"))
    assert set(arms) == {"base-ox-7", "base-rs-7", "tune-ox-7", "tune-rs-7"}


def test_amp_arms_lists_raw_arm_directories():
    arms = amp_arms(Path("eval/results/v04-amp/raw"))
    assert set(arms) == {"1.5-ox", "1.5-rs", "7-ox", "7-rs", "14-ox", "14-rs"}


def test_handrolled_families_cover_the_spec_slate():
    assert {"occurrence_count", "removal_rebuild", "minmax_scan",
            "sum_scan", "string_build"} <= set(HANDROLLED)


def test_handrolled_occurrence_count_positive_and_negative():
    # Duplicated with a second accumulator name in the same program: the
    # per-program counting rule must hold this at 1, not 2 (per-occurrence
    # flip mutation check).
    positive_once = (
        "fn main() {\n"
        "    let count = 0\n"
        "    for c in chars(\"coffee\") {\n"
        "        if c == \"f\" {\n"
        "            count = count + 1\n"
        "        }\n"
        "    }\n"
        "    print(count)\n"
        "}\n"
    )
    positive_twice = positive_once + positive_once.replace("count", "total")
    # A for loop with NO if-guard is sum_scan-shaped, not
    # occurrence_count-shaped -- must not register here.
    negative = (
        "fn main() {\n"
        "    let total = 0\n"
        "    for x in v {\n"
        "        total = total + x\n"
        "    }\n"
        "    print(total)\n"
        "}\n"
    )
    counts = census_handrolled_programs(
        references={"n001/oxide.ox": positive_twice, "n002/oxide.ox": negative},
        amplified={},
    )
    assert counts["occurrence_count"]["reference"]["arithmetic/loops"] == 1


def test_handrolled_sum_scan_positive_and_negative():
    positive = (
        "fn main() {\n"
        "    let total = 0\n"
        "    for i in range(1, 6) {\n"
        "        total = total + i * i * i\n"
        "    }\n"
        "    print(total)\n"
        "}\n"
    )
    # The accumulator is never reassigned inside the for -- no scan, just
    # a zero-init that happens to precede an unrelated loop.
    negative = (
        "fn main() {\n"
        "    let total = 0\n"
        "    for i in range(1, 6) {\n"
        "        print(i)\n"
        "    }\n"
        "    print(total)\n"
        "}\n"
    )
    counts = census_handrolled_programs(
        references={"n001/oxide.ox": positive, "n002/oxide.ox": negative},
        amplified={},
    )
    assert counts["sum_scan"]["reference"]["arithmetic/loops"] == 1


def test_handrolled_minmax_scan_positive_and_negative():
    positive = (
        "fn main() {\n"
        "    let best = 1000000\n"
        "    for x in v {\n"
        "        if x < best {\n"
        "            best = x\n"
        "        }\n"
        "    }\n"
        "    print(best)\n"
        "}\n"
    )
    # Uses the min() builtin directly -- no hand-rolled scan at all.
    negative_builtin = (
        "fn main() {\n"
        "    let best = unwrap_or(min(v), 1000000)\n"
        "    print(best)\n"
        "}\n"
    )
    # A counter accumulation gated by a threshold comparison -- shaped
    # like occurrence_count/sum_scan (self-referential `= acc + 1`), NOT
    # a comparative min/max reassignment (`= x`, a DIFFERENT variable).
    # This is the exact false positive an early draft of minmax_scan's
    # regex produced against real n046/oxide.ox before the self-reference
    # exclusion was added (see task-1-report.md's fixture rationale).
    negative_self_reference = (
        "fn main() {\n"
        "    let under = 0\n"
        "    for x in v {\n"
        "        if x < 10 {\n"
        "            under = under + 1\n"
        "        }\n"
        "    }\n"
        "    print(under)\n"
        "}\n"
    )
    counts = census_handrolled_programs(
        references={
            "n001/oxide.ox": positive,
            "n002/oxide.ox": negative_builtin,
            "n003/oxide.ox": negative_self_reference,
        },
        amplified={},
    )
    assert counts["minmax_scan"]["reference"]["arithmetic/loops"] == 1


def test_handrolled_removal_rebuild_positive_and_negative():
    positive = (
        "fn main() {\n"
        "    let rest = vec()\n"
        "    let removed = false\n"
        "    for x in remaining {\n"
        "        if x == m && removed == false {\n"
        "            removed = true\n"
        "        } else {\n"
        "            rest = push(rest, x)\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    # Unconditional push -- no skip condition, so this is ordinary
    # vec-building, not removal_rebuild.
    negative = (
        "fn main() {\n"
        "    let out = vec()\n"
        "    for x in v {\n"
        "        out = push(out, x)\n"
        "    }\n"
        "}\n"
    )
    counts = census_handrolled_programs(
        references={"n041/oxide.ox": positive, "n043/oxide.ox": negative},
        amplified={},
    )
    assert counts["removal_rebuild"]["reference"]["vectors"] == 1


def test_handrolled_string_build_positive_and_negative():
    positive = (
        "fn main() {\n"
        "    let cs = chars(\"drum\")\n"
        "    let out = \"\"\n"
        "    for c in cs {\n"
        "        out = concat(c, out)\n"
        "    }\n"
        "    print_str(out)\n"
        "}\n"
    )
    # chars() drives the loop but nothing is built -- a per-char SCAN,
    # not a per-char BUILD.
    negative = (
        "fn main() {\n"
        "    let i = 0\n"
        "    for c in chars(\"banana\") {\n"
        "        if c == \"n\" {\n"
        "            print(i)\n"
        "        }\n"
        "        i = i + 1\n"
        "    }\n"
        "}\n"
    )
    counts = census_handrolled_programs(
        references={"n051/oxide.ox": positive, "n052/oxide.ox": negative},
        amplified={},
    )
    assert counts["string_build"]["reference"]["strings"] == 1


def test_handrolled_amplified_source():
    """The `amplified` pool is a separate code path from `references` --
    exercised independently so a bug scoped to just one source cannot
    hide behind the reference-side tests above."""
    positive = (
        "fn main() {\n"
        "    let total = 0\n"
        "    for i in range(1, 6) {\n"
        "        total = total + i\n"
        "    }\n"
        "    print(total)\n"
        "}\n"
    )
    counts = census_handrolled_programs(
        references={},
        amplified={("n001", "oxide"): {positive}},
    )
    assert counts["sum_scan"]["amplified"]["arithmetic/loops"] == 1


def test_acceptance_pin_rejection_crossed_compound_assign():
    counts = census_rejection_crossed(
        Path("eval/results/v04-campaign"), ("base-ox-7",))
    # Hand-verified 2026-08-28, two independent ways (neither calls
    # census_rejection_crossed or any function in eval/demand_census.py;
    # full transcript in task-1-report.md):
    #   1. grep -rlP '(?<![+\-*/=!<>])\+=' \
    #        eval/results/v04-campaign/base-ox-7/*/raw/*.1.txt | wc -l
    #      -> 64 (a plain `grep -rl '+='` over the same files also gives
    #      64, confirming the lookbehind guard changes nothing on this
    #      arm's real first-attempt replies).
    #   2. a from-scratch python recount that re-implements the join
    #      independently (its own regex, its own cells.jsonl parsing) and
    #      cross-tabulates first_compiled for those same 64 files ->
    #      present=64, rejected=64. Oxide has no `+=`: EVERY first-attempt
    #      reply that reaches for it fails to compile.
    result = counts["compound_assign"]["plus_eq"]["base-ox-7"]
    assert result == {"present": 64, "rejected": 64}
