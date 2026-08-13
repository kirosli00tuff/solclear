"""Transport semantics: errors raise, skipped slots stay None, pacing is real.

These pin the two Stage C Task 3 fixes against a mock transport:

1. A JSON-RPC error is a transport fact and RAISES; only the chain's
   skipped-slot codes (-32007/-32009) are data facts mapping to None/[].
   The defect this closes: a transient node error silently absorbed as
   "slot skipped", corrupting the binary search from inside.
2. Rate limiting is an explicit policy — minimum spacing between requests,
   429 retried with backoff honouring Retry-After — with the measured
   free-tier defaults, not the documented ones.

The API key never appears in any exception message.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from solclear.rpc import HeliusRpc, RatePolicy, RpcError

KEY = "test-key-59a1e2c7"


class FakeClock:
    """Deterministic monotonic clock; sleeping advances it and is recorded."""

    def __init__(self) -> None:
        self.now = 1_000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _rpc(
    responses: list[httpx.Response], policy: RatePolicy | None = None
) -> tuple[HeliusRpc, FakeClock, list[httpx.Request]]:
    """A client whose transport replays canned responses and records requests."""
    seen: list[httpx.Request] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return queue.pop(0)

    clock = FakeClock()
    rpc = HeliusRpc(
        KEY,
        policy=policy or RatePolicy(),
        transport=httpx.MockTransport(handler),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )
    return rpc, clock, seen


def _ok(result: Any) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})


def _rpc_error(code: int) -> httpx.Response:
    return httpx.Response(
        200, json={"jsonrpc": "2.0", "id": 1, "error": {"code": code, "message": "node says no"}}
    )


# --------------------- errors raise; skipped slots stay ---------------------- #


def test_json_rpc_error_raises_instead_of_reading_as_skipped() -> None:
    # The Stage B defect: this used to return None, indistinguishable from a
    # legitimately skipped slot, and the binary search scanned on.
    rpc, _, _ = _rpc([_rpc_error(-32602)])
    with pytest.raises(RpcError, match=r"getBlockTime: JSON-RPC error -32602"):
        rpc.block_time(123)


def test_block_not_available_error_raises_rather_than_skipping() -> None:
    # -32004 is transient near the tip; retrying is the caller's decision.
    rpc, _, _ = _rpc([_rpc_error(-32004)])
    with pytest.raises(RpcError, match="-32004"):
        rpc.block_time(123)


@pytest.mark.parametrize("code", [-32007, -32009])
def test_skipped_slot_codes_remain_none_for_block_time(code: int) -> None:
    rpc, _, _ = _rpc([_rpc_error(code)])
    assert rpc.block_time(123) is None


@pytest.mark.parametrize("code", [-32007, -32009])
def test_skipped_slot_codes_remain_empty_for_block_signatures(code: int) -> None:
    rpc, _, _ = _rpc([_rpc_error(code)])
    assert rpc.block_signatures(123) == []


def test_get_block_error_raises_instead_of_reading_as_empty() -> None:
    # An empty block and a failed getBlock are different facts.
    rpc, _, _ = _rpc([_rpc_error(-32602)])
    with pytest.raises(RpcError, match="getBlock: JSON-RPC error"):
        rpc.block_signatures(123)


def test_null_result_is_none_and_real_result_is_int() -> None:
    rpc, _, _ = _rpc([_ok(None), _ok(1_723_500_000)])
    assert rpc.block_time(1) is None
    assert rpc.block_time(2) == 1_723_500_000


def test_error_messages_never_contain_the_api_key() -> None:
    rpc, _, _ = _rpc([_rpc_error(-32602)])
    with pytest.raises(RpcError) as err:
        rpc.block_time(123)
    assert KEY not in str(err.value)


# ------------------------- pacing and 429 handling -------------------------- #


def test_requests_are_paced_to_the_policy_interval() -> None:
    rpc, clock, _ = _rpc([_ok(1), _ok(2)], policy=RatePolicy(min_interval_s=0.15))
    rpc.latest_slot()
    rpc.latest_slot()  # immediate second call must wait out the interval
    assert clock.sleeps == [pytest.approx(0.15)]


def test_429_is_retried_with_backoff_and_succeeds() -> None:
    rpc, clock, seen = _rpc(
        [httpx.Response(429), httpx.Response(429), _ok(77)],
        policy=RatePolicy(min_interval_s=0.0, backoff_base_s=1.0, backoff_cap_s=8.0),
    )
    assert rpc.latest_slot() == 77
    assert len(seen) == 3
    assert clock.sleeps == [pytest.approx(1.0), pytest.approx(2.0)]  # 1*2^0, 1*2^1


def test_429_honours_retry_after_when_larger_than_backoff() -> None:
    rpc, clock, _ = _rpc(
        [httpx.Response(429, headers={"retry-after": "5"}), _ok(1)],
        policy=RatePolicy(min_interval_s=0.0, backoff_base_s=1.0),
    )
    rpc.latest_slot()
    assert clock.sleeps == [pytest.approx(5.0)]


def test_persistent_429_raises_after_max_retries() -> None:
    policy = RatePolicy(min_interval_s=0.0, max_retries_429=2, backoff_base_s=0.1)
    rpc, _, seen = _rpc([httpx.Response(429)] * 3, policy=policy)
    with pytest.raises(RpcError, match="HTTP 429 after 2 retries"):
        rpc.latest_slot()
    assert len(seen) == 3  # initial attempt + 2 retries, then a refusal


def test_request_body_is_well_formed_jsonrpc() -> None:
    rpc, _, seen = _rpc([_ok(42)])
    assert rpc.latest_slot() == 42
    body = json.loads(seen[0].content)
    assert body["method"] == "getSlot"
    assert body["jsonrpc"] == "2.0"
