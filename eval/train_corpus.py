"""Training-corpus loading and the contamination guard.

The guard is what protects the v03c comparison. If any t01-t20 content
reaches the training corpus, a model fine-tuned on it and evaluated on
t01-t20 posts a gain whether or not Black Oxide is easier to learn than
Rust -- which is the entire question the fine-tune track exists to ask.

Design: docs/superpowers/specs/2026-08-11-finetune-data-factory-design.md
"""

from __future__ import annotations

import argparse
import json
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
    """One way a subject item overlaps a corpus it must not have seen.

    ``train_id`` and ``eval_id`` are historical names from the first
    direction (training corpus checked against the held-out eval set) and
    are read generally: ``train_id`` is the SUBJECT item, ``eval_id`` the
    REFERENCE item it collided with. Renaming them would churn every
    caller and every pinned test for no measurement gain.
    """

    train_id: str
    kind: str  # "solution" | "prompt" | "train_program" | "train_prompt"
    eval_id: str
    detail: str


def _eval_solutions() -> dict[str, str]:
    """Normalised eval solution text -> the task id it solves."""
    found: dict[str, str] = {}
    for arm, pattern in _SOLUTION_GLOBS:
        for path in sorted((SOLUTIONS_ROOT / arm).glob(pattern)):
            found[normalize_source(path.read_text(encoding="utf-8"))] = path.stem
    return found


def _program_index(programs: dict[str, str]) -> dict[str, str]:
    """Normalised program text -> the id of the reference carrying it."""
    return {normalize_source(text): pid for pid, text in programs.items()}


def _program_hits(
    subject_programs: dict[str, str],
    reference_index: dict[str, str],
    kind: str,
    detail: str,
) -> list[Contamination]:
    """THE program hit definition, shared by every direction.

    A hit is exact equality of ``normalize_source`` text. Both directions
    call this function rather than re-deriving the rule, so a direction
    cannot silently drift to a looser or stricter one.
    """
    hits: list[Contamination] = []
    for subject_id, source in sorted(subject_programs.items()):
        reference_id = reference_index.get(normalize_source(source))
        if reference_id is not None:
            hits.append(Contamination(subject_id, kind, reference_id, detail))
    return hits


def _prompt_hits(
    subject_tasks: dict[str, dict],
    reference_ngrams: dict[str, set[tuple[str, ...]]],
    kind: str,
) -> list[Contamination]:
    """THE prompt hit definition, shared by every direction.

    A hit is one shared NGRAM_WORDS-word span. At most one hit is reported
    per subject task: the question is whether the task is contaminated, and
    listing every colliding reference would let one bad prompt swamp a
    report that has to stay readable.
    """
    hits: list[Contamination] = []
    for subject_id, task in sorted(subject_tasks.items()):
        mine = _word_ngrams(task["prompt"], NGRAM_WORDS)
        for reference_id, theirs in sorted(reference_ngrams.items()):
            shared = mine & theirs
            if shared:
                span = " ".join(sorted(shared)[0])
                hits.append(
                    Contamination(
                        subject_id,
                        kind,
                        reference_id,
                        f"shares a {NGRAM_WORDS}-word span: {span!r}",
                    )
                )
                break
    return hits


def contamination_report(
    train_tasks: dict[str, dict],
    train_programs: dict[str, str],
) -> tuple[Contamination, ...]:
    """Every way a task set overlaps the held-out eval corpus.

    An empty result is the only acceptable state for a committed corpus.
    """
    eval_ngrams = {
        tid: _word_ngrams(task["prompt"], NGRAM_WORDS)
        for tid, task in harness.load_tasks().items()
    }
    return tuple(
        _program_hits(
            train_programs,
            _eval_solutions(),
            "solution",
            "program matches a committed eval solution",
        )
        + _prompt_hits(train_tasks, eval_ngrams, "prompt")
    )


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


# ------------------------------------------ training-corpus direction

# The eval-set direction above asks "did the benchmark leak into the
# training data?". This one asks the mirror question -- "was this task set
# already in the corpus the adapters were fine-tuned on?" -- and it is the
# one that binds a dynamic wave: a task whose program or prompt the
# adapters were trained on measures recall, not the language.
#
# Wave 8's large tier was checked in both directions but only the first
# was in the instrument; the second was run ad-hoc and reported in prose
# (eval/results/v04-wave8-large/REPORT.md, feed-forward item 6). It is
# committed code from here on.


@dataclass(frozen=True, slots=True)
class TrainCorpus:
    """A built training corpus: what a fine-tune was actually shown.

    Two files, because the fine-tune reads two: ``scripts/runpod/train_lora.py``
    renders the prompt from ``tasks_path`` and supervises on the ``text``
    of each row under ``programs_dir``. Checking only one of them would
    leave the other direction of leakage unmeasured while looking checked.

    ``tasks_path`` is optional. A corpus whose prompt provenance is not
    known is still worth checking on programs -- but the prompt side is
    then reported as None, never as zero hits.
    """

    name: str
    programs_dir: Path
    tasks_path: Path | None = None


# The corpus the v5 adapters were fine-tuned on, which every v0.4 wave from
# 4 onward reads against. Recorded, not guessed: wave 4's REPORT.md counts
# "282 oxide training examples" and "contamination 0 of 661", and both
# reproduce from this directory. The prompts are eval/train/tasks.jsonl --
# train_lora.py's TRAIN_TASKS, unchanged since 2026-08-13, well before the
# 2026-08-31 wave-4 run. NOT the default of any entry point: a caller names
# the corpus it means.
V5_TRAIN_CORPUS = TrainCorpus(
    "v5",
    _REPO_ROOT / "eval" / "results" / "v04-campaign4" / "matched-v5",
    TRAIN_TASKS_PATH,
)

CORPUS_ARMS = ("oxide", "rust")


def load_corpus_programs(programs_dir: Path) -> dict[str, str]:
    """Every program in a built matched corpus, keyed ``arm/task/sha12``.

    The key is the one ``eval.token_match`` writes, so a count here is
    directly comparable to a manifest's ``programs_checked`` -- 661 for
    the v5 corpus, which is the number wave 4 reported.
    """
    programs: dict[str, str] = {}
    for arm in CORPUS_ARMS:
        path = Path(programs_dir) / f"{arm}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            programs[f"{arm}/{row['task']}/{row['sha256'][:12]}"] = row["text"]
    return programs


def train_corpus_contamination(
    subject_tasks: dict[str, dict],
    subject_programs: dict[str, str],
    corpus: TrainCorpus,
) -> tuple[Contamination, ...]:
    """Every way a task set overlaps the corpus a fine-tune was trained on.

    Identical hit definition to the eval-set direction -- both call
    ``_program_hits`` and ``_prompt_hits``, so neither can drift. Only the
    reference side moves: from ``eval/solutions/`` and ``eval/tasks.jsonl``
    to the corpus's own programs and prompts.

    The kinds are named ``train_program`` / ``train_prompt`` rather than
    reusing ``solution`` / ``prompt`` so that a hit stays attributable to
    its direction if a caller flattens both lists.

    A corpus with no ``tasks_path`` contributes no prompt hits, and callers
    must report that side as unmeasured rather than clean --
    ``both_directions_report`` does.
    """
    hits = _program_hits(
        subject_programs,
        _program_index(load_corpus_programs(corpus.programs_dir)),
        "train_program",
        f"program matches a program in the {corpus.name} training corpus",
    )
    if corpus.tasks_path is not None:
        corpus_ngrams = {
            tid: _word_ngrams(task["prompt"], NGRAM_WORDS)
            for tid, task in harness.load_tasks(corpus.tasks_path).items()
        }
        hits += _prompt_hits(subject_tasks, corpus_ngrams, "train_prompt")
    return tuple(hits)


def _direction_row(hits: tuple[Contamination, ...], **counts) -> dict:
    return {
        "hits": [
            {
                "subject_id": h.train_id,
                "kind": h.kind,
                "reference_id": h.eval_id,
                "detail": h.detail,
            }
            for h in hits
        ],
        "hit_count": len(hits),
        **counts,
    }


def both_directions_report(
    subject_tasks: dict[str, dict],
    subject_programs: dict[str, str],
    corpus: TrainCorpus | None = None,
) -> dict:
    """Both contamination directions for one task set, side by side.

    ``train_corpus`` is None -- never ``{"hit_count": 0}`` -- when no corpus
    was named, and ``prompts_checked`` is None when the named corpus has no
    ``tasks_path``. An unrun check and a clean check are different states
    and a reader must be able to tell them apart; the whole value of this
    report is that "zero in both directions" cannot be claimed from one.
    """
    report = {
        "eval_set": _direction_row(
            contamination_report(subject_tasks, subject_programs),
            programs_checked=len(subject_programs),
            prompts_checked=len(subject_tasks),
        ),
        "train_corpus": None,
    }
    if corpus is not None:
        report["train_corpus"] = _direction_row(
            train_corpus_contamination(subject_tasks, subject_programs, corpus),
            corpus=corpus.name,
            programs_dir=str(corpus.programs_dir),
            tasks_path=None if corpus.tasks_path is None else str(corpus.tasks_path),
            programs_checked=len(load_corpus_programs(corpus.programs_dir)),
            prompts_checked=(
                None
                if corpus.tasks_path is None
                else len(harness.load_tasks(corpus.tasks_path))
            ),
        )
    return report


# --------------------------------------------------------- Stage A gate

# SPEC section 22 reserves this prefix for generated Rust. Its presence in
# a hand-authored Rust reference means the file is transpiler output.
OXIDE_PREFIX = "__oxide_"


def _failure_reason(arm: str, verdict: dict, expected: str) -> str:
    if not verdict["compiled"]:
        diagnostics = verdict["diagnostics"]
        head = diagnostics[0] if diagnostics else {}
        code = head.get("code", "?")
        message = head.get("message", "no diagnostics recorded")
        return f"{arm} reference did not compile: {code} {message}"
    return (
        f"{arm} reference compiled but printed {verdict['stdout']!r}, "
        f"expected {expected!r}"
    )


def validate_pair(task: dict, oxide_path: Path, rust_path: Path) -> dict:
    """Gate one Stage A reference pair.

    Both arms must compile, run, and match the task's expected_stdout --
    which also proves the two references agree with each other, so a task
    whose arms implement different things cannot enter the corpus as a
    matched pair.

    The Rust reference must not contain the reserved codegen prefix. A
    Rust arm trained on transpiler output is a handicapped control, and
    any Black Oxide advantage measured against it would be an artifact of
    that handicap rather than a property of the language.

    Returns ``{"ok": bool, "reasons": tuple[str, ...]}``. A failing pair is
    discarded, never repaired: a task massaged into passing is a task the
    language could not express, kept anyway.
    """
    reasons: list[str] = []

    if OXIDE_PREFIX in rust_path.read_text(encoding="utf-8"):
        reasons.append(
            f"rust reference contains the reserved {OXIDE_PREFIX!r} prefix "
            f"(SPEC section 22) -- transpiler output is not idiomatic Rust"
        )

    expected = task["expected_stdout"]
    for arm, path in (("oxide", oxide_path), ("rust", rust_path)):
        verdict = harness.run_file(arm, path, expected)
        if not verdict["passed"]:
            reasons.append(_failure_reason(arm, verdict, expected))

    return {"ok": not reasons, "reasons": tuple(reasons)}


# ------------------------------------------------ amplification collector

TRAINING_ARMS = ("oxide", "rust")


def collect_verified(
    results_root: Path,
    arms: tuple[str, ...] = TRAINING_ARMS,
) -> dict[tuple[str, str], set[str]]:
    """Deduplicated passing programs per (task, arm) from an amplification run.

    Deduplication is on normalised source. Within a single campaign roughly
    84% of passing programs are already distinct, so this removes about a
    sixth rather than the two-thirds a cross-campaign figure would suggest --
    but it is not optional: counting cosmetic restatements separately would
    inflate the per-task yield the pilot is scored on.

    The explicit dialect is excluded by default. It is the eval's control
    arm, not a training target, and it rides along in every run only
    because ARMS is fixed.
    """
    found: dict[tuple[str, str], set[str]] = {}
    root = Path(results_root)
    if not root.exists():
        return found
    for path in sorted(root.rglob("triples.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("passed") and rec.get("arm") in arms:
                found.setdefault((rec["task"], rec["arm"]), set()).add(
                    normalize_source(rec["code"])
                )
    return found


# ------------------------------------------------------------------ CLI


def load_subject(source) -> tuple[dict[str, dict], dict[str, str]]:
    """One task set's tasks and both reference arms, from a PairSource.

    ``eval.cost_census.PairSource`` already describes where each of the
    three task sets lives, and wave 8 shipped it precisely so that a fourth
    set can be added in one place. Imported inside the function because
    cost_census imports this module.
    """
    programs: dict[str, str] = {}
    tasks = harness.load_tasks(source.tasks_path)
    for tid in sorted(tasks):
        programs[f"oxide/{tid}"] = source.oxide_path(tid).read_text(encoding="utf-8")
        programs[f"rust/{tid}"] = source.rust_path(tid).read_text(encoding="utf-8")
    return tasks, programs


def render_directions(report: dict) -> str:
    """One line per direction. An unrun direction says so in words."""
    lines = []
    left = report["eval_set"]
    lines.append(
        f"eval set:     {left['hit_count']} hits "
        f"({left['programs_checked']} programs, {left['prompts_checked']} prompts)"
    )
    right = report["train_corpus"]
    if right is None:
        lines.append(
            "train corpus: UNMEASURED -- no --train-corpus given "
            "(not the same as zero hits)"
        )
    else:
        prompts = (
            "UNMEASURED prompts"
            if right["prompts_checked"] is None
            else f"{right['prompts_checked']} prompts"
        )
        lines.append(
            f"train corpus: {right['hit_count']} hits "
            f"({right['programs_checked']} programs, {prompts}) "
            f"[{right['corpus']} @ {right['programs_dir']}]"
        )
    for direction in ("eval_set", "train_corpus"):
        row = report[direction]
        if row is None:
            continue
        for hit in row["hits"]:
            lines.append(
                f"  HIT {direction} {hit['subject_id']} ~ {hit['reference_id']} "
                f"({hit['kind']}): {hit['detail']}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from eval.cost_census import SOURCES  # deferred: cost_census imports this module

    parser = argparse.ArgumentParser(
        prog="python -m eval.train_corpus",
        description="Contamination report for one task set, in both directions.",
    )
    parser.add_argument("--source", choices=sorted(SOURCES), default="large")
    parser.add_argument(
        "--train-corpus",
        type=Path,
        default=None,
        help=(
            "directory holding a built matched corpus (oxide.jsonl, rust.jsonl). "
            "No default: naming the wrong corpus and guessing one are the same "
            "error, and only the first is visible in a command line. The v5 "
            "adapters every v0.4 wave reads were trained from "
            "eval/results/v04-campaign4/matched-v5."
        ),
    )
    parser.add_argument(
        "--train-tasks",
        type=Path,
        default=None,
        help=(
            "tasks file supplying that corpus's prompts (train_lora.py reads "
            "eval/train/tasks.jsonl). Omitted, the prompt side of the "
            "training-corpus direction is reported UNMEASURED, not clean."
        ),
    )
    parser.add_argument("--json", type=Path, default=None, help="also write JSON here")
    args = parser.parse_args(argv)

    if args.train_corpus is None and args.train_tasks is not None:
        parser.error("--train-tasks needs --train-corpus")

    corpus = (
        None
        if args.train_corpus is None
        else TrainCorpus(args.train_corpus.name, args.train_corpus, args.train_tasks)
    )
    tasks, programs = load_subject(SOURCES[args.source])
    report = both_directions_report(tasks, programs, corpus)
    print(f"source: {args.source}")
    print(render_directions(report))
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    measured = [d for d in report.values() if d is not None]
    return 1 if any(d["hit_count"] for d in measured) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
