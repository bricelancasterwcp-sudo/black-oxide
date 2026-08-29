"""Card-free prompt mode: tuned arms see no lead material anywhere.

The experiment spec's tuned arms are card-free in generation, repair
rounds, and seeded-defect probes alike; the default path must stay
byte-identical (the 1520-test suite pins most of it; the first test
pins the equality explicitly).
"""
import pytest

from eval import harness, probe
from eval.repair import build_repair_prompt


def _card(arm: str) -> str:
    return (harness._REPO_ROOT / harness.CARD_FILES[arm]).read_text(
        encoding="utf-8"
    )


def test_default_prompt_byte_identical_to_explicit_true():
    assert harness.build_prompt("oxide", "t01") == harness.build_prompt(
        "oxide", "t01", include_lead=True
    )


def test_cardfree_prompt_is_task_and_contract_only():
    task = harness.load_tasks()["t01"]
    p = harness.build_prompt("oxide", "t01", include_lead=False)
    assert p == (
        "Task:\n" + task["prompt"].rstrip("\n") + "\n\n"
        + harness.OUTPUT_CONTRACT + "\n"
    )
    assert _card("oxide")[:80] not in p


def test_cardfree_rust_prompt_drops_preamble():
    p = harness.build_prompt("rust", "t01", include_lead=False)
    assert harness.RUST_PREAMBLE.strip()[:40] not in p


def test_cardfree_shots_refused():
    with pytest.raises(harness.HarnessError):
        harness.build_prompt("oxide", "t01", shots=3, include_lead=False)


def test_cardfree_repair_prompt_retains_no_card():
    verdict = {"compiled": True, "passed": False, "stdout": "wrong\n"}
    p = build_repair_prompt(
        "oxide", "fn main() { }", verdict, task_id="t01", include_lead=False
    )
    assert _card("oxide")[:80] not in p
    assert "The program below was rejected" in p
    assert "Task:\n" in p  # the task statement itself is retained


def test_cardfree_probe_prompt():
    rec = next(r for r in probe.load_probes() if r["arm"] == "oxide")
    diags = [{"code": "OX0400", "message": "m", "line": 1, "col": 1}]
    with_card = probe.build_probe_prompt(rec, diags)
    without = probe.build_probe_prompt(rec, diags, include_card=False)
    assert probe.language_card("oxide")[:80] in with_card
    assert probe.language_card("oxide")[:80] not in without
    assert without.startswith(probe.PROBE_INSTRUCTION[:20])
