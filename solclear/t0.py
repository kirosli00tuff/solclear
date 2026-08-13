"""T0 acquisition: the question ADR-004 says precedes the rest of the live path.

Two paths, deliberately separate (Stage C Task 4):

**Live** — the scanner's case (Stage D): pool creation is observed as it
happens, so T0 costs nothing and is first-party. Only the interface is
defined here (:class:`LiveT0Source`); nothing in this repository implements
it yet.

**Retrospective** — a mint is resolved to its pools via GeckoTerminal's
keyless API and the earliest ``pool_created_at`` is read. The addendum
verified this resolves 6 of 6 pre-registered 2024 mints, including dead
pairs DexScreener has forgotten. The result is an *external claim*, typed as
:class:`T0Claim` and stamped with source and retrieval time: Method B
anchors to the slot at or after it and the window derives from it, but the
tolerance between the claimed creation time and on-chain first activity is
**measured** (Stage C Task 4's live measurement), never assumed zero.

Pacing: GeckoTerminal documents 30 req/min but 429'd the addendum's pager at
2.5 s spacing; 6 s spacing held (measured 2026-08-13). The default interval
records the measurement, not the docs.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx

GECKO_BASE_URL = "https://api.geckoterminal.com/api/v2"
SOURCE_NAME = "geckoterminal:token_pools"
# Measured, not documented: 2.5 s spacing 429'd on 2026-08-13; 6 s held.
DEFAULT_MIN_INTERVAL_S = 6.0
DEFAULT_TIMEOUT_S = 20.0
# GeckoTerminal's edge blocks default library user agents (urllib was 403'd
# on 2026-08-13); a descriptive UA passed.
_USER_AGENT = "solclear/0.1 (research; github.com/kirosli00tuff/solclear)"


class LiveT0Source(Protocol):
    """The scanner's T0 path: creations observed as they happen, first-party.

    Yields ``(pool_address, mint, t0_s)`` as pools are created. Costs no
    credits and involves no external claim — the observer saw the creation.
    Implementation belongs to the Stage D scanner; this interface exists so
    the pipeline can be written against both T0 paths now.
    """

    def stream(self) -> Iterator[tuple[str, str, int]]: ...


@dataclass(frozen=True)
class T0Claim:
    """A pool's claimed launch time, from an external source, stamped as such.

    ``claimed_t0_s`` is treated as a claim, not a fact: the measured offset
    between claimed creation and on-chain first activity travels in the Stage
    C progress entry, and Method B fetches derive their window from the claim
    only after that tolerance was measured.
    """

    mint: str
    pool_address: str
    dex: str
    claimed_t0_s: int
    source: str
    source_url: str
    retrieved_at: str  # ISO 8601 UTC


class T0ResolutionError(RuntimeError):
    """The resolver could not produce a claim (transport or malformed body)."""


def _parse_created_at(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


class GeckoTerminalResolver:
    """Keyless retrospective T0 resolver over GeckoTerminal token→pools.

    Picks the pool with the EARLIEST ``pool_created_at`` — the launch pool —
    rather than the first row the API happens to order first. Returns None
    when the mint resolves to no pools (reported and excluded by callers,
    never substituted). Requests are paced to the measured interval and a
    single 429 retry waits ``retry_429_wait_s`` before failing loudly.
    """

    def __init__(
        self,
        *,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        retry_429_wait_s: float = 30.0,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._client = httpx.Client(
            base_url=GECKO_BASE_URL,
            timeout=timeout_s,
            transport=transport,
            headers={"accept": "application/json", "user-agent": _USER_AGENT},
        )
        self._min_interval_s = min_interval_s
        self._retry_429_wait_s = retry_429_wait_s
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

    def _get(self, path: str) -> httpx.Response:
        self._pace()
        try:
            resp = self._client.get(path)
        except httpx.HTTPError as exc:
            raise T0ResolutionError(f"transport error ({type(exc).__name__})") from None
        if resp.status_code == 429:
            self._sleep(self._retry_429_wait_s)
            self._last_request_at = self._monotonic()
            resp = self._client.get(path)
        return resp

    def resolve(self, mint: str) -> T0Claim | None:
        path = f"/networks/solana/tokens/{mint}/pools"
        resp = self._get(path)
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise T0ResolutionError(f"HTTP {resp.status_code} resolving a mint")
        pools: list[dict[str, Any]] = resp.json().get("data") or []
        if not pools:
            return None
        earliest = min(pools, key=lambda p: _parse_created_at(p["attributes"]["pool_created_at"]))
        attrs = earliest["attributes"]
        return T0Claim(
            mint=mint,
            pool_address=str(attrs["address"]),
            dex=str(earliest["relationships"]["dex"]["data"]["id"]),
            claimed_t0_s=_parse_created_at(str(attrs["pool_created_at"])),
            source=SOURCE_NAME,
            source_url=f"{GECKO_BASE_URL}{path}",
            retrieved_at=self._now().isoformat(),
        )
