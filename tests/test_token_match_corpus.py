"""Acceptance pin: the collector reproduces the counts the spec was approved on.

These are the 2026-08-27 measured numbers (spec, 'What exists'). If this
test fails, the corpus or collector drifted — that voids the approval,
so the failure must be loud, never accommodated by editing the numbers
without a spec amendment.
"""
import hashlib
import json

from eval.token_match import (
    ARMS,
    MATCHED_DIR,
    load_matched_inputs,
    qwen_counter,
    token_efficiency,
)
from eval.tokenizer_pin import TOKENIZER_FILE
from eval.train_corpus import contamination_report, load_train_tasks

APPROVED_COUNTS = {
    "oxide": {"arithmetic/loops": 93, "strings": 10, "structs/option": 78, "vectors": 30},
    "rust": {"arithmetic/loops": 139, "strings": 67, "structs/option": 62, "vectors": 103},
}


def test_amplified_counts_match_spec_approval():
    tasks, references, amplified = load_matched_inputs()
    counts = {"oxide": {}, "rust": {}}
    for (task, arm), progs in amplified.items():
        cls = tasks[task]["class"]
        counts[arm][cls] = counts[arm].get(cls, 0) + len(progs)
    assert counts == APPROVED_COUNTS
    assert sum(counts["oxide"].values()) == 211
    assert sum(counts["rust"].values()) == 371


def test_references_present_for_all_40_tasks():
    tasks, references, amplified = load_matched_inputs()
    assert len(tasks) == 40
    for tid in tasks:
        assert (tid, "oxide") in references
        assert (tid, "rust") in references


def _manifest():
    return json.loads((MATCHED_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_qwen_counter_includes_terminator():
    count = qwen_counter()
    base = count("fn main() {}")
    assert base >= 2  # at least one content token + the terminator
    assert count("") == 1  # terminator only


def test_token_efficiency_covers_both_sources_and_overall():
    tasks, references, amplified = load_matched_inputs()
    eff = token_efficiency(tasks, references, amplified, lambda s: len(s.split()) + 1)
    for section in ("references", "amplified"):
        assert "overall" in eff[section]
        for cls in {t["class"] for t in tasks.values()} | {"overall"}:
            for arm in ARMS:
                cell = eff[section][cls][arm]
                assert set(cell) == {"n", "mean_sup_tokens"}
                assert cell["n"] > 0 or section == "amplified"


def test_committed_manifest_pin_matches_provenance():
    manifest = _manifest()
    file_hash = hashlib.sha256(TOKENIZER_FILE.read_bytes()).hexdigest()
    assert manifest["tokenizer"]["sha256"] == file_hash


def test_committed_matched_corpus_is_uncontaminated():
    tasks = load_train_tasks()
    programs = {}
    for arm in ARMS:
        for line in (MATCHED_DIR / f"{arm}.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            programs[f"{arm}/{row['task']}/{row['sha256'][:12]}"] = row["text"]
    assert contamination_report(tasks, programs) == ()
    assert _manifest()["contamination"]["hits"] == 0
    assert _manifest()["contamination"]["programs_checked"] == len(programs)


def test_committed_matched_corpus_has_one_reference_per_task_both_arms():
    """References are never trimmed (spec decision 5): each arm's committed
    matched/{arm}.jsonl must carry exactly 40 reference rows, one per task
    in tasks.jsonl. A filter that strikes a reference whenever it shares
    (task, sha256) with a dropped amplified program silently loses rows
    here without failing any other guard — this is the enforcement.
    """
    tasks = load_train_tasks()
    assert len(tasks) == 40
    for arm in ARMS:
        rows = [json.loads(line) for line in
                (MATCHED_DIR / f"{arm}.jsonl").read_text(encoding="utf-8").splitlines()]
        ref_tasks = [r["task"] for r in rows if r["source"] == "reference"]
        assert len(ref_tasks) == 40
        assert set(ref_tasks) == set(tasks)


def test_committed_budgets_hold():
    manifest = _manifest()
    for row in manifest["classes"]:
        kept = row["kept_tokens"]
        assert max(kept.values()) == row["budget"]
        assert row["gap"] == max(kept.values()) - min(kept.values())
        assert row["gap"] <= row["quantization_step"]
    # dropped-list integrity: dropped + kept tokens reconstruct the
    # surplus arm's pre-trim totals per class, cross-checked from inputs
    tasks, references, amplified = load_matched_inputs()
    count = qwen_counter()
    from eval.token_match import build_matched
    rebuilt = build_matched(tasks, references, amplified, count)
    assert [
        {"class": b.cls, "budget": b.budget, "kept_tokens": b.kept_tokens,
         "kept_examples": b.kept_examples, "gap": b.gap,
         "quantization_step": b.quantization_step}
        for b in rebuilt.budgets
    ] == manifest["classes"]
