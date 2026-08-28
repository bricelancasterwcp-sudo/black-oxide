"""Invariants of the matched-corpus builder (spec 2026-08-27).

All tests use a word-count token counter so the core is exercised
without the real tokenizer; Task 5 adds the real-counter path.
"""
import json

import pytest

from eval.token_match import (
    ARMS,
    Example,
    MANIFEST_KEYS,
    MatchError,
    build_matched,
    sha256_hex,
    write_matched,
)


def words(text: str) -> int:
    return len(text.split()) + 1  # +1 mirrors the real counter's terminator


def corpus():
    """Two classes; rust surplus in 'alpha', oxide surplus in 'beta'.

    'beta' carries two tasks (n003, n004) with four oxide-arm amplified
    candidates of uneven size so that trimming stops partway through the
    candidate list. That partial trim is what makes the class able to
    tell a (sha256, task)-ordered removal apart from any other removal
    order: with only one or two tasks and a trim that always empties the
    whole candidate list (as with 'alpha' and a single-task 'beta'),
    every removal order reaches the same end state and the order is
    unobservable. See test_trim_order_is_hash_order.

    n004's oxide amplified set also includes "fn main() { d }" —
    byte-identical (same normalized text, same sha256) to n004's own
    oxide reference. It sorts last among the beta/oxide candidates by
    sha256, so trimming reaches and removes it: (task="n004", sha256)
    lands in `removed` while a reference row with that exact (task,
    sha256) also exists. A filter that keys removal on (task, sha256)
    alone — instead of also requiring source == "amplified" — strikes
    the reference too. See test_references_survive_every_task_both_arms.
    """
    tasks = {
        "n001": {"class": "alpha", "prompt": "add two numbers"},
        "n002": {"class": "alpha", "prompt": "sum a vector"},
        "n003": {"class": "beta", "prompt": "greet a name"},
        "n004": {"class": "beta", "prompt": "wave at someone"},
    }
    references = {
        ("n001", "oxide"): "fn main() { a }",
        ("n001", "rust"): "fn main() { a }",
        ("n002", "oxide"): "fn main() { b }",
        ("n002", "rust"): "fn main() { b }",
        ("n003", "oxide"): "fn main() { c }",
        ("n003", "rust"): "fn main() { c }",
        ("n004", "oxide"): "fn main() { d }",
        ("n004", "rust"): "fn main() { d }",
    }
    amplified = {
        ("n001", "oxide"): {"one two three"},
        ("n001", "rust"): {"one two three four", "five six seven eight nine"},
        ("n002", "rust"): {"ten eleven twelve thirteen"},
        ("n003", "oxide"): {"a b c d e f g h", "i j k l m n"},
        ("n003", "rust"): {"o p q"},
        ("n004", "oxide"): {"red", "blue", "fn main() { d }"},
    }
    return tasks, references, amplified


def test_budget_invariant_and_symmetric_surplus():
    tasks, references, amplified = corpus()
    result = build_matched(tasks, references, amplified, words)
    for b in result.budgets:
        # the budget-setting arm keeps everything (== budget); the
        # trimmed arm ends at or below it
        assert max(b.kept_tokens.values()) == b.budget
        assert min(b.kept_tokens.values()) <= b.budget
        assert b.gap == b.budget - min(b.kept_tokens.values())
        assert b.gap <= b.quantization_step
    # surplus direction differs by class: alpha trims rust, beta trims oxide
    dropped_arms = {(d.cls, d.arm) for d in result.dropped}
    assert ("alpha", "rust") in dropped_arms
    assert ("beta", "oxide") in dropped_arms


def test_references_survive_every_task_both_arms():
    tasks, references, amplified = corpus()
    result = build_matched(tasks, references, amplified, words)
    for arm in ARMS:
        ref_tasks = {e.task for e in result.kept[arm] if e.source == "reference"}
        assert ref_tasks == set(tasks)


def test_determinism_under_input_reordering():
    tasks, references, amplified = corpus()
    a = build_matched(tasks, references, amplified, words)
    reordered_tasks = dict(reversed(list(tasks.items())))
    reordered_amp = {k: set(sorted(v, reverse=True)) for k, v in reversed(list(amplified.items()))}
    b = build_matched(reordered_tasks, dict(reversed(list(references.items()))), reordered_amp, words)
    assert a == b


def test_trim_order_is_hash_order():
    tasks, references, amplified = corpus()
    result = build_matched(tasks, references, amplified, words)
    for cls in {"alpha", "beta"}:
        drops = [d for d in result.dropped if d.cls == cls]
        assert drops == sorted(drops, key=lambda d: (d.sha256, d.task))
        if not drops:
            continue
        # Membership, not just display order: the final `dropped` tuple is
        # unconditionally re-sorted by (sha256, task) before it's returned
        # (needed for determinism — see test_determinism_under_input_reordering),
        # so the assertion above holds no matter which items were actually
        # selected for removal. To catch a mutation to the *selection* order
        # itself, confirm the removed set is exactly the shortest leading
        # prefix of all candidates sorted by (sha256, task) — i.e. trimming
        # really did stop at the cheapest-by-hash items, not merely display
        # them that way afterward.
        arm = drops[0].arm
        all_candidates = sorted(
            (sha256_hex(text), task)
            for (task, a), texts in amplified.items()
            if a == arm and tasks[task]["class"] == cls
            for text in texts
        )
        prefix = set(all_candidates[: len(drops)])
        assert {(d.sha256, d.task) for d in drops} == prefix


def test_missing_reference_fails_closed():
    tasks, references, amplified = corpus()
    del references[("n002", "rust")]
    with pytest.raises(MatchError, match="n002"):
        build_matched(tasks, references, amplified, words)


def test_references_exceeding_budget_fail_closed():
    tasks = {"n009": {"class": "gamma", "prompt": "p"}}
    references = {
        ("n009", "oxide"): "tiny",
        ("n009", "rust"): "very long reference " * 20,
    }
    with pytest.raises(MatchError, match="gamma"):
        build_matched(tasks, references, {}, words)


def test_prompt_tokens_reported_per_arm():
    tasks, references, amplified = corpus()
    result = build_matched(tasks, references, amplified, words)
    for arm in ARMS:
        expected = sum(words(tasks[e.task]["prompt"]) for e in result.kept[arm])
        assert result.prompt_tokens[arm] == expected


def build_and_write(tmp_path):
    tasks, references, amplified = corpus()
    result = build_matched(tasks, references, amplified, words)
    write_matched(
        tmp_path,
        result,
        tokenizer={"id": "test", "sha256": "0" * 64},
        counts_source={"roots": ["r1"], "commit": "abc"},
        contamination={"hits": 0, "programs_checked": 9},
        token_efficiency={"references": {}, "amplified": {}},
    )
    return result


def test_write_is_byte_deterministic(tmp_path):
    a_dir, b_dir = tmp_path / "a", tmp_path / "b"
    a_dir.mkdir(); b_dir.mkdir()
    tasks, references, amplified = corpus()
    kwargs = dict(
        tokenizer={"id": "test", "sha256": "0" * 64},
        counts_source={"roots": ["r1"], "commit": "abc"},
        contamination={"hits": 0, "programs_checked": 9},
        token_efficiency={"references": {}, "amplified": {}},
    )
    write_matched(a_dir, build_matched(tasks, references, amplified, words), **kwargs)
    write_matched(b_dir, build_matched(
        dict(reversed(list(tasks.items()))), references, amplified, words), **kwargs)
    for name in ("oxide.jsonl", "rust.jsonl", "manifest.json"):
        assert (a_dir / name).read_bytes() == (b_dir / name).read_bytes()


def test_manifest_completeness(tmp_path):
    build_and_write(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == set(MANIFEST_KEYS)
    for row in manifest["classes"]:
        assert set(row) == {"class", "budget", "kept_tokens",
                            "kept_examples", "gap", "quantization_step"}
    for row in manifest["dropped"]:
        assert set(row) == {"task", "arm", "class", "sha256", "sup_tokens"}
    assert set(manifest["totals"]) == {"kept_tokens", "kept_examples"}


def test_jsonl_round_trip_matches_result(tmp_path):
    result = build_and_write(tmp_path)
    for arm in ARMS:
        rows = [json.loads(line) for line in
                (tmp_path / f"{arm}.jsonl").read_text(encoding="utf-8").splitlines()]
        assert [
            (r["task"], r["class"], r["source"], r["text"], r["sha256"], r["sup_tokens"])
            for r in rows
        ] == [
            (e.task, e.cls, e.source, e.text, e.sha256, e.sup_tokens)
            for e in result.kept[arm]
        ]
