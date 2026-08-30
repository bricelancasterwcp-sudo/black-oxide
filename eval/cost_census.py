"""Cost census: where the oxide/rust token surplus actually sits.

The demand census (``eval/demand_census.py``) counts what models ATTEMPT
to write. This module counts what correct programs COST. Wave 2 proved
the two disagree: ``swap`` and index assignment had near-zero reply
demand and carried the single largest token surplus in the corpus, so a
slate gated on demand alone deferred the most expensive gap in the
language. Wave 3 gates on both.

A separate module rather than another section of ``demand_census.py``:
that file is already 954 lines and flagged for a split.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from eval.token_match import qwen_counter
from eval.tokenizer_pin import TOKENIZER_FILE
from eval.train_corpus import PAIRS_ROOT, load_train_tasks

RESULTS_DIR = Path("eval/results/v04-cost-census")


@dataclass(frozen=True)
class PairCost:
    """One reference pair's token cost in both arms."""

    task: str
    cls: str
    oxide_tokens: int
    rust_tokens: int

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


def pair_costs(count: Callable[[str], int]) -> tuple[list[PairCost], list[str]]:
    """Every reference pair's cost, plus the ids of pairs that could not
    be measured. An unreadable pair is DROPPED and named -- never scored
    zero, which would read as "this pair costs nothing"."""
    tasks = load_train_tasks()
    costs: list[PairCost] = []
    dropped: list[str] = []
    for tid in sorted(tasks):
        try:
            oxide = (PAIRS_ROOT / tid / "oxide.ox").read_text(encoding="utf-8")
            rust = (PAIRS_ROOT / tid / "rust.rs").read_text(encoding="utf-8")
        except OSError:
            dropped.append(tid)
            continue
        costs.append(PairCost(tid, tasks[tid]["class"], count(oxide), count(rust)))
    return costs, dropped


def rank_by_surplus(costs: list[PairCost]) -> list[PairCost]:
    """Most expensive first. Ties break on task id so the ranking is
    reproducible rather than input-order dependent."""
    return sorted(costs, key=lambda c: (-c.surplus, c.task))


def class_subtotals(costs: list[PairCost]) -> dict[str, dict]:
    """Per-class arm totals, signed surplus, and the ratio OF THE TOTALS
    (not a mean of per-pair ratios -- the estimand is tokens per program
    across the class, so long programs must weigh more than short ones)."""
    subs: dict[str, dict] = {}
    for c in costs:
        entry = subs.setdefault(c.cls, {"oxide": 0, "rust": 0})
        entry["oxide"] += c.oxide_tokens
        entry["rust"] += c.rust_tokens
    for entry in subs.values():
        entry["surplus"] = entry["oxide"] - entry["rust"]
        entry["ratio"] = None if entry["rust"] == 0 else entry["oxide"] / entry["rust"]
    return subs


def _tokenizer_sha256() -> str:
    return hashlib.sha256(Path(TOKENIZER_FILE).read_bytes()).hexdigest()


def build_cost_census() -> dict:
    costs, dropped = pair_costs(qwen_counter())
    subs = class_subtotals(costs)
    overall_ox = sum(c.oxide_tokens for c in costs)
    overall_rs = sum(c.rust_tokens for c in costs)
    return {
        "tokenizer": {"path": str(TOKENIZER_FILE), "sha256": _tokenizer_sha256()},
        "dropped": dropped,
        "pairs": [
            {
                "task": c.task,
                "class": c.cls,
                "oxide": c.oxide_tokens,
                "rust": c.rust_tokens,
                "surplus": c.surplus,
                "ratio": c.ratio,
            }
            for c in rank_by_surplus(costs)
        ],
        "classes": subs,
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
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.cost_census")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR)
    args = parser.parse_args(argv)
    census = build_cost_census()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cost_census.json").write_text(
        json.dumps(census, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "REPORT.md").write_text(render_report(census), encoding="utf-8")
    print(f"cost census written to {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
