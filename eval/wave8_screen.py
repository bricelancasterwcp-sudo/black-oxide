"""Wave 8's 14B screen: is the cliff a 7B property or a language property?

Plan: docs/superpowers/plans/2026-09-01-v04-wave8-14b-screen-plan.md

Computes only what the plan pre-registers. The primary endpoint is a
RATIO of compile rates, not an absolute: a 14B that is simply better at
everything must not read as a rescue.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.experiment_report import ReportError, load_cells

#: Wave 4's committed cells RESTRICTED TO SEEDS 1-3. A three-seed run
#: cannot reproduce a ten-seed figure, and comparing them would be the
#: wave-6 estimand defect again. tune-ox-14 reads 0.7450 over ten seeds
#: and 0.8000 over these three.
GUARD_ANCHORS = {
    "base-rs-14": 0.5500,
    "tune-ox-14": 0.8000,
}

#: Pre-registered bands on the large-tier compile-rate ratio, ox / rs.
#: At 7B the ratio was 0.067 (5.5% vs 81.5%).
BAND_SEVEN_B = 0.50
BAND_LANGUAGE = 0.20

SEVEN_B_RATIO = 0.067


def compile_rate(arm_dir: Path) -> dict:
    """First-attempt compile rate: did the model produce a program the
    compiler accepted at all? Correctness is a separate, later question,
    and at this size it is the wrong one to lead with."""
    cells = load_cells(arm_dir)
    n = len(cells)
    compiled = sum(bool(c.get("first_compiled")) for c in cells)
    return {
        "n": n,
        "compiled": compiled,
        "rate": compiled / n if n else None,
    }


def pass1(arm_dir: Path) -> float | None:
    cells = load_cells(arm_dir)
    if not cells:
        return None
    return sum(bool(c["first_passed"]) for c in cells) / len(cells)


def guard(arm_dir: Path, arm: str) -> dict:
    """A guard reports a VERDICT. A run that missed its anchor is not a
    run whose other figures may be quoted."""
    if arm not in GUARD_ANCHORS:
        raise ReportError(f"no pre-registered anchor for {arm!r}")
    got = pass1(arm_dir)
    anchor = GUARD_ANCHORS[arm]
    return {
        "arm": arm,
        "pass1": got,
        "anchor": anchor,
        "reproduced": got == anchor,
    }


#: Wave 8's 14B large-tier baseline: 73 of 191 first diagnostics were
#: OX0001 (lexer), overwhelmingly `unexpected character '['`.
LEXER_SHARE_BASELINE = 73 / 191


def diagnostic_mix(arm_dir: Path) -> dict:
    """First diagnostic per failing attempt, counted by code.

    The FIRST one only: it is the cause, and later diagnostics on the
    same attempt are usually consequences of it. The lexer share is the
    mechanism check for SPEC 65 -- if `OX0001` stays high after `[`
    became legal, the wave-8 attribution was wrong.
    """
    counts: dict[str, int] = {}
    attempts = 0
    for path in sorted(Path(arm_dir).glob("*-gen-s*/triples.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            attempts += 1
            for diag in (json.loads(line).get("diagnostics") or [])[:1]:
                code = diag.get("code", "?")
                counts[code] = counts.get(code, 0) + 1
    total = sum(counts.values())
    return {
        "attempts": attempts,
        "failed": total,
        "codes": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "lexer_share": (counts.get("OX0001", 0) / total) if total else None,
    }


def verdict(ratio: float | None) -> str:
    """The plan's three states. 'escalate' is a real outcome, not a
    failure: the screen is allowed to decline to conclude."""
    if ratio is None:
        return "unmeasured"
    if ratio >= BAND_SEVEN_B:
        return "seven-b-property"
    if ratio <= BAND_LANGUAGE:
        return "language-property"
    return "escalate"


def screen(large_root: Path, small_root: Path) -> dict:
    guards = [
        guard(Path(small_root) / arm, arm) for arm in ("base-rs-14", "tune-ox-14")
    ]
    ox = compile_rate(Path(large_root) / "tune-ox-14")
    rs = compile_rate(Path(large_root) / "tune-rs-14")
    ratio = None
    if ox["rate"] is not None and rs["rate"]:
        ratio = round(ox["rate"] / rs["rate"], 4)
    return {
        "guards": guards,
        "guards_all_reproduced": all(g["reproduced"] for g in guards),
        "large": {"oxide": ox, "rust": rs, "compile_ratio": ratio},
        "diagnostics": diagnostic_mix(Path(large_root) / "tune-ox-14"),
        "lexer_share_baseline": round(LEXER_SHARE_BASELINE, 4),
        "seven_b_ratio": SEVEN_B_RATIO,
        "verdict": verdict(ratio),
    }


def render(report: dict) -> str:
    lines = ["# wave 8 — 14B screen (seeds 1,2,3)", ""]
    for g in report["guards"]:
        mark = "REPRODUCED" if g["reproduced"] else "MISSED"
        lines.append(
            f"- guard `{g['arm']}` pass@1 **{g['pass1']}** "
            f"(anchor {g['anchor']}, seeds 1-3): **{mark}**"
        )
    lines += ["", "| large tier | compiled | n | rate |", "|---|---:|---:|---:|"]
    for name, short in (("oxide", "ox"), ("rust", "rs")):
        c = report["large"][name]
        rate = "n/a" if c["rate"] is None else f"{c['rate']:.3f}"
        lines.append(f"| tune-{short}-14 | {c['compiled']} | {c['n']} | {rate} |")
    ratio = report["large"]["compile_ratio"]
    lines += [
        "",
        f"**compile-rate ratio ox/rs = {ratio}** "
        f"(7B: {report['seven_b_ratio']}) → **{report['verdict'].upper()}**",
        "",
    ]
    dm = report["diagnostics"]
    if dm["failed"]:
        share = dm["lexer_share"]
        lines += [
            f"Oxide first-diagnostic mix over {dm['failed']} failing "
            f"attempts: `{dm['codes']}`",
            "",
            f"**OX0001 (lexer) share {share:.3f}** "
            f"(wave 8: {report['lexer_share_baseline']:.3f})",
            "",
        ]
    if report["verdict"] == "escalate":
        lines.append(
            "Between the pre-registered bands. **Escalate to ten seeds "
            "before concluding** — the screen declines to call it."
        )
    if not report["guards_all_reproduced"]:
        lines += [
            "",
            "**A guard did not reproduce.** Per the plan the environment or "
            "the merge is suspect, and no ratio above may be published "
            "against prior waves.",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.wave8_screen")
    parser.add_argument("--large-root", type=Path, required=True)
    parser.add_argument("--small-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        report = screen(args.large_root, args.small_root)
    except ReportError as exc:
        parser.error(str(exc))
    text = render(report)
    if args.out is not None:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "screen.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (args.out / "REPORT.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
