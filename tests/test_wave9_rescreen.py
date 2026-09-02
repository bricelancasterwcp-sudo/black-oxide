"""Wave 9's re-screen reader. Every test pins a way the reader must
refuse to overclaim: bands are the ones pre-registered on 2026-09-02,
the baseline comes from the committed wave-8 cells rather than a typed
number, and a missed guard blocks the comparison outright."""
import json
from pathlib import Path

import pytest

from eval.wave8_screen import LEXER_SHARE_BASELINE, diagnostic_mix, compile_rate
from eval.wave9_rescreen import (
    BAND_PARTIAL,
    BAND_REAL,
    BASELINE_RATIO,
    LEXER_SHARE_CONFIRMED_BELOW,
    mechanism,
    reading,
    render,
    rescreen,
)

WAVE8 = Path("eval/results/v04-wave8-14b-screen")


def _arm(root, name, rows):
    d = root / name / "gen-s1"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "cells.jsonl", "w", encoding="utf-8") as fh:
        for i, (comp, passed) in enumerate(rows):
            fh.write(json.dumps({
                "task": f"t{i:02d}", "tokens_out": 10, "attempts_to_pass": 1,
                "first_compiled": comp, "first_passed": passed,
                "final_passed": passed,
            }) + "\n")


def _triples(root, name, codes):
    d = root / name / f"{name}-gen-s1"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "triples.jsonl", "w", encoding="utf-8") as fh:
        for code in codes:
            diags = [] if code is None else [{"code": code, "message": "m"}]
            fh.write(json.dumps({"task": "g01", "attempt": 1, "code": "x",
                                 "diagnostics": diags}) + "\n")


def _guards_ok(root):
    _arm(root, "base-rs-14", [(True, True)] * 33 + [(True, False)] * 27)
    _arm(root, "tune-ox-14", [(True, True)] * 48 + [(True, False)] * 12)


def test_reading_bands_are_the_pre_registered_ones():
    """Literal edges, not the constants: a constant that drifted would
    otherwise agree with itself."""
    assert (BAND_REAL, BAND_PARTIAL) == (0.20, 0.12)
    assert reading(0.30) == "binding-constraint"
    assert reading(0.20) == "binding-constraint"
    assert reading(0.199) == "partial"
    assert reading(0.15) == "partial"
    assert reading(0.12) == "partial"
    assert reading(0.119) == "next-barrier"
    assert reading(0.0652) == "next-barrier"
    assert reading(None) == "unmeasured"


def test_mechanism_check_is_the_lexer_share_against_a_chosen_threshold():
    assert LEXER_SHARE_CONFIRMED_BELOW == 0.15
    assert mechanism(0.10) == "attribution-confirmed"
    assert mechanism(0.149) == "attribution-confirmed"
    assert mechanism(0.15) == "attribution-wrong"
    assert mechanism(0.30) == "attribution-wrong"
    assert mechanism(None) == "unmeasured"


def test_baselines_are_the_committed_wave8_cells_not_typed_numbers():
    """The plan first quoted 73/191; the instrument over the committed
    cells says 73/216. Whatever the constant claims, it must equal what
    the same code computes from the record."""
    ox = compile_rate(WAVE8 / "results-large" / "tune-ox-14")
    rs = compile_rate(WAVE8 / "results-large" / "tune-rs-14")
    assert round(ox["rate"] / rs["rate"], 4) == BASELINE_RATIO == 0.0652
    mix = diagnostic_mix(WAVE8 / "results-large" / "tune-ox-14")
    assert (mix["codes"]["OX0001"], mix["failed"]) == (73, 216)
    assert mix["lexer_share"] == LEXER_SHARE_BASELINE == 73 / 216


def test_rescreen_reports_the_delta_against_wave8(tmp_path):
    large = tmp_path / "large"; small = tmp_path / "small"
    _guards_ok(small)
    _arm(large, "tune-ox-14", [(True, True)] * 15 + [(False, False)] * 45)
    _arm(large, "tune-rs-14", [(True, True)] * 45 + [(False, False)] * 15)
    _triples(large, "tune-ox-14", ["OX0001"] * 4 + ["OX0200"] * 36)
    r = rescreen(large, small)
    w9 = r["wave9"]
    assert w9["ratio"] == round(0.25 / 0.75, 4)
    assert w9["baseline_ratio"] == 0.0652
    assert w9["delta"] == round(w9["ratio"] - 0.0652, 4)
    assert w9["reading"] == "binding-constraint"
    assert w9["lexer_share"] == 0.1
    assert w9["mechanism"] == "attribution-confirmed"


def test_wave8_band_verdict_is_not_the_headline(tmp_path):
    """wave8_screen's verdict() applies wave 8's bands (0.50/0.20). Left
    at the top level it would read as THE verdict of this run. It is
    kept, renamed, so nobody mistakes it."""
    large = tmp_path / "large"; small = tmp_path / "small"
    _guards_ok(small)
    _arm(large, "tune-ox-14", [(True, True)] * 3 + [(False, False)] * 57)
    _arm(large, "tune-rs-14", [(True, True)] * 46 + [(False, False)] * 14)
    _triples(large, "tune-ox-14", ["OX0001"] * 5 + ["OX0200"] * 5)
    r = rescreen(large, small)
    assert "verdict" not in r
    assert r["wave8_band_verdict"] == "language-property"


def test_missed_guard_blocks_the_comparison(tmp_path):
    """Stop 1 of the plan: a guard off its seed-matched anchor means the
    environment or the merge is suspect, and no ratio is published
    against wave 8. The ratio is still printed for the record."""
    large = tmp_path / "large"; small = tmp_path / "small"
    _arm(small, "base-rs-14", [(True, True)] * 40 + [(True, False)] * 20)  # 0.667 != 0.55
    _arm(small, "tune-ox-14", [(True, True)] * 48 + [(True, False)] * 12)
    _arm(large, "tune-ox-14", [(True, True)] * 15 + [(False, False)] * 45)
    _arm(large, "tune-rs-14", [(True, True)] * 45 + [(False, False)] * 15)
    _triples(large, "tune-ox-14", ["OX0001"] * 4 + ["OX0200"] * 36)
    r = rescreen(large, small)
    assert r["guards_all_reproduced"] is False
    assert r["wave9"]["ratio"] == round(0.25 / 0.75, 4)
    assert r["wave9"]["delta"] is None
    assert r["wave9"]["reading"] == "guards-missed"
    text = render(r)
    assert "did not reproduce" in text and "no ratio" in text.lower()


def test_render_states_reading_mechanism_and_both_baselines(tmp_path):
    large = tmp_path / "large"; small = tmp_path / "small"
    _guards_ok(small)
    # 6/60 over 45/60 = 0.1333: inside [0.12, 0.20). (9/60 would be
    # exactly 0.20, the band edge, and read as binding -- caught the
    # first time this test ran.)
    _arm(large, "tune-ox-14", [(True, True)] * 6 + [(False, False)] * 54)
    _arm(large, "tune-rs-14", [(True, True)] * 45 + [(False, False)] * 15)
    _triples(large, "tune-ox-14", ["OX0001"] * 12 + ["OX0200"] * 28)
    text = render(rescreen(large, small))
    assert "0.0652" in text and "0.338" in text
    assert "PARTIAL" in text
    assert "ATTRIBUTION-WRONG" in text
    assert "base-rs-14" in text and "tune-ox-14" in text
