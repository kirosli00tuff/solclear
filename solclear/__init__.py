"""solclear: clears Solana launch pools as not-a-hard-rug. Nothing more.

The public API is the clearance direction only — see CLAUDE.md for the scope
statement this package exists to enforce, and FINDINGS.md for the measured
negatives that travel with it.
"""

from solclear.metrics import calibration_statement
from solclear.scorer import Clearance, ClearanceScorer, Unscorable, clearance, load_scorer

__all__ = [
    "Clearance",
    "ClearanceScorer",
    "Unscorable",
    "calibration_statement",
    "clearance",
    "load_scorer",
]
