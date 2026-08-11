"""The documented operating point — single source of truth for every figure.

Every number here was measured in MLCryptoEngine (C.23/C.24, 2026-08-07) and
is asserted by ``tests/test_honesty.py`` in two directions at once: the README
and CLAUDE.md must carry these figures, and the persisted model must reproduce
them on the committed holdout matrix. A change that degrades the model, or a
doc edit that inflates a claim, breaks the build rather than quietly shipping.
"""

from __future__ import annotations

HOLDOUT = (
    "2024 time-split holdout (train <= 2023, test Jan-Nov 2024, n=194), "
    "SolRPDS-labelled Solana pools, pre-event 30-minute launch-window state"
)

# The clearance direction — the only trustworthy one. Max-precision operating
# point subject to honest-class recall >= 0.5 on the holdout.
CLEARANCE_PRECISION = 0.984
CLEARANCE_RECALL = 0.538

# The misuse direction, documented so it is never rediscovered the hard way:
# inverted into a hard-rug alarm, the same separator is wrong more often than
# right. This figure exists to make the misuse case self-refuting.
MISUSE_FLAG_PRECISION = 0.464

# The boundary this scorer does NOT cross (C.23): honest launches versus
# soft/slow rugs, absent from launch-window state.
T0_HONEST_BOUNDARY_PRECISION = 0.574
T0_HONEST_BOUNDARY_BASE_RATE = 0.500

# The wild base rate (Solidus Labs): ~98.7% of pump.fun launches show
# scam-adjacent characteristics. Predicting rug on everything scores 98.7%
# accuracy — which is why nothing here is ever judged on accuracy.
WILD_SCAM_ADJACENT_RATE = 0.987


def calibration_statement() -> str:
    """The scope statement attached to every Clearance. Never ship a bare number."""
    return (
        "CLEARANCE, not safety: this score answers one question — will this pool avoid "
        "a hard rug (near-total, >=99% liquidity removal)? A cleared pool avoided a hard "
        f"rug at {CLEARANCE_PRECISION:.3f} precision, covering {CLEARANCE_RECALL:.3f} of "
        f"honest pools, measured on the {HOLDOUT}. It does NOT answer whether the pool is "
        "safe: the honest-versus-soft/slow-rug boundary is absent from launch-window state "
        f"({T0_HONEST_BOUNDARY_PRECISION:.3f} precision against a "
        f"{T0_HONEST_BOUNDARY_BASE_RATE:.3f} base rate), so a cleared pool can still "
        "dev-dump or bleed out over months. Do not invert this into a rug alarm: used that "
        f"way the same model measures {MISUSE_FLAG_PRECISION:.3f} precision — wrong more "
        f"often than right. Roughly {WILD_SCAM_ADJACENT_RATE:.1%} of pump.fun launches are "
        "scam-adjacent, so this is a filter for a small honest minority, judged on "
        "minority-class precision, never accuracy."
    )
