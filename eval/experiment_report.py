"""Pre-registered endpoints for the RunPod fine-tune experiment.

Computes ONLY what the spec registers, and refuses to run before all
twelve arms are complete — the no-interim-analysis rule is enforced
here, in code, not by convention. Censored values are None and named,
never zero (a value that looks like a measurement but is not).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.probe import summarize

ARM_NAMES = (
    "base-ox-1.5", "base-ox-7", "base-ox-14",
    "base-rs-1.5", "base-rs-7", "base-rs-14",
    "tune-ox-1.5", "tune-ox-7", "tune-ox-14",
    "tune-rs-1.5", "tune-rs-7", "tune-rs-14",
)
SIZES = ("1.5", "7", "14")


class ReportError(RuntimeError):
    """The analysis cannot honestly run; nothing is computed."""


def load_cells(arm_dir: Path) -> list[dict]:
    cells: list[dict] = []
    for path in sorted(Path(arm_dir).glob("gen-s*/cells.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cells.append(json.loads(line))
    return cells


def gen_metrics(cells: list[dict]) -> dict:
    if not cells:
        raise ReportError("no cells to score")
    n = len(cells)
    by_task: dict[str, list[dict]] = {}
    for c in cells:
        by_task.setdefault(c["task"], []).append(c)
    greens = [c for c in cells if c["final_passed"]]
    tokens = [c["tokens_out"] for c in greens]
    iters = [c["attempts_to_pass"] for c in greens]
    return {
        "n": n,
        "pass1": sum(bool(c["first_passed"]) for c in cells) / n,
        "pass10_verifier": sum(
            1 for cs in by_task.values() if any(c["final_passed"] for c in cs)
        ) / len(by_task),
        "tokens_to_green_mean": round(sum(tokens) / len(tokens), 1) if tokens else None,
        "iters_to_green_mean": round(sum(iters) / len(iters), 2) if iters else None,
        "censored_sessions": n - len(greens),
    }


def _rates_by_task(cells: list[dict]) -> dict[str, float]:
    by: dict[str, list[bool]] = {}
    for c in cells:
        by.setdefault(c["task"], []).append(bool(c["first_passed"]))
    return {t: sum(v) / len(v) for t, v in by.items()}


def paired_pass1(a_cells: list[dict], b_cells: list[dict]) -> dict:
    ta, tb = _rates_by_task(a_cells), _rates_by_task(b_cells)
    tasks = sorted(set(ta) & set(tb))
    if len(tasks) < 2:
        raise ReportError("paired delta needs >= 2 shared tasks")
    diffs = [ta[t] - tb[t] for t in tasks]
    delta = sum(diffs) / len(diffs)
    var = sum((d - delta) ** 2 for d in diffs) / (len(diffs) - 1)
    se = (var / len(diffs)) ** 0.5
    return {
        "delta_pp": round(delta * 100, 1),
        "two_se_pp": round(2 * se * 100, 1),
        "n_tasks": len(tasks),
    }


def unpaired_pass1(a_cells: list[dict], b_cells: list[dict]) -> dict:
    pa = sum(bool(c["first_passed"]) for c in a_cells) / len(a_cells)
    pb = sum(bool(c["first_passed"]) for c in b_cells) / len(b_cells)
    se = (pa * (1 - pa) / len(a_cells) + pb * (1 - pb) / len(b_cells)) ** 0.5
    return {
        "a": pa,
        "b": pb,
        "delta_pp": round((pa - pb) * 100, 1),
        "two_se_pp": round(2 * se * 100, 1),
    }


def _unpaired_binomial(a_rate: float, a_n: int, b_rate: float, b_n: int) -> dict:
    """Same 2-SE-on-two-binomials formula as `unpaired_pass1`, but starting
    from already-aggregated (rate, n) pairs rather than cell rows — the
    shape `strict_repair_rate` produces, since probe outcomes are not
    `first_passed` cells. Generic `a`/`b` keys, same as `unpaired_pass1`;
    callers relabel to named keys when the comparison has fixed roles
    (e.g. primaries' tune_ox/tune_rs)."""
    se = (a_rate * (1 - a_rate) / a_n + b_rate * (1 - b_rate) / b_n) ** 0.5
    return {
        "a": a_rate,
        "b": b_rate,
        "delta_pp": round((a_rate - b_rate) * 100, 1),
        "two_se_pp": round(2 * se * 100, 1),
    }


def _ratio_or_none(a_mean: float | None, b_mean: float | None) -> float | None:
    """`a_mean / b_mean`, rounded to 3 decimals -- or None if EITHER side
    is censored. A ratio computed against a censored (None) mean would
    look like a measurement while actually encoding "we don't know"; the
    censoring already named in `gen_metrics` must propagate here rather
    than being silently treated as a real number (or worse, as 0)."""
    if a_mean is None or b_mean is None:
        return None
    return round(a_mean / b_mean, 3)


def strict_repair_rate(probes_root: Path) -> dict:
    """Reuse eval.probe's committed scoring over the campaign cell dirs.

    `probes_root` holds one probe_campaign.py cell per (language-arm,
    seed): `<arm>-s<seed>/probe_results.jsonl`, each line one already-
    scored `eval.probe.score()` result. This function does not rescore
    anything -- it loads the persisted rows and reduces them with
    `eval.probe.summarize`, the same aggregation the campaign itself
    writes to each cell's `probe_summary.json`, just pooled over every
    seed found under `probes_root` instead of one cell at a time.
    """
    probes_root = Path(probes_root)
    results: list[dict] = []
    for results_path in sorted(probes_root.glob("*-s*/probe_results.jsonl")):
        for line in results_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                results.append(json.loads(line))
    if not results:
        raise ReportError(f"no probe cells found under {probes_root}")
    summary = summarize(results)
    arms = summary["arms"]
    if len(arms) != 1:
        raise ReportError(
            f"expected exactly one probe language-arm under {probes_root}, "
            f"found {sorted(arms)}"
        )
    (arm_summary,) = arms.values()
    return {"rate": arm_summary["strict"], "n": arm_summary["probes"]}


def require_complete(root: Path) -> None:
    missing = [a for a in ARM_NAMES if not (Path(root) / a / ".DONE").is_file()]
    if missing:
        raise ReportError(
            f"refusing to analyse: arms incomplete: {missing}. "
            f"No endpoint exists until all 12 arms are done."
        )


def build_report(root: Path) -> dict:
    require_complete(root)
    root = Path(root)
    arms = {a: gen_metrics(load_cells(root / a)) for a in ARM_NAMES}
    repair = {a: strict_repair_rate(root / a / "probes") for a in ARM_NAMES}
    primaries = {}
    for s in SIZES:
        rep = _unpaired_binomial(
            repair[f"tune-ox-{s}"]["rate"], repair[f"tune-ox-{s}"]["n"],
            repair[f"tune-rs-{s}"]["rate"], repair[f"tune-rs-{s}"]["n"],
        )
        primaries[s] = {
            "gen": paired_pass1(load_cells(root / f"tune-ox-{s}"),
                                load_cells(root / f"tune-rs-{s}")),
            # Strict repair rates come from independent probe corpora per
            # language-arm, not shared tasks -- a task-paired delta is not
            # possible across languages, so this is the unpaired-binomial
            # form (same formula as `unpaired_pass1`) over probe outcomes.
            # Relabeled from generic a/b to the fixed tune_ox/tune_rs roles
            # every size uses.
            "repair": {
                "tune_ox": rep["a"], "tune_rs": rep["b"],
                "delta_pp": rep["delta_pp"], "two_se_pp": rep["two_se_pp"],
            },
        }
    headline = {
        "gen": unpaired_pass1(load_cells(root / "tune-ox-7"),
                              load_cells(root / "base-rs-14")),
        # tune-ox-7 vs base-rs-14 is not a tune_ox/tune_rs pair -- generic
        # a/b keys, same convention as `unpaired_pass1`'s own "gen" above.
        "repair": _unpaired_binomial(
            repair["tune-ox-7"]["rate"], repair["tune-ox-7"]["n"],
            repair["base-rs-14"]["rate"], repair["base-rs-14"]["n"],
        ),
    }
    efficiency = {
        s: {
            "gen_tokens_to_green_ratio": _ratio_or_none(
                arms[f"tune-ox-{s}"]["tokens_to_green_mean"],
                arms[f"tune-rs-{s}"]["tokens_to_green_mean"],
            ),
        }
        for s in SIZES
    }
    return {
        "arms": arms,
        "repair": repair,
        "primaries": primaries,
        "headline": headline,
        "efficiency": efficiency,
        "window_trend_gen_pp": [primaries[s]["gen"]["delta_pp"] for s in SIZES],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(args.root)
    out = args.root / "ENDPOINTS.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
