"""Wave 8 Phase B endpoints, computed by command rather than by hand.

Wave 7A's eval-set numbers were produced ad-hoc and could not be
reproduced without re-deriving them; this module exists so wave 8's
cannot repeat that. It computes ONLY what the run plan pre-registers:
the drift guard, and the surplus on each task set.

Plan: docs/superpowers/plans/2026-09-01-v04-wave8-phaseb-plan.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.cost_census import EVAL_SOURCE, LARGE_SOURCE
from eval.experiment_report import (
    ReportError,
    gen_metrics,
    load_cells,
    load_cells_keyed,
    model_surplus,
)
from eval.token_match import qwen_counter

#: SPEC: base-rs-7 has read this pass@1 byte-exact in seven environments.
DRIFT_GUARD_PASS1 = 0.565
#: The plan's stop 3: below this the surplus rests on too small a sample.
MIN_PAIRS = 5


def drift_guard(arm_dir: Path) -> dict:
    """Did the environment reproduce the control?

    Reported as a verdict, never as a bare number: a run that missed the
    control is not a run whose other figures may be quoted.
    """
    metrics = gen_metrics(load_cells(arm_dir))
    pass1 = metrics["pass1"]
    return {
        "arm_dir": str(arm_dir),
        "pass1": pass1,
        "expected": DRIFT_GUARD_PASS1,
        "reproduced": pass1 == DRIFT_GUARD_PASS1,
        "n": metrics["n"],
    }


def paired_attempts(ox_keyed, rs_keyed, keys) -> dict:
    """Mean attempts-to-pass per arm over the SAME paired cells.

    `tokens_out` accumulates across repair attempts, so an arm that needs
    more repair spends more tokens for a reason that is not expression.
    The ratio-of-ratios largely cancels this, but not if the asymmetry is
    itself lopsided -- so it is reported beside the surplus rather than
    left for a reader to wonder about.
    """
    if not keys:
        return {"oxide": None, "rust": None}
    return {
        "oxide": round(
            sum(ox_keyed[k]["attempts_to_pass"] for k in keys) / len(keys), 2
        ),
        "rust": round(
            sum(rs_keyed[k]["attempts_to_pass"] for k in keys) / len(keys), 2
        ),
    }


def tier_surplus(results_root: Path, source, count) -> dict:
    """The surplus on one task set, with the sample it rests on."""
    from eval.experiment_report import green_pair_keys

    ox = load_cells_keyed(Path(results_root) / "tune-ox-7")
    rs = load_cells_keyed(Path(results_root) / "tune-rs-7")
    out = model_surplus(ox, rs, source=source, count=count)
    out["attempts"] = paired_attempts(ox, rs, green_pair_keys(ox, rs))
    n_pairs = out["model"]["n_pairs"]
    out["tier"] = source.name
    out["sufficient"] = n_pairs >= MIN_PAIRS
    if not out["sufficient"]:
        # Stop 3: the ratio is not withdrawn silently -- it is reported
        # beside the reason it cannot be leaned on.
        out["note"] = (
            f"only {n_pairs} paired green cells (< {MIN_PAIRS}); the "
            f"surplus is reported but must not be quoted as an endpoint"
        )
    return out


def build(large_root: Path, small_root: Path) -> dict:
    count = qwen_counter()
    return {
        "drift_guard": drift_guard(Path(small_root) / "base-rs-7"),
        "large": tier_surplus(large_root, LARGE_SOURCE, count),
        "small": tier_surplus(small_root, EVAL_SOURCE, count),
    }


def render(report: dict) -> str:
    g = report["drift_guard"]
    lines = [
        "# wave 8 Phase B — endpoints",
        "",
        f"Drift guard base-rs-7 pass@1 **{g['pass1']}** "
        f"(expected {g['expected']}, n={g['n']}): "
        f"**{'REPRODUCED' if g['reproduced'] else 'MISSED'}**",
        "",
        "| tier | model ox/rs | reference ox/rs | surplus | n_pairs | "
        "n_tasks | attempts ox/rs |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key in ("small", "large"):
        r = report[key]
        m, ref = r["model"], r["reference"]
        a = r["attempts"]
        lines.append(
            f"| {r['tier']} | {m['ratio']} | {ref['ratio']} | "
            f"**{r['surplus']}** | {m['n_pairs']} | {m['n_tasks']} "
            f"| {a['oxide']} / {a['rust']} |"
        )
    lines.append("")
    for key in ("small", "large"):
        if report[key].get("note"):
            lines.append(f"- **{key}**: {report[key]['note']}")
    if not g["reproduced"]:
        lines += [
            "",
            "**The control did not reproduce.** Per the run plan's stop 1 "
            "the environment is not comparable with waves 0-7, and no "
            "surplus above may be published against their numbers.",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.wave8_report")
    parser.add_argument("--large-root", type=Path, required=True)
    parser.add_argument("--small-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        report = build(args.large_root, args.small_root)
    except ReportError as exc:
        parser.error(str(exc))
    text = render(report)
    if args.out is not None:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "endpoints.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (args.out / "REPORT.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
