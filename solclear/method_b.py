"""Method B: depth-independent retrieval of a pool's launch-window history.

The algorithm (measured and verified in MLCryptoEngine C.25, ADR-053 there,
ADR-002 here): resolve the target window's end to a slot by binary-searching
``getBlockTime``, take a seed signature from that block via ``getBlock``, then
page ``getSignaturesForAddress(address, before=seed)`` backward until the
window's start. ``before`` accepts a foreign signature — measured, not assumed
— so the seed need not belong to the address. Cost is O(window) plus a
logarithmic number of block-time lookups: roughly **33 weighted credits per
pool regardless of pool depth**.

**Why this matters is correctness, not performance.** The naive walk pages
``getSignaturesForAddress`` backward from *now*, so reaching a historical
launch costs O(the pool's entire subsequent history) and silently fails on
deep pools when a page cap truncates the walk. C.25 measured that failure
mode: the from-now walk **excluded 57% of the honest class**, because thriving
pools are deep and get truncated — biasing any sample toward faded pools,
which look rug-like. Half of a measured behavioural lift turned out to be that
selection artifact. A retrieval method that cannot reach deep pools does not
merely cost more; it changes the answer.

Correctness of Method B itself was checked, not assumed: on every pool where
both methods reached the launch window, the window signature sets matched at
**Jaccard 1.0** (C.25). A cheaper method returning *different* history would
have been a correctness failure, not a win.

Every request is priced through the credit gate before it is sent: wrap any
transport in :class:`GatedRpc`. A refusal raises before the network call and
writes nothing to the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from solclear.gate import CreditGate

DEFAULT_PAGE_LIMIT = 1_000
DEFAULT_MAX_PAGES = 40
# Longest run of consecutive skipped slots this module will scan across before
# declaring the chain segment unusable. Mainnet skip runs are far shorter.
MAX_SKIPPED_SLOT_SCAN = 64


class RetrievalError(RuntimeError):
    """The window could not be resolved or seeded on this chain segment."""


@dataclass(frozen=True)
class SigInfo:
    """One signature's cheap metadata (the fields the RPC actually returns)."""

    signature: str
    slot: int
    block_time_s: int | None
    err: bool = False


class RpcClient(Protocol):
    """Minimal Solana RPC surface Method B needs.

    Implementations do no pricing of their own; wrap them in :class:`GatedRpc`
    so every request is charged before it is sent.
    """

    def latest_slot(self) -> int: ...

    def block_time(self, slot: int) -> int | None:
        """Unix seconds for a slot, or None when the slot was skipped."""
        ...

    def block_signatures(self, slot: int) -> list[str]:
        """Signatures in a block, empty when the slot was skipped."""
        ...

    def signatures_for_address(self, address: str, before: str | None, limit: int) -> list[SigInfo]:
        """Signatures involving ``address`` strictly before ``before``, newest first."""
        ...


class GatedRpc:
    """Prices every request through the credit gate BEFORE sending it.

    Implements :class:`RpcClient` by delegation, so anything accepting the
    protocol accepts the gated wrapper. A gate refusal raises
    :class:`solclear.gate.CreditCapError` before the transport is touched.
    """

    def __init__(self, client: RpcClient, gate: CreditGate) -> None:
        self._client = client
        self._gate = gate

    def latest_slot(self) -> int:
        self._gate.charge("rpc", 1, "getSlot")
        return self._client.latest_slot()

    def block_time(self, slot: int) -> int | None:
        self._gate.charge("rpc", 1, f"getBlockTime slot={slot}")
        return self._client.block_time(slot)

    def block_signatures(self, slot: int) -> list[str]:
        self._gate.charge("rpc", 1, f"getBlock slot={slot}")
        return self._client.block_signatures(slot)

    def signatures_for_address(self, address: str, before: str | None, limit: int) -> list[SigInfo]:
        self._gate.charge("rpc", 1, f"getSignaturesForAddress {address}")
        return self._client.signatures_for_address(address, before, limit)


@dataclass(frozen=True)
class WindowFetch:
    """A retrieved launch window: signatures with block time in [t0_s, end_s).

    ``reached_t0`` is an honest flag, never assumed: True only when the walk
    saw a signature older than the window start or exhausted the address's
    history. A fetch stopped by ``max_pages`` reports False and must be treated
    as a corrupted partial (its earliest signatures are missing), not used.
    """

    address: str
    t0_s: int
    end_s: int
    signatures: tuple[SigInfo, ...]  # ascending block time
    pages: int
    reached_t0: bool


def _block_time_at_or_after(rpc: RpcClient, slot: int) -> tuple[int, int]:
    """(slot, block_time) of the first non-skipped slot at or after ``slot``."""
    for s in range(slot, slot + MAX_SKIPPED_SLOT_SCAN + 1):
        ts = rpc.block_time(s)
        if ts is not None:
            return s, ts
    raise RetrievalError(
        f"no block time found in slots [{slot}, {slot + MAX_SKIPPED_SLOT_SCAN}]; "
        "skipped-slot run exceeds the scan bound"
    )


def slot_at_or_after(rpc: RpcClient, target_ts_s: int, lo: int = 0, hi: int | None = None) -> int:
    """First (non-skipped) slot whose block time is >= ``target_ts_s``.

    Binary search on ``getBlockTime`` — the anchor step of Method B. Skipped
    slots (no block time) are resolved by scanning forward a bounded number of
    slots, so the search stays O(log chain) block-time lookups.
    """
    if hi is None:
        hi = rpc.latest_slot()
    _, tip_ts = _block_time_at_or_after(rpc, hi)
    if tip_ts < target_ts_s:
        raise RetrievalError(
            f"target time {target_ts_s} is beyond the chain tip (slot {hi} at {tip_ts})"
        )
    while lo < hi:
        mid = (lo + hi) // 2
        found_slot, ts = _block_time_at_or_after(rpc, mid)
        if ts >= target_ts_s:
            hi = mid
        else:
            lo = found_slot + 1
    return _block_time_at_or_after(rpc, lo)[0]


def seed_signature(rpc: RpcClient, slot: int) -> str:
    """A signature from the first non-empty block at or after ``slot``.

    Any signature at or after the window end anchors ``before=`` paging over
    the whole window; it need not involve the target address (measured in
    C.25: ``before`` accepts a foreign signature).
    """
    for s in range(slot, slot + MAX_SKIPPED_SLOT_SCAN + 1):
        sigs = rpc.block_signatures(s)
        if sigs:
            return sigs[0]
    raise RetrievalError(
        f"no non-empty block found in slots [{slot}, {slot + MAX_SKIPPED_SLOT_SCAN}]"
    )


def fetch_window(
    rpc: RpcClient,
    address: str,
    t0_s: int,
    end_s: int,
    *,
    page_limit: int = DEFAULT_PAGE_LIMIT,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> WindowFetch:
    """Retrieve ``address``'s signatures with block time in ``[t0_s, end_s)``.

    Depth-independent by construction: the seed anchors at the window end, so
    paging backward never touches the address's post-window history, however
    deep. The walk stops at the first signature older than ``t0_s`` (or when
    history is exhausted); ``max_pages`` bounds pathological in-window volume,
    and hitting it is reported via ``reached_t0=False``, never silently.
    """
    if end_s <= t0_s:
        raise ValueError(f"window end {end_s} must be after window start {t0_s}")
    anchor_slot = slot_at_or_after(rpc, end_s)
    seed = seed_signature(rpc, anchor_slot)
    before: str | None = seed
    collected: list[SigInfo] = []
    pages = 0
    reached = False
    while pages < max_pages:
        batch = rpc.signatures_for_address(address, before, page_limit)
        pages += 1
        if not batch:
            reached = True  # history exhausted: nothing older than the window exists
            break
        for sig in batch:
            if sig.block_time_s is None:
                continue
            if sig.block_time_s < t0_s:
                reached = True
                break
            if sig.block_time_s < end_s:
                collected.append(sig)
        if reached:
            break
        before = batch[-1].signature
    return WindowFetch(
        address=address,
        t0_s=t0_s,
        end_s=end_s,
        signatures=tuple(reversed(collected)),
        pages=pages,
        reached_t0=reached,
    )
