"""Campaign driver: 12-arm table, card-free plumbing, rerun-from-zero."""
import json
from pathlib import Path

from eval import harness, probe_campaign
from eval.exp_campaign import ARM_SPECS, SEEDS, TEMPERATURE, run_arm
from eval.experiment_report import ARM_NAMES
from eval.models import Generation


def test_arm_specs_table():
    assert len(ARM_SPECS) == 12
    assert tuple(s.name for s in ARM_SPECS) == ARM_NAMES
    assert len({s.gguf for s in ARM_SPECS}) == 9  # base ggufs serve 2 arms
    for s in ARM_SPECS:
        if s.name.startswith("tune-"):
            assert s.include_lead is False
        else:
            assert s.include_lead is True
        assert s.arm == ("oxide" if "-ox-" in s.name else "rust")
    assert SEEDS == tuple(range(1, 11))
    assert TEMPERATURE == 0.2


class FakeClient:
    """Answers every prompt with one fixed reply; records the prompts."""

    def __init__(self, reply: str):
        self.reply = reply
        self.prompts: list[str] = []

    def generate(self, prompt: str, *, seed: int) -> Generation:
        self.prompts.append(prompt)
        return Generation(text=self.reply, tokens_in=10, tokens_out=5,
                          ms=1, truncated=False)


def _one_task_file(tmp_path: Path) -> Path:
    task = harness.load_tasks()["t01"]
    p = tmp_path / "tasks.jsonl"
    p.write_text(json.dumps(task) + "\n", encoding="utf-8")
    return p


def _passing_reply() -> str:
    src = Path("eval/solutions/oxide/t01.ox").read_text(encoding="utf-8")
    return f"```\n{src}\n```"


def _card(arm: str) -> str:
    return (harness._REPO_ROOT / harness.CARD_FILES[arm]).read_text(
        encoding="utf-8"
    )


def test_run_arm_cardfree_end_to_end(tmp_path):
    spec = next(s for s in ARM_SPECS if s.name == "tune-ox-7")
    client = FakeClient(_passing_reply())
    tasks_path = _one_task_file(tmp_path)
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=tasks_path, seeds=(1,), families=("gen",),
            client=client)
    arm = tmp_path / "exp" / "tune-ox-7"
    cells = [json.loads(l) for l in
             (arm / "gen-s1" / "cells.jsonl").read_text().splitlines()]
    assert len(cells) == 1 and cells[0]["first_passed"] is True
    assert (arm / ".DONE").is_file()
    card = _card("oxide")
    for prompt in client.prompts:
        assert card[:80] not in prompt


def test_run_arm_baseline_prompt_has_card(tmp_path):
    spec = next(s for s in ARM_SPECS if s.name == "base-ox-7")
    client = FakeClient(_passing_reply())
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=_one_task_file(tmp_path), seeds=(1,),
            families=("gen",), client=client)
    card = _card("oxide")
    assert card[:80] in client.prompts[0]


def test_run_arm_reruns_from_zero(tmp_path):
    spec = next(s for s in ARM_SPECS if s.name == "tune-ox-7")
    arm = tmp_path / "exp" / "tune-ox-7"
    (arm / "gen-s1").mkdir(parents=True)
    (arm / "gen-s1" / "cells.jsonl").write_text("JUNK\n", encoding="utf-8")
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=_one_task_file(tmp_path), seeds=(1,),
            families=("gen",), client=FakeClient(_passing_reply()))
    cells = (arm / "gen-s1" / "cells.jsonl").read_text(encoding="utf-8")
    assert "JUNK" not in cells  # the junk arm dir was wiped, not resumed


def test_run_arm_done_is_idempotent(tmp_path):
    spec = next(s for s in ARM_SPECS if s.name == "tune-ox-7")
    arm = tmp_path / "exp" / "tune-ox-7"
    arm.mkdir(parents=True)
    (arm / ".DONE").write_text("")
    client = FakeClient(_passing_reply())
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=_one_task_file(tmp_path), seeds=(1,),
            families=("gen",), client=client)
    assert client.prompts == []


def test_repair_rounds_stay_cardfree(tmp_path):
    """Task 2's known gap, closed permanently: a tuned arm's REPAIR round
    (not just its initial prompt) must never carry the language card.
    A non-passing reply forces at least one repair round to fire, and the
    card must be absent from every prompt including the repair prompt at
    index 1."""
    spec = next(s for s in ARM_SPECS if s.name == "tune-ox-7")
    client = FakeClient("```\nfn main() { broken\n```")
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=_one_task_file(tmp_path), seeds=(1,),
            families=("gen",), client=client)
    card = _card("oxide")
    assert len(client.prompts) > 1  # repair round(s) actually fired
    for prompt in client.prompts:
        assert card[:80] not in prompt


def test_run_arm_extra_provenance_merged(tmp_path):
    """--gguf-sha / --llamacpp-commit (threaded through as
    `extra_provenance`) must land in provenance.json alongside the
    fields `run_arm` always records itself -- not replace them."""
    spec = next(s for s in ARM_SPECS if s.name == "tune-ox-7")
    client = FakeClient(_passing_reply())
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=_one_task_file(tmp_path), seeds=(1,),
            families=("gen",), client=client,
            extra_provenance={"gguf_sha256": "x"})
    provenance = json.loads(
        (tmp_path / "exp" / "tune-ox-7" / "provenance.json").read_text()
    )
    assert provenance["gguf_sha256"] == "x"
    assert provenance["name"] == "tune-ox-7"  # existing fields untouched


def test_run_arm_extra_provenance_none_default_unchanged(tmp_path):
    """None (the default) must not add or remove anything from
    provenance.json -- existing callers are untouched."""
    spec = next(s for s in ARM_SPECS if s.name == "tune-ox-7")
    client = FakeClient(_passing_reply())
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=_one_task_file(tmp_path), seeds=(1,),
            families=("gen",), client=client)
    provenance = json.loads(
        (tmp_path / "exp" / "tune-ox-7" / "provenance.json").read_text()
    )
    assert "gguf_sha256" not in provenance
    assert "llamacpp_commit" not in provenance


def test_run_arm_cardfree_probes_end_to_end(tmp_path):
    """include_card=False threading from run_arm through
    probe_campaign.run_campaign -> run_corpus -> build_probe_prompt, proven
    end to end across BOTH families in one run: the card must be absent
    from every recorded prompt, generation and probes alike, and the
    probes cell directory must actually have been created (real diagnose
    against the corpus, real rustc, no stubbing of the oracle)."""
    spec = next(s for s in ARM_SPECS if s.name == "tune-ox-7")
    client = FakeClient(_passing_reply())
    tasks_path = _one_task_file(tmp_path)
    run_arm(spec, host="http://unused", results_root=tmp_path / "exp",
            tasks_path=tasks_path, seeds=(1,), families=("gen", "probes"),
            client=client)
    arm = tmp_path / "exp" / "tune-ox-7"
    assert (arm / ".DONE").is_file()
    probes_cell = probe_campaign.cell_dir(arm / "probes", spec.arm, 1)
    assert probes_cell.is_dir()
    assert (probes_cell / "probe_summary.json").is_file()
    card = _card("oxide")
    assert client.prompts  # sanity: something was actually recorded
    for prompt in client.prompts:
        assert card[:80] not in prompt


# ------------------------------------------- wave 8: task set and families

def test_cli_passes_the_tasks_file_and_families_through(monkeypatch, tmp_path):
    """Wave 8 runs the large tier through the same arms, and needs only
    the gen family. Both were reachable in run_arm and unreachable from
    the CLI, which is why wave 7A's numbers were computed by hand."""
    import eval.exp_campaign as ec

    seen = {}

    def fake_run_arm(spec, **kwargs):
        seen["spec"] = spec.name
        seen.update(kwargs)

    monkeypatch.setattr(ec, "run_arm", fake_run_arm)
    ec.main([
        "--arm", "tune-ox-7", "--root", str(tmp_path),
        "--tasks", "eval/tasks-large.jsonl", "--families", "gen",
    ])
    assert seen["spec"] == "tune-ox-7"
    assert str(seen["tasks_path"]) == "eval/tasks-large.jsonl"
    assert seen["families"] == ("gen",)
    assert seen["extra_provenance"]["tasks_path"] == "eval/tasks-large.jsonl"


def test_cli_defaults_keep_the_previous_behaviour(monkeypatch, tmp_path):
    """Every earlier wave ran without these flags; their meaning must not
    move underneath a re-run."""
    import eval.exp_campaign as ec

    seen = {}
    monkeypatch.setattr(ec, "run_arm", lambda spec, **kw: seen.update(kw))
    ec.main(["--arm", "base-rs-7", "--root", str(tmp_path)])
    assert seen["tasks_path"] is None
    assert seen["families"] == ("gen", "probes")


def test_cli_rejects_an_unknown_family_instead_of_silently_running_none():
    import eval.exp_campaign as ec
    import pytest as _pytest

    with _pytest.raises(SystemExit):
        ec.main(["--arm", "base-rs-7", "--root", "/tmp/x", "--families", "genn"])


def test_cli_accepts_a_seed_subset_and_records_it(monkeypatch, tmp_path):
    """A subset run is NOT comparable with a published ten-seed figure --
    wave 4's tune-ox-14 reads 0.745 over ten seeds and 0.800 over seeds
    1-3. The subset must therefore be recorded in provenance, so no later
    reader can mistake one for the other."""
    import eval.exp_campaign as ec

    seen = {}
    monkeypatch.setattr(ec, "run_arm", lambda spec, **kw: seen.update(kw))
    ec.main(["--arm", "tune-ox-14", "--root", str(tmp_path), "--seeds", "1,2,3"])
    assert seen["seeds"] == (1, 2, 3)
    assert seen["extra_provenance"]["seeds_subset"] == [1, 2, 3]


def test_cli_default_seeds_are_the_full_set_and_unrecorded(monkeypatch, tmp_path):
    import eval.exp_campaign as ec

    seen = {}
    monkeypatch.setattr(ec, "run_arm", lambda spec, **kw: seen.update(kw))
    ec.main(["--arm", "tune-ox-14", "--root", str(tmp_path)])
    assert seen["seeds"] == ec.SEEDS
    assert "seeds_subset" not in (seen["extra_provenance"] or {})


def test_cli_rejects_a_seed_outside_the_campaign_set():
    import eval.exp_campaign as ec
    import pytest as _pytest

    with _pytest.raises(SystemExit):
        ec.main(["--arm", "tune-ox-14", "--root", "/tmp/x", "--seeds", "1,99"])


def test_cli_rejects_non_integer_seeds():
    import eval.exp_campaign as ec
    import pytest as _pytest

    with _pytest.raises(SystemExit):
        ec.main(["--arm", "tune-ox-14", "--root", "/tmp/x", "--seeds", "a,b"])
