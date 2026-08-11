"""The clearance scorer. The API is clearance — there is no other direction.

This packages the one thing the parent project's detection track measured as
working: separating **hard rugs** (near-total, >= 99% liquidity removal) from
other launches on pre-event launch-window state. The API is shaped by that
measurement, deliberately:

- The entry point is :func:`clearance` and it returns a :class:`Clearance` —
  a verdict with its calibration statement attached, never a bare number.
- **No probability of danger is exposed.** The underlying model estimates
  P(hard_rug), but that direction measured 0.464 precision as an alarm —
  wrong more often than right — so surfacing it would invite the exact misuse
  the measurements refute. The public score is *clearance evidence* only, and
  ``tests/test_honesty.py`` pins the API surface so a rug-detection-shaped
  name cannot appear without breaking the build.
- Creator-history features are deliberately excluded: C.23 measured them
  inert on the honest boundary and harmful out of sample.

The model artifact lives in ``solclear/artifacts/`` and is regenerable from
the committed immutable snapshot matrix via ``make train`` (solclear/train.py).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
DEFAULT_MODEL = ARTIFACT_DIR / "hard_rug_clearance.txt"
DEFAULT_META = ARTIFACT_DIR / "hard_rug_clearance.meta.json"

# Launch-window features only (features.features + GoPlus token-security),
# fixed order. Creator-history columns are intentionally absent — C.23 measured
# them inert on the honest boundary and harmful out of sample.
FEATURES: tuple[str, ...] = (
    "creator_allocation_t0",
    "top5_concentration_wend",
    "creator_time_to_first_sell_s",
    "authority_revoked_in_window",
    "n_early_holders",
    "insider_funded_early_holders",
    "freezable",
    "mintable",
    "nontransf",
    "thook",
)

# Sentinel for an unavailable feature — matches the training matrix, so the
# model sees missing values encoded identically at score time. A real 0.0
# would read as "measured and zero"; this reads as "absent".
MISSING = -1.0


def feature_vector(features: Mapping[str, float | None]) -> list[float]:
    """Order a feature dict into the model's input vector, missing -> sentinel."""
    out: list[float] = []
    for k in FEATURES:
        v = features.get(k)
        out.append(MISSING if v is None else float(v))
    return out


@dataclass(frozen=True)
class Clearance:
    """A clearance verdict for one pool. The calibration statement travels with it.

    ``clearance_score`` is evidence of clearance only, in [0, 1]: higher means
    stronger evidence the pool avoids a hard rug. It is NOT a safety score and
    NOT an invertible rug probability — inverted into an alarm the underlying
    separator measures 0.464 precision (see ``calibration``).
    """

    pool: str
    cleared: bool
    clearance_score: float
    calibration: str


@dataclass(frozen=True)
class ClearanceScorer:
    """A loaded model answering exactly one question: clearance."""

    booster: Any  # lightgbm.Booster; kept loose so the module imports without lightgbm
    threshold: float  # registered operating threshold in clearance-score space
    calibration: str

    def clearance(self, pool: str, features: Mapping[str, float | None]) -> Clearance:
        """Clearance verdict for one pool's launch-window feature dict."""
        raw = self.booster.predict([feature_vector(features)])
        score = 1.0 - float(raw[0])
        return Clearance(
            pool=pool,
            cleared=score >= self.threshold,
            clearance_score=score,
            calibration=self.calibration,
        )


def load_scorer(
    model_path: Path = DEFAULT_MODEL, meta_path: Path = DEFAULT_META
) -> ClearanceScorer:
    """Load the persisted artifact and its operating point (lightgbm lazily)."""
    import lightgbm as lgb

    meta = json.loads(meta_path.read_text())
    return ClearanceScorer(
        booster=lgb.Booster(model_file=str(model_path)),
        threshold=float(meta["clearance_point"]["threshold"]),
        calibration=str(meta["calibration"]),
    )


@cache
def _default_scorer() -> ClearanceScorer:
    return load_scorer()


def clearance(
    pool: str,
    features: Mapping[str, float | None],
    scorer: ClearanceScorer | None = None,
) -> Clearance:
    """Clearance verdict for a pool identifier and its launch-window features.

    ``features`` comes from the caller's retrieval pipeline (Method B fetch ->
    ``solclear.features.features``), keeping this function scorable without a
    vendor key. With no ``scorer`` given, the committed artifact is used.
    """
    return (scorer or _default_scorer()).clearance(pool, features)
