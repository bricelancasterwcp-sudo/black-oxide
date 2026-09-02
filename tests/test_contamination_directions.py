"""The contamination instrument's second direction: subject vs training corpus.

The first direction asks whether the benchmark leaked into the training
data. This one asks whether a task set was already in the corpus the
adapters were fine-tuned on -- and it is the one that binds a dynamic
wave, because a task the adapters were trained on measures recall rather
than the language.

Wave 8 ran this check by hand and said so
(eval/results/v04-wave8-large/REPORT.md). These tests are what make it
committed code: the real-data pins at the bottom would both pass against
an instrument that always returns nothing, so each is paired with a
planted duplicate that must be caught exactly once.
"""

import json
from pathlib import Path

import pytest

from eval import train_corpus as tc
from eval.cost_census import LARGE_SOURCE

# Deliberately unlike anything in either committed corpus, and 13 words
# long so it HAS twelve-grams to share. A shorter fixture would pass the
# prompt tests vacuously, by having no n-grams at all.
ALIEN_PROMPT = (
    "Zephyr quokka lanterns drift beyond the marmalade quorum while "
    "nineteen tessellated pangolins hum."
)
ALIEN_PROGRAM = "fn main() {\n    print(4919)\n}\n"

# Eval task t01's prompt, verbatim -- the fixture for "a prompt side that
# fell back to the default tasks file would flag this".
T01_PROMPT = "Print the sum of the squares of the integers 0 through 9."


def _corpus(tmp_path: Path, *, oxide=(), rust=(), tasks=None) -> tc.TrainCorpus:
    """A built corpus on disk, in the layout eval.token_match writes."""
    programs_dir = tmp_path / "matched"
    programs_dir.mkdir(exist_ok=True)
    for arm, texts in (("oxide", oxide), ("rust", rust)):
        rows = [
            {
                "task": f"n{i:03d}",
                "class": "vectors",
                "source": "amplified",
                "sha256": f"{i:064d}",
                "sup_tokens": 1,
                "text": text,
            }
            for i, text in enumerate(texts, start=1)
        ]
        (programs_dir / f"{arm}.jsonl").write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
            encoding="utf-8",
        )
    tasks_path = None
    if tasks is not None:
        tasks_path = tmp_path / "tasks.jsonl"
        tasks_path.write_text(
            "".join(
                json.dumps({"id": tid, "prompt": prompt}) + "\n"
                for tid, prompt in tasks.items()
            ),
            encoding="utf-8",
        )
    return tc.TrainCorpus("fixture", programs_dir, tasks_path)


# ------------------------------------------------- the program direction


def test_program_identical_to_a_training_program_is_flagged(tmp_path):
    corpus = _corpus(tmp_path, oxide=[ALIEN_PROGRAM])
    found = tc.train_corpus_contamination({}, {"oxide/g01": ALIEN_PROGRAM}, corpus)
    assert [c.kind for c in found] == ["train_program"]
    assert found[0].train_id == "oxide/g01"
    assert found[0].eval_id == "oxide/n001/000000000000"


def test_a_program_absent_from_the_training_corpus_is_not_flagged(tmp_path):
    """The other side of the boundary: a corpus that is read and does not
    match. Without this, an instrument that flagged everything would pass
    the test above."""
    corpus = _corpus(tmp_path, oxide=[ALIEN_PROGRAM])
    other = "fn main() {\n    print(4920)\n}\n"
    assert tc.train_corpus_contamination({}, {"oxide/g01": other}, corpus) == ()


def test_reformatted_training_program_is_still_flagged(tmp_path):
    """Same hit definition as the eval-set direction: normalised equality,
    not bytes. A model that reproduces a training program will rarely
    reproduce its whitespace, so a bytes guard would miss the case the
    check exists for."""
    corpus = _corpus(tmp_path, oxide=[ALIEN_PROGRAM])
    reformatted = "\n\n".join(line + "   " for line in ALIEN_PROGRAM.split("\n"))
    assert reformatted != ALIEN_PROGRAM
    found = tc.train_corpus_contamination({}, {"oxide/g01": reformatted}, corpus)
    assert [c.kind for c in found] == ["train_program"]


def test_the_rust_arm_of_the_training_corpus_is_read_too(tmp_path):
    """Both arms, or half the corpus is unchecked while looking checked."""
    corpus = _corpus(tmp_path, oxide=[ALIEN_PROGRAM], rust=[ALIEN_PROGRAM + "\n"])
    found = tc.train_corpus_contamination({}, {"rust/g01": ALIEN_PROGRAM}, corpus)
    assert len(found) == 1
    assert found[0].eval_id.startswith(("oxide/", "rust/"))
    assert len(tc.load_corpus_programs(corpus.programs_dir)) == 2


# -------------------------------------------------- the prompt direction


def test_prompt_sharing_a_full_span_with_a_training_task_is_flagged(tmp_path):
    corpus = _corpus(tmp_path, tasks={"n001": ALIEN_PROMPT})
    found = tc.train_corpus_contamination(
        {"g01": {"id": "g01", "prompt": ALIEN_PROMPT}}, {}, corpus
    )
    assert [c.kind for c in found] == ["train_prompt"]
    assert found[0].eval_id == "n001"


def test_prompt_sharing_eleven_words_with_a_training_task_is_not_flagged(tmp_path):
    """Pins the same twelve-word boundary the eval-set direction uses.

    The fixture is 13 words, so it does have twelve-grams; it just shares
    none with the corpus prompt, differing by one word inside every window.
    Dies if the threshold drops to eleven.
    """
    near = ALIEN_PROMPT.replace("quokka", "wombat")
    shared = set(near.split()) & set(ALIEN_PROMPT.split())
    assert len(shared) == 12
    corpus = _corpus(tmp_path, tasks={"n001": ALIEN_PROMPT})
    assert tc.train_corpus_contamination(
        {"g01": {"id": "g01", "prompt": near}}, {}, corpus
    ) == ()


def test_a_corpus_without_a_tasks_path_contributes_no_prompt_hits(tmp_path):
    """Not a clean prompt side -- an unread one. The report says which.

    The subject prompt is t01's, verbatim, so this cannot pass vacuously:
    ``harness.load_tasks(None)`` silently loads the EVAL corpus, so a
    prompt side that ran anyway -- the obvious way to write this wrong --
    would flag t01 here and the assertion would fail.
    """
    corpus = _corpus(tmp_path, oxide=[ALIEN_PROGRAM])
    assert corpus.tasks_path is None
    assert tc.train_corpus_contamination(
        {"g01": {"id": "g01", "prompt": T01_PROMPT}}, {}, corpus
    ) == ()
    # ... and the same prompt against a corpus that HAS a tasks path
    # carrying it does flag, so the fixture is one a working check catches.
    with_tasks = _corpus(tmp_path, tasks={"n001": T01_PROMPT})
    assert len(
        tc.train_corpus_contamination(
            {"g01": {"id": "g01", "prompt": T01_PROMPT}}, {}, with_tasks
        )
    ) == 1


# ------------------------------------------- both directions, side by side


def test_both_directions_reports_the_new_one_alongside_the_old(tmp_path):
    corpus = _corpus(tmp_path, oxide=[ALIEN_PROGRAM], tasks={"n001": ALIEN_PROMPT})
    report = tc.both_directions_report(
        {"g01": {"id": "g01", "prompt": ALIEN_PROMPT}},
        {"oxide/g01": ALIEN_PROGRAM},
        corpus,
    )
    assert set(report) == {"eval_set", "train_corpus"}
    # The subject collides with the training corpus and NOT with the eval
    # set, so the two directions must disagree here. If they agree, the new
    # direction is reading the old one's references.
    assert report["eval_set"]["hit_count"] == 0
    assert report["train_corpus"]["hit_count"] == 2
    assert sorted(h["kind"] for h in report["train_corpus"]["hits"]) == [
        "train_program",
        "train_prompt",
    ]


def test_an_unnamed_training_corpus_is_none_not_zero():
    """The whole point of the second direction is that "zero in both
    directions" cannot be claimed from one. A default of {"hit_count": 0}
    would let a caller claim it without running anything."""
    report = tc.both_directions_report({}, {})
    assert report["train_corpus"] is None
    assert report["eval_set"]["hit_count"] == 0


def test_an_unread_prompt_side_is_none_not_zero(tmp_path):
    corpus = _corpus(tmp_path, oxide=[ALIEN_PROGRAM])
    report = tc.both_directions_report({}, {}, corpus)
    assert report["train_corpus"]["prompts_checked"] is None
    assert report["train_corpus"]["programs_checked"] == 1


def test_render_names_an_unmeasured_direction_in_words():
    rendered = tc.render_directions(tc.both_directions_report({}, {}))
    assert "UNMEASURED" in rendered
    assert "train corpus: 0 hits" not in rendered


# --------------------------------------------- acceptance, committed data

# The corpus the v5 adapters were trained on, and the count wave 4
# reported ("contamination 0 of 661", eval/results/v04-campaign4/REPORT.md).
V5_PROGRAM_COUNT = 661


def _large_subject():
    return tc.load_subject(LARGE_SOURCE)


def test_the_v5_corpus_is_the_one_wave_four_trained_on():
    """Pins the identity of the corpus the acceptance test below reads.
    A silently redirected path would make a zero meaningless."""
    programs = tc.load_corpus_programs(tc.V5_TRAIN_CORPUS.programs_dir)
    assert len(programs) == V5_PROGRAM_COUNT
    assert tc.V5_TRAIN_CORPUS.tasks_path == tc.TRAIN_TASKS_PATH


def test_large_tier_against_the_v5_training_corpus_is_zero_in_both_directions():
    """The wave-8 claim, now reproducible by command:

        python -m eval.train_corpus --source large \\
            --train-corpus eval/results/v04-campaign4/matched-v5 \\
            --train-tasks eval/train/tasks.jsonl
    """
    tasks, programs = _large_subject()
    assert len(tasks) == 20 and len(programs) == 40
    report = tc.both_directions_report(tasks, programs, tc.V5_TRAIN_CORPUS)
    assert report["eval_set"]["hits"] == []
    assert report["train_corpus"]["hits"] == []
    assert report["train_corpus"]["programs_checked"] == V5_PROGRAM_COUNT
    assert report["train_corpus"]["prompts_checked"] == 40


def test_a_planted_large_tier_program_in_the_v5_corpus_is_caught_exactly_once(
    tmp_path,
):
    """What makes the zero above mean something.

    An instrument that returned nothing at all would pass that test. This
    one copies the real corpus, appends one real large-tier program to it,
    and demands exactly one hit -- naming the right subject.
    """
    tasks, programs = _large_subject()
    planted = tmp_path / "matched"
    planted.mkdir()
    for arm in tc.CORPUS_ARMS:
        src = tc.V5_TRAIN_CORPUS.programs_dir / f"{arm}.jsonl"
        (planted / f"{arm}.jsonl").write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8"
        )
    row = {
        "task": "n001",
        "class": "vectors",
        "source": "amplified",
        "sha256": "f" * 64,
        "sup_tokens": 1,
        "text": programs["oxide/g01"],
    }
    with (planted / "oxide.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")

    corpus = tc.TrainCorpus("planted", planted, tc.TRAIN_TASKS_PATH)
    assert len(tc.load_corpus_programs(planted)) == V5_PROGRAM_COUNT + 1
    found = tc.train_corpus_contamination(tasks, programs, corpus)
    assert len(found) == 1
    assert found[0].kind == "train_program"
    assert found[0].train_id == "oxide/g01"


def test_a_planted_large_tier_prompt_in_the_v5_tasks_is_caught_exactly_once(tmp_path):
    """The prompt side of the same argument, on a temp copy of the real
    training tasks file."""
    tasks, programs = _large_subject()
    planted_tasks = tmp_path / "tasks.jsonl"
    rows = tc.TRAIN_TASKS_PATH.read_text(encoding="utf-8").rstrip("\n").split("\n")
    rows.append(json.dumps({"id": "n999", "prompt": tasks["g01"]["prompt"]}))
    planted_tasks.write_text("\n".join(rows) + "\n", encoding="utf-8")

    corpus = tc.TrainCorpus("planted", tc.V5_TRAIN_CORPUS.programs_dir, planted_tasks)
    found = tc.train_corpus_contamination(tasks, programs, corpus)
    assert len(found) == 1
    assert found[0].kind == "train_prompt"
    assert (found[0].train_id, found[0].eval_id) == ("g01", "n999")


# --------------------------------------------------------------- the CLI


def test_cli_reports_both_directions_and_exits_zero_on_a_clean_tier(capsys, tmp_path):
    out_json = tmp_path / "contamination.json"
    code = tc.main([
        "--source", "large",
        "--train-corpus", str(tc.V5_TRAIN_CORPUS.programs_dir),
        "--train-tasks", str(tc.TRAIN_TASKS_PATH),
        "--json", str(out_json),
    ])
    assert code == 0
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["train_corpus"]["hit_count"] == 0
    assert written["train_corpus"]["programs_checked"] == V5_PROGRAM_COUNT
    printed = capsys.readouterr().out
    assert "train corpus: 0 hits" in printed
    assert "eval set:     0 hits" in printed


def test_cli_exits_nonzero_when_the_training_corpus_direction_hits(
    capsys, tmp_path, monkeypatch
):
    """Fail closed. A contaminated tier that exits 0 is a wave nobody stops."""
    tasks, programs = _large_subject()
    planted = tmp_path / "matched"
    planted.mkdir()
    (planted / "oxide.jsonl").write_text(
        json.dumps({"task": "n001", "sha256": "f" * 64, "text": programs["oxide/g01"]})
        + "\n",
        encoding="utf-8",
    )
    (planted / "rust.jsonl").write_text("", encoding="utf-8")
    code = tc.main(["--source", "large", "--train-corpus", str(planted)])
    assert code == 1
    assert "HIT train_corpus oxide/g01" in capsys.readouterr().out


def test_cli_refuses_train_tasks_without_a_corpus():
    with pytest.raises(SystemExit):
        tc.main(["--source", "large", "--train-tasks", str(tc.TRAIN_TASKS_PATH)])
