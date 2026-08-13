"""The two-arm, per-class difficulty band.

Origin: `eval/results/train-pilot-amp/REPORT.md`, recommendation 3. The
data-factory design pre-registered a difficulty band on the **oxide arm
only**, **whole-corpus only** (±10pp of `v03c` first-pass, per family).
It passed in all three families while two things it could not see went
wrong: codegemma's *rust* first-pass moved −10.5pp — larger than its
oxide move — and the vector and string classes drifted more than 20pp
each inside a passing whole-corpus number, because opposite per-class
drifts average out.

This module is the corrected instrument. It bands **both training arms**
(`oxide` and `rust` — the explicit-control arm is not a training arm and
is ignored) at **two granularities**: whole-corpus at the registered
±10pp, and per-class at ±20pp. The class width is derived, not chosen:
the worst-precision comparison is the strings class (4 eval tasks × 10
seeds = 40 attempts on the `v03c` side against ~100 on a pilot side),
where 2 SE of the difference is ≈17pp at the rates involved, so ±20pp
sits just outside the noise it must survive — the same
just-outside-noise rule the whole-corpus ±10pp was built on. Like that
band, it is a drift detector, deliberately not a significance test.

Missing data is loud, never a pass: a candidate missing a (family, arm)
the reference has, or missing a reference class entirely, raises
instead of producing a verdict — an unmeasured band is not a passed
band. Verdicts carry measured/reference/band via the shape gate's
`MetricVerdict`; one instrument vocabulary, two instruments.

CLI:
    python -m eval.difficulty_band CANDIDATE_ROOT \
        --candidate-tasks eval/train/tasks.jsonl \
        [--reference-root eval/results/v03-closing-baseline] \
        [--reference-tasks eval/tasks.jsonl]

exits 0 (all bands hold) or 1 (drift), printing every verdict.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from eval.shape_gate import GateResult, MetricVerdict, banded_verdict

WHOLE_BAND_PP = 0.10
CLASS_BAND_PP = 0.20

TRAINING_ARMS = ("oxide", "rust")

_FAMILY_RE = re.compile(r"-(qwen|codegemma|granite)\d+b-")

_REFERENCE_ROOT = Path(__file__).resolve().parent / "results" / "v03-closing-baseline"
_EVAL_TASKS = Path(__file__).resolve().parent / "tasks.jsonl"


@dataclass(frozen=True)
class Rates:
    """(passes, attempts) overall and per class, for one (family, arm)."""
    overall: tuple[int, int]
    per_class: dict[str, tuple[int, int]]


def task_classes(tasks_path: Path | str) -> dict[str, str]:
    return {
        row["id"]: row["class"]
        for row in (json.loads(line)
                    for line in Path(tasks_path).read_text().splitlines()
                    if line.strip())
    }


def load_family_cells(root: Path | str) -> dict[str, list[dict]]:
    """Every `cells.jsonl` under `root`, grouped by the family named in
    its run directory. A run dir whose name matches no known family is
    an error, not a silent skip — a mis-named run vanishing from the
    band is exactly the failure mode this instrument exists to close."""
    by_family: dict[str, list[dict]] = {}
    found = False
    for cells_path in sorted(Path(root).glob("*/cells.jsonl")):
        m = _FAMILY_RE.search(cells_path.parent.name)
        if not m:
            raise ValueError(
                f"run dir {cells_path.parent.name!r} names no known family"
            )
        found = True
        rows = [json.loads(line)
                for line in cells_path.read_text().splitlines() if line.strip()]
        by_family.setdefault(m.group(1), []).extend(rows)
    if not found:
        raise ValueError(f"no */cells.jsonl under {root}")
    return by_family


def first_pass_rates(
    cells_by_family: Mapping[str, Iterable[dict]],
    classes: Mapping[str, str],
) -> dict[tuple[str, str], Rates]:
    """First-pass (passes, attempts) per (family, arm), overall and per
    class. Only the training arms count; a cell naming a task absent
    from `classes` is an error — a task without a class would silently
    fall out of every per-class band."""
    acc: dict[tuple[str, str], dict] = {}
    for family, cells in cells_by_family.items():
        for c in cells:
            if c["arm"] not in TRAINING_ARMS:
                continue
            if c["task"] not in classes:
                raise ValueError(
                    f"cell for task {c['task']!r} has no class mapping"
                )
            slot = acc.setdefault((family, c["arm"]),
                                  {"passes": 0, "n": 0, "cls": {}})
            passed = int(bool(c["first_passed"]))
            slot["passes"] += passed
            slot["n"] += 1
            cp, cn = slot["cls"].get(classes[c["task"]], (0, 0))
            slot["cls"][classes[c["task"]]] = (cp + passed, cn + 1)
    return {
        key: Rates(overall=(s["passes"], s["n"]), per_class=dict(s["cls"]))
        for key, s in acc.items()
    }


def _rate(pair: tuple[int, int]) -> float:
    passes, n = pair
    return passes / n


def band_check(
    candidate: Mapping[tuple[str, str], Rates],
    reference: Mapping[tuple[str, str], Rates],
    *,
    whole_pp: float = WHOLE_BAND_PP,
    class_pp: float = CLASS_BAND_PP,
) -> GateResult:
    verdicts: list[MetricVerdict] = []
    for (family, arm) in sorted(reference):
        if (family, arm) not in candidate:
            raise ValueError(
                f"candidate has no cells for ({family!r}, {arm!r}); "
                f"an unmeasured band is not a passed band"
            )
        ref, cand = reference[(family, arm)], candidate[(family, arm)]
        verdicts.append(banded_verdict(
            f"{family}/{arm}/overall",
            _rate(cand.overall), _rate(ref.overall), whole_pp))
        for cls in sorted(ref.per_class):
            if cls not in cand.per_class:
                raise ValueError(
                    f"candidate ({family!r}, {arm!r}) has no "
                    f"{cls!r} cells; an unmeasured band is not a passed band"
                )
            verdicts.append(banded_verdict(
                f"{family}/{arm}/class:{cls}",
                _rate(cand.per_class[cls]), _rate(ref.per_class[cls]),
                class_pp))
    return GateResult(passed=all(v.passed for v in verdicts),
                      verdicts=tuple(verdicts))


def render(result: GateResult) -> str:
    lines = []
    for v in result.verdicts:
        mark = "ok  " if v.passed else "FAIL"
        lines.append(f"  {mark} {v.metric:<40} {v.measured:>7.3f}  "
                     f"band [{v.band_lo:.3f}, {v.band_hi:.3f}]  "
                     f"(reference {v.reference:.3f})")
    lines.append("difficulty band: " + ("PASS" if result.passed else "DRIFTED"))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Two-arm, per-class difficulty band: compare a "
                    "campaign's first-pass rates against the v03c "
                    "reference, both training arms, whole-corpus and "
                    "per-class.")
    parser.add_argument("candidate_root", type=Path)
    parser.add_argument("--candidate-tasks", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, default=_REFERENCE_ROOT)
    parser.add_argument("--reference-tasks", type=Path, default=_EVAL_TASKS)
    args = parser.parse_args(argv)
    result = band_check(
        first_pass_rates(load_family_cells(args.candidate_root),
                         task_classes(args.candidate_tasks)),
        first_pass_rates(load_family_cells(args.reference_root),
                         task_classes(args.reference_tasks)),
    )
    print(render(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
