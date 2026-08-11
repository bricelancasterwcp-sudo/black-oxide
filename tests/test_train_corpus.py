"""Tests for the training-corpus module and its contamination guard.

The guard is what protects the v03c comparison. If any t01-t20 content
reaches the training corpus, a model fine-tuned on it and evaluated on
t01-t20 posts a gain whether or not Black Oxide is easier to learn than
Rust -- which is the entire question the fine-tune track exists to ask.
So these tests are written to survive mutation, not merely to pass:
see the boundary pair at the bottom, which pins NGRAM_WORDS from both
sides.
"""

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
