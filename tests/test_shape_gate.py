"""The pre-flight corpus-shape gate (eval/shape_gate.py).

Origin: eval/results/train-pilot-amp/REPORT.md — the 40-task pilot
corpus passed all four pre-registered endpoints while drifting
structurally from the eval (multi-line-output share 5% vs 65%), and the
drift was only discovered after 14 hours of GPU. The gate computes the
structural comparison in seconds, before authoring is accepted.

The two real-data tests at the bottom are the acceptance criteria from
the approved design: the gate must FAIL the known-drifted pilot corpus
and PASS the eval corpus against itself. If the pilot corpus ever
passes, the gate is wrong — not the corpus.
"""

import json
from pathlib import Path

from eval.shape_gate import (
    DEFAULT_BANDS,
    Bands,
    corpus_shape,
    gate,
    load_tasks,
    main,
    output_lines,
)

REPO = Path(__file__).resolve().parent.parent
EVAL_TASKS = REPO / "eval" / "tasks.jsonl"
TRAIN_TASKS = REPO / "eval" / "train" / "tasks.jsonl"


def task(stdout: str, prompt: str = "p" * 100, cls: str = "vectors") -> dict:
    return {"id": "x", "title": "t", "difficulty": "core", "class": cls,
            "prompt": prompt, "expected_stdout": stdout}


# --- output_lines -----------------------------------------------------------

def test_output_lines_counts_lines_not_newlines():
    # "4\n12\n" is TWO lines of output, not "two newlines plus empty".
    assert output_lines("4\n12\n") == 2
    assert output_lines("7\n") == 1
    assert output_lines("7") == 1          # missing trailing newline: still one line
    assert output_lines("") == 0
    assert output_lines("a\n\nb\n") == 3   # interior blank line is a line
    assert output_lines("\n\n") == 2       # two blank lines are two lines
    assert output_lines("\n") == 1         # one blank line is one line


# --- corpus_shape -----------------------------------------------------------

def test_shape_measures_share_mean_and_prompt_length():
    tasks = [task("1\n", prompt="a" * 50), task("a\nb\n", prompt="a" * 150),
             task("x\ny\nz\n", prompt="a" * 100)]
    s = corpus_shape(tasks)
    assert s.n == 3
    assert s.multi_line_share == 2 / 3
    assert s.mean_output_lines == 2.0
    assert s.prompt_chars_mean == 100.0


def test_shape_counts_class_shares():
    tasks = [task("1\n", cls="vectors"), task("1\n", cls="vectors"),
             task("1\n", cls="strings"), task("1\n", cls="arithmetic/loops")]
    s = corpus_shape(tasks)
    assert s.class_shares == {"vectors": 0.5, "strings": 0.25,
                              "arithmetic/loops": 0.25}


# --- gate -------------------------------------------------------------------

def test_gate_passes_a_corpus_against_itself():
    tasks = [task("1\n2\n"), task("1\n", cls="strings")]
    result = gate(corpus_shape(tasks), corpus_shape(tasks))
    assert result.passed
    assert all(v.passed for v in result.verdicts)


def test_gate_fails_multi_line_share_outside_band_and_names_it():
    ref = [task("1\n2\n") for _ in range(13)] + [task("1\n") for _ in range(7)]
    cand = [task("1\n") for _ in range(19)] + [task("1\n2\n")]
    result = gate(corpus_shape(cand), corpus_shape(ref))
    assert not result.passed
    bad = [v for v in result.verdicts if v.metric == "multi_line_share"]
    assert len(bad) == 1 and not bad[0].passed
    assert bad[0].measured == 0.05 and bad[0].reference == 0.65


def test_gate_fails_when_a_reference_class_is_absent():
    ref = [task("1\n", cls="vectors"), task("1\n", cls="strings")]
    cand = [task("1\n", cls="vectors"), task("1\n", cls="vectors")]
    result = gate(corpus_shape(cand), corpus_shape(ref))
    assert not result.passed
    bad = [v for v in result.verdicts if v.metric == "class_share:strings"]
    assert len(bad) == 1 and not bad[0].passed and bad[0].measured == 0.0


def test_gate_band_edges_are_inclusive():
    # Exactly AT the band edge passes; beyond it fails. Bands are
    # closed intervals — pinned here so <= cannot silently become <.
    ref = [task("1\n2\n"), task("1\n")]                       # share 0.5
    at_edge = [task("1\n2\n") for _ in range(6)] + [task("1\n") for _ in range(4)]
    result = gate(corpus_shape(at_edge), corpus_shape(ref),
                  bands=Bands(multi_line_share_pp=0.10, mean_output_lines=1.0,
                              prompt_chars_rel=0.25, class_share_pp=1.0))
    v = [v for v in result.verdicts if v.metric == "multi_line_share"][0]
    assert v.measured == 0.6 and v.passed


def test_gate_verdicts_carry_measured_reference_and_band():
    tasks = [task("1\n")]
    result = gate(corpus_shape(tasks), corpus_shape(tasks))
    for v in result.verdicts:
        assert v.metric
        assert v.band_lo <= v.measured <= v.band_hi, v.metric
        assert v.reference is not None


# --- the acceptance criteria (real data) ------------------------------------

def test_eval_corpus_passes_against_itself():
    shape = corpus_shape(load_tasks(EVAL_TASKS))
    assert shape.n == 20
    assert gate(shape, shape, bands=DEFAULT_BANDS).passed


def test_pilot_train_corpus_fails_the_gate():
    # The REPORT's finding, as a permanent regression test: the 40-task
    # pilot corpus is structurally drifted (multi-line share 5% vs 65%)
    # and the gate must refuse it.
    result = gate(corpus_shape(load_tasks(TRAIN_TASKS)),
                  corpus_shape(load_tasks(EVAL_TASKS)),
                  bands=DEFAULT_BANDS)
    assert not result.passed
    failing = {v.metric for v in result.verdicts if not v.passed}
    assert "multi_line_share" in failing


# --- CLI --------------------------------------------------------------------

def test_cli_exit_codes(capsys):
    assert main([str(EVAL_TASKS), "--reference", str(EVAL_TASKS)]) == 0
    assert main([str(TRAIN_TASKS), "--reference", str(EVAL_TASKS)]) == 1
    out = capsys.readouterr().out
    assert "multi_line_share" in out
