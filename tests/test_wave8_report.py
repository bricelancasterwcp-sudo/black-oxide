"""Wave 8 Phase B endpoint reporting.

Synthetic cells exercise the verdicts; the point of every test here is
that a number cannot be quoted without the thing that qualifies it.
"""
import json

import pytest

from eval.wave8_report import (
    DRIFT_GUARD_PASS1,
    MIN_PAIRS,
    build,
    drift_guard,
    render,
    tier_surplus,
)


def _write_arm(root, arm, rows):
    """rows: {(seed, task): (tokens_out, passed)}"""
    for (seed, task), (tokens, passed) in rows.items():
        d = root / arm / seed
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "cells.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "task": task, "arm": arm, "tokens_out": tokens,
                "first_passed": passed, "final_passed": passed,
                "attempts_to_pass": 1,
            }) + "\n")


def test_drift_guard_reports_a_verdict_not_a_bare_number(tmp_path):
    """A run that missed the control is not a run whose other figures may
    be quoted, so the guard must say so rather than emit a float."""
    _write_arm(tmp_path, "base-rs-7", {
        ("gen-s1", "t01"): (10, True),
        ("gen-s1", "t02"): (10, False),
    })
    g = drift_guard(tmp_path / "base-rs-7")
    assert g["pass1"] == 0.5
    assert g["reproduced"] is False
    assert g["expected"] == DRIFT_GUARD_PASS1


def test_drift_guard_reproduced_when_it_hits_the_pinned_control(tmp_path):
    rows = {}
    for i in range(1000):
        rows[(f"gen-s{i}", "t01")] = (10, i < 565)
    _write_arm(tmp_path, "base-rs-7", rows)
    assert drift_guard(tmp_path / "base-rs-7")["reproduced"] is True


def test_tier_surplus_flags_an_undersized_sample_rather_than_hiding_it(tmp_path):
    """Stop 3. The ratio is still reported -- withdrawing it silently
    would be its own dishonesty -- but it carries the reason it cannot
    be leaned on."""
    from eval.cost_census import LARGE_SOURCE
    from eval.token_match import qwen_counter

    _write_arm(tmp_path, "tune-ox-7", {("gen-s1", "g01"): (272, True)})
    _write_arm(tmp_path, "tune-rs-7", {("gen-s1", "g01"): (265, True)})
    out = tier_surplus(tmp_path, LARGE_SOURCE, qwen_counter())
    assert out["model"]["n_pairs"] == 1 < MIN_PAIRS
    assert out["sufficient"] is False
    assert "must not be quoted as an endpoint" in out["note"]
    assert out["surplus"] is not None


def test_tier_surplus_is_clean_when_the_sample_is_large_enough(tmp_path):
    from eval.cost_census import LARGE_SOURCE
    from eval.token_match import qwen_counter

    ox = {(f"gen-s{i}", "g01"): (272, True) for i in range(1, 7)}
    rs = {(f"gen-s{i}", "g01"): (265, True) for i in range(1, 7)}
    _write_arm(tmp_path, "tune-ox-7", ox)
    _write_arm(tmp_path, "tune-rs-7", rs)
    out = tier_surplus(tmp_path, LARGE_SOURCE, qwen_counter())
    assert out["model"]["n_pairs"] == 6
    assert out["sufficient"] is True
    assert "note" not in out
    assert out["surplus"] == 1.0


def test_render_says_loudly_when_the_control_did_not_reproduce(tmp_path):
    _write_arm(tmp_path, "base-rs-7", {("gen-s1", "t01"): (10, False)})
    _write_arm(tmp_path, "tune-ox-7", {("gen-s1", "g01"): (272, True)})
    _write_arm(tmp_path, "tune-rs-7", {("gen-s1", "g01"): (265, True)})
    text = render(build(tmp_path, tmp_path))
    assert "MISSED" in text
    assert "not comparable" in text


def test_build_refuses_when_the_control_arm_is_missing(tmp_path):
    from eval.experiment_report import ReportError

    with pytest.raises(ReportError):
        build(tmp_path, tmp_path)
