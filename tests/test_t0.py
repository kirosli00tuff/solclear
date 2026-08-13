"""T0 resolver: earliest pool wins, claims are stamped, absence is None.

The resolver's output is an external CLAIM (Stage C Task 4): these tests pin
that every claim carries its source and retrieval timestamp, that the
earliest-created pool is chosen over whatever ordering the API returns, and
that an unresolvable mint is None — reported and excluded by callers, never
substituted or defaulted.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from solclear.t0 import SOURCE_NAME, GeckoTerminalResolver, T0Claim

MINT = "MintAAAA1111111111111111111111111111111111"


def _pool(address: str, created: str, dex: str = "raydium") -> dict[str, Any]:
    return {
        "attributes": {"address": address, "pool_created_at": created},
        "relationships": {"dex": {"data": {"id": dex}}},
    }


class FakeClock:
    def __init__(self) -> None:
        self.now = 5_000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _resolver(
    responses: list[httpx.Response], min_interval_s: float = 6.0
) -> tuple[GeckoTerminalResolver, FakeClock, list[httpx.Request]]:
    seen: list[httpx.Request] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return queue.pop(0)

    clock = FakeClock()
    resolver = GeckoTerminalResolver(
        min_interval_s=min_interval_s,
        retry_429_wait_s=30.0,
        transport=httpx.MockTransport(handler),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        now=lambda: datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC),
    )
    return resolver, clock, seen


def test_resolution_picks_the_earliest_created_pool_not_the_first_row() -> None:
    # The API's first row is a LATER pool; the launch pool is second.
    body = {
        "data": [
            _pool("PoolLater", "2025-01-01T00:00:00Z", dex="pumpswap"),
            _pool("PoolLaunch", "2024-05-02T11:56:47Z", dex="raydium"),
        ]
    }
    resolver, _, _ = _resolver([httpx.Response(200, json=body)])

    claim = resolver.resolve(MINT)

    assert isinstance(claim, T0Claim)
    assert claim.pool_address == "PoolLaunch"
    assert claim.dex == "raydium"
    assert claim.claimed_t0_s == int(datetime(2024, 5, 2, 11, 56, 47, tzinfo=UTC).timestamp())


def test_every_claim_is_stamped_with_source_and_retrieval_time() -> None:
    body = {"data": [_pool("PoolA", "2024-07-03T05:25:29Z")]}
    resolver, _, _ = _resolver([httpx.Response(200, json=body)])

    claim = resolver.resolve(MINT)

    assert claim is not None
    assert claim.source == SOURCE_NAME
    assert MINT in claim.source_url
    assert claim.retrieved_at == "2026-08-13T12:00:00+00:00"


def test_unknown_mint_and_empty_pools_resolve_to_none() -> None:
    resolver, _, _ = _resolver(
        [httpx.Response(404, json={"errors": []}), httpx.Response(200, json={"data": []})]
    )
    assert resolver.resolve(MINT) is None
    assert resolver.resolve(MINT) is None


def test_requests_are_paced_to_the_measured_interval() -> None:
    body = {"data": [_pool("PoolA", "2024-07-03T05:25:29Z")]}
    resolver, clock, _ = _resolver([httpx.Response(200, json=body), httpx.Response(200, json=body)])
    resolver.resolve(MINT)
    resolver.resolve(MINT)
    assert clock.sleeps == [6.0]  # second call waited out the measured interval


def test_a_429_is_retried_once_after_the_registered_wait() -> None:
    body = {"data": [_pool("PoolA", "2024-07-03T05:25:29Z")]}
    resolver, clock, seen = _resolver([httpx.Response(429), httpx.Response(200, json=body)])

    claim = resolver.resolve(MINT)

    assert claim is not None
    assert len(seen) == 2
    assert 30.0 in clock.sleeps
