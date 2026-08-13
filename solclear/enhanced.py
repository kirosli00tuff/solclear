"""Helius Enhanced Transactions client — the step ADR-004 said was never built.

Priced before it is used (Stage C ordering): the gate weight for ``enhanced``
was corrected to the vendor's published 100 credits per call *before* this
module existed, so the first enhanced request ever sent from this repository
was priced correctly. Wrap the client in :class:`GatedEnhanced` — one
``enhanced`` charge per call, before the request — exactly as ``GatedRpc``
wraps the JSON-RPC transport.

Vendor-documented semantics (docs read 2026-08-13; the acceptance boundary
is re-measured live in Stage C Task 5, because documented and real limits
differ — the standing lesson):

- ``POST /v0/transactions`` accepts up to **100 signatures per request**.
- Billing is a flat **100 credits per request** regardless of batch fill,
  so a pool window of N signatures costs ``ceil(N / 100) * 100`` credits —
  :func:`calls_needed` * 100 — and a sweep must be priced with it *before*
  the first call (registered sub-budget rule).
- The free plan rate-limits this API at 2 req/s (documented); the default
  pacing below uses 0.6 s spacing — documented-with-margin, flagged as
  provisional until the live measurement replaces it.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence
from typing import Any, Protocol

import httpx

from solclear.gate import CreditGate
from solclear.rpc import PacedSender, RatePolicy, RpcError

DEFAULT_ENHANCED_BASE_URL = "https://api.helius.xyz"
DEFAULT_TIMEOUT_S = 30.0
# Vendor-documented (helius.dev/docs, read 2026-08-13). The live acceptance
# boundary (does 101 reject?) is measured in Stage C Task 5.
MAX_SIGNATURES_PER_CALL = 100
CREDITS_PER_CALL_DOCUMENTED = 100
# Documented free-tier enhanced rate is 2 req/s; 0.6 s adds margin.
# Provisional until measured — the JSON-RPC lesson says docs and reality differ.
DEFAULT_ENHANCED_POLICY = RatePolicy(min_interval_s=0.6)


def calls_needed(n_signatures: int) -> int:
    """Enhanced calls a window of ``n_signatures`` costs — for pricing BEFORE sending."""
    return math.ceil(n_signatures / MAX_SIGNATURES_PER_CALL)


class EnhancedTransactions(Protocol):
    """The one call the parse needs; implementations do no pricing of their own."""

    def transactions(self, signatures: Sequence[str]) -> list[dict[str, Any]]: ...


class EnhancedClient:
    """Synchronous client for ``POST /v0/transactions``. One batch per call.

    A batch larger than :data:`MAX_SIGNATURES_PER_CALL` raises ``ValueError``
    rather than being split silently: splitting multiplies credits, and
    spending decisions belong to the caller holding the gate.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_ENHANCED_BASE_URL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        policy: RatePolicy | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout_s, transport=transport)
        self._path = f"/v0/transactions?api-key={api_key}"
        self._sender = PacedSender(
            policy if policy is not None else DEFAULT_ENHANCED_POLICY, sleep, monotonic
        )

    def close(self) -> None:
        self._client.close()

    def transactions(self, signatures: Sequence[str]) -> list[dict[str, Any]]:
        if not signatures:
            raise ValueError("empty signature batch: nothing to fetch, nothing to spend")
        if len(signatures) > MAX_SIGNATURES_PER_CALL:
            raise ValueError(
                f"batch of {len(signatures)} exceeds {MAX_SIGNATURES_PER_CALL} signatures/call; "
                "split deliberately and price each call through the gate first"
            )
        resp = self._sender.send(
            "enhancedTransactions",
            lambda: self._client.post(self._path, json={"transactions": list(signatures)}),
        )
        if resp.status_code == 429:
            raise RpcError(
                f"enhancedTransactions: HTTP 429 after {self._sender.policy.max_retries_429} retries"
            )
        if resp.status_code != 200:
            raise RpcError(f"enhancedTransactions: HTTP {resp.status_code}")
        payload = resp.json()
        if not isinstance(payload, list):
            raise RpcError("enhancedTransactions: non-list result")
        return payload


class GatedEnhanced:
    """Charges one ``enhanced`` credit-weight per call BEFORE it is sent.

    A gate refusal raises :class:`solclear.gate.CreditCapError` before the
    transport is touched and writes nothing (ADR-003).
    """

    def __init__(self, client: EnhancedTransactions, gate: CreditGate) -> None:
        self._client = client
        self._gate = gate

    def transactions(self, signatures: Sequence[str]) -> list[dict[str, Any]]:
        self._gate.charge("enhanced", 1, f"enhancedTransactions n={len(signatures)}")
        return self._client.transactions(signatures)
