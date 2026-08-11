"""Method B: known-answer retrieval, depth independence, and gated pricing.

The fake chain is deterministic: slot ``s`` closes at ``GENESIS_TS + s`` (one
second per slot), every non-skipped slot carries a filler signature (so the
seed is a *foreign* signature — the measured C.25 property that ``before``
accepts one), and the target address's signatures sit at known slots. The
known answer is therefore exact: the window fetch must return precisely the
in-window signatures, in ascending order, and nothing else.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from solclear.config import Settings
from solclear.gate import CreditCapError, CreditGate
from solclear.method_b import (
    GatedRpc,
    RetrievalError,
    SigInfo,
    WindowFetch,
    fetch_window,
    seed_signature,
    slot_at_or_after,
)

GENESIS_TS = 1_700_000_000
POOL = "PooLAddr1111111111111111111111111111111111"


class FakeRpc:
    """A deterministic chain: 1 slot/second, filler sig per block, counted calls."""

    def __init__(
        self,
        tip_slot: int,
        addr_slots: list[int],
        skipped: set[int] | None = None,
    ) -> None:
        self.tip_slot = tip_slot
        self.skipped = skipped or set()
        # Address signatures ordered by slot; seq = slot * 10 + 1 (filler = slot * 10).
        self.addr_sigs = [
            SigInfo(signature=f"pool{s}", slot=s, block_time_s=GENESIS_TS + s)
            for s in sorted(addr_slots)
        ]
        self.calls = {
            "latest_slot": 0,
            "block_time": 0,
            "block_signatures": 0,
            "signatures_for_address": 0,
        }

    def _seq(self, signature: str) -> int:
        if signature.startswith("blk"):
            return int(signature[3:]) * 10
        if signature.startswith("pool"):
            return int(signature[4:]) * 10 + 1
        raise AssertionError(f"unknown signature {signature}")

    def latest_slot(self) -> int:
        self.calls["latest_slot"] += 1
        return self.tip_slot

    def block_time(self, slot: int) -> int | None:
        self.calls["block_time"] += 1
        if slot in self.skipped or slot > self.tip_slot:
            return None
        return GENESIS_TS + slot

    def block_signatures(self, slot: int) -> list[str]:
        self.calls["block_signatures"] += 1
        if slot in self.skipped or slot > self.tip_slot:
            return []
        sigs = [f"blk{slot}"]
        sigs.extend(s.signature for s in self.addr_sigs if s.slot == slot)
        return sigs

    def signatures_for_address(self, address: str, before: str | None, limit: int) -> list[SigInfo]:
        self.calls["signatures_for_address"] += 1
        assert address == POOL
        cut = self._seq(before) if before is not None else 10 * (self.tip_slot + 1)
        older = [s for s in self.addr_sigs if self._seq(s.signature) < cut]
        older.sort(key=lambda s: self._seq(s.signature), reverse=True)
        return older[:limit]

    def total_calls(self) -> int:
        return sum(self.calls.values())


def _window(rpc: FakeRpc | GatedRpc, **kwargs: int) -> WindowFetch:
    return fetch_window(rpc, POOL, t0_s=GENESIS_TS + 1_000, end_s=GENESIS_TS + 1_800, **kwargs)


def test_known_answer_window_fetch_returns_exactly_the_in_window_signatures() -> None:
    # Arrange — sigs before, inside (boundary cases included), and after the window.
    # Window is [t0, end): slot 1000 (== t0) is IN, slot 1800 (== end) is OUT.
    rpc = FakeRpc(tip_slot=10_000, addr_slots=[900, 1_000, 1_200, 1_799, 1_800, 1_805, 5_000])

    # Act
    fetched = _window(rpc)

    # Assert — exact set, ascending order, honest reach flag.
    assert [s.slot for s in fetched.signatures] == [1_000, 1_200, 1_799]
    assert fetched.reached_t0 is True
    assert fetched.pages >= 1


def test_slot_resolution_steps_over_skipped_slots() -> None:
    # Arrange — the window-end slot and its neighbour are skipped.
    rpc = FakeRpc(tip_slot=10_000, addr_slots=[1_000], skipped={1_800, 1_801})

    # Act — the anchor resolves to the first non-skipped slot at/after target.
    slot = slot_at_or_after(rpc, GENESIS_TS + 1_800)

    # Assert
    assert slot == 1_802
    assert rpc.block_time(slot) is not None


def test_seed_is_a_foreign_signature_and_anchors_the_walk() -> None:
    # The seed comes from a block, not from the address's own history — the
    # measured property that makes depth independence possible at all.
    rpc = FakeRpc(tip_slot=10_000, addr_slots=[1_000, 1_200])
    slot = slot_at_or_after(rpc, GENESIS_TS + 1_800)
    seed = seed_signature(rpc, slot)
    assert seed.startswith("blk")  # foreign: no pool signature at that slot
    assert seed not in {s.signature for s in rpc.addr_sigs}


def test_cost_is_independent_of_post_window_depth() -> None:
    """The load-bearing claim: a far deeper pool costs exactly the same."""
    # Arrange — identical windows; the deep pool has 2,000 extra post-window sigs.
    shallow = FakeRpc(tip_slot=40_000, addr_slots=[900, 1_000, 1_200, 1_799])
    deep_slots = [900, 1_000, 1_200, 1_799, *range(2_000, 22_000, 10)]
    deep = FakeRpc(tip_slot=40_000, addr_slots=deep_slots)

    # Act
    got_shallow = _window(shallow)
    got_deep = _window(deep)

    # Assert — same window content, same pages, same total request count.
    assert [s.signature for s in got_shallow.signatures] == [
        s.signature for s in got_deep.signatures
    ]
    assert got_shallow.pages == got_deep.pages
    assert shallow.total_calls() == deep.total_calls()


def test_page_bound_reports_an_honest_partial_never_a_silent_one() -> None:
    # Arrange — 30 in-window sigs, page limit 10, one page allowed.
    rpc = FakeRpc(tip_slot=10_000, addr_slots=list(range(1_000, 1_600, 20)))

    # Act
    fetched = _window(rpc, page_limit=10, max_pages=1)

    # Assert — the walk stopped early and says so; the partial is not "reached".
    assert fetched.reached_t0 is False
    assert fetched.pages == 1
    assert len(fetched.signatures) == 10


def test_history_exhaustion_counts_as_reaching_t0() -> None:
    # Arrange — the pool's first-ever signature sits inside the window, so the
    # walk runs out of history without ever seeing a pre-window signature.
    rpc = FakeRpc(tip_slot=10_000, addr_slots=[1_200, 1_400])

    # Act
    fetched = _window(rpc)

    # Assert
    assert fetched.reached_t0 is True
    assert [s.slot for s in fetched.signatures] == [1_200, 1_400]


def test_target_beyond_chain_tip_is_refused() -> None:
    rpc = FakeRpc(tip_slot=1_000, addr_slots=[])
    with pytest.raises(RetrievalError, match="beyond the chain tip"):
        slot_at_or_after(rpc, GENESIS_TS + 5_000)


def test_gated_fetch_prices_every_request_and_refusal_stops_the_walk(tmp_path: Path) -> None:
    # Arrange — a cap of 3 rpc credits cannot fund the binary search.
    inner = FakeRpc(tip_slot=10_000, addr_slots=[900, 1_000, 1_200])
    gate = CreditGate(
        Settings(helius_credit_cap=3, data_root=tmp_path),
        ledger_path=tmp_path / "ledger.jsonl",
    )
    rpc = GatedRpc(inner, gate)

    # Act / Assert — the refusal fires mid-walk, before the 4th request is sent.
    with pytest.raises(CreditCapError):
        _window(rpc)
    # Every request that WAS sent had been charged first, and the refused one
    # wrote nothing: ledger total equals transport call count exactly.
    assert inner.total_calls() == 3
    assert gate.spent() == 3


def test_gated_fetch_full_window_stays_near_the_measured_per_pool_cost(tmp_path: Path) -> None:
    # Arrange — a realistic chain tip so the binary search does real work.
    inner = FakeRpc(tip_slot=250_000_000, addr_slots=[900, 1_000, 1_200, 1_799])
    gate = CreditGate(
        Settings(helius_credit_cap=1_000, data_root=tmp_path),
        ledger_path=tmp_path / "ledger.jsonl",
    )
    rpc = GatedRpc(inner, gate)

    # Act
    fetched = fetch_window(rpc, POOL, t0_s=GENESIS_TS + 1_000, end_s=GENESIS_TS + 1_800)

    # Assert — correct content, and the whole fetch stays in the tens of
    # credits (the measured ~33/pool order), depth playing no part.
    assert [s.slot for s in fetched.signatures] == [1_000, 1_200, 1_799]
    assert gate.spent() == inner.total_calls()
    assert gate.spent() < 50
