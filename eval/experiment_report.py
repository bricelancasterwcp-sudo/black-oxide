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


def _paired_rates(ra: dict[str, float], rb: dict[str, float]) -> dict:
    """The paired-delta / 2-SE construction shared by every "same
    construction as co-primary" endpoint the spec registers: match `ra`
    and `rb` by key (never by position -- two rate dicts built from
    differently-ordered inputs must still pair correctly), take per-key
    differences, and report the mean difference with a sample-SE-based
    2-SE band.

    `paired_pass1` (per-task rates) and `paired_strict_repair` (per-
    defect-class rates) both route their arithmetic through this single
    function, so "same construction" is not just a claim in a comment --
    a mutation to the shared math here breaks both callers' tests at
    once.
    """
    keys = sorted(set(ra) & set(rb))
    if len(keys) < 2:
        raise ReportError("paired delta needs >= 2 shared keys")
    diffs = [ra[k] - rb[k] for k in keys]
    delta = sum(diffs) / len(diffs)
    var = sum((d - delta) ** 2 for d in diffs) / (len(diffs) - 1)
    se = (var / len(diffs)) ** 0.5
    return {
        "delta_pp": round(delta * 100, 1),
        "two_se_pp": round(2 * se * 100, 1),
        "n": len(keys),
    }


def paired_pass1(a_cells: list[dict], b_cells: list[dict]) -> dict:
    ta, tb = _rates_by_task(a_cells), _rates_by_task(b_cells)
    result = _paired_rates(ta, tb)
    return {
        "delta_pp": result["delta_pp"],
        "two_se_pp": result["two_se_pp"],
        "n_tasks": result["n"],
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
    `first_passed` cells. Generic `a`/`b` keys, same as `unpaired_pass1`.

    Only the HEADLINE strict-repair comparison uses this. The spec
    registers "Unpaired Welch-style 2-SE" for the headline endpoint by
    choice, not because pairing across languages is impossible — it is
    not: see `paired_strict_repair` for the paired construction the spec
    registers for the repair co-primary (endpoint 1)."""
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


def load_cells_keyed(arm_dir: Path) -> dict[tuple[str, str], dict]:
    """Every cell of one arm keyed by `(seed_dir_name, task)`.

    `load_cells` flattens seeds away, which is right for whole-arm rates
    and wrong for anything paired: two arms' cells can only be matched
    if the seed survives. The key is the seed DIRECTORY name (`gen-s7`),
    not a parsed integer, so a layout that ever names seeds differently
    still pairs correctly or not at all -- never approximately.
    """
    keyed: dict[tuple[str, str], dict] = {}
    for path in sorted(Path(arm_dir).glob("gen-s*/cells.jsonl")):
        seed = path.parent.name
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cell = json.loads(line)
                keyed[(seed, cell["task"])] = cell
    return keyed


def green_pair_keys(
    a_keyed: dict[tuple[str, str], dict],
    b_keyed: dict[tuple[str, str], dict],
) -> set[tuple[str, str]]:
    """The `(seed, task)` keys present in BOTH arms and green in both."""
    return {
        key
        for key in a_keyed.keys() & b_keyed.keys()
        if a_keyed[key]["final_passed"] and b_keyed[key]["final_passed"]
    }


def paired_tokens_to_green(
    a_keyed: dict[tuple[str, str], dict],
    b_keyed: dict[tuple[str, str], dict],
    *,
    restrict_to: set[tuple[str, str]] | None = None,
) -> dict:
    """Composition-controlled token ratio between two arms (SPEC 59.7).

    `gen_metrics`'s `tokens_to_green_mean` averages over each arm's OWN
    green sessions, so the two means describe different task sets and a
    pass-rate change moves the ratio for a reason that is not token
    efficiency. This construction averages both arms over the SAME
    cells: paired by `(seed, task)`, green in both, optionally further
    restricted to `restrict_to` (the cross-wave common set).

    Returns means and ratio as None -- never 0.0 -- when no pair
    qualifies, and always reports `n_pairs` so a ratio can never be read
    without the sample it rests on.
    """
    keys = green_pair_keys(a_keyed, b_keyed)
    if restrict_to is not None:
        keys &= restrict_to
    n = len(keys)
    if n == 0:
        return {
            "n_pairs": 0,
            "n_shared": len(a_keyed.keys() & b_keyed.keys()),
            "n_tasks": 0,
            "a_mean": None,
            "b_mean": None,
            "ratio": None,
        }
    a_mean = sum(a_keyed[k]["tokens_out"] for k in keys) / n
    b_mean = sum(b_keyed[k]["tokens_out"] for k in keys) / n
    return {
        "n_pairs": n,
        "n_shared": len(a_keyed.keys() & b_keyed.keys()),
        "n_tasks": len({task for _, task in keys}),
        "a_mean": round(a_mean, 1),
        "b_mean": round(b_mean, 1),
        "ratio": _ratio_or_none(a_mean, b_mean),
    }


def _load_probe_rows(probes_root: Path) -> list[dict]:
    """Every already-scored `eval.probe.score()` result row persisted
    under `probes_root`: one probe_campaign.py cell per (language-arm,
    seed), `<arm>-s<seed>/probe_results.jsonl`. Shared by every reader of
    this on-disk layout (`strict_repair_rate`, `paired_strict_repair`) so
    there is exactly one place that knows the glob and the JSONL format --
    this never rescores anything, only reads what was already judged.
    """
    probes_root = Path(probes_root)
    results: list[dict] = []
    for results_path in sorted(probes_root.glob("*-s*/probe_results.jsonl")):
        for line in results_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                results.append(json.loads(line))
    return results


def _class_rates(results: list[dict]) -> dict[str, float]:
    """Per-defect-class strict-pass rate, pooled over every seed replicate
    of that class. The repair-side analogue of `_rates_by_task`: `defect`
    is the seeded-defect class identifier (`eval/probes.jsonl` carries
    exactly one `defect` per probe `id`, shared 1:1 across language
    arms), the way `task` identifies a generation task shared across
    arms.
    """
    by: dict[str, list[bool]] = {}
    for r in results:
        by.setdefault(r["defect"], []).append(bool(r["strict"]))
    return {d: sum(v) / len(v) for d, v in by.items()}


def paired_strict_repair(a_probes_root: Path, b_probes_root: Path) -> dict:
    """Repair's co-primary: the spec's endpoint 1 registers "Same
    construction for strict repair rate as co-primary" -- i.e. the same
    paired machinery as `paired_pass1`, over per-defect-class strict-pass
    rates instead of per-task pass rates. Routes through `_paired_rates`,
    the exact function `paired_pass1` uses, so the construction really is
    the same code, not just the same formula typed twice.

    Reuses `eval.probe`'s already-scored rows via `_load_probe_rows` --
    nothing here re-judges pass/fail. The 20 seeded-defect classes are
    shared 1:1 across the oxide/rust probe corpora (`eval/probes.jsonl`),
    so pairing on `defect` is not merely possible but exact: a mismatched
    class set between the two sides is a data-integrity fault, not
    something to quietly intersect around the way `_paired_rates` alone
    would, so it raises rather than falling back to the overlap.
    """
    a_results = _load_probe_rows(a_probes_root)
    b_results = _load_probe_rows(b_probes_root)
    if not a_results:
        raise ReportError(f"no probe cells found under {a_probes_root}")
    if not b_results:
        raise ReportError(f"no probe cells found under {b_probes_root}")
    ra, rb = _class_rates(a_results), _class_rates(b_results)
    if set(ra) != set(rb):
        raise ReportError(
            f"paired strict repair needs identical defect-class sets: "
            f"only in {a_probes_root}: {sorted(set(ra) - set(rb))}; "
            f"only in {b_probes_root}: {sorted(set(rb) - set(ra))}"
        )
    return _paired_rates(ra, rb)


def strict_repair_rate(probes_root: Path) -> dict:
    """Reuse eval.probe's committed scoring over the campaign cell dirs.

    `probes_root` holds one probe_campaign.py cell per (language-arm,
    seed): `<arm>-s<seed>/probe_results.jsonl`, each line one already-
    scored `eval.probe.score()` result. This function does not rescore
    anything -- it loads the persisted rows (via `_load_probe_rows`) and
    reduces them with `eval.probe.summarize`, the same aggregation the
    campaign itself writes to each cell's `probe_summary.json`, just
    pooled over every seed found under `probes_root` instead of one cell
    at a time.
    """
    results = _load_probe_rows(probes_root)
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


def _check_shape(cells_by_arm: dict[str, list[dict]]) -> None:
    """Every arm must be exactly 200 cells over exactly 20 distinct tasks
    -- the spec's 20 tasks x 10 seeds generation shape. A silently short
    or malformed arm (a partial run, a task that failed to enqueue, a
    seed accidentally run twice) would otherwise score as a valid but
    smaller-n result instead of the infrastructure fault it actually is.
    """
    for a, cells in cells_by_arm.items():
        n_tasks = len({c["task"] for c in cells})
        if len(cells) != 200 or n_tasks != 20:
            raise ReportError(
                f"{a}: expected exactly 200 cells over 20 tasks, found "
                f"{len(cells)} cells over {n_tasks} tasks"
            )


def build_report(root: Path, *, strict_shape: bool = True) -> dict:
    require_complete(root)
    root = Path(root)
    cells_by_arm = {a: load_cells(root / a) for a in ARM_NAMES}
    if strict_shape:
        _check_shape(cells_by_arm)
    arms = {a: gen_metrics(cells_by_arm[a]) for a in ARM_NAMES}
    repair = {a: strict_repair_rate(root / a / "probes") for a in ARM_NAMES}
    primaries = {}
    for s in SIZES:
        primaries[s] = {
            "gen": paired_pass1(cells_by_arm[f"tune-ox-{s}"],
                                cells_by_arm[f"tune-rs-{s}"]),
            # Same paired construction as "gen" above (`_paired_rates`,
            # shared with `paired_pass1`) -- the spec's endpoint 1
            # registers "Same construction for strict repair rate as
            # co-primary". Pairing IS possible here: the 20 seeded-defect
            # classes are shared 1:1 across the oxide/rust probe corpora
            # (`eval/probes.jsonl`). The HEADLINE repair comparison below
            # stays unpaired -- not because pairing across languages is
            # impossible, but because the spec explicitly registers
            # "Unpaired Welch-style 2-SE" for the headline endpoint.
            "repair": paired_strict_repair(
                root / f"tune-ox-{s}" / "probes",
                root / f"tune-rs-{s}" / "probes",
            ),
        }
    headline = {
        "gen": unpaired_pass1(cells_by_arm["tune-ox-7"],
                              cells_by_arm["base-rs-14"]),
        # tune-ox-7 vs base-rs-14 is not a tune_ox/tune_rs pair -- generic
        # a/b keys, same convention as `unpaired_pass1`'s own "gen" above.
        # Unpaired by the spec's own registered choice for the headline
        # endpoint (see the primaries loop above for the co-primary,
        # which pairs).
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


# --------------------------------------------- wave 8: the surplus estimand

def reference_ratio(tasks, source, count) -> dict:
    """The references' oxide/rust token ratio over EXACTLY these tasks.

    Restricted to a task list rather than computed over a whole tier: the
    surplus divides a model ratio by this one, and a denominator measured
    over tasks the numerator never covered is the wave-6 defect again --
    two halves of a comparison on different footings.
    """
    from eval.cost_census import pair_costs

    wanted = set(tasks)
    costs, dropped = pair_costs(count, source)
    kept = [c for c in costs if c.task in wanted]
    missing = sorted(wanted - {c.task for c in kept})
    oxide = sum(c.oxide_tokens for c in kept)
    rust = sum(c.rust_tokens for c in kept)
    return {
        "n_tasks": len(kept),
        "missing": missing,
        "dropped": dropped,
        "oxide": oxide,
        "rust": rust,
        # None, never a fabricated number, when no task qualified -- the
        # same rule PairCost.ratio applies to an empty rust arm.
        "ratio": None if rust == 0 else _ratio_or_none(oxide, rust),
    }


def model_surplus(
    ox_keyed: dict[tuple[str, str], dict],
    rs_keyed: dict[tuple[str, str], dict],
    *,
    source,
    count,
    restrict_to: set[tuple[str, str]] | None = None,
) -> dict:
    """Wave 8's pre-registered endpoint: how much more the MODEL spends
    than the language requires, on the same tasks.

    surplus = (model oxide/rust, paired per SPEC 59.7)
              / (reference oxide/rust over the tasks that paired)

    Stating it as a raw ratio was a defect the wave-8 spec was amended to
    fix: the large tier's references sit at 1.0622, so a model matching
    them exactly would score 1.0622 and read as a real surplus when its
    surplus is zero. Dividing restores the estimand wave 6 actually used
    (1.1982 / 0.9393 = 1.276).
    """
    paired = paired_tokens_to_green(ox_keyed, rs_keyed, restrict_to=restrict_to)
    keys = green_pair_keys(ox_keyed, rs_keyed)
    if restrict_to is not None:
        keys &= restrict_to
    reference = reference_ratio(sorted({task for _, task in keys}), source, count)
    return {
        "model": paired,
        "reference": reference,
        "surplus": _ratio_or_none(paired["ratio"], reference["ratio"])
        if paired["ratio"] is not None and reference["ratio"] is not None
        else None,
    }
