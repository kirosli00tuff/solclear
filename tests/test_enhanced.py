"""Enhanced client: priced before use, batch bounds explicit, refusal sends nothing.

The gate weight for ``enhanced`` was corrected to the vendor's 100/call
before this client existed; these tests pin that the client cannot spend
around that ordering: every call is charged first, an over-cap charge sends
no request, and an over-sized batch refuses rather than silently splitting
into more (billable) calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from solclear.config import Settings
from solclear.enhanced import (
    MAX_SIGNATURES_PER_CALL,
    EnhancedClient,
    GatedEnhanced,
    calls_needed,
)
from solclear.gate import CreditCapError, CreditGate
from solclear.rpc import RatePolicy, RpcError

KEY = "test-key-77e1b9"


def _client(
    responses: list[httpx.Response],
) -> tuple[EnhancedClient, list[httpx.Request], list[float]]:
    seen: list[httpx.Request] = []
    sleeps: list[float] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return queue.pop(0)

    clock = {"now": 0.0}

    def sleep(s: float) -> None:
        sleeps.append(s)
        clock["now"] += s

    client = EnhancedClient(
        KEY,
        policy=RatePolicy(min_interval_s=0.0, max_retries_429=1, backoff_base_s=0.5),
        transport=httpx.MockTransport(handler),
        sleep=sleep,
        monotonic=lambda: clock["now"],
    )
    return client, seen, sleeps


def _ok(body: list[dict[str, Any]]) -> httpx.Response:
    return httpx.Response(200, json=body)


def test_calls_needed_prices_a_window_before_any_call() -> None:
    assert calls_needed(1) == 1
    assert calls_needed(100) == 1
    assert calls_needed(101) == 2
    assert calls_needed(1_000) == 10


def test_oversized_batch_refuses_rather_than_silently_splitting() -> None:
    client, seen, _ = _client([])
    with pytest.raises(ValueError, match="exceeds 100"):
        client.transactions([f"sig{i}" for i in range(MAX_SIGNATURES_PER_CALL + 1)])
    assert seen == []  # nothing was sent, nothing could be billed


def test_empty_batch_refuses() -> None:
    client, seen, _ = _client([])
    with pytest.raises(ValueError, match="empty"):
        client.transactions([])
    assert seen == []


def test_transactions_posts_the_batch_and_returns_the_parsed_list() -> None:
    client, seen, _ = _client([_ok([{"signature": "sigA"}, {"signature": "sigB"}])])
    out = client.transactions(["sigA", "sigB"])
    assert [t["signature"] for t in out] == ["sigA", "sigB"]
    assert b'"transactions"' in seen[0].content


def test_gated_client_charges_before_sending(tmp_path: Path) -> None:
    inner, seen, _ = _client([_ok([])])
    gate = CreditGate(Settings(helius_credit_cap=150, data_root=tmp_path), tmp_path / "l.jsonl")

    GatedEnhanced(inner, gate).transactions(["sigA"])

    assert gate.spent() == 100  # the corrected vendor price, charged as one call
    assert len(seen) == 1


def test_gate_refusal_sends_no_request_and_writes_nothing(tmp_path: Path) -> None:
    inner, seen, _ = _client([_ok([])])
    gate = CreditGate(Settings(helius_credit_cap=99, data_root=tmp_path), tmp_path / "l.jsonl")

    with pytest.raises(CreditCapError):
        GatedEnhanced(inner, gate).transactions(["sigA"])

    assert seen == []  # refused before the transport was touched
    assert gate.spent() == 0


def test_persistent_429_raises_and_names_no_key() -> None:
    client, _, _ = _client([httpx.Response(429), httpx.Response(429)])
    with pytest.raises(RpcError) as err:
        client.transactions(["sigA"])
    assert "429" in str(err.value)
    assert KEY not in str(err.value)
