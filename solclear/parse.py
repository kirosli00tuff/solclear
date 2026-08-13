"""Parse: Helius enhanced payloads → ``features.Tx`` events, nothing dropped silently.

The missing link ADR-004 named first: Method B returns signatures,
``features.features()`` consumes balance-changing events, and nothing
converted one into the other. This module is that conversion, with the event
definitions stated here precisely because the KAT (Stage C Task 8) judges
them against the committed snapshot.

**Event definitions** — all relative to the scored token mint ``M`` and the
launch pool address ``P``, over payload objects from ``POST
/v0/transactions`` (fields used: ``signature``, ``timestamp`` [unix s],
``type``, ``feePayer``, ``transactionError``, ``tokenTransfers[]`` with
``mint``, ``fromUserAccount``, ``toUserAccount``, ``tokenAmount``):

- ``mint_to`` — a token transfer of ``M`` with an empty/absent
  ``fromUserAccount``: tokens created to ``toUserAccount``.
- ``sell`` — a token transfer of ``M`` **into the pool**
  (``toUserAccount == P``): the swap-direction rule, fixed here, is that
  direction is judged relative to the pool — ``M`` flowing in is a sale by
  ``fromUserAccount``, whatever the counter-asset did.
- buys (``M`` flowing **out of the pool**, ``fromUserAccount == P``) are
  recorded as ``transfer`` events with ``source = P``: the buyer's first
  funding is the pool, so pool-funded buyers never enter the
  creator-funded insider set — matching the training-time semantics.
- ``transfer`` — a token transfer of ``M`` between two wallets, neither of
  them ``P``, with a real sender; carries ``source = fromUserAccount``.
- ``revoke_authority`` — a payload of type ``SET_AUTHORITY`` that references
  ``M``. Known approximation, stated rather than hidden: the enhanced
  payload does not reliably expose the new authority, so an authority
  *transfer* (rare in a launch window) would also match; the feature is
  binary presence-in-window and the KAT judges the consequence.

**Accounting**: every payload object lands in exactly one of ``parsed``
(produced ≥ 1 event), ``ignored`` (understood, deliberately no event:
failed transactions, out-of-window timestamps, transfers of other mints,
native-SOL-only movements), or ``unparseable`` (references ``M`` but its
token movement could not be decoded). ``unparseable > 0`` refuses scoring
at the pipeline (ADR-006) — a parse that quietly discards what it does not
understand is the absence-as-evidence failure in new clothes.

**Window discipline**: an event is emitted only for ``t0_s <= ts < end_s``;
out-of-window payloads are ignored by construction, which is what the
prefix-invariance and planted-future-canary tests in ``tests/test_parse.py``
hold down.

``creator`` follows the registered definition (Stage C Task 0): recipient of
the first in-window ``mint_to``, else the fee payer of the earliest
in-window payload; None when the window is empty.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from solclear.features import Tx
from solclear.pipeline import ParseReport


@dataclass(frozen=True)
class ParsedWindow:
    """Events strictly inside the window, the accounting, and the creator."""

    events: tuple[Tx, ...]
    report: ParseReport
    creator: str | None


def _events_for(payload: Mapping[str, Any], mint: str, pool_address: str) -> tuple[list[Tx], bool]:
    """(events, understood) for one in-window payload. Never raises on shape."""
    ts = float(payload["timestamp"])
    events: list[Tx] = []
    references_mint = False

    if str(payload.get("type", "")) == "SET_AUTHORITY":
        blob = repr(payload)
        if mint in blob:
            events.append(Tx(ts, "revoke_authority", str(payload.get("feePayer", ""))))
            return events, True

    transfers = payload.get("tokenTransfers")
    if transfers is None:
        transfers = []
    if not isinstance(transfers, list):
        return [], False

    for item in transfers:
        if not isinstance(item, Mapping) or item.get("mint") != mint:
            continue
        references_mint = True
        try:
            amount = float(item["tokenAmount"])
            sender = str(item.get("fromUserAccount") or "")
            receiver = str(item.get("toUserAccount") or "")
        except (KeyError, TypeError, ValueError):
            return [], False
        if not sender and receiver:
            events.append(Tx(ts, "mint_to", receiver, amount))
        elif receiver == pool_address and sender:
            events.append(Tx(ts, "sell", sender, amount))
        elif sender == pool_address and receiver:
            events.append(Tx(ts, "transfer", receiver, amount, source=pool_address))
        elif sender and receiver:
            events.append(Tx(ts, "transfer", receiver, amount, source=sender))
        else:
            return [], False

    if references_mint and not events:
        return [], False  # referenced the mint but nothing decodable moved
    return events, True


def parse_window(
    payloads: Sequence[Mapping[str, Any]],
    *,
    mint: str,
    pool_address: str,
    t0_s: float,
    end_s: float,
) -> ParsedWindow:
    """Parse enhanced payloads into window events, accounting for every object."""
    events: list[Tx] = []
    parsed = ignored = unparseable = 0
    earliest_fee_payer: str | None = None
    earliest_ts: float | None = None

    for payload in payloads:
        ts_raw = payload.get("timestamp")
        if not isinstance(ts_raw, int | float):
            unparseable += 1
            continue
        ts = float(ts_raw)
        if payload.get("transactionError") is not None or not (t0_s <= ts < end_s):
            ignored += 1
            continue
        if earliest_ts is None or ts < earliest_ts:
            earliest_ts = ts
            earliest_fee_payer = str(payload.get("feePayer") or "") or None
        tx_events, understood = _events_for(payload, mint, pool_address)
        if not understood:
            unparseable += 1
        elif tx_events:
            parsed += 1
            events.extend(tx_events)
        else:
            ignored += 1

    events.sort(key=lambda e: e.ts_s)
    first_mint_to = next((e for e in events if e.kind == "mint_to"), None)
    creator = first_mint_to.wallet if first_mint_to is not None else earliest_fee_payer
    return ParsedWindow(
        events=tuple(events),
        report=ParseReport(
            total=len(payloads), parsed=parsed, ignored=ignored, unparseable=unparseable
        ),
        creator=creator,
    )
