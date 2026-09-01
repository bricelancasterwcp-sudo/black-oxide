"""The cost census: where the oxide/rust token surplus actually sits.

Synthetic fixtures exercise the arithmetic; the acceptance test pins the
instrument against the committed corpus (the 2026-08-29 measured numbers
the wave-3 spec was approved on). If the acceptance test fails, either
the corpus moved or the instrument drifted -- both must be loud.
"""
from eval.cost_census import (
    PairCost,
    build_cost_census,
    class_subtotals,
    pair_costs,
    rank_by_surplus,
)
from eval.token_match import qwen_counter


def test_surplus_is_signed_never_clipped():
    """structs/option runs NEGATIVE in the real corpus and that is
    load-bearing for the whole-corpus ratio -- a census that clipped at
    zero would silently inflate the total."""
    win = PairCost("n001", "structs/option", oxide_tokens=40, rust_tokens=55)
    lose = PairCost("n002", "vectors", oxide_tokens=90, rust_tokens=60)
    assert win.surplus == -15
    assert lose.surplus == +30


def test_ratio_is_none_rather_than_a_fabricated_number():
    empty = PairCost("n003", "vectors", oxide_tokens=10, rust_tokens=0)
    assert empty.ratio is None


def test_rank_by_surplus_orders_most_expensive_first():
    costs = [
        PairCost("a", "vectors", 70, 60),
        PairCost("b", "vectors", 142, 60),
        PairCost("c", "vectors", 40, 50),
    ]
    assert [c.task for c in rank_by_surplus(costs)] == ["b", "a", "c"]


def test_class_subtotals_sum_both_arms_and_ratio_the_totals():
    costs = [
        PairCost("a", "vectors", 100, 50),
        PairCost("b", "vectors", 50, 50),
        PairCost("c", "strings", 30, 30),
    ]
    subs = class_subtotals(costs)
    assert subs["vectors"]["oxide"] == 150
    assert subs["vectors"]["rust"] == 100
    assert subs["vectors"]["surplus"] == 50
    assert subs["vectors"]["ratio"] == 1.5
    assert subs["strings"]["surplus"] == 0


def test_acceptance_pins_the_committed_corpus_numbers():
    """A DRIFT ALARM, not a constant.

    These are the figures after wave 3 closed. The values this
    instrument was born against, one wave earlier, were vectors 789/573,
    strings 615/578, overall 2536/2332 (ratio 1.0875), with the ranked
    top three n043 +82, n050 +60, n045 +40 -- the surpluses that
    swap/reverse/unwrap_or/count_if were shipped to close. The corpus
    now sits BELOW parity at 2302/2332 = 0.9871 -- wave 4's predicate
    re-spelling to the bar form cost exactly the 2 tokens it predicted,
    deliberately trading static efficiency for learnability. Both sets
    are recorded
    so a future reader can see what the wave moved, and so a corpus
    change nobody intended fails loudly here.
    """
    costs, dropped = pair_costs(qwen_counter())
    assert dropped == []
    subs = class_subtotals(costs)
    assert (subs["vectors"]["oxide"], subs["vectors"]["rust"]) == (557, 573)
    assert (subs["strings"]["oxide"], subs["strings"]["rust"]) == (613, 578)
    assert (subs["structs/option"]["oxide"], subs["structs/option"]["rust"]) == (623, 677)
    assert (subs["arithmetic/loops"]["oxide"], subs["arithmetic/loops"]["rust"]) == (
        509,
        504,
    )
    top = rank_by_surplus(costs)[:3]
    assert [c.task for c in top] == ["n054", "n064", "n045"]
    assert [c.surplus for c in top] == [20, 15, 14]


def test_census_payload_carries_its_lens():
    census = build_cost_census()
    assert census["tokenizer"]["sha256"]
    assert census["dropped"] == []
    assert census["overall"]["oxide"] == 2302  # 2536 at wave-3 start; 2300 at its close
    assert census["overall"]["rust"] == 2332


# ------------------------------------------------------- wave 8: sources

def _tmp_source(tmp_path, tasks, pairs):
    """A by-arm source on disk. Real files rather than a monkeypatched
    loader: the layout IS the thing under test."""
    import json as _json

    from eval.cost_census import PairSource

    tasks_path = tmp_path / "tasks.jsonl"
    tasks_path.write_text(
        "".join(_json.dumps(t) + "\n" for t in tasks), encoding="utf-8"
    )
    root = tmp_path / "refs"
    for arm in ("oxide", "rust"):
        (root / arm).mkdir(parents=True)
    for tid, (ox, rs) in pairs.items():
        (root / "oxide" / f"{tid}.ox").write_text(ox, encoding="utf-8")
        (root / "rust" / f"{tid}.rs").write_text(rs, encoding="utf-8")
    return PairSource(
        "tmp", tasks_path, root, "oxide/{task}.ox", "rust/{task}.rs"
    )


def test_pair_source_resolves_both_repo_layouts():
    """The train corpus nests arms under the task; the eval sets key by
    arm first. One reader must serve both or the census stays bound to
    whichever layout it was born against."""
    from eval.cost_census import EVAL_SOURCE, LARGE_SOURCE, TRAIN_SOURCE

    assert TRAIN_SOURCE.oxide_path("n001").as_posix().endswith("n001/oxide.ox")
    assert TRAIN_SOURCE.rust_path("n001").as_posix().endswith("n001/rust.rs")
    assert EVAL_SOURCE.oxide_path("t01").as_posix().endswith("references-v04/oxide/t01.ox")
    assert LARGE_SOURCE.rust_path("g01").as_posix().endswith("references-large/rust/g01.rs")


def test_pair_costs_reads_the_source_it_is_given(tmp_path):
    source = _tmp_source(
        tmp_path,
        [{"id": "x1", "class": "vectors", "stratum": "linear"}],
        {"x1": ("a b c", "a b")},
    )
    costs, dropped = pair_costs(lambda s: len(s.split()), source)
    assert dropped == []
    assert (costs[0].oxide_tokens, costs[0].rust_tokens) == (3, 2)
    assert costs[0].stratum == "linear"


def test_pair_costs_names_unreadable_pairs_in_a_given_source(tmp_path):
    """The wave-2 rule, re-pinned at the new seam: a pair that cannot be
    read is named, never scored zero -- zero reads as 'costs nothing'."""
    source = _tmp_source(
        tmp_path,
        [
            {"id": "x1", "class": "vectors"},
            {"id": "gone", "class": "strings"},
        ],
        {"x1": ("a b c", "a b")},
    )
    costs, dropped = pair_costs(lambda s: len(s.split()), source)
    assert dropped == ["gone"]
    assert [c.task for c in costs] == ["x1"]


def test_stratum_subtotals_split_the_two_strata():
    from eval.cost_census import stratum_subtotals

    costs = [
        PairCost("a", "vectors", 100, 50, "compositional"),
        PairCost("b", "strings", 50, 50, "compositional"),
        PairCost("c", "vectors", 30, 60, "linear"),
    ]
    strata = stratum_subtotals(costs)
    assert strata["compositional"]["ratio"] == 1.5
    assert strata["linear"]["ratio"] == 0.5


def test_stratum_subtotals_omit_unstratified_pairs_rather_than_labelling_them():
    """The train and eval sets carry no stratum. Bucketing them under
    'unknown' would invent a group that was never authored."""
    from eval.cost_census import stratum_subtotals

    assert stratum_subtotals([PairCost("a", "vectors", 10, 10)]) == {}


def test_census_names_its_source_so_a_number_cannot_be_quoted_rootless():
    from eval.cost_census import LARGE_SOURCE

    census = build_cost_census(LARGE_SOURCE)
    assert census["source"] == "large"
    assert census["dropped"] == []
    assert set(census["strata"]) == {"compositional", "linear"}


def test_acceptance_pins_the_large_tier():
    """Wave 8's drift alarm. Authored 2026-09-01: 20 tasks, both arms
    oracle-verified, every program inside the 200-600 token band.

    5823/5482 = 1.0622 AFTER the symmetric re-review, which converted six
    Oxide `while i < len(v)` loops to `range` where the Rust arm already
    had a counted loop and moved the ratio 1.0766 -> 1.0622 in Oxide's
    favour. The small tiers read 0.9462 (eval) and 0.9871 (train), so
    this tier crossing parity is the wave's finding, not a defect. If
    this fails, either the tier moved or the tokenizer did."""
    from eval.cost_census import LARGE_SOURCE

    costs, dropped = pair_costs(qwen_counter(), LARGE_SOURCE)
    assert dropped == []
    assert len(costs) == 20
    assert all(200 <= c.oxide_tokens <= 600 for c in costs)
    assert all(200 <= c.rust_tokens <= 600 for c in costs)
    overall_ox = sum(c.oxide_tokens for c in costs)
    overall_rs = sum(c.rust_tokens for c in costs)
    assert (overall_ox, overall_rs) == (5823, 5482)
