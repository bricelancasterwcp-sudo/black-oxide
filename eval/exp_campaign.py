"""Drive one experiment arm against a llama-server: generation + probes.

The spec's serving rules live here: pinned sampler, unconstrained
decoding, identity preflight before any scored session, rerun-from-zero
for interrupted arms, `.DONE` as the only completion marker.
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from eval import harness, probe_campaign
from eval.driver import run_session
from eval.llamacpp import LlamaCppClient
from eval.models import ModelError

SEEDS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
TEMPERATURE = 0.2
TOP_P = 0.95
NUM_CTX = 8192
NUM_PREDICT = 2048


@dataclass(frozen=True, slots=True)
class ArmSpec:
    name: str
    gguf: str
    arm: str
    include_lead: bool


def _specs() -> tuple[ArmSpec, ...]:
    rows: list[ArmSpec] = []
    for kind in ("base", "tune"):
        for lang, arm in (("ox", "oxide"), ("rs", "rust")):
            for size in ("1.5", "7", "14"):
                name = f"{kind}-{lang}-{size}"
                gguf = (f"base-{size}.q8_0.gguf" if kind == "base"
                        else f"{name}.q8_0.gguf")
                rows.append(ArmSpec(name, gguf, arm, kind == "base"))
    order = {n: i for i, n in enumerate((
        "base-ox-1.5", "base-ox-7", "base-ox-14",
        "base-rs-1.5", "base-rs-7", "base-rs-14",
        "tune-ox-1.5", "tune-ox-7", "tune-ox-14",
        "tune-rs-1.5", "tune-rs-7", "tune-rs-14",
    ))}
    return tuple(sorted(rows, key=lambda s: order[s.name]))


ARM_SPECS = _specs()


def make_client(spec: ArmSpec, host: str) -> LlamaCppClient:
    return LlamaCppClient(
        model=spec.gguf, grammar=None, temperature=TEMPERATURE,
        top_p=TOP_P, num_predict=NUM_PREDICT, num_ctx=NUM_CTX, host=host,
    )


def identity_preflight(client: LlamaCppClient, spec: ArmSpec) -> dict:
    props = client.props()
    path = props.get("model_path")
    if not isinstance(path, str) or not path.endswith(spec.gguf):
        raise ModelError(
            f"{spec.name}: server serves {path!r}, expected a path ending "
            f"in {spec.gguf!r} -- wrong weights, refusing to measure"
        )
    client.preflight()
    return {"model_path": path}


def run_arm(
    spec: ArmSpec,
    *,
    host: str,
    results_root: Path,
    tasks_path: Path | None = None,
    seeds: tuple[int, ...] = SEEDS,
    families: tuple[str, ...] = ("gen", "probes"),
    client: object | None = None,
    extra_provenance: dict | None = None,
) -> None:
    arm_dir = Path(results_root) / spec.name
    if (arm_dir / ".DONE").is_file():
        return
    if arm_dir.exists():
        shutil.rmtree(arm_dir)  # interrupted arm: rerun from zero, never splice
    arm_dir.mkdir(parents=True)
    provenance: dict = {
        **asdict(spec),
        "temperature": TEMPERATURE, "top_p": TOP_P,
        "num_ctx": NUM_CTX, "num_predict": NUM_PREDICT,
        "seeds": list(seeds), "families": list(families),
    }
    if client is None:
        client = make_client(spec, host)
        provenance["identity"] = identity_preflight(client, spec)
    if extra_provenance:
        # Caller-supplied provenance (e.g. --gguf-sha / --llamacpp-commit
        # from the pod wrapper) merged in last: it augments, never
        # replaces, the fields this function always records itself.
        provenance.update(extra_provenance)
    (arm_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if "gen" in families:
        tasks = harness.load_tasks(tasks_path)
        for seed in seeds:
            run_dir = arm_dir / f"gen-s{seed}"
            cells_path = run_dir / "cells.jsonl"
            for task_id in sorted(tasks):
                cell = run_session(
                    client, run_id=f"{spec.name}-gen-s{seed}",
                    task_id=task_id, arm=spec.arm, shots=0,
                    results_root=arm_dir, raw_dir=run_dir / "raw",
                    tasks_path=tasks_path, seed=seed,
                    include_lead=spec.include_lead,
                )
                cells_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cells_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(cell, sort_keys=True) + "\n")
    if "probes" in families:
        probe_campaign.run_campaign(
            arm_dir / "probes", (spec.arm,), seeds,
            client_factory=lambda arm: client,
            provenance=provenance,
            include_card=spec.include_lead,
        )
    (arm_dir / ".DONE").write_text("")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True,
                        choices=[s.name for s in ARM_SPECS])
    parser.add_argument("--host", default="http://127.0.0.1:8081")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--gguf-sha", default=None,
        help="sha256 of the served GGUF; recorded in provenance.json",
    )
    parser.add_argument(
        "--llamacpp-commit", default=None,
        help="llama.cpp commit the server was built from; recorded in "
             "provenance.json",
    )
    parser.add_argument(
        "--tasks", type=Path, default=None,
        help="tasks file to generate against (default: the eval corpus). "
             "Wave 8 runs the large tier through the same arms.",
    )
    parser.add_argument(
        "--families", default="gen,probes",
        help="comma-separated families to run. Wave 8's token-efficiency "
             "endpoint needs only 'gen'.",
    )
    parser.add_argument(
        "--seeds", default=None,
        help="comma-separated seeds (default: all ten). A SUBSET run is "
             "not comparable with a published ten-seed figure -- anchor it "
             "on the same seeds, restricted from committed cells.",
    )
    args = parser.parse_args(argv)
    families = tuple(f for f in args.families.split(",") if f)
    unknown = set(families) - {"gen", "probes"}
    if unknown:
        parser.error(f"unknown families: {sorted(unknown)}")
    if args.seeds is None:
        seeds = SEEDS
    else:
        try:
            seeds = tuple(int(s) for s in args.seeds.split(",") if s)
        except ValueError:
            parser.error(f"seeds must be integers: {args.seeds!r}")
        if not seeds:
            parser.error("--seeds given but empty")
        stray = sorted(set(seeds) - set(SEEDS))
        if stray:
            parser.error(f"seeds outside the campaign set {SEEDS}: {stray}")
    spec = next(s for s in ARM_SPECS if s.name == args.arm)
    extra_provenance: dict = {}
    if args.gguf_sha is not None:
        extra_provenance["gguf_sha256"] = args.gguf_sha
    if args.llamacpp_commit is not None:
        extra_provenance["llamacpp_commit"] = args.llamacpp_commit
    if args.tasks is not None:
        extra_provenance["tasks_path"] = str(args.tasks)
    if seeds != SEEDS:
        extra_provenance["seeds_subset"] = list(seeds)
    run_arm(spec, host=args.host, results_root=args.root,
            tasks_path=args.tasks, families=families, seeds=seeds,
            extra_provenance=extra_provenance or None)
    print(f"{spec.name}: DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
