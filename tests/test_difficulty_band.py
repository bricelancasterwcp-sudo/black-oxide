"""The two-arm, per-class difficulty band (eval/difficulty_band.py).

Origin: pilot REPORT recommendation 3. The pre-registered difficulty
band checked the oxide arm only, whole-corpus only — and passed in all
three families while (a) codegemma's RUST first-pass moved −10.5pp
unbanded, and (b) the vector and string classes drifted more than 20pp
inside a passing whole-corpus number. This instrument bands both arms
at whole-corpus and per-class granularity.

The real-data tests at the bottom are the acceptance criteria: run the
checker over the committed pilot (`train-pilot-amp`) against the
committed reference (`v03-closing-baseline`) and it must catch exactly
what the REPORT caught by hand — and pass exactly what really held.
"""

from pathlib import Path

from eval.difficulty_band import (
    CLASS_BAND_PP,
    WHOLE_BAND_PP,
    band_check,
    first_pass_rates,
    load_family_cells,
    main,
    task_classes,
)

REPO = Path(__file__).resolve().parent.parent
V03C = REPO / "eval" / "results" / "v03-closing-baseline"
PILOT = REPO / "eval" / "results" / "train-pilot-amp"
EVAL_TASKS = REPO / "eval" / "tasks.jsonl"
PILOT_TASKS = PILOT / "tasks-pilot.jsonl"


def cell(task: str, arm: str, passed: bool) -> dict:
    return {"task": task, "arm": arm, "first_passed": passed}


CLASSES = {"a1": "arithmetic/loops", "a2": "arithmetic/loops", "v1": "vectors"}


# --- first_pass_rates -------------------------------------------------------

def test_rates_split_by_family_arm_and_class():
    cells = {"qwen": [cell("a1", "oxide", True), cell("a2", "oxide", False),
                      cell("v1", "oxide", True), cell("a1", "rust", True)]}
    rates = first_pass_rates(cells, CLASSES)
    assert rates[("qwen", "oxide")].overall == (2, 3)
    assert rates[("qwen", "oxide")].per_class["arithmetic/loops"] == (1, 2)
    assert rates[("qwen", "oxide")].per_class["vectors"] == (1, 1)
    assert rates[("qwen", "rust")].overall == (1, 1)


def test_rates_ignore_arms_outside_oxide_and_rust():
    cells = {"qwen": [cell("a1", "explicit", True), cell("a1", "oxide", False)]}
    rates = first_pass_rates(cells, CLASSES)
    assert ("qwen", "explicit") not in rates
    assert rates[("qwen", "oxide")].overall == (0, 1)


# --- band_check -------------------------------------------------------------

def _rates(family_cells):
    return first_pass_rates(family_cells, CLASSES)


def test_identical_rates_pass_everywhere():
    cells = {"qwen": [cell("a1", "oxide", True), cell("v1", "oxide", False),
                      cell("a1", "rust", True), cell("v1", "rust", True)]}
    result = band_check(_rates(cells), _rates(cells))
    assert result.passed
    metrics = {v.metric for v in result.verdicts}
    assert "qwen/oxide/overall" in metrics
    assert "qwen/rust/overall" in metrics
    assert "qwen/oxide/class:vectors" in metrics


def test_rust_arm_drift_fails_even_when_oxide_holds():
    # The codegemma omission, in miniature: oxide identical, rust moved.
    ref = {"f": [cell("a1", "oxide", True), cell("a2", "oxide", False)]
                + [cell("a1", "rust", True)] * 10}
    cand = {"f": [cell("a1", "oxide", True), cell("a2", "oxide", False)]
                 + [cell("a1", "rust", False)] * 10}
    result = band_check(first_pass_rates(cand, CLASSES),
                        first_pass_rates(ref, CLASSES))
    assert not result.passed
    bad = {v.metric for v in result.verdicts if not v.passed}
    assert "f/rust/overall" in bad
    assert "f/oxide/overall" not in bad


def test_class_drift_fails_inside_a_passing_whole_corpus():
    # The REPORT's second finding, in miniature: equal overall rates,
    # opposite per-class drifts that cancel.
    ref = {"f": [cell("a1", "oxide", True)] * 10 + [cell("a2", "oxide", True)] * 0
                + [cell("v1", "oxide", False)] * 10}
    cand = {"f": [cell("a1", "oxide", False)] * 10
                 + [cell("v1", "oxide", True)] * 10}
    result = band_check(first_pass_rates(cand, CLASSES),
                        first_pass_rates(ref, CLASSES))
    overall = [v for v in result.verdicts if v.metric == "f/oxide/overall"][0]
    assert overall.passed
    bad = {v.metric for v in result.verdicts if not v.passed}
    assert "f/oxide/class:vectors" in bad


def test_missing_candidate_family_arm_is_loud():
    ref = {"f": [cell("a1", "oxide", True), cell("a1", "rust", True)]}
    cand = {"f": [cell("a1", "oxide", True)]}
    try:
        band_check(first_pass_rates(cand, CLASSES),
                    first_pass_rates(ref, CLASSES))
    except ValueError as e:
        assert "rust" in str(e)
    else:
        raise AssertionError("missing (family, arm) must raise, not pass")


def test_reference_class_missing_from_candidate_is_loud():
    ref = {"f": [cell("a1", "oxide", True), cell("v1", "oxide", True)]}
    cand = {"f": [cell("a1", "oxide", True)]}
    try:
        band_check(first_pass_rates(cand, CLASSES),
                    first_pass_rates(ref, CLASSES))
    except ValueError as e:
        assert "vectors" in str(e)
    else:
        raise AssertionError("missing class must raise, not pass")


# --- acceptance: the committed pilot vs the committed reference -------------

def _real_result():
    ref = first_pass_rates(load_family_cells(V03C), task_classes(EVAL_TASKS))
    cand = first_pass_rates(load_family_cells(PILOT), task_classes(PILOT_TASKS))
    return band_check(cand, ref)


def test_pilot_oxide_whole_corpus_passes_as_the_old_endpoint_did():
    result = _real_result()
    for fam in ("qwen", "codegemma", "granite"):
        v = [x for x in result.verdicts if x.metric == f"{fam}/oxide/overall"][0]
        assert v.passed, (v.metric, v.measured, v.reference)


def test_pilot_rust_codegemma_fails_the_band_the_report_said_was_missing():
    result = _real_result()
    v = [x for x in result.verdicts if x.metric == "codegemma/rust/overall"][0]
    assert not v.passed
    assert v.measured < v.band_lo  # it moved DOWN, ~-10.5pp


def test_pilot_vector_and_string_classes_fail_per_class_bands():
    result = _real_result()
    bad = {v.metric for v in result.verdicts if not v.passed}
    assert "qwen/oxide/class:vectors" in bad
    assert "qwen/oxide/class:strings" in bad
    assert "codegemma/oxide/class:strings" in bad
    # arithmetic matched within 3.6pp in every family - must NOT flag.
    for fam in ("qwen", "codegemma", "granite"):
        assert f"{fam}/oxide/class:arithmetic/loops" not in bad
    # Drifts inside the derived ±20pp noise tolerance must PASS — the
    # class band is wider than the whole-corpus band on purpose (worst
    # class is 40 attempts on the v03c side; 2 SE ≈ 17pp). These two sit
    # at +14pp on the committed data and pin that width: a narrower band
    # would flag noise as drift.
    assert "codegemma/oxide/class:vectors" not in bad
    assert "granite/oxide/class:strings" not in bad
    assert not result.passed


# --- CLI --------------------------------------------------------------------

def test_cli_exit_codes(capsys):
    argv_common = ["--reference-root", str(V03C),
                   "--reference-tasks", str(EVAL_TASKS)]
    assert main([str(V03C), "--candidate-tasks", str(EVAL_TASKS)]
                + argv_common) == 0
    assert main([str(PILOT), "--candidate-tasks", str(PILOT_TASKS)]
                + argv_common) == 1
    out = capsys.readouterr().out
    assert "codegemma/rust/overall" in out


def test_bands_are_the_registered_widths():
    assert WHOLE_BAND_PP == 0.10
    assert CLASS_BAND_PP == 0.20
