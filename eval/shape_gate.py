"""The pre-flight corpus-shape gate.

Origin: `eval/results/train-pilot-amp/REPORT.md`. The 40-task pilot
corpus passed all four pre-registered endpoints — every one asked "did
the factory produce enough usable programs?" — while drifting
structurally from the eval it must match: multi-line-output share 5%
against the eval's 65%, discovered only after 3,600 sessions and 14
hours of GPU. Every discriminating signature was computable in seconds
from the two `tasks.jsonl` files alone.

This module is that computation, run BEFORE authoring is accepted:
compare a candidate corpus's structural profile against the eval
corpus on four axes — multi-line-output share, mean output lines,
mean prompt length, per-class shares — and refuse the corpus if any
axis leaves its band. The GPU run stays as confirmation; it stops
being the first line of defence.

Band defaults are stated here, not scattered: ±10pp on shares, ±0.5
on mean output lines, ±25% relative on mean prompt chars. Bands are
CLOSED intervals (exactly-at-the-edge passes; `tests/test_shape_gate.py`
pins the inclusivity). A reference class absent from the candidate is
a failure (its share is 0.0, outside any band around a real share);
a candidate class absent from the reference is NOT — novel coverage
is authoring's prerogative, matching the eval's profile is the gate's.

The gate never returns a bare boolean: `GateResult.verdicts` carries
one `MetricVerdict` per axis with the measured value, the reference,
and the band it had to sit in, so a refusal names exactly what drifted
and by how much. The permanent regression anchor is the pilot corpus
itself: `eval/train/tasks.jsonl` must FAIL this gate against
`eval/tasks.jsonl` for as long as both files exist as they are.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

_EVAL_TASKS = Path(__file__).resolve().parent / "tasks.jsonl"


@dataclass(frozen=True)
class Bands:
    multi_line_share_pp: float   # absolute, on a 0..1 share
    mean_output_lines: float     # absolute, in lines
    prompt_chars_rel: float      # relative to the reference mean
    class_share_pp: float        # absolute, on a 0..1 share


DEFAULT_BANDS = Bands(
    multi_line_share_pp=0.10,
    mean_output_lines=0.5,
    prompt_chars_rel=0.25,
    class_share_pp=0.10,
)


def output_lines(stdout: str) -> int:
    """Lines of expected output. `"4\\n12\\n"` is two lines — the count
    is of lines, not newlines, and a missing trailing newline does not
    remove the final line. Empty output is zero lines. An interior
    blank line is a line: it is something the program must print."""
    lines = stdout.split("\n")
    if lines and lines[-1] == "":
        lines.pop()          # a trailing newline terminates the last line;
    return len(lines)        # it does not start an extra empty one


@dataclass(frozen=True)
class Shape:
    n: int
    multi_line_share: float
    mean_output_lines: float
    prompt_chars_mean: float
    class_shares: dict[str, float]


def corpus_shape(tasks: Iterable[dict]) -> Shape:
    rows = list(tasks)
    if not rows:
        raise ValueError("an empty corpus has no shape to measure")
    lines = [output_lines(r["expected_stdout"]) for r in rows]
    n = len(rows)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    return Shape(
        n=n,
        multi_line_share=sum(1 for x in lines if x > 1) / n,
        mean_output_lines=sum(lines) / n,
        prompt_chars_mean=sum(len(r["prompt"]) for r in rows) / n,
        class_shares={c: k / n for c, k in counts.items()},
    )


@dataclass(frozen=True)
class MetricVerdict:
    metric: str
    measured: float
    reference: float
    band_lo: float
    band_hi: float
    passed: bool


@dataclass(frozen=True)
class GateResult:
    passed: bool
    verdicts: tuple[MetricVerdict, ...]


def banded_verdict(metric: str, measured: float, reference: float,
             half_width: float) -> MetricVerdict:
    lo, hi = reference - half_width, reference + half_width
    return MetricVerdict(metric=metric, measured=measured,
                         reference=reference, band_lo=lo, band_hi=hi,
                         passed=lo <= measured <= hi)


def gate(candidate: Shape, reference: Shape,
         bands: Bands = DEFAULT_BANDS) -> GateResult:
    verdicts = [
        banded_verdict("multi_line_share", candidate.multi_line_share,
                 reference.multi_line_share, bands.multi_line_share_pp),
        banded_verdict("mean_output_lines", candidate.mean_output_lines,
                 reference.mean_output_lines, bands.mean_output_lines),
        banded_verdict("prompt_chars_mean", candidate.prompt_chars_mean,
                 reference.prompt_chars_mean,
                 reference.prompt_chars_mean * bands.prompt_chars_rel),
    ]
    for cls in sorted(reference.class_shares):
        verdicts.append(banded_verdict(
            f"class_share:{cls}",
            candidate.class_shares.get(cls, 0.0),
            reference.class_shares[cls],
            bands.class_share_pp,
        ))
    return GateResult(passed=all(v.passed for v in verdicts),
                      verdicts=tuple(verdicts))


def load_tasks(path: Path | str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines()
            if line.strip()]


def render(result: GateResult) -> str:
    lines = []
    for v in result.verdicts:
        mark = "ok  " if v.passed else "FAIL"
        lines.append(f"  {mark} {v.metric:<28} {v.measured:>8.3f}  "
                     f"band [{v.band_lo:.3f}, {v.band_hi:.3f}]  "
                     f"(reference {v.reference:.3f})")
    lines.append("gate: " + ("PASS" if result.passed else "REFUSED"))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pre-flight corpus-shape gate: refuse a task corpus "
                    "that drifts structurally from the eval, before any "
                    "GPU is spent.")
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--reference", type=Path, default=_EVAL_TASKS)
    args = parser.parse_args(argv)
    result = gate(corpus_shape(load_tasks(args.candidate)),
                  corpus_shape(load_tasks(args.reference)))
    print(render(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
