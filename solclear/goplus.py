"""GoPlus token-security client: the last four model features, with their
monotonicity stated per field because the KAT's comparison depends on it.

Keyless free tier, ``GET /api/v1/solana/token_security``. The response
schema below was MEASURED on 2026-08-13 (probe on a holdout mint), not
quoted: ``freezable`` and ``mintable`` arrive as ``{"status": "0"/"1",
"authority": [...]}``; ``non_transferable`` is a bare ``"0"/"1"`` string;
``transfer_hook`` is a list (empty = absent).

**Monotonicity, per field — these are NOW-state reads on a retrospective
pool, and the directions are not symmetric:**

- ``freezable``, ``mintable`` (authority-backed): an authority can be
  revoked but never re-granted, so **present now (1) proves present at
  launch** — leak-free in that direction; **absent now (0) proves nothing
  about launch state** (it may have been revoked after the window). Task 8
  treats live 1 vs snapshot 0 as a genuine mismatch, and live 0 vs snapshot
  1 as *monotonic-unknowable* — a provenance class, not a defect
  (registered Amendment 1, Stage C Task 0).
- ``nontransf`` (non-transferable), ``thook`` (transfer hook): Token-2022
  extensions fixed when the mint is initialized, so they are treated as
  **time-invariant** — both directions must agree in Task 8. ``thook``
  reads presence of the ``transfer_hook`` extension itself; a mutable hook
  *program* behind an existing extension does not change presence.

An undecodable field maps to ``None``, never to a guessed 0.0 — downstream,
None is an absent required feature and the scorer REFUSES (ADR-006), so a
schema drift fails closed instead of scoring as "no risk flags".

Rate limits are measured rather than quoted (the standing lesson): the
measured burst tolerance travels in the Stage C progress entry, and the
default interval here is conservative against it.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

GOPLUS_BASE_URL = "https://api.gopluslabs.io/api/v1"
SOURCE_NAME = "goplus:solana_token_security"
TOKEN_SECURITY_FIELDS = ("freezable", "mintable", "nontransf", "thook")
DEFAULT_MIN_INTERVAL_S = 2.0
DEFAULT_TIMEOUT_S = 20.0


class GoPlusError(RuntimeError):
    """The token-security endpoint failed (transport or HTTP)."""


@dataclass(frozen=True)
class TokenSecurity:
    """The four model features from a now-state read, stamped with provenance."""

    mint: str
    freezable: float | None
    mintable: float | None
    nontransf: float | None
    thook: float | None
    source: str
    retrieved_at: str  # ISO 8601 UTC

    def as_features(self) -> dict[str, float | None]:
        return {
            "freezable": self.freezable,
            "mintable": self.mintable,
            "nontransf": self.nontransf,
            "thook": self.thook,
        }


def _status_flag(value: Any) -> float | None:
    """``{"status": "0"/"1"}`` → 0.0/1.0; anything else undecodable → None."""
    if isinstance(value, Mapping):
        status = value.get("status")
        if status in ("0", "1", 0, 1):
            return float(int(status))
    return None


def _string_flag(value: Any) -> float | None:
    if value in ("0", "1", 0, 1):
        return float(int(value))
    return None


def _list_flag(value: Any) -> float | None:
    if isinstance(value, list):
        return 1.0 if value else 0.0
    return None


class GoPlusClient:
    """Keyless client for the Solana token-security endpoint, paced."""

    def __init__(
        self,
        *,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._client = httpx.Client(
            base_url=GOPLUS_BASE_URL,
            timeout=timeout_s,
            transport=transport,
            headers={"accept": "application/json"},
        )
        self._min_interval_s = min_interval_s
        self._sleep = sleep
        self._monotonic = monotonic
        self._now = now
        self._last_request_at = float("-inf")

    def close(self) -> None:
        self._client.close()

    def _pace(self) -> None:
        wait = self._last_request_at + self._min_interval_s - self._monotonic()
        if wait > 0:
            self._sleep(wait)
        self._last_request_at = self._monotonic()

    def token_security(self, mint: str) -> TokenSecurity | None:
        """The four flags for one mint, or None when GoPlus does not know it."""
        self._pace()
        try:
            resp = self._client.get("/solana/token_security", params={"contract_addresses": mint})
        except httpx.HTTPError as exc:
            raise GoPlusError(f"transport error ({type(exc).__name__})") from None
        if resp.status_code != 200:
            raise GoPlusError(f"HTTP {resp.status_code}")
        result = resp.json().get("result") or {}
        token = result.get(mint)
        if not isinstance(token, Mapping):
            return None
        return TokenSecurity(
            mint=mint,
            freezable=_status_flag(token.get("freezable")),
            mintable=_status_flag(token.get("mintable")),
            nontransf=_string_flag(token.get("non_transferable")),
            thook=_list_flag(token.get("transfer_hook")),
            source=SOURCE_NAME,
            retrieved_at=self._now().isoformat(),
        )
