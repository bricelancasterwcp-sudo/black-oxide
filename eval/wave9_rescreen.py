"""Wave 9's re-screen: does shipping `[` move the large-tier compile rate?

Plan: docs/superpowers/plans/2026-09-02-v04-wave9-rescreen-plan.md

The run is wave 8's 14B screen with nothing changed but the language --
same arms, seeds 1-3, seed-matched anchors, unchanged v5 adapters. So
the measurement is wave 8's `screen()`; what is new is the READING. Wave
9 pre-registered bands on the compile-rate ratio that decide the method
(one construct at a time, or the slate together), and a mechanism check
on the lexer share. Both are computed here and nowhere else.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.experiment_report import ReportError
from eval.wave8_screen import LEXER_SHARE_BASELINE, screen

#: Wave 8's 14B screen, seeds 1-3: 5.0% / 76.7%. Pinned to the committed
#: cells by tests/test_wave9_rescreen.py.
BASELINE_RATIO = 0.0652

#: Pre-registered bands on the large-tier compile-rate ratio, ox / rs.
#: >= BAND_REAL: indexing was a real binding constraint; one construct at a
#: time works. [BAND_PARTIAL, BAND_REAL): real but shallow; re-rank before
#: the next. < BAND_PARTIAL: removing one barrier exposed the next; ship
#: the ranked slate together or accept the gap is not closable by vocabulary.
BAND_REAL = 0.20
BAND_PARTIAL = 0.12

#: The mechanism check. A CHOSEN number (marked as such in the plan's
#: 11:55 UTC amendment): if `[` was the dominant lexer cause, the OX0001
#: share of first diagnostics should fall below this once `[` is legal.
LEXER_SHARE_CONFIRMED_BELOW = 0.15


def reading(ratio: float | None) -> str:
    if ratio is None:
        return "unmeasured"
    if ratio >= BAND_REAL:
        return "binding-constraint"
    if ratio >= BAND_PARTIAL:
        return "partial"
    return "next-barrier"


def mechanism(lexer_share: float | None) -> str:
    if lexer_share is None:
        return "unmeasured"
    if lexer_share < LEXER_SHARE_CONFIRMED_BELOW:
        return "attribution-confirmed"
    return "attribution-wrong"


def rescreen(large_root: Path, small_root: Path) -> dict:
    base = screen(Path(large_root), Path(small_root))
    # wave8_screen.verdict() applies WAVE 8's bands (0.50 / 0.20). Kept for
    # the record, renamed so it cannot be read as this run's verdict.
    base["wave8_band_verdict"] = base.pop("verdict")
    ratio = base["large"]["compile_ratio"]
    share = base["diagnostics"]["lexer_share"]
    guards_ok = base["guards_all_reproduced"]
    base["wave9"] = {
        "baseline_ratio": BASELINE_RATIO,
        "ratio": ratio,
        # Stop 1: a missed guard publishes no ratio against wave 8.
        "delta": round(ratio - BASELINE_RATIO, 4) if (guards_ok and ratio is not None) else None,
        "reading": reading(ratio) if guards_ok else "guards-missed",
        "lexer_share_baseline": round(LEXER_SHARE_BASELINE, 4),
        "lexer_share": share,
        "mechanism": mechanism(share),
        "bands": {"real": BAND_REAL, "partial": BAND_PARTIAL,
                  "lexer_confirmed_below": LEXER_SHARE_CONFIRMED_BELOW},
    }
    return base


def render(report: dict) -> str:
    w9 = report["wave9"]
    lines = ["# wave 9 — re-screen (seeds 1,2,3), read against wave 8", ""]
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
    lines += [
        "",
        f"**compile-rate ratio ox/rs = {w9['ratio']}** "
        f"(wave 8: {w9['baseline_ratio']}; delta {w9['delta']}) → "
        f"**{w9['reading'].upper()}**",
        "",
    ]
    dm = report["diagnostics"]
    if dm["failed"]:
        lines += [
            f"Oxide first-diagnostic mix over {dm['failed']} failing "
            f"attempts: `{dm['codes']}`",
            "",
            f"**OX0001 (lexer) share {w9['lexer_share']:.3f}** "
            f"(wave 8: {w9['lexer_share_baseline']:.3f}; confirmed if < "
            f"{w9['bands']['lexer_confirmed_below']}) → "
            f"**{w9['mechanism'].upper()}**",
            "",
        ]
    if not report["guards_all_reproduced"]:
        lines += [
            "",
            "**A guard did not reproduce.** Per stop 1 the environment or the "
            "merge is suspect, and NO RATIO above may be published against "
            "wave 8; it is printed for the record only.",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.wave9_rescreen")
    parser.add_argument("--large-root", type=Path, required=True)
    parser.add_argument("--small-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        report = rescreen(args.large_root, args.small_root)
    except ReportError as exc:
        parser.error(str(exc))
    text = render(report)
    if args.out is not None:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "rescreen.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (args.out / "SCREEN.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
