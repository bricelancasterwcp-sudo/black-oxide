"""Acceptance pin: the collector reproduces the counts the spec was approved on.

These are the 2026-08-27 measured numbers (spec, 'What exists'). If this
test fails, the corpus or collector drifted — that voids the approval,
so the failure must be loud, never accommodated by editing the numbers
without a spec amendment.
"""
from eval.token_match import load_matched_inputs

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
