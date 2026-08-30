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


def test_pair_costs_names_unreadable_pairs_instead_of_scoring_them_zero(monkeypatch):
    import eval.cost_census as cc

    monkeypatch.setattr(
        cc,
        "load_train_tasks",
        lambda: {"nXX": {"class": "vectors"}, "n001": {"class": "arithmetic/loops"}},
    )
    costs, dropped = cc.pair_costs(lambda s: len(s.split()))
    assert "nXX" in dropped
    assert all(c.task != "nXX" for c in costs)


def test_acceptance_pins_the_committed_corpus_numbers():
    """A DRIFT ALARM, not a constant.

    These are the figures after wave 3 closed. The values this
    instrument was born against, one wave earlier, were vectors 789/573,
    strings 615/578, overall 2536/2332 (ratio 1.0875), with the ranked
    top three n043 +82, n050 +60, n045 +40 -- the surpluses that
    swap/reverse/unwrap_or/count_if were shipped to close. The corpus
    now sits BELOW parity at 2300/2332 = 0.9863. Both sets are recorded
    so a future reader can see what the wave moved, and so a corpus
    change nobody intended fails loudly here.
    """
    costs, dropped = pair_costs(qwen_counter())
    assert dropped == []
    subs = class_subtotals(costs)
    assert (subs["vectors"]["oxide"], subs["vectors"]["rust"]) == (555, 573)
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
    assert census["overall"]["oxide"] == 2300  # was 2536 at wave-3 start
    assert census["overall"]["rust"] == 2332
