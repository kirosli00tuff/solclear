"""Clearance scorer: deterministic vectors, excluded features stay out,
clearance moves the right way, and every verdict carries its calibration.
"""

from __future__ import annotations

import lightgbm as lgb
import numpy as np

from solclear import metrics
from solclear import scorer as sc


def test_feature_vector_orders_and_fills_missing_with_sentinel() -> None:
    # Arrange — a dict missing several features and carrying an explicit None.
    features = {"top5_concentration_wend": 0.8, "mintable": 1.0, "n_early_holders": None}

    # Act
    vec = sc.feature_vector(features)

    # Assert — length matches FEATURES, values land in order, missing -> -1.0.
    assert len(vec) == len(sc.FEATURES)
    assert vec[sc.FEATURES.index("top5_concentration_wend")] == 0.8
    assert vec[sc.FEATURES.index("mintable")] == 1.0
    assert vec[sc.FEATURES.index("n_early_holders")] == sc.MISSING  # None -> sentinel
    assert vec[sc.FEATURES.index("freezable")] == sc.MISSING  # absent -> sentinel


def test_features_exclude_creator_history_columns() -> None:
    # C.23 measured creator-history features inert on the honest boundary and
    # harmful out of sample; the deliverable must not silently readopt them.
    assert not any(f.startswith("creator_prior") for f in sc.FEATURES)
    assert "creator_days_since_prev_launch" not in sc.FEATURES
    assert "creator_first_seen" not in sc.FEATURES


def _toy_scorer() -> sc.ClearanceScorer:
    # top5_concentration_wend alone separates the classes in this toy model.
    rng = np.random.default_rng(0)
    n = 240
    x = rng.normal(0.0, 0.05, size=(n, len(sc.FEATURES)))
    y = (np.arange(n) % 2 == 0).astype(int)
    x[:, sc.FEATURES.index("top5_concentration_wend")] = np.where(y == 1, 0.95, 0.30)
    model = lgb.LGBMClassifier(n_estimators=50, learning_rate=0.1, verbose=-1)
    model.fit(x, y)
    return sc.ClearanceScorer(
        booster=model.booster_, threshold=0.5, calibration=metrics.calibration_statement()
    )


def test_clearance_score_falls_as_concentration_rises() -> None:
    # Higher launch concentration is rug-like: clearance evidence must drop.
    scorer = _toy_scorer()

    concentrated = scorer.clearance("POOL_HI", {"top5_concentration_wend": 0.95})
    dispersed = scorer.clearance("POOL_LO", {"top5_concentration_wend": 0.30})

    assert 0.0 <= concentrated.clearance_score <= 1.0
    assert 0.0 <= dispersed.clearance_score <= 1.0
    assert dispersed.clearance_score > concentrated.clearance_score
    assert dispersed.cleared is True
    assert concentrated.cleared is False


def test_clearance_returns_verdict_with_calibration_attached() -> None:
    # The function takes a pool identifier and returns a Clearance carrying its
    # calibration statement — never a bare number.
    scorer = _toy_scorer()

    verdict = sc.clearance("MINT_A", {"top5_concentration_wend": 0.30}, scorer=scorer)

    assert isinstance(verdict, sc.Clearance)
    assert verdict.pool == "MINT_A"
    assert verdict.calibration == metrics.calibration_statement()
    assert "0.984" in verdict.calibration  # the figure travels with every verdict


def test_load_scorer_reads_the_committed_artifact_and_scores() -> None:
    # The persisted artifact loads with its registered operating threshold and
    # produces a verdict end to end (no vendor key involved anywhere).
    scorer = sc.load_scorer()

    assert scorer.threshold > 0.0
    assert "0.984" in scorer.calibration
    verdict = scorer.clearance("SMOKE", {"top5_concentration_wend": 0.5, "mintable": 0.0})
    assert isinstance(verdict, sc.Clearance)
    assert verdict.calibration == scorer.calibration
