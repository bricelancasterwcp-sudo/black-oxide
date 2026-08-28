"""Matched supervised-token training corpora from the paired factory output.

Implements docs/superpowers/specs/2026-08-27-token-matching-design.md.
Per class the smaller arm sets the budget; the surplus arm's AMPLIFIED
programs are dropped in ascending (sha256, task) order until its total
first reaches the budget or below; references are never trimmed. All
token counts flow through an injected counter so the core is testable
without the real tokenizer (Task 5 supplies the pinned Qwen counter).
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from eval.train_corpus import PAIRS_ROOT, collect_verified, load_train_tasks, normalize_source

ARMS = ("oxide", "rust")
_SOURCE_RANK = {"reference": 0, "amplified": 1}


class MatchError(ValueError):
    """Construction cannot satisfy the spec; fail closed."""


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Example:
    task: str
    cls: str
    source: str  # "reference" | "amplified"
    text: str
    sha256: str
    sup_tokens: int


@dataclass(frozen=True, slots=True)
class Dropped:
    task: str
    arm: str
    cls: str
    sha256: str
    sup_tokens: int


@dataclass(frozen=True, slots=True)
class ClassBudget:
    cls: str
    budget: int
    kept_tokens: dict[str, int]
    kept_examples: dict[str, int]
    gap: int
    quantization_step: int


@dataclass(frozen=True, slots=True)
class MatchResult:
    kept: dict[str, tuple[Example, ...]]
    dropped: tuple[Dropped, ...]
    budgets: tuple[ClassBudget, ...]
    prompt_tokens: dict[str, int]


def _class_examples(
    tasks: dict[str, dict],
    references: dict[tuple[str, str], str],
    amplified: dict[tuple[str, str], set[str]],
    count_tokens: Callable[[str], int],
) -> dict[tuple[str, str], list[Example]]:
    out: dict[tuple[str, str], list[Example]] = {}
    for tid in sorted(tasks):
        cls = tasks[tid]["class"]
        for arm in ARMS:
            ref = references.get((tid, arm))
            if ref is None:
                raise MatchError(f"missing {arm} reference for {tid}")
            norm = normalize_source(ref)
            items = [Example(tid, cls, "reference", norm, sha256_hex(norm), count_tokens(norm))]
            for text in sorted(amplified.get((tid, arm), set())):
                items.append(Example(tid, cls, "amplified", text, sha256_hex(text), count_tokens(text)))
            out.setdefault((cls, arm), []).extend(items)
    return out


def build_matched(
    tasks: dict[str, dict],
    references: dict[tuple[str, str], str],
    amplified: dict[tuple[str, str], set[str]],
    count_tokens: Callable[[str], int],
) -> MatchResult:
    by_class = _class_examples(tasks, references, amplified, count_tokens)
    classes = sorted({cls for cls, _ in by_class})

    kept: dict[str, list[Example]] = {arm: [] for arm in ARMS}
    dropped: list[Dropped] = []
    budgets: list[ClassBudget] = []
    for cls in classes:
        totals = {
            arm: sum(e.sup_tokens for e in by_class.get((cls, arm), ())) for arm in ARMS
        }
        budget = min(totals.values())
        surplus_arm = max(ARMS, key=lambda a: totals[a])
        surplus = by_class.get((cls, surplus_arm), [])
        ref_tokens = sum(e.sup_tokens for e in surplus if e.source == "reference")
        if ref_tokens > budget:
            raise MatchError(
                f"references alone exceed budget in class {cls!r} "
                f"({ref_tokens} > {budget}); re-author before matching"
            )
        candidates = sorted(
            (e for e in surplus if e.source == "amplified"),
            key=lambda e: (e.sha256, e.task),
        )
        step = max((e.sup_tokens for e in candidates), default=0)
        total = totals[surplus_arm]
        removed: set[tuple[str, str]] = set()
        for e in candidates:
            if total <= budget:
                break
            total -= e.sup_tokens
            removed.add((e.task, e.sha256))
            dropped.append(Dropped(e.task, surplus_arm, cls, e.sha256, e.sup_tokens))
        kept_tokens: dict[str, int] = {}
        kept_examples: dict[str, int] = {}
        for arm in ARMS:
            arm_kept = [
                e
                for e in by_class.get((cls, arm), ())
                if not (arm == surplus_arm and (e.task, e.sha256) in removed)
            ]
            kept[arm].extend(arm_kept)
            kept_tokens[arm] = sum(e.sup_tokens for e in arm_kept)
            kept_examples[arm] = len(arm_kept)
        budgets.append(
            ClassBudget(
                cls,
                budget,
                kept_tokens,
                kept_examples,
                max(kept_tokens.values()) - min(kept_tokens.values()),
                step,
            )
        )

    def sort_key(e: Example) -> tuple:
        return (e.cls, e.task, _SOURCE_RANK[e.source], e.sha256)

    kept_sorted = {arm: tuple(sorted(kept[arm], key=sort_key)) for arm in ARMS}
    prompt_tokens = {
        arm: sum(count_tokens(tasks[e.task]["prompt"]) for e in kept_sorted[arm])
        for arm in ARMS
    }
    return MatchResult(
        kept=kept_sorted,
        dropped=tuple(sorted(dropped, key=lambda d: (d.cls, d.arm, d.sha256, d.task))),
        budgets=tuple(budgets),
        prompt_tokens=prompt_tokens,
    )


MANIFEST_KEYS = frozenset({
    "tokenizer", "classes", "totals", "prompt_tokens",
    "dropped", "counts_source", "contamination", "token_efficiency",
})


def _example_row(e: Example) -> dict:
    return {"task": e.task, "class": e.cls, "source": e.source,
            "text": e.text, "sha256": e.sha256, "sup_tokens": e.sup_tokens}


def write_matched(
    out_dir: Path,
    result: MatchResult,
    *,
    tokenizer: dict,
    counts_source: dict,
    contamination: dict,
    token_efficiency: dict,
) -> None:
    """Serialize a MatchResult; byte-identical for equal inputs, no timestamps."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for arm in ARMS:
        lines = [json.dumps(_example_row(e), ensure_ascii=False, sort_keys=True)
                 for e in result.kept[arm]]
        (out_dir / f"{arm}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "tokenizer": tokenizer,
        "classes": [
            {"class": b.cls, "budget": b.budget, "kept_tokens": b.kept_tokens,
             "kept_examples": b.kept_examples, "gap": b.gap,
             "quantization_step": b.quantization_step}
            for b in result.budgets
        ],
        "totals": {
            "kept_tokens": {arm: sum(e.sup_tokens for e in result.kept[arm]) for arm in ARMS},
            "kept_examples": {arm: len(result.kept[arm]) for arm in ARMS},
        },
        "prompt_tokens": result.prompt_tokens,
        "dropped": [
            {"task": d.task, "arm": d.arm, "class": d.cls,
             "sha256": d.sha256, "sup_tokens": d.sup_tokens}
            for d in result.dropped
        ],
        "counts_source": counts_source,
        "contamination": contamination,
        "token_efficiency": token_efficiency,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


AMP_ROOTS = (
    Path("eval/results/train-amp2"),
    Path("eval/results/train-amp2-slice"),
)


def load_matched_inputs() -> tuple[
    dict[str, dict],
    dict[tuple[str, str], str],
    dict[tuple[str, str], set[str]],
]:
    """Tasks, references, and merged amplified programs for kept tasks only.

    Merging the amp2 and slice roots and restricting to the live
    tasks.jsonl reproduces the corpus the difficulty band cleared on
    2026-08-13 (slice REPORT: merged band PASS 30/30).
    """
    tasks = load_train_tasks()
    references = {}
    for tid in tasks:
        for arm, fname in (("oxide", "oxide.ox"), ("rust", "rust.rs")):
            references[(tid, arm)] = (PAIRS_ROOT / tid / fname).read_text(encoding="utf-8")
    amplified: dict[tuple[str, str], set[str]] = {}
    for root in AMP_ROOTS:
        for (task, arm), progs in collect_verified(root).items():
            if task in tasks:
                amplified.setdefault((task, arm), set()).update(progs)
    return tasks, references, amplified
