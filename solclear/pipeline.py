"""The live scoring pipeline's contract: refuse before a partial can mislead.

This module is the structural link Stage B measured as absent (ADR-005): the
scorer alone cannot see whether retrieval reached T0 or whether the parse
accounted for every transaction, so before it exists, a truncated fetch or a
lossy parse quietly becomes a confident-looking number. :func:`score_pool`
is the only sanctioned path from a retrieved window to a verdict, and it
refuses — returning :class:`solclear.scorer.Unscorable`, never a score —
when any of the three registered conditions holds (Stage C Task 0):

1. **Retrieval incomplete** — the fetch reports ``reached_t0=False``; a
   partial window is a corrupted partial (ADR-002), and its features would
   be computed over missing history.
2. **Parse incomplete** — the parse counted transactions it could not
   understand; dropping them silently would be the absence-as-evidence
   failure in new clothes.
3. **Missing features** — the assembled mapping lacks a required feature
   whose SOURCE was unavailable (a vendor field the token-security client
   could not decode); the scorer refuses this (ADR-006). Window features
   that are None from a COMPLETE window are measured absence, not missing
   data, and encode to the trained sentinel instead (ADR-012).

The upstream producers arrive in later Stage C tasks: the enhanced-detail
fetch and parse produce ``txs`` and the :class:`ParseReport`, and the
token-security client produces ``token_security``. This module deliberately
predates them so their outputs land against an existing refusal contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from solclear import metrics
from solclear.features import Tx, features
from solclear.method_b import WindowFetch
from solclear.scorer import MISSING, Clearance, ClearanceScorer, Unscorable, clearance


@dataclass(frozen=True)
class ParseReport:
    """Accounting for every transaction the parse saw. Nothing drops silently.

    ``total`` is the number of transactions examined; ``parsed`` produced
    :class:`~solclear.features.Tx` events; ``ignored`` were understood and
    deliberately irrelevant (e.g. unrelated programs touching the address);
    ``unparseable`` were NOT understood — any nonzero count refuses scoring.
    """

    total: int
    parsed: int
    ignored: int
    unparseable: int


def score_pool(
    fetch: WindowFetch,
    txs: list[Tx],
    parse_report: ParseReport,
    token_security: Mapping[str, float | None],
    creator: str,
    scorer: ClearanceScorer | None = None,
) -> Clearance | Unscorable:
    """Score one retrieved pool window, refusing anything that cannot be honest.

    ``creator`` follows the registered definition (Stage C Task 0): the
    recipient of the first in-window ``mint_to``, else the fee payer of the
    earliest in-window transaction — resolved by the caller from the parsed
    events. ``label_event_s`` is None by construction: scoring happens at the
    window edge, before any label event can be known (the window guard's
    refusal protects label construction at training time, not scoring).
    """
    if not fetch.reached_t0:
        return Unscorable(
            pool=fetch.address,
            reason="retrieval_incomplete",
            missing=(),
            calibration=metrics.calibration_statement(),
        )
    if parse_report.unparseable > 0:
        return Unscorable(
            pool=fetch.address,
            reason="parse_incomplete",
            missing=(),
            calibration=metrics.calibration_statement(),
        )
    # ADR-012: both completeness gates passed, so a None window feature is a
    # MEASURED absence (e.g. the creator never sold) and encodes to the
    # trained -1.0 sentinel — exactly how the committed matrix encodes it.
    # Vendor (token-security) None is absent DATA and still refuses below.
    assembled: dict[str, float | None] = {
        k: (MISSING if v is None else v)
        for k, v in features(txs, float(fetch.t0_s), creator, label_event_s=None).items()
    }
    assembled.update(token_security)
    return clearance(fetch.address, assembled, scorer=scorer)
