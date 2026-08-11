"""Training-corpus loading and the contamination guard.

The guard is what protects the v03c comparison. If any t01-t20 content
reaches the training corpus, a model fine-tuned on it and evaluated on
t01-t20 posts a gain whether or not Black Oxide is easier to learn than
Rust -- which is the entire question the fine-tune track exists to ask.

Design: docs/superpowers/specs/2026-08-11-finetune-data-factory-design.md
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eval import harness

_REPO_ROOT = Path(__file__).resolve().parents[1]

TRAIN_ROOT = _REPO_ROOT / "eval" / "train"
TRAIN_TASKS_PATH = TRAIN_ROOT / "tasks.jsonl"
PAIRS_ROOT = TRAIN_ROOT / "pairs"
SOLUTIONS_ROOT = _REPO_ROOT / "eval" / "solutions"

# A shared span this long between a training prompt and an eval prompt is
# copying, not coincidence: t01's whole prompt is exactly twelve words.
# Eleven is ordinary English -- "the sum of the squares of the integers 0
# through 9." is a phrase two independent authors can both write.
# tests/test_train_corpus.py pins BOTH sides of this boundary, and moving
# it one word in either direction kills a named test.
NGRAM_WORDS = 12

# The committed eval solutions, by arm and the extension each arm uses.
_SOLUTION_GLOBS = (("oxide", "*.ox"), ("explicit", "*.ox"), ("rust", "*.rs"))


def normalize_source(text: str) -> str:
    """Whitespace-insensitive form used for exact-match comparison.

    Trailing space and blank lines are discarded; leading indentation is
    NOT, because it is real program structure and collapsing it would
    make distinct programs compare equal.
    """
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(line for line in lines if line.strip())


def _word_ngrams(text: str, n: int) -> set[tuple[str, ...]]:
    words = text.split()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


@dataclass(frozen=True, slots=True)
class Contamination:
    """One way a training item overlaps the held-out eval corpus."""

    train_id: str
    kind: str  # "solution" | "prompt"
    eval_id: str
    detail: str


def _eval_solutions() -> dict[str, str]:
    """Normalised eval solution text -> the task id it solves."""
    found: dict[str, str] = {}
    for arm, pattern in _SOLUTION_GLOBS:
        for path in sorted((SOLUTIONS_ROOT / arm).glob(pattern)):
            found[normalize_source(path.read_text(encoding="utf-8"))] = path.stem
    return found


def contamination_report(
    train_tasks: dict[str, dict],
    train_programs: dict[str, str],
) -> tuple[Contamination, ...]:
    """Every way the training corpus overlaps the held-out eval corpus.

    An empty result is the only acceptable state for a committed corpus.
    """
    hits: list[Contamination] = []

    solutions = _eval_solutions()
    for train_id, source in sorted(train_programs.items()):
        eval_id = solutions.get(normalize_source(source))
        if eval_id is not None:
            hits.append(
                Contamination(
                    train_id,
                    "solution",
                    eval_id,
                    "program matches a committed eval solution",
                )
            )

    eval_ngrams = {
        tid: _word_ngrams(task["prompt"], NGRAM_WORDS)
        for tid, task in harness.load_tasks().items()
    }
    for train_id, task in sorted(train_tasks.items()):
        mine = _word_ngrams(task["prompt"], NGRAM_WORDS)
        for eval_id, theirs in sorted(eval_ngrams.items()):
            shared = mine & theirs
            if shared:
                span = " ".join(sorted(shared)[0])
                hits.append(
                    Contamination(
                        train_id,
                        "prompt",
                        eval_id,
                        f"shares a {NGRAM_WORDS}-word span: {span!r}",
                    )
                )
                break

    return tuple(hits)


def load_train_tasks() -> dict[str, dict]:
    """The training corpus, keyed by task id."""
    return harness.load_tasks(TRAIN_TASKS_PATH)


def load_train_programs() -> dict[str, str]:
    """Every committed training program, keyed by its path under pairs/."""
    programs: dict[str, str] = {}
    if not PAIRS_ROOT.exists():
        return programs
    for path in sorted(PAIRS_ROOT.rglob("*")):
        if path.is_file() and path.suffix in (".ox", ".rs"):
            programs[str(path.relative_to(PAIRS_ROOT))] = path.read_text(
                encoding="utf-8"
            )
    return programs
