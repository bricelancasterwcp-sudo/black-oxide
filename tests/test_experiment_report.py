"""The analysis instrument: pre-registered endpoints, refusal until done.

Synthetic fixtures exercise the math; the acceptance test pins the
instrument against the committed v03 closing baseline (qwen oxide
first-pass 0.305, rust 0.565 — the published REPORT numbers).
"""
import json
from pathlib import Path

import pytest

from eval.experiment_report import (
    ARM_NAMES,
    SIZES,
    ReportError,
    build_report,
    gen_metrics,
    load_cells,
    paired_pass1,
    require_complete,
    strict_repair_rate,
    unpaired_pass1,
)


def _cell(task, first, final, attempts_to_pass=1, tokens_out=50):
    return {"task": task, "arm": "oxide", "first_passed": first,
            "final_passed": final, "attempts_to_pass": attempts_to_pass,
            "tokens_out": tokens_out, "attempts": attempts_to_pass}


def test_gen_metrics_shapes_and_censoring():
    cells = [
        _cell("t01", True, True, 1, 40),
        _cell("t01", False, True, 3, 90),
        _cell("t02", False, False, 5, 200),  # never green: sentinel 5
        _cell("t02", False, False, 5, 210),
    ]
    m = gen_metrics(cells)
    assert m["n"] == 4
    assert m["pass1"] == 0.25
    assert m["pass10_verifier"] == 0.5      # t01 green, t02 never
    assert m["tokens_to_green_mean"] == 65.0  # mean(40, 90) — censored excluded
    assert m["iters_to_green_mean"] == 2.0
    assert m["censored_sessions"] == 2


def test_gen_metrics_all_censored_is_none_not_zero():
    cells = [_cell("t01", False, False, 5, 100)]
    m = gen_metrics(cells)
    assert m["tokens_to_green_mean"] is None
    assert m["iters_to_green_mean"] is None
    assert m["censored_sessions"] == 1


def test_gen_metrics_pass10_uses_final_passed_not_first_passed():
    # The Step-2 fixture's t01 row happens to have first_passed True on the
    # SAME row that carries final_passed True, so a mutant that counts
    # `first_passed` there gives the identical 0.5 -- it does not
    # distinguish the two fields. Here t01 is verified green only on a
    # later attempt (first_passed False, final_passed True): a
    # first_passed-based count must score it 0/2, the real pass10_verifier
    # (which asks "did this task EVER go green") must score it 1/2.
    cells = [
        _cell("t01", False, True, 3, 80),
        _cell("t02", False, False, 5, 100),
    ]
    m = gen_metrics(cells)
    assert m["pass10_verifier"] == 0.5


def test_paired_pass1_hand_computed():
    # t01/t02 alone give two IDENTICAL diffs (0.5, 0.5) -- variance is zero
    # under either a sample (n-1) or population (n) denominator, so that
    # pair alone cannot distinguish the two and would let a population-SD
    # mutation of `se` slip through. t03 (diff 1.0) breaks the symmetry:
    # sample SE = 33.3, population-denominator SE = 47.1 (hand-verified).
    a = [_cell("t01", True, True), _cell("t01", True, True),
         _cell("t02", False, False, 5), _cell("t02", True, True),
         _cell("t03", True, True)]
    b = [_cell("t01", False, False, 5), _cell("t01", True, True),
         _cell("t02", False, False, 5), _cell("t02", False, False, 5),
         _cell("t03", False, False, 5)]
    r = paired_pass1(a, b)
    # per-task rates: a={t01:1.0,t02:0.5,t03:1.0} b={t01:0.5,t02:0.0,t03:0.0}
    # diffs 0.5, 0.5, 1.0; delta=2/3=66.7pp; sample SE -> 2*SE=33.3pp
    assert r["delta_pp"] == 66.7
    assert r["two_se_pp"] == 33.3
    assert r["n_tasks"] == 3


def test_unpaired_pass1_hand_computed():
    a = [_cell("t01", True, True)] * 3 + [_cell("t01", False, False, 5)]
    b = [_cell("t01", False, False, 5)] * 4
    r = unpaired_pass1(a, b)
    assert r["a"] == 0.75 and r["b"] == 0.0
    assert r["delta_pp"] == 75.0
    assert r["two_se_pp"] == pytest.approx(2 * (0.75 * 0.25 / 4) ** 0.5 * 100, abs=0.1)


def test_require_complete_refuses_and_names_missing(tmp_path):
    for arm in ARM_NAMES[:-1]:
        d = tmp_path / arm
        d.mkdir()
        (d / ".DONE").write_text("")
    with pytest.raises(ReportError, match=ARM_NAMES[-1]):
        require_complete(tmp_path)
    d = tmp_path / ARM_NAMES[-1]
    d.mkdir()
    (d / ".DONE").write_text("")
    require_complete(tmp_path)  # now silent


def test_load_cells_reads_all_seed_runs(tmp_path):
    arm = tmp_path / "base-ox-7"
    for seed in (1, 2):
        run = arm / f"gen-s{seed}"
        run.mkdir(parents=True)
        (run / "cells.jsonl").write_text(
            json.dumps(_cell("t01", True, True)) + "\n", encoding="utf-8"
        )
    assert len(load_cells(arm)) == 2


def _probe_row(arm, strict):
    return {"arm": arm, "strict": strict, "lenient": strict, "codes": []}


def _write_probe_cell(probes_root, lang, seed, strict_flags):
    cell = Path(probes_root) / f"{lang}-s{seed}"
    cell.mkdir(parents=True, exist_ok=True)
    (cell / "probe_results.jsonl").write_text(
        "\n".join(json.dumps(_probe_row(lang, s)) for s in strict_flags) + "\n",
        encoding="utf-8",
    )


def test_strict_repair_rate_pools_seeds_via_probe_summarize(tmp_path):
    # 2 cells (2 seeds), one language-arm: reuses eval.probe.summarize
    # rather than re-deriving strict/n from raw rows.
    _write_probe_cell(tmp_path, "oxide", 1, [True, True, False])
    _write_probe_cell(tmp_path, "oxide", 2, [True, False])
    r = strict_repair_rate(tmp_path)
    assert r["n"] == 5
    assert r["rate"] == pytest.approx(3 / 5)


def _write_gen_cell(root, arm_name, seed=1, rows=None):
    run = root / arm_name / f"gen-s{seed}"
    run.mkdir(parents=True, exist_ok=True)  # exist_ok: tests override one arm's default
    if rows is None:
        rows = [_cell("t1", True, True), _cell("t2", False, False, 5)]
    (run / "cells.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )


def test_build_report_repair_primaries_and_headline_hand_computed(tmp_path):
    root = tmp_path
    lang_for = {a: ("oxide" if "-ox-" in a else "rust") for a in ARM_NAMES}
    for arm in ARM_NAMES:
        (root / arm).mkdir()
        (root / arm / ".DONE").write_text("")
        _write_gen_cell(root, arm)
        # neutral 5/10 filler so every arm scores without erroring; the
        # cases under test are overridden below
        _write_probe_cell(root / arm / "probes", lang_for[arm], 1, [True] * 5 + [False] * 5)

    _write_probe_cell(root / "tune-ox-1.5" / "probes", "oxide", 1, [True] * 8 + [False] * 2)  # 0.8/10
    _write_probe_cell(root / "tune-rs-1.5" / "probes", "rust", 1, [True] * 2 + [False] * 8)   # 0.2/10
    _write_probe_cell(root / "tune-ox-7" / "probes", "oxide", 1, [True] * 7 + [False] * 3)    # 0.7/10
    _write_probe_cell(root / "tune-rs-7" / "probes", "rust", 1, [True] * 4 + [False] * 6)     # 0.4/10
    _write_probe_cell(root / "base-rs-14" / "probes", "rust", 1, [True] * 3 + [False] * 7)    # 0.3/10

    report = build_report(root)

    # hand: 0.8 vs 0.2 -> delta 60.0, 2SE = 2*sqrt(.16/10+.16/10)*100 = 35.8
    assert report["primaries"]["1.5"]["repair"] == {
        "tune_ox": 0.8, "tune_rs": 0.2, "delta_pp": 60.0, "two_se_pp": 35.8,
    }
    # hand: 0.7 vs 0.4 -> delta 30.0, 2SE = 2*sqrt(.021+.024)*100 = 42.4
    assert report["primaries"]["7"]["repair"] == {
        "tune_ox": 0.7, "tune_rs": 0.4, "delta_pp": 30.0, "two_se_pp": 42.4,
    }
    # hand: 0.5 vs 0.5 (both filler) -> delta 0.0, 2SE = 2*sqrt(.025+.025)*100 = 44.7
    assert report["primaries"]["14"]["repair"] == {
        "tune_ox": 0.5, "tune_rs": 0.5, "delta_pp": 0.0, "two_se_pp": 44.7,
    }
    # headline: tune-ox-7 (0.7/10) vs base-rs-14 (0.3/10), generic a/b keys
    # -- base-rs-14 is not "tune_rs", so it must not be labelled that way.
    assert report["headline"]["repair"] == {
        "a": 0.7, "b": 0.3, "delta_pp": 40.0, "two_se_pp": 41.0,
    }

    # gen wiring: build_report's paired delta must equal calling
    # paired_pass1 directly on the same on-disk cells (checks wiring, not
    # the arithmetic, which test_paired_pass1_hand_computed already owns).
    for s in SIZES:
        expected = paired_pass1(
            load_cells(root / f"tune-ox-{s}"), load_cells(root / f"tune-rs-{s}")
        )
        assert report["primaries"][s]["gen"] == expected


def _filtered_probes_root(tmp_path, real_root, lang):
    """A tmp root holding only `lang`'s cells from a real committed
    campaign, symlinked in (never copied/modified) -- `strict_repair_rate`
    refuses a probes_root that mixes more than one language-arm, and a
    real campaign directory like `ownership-probe-deepseek/` holds all
    three at once."""
    filtered = tmp_path / lang
    filtered.mkdir()
    for cell in sorted(real_root.glob(f"{lang}-s*")):
        (filtered / cell.name).symlink_to(cell.resolve(), target_is_directory=True)
    return filtered


def test_acceptance_ownership_probe_deepseek_strict_rates(tmp_path):
    """`eval/results/ownership-probe-deepseek/REPORT.md` states the raw
    counts directly (lines ~109-111): rust 164/200 = 82.0%,
    oxide 43/200 = 21.5%, explicit 15/200 = 7.5%. This is the one
    committed campaign laid out in the `<arm>-s<seed>/probe_results.jsonl`
    layout `strict_repair_rate` consumes (`ownership-probe-deepseek` is
    for DeepSeek-Coder-V2-Lite, not qwen -- see the report's STOP note on
    why no committed layout can pin qwen's published 73.0/14.0 the same
    way)."""
    real_root = Path("eval/results/ownership-probe-deepseek")
    expected = {
        "oxide": {"rate": 0.215, "n": 200},
        "explicit": {"rate": 0.075, "n": 200},
        "rust": {"rate": 0.82, "n": 200},
    }
    for lang, exp in expected.items():
        r = strict_repair_rate(_filtered_probes_root(tmp_path, real_root, lang))
        assert r == exp


def test_build_report_efficiency_ratio_and_none_propagation(tmp_path):
    root = tmp_path
    lang_for = {a: ("oxide" if "-ox-" in a else "rust") for a in ARM_NAMES}
    for arm in ARM_NAMES:
        (root / arm).mkdir()
        (root / arm / ".DONE").write_text("")
        _write_gen_cell(root, arm)  # default: t1 green @ tokens_out=50, t2 censored
        _write_probe_cell(root / arm / "probes", lang_for[arm], 1, [True] * 5 + [False] * 5)

    # size "1.5": both sides green with distinct token means -> hand ratio
    _write_gen_cell(root, "tune-ox-1.5",
                     rows=[_cell("t1", True, True, 1, 80), _cell("t2", False, False, 5)])
    _write_gen_cell(root, "tune-rs-1.5",
                     rows=[_cell("t1", True, True, 1, 40), _cell("t2", False, False, 5)])

    # size "7": tune-ox-7 never goes green (fully censored) -> mean is None,
    # so the ratio must be None even though tune-rs-7's mean is a real number.
    _write_gen_cell(root, "tune-ox-7",
                     rows=[_cell("t1", False, False, 5, 999), _cell("t2", False, False, 5, 999)])

    report = build_report(root)

    # hand: 80.0 / 40.0 = 2.0
    assert report["efficiency"]["1.5"]["gen_tokens_to_green_ratio"] == pytest.approx(2.0)
    # None-propagation: tune-ox-7 censored -> ratio None, not 0 and not a number
    assert report["efficiency"]["7"]["gen_tokens_to_green_ratio"] is None
    # size "14" untouched: both sides default to 50.0 -> ratio 1.0 (sanity)
    assert report["efficiency"]["14"]["gen_tokens_to_green_ratio"] == pytest.approx(1.0)


def test_acceptance_v03_closing_baseline_qwen():
    root = Path("eval/results/v03-closing-baseline")
    runs = sorted(root.glob("*qwen*"))
    assert runs, "discover the real dir naming with ls and pin it here"
    cells = []
    for run in runs:
        cells += [json.loads(l) for l in
                  (run / "cells.jsonl").read_text(encoding="utf-8").splitlines()]
    oxide = [c for c in cells if c["arm"] == "oxide"]
    rust = [c for c in cells if c["arm"] == "rust"]
    assert gen_metrics(oxide)["pass1"] == pytest.approx(0.305, abs=1e-9)
    assert gen_metrics(rust)["pass1"] == pytest.approx(0.565, abs=1e-9)
