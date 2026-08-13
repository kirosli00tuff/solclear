"""Thin Helius JSON-RPC transport implementing the Method B client protocol.

Does no pricing of its own — wrap it in :class:`solclear.method_b.GatedRpc` so
every request is charged before it is sent. Transport errors are re-raised as
:class:`RpcError` carrying the method name only: the request URL embeds the
API key and must never appear in an exception message or a log line.

**Errors raise; skipped slots remain None** (Stage C Task 3, fixing a defect
Stage B named): a JSON-RPC error is a *transport fact* and raises
:class:`RpcError` naming the method and code — with exactly two exceptions,
the chain's skipped/missing-slot codes (-32007, -32009), which are *data
facts* about the slot and map to ``None``/``[]``. Under the old behaviour a
transient node error was silently absorbed as "slot skipped" and the binary
search scanned on past it. Code -32004 ("block not available", transient
near the tip) deliberately raises: retrying it is the caller's decision, not
something to disguise as a skip.

**Rate limiting is an explicit policy, not a hidden sleep** (same task):
Stage B measured the free tier returning HTTP 429 mid-binary-search despite
the documented 10 RPS, and the addendum measured GeckoTerminal 429ing below
its documented limit too — documented limits and real limits differ, so
:class:`RatePolicy`'s defaults record what was measured (150 ms spacing held
on 2026-08-12), and 429 responses are retried with exponential backoff,
honouring ``Retry-After`` when the server sends one.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

import httpx

from solclear.method_b import SigInfo

DEFAULT_BASE_URL = "https://mainnet.helius-rpc.com"
DEFAULT_TIMEOUT_S = 30.0

# The chain's "this slot has no block" JSON-RPC codes — data, not errors:
# -32007 "Slot was skipped, or missing due to ledger jump"; -32009 "Slot was
# skipped, or missing in long-term storage".
_SKIPPED_SLOT_CODES: Final = frozenset({-32007, -32009})
_SLOT_SKIPPED: Final = object()


class RpcError(RuntimeError):
    """An RPC call failed. The message names the method, never the URL."""


@dataclass(frozen=True)
class RatePolicy:
    """Request pacing and 429 handling, visible and configurable.

    Defaults record the *measured* free-tier behaviour (Stage B, 2026-08-12:
    bursts 429'd; 150 ms spacing held), not the documented limit. Set
    ``min_interval_s=0`` for a paid tier where pacing is unnecessary.
    """

    min_interval_s: float = 0.15
    max_retries_429: int = 4
    backoff_base_s: float = 1.0
    backoff_cap_s: float = 8.0


class HeliusRpc:
    """Synchronous JSON-RPC client for the four calls Method B needs."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        policy: RatePolicy | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout_s, transport=transport)
        self._path = f"/?api-key={api_key}"
        self._policy = policy if policy is not None else RatePolicy()
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at = float("-inf")

    def close(self) -> None:
        self._client.close()

    def _pace(self) -> None:
        if self._policy.min_interval_s <= 0:
            return
        wait = self._last_request_at + self._policy.min_interval_s - self._monotonic()
        if wait > 0:
            self._sleep(wait)
        self._last_request_at = self._monotonic()

    def _retry_delay_s(self, resp: httpx.Response, attempt: int) -> float:
        backoff = min(self._policy.backoff_cap_s, self._policy.backoff_base_s * (2.0**attempt))
        retry_after = resp.headers.get("retry-after")
        if retry_after is not None:
            try:
                return max(backoff, float(retry_after))
            except ValueError:
                pass
        return backoff

    def _post(self, method: str, params: list[Any]) -> httpx.Response:
        attempt = 0
        while True:
            self._pace()
            try:
                resp = self._client.post(
                    self._path,
                    json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                )
            except httpx.HTTPError as exc:  # redact: httpx messages can embed the URL
                raise RpcError(f"{method}: transport error ({type(exc).__name__})") from None
            if resp.status_code == 429 and attempt < self._policy.max_retries_429:
                self._sleep(self._retry_delay_s(resp, attempt))
                attempt += 1
                continue
            return resp

    def _call(self, method: str, params: list[Any]) -> Any:
        resp = self._post(method, params)
        if resp.status_code == 429:
            raise RpcError(f"{method}: HTTP 429 after {self._policy.max_retries_429} retries")
        if resp.status_code != 200:
            raise RpcError(f"{method}: HTTP {resp.status_code}")
        payload = resp.json()
        if "error" in payload:
            code = payload["error"].get("code")
            if code in _SKIPPED_SLOT_CODES:
                return _SLOT_SKIPPED
            raise RpcError(f"{method}: JSON-RPC error {code}")
        return payload.get("result")

    def latest_slot(self) -> int:
        result = self._call("getSlot", [])
        if not isinstance(result, int):
            raise RpcError("getSlot: non-integer result")
        return result

    def block_time(self, slot: int) -> int | None:
        """Unix seconds, or None ONLY when the chain reports the slot skipped.

        A JSON-RPC error other than the skipped-slot codes raises — a
        transient node failure must never be read as "slot skipped"
        (Stage C Task 3; the old conflation would silently corrupt the
        binary search).
        """
        result = self._call("getBlockTime", [slot])
        if result is _SLOT_SKIPPED or result is None:
            return None
        if not isinstance(result, int):
            raise RpcError("getBlockTime: non-integer result")
        return result

    def block_signatures(self, slot: int) -> list[str]:
        """Signatures in a block; empty ONLY when the chain reports it skipped."""
        result = self._call(
            "getBlock",
            [
                slot,
                {
                    "transactionDetails": "signatures",
                    "rewards": False,
                    "maxSupportedTransactionVersion": 0,
                },
            ],
        )
        if result is _SLOT_SKIPPED:
            return []
        if not isinstance(result, dict):
            raise RpcError("getBlock: non-object result")
        return [str(s) for s in result.get("signatures", [])]

    def signatures_for_address(self, address: str, before: str | None, limit: int) -> list[SigInfo]:
        opts: dict[str, Any] = {"limit": limit}
        if before is not None:
            opts["before"] = before
        result = self._call("getSignaturesForAddress", [address, opts])
        if not isinstance(result, list):
            raise RpcError("getSignaturesForAddress: non-list result")
        return [
            SigInfo(
                signature=str(item["signature"]),
                slot=int(item["slot"]),
                block_time_s=int(item["blockTime"]) if item.get("blockTime") is not None else None,
                err=item.get("err") is not None,
            )
            for item in result
        ]
