"""Parse path: leakage suite extended FIRST, then the event definitions pinned.

The domain's labels are defined by future events, so the trap lives exactly
here: a parse that reads past the window would leak the future into every
downstream feature. Before any real feature is computed from live data,
these tests extend the two leakage defenses to the parse path over synthetic
enhanced-payload fixtures:

1. **Prefix invariance** — payload sets identical inside the window and
   differing after it must parse to identical features.
2. **Planted-future canary** — a deliberately leaky parse (out-of-window
   timestamps CLAMPED into the window instead of excluded) must be CAUGHT by
   that same comparison, proving the detector has teeth.

The remaining tests pin the registered event definitions, above all the
swap-direction rule: mint INTO the pool is a sell, mint OUT of the pool is a
pool-funded transfer, so pool-funded buyers never enter the creator-funded
insider set.
"""

from __future__ import annotations

from typing import Any

from solclear import features as feat
from solclear.parse import parse_window

MINT = "MintM1111111111111111111111111111111111111"
POOL = "PoolP1111111111111111111111111111111111111"
CREATOR = "CreatorWallet111111111111111111111111111111"
T0 = 1_720_000_000.0
END = T0 + 1_800.0


def _tt(frm: str, to: str, amount: float, mint: str = MINT) -> dict[str, Any]:
    return {"mint": mint, "fromUserAccount": frm, "toUserAccount": to, "tokenAmount": amount}


def _payload(
    ts: float,
    transfers: list[dict[str, Any]] | None = None,
    *,
    ttype: str = "TRANSFER",
    fee_payer: str = "FeePayer111",
    err: str | None = None,
    signature: str = "sig",
) -> dict[str, Any]:
    return {
        "signature": signature,
        "timestamp": ts,
        "type": ttype,
        "feePayer": fee_payer,
        "transactionError": err,
        "tokenTransfers": transfers or [],
    }


def _base_payloads() -> list[dict[str, Any]]:
    return [
        _payload(T0, [_tt("", CREATOR, 1_000.0)], ttype="TOKEN_MINT"),  # mint_to
        _payload(T0 + 60, [_tt(CREATOR, "early1", 200.0)]),  # creator funds early1
        _payload(T0 + 90, [_tt(POOL, "buyer1", 50.0)], ttype="SWAP"),  # buy: pool -> buyer
        _payload(T0 + 120, [_tt(CREATOR, POOL, 100.0)], ttype="SWAP"),  # sell: creator -> pool
        _payload(T0 + 150, [], ttype="SET_AUTHORITY", fee_payer=CREATOR, signature=MINT),
    ]


def _features_via_parse(payloads: list[dict[str, Any]]) -> dict[str, float | None]:
    parsed = parse_window(payloads, mint=MINT, pool_address=POOL, t0_s=T0, end_s=END)
    assert parsed.report.unparseable == 0
    assert parsed.creator == CREATOR
    return feat.features(list(parsed.events), T0, parsed.creator or "", None)


# ------------------- leakage defenses through the parse path ----------------- #


def test_parse_path_is_prefix_invariant_beyond_the_window() -> None:
    base = _base_payloads()
    noisy = [*base, _payload(END + 600, [_tt(CREATOR, POOL, 900.0)], ttype="SWAP")]

    assert _features_via_parse(base) == _features_via_parse(noisy)


def test_canary_a_parse_clamping_the_future_into_the_window_is_detected() -> None:
    # The leaky variant, planted on purpose: instead of EXCLUDING out-of-window
    # payloads, it CLAMPS their timestamps to just inside the window end — the
    # exact bug shape the parent project's window guard exists for. Note the
    # honest parse's mere inclusion of later events cannot leak, because
    # features() re-clamps to its own window; clamped TIMESTAMPS are the leak.
    def leaky(payloads: list[dict[str, Any]]) -> dict[str, float | None]:
        clamped = [
            {**p, "timestamp": min(float(p["timestamp"]), END - 1.0)}
            if isinstance(p.get("timestamp"), int | float)
            else p
            for p in payloads
        ]
        parsed = parse_window(clamped, mint=MINT, pool_address=POOL, t0_s=T0, end_s=END)
        return feat.features(list(parsed.events), T0, parsed.creator or "", None)

    base = _base_payloads()
    future = [*base, _payload(END + 600, [_tt(CREATOR, POOL, 900.0)], ttype="SWAP")]

    # The real parse must not move...
    assert _features_via_parse(base) == _features_via_parse(future)
    # ...and the same comparison must FLAG the leaky variant, or it proves nothing.
    assert leaky(base) != leaky(future), (
        "the invariance check failed to catch a parse that reads the future"
    )


# ------------------------ registered event definitions ----------------------- #


def test_known_answer_events_kinds_direction_and_creator() -> None:
    parsed = parse_window(_base_payloads(), mint=MINT, pool_address=POOL, t0_s=T0, end_s=END)

    kinds = [(e.kind, e.wallet) for e in parsed.events]
    assert kinds == [
        ("mint_to", CREATOR),
        ("transfer", "early1"),
        ("transfer", "buyer1"),  # buy: M out of the pool, funded BY the pool
        ("sell", CREATOR),  # sell: M into the pool
        ("revoke_authority", CREATOR),
    ]
    # The swap-direction rule, both directions explicit:
    sell = parsed.events[3]
    assert sell.kind == "sell" and sell.wallet == CREATOR
    buy = parsed.events[2]
    assert buy.source == POOL  # pool-funded, so never creator-funded-insider
    assert parsed.creator == CREATOR
    assert parsed.report.parsed == 5
    assert parsed.report.unparseable == 0


def test_pool_funded_buyers_do_not_enter_the_creator_insider_set() -> None:
    parsed = parse_window(_base_payloads(), mint=MINT, pool_address=POOL, t0_s=T0, end_s=END)
    insiders = feat.insider_set(list(parsed.events), CREATOR, END)
    assert "early1" in insiders  # creator-funded: insider
    assert "buyer1" not in insiders  # pool-funded: not an insider


def test_unparseable_is_counted_never_dropped() -> None:
    payloads = [
        _payload(T0 + 10, [_tt("", CREATOR, 1_000.0)]),
        _payload(
            T0 + 20,
            [{"mint": MINT, "fromUserAccount": CREATOR, "toUserAccount": POOL, "tokenAmount": "x"}],
        ),
        {"signature": "no-timestamp"},
    ]
    parsed = parse_window(payloads, mint=MINT, pool_address=POOL, t0_s=T0, end_s=END)
    assert parsed.report.unparseable == 2
    assert parsed.report.parsed == 1
    assert parsed.report.total == 3


def test_failed_and_out_of_window_and_foreign_mint_payloads_are_ignored() -> None:
    payloads = [
        _payload(T0 + 10, [_tt(CREATOR, POOL, 5.0)], err="InstructionError"),
        _payload(T0 - 5, [_tt("", CREATOR, 10.0)]),  # before the window
        _payload(END, [_tt(CREATOR, POOL, 5.0)]),  # exactly at end: outside [t0, end)
        _payload(T0 + 30, [_tt("a", "b", 5.0, mint="OtherMint111")]),
    ]
    parsed = parse_window(payloads, mint=MINT, pool_address=POOL, t0_s=T0, end_s=END)
    assert parsed.report.ignored == 4
    assert parsed.report.parsed == 0
    assert parsed.report.unparseable == 0
    assert parsed.events == ()


def test_creator_falls_back_to_earliest_fee_payer_without_a_mint_to() -> None:
    payloads = [
        _payload(T0 + 40, [_tt("w1", "w2", 5.0)], fee_payer="LatePayer"),
        _payload(T0 + 20, [_tt("w2", "w3", 5.0)], fee_payer="EarlyPayer"),
    ]
    parsed = parse_window(payloads, mint=MINT, pool_address=POOL, t0_s=T0, end_s=END)
    assert parsed.creator == "EarlyPayer"
