"""Cost census: where the oxide/rust token surplus actually sits.

The demand census (``eval/demand_census.py``) counts what models ATTEMPT
to write. This module counts what correct programs COST. Wave 2 proved
the two disagree: ``swap`` and index assignment had near-zero reply
demand and carried the single largest token surplus in the corpus, so a
slate gated on demand alone deferred the most expensive gap in the
language. Wave 3 gates on both.

A separate module rather than another section of ``demand_census.py``:
that file is already 954 lines and flagged for a split.

Wave 8 parameterised the census over a ``PairSource``. It was bound to
the train pairs root, so wave 7A's eval-set census had to be computed
ad-hoc rather than by committed code -- a number nobody could reproduce
by command. Three task sets now run through one instrument.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from eval import harness
from eval.token_match import qwen_counter
from eval.tokenizer_pin import TOKENIZER_FILE
from eval.train_corpus import PAIRS_ROOT, TRAIN_TASKS_PATH

RESULTS_DIR = Path("eval/results/v04-cost-census")

_REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class PairSource:
    """Where one set of reference pairs lives, and how it is laid out.

    Two layouts exist in this repo and neither is going away: the train
    corpus nests both arms under a per-task directory, the eval sets key
    by arm and then by task. Templates rather than a layout flag, so a
    fourth set can be added without touching the reader.
    """

    name: str
    tasks_path: Path
    root: Path
    oxide_template: str
    rust_template: str

    def oxide_path(self, task: str) -> Path:
        return self.root / self.oxide_template.format(task=task)

    def rust_path(self, task: str) -> Path:
        return self.root / self.rust_template.format(task=task)


TRAIN_SOURCE = PairSource(
    "train", TRAIN_TASKS_PATH, PAIRS_ROOT, "{task}/oxide.ox", "{task}/rust.rs"
)
EVAL_SOURCE = PairSource(
    "eval",
    harness.TASKS_PATH,
    _REPO_ROOT / "eval" / "references-v04",
    "oxide/{task}.ox",
    "rust/{task}.rs",
)
LARGE_SOURCE = PairSource(
    "large",
    _REPO_ROOT / "eval" / "tasks-large.jsonl",
    _REPO_ROOT / "eval" / "references-large",
    "oxide/{task}.ox",
    "rust/{task}.rs",
)
SOURCES = {s.name: s for s in (TRAIN_SOURCE, EVAL_SOURCE, LARGE_SOURCE)}


@dataclass(frozen=True)
class PairCost:
    """One reference pair's token cost in both arms."""

    task: str
    cls: str
    oxide_tokens: int
    rust_tokens: int
    stratum: str | None = None

    @property
    def surplus(self) -> int:
        """Signed: NEGATIVE where oxide wins. Never clipped at zero --
        structs/option runs negative in the real corpus and cancels most
        of the strings surplus, so clipping would inflate the total."""
        return self.oxide_tokens - self.rust_tokens

    @property
    def ratio(self) -> float | None:
        """None rather than a fabricated number if a rust side is empty."""
        if self.rust_tokens == 0:
            return None
        return self.oxide_tokens / self.rust_tokens


def pair_costs(
    count: Callable[[str], int],
    source: PairSource = TRAIN_SOURCE,
) -> tuple[list[PairCost], list[str]]:
    """Every reference pair's cost, plus the ids of pairs that could not
    be measured. An unreadable pair is DROPPED and named -- never scored
    zero, which would read as "this pair costs nothing"."""
    tasks = harness.load_tasks(source.tasks_path)
    costs: list[PairCost] = []
    dropped: list[str] = []
    for tid in sorted(tasks):
        try:
            oxide = source.oxide_path(tid).read_text(encoding="utf-8")
            rust = source.rust_path(tid).read_text(encoding="utf-8")
        except OSError:
            dropped.append(tid)
            continue
        costs.append(
            PairCost(
                tid,
                tasks[tid]["class"],
                count(oxide),
                count(rust),
                tasks[tid].get("stratum"),
            )
        )
    return costs, dropped


def rank_by_surplus(costs: list[PairCost]) -> list[PairCost]:
    """Most expensive first. Ties break on task id so the ranking is
    reproducible rather than input-order dependent."""
    return sorted(costs, key=lambda c: (-c.surplus, c.task))


def subtotals(
    costs: list[PairCost],
    key: Callable[[PairCost], str | None],
) -> dict[str, dict]:
    """Arm totals, signed surplus, and the ratio OF THE TOTALS (not a mean
    of per-pair ratios -- the estimand is tokens per program across the
    group, so long programs must weigh more than short ones).

    Pairs whose key is None are omitted from the grouping rather than
    bucketed under a fabricated label."""
    subs: dict[str, dict] = {}
    for c in costs:
        name = key(c)
        if name is None:
            continue
        entry = subs.setdefault(name, {"oxide": 0, "rust": 0})
        entry["oxide"] += c.oxide_tokens
        entry["rust"] += c.rust_tokens
    for entry in subs.values():
        entry["surplus"] = entry["oxide"] - entry["rust"]
        entry["ratio"] = None if entry["rust"] == 0 else entry["oxide"] / entry["rust"]
    return subs


def class_subtotals(costs: list[PairCost]) -> dict[str, dict]:
    """Per-class subtotals. Kept as a named entry point because the class
    breakdown is the one every wave reports."""
    return subtotals(costs, lambda c: c.cls)


def stratum_subtotals(costs: list[PairCost]) -> dict[str, dict]:
    """Per-stratum subtotals, empty for a source that carries no strata.

    Wave 8's large tier splits compositional from large-linear tasks: if
    the surplus collapses on one and persists on the other, the model's
    habit is premature rather than wrong, and only this split can say so.
    """
    return subtotals(costs, lambda c: c.stratum)


def _tokenizer_sha256() -> str:
    return hashlib.sha256(Path(TOKENIZER_FILE).read_bytes()).hexdigest()


def build_cost_census(source: PairSource = TRAIN_SOURCE) -> dict:
    costs, dropped = pair_costs(qwen_counter(), source)
    subs = class_subtotals(costs)
    strata = stratum_subtotals(costs)
    overall_ox = sum(c.oxide_tokens for c in costs)
    overall_rs = sum(c.rust_tokens for c in costs)
    return {
        "source": source.name,
        "tokenizer": {"path": str(TOKENIZER_FILE), "sha256": _tokenizer_sha256()},
        "dropped": dropped,
        "pairs": [
            {
                "task": c.task,
                "class": c.cls,
                "stratum": c.stratum,
                "oxide": c.oxide_tokens,
                "rust": c.rust_tokens,
                "surplus": c.surplus,
                "ratio": c.ratio,
            }
            for c in rank_by_surplus(costs)
        ],
        "classes": subs,
        "strata": strata,
        "overall": {
            "oxide": overall_ox,
            "rust": overall_rs,
            "surplus": overall_ox - overall_rs,
            "ratio": None if overall_rs == 0 else overall_ox / overall_rs,
        },
    }


def render_report(census: dict) -> str:
    lines = [
        "# v0.4 Cost Census",
        "",
        "Per-pair oxide/rust token surplus over the committed reference",
        "pairs, ranked. The demand census counts what models attempt; this",
        "counts what correct programs cost. Surplus is signed -- negative",
        "means oxide wins -- and is never clipped.",
        "",
        f"Source: `{census['source']}`",
        "",
        f"Tokenizer: `{census['tokenizer']['path']}` "
        f"sha256 `{census['tokenizer']['sha256'][:16]}...`",
        "",
        f"Dropped (unmeasured, named not zeroed): {census['dropped'] or 'none'}",
        "",
        "## Ranked by surplus",
        "",
        "| task | class | oxide | rust | surplus | ratio |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for p in census["pairs"]:
        ratio = "n/a" if p["ratio"] is None else f"{p['ratio']:.3f}"
        lines.append(
            f"| {p['task']} | {p['class']} | {p['oxide']} | {p['rust']} "
            f"| {p['surplus']:+d} | {ratio} |"
        )
    lines += [
        "",
        "## Class subtotals",
        "",
        "| class | oxide | rust | surplus | ratio |",
        "|---|---:|---:|---:|---:|",
    ]
    for cls in sorted(census["classes"]):
        e = census["classes"][cls]
        ratio = "n/a" if e["ratio"] is None else f"{e['ratio']:.4f}"
        lines.append(
            f"| {cls} | {e['oxide']} | {e['rust']} | {e['surplus']:+d} | {ratio} |"
        )
    o = census["overall"]
    ratio = "n/a" if o["ratio"] is None else f"{o['ratio']:.4f}"
    lines += [
        f"| **overall** | **{o['oxide']}** | **{o['rust']}** "
        f"| **{o['surplus']:+d}** | **{ratio}** |",
        "",
    ]
    if census["strata"]:
        lines += [
            "## Stratum subtotals",
            "",
            "| stratum | oxide | rust | surplus | ratio |",
            "|---|---:|---:|---:|---:|",
        ]
        for name in sorted(census["strata"]):
            e = census["strata"][name]
            r = "n/a" if e["ratio"] is None else f"{e['ratio']:.4f}"
            lines.append(
                f"| {name} | {e['oxide']} | {e['rust']} | {e['surplus']:+d} | {r} |"
            )
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.cost_census")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR)
    parser.add_argument("--source", choices=sorted(SOURCES), default="train")
    args = parser.parse_args(argv)
    census = build_cost_census(SOURCES[args.source])
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cost_census.json").write_text(
        json.dumps(census, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "REPORT.md").write_text(render_report(census), encoding="utf-8")
    print(f"cost census written to {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
