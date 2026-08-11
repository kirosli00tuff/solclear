"""Leakage suite: no feature may know the future. First-class tests, wired first.

Ported from the parent project's ordering (C.21): these existed before any
real feature was ever computed there, and they gate every feature here. Three
defenses, each catching a different failure shape:

1. **Window-leak refusal** — a pool whose label event falls inside the feature
   window is refused, never clamped: clamping would leak the event time
   through the window length.
2. **Prefix invariance** — activity after the window must move no feature.
3. **Planted-future canary** — a deliberately leaky feature computation must
   be CAUGHT by the same comparison, proving the detector has teeth rather
   than passing vacuously.
"""

from __future__ import annotations

import pytest

from solclear import features as feat

T0 = 1_700_000_000.0


def _base_history() -> list[feat.Tx]:
    return [
        feat.Tx(T0, "mint_to", "creator", 1000.0),
        feat.Tx(T0 + 60, "transfer", "early1", 200.0, source="creator"),
        feat.Tx(T0 + 120, "sell", "creator", 100.0),
    ]


# ------------------------- window guard: the refusal ------------------------ #


def test_a_label_event_inside_the_window_is_refused_not_clamped() -> None:
    # An event at T0+10 min sits inside the 30-min window: the computation must
    # refuse, because clamping would leak the event time.
    with pytest.raises(feat.WindowLeakError, match="EXCLUDED"):
        feat.feature_window_end(T0, T0 + 600)
    # An event at exactly the window end is still a leak (<=, not <).
    with pytest.raises(feat.WindowLeakError):
        feat.feature_window_end(T0, T0 + 1_800)
    # An event after the window is fine, and the end is exactly T0+1800.
    assert feat.feature_window_end(T0, T0 + 5_000) == T0 + 1_800.0


# --------------------------- prefix invariance ------------------------------ #


def test_features_are_prefix_invariant_beyond_the_window() -> None:
    # Identical histories except for post-window activity: nothing after the
    # window may move any feature.
    base = _base_history()
    noisy = [*base, feat.Tx(T0 + 3_000, "sell", "creator", 900.0)]

    assert feat.features(base, T0, "creator", None) == feat.features(noisy, T0, "creator", None)


def test_balances_replay_reads_nothing_after_the_cutoff() -> None:
    base = _base_history()
    noisy = [*base, feat.Tx(T0 + 1_801, "transfer", "late", 500.0, source="creator")]

    assert feat.balances_at(base, T0 + 1_800) == feat.balances_at(noisy, T0 + 1_800)


# ------------------- the planted-future canary, with teeth ------------------ #


def _leaky_features(txs: list[feat.Tx], t0_s: float, creator: str) -> dict[str, float | None]:
    """A deliberately leaky variant: reads an hour past the registered window.

    This simulates the clamping/over-reading bug the suite exists to catch.
    It must NOT be exported or used anywhere outside this test.
    """
    leaky_end = t0_s + 3_600.0  # past the 1,800 s window: reads the future
    at_end = feat.balances_at(txs, leaky_end)
    total = sum(at_end.values())
    creator_share = at_end.get(creator, 0.0) / total if total else None
    return {"creator_share": creator_share, "n_holders": float(len(at_end))}


def test_canary_a_leaky_feature_is_detected_by_the_invariance_check() -> None:
    # Two histories identical up to the window end, differing only after it —
    # exactly the comparison the prefix-invariance test runs.
    base = _base_history()
    future = [*base, feat.Tx(T0 + 2_400, "sell", "creator", 800.0)]  # inside the leak

    # The real feature set must not move...
    assert feat.features(base, T0, "creator", None) == feat.features(future, T0, "creator", None)
    # ...and the detector must FLAG the leaky variant, or it proves nothing.
    assert _leaky_features(base, T0, "creator") != _leaky_features(future, T0, "creator"), (
        "the invariance check failed to catch a feature that reads the future"
    )


# ----------------------- known-answer feature values ------------------------ #


def test_concentration_and_creator_ttfs_read_inside_the_window_only() -> None:
    # Creator mints 1000, sends 200 to early1, sells 100 at T0+120.
    out = feat.features(_base_history(), T0, "creator", None)

    # Allocation at T0 is 100%; two holders at window end; TTFS 120 s; early1
    # is insider-funded; two holders means top-5 covers everything.
    assert out["creator_allocation_t0"] == pytest.approx(1.0)
    assert out["n_early_holders"] == 2.0
    assert out["creator_time_to_first_sell_s"] == pytest.approx(120.0)
    assert out["insider_funded_early_holders"] == 1.0
    assert out["top5_concentration_wend"] == pytest.approx(1.0)


def test_decontamination_thresholds_split_soft_slow_and_honest() -> None:
    # Insiders hold 1000 at window end; sells timed around the registered
    # 72 h / 30 d horizons at the 70% fraction.
    def txs(sell_ts: float, amount: float) -> list[feat.Tx]:
        return [
            feat.Tx(T0, "mint_to", "creator", 1000.0),
            feat.Tx(sell_ts, "sell", "creator", amount),
        ]

    soft = feat.decontaminate(txs(T0 + 71 * 3_600, 700.0), T0, "creator")
    slow = feat.decontaminate(txs(T0 + 100 * 3_600, 700.0), T0, "creator")
    honest_small = feat.decontaminate(txs(T0 + 71 * 3_600, 699.0), T0, "creator")
    honest_late = feat.decontaminate(txs(T0 + 31 * 86_400, 700.0), T0, "creator")

    assert soft == "soft_rug"
    assert slow == "slow_rug"
    assert honest_small == "honest_candidate"  # 69.9% is below the registered 70%
    assert honest_late == "honest_candidate"  # beyond 30 days is outside both rules
