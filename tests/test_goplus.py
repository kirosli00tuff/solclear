"""GoPlus client: measured shapes parse, drift fails closed, provenance travels.

The undecodable-field behaviour is the load-bearing one: a schema drift maps
to None, and None is an absent required feature downstream, so the scorer
REFUSES rather than reading vendor drift as "no risk flags" (ADR-006).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from solclear.goplus import SOURCE_NAME, GoPlusClient, TokenSecurity

MINT = "MintGP111111111111111111111111111111111111"


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _client(responses: list[httpx.Response]) -> tuple[GoPlusClient, FakeClock]:
    queue = list(responses)
    clock = FakeClock()
    client = GoPlusClient(
        min_interval_s=2.0,
        transport=httpx.MockTransport(lambda req: queue.pop(0)),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        now=lambda: datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC),
    )
    return client, clock


def _body(token: dict[str, Any] | None) -> dict[str, Any]:
    return {"code": 1, "message": "ok", "result": {} if token is None else {MINT: token}}


def test_measured_schema_shapes_parse_to_the_four_features() -> None:
    # The shapes as MEASURED 2026-08-13: status-dicts, a bare string, a list.
    token = {
        "freezable": {"authority": [], "status": "0"},
        "mintable": {"authority": ["SomeAuth"], "status": "1"},
        "non_transferable": "0",
        "transfer_hook": ["hook111"],
    }
    client, _ = _client([httpx.Response(200, json=_body(token))])

    sec = client.token_security(MINT)

    assert isinstance(sec, TokenSecurity)
    assert sec.as_features() == {
        "freezable": 0.0,
        "mintable": 1.0,
        "nontransf": 0.0,
        "thook": 1.0,
    }
    assert sec.source == SOURCE_NAME
    assert sec.retrieved_at.startswith("2026-08-13T12:00:00")


def test_undecodable_shapes_map_to_none_which_refuses_downstream() -> None:
    # Schema drift must fail closed: None is an absent required feature and
    # the scorer refuses — never a guessed 0.0 reading as "no risk flags".
    token = {
        "freezable": {"no_status_key": True},
        "mintable": "maybe",
        "non_transferable": 2,
        "transfer_hook": {"status": "1"},
    }
    client, _ = _client([httpx.Response(200, json=_body(token))])

    sec = client.token_security(MINT)

    assert sec is not None
    assert sec.as_features() == {
        "freezable": None,
        "mintable": None,
        "nontransf": None,
        "thook": None,
    }


def test_unknown_token_returns_none() -> None:
    client, _ = _client([httpx.Response(200, json=_body(None))])
    assert client.token_security(MINT) is None


def test_requests_are_paced() -> None:
    client, clock = _client(
        [httpx.Response(200, json=_body(None)), httpx.Response(200, json=_body(None))]
    )
    client.token_security(MINT)
    client.token_security(MINT)
    assert clock.sleeps == [2.0]
