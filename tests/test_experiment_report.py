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
    paired_strict_repair,
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


def _probe_row(arm, strict, defect):
    return {"arm": arm, "strict": strict, "lenient": strict, "codes": [],
            "defect": defect}


def _write_probe_cell(probes_root, lang, seed, strict_flags):
    # `defect` defaults to the row's position ("class0", "class1", ...):
    # harmless for `strict_repair_rate`/`summarize` (neither reads it),
    # and gives `paired_strict_repair` a real, position-matched class key
    # to pair on when a fixture writes the SAME strict_flags length for
    # both sides of a comparison.
    cell = Path(probes_root) / f"{lang}-s{seed}"
    cell.mkdir(parents=True, exist_ok=True)
    (cell / "probe_results.jsonl").write_text(
        "\n".join(
            json.dumps(_probe_row(lang, s, f"class{i}"))
            for i, s in enumerate(strict_flags)
        ) + "\n",
        encoding="utf-8",
    )


def _write_probe_cell_classed(probes_root, lang, seed, defect_flags):
    """Like `_write_probe_cell`, but the caller picks the (defect, strict)
    pairs and their order explicitly -- used where the row-insertion
    order into `_class_rates`'s dict must be controlled (proving pairing
    is by `defect` key, not by position)."""
    cell = Path(probes_root) / f"{lang}-s{seed}"
    cell.mkdir(parents=True, exist_ok=True)
    rows = [_probe_row(lang, strict, defect) for defect, strict in defect_flags]
    (cell / "probe_results.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8",
    )


def test_strict_repair_rate_pools_seeds_via_probe_summarize(tmp_path):
    # 2 cells (2 seeds), one language-arm: reuses eval.probe.summarize
    # rather than re-deriving strict/n from raw rows.
    _write_probe_cell(tmp_path, "oxide", 1, [True, True, False])
    _write_probe_cell(tmp_path, "oxide", 2, [True, False])
    r = strict_repair_rate(tmp_path)
    assert r["n"] == 5
    assert r["rate"] == pytest.approx(3 / 5)


def test_paired_strict_repair_hand_computed(tmp_path):
    # 3 shared defect classes, one seed-cell per side. Insertion order
    # into `_class_rates`'s per-side dict is DELIBERATELY reversed
    # between the two sides (a: d1,d2,d3 / b: d3,d2,d1), and the class
    # rates are chosen so a positional (insertion-order) zip gives a
    # DIFFERENT two_se_pp than matching by the `defect` key -- see the
    # hand computation below. The same values also give a non-symmetric
    # diff set, so a population-SD (n, not n-1) mutation in the shared
    # `_paired_rates` helper is caught too.
    a_root, b_root = tmp_path / "a", tmp_path / "b"
    _write_probe_cell_classed(a_root, "oxide", 1, [
        ("d1", True), ("d1", True), ("d1", True), ("d1", True), ("d1", True),
        ("d1", True), ("d1", True), ("d1", True), ("d1", True), ("d1", False),
        ("d2", True), ("d2", True), ("d2", True), ("d2", True), ("d2", True),
        ("d2", True), ("d2", False), ("d2", False), ("d2", False), ("d2", False),
        ("d3", True), ("d3", True), ("d3", False), ("d3", False), ("d3", False),
        ("d3", False), ("d3", False), ("d3", False), ("d3", False), ("d3", False),
    ])
    _write_probe_cell_classed(b_root, "rust", 1, [
        ("d3", True), ("d3", True), ("d3", True), ("d3", False), ("d3", False),
        ("d3", False), ("d3", False), ("d3", False), ("d3", False), ("d3", False),
        ("d2", True), ("d2", True), ("d2", True), ("d2", True), ("d2", True),
        ("d2", False), ("d2", False), ("d2", False), ("d2", False), ("d2", False),
        ("d1", True), ("d1", True), ("d1", True), ("d1", True), ("d1", False),
        ("d1", False), ("d1", False), ("d1", False), ("d1", False), ("d1", False),
    ])
    r = paired_strict_repair(a_root, b_root)
    # per-class rates: a={d1: 9/10=0.9, d2: 6/10=0.6, d3: 2/10=0.2}
    #                  b={d3: 3/10=0.3, d2: 5/10=0.5, d1: 4/10=0.4}
    # paired-by-KEY diffs (d1,d2,d3): 0.5, 0.1, -0.1 -> delta=16.7pp,
    # sample SE -> two_se=35.3pp (hand-verified; a positional zip using
    # each side's insertion order instead gives 46.7pp, a population-SD
    # denominator gives 28.8pp -- both wrong and distinguishable here).
    assert r["delta_pp"] == 16.7
    assert r["two_se_pp"] == 35.3
    assert r["n"] == 3


def test_paired_strict_repair_mismatched_classes_raises(tmp_path):
    a_root, b_root = tmp_path / "a", tmp_path / "b"
    _write_probe_cell_classed(a_root, "oxide", 1,
                               [("d1", True), ("d2", True)])
    _write_probe_cell_classed(b_root, "rust", 1,
                               [("d1", True), ("d3", False)])
    with pytest.raises(ReportError, match="identical defect-class sets"):
        paired_strict_repair(a_root, b_root)


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

    report = build_report(root, strict_shape=False)

    # `_write_probe_cell` tags row i's defect "classI" by position, so
    # tune-ox-{s}/tune-rs-{s} pairs of equal length share class0..class9
    # -- the paired (per-class) construction over one replicate per class
    # reduces to the plain per-arm rate for delta_pp (same as the old
    # unpaired numbers below), but two_se_pp is now the PAIRED sample-SE
    # over per-class diffs, not the two-binomials formula -- hand-verified
    # via the same {0,1}-diffs construction as test_paired_pass1_hand_computed.
    # hand: diffs [0,0,1,1,1,1,1,1,0,0] -> delta 60.0, sample 2SE = 32.7
    assert report["primaries"]["1.5"]["repair"] == {
        "delta_pp": 60.0, "two_se_pp": 32.7, "n": 10,
    }
    # hand: diffs [0,0,0,0,1,1,1,0,0,0] -> delta 30.0, sample 2SE = 30.6
    assert report["primaries"]["7"]["repair"] == {
        "delta_pp": 30.0, "two_se_pp": 30.6, "n": 10,
    }
    # hand: both sides identical filler -> all-zero diffs -> delta 0.0, 2SE 0.0
    assert report["primaries"]["14"]["repair"] == {
        "delta_pp": 0.0, "two_se_pp": 0.0, "n": 10,
    }
    # headline stays UNPAIRED (the spec's own choice, not an impossibility):
    # tune-ox-7 (0.7/10) vs base-rs-14 (0.3/10), generic a/b keys -- unchanged
    # by the primaries-side paired refactor.
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

    # repair wiring: same check, against `paired_strict_repair` directly.
    for s in SIZES:
        expected = paired_strict_repair(
            root / f"tune-ox-{s}" / "probes", root / f"tune-rs-{s}" / "probes"
        )
        assert report["primaries"][s]["repair"] == expected


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

    report = build_report(root, strict_shape=False)

    # hand: 80.0 / 40.0 = 2.0
    assert report["efficiency"]["1.5"]["gen_tokens_to_green_ratio"] == pytest.approx(2.0)
    # None-propagation: tune-ox-7 censored -> ratio None, not 0 and not a number
    assert report["efficiency"]["7"]["gen_tokens_to_green_ratio"] is None
    # size "14" untouched: both sides default to 50.0 -> ratio 1.0 (sanity)
    assert report["efficiency"]["14"]["gen_tokens_to_green_ratio"] == pytest.approx(1.0)


def test_build_report_strict_shape_names_bad_arm(tmp_path):
    """The real campaign shape is 20 tasks x 10 seeds = 200 cells per arm.
    `strict_shape=True` (the CLI's default) must refuse a short arm by
    name rather than silently scoring it as a smaller-n result. Every
    arm otherwise has a complete, scoreable shape (full 200-cell gen
    fixture and probe filler) so this test fails on the shape check
    specifically -- not on some unrelated missing-data error that would
    happen to also mention "base-ox-1.5" in its message and mask a
    disabled shape check."""
    root = tmp_path
    full_shape = [_cell(f"t{n:02d}", True, True) for _ in range(10) for n in range(1, 21)]
    lang_for = {a: ("oxide" if "-ox-" in a else "rust") for a in ARM_NAMES}
    for arm in ARM_NAMES:
        (root / arm).mkdir()
        (root / arm / ".DONE").write_text("")
        rows = full_shape[:-1] if arm == "base-ox-1.5" else full_shape
        _write_gen_cell(root, arm, rows=rows)
        _write_probe_cell(root / arm / "probes", lang_for[arm], 1, [True] * 5 + [False] * 5)
    with pytest.raises(ReportError, match="base-ox-1.5"):
        build_report(root)  # strict_shape defaults to True
    build_report(root, strict_shape=False)  # otherwise a fully valid report


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
