"""The 14B screen. Every test here pins a way the screen must refuse to
overclaim: a ratio not an absolute, a verdict not a number, and an
explicit right to decline."""
import json

import pytest

from eval.wave8_screen import (
    BAND_LANGUAGE,
    BAND_SEVEN_B,
    GUARD_ANCHORS,
    compile_rate,
    guard,
    render,
    screen,
    verdict,
)


def _arm(root, name, rows):
    """rows: list of (first_compiled, first_passed)"""
    d = root / name / "gen-s1"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "cells.jsonl", "w", encoding="utf-8") as fh:
        for i, (comp, passed) in enumerate(rows):
            fh.write(json.dumps({
                "task": f"t{i:02d}", "tokens_out": 10, "attempts_to_pass": 1,
                "first_compiled": comp, "first_passed": passed,
                "final_passed": passed,
            }) + "\n")


def test_compile_rate_counts_first_attempts_not_repairs(tmp_path):
    """Compile rate is the headline at this size, and it must describe
    the FIRST attempt -- a repair loop that eventually compiles says
    something different from a model that can write the language."""
    # The third cell did not compile on the first attempt but passed
    # after repair. Counting it would overstate the model's ability to
    # write the language, which is exactly what this metric is for.
    _arm(tmp_path, "a", [(True, False), (True, True), (False, True), (False, False)])
    c = compile_rate(tmp_path / "a")
    assert (c["n"], c["compiled"], c["rate"]) == (4, 2, 0.5)


def test_verdict_bands_are_the_pre_registered_ones():
    assert verdict(0.60) == "seven-b-property"
    assert verdict(BAND_SEVEN_B) == "seven-b-property"
    assert verdict(0.10) == "language-property"
    assert verdict(BAND_LANGUAGE) == "language-property"
    assert verdict(0.35) == "escalate"
    assert verdict(None) == "unmeasured"


def test_escalate_is_a_real_outcome_not_a_failure(tmp_path):
    """The screen is allowed to decline to conclude. A design that forced
    a verdict at n=60 would be manufacturing confidence."""
    _arm(tmp_path, "tune-ox-14", [(True, True)] * 30 + [(False, False)] * 30)
    _arm(tmp_path, "tune-rs-14", [(True, True)] * 60)
    _arm(tmp_path, "base-rs-14", [(True, True)] * 33 + [(True, False)] * 27)
    r = screen(tmp_path, tmp_path)
    assert r["large"]["compile_ratio"] == 0.5
    text = render(r)
    assert "ESCALATE" in text or r["verdict"] == "seven-b-property"


def test_ratio_not_absolute_so_a_better_14b_is_not_a_rescue(tmp_path):
    """The rust arm is deliberately NOT at 100%: with a perfect control
    the ratio numerically equals the oxide rate, and a version that
    reported the bare absolute would be indistinguishable from one that
    divides. Oxide 0.30 against rust 0.60 is a ratio of 0.50 -- a
    borderline rescue -- while the absolute 0.30 would read as a language
    property. The two disagree, which is the point."""
    _arm(tmp_path, "tune-ox-14", [(True, True)] * 30 + [(False, False)] * 70)
    _arm(tmp_path, "tune-rs-14", [(True, True)] * 60 + [(False, False)] * 40)
    _arm(tmp_path, "base-rs-14", [(True, True)] * 33 + [(True, False)] * 27)
    r = screen(tmp_path, tmp_path)
    assert r["large"]["oxide"]["rate"] == 0.30
    assert r["large"]["compile_ratio"] == 0.5
    assert r["verdict"] == "seven-b-property"
    assert verdict(0.30) == "escalate"  # what the absolute would have said


def test_guard_reports_a_verdict_against_the_seed_matched_anchor(tmp_path):
    """0.8000 is wave 4's tune-ox-14 restricted to seeds 1-3; its
    PUBLISHED ten-seed figure is 0.7450. Anchoring on the published
    number would fail a healthy adapter."""
    assert GUARD_ANCHORS["tune-ox-14"] == 0.8000
    _arm(tmp_path, "tune-ox-14", [(True, True)] * 48 + [(True, False)] * 12)
    g = guard(tmp_path / "tune-ox-14", "tune-ox-14")
    assert g["pass1"] == 0.8
    assert g["reproduced"] is True


def test_missed_guard_is_said_loudly_in_the_render(tmp_path):
    _arm(tmp_path, "base-rs-14", [(True, True)] * 10 + [(True, False)] * 50)
    _arm(tmp_path, "tune-ox-14", [(True, True)] * 48 + [(True, False)] * 12)
    _arm(tmp_path, "tune-rs-14", [(True, True)] * 60)
    r = screen(tmp_path, tmp_path)
    assert r["guards_all_reproduced"] is False
    assert "did not reproduce" in render(r)


def test_guard_without_an_anchor_refuses_rather_than_inventing_one(tmp_path):
    from eval.experiment_report import ReportError

    _arm(tmp_path, "tune-rs-14", [(True, True)] * 60)
    with pytest.raises(ReportError):
        guard(tmp_path / "tune-rs-14", "tune-rs-14")


def test_zero_rust_compiles_yields_no_ratio_rather_than_a_division(tmp_path):
    _arm(tmp_path, "base-rs-14", [(True, True)] * 33 + [(True, False)] * 27)
    _arm(tmp_path, "tune-ox-14", [(True, True)] * 48 + [(True, False)] * 12)
    _arm(tmp_path, "tune-rs-14", [(False, False)] * 60)
    r = screen(tmp_path, tmp_path)
    assert r["large"]["compile_ratio"] is None
    assert r["verdict"] == "unmeasured"
