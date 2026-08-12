"""Tests for the training-corpus module and its contamination guard.

The guard is what protects the v03c comparison. If any t01-t20 content
reaches the training corpus, a model fine-tuned on it and evaluated on
t01-t20 posts a gain whether or not Black Oxide is easier to learn than
Rust -- which is the entire question the fine-tune track exists to ask.
So these tests are written to survive mutation, not merely to pass:
see the boundary pair at the bottom, which pins NGRAM_WORDS from both
sides.
"""

import json

import pytest

from eval import train_corpus as tc

EVAL_T01_OXIDE = (tc.SOLUTIONS_ROOT / "oxide" / "t01.ox").read_text(encoding="utf-8")

# t01's prompt, verbatim. Exactly twelve words, which is why it is the
# fixture for the "at threshold" case.
T01_PROMPT = "Print the sum of the squares of the integers 0 through 9."


def test_normalize_source_ignores_trailing_space_and_blank_lines():
    a = tc.normalize_source("fn main() {\n\n    print(1)   \n}\n")
    b = tc.normalize_source("fn main() {\n    print(1)\n}")
    assert a == b


def test_normalize_source_preserves_leading_indentation():
    """Indentation is real program structure; normalising it away would
    collapse distinct programs onto each other and over-report matches."""
    assert tc.normalize_source("fn main() {\n    print(1)\n}") != tc.normalize_source(
        "fn main() {\nprint(1)\n}"
    )


def test_clean_corpus_reports_no_contamination():
    tasks = {"n001": {"id": "n001", "prompt": "Count how many vowels appear in a fixed word."}}
    programs = {"n001": "fn main() {\n    print(3)\n}\n"}
    assert tc.contamination_report(tasks, programs) == ()


def test_program_identical_to_an_eval_solution_is_flagged():
    tasks = {"n001": {"id": "n001", "prompt": "Something entirely unrelated goes here."}}
    found = tc.contamination_report(tasks, {"n001": EVAL_T01_OXIDE})
    assert [c.kind for c in found] == ["solution"]
    assert found[0].eval_id == "t01"


def test_reformatted_eval_solution_is_still_flagged():
    """The guard must survive cosmetic edits, or it guards nothing.

    A model that reproduces an eval solution will rarely reproduce its
    whitespace exactly, so an exact-bytes guard would miss the case it
    exists for.
    """
    reformatted = "\n\n".join(line + "   " for line in EVAL_T01_OXIDE.split("\n"))
    assert reformatted != EVAL_T01_OXIDE
    tasks = {"n001": {"id": "n001", "prompt": "Something entirely unrelated goes here."}}
    found = tc.contamination_report(tasks, {"n001": reformatted})
    assert [c.kind for c in found] == ["solution"]
    assert found[0].eval_id == "t01"


def test_ngram_threshold_is_twelve_words():
    """The canary, kept in ONE place.

    The two tests below deliberately do not assert the threshold value.
    If they did, any change to NGRAM_WORDS would trip that assertion
    before their behavioural assertion ran -- and a behavioural test that
    can only ever fail on its own preamble is pinning nothing. Here the
    value is pinned once, and there the behaviour is pinned independently.
    """
    assert tc.NGRAM_WORDS == 12
    assert len(T01_PROMPT.split()) == 12


def test_prompt_sharing_a_full_span_with_an_eval_task_is_flagged():
    """Behavioural: an eval prompt copied verbatim must be caught.

    Dies if the threshold rises above twelve, because t01's prompt is
    twelve words long and would then contain no comparable span at all.
    """
    found = tc.contamination_report({"n001": {"id": "n001", "prompt": T01_PROMPT}}, {})
    assert [c.kind for c in found] == ["prompt"]
    assert found[0].eval_id == "t01"


def test_prompt_sharing_eleven_words_is_not_flagged():
    """Behavioural: pins the other side of the threshold.

    This fixture is deliberately twelve words long, so it DOES have a
    twelve-gram to compare -- it just is not t01's. A shorter prompt
    would pass vacuously, by having no n-grams at all, and would keep
    passing if the threshold were moved to 2. Dies if the threshold drops
    to eleven, because the shared span then becomes detectable.
    """
    prompt = "Compute the sum of the squares of the integers 0 through 9."
    # Heavy vocabulary overlap -- the two prompts differ in one word out of
    # twelve -- and yet no shared full span, which is exactly the case the
    # threshold has to get right.
    shared = set(prompt.split()) & set(T01_PROMPT.split())
    assert len(shared) == 8
    assert tc.contamination_report({"n001": {"id": "n001", "prompt": prompt}}, {}) == ()


def test_committed_training_corpus_is_clean():
    """Runs against the real corpus once it exists; skips before Task 4."""
    if not tc.TRAIN_TASKS_PATH.exists():
        pytest.skip("training corpus not authored yet")
    assert tc.contamination_report(tc.load_train_tasks(), tc.load_train_programs()) == ()


# ----------------------------------------------------------- Stage A gate

_OX_PRINTS_3 = "fn main() {\n    print(3)\n}\n"
_RS_PRINTS_3 = 'fn main() {\n    println!("3");\n}\n'


def _pair(tmp_path, oxide_src: str, rust_src: str):
    ox = tmp_path / "oxide.ox"
    rs = tmp_path / "rust.rs"
    ox.write_text(oxide_src, encoding="utf-8")
    rs.write_text(rust_src, encoding="utf-8")
    return ox, rs


def test_validate_pair_accepts_agreeing_references(tmp_path):
    ox, rs = _pair(tmp_path, _OX_PRINTS_3, _RS_PRINTS_3)
    result = tc.validate_pair({"id": "n001", "expected_stdout": "3\n"}, ox, rs)
    assert result["ok"] is True
    assert result["reasons"] == ()


def test_validate_pair_rejects_rust_containing_the_oxide_prefix(tmp_path):
    """Transpiler output as Rust training data makes the control a
    strawman, so the Black Oxide advantage it would produce is an
    artifact. This Rust program is otherwise correct -- it compiles and
    prints the expected output -- so the prefix is the ONLY reason it is
    rejected, which is what the single-reason assertion pins.
    """
    rust = 'fn __oxide_helper() {}\nfn main() {\n    println!("3");\n}\n'
    ox, rs = _pair(tmp_path, _OX_PRINTS_3, rust)
    result = tc.validate_pair({"id": "n001", "expected_stdout": "3\n"}, ox, rs)
    assert result["ok"] is False
    assert len(result["reasons"]) == 1
    assert "__oxide_" in result["reasons"][0]


def test_validate_pair_rejects_arms_that_disagree(tmp_path):
    """Both arms must match expected_stdout, which also proves they agree
    with each other -- a task whose two references implement different
    things would otherwise enter the corpus as a matched pair."""
    ox, rs = _pair(tmp_path, _OX_PRINTS_3, 'fn main() {\n    println!("4");\n}\n')
    result = tc.validate_pair({"id": "n001", "expected_stdout": "3\n"}, ox, rs)
    assert result["ok"] is False
    assert any("rust" in r for r in result["reasons"])


def test_validate_pair_rejects_an_oxide_reference_that_does_not_compile(tmp_path):
    ox, rs = _pair(tmp_path, "fn main() {\n    print(nope)\n}\n", _RS_PRINTS_3)
    result = tc.validate_pair({"id": "n001", "expected_stdout": "3\n"}, ox, rs)
    assert result["ok"] is False
    assert any("oxide" in r for r in result["reasons"])


# ------------------------------------------------- run-length derivation

def test_sessions_per_run_derives_from_an_explicit_corpus():
    """A 40-task training corpus is 120 sessions, not the eval corpus's 60.

    Hardcoding 60 would make is_complete judge every amplification run
    complete after 60 of its 120 cells, silently truncating the run and
    reporting it as finished.
    """
    from eval import driver

    assert driver.sessions_per_run(None) == driver.SESSIONS_PER_RUN
    if not tc.TRAIN_TASKS_PATH.exists():
        pytest.skip("training corpus not authored yet")
    n_tasks = len(tc.load_train_tasks())
    assert driver.sessions_per_run(tc.TRAIN_TASKS_PATH) == n_tasks * 3
    assert driver.sessions_per_run(tc.TRAIN_TASKS_PATH) != driver.SESSIONS_PER_RUN


def test_is_complete_honours_the_expected_count(tmp_path):
    from eval import driver

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "cells.jsonl").write_text("{}\n" * 60, encoding="utf-8")
    assert driver.is_complete(run_dir, 60) is True
    assert driver.is_complete(run_dir, 120) is False


# ------------------------------------------------ amplification collector

def _write_triples(root, run, records):
    d = root / run
    d.mkdir(parents=True, exist_ok=True)
    (d / "triples.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def test_collect_verified_keeps_only_passing_programs(tmp_path):
    _write_triples(tmp_path, "r1", [
        {"task": "n001", "arm": "oxide", "attempt": 1, "passed": True,
         "code": "fn main() {\n    print(1)\n}\n"},
        {"task": "n001", "arm": "oxide", "attempt": 2, "passed": False,
         "code": "fn main() {\n    print(2)\n}\n"},
    ])
    got = tc.collect_verified(tmp_path)
    assert set(got) == {("n001", "oxide")}
    assert got[("n001", "oxide")] == {"fn main() {\n    print(1)\n}"}


def test_collect_verified_deduplicates_on_normalised_source(tmp_path):
    """Two passing programs differing only in trailing whitespace are one
    program; counting them twice would inflate the yield endpoint."""
    _write_triples(tmp_path, "r1", [
        {"task": "n001", "arm": "oxide", "attempt": 1, "passed": True,
         "code": "fn main() {\n    print(1)\n}\n"},
        {"task": "n001", "arm": "oxide", "attempt": 1, "passed": True,
         "code": "fn main() {\n    print(1)   \n}\n\n"},
    ])
    assert len(tc.collect_verified(tmp_path)[("n001", "oxide")]) == 1


def test_collect_verified_separates_arms_and_tasks(tmp_path):
    _write_triples(tmp_path, "r1", [
        {"task": "n001", "arm": "oxide", "attempt": 1, "passed": True, "code": "a"},
        {"task": "n001", "arm": "rust", "attempt": 1, "passed": True, "code": "a"},
        {"task": "n002", "arm": "oxide", "attempt": 1, "passed": True, "code": "a"},
    ])
    got = tc.collect_verified(tmp_path)
    assert set(got) == {("n001", "oxide"), ("n001", "rust"), ("n002", "oxide")}


def test_collect_verified_excludes_the_explicit_arm_by_default(tmp_path):
    """explicit is the eval's control dialect, not a training target."""
    _write_triples(tmp_path, "r1", [
        {"task": "n001", "arm": "explicit", "attempt": 1, "passed": True, "code": "a"},
        {"task": "n001", "arm": "oxide", "attempt": 1, "passed": True, "code": "b"},
    ])
    assert set(tc.collect_verified(tmp_path)) == {("n001", "oxide")}


def test_collect_verified_spans_run_directories(tmp_path):
    """One seed is one run dir; the corpus is the union across all of them."""
    _write_triples(tmp_path, "r1", [
        {"task": "n001", "arm": "oxide", "attempt": 1, "passed": True, "code": "a"}])
    _write_triples(tmp_path, "r2", [
        {"task": "n001", "arm": "oxide", "attempt": 1, "passed": True, "code": "b"}])
    assert len(tc.collect_verified(tmp_path)[("n001", "oxide")]) == 2


def test_collect_verified_on_a_missing_root_is_empty(tmp_path):
    assert tc.collect_verified(tmp_path / "nope") == {}


# ------------------------------ analysis-path run-length (g0_report/rollup)

def _cells(run_dir, n):
    """n cell records shaped like a real one, cycling the three arms."""
    run_dir.mkdir(parents=True, exist_ok=True)
    arms = ("oxide", "explicit", "rust")
    rows = [
        {"arm": arms[i % 3], "task": f"t{i // 3 + 1:02d}", "attempts": 1,
         "attempts_to_pass": 1, "context_exhausted": False,
         "contract_compliant": [True], "final_passed": True,
         "first_compiled": True, "first_passed": True, "ms": 10,
         "tokens_in": 1, "tokens_out": 1, "truncated": [False]}
        for i in range(n)
    ]
    (run_dir / "cells.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_missing_runs_uses_the_corpus_run_length(tmp_path):
    """A 40-task run is 120 cells. Judged against the eval corpus's pinned
    60, a half-finished amplification run reads as complete and g0_report
    would report a partial measurement as a finished one -- the exact
    failure missing_runs exists to prevent.
    """
    from eval import g0_report
    from eval.driver import build_run_id

    run_id = build_run_id("qwen7b", 0, 1, prefix="ampq")
    _cells(tmp_path / run_id, 60)

    # Against the eval corpus's length this run is complete...
    assert g0_report.missing_runs(tmp_path, ["qwen7b"], [1], "ampq") == []
    # ...but against the 40-task corpus it is only half done.
    assert g0_report.missing_runs(
        tmp_path, ["qwen7b"], [1], "ampq", tasks_path=tc.TRAIN_TASKS_PATH
    ) == [run_id]

    _cells(tmp_path / run_id, 120)
    assert g0_report.missing_runs(
        tmp_path, ["qwen7b"], [1], "ampq", tasks_path=tc.TRAIN_TASKS_PATH
    ) == []


def test_rollup_aggregate_uses_the_corpus_run_length(tmp_path):
    """Same latent bug as missing_runs, in the other analysis entry point."""
    from eval import rollup
    from eval.driver import build_run_id

    run_id = build_run_id("qwen7b", 0, 1, prefix="ampq")
    _cells(tmp_path / run_id, 60)
    common = dict(slugs=["qwen7b"], shot_counts=[0], seeds=[1],
                  partial=True, prefix="ampq")
    assert rollup.aggregate(tmp_path, **common)["missing"] == []
    assert rollup.aggregate(
        tmp_path, tasks_path=tc.TRAIN_TASKS_PATH, **common
    )["missing"] == [run_id]
