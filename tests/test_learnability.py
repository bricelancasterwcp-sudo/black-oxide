"""The learnability estimand (SPEC §62.1): uptake per unit exposure.

The acceptance test pins wave 3's §6.1 observation -- the one the
estimand exists to express -- so a change that stopped distinguishing
`reverse` from `count_if` would fail loudly.
"""
from eval.learnability import learnability, rank, render, unmeasured


def test_ratio_is_uptake_over_exposure():
    rows = learnability({"reverse": 50}, {"reverse": 0.017})
    assert round(rows["reverse"]["ratio"], 1) == round(50 / 0.017, 1)


def test_zero_exposure_is_none_not_infinity_and_not_zero():
    """A construct the corpus never taught has NO learnability reading.
    Infinity would flatter it; 0.0 would convict it. Both are lies."""
    rows = learnability({"swap": 0}, {"swap": 0.0})
    assert rows["swap"]["ratio"] is None
    assert unmeasured(rows) == ["swap"]


def test_missing_exposure_is_also_unmeasured():
    rows = learnability({"mystery": 5}, {})
    assert rows["mystery"]["ratio"] is None


def test_zero_uptake_at_real_exposure_is_a_measured_zero():
    """This one IS a reading: the corpus taught it and the model still
    would not use it."""
    rows = learnability({"count_if": 0}, {"count_if": 0.024})
    assert rows["count_if"]["ratio"] == 0.0
    assert unmeasured(rows) == []


def test_both_terms_are_carried_so_a_ratio_is_never_read_alone():
    rows = learnability({"swap": 0}, {"swap": 0.007})
    assert rows["swap"]["uptake"] == 0
    assert rows["swap"]["exposure"] == 0.007


def test_rank_orders_most_learnable_first_and_puts_unmeasured_last():
    rows = learnability({"a": 50, "b": 10, "c": 0}, {"a": 0.02, "b": 0.02, "c": 0.0})
    assert [name for name, _ in rank(rows)] == ["a", "b", "c"]


def test_rank_breaks_ties_on_name_for_reproducibility():
    rows = learnability({"z": 10, "a": 10}, {"z": 0.02, "a": 0.02})
    assert [name for name, _ in rank(rows)] == ["a", "z"]


def test_render_shows_exposure_beside_every_ratio():
    rows = learnability({"count_if": 0}, {"count_if": 0.024})
    out = render(rows)
    assert "2.4%" in out and "`count_if`" in out


def test_wave3_acceptance_reverse_outlearns_count_if_at_lower_exposure():
    """The §6.1 observation, pinned: raw uptake and learnability rank
    these differently, and learnability is the one that matches what
    familiarity predicts."""
    uptake = {"reverse": 50, "count_if": 0, "+=": 194, "swap": 0}
    exposure = {"reverse": 0.017, "count_if": 0.024, "+=": 0.241, "swap": 0.007}
    rows = learnability(uptake, exposure)
    assert rows["reverse"]["ratio"] > rows["count_if"]["ratio"]
    # reverse is more LEARNABLE than += even though += has 4x the uptake,
    # because += needed 14x the exposure to get there.
    assert rows["reverse"]["ratio"] > rows["+="]["ratio"]
    assert rows["swap"]["ratio"] is not None  # 0.7% is small, not zero
    assert [name for name, _ in rank(rows)][0] == "reverse"
