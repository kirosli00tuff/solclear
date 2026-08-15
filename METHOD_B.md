# Method B — depth-independent retrieval of a Solana address's historical window

**The reusable component of this project.** Nothing in this file is specific to
rug detection, to the clearance model, or to memecoins. If you need *every
transaction an address saw during some past interval*, and that address may
have had a long life since, this is the algorithm — and the reason it exists is
correctness, not speed.

Implementation: [`solclear/method_b.py`](solclear/method_b.py). It depends on
nothing else in this package except the credit gate, and the RPC surface it
needs is a four-method `Protocol` that any Solana client can satisfy.

---

## The problem it solves

The obvious way to reach a historical launch window is to page
`getSignaturesForAddress` backward from *now* until you arrive. That walk costs
**O(the address's entire subsequent history)** — so it is cheapest exactly
where you need it least, and most expensive exactly where you need it most.

Every implementation therefore caps the page count, and the cap does not fail
loudly. It returns a plausible partial. Measured (C.25) on **n = 14 random
honest-2024 pools: 8 of 14 were too deep** for a 40-page cap, at a mean of
**73.6 pages per pool**. Those 8 were not a random 8 — they were the thriving,
deeply-traded survivors, precisely the pools a sample most needs.

**So the naive walk had excluded 57% of the honest class**, and what remained
skewed toward faded pools, which look rug-like.

This is not a performance complaint. It is a **correctness argument**, and it
has a measured price attached: when the sample was rebuilt without the depth
bias, **half of a previously measured behavioural lift disappeared** (+0.115 →
+0.047, with the high-activity stratum collapsing +0.156 → +0.015 — see
[FINDINGS.md](FINDINGS.md) §5 and §7). A retrieval method that cannot reach
deep addresses does not merely cost more; **it changes the answer**, silently,
in a direction that looks like a finding.

## The algorithm

Given an address and a target window `[t0, end)`:

1. **Binary-search block time to resolve the window's *end* to a slot.**
   `getBlockTime` over the slot range — `O(log chain)` lookups. Skipped slots
   (no block time) are resolved by scanning forward a bounded number of slots
   (`MAX_SKIPPED_SLOT_SCAN = 64`); a skip run longer than that raises rather
   than guessing.
2. **Seed a signature from that block.** `getBlock` at the anchor slot, take
   any signature. It does **not** need to involve your address — that `before=`
   accepts a foreign signature was measured, not assumed.
3. **Page backward from the seed.**
   `getSignaturesForAddress(address, before=seed, limit=…)`, following each
   batch's last signature, collecting everything whose block time lands in
   `[t0, end)`.
4. **Stop at the first signature older than `t0`** — or when history is
   exhausted. Either way the window's start has been reached honestly.

The key property falls out of step 1: **because the seed anchors at the window
end, the backward walk never touches the address's post-window history, however
deep it is.** Cost is `O(window)` plus a logarithmic number of block-time
lookups, and is independent of how successful the address later became.

## Measured cost

**~33–38 weighted credits per pool, regardless of pool depth.**

| measurement | windows retrieved | credits per pool |
|---|---|---|
| C.25 (parent, original) | launch windows | ~33 |
| Stage C.1 (this repo, live) | 83 → 9,808 signatures | 34–43 |
| Stage C.1 T0-tolerance probe (90-min windows) | 220 → 18,099 signatures | 42–55 |
| Stage E (77-pool cohort) | mixed | ~38 typical |

A 118× spread in window population moves the cost by well under 2×, and the
address's history *outside* the window does not enter the cost at all. Compare
the naive walk's mean of 73.6 pages per pool — one request per page, before it
even reaches the window.

**What this does not cover.** Method B retrieves *signatures and their cheap
metadata*. Turning those into balance-changing events needs the Enhanced
Transactions API at **100 credits per 100-signature call**, which dominates
total cost (typical ≈ 1,400 per pool, extreme observed 9,900). Method B makes
retrieval affordable and unbiased; it does not make a whole pipeline cheap. See
the cost section of [README.md](README.md).

## Verification — why a cheaper method can be trusted

A cheaper method returning *different* history would be a correctness failure
dressed as a win, so cheapness was never the acceptance bar. Agreement was:

**On every pool where both methods reached the launch window, the two signature
sets matched at Jaccard 1.0** (C.25). Method B was adopted only after that.

This is the repository's standing practice — a new retrieval or scoring path
must reproduce a previously measured answer before its output is believed — and
it is why the depth-bias finding above is trustworthy: the corrected sample was
demonstrably the *same* history, just more of it.

## Partial fetches are flagged, never silently returned

`WindowFetch.reached_t0` is `True` only when the walk saw a signature older
than the window start, or exhausted the address's history. A fetch stopped by
the `max_pages` bound reports **`reached_t0=False`** and must be treated as a
corrupted partial — its earliest signatures are missing.

In this package that flag is load-bearing: `solclear.pipeline.score_pool`
refuses to score a `reached_t0=False` fetch at all, returning an `Unscorable`
carrying no number (ADR-002, ADR-006). If you reuse Method B elsewhere,
**check the flag** — a truncated window that gets analysed anyway reproduces
exactly the bias this algorithm exists to eliminate.

## Reusing it

The only RPC surface required is this protocol:

```python
class RpcClient(Protocol):
    def latest_slot(self) -> int: ...
    def block_time(self, slot: int) -> int | None: ...  # None == skipped slot
    def block_signatures(self, slot: int) -> list[str]: ...
    def signatures_for_address(
        self, address: str, before: str | None, limit: int
    ) -> list[SigInfo]: ...
```

Any Solana RPC client can satisfy it. `solclear.rpc.HeliusRpc` is one
implementation; there is nothing Helius-specific in the algorithm.

```python
from solclear.config import Settings
from solclear.gate import CreditGate
from solclear.method_b import GatedRpc, fetch_window
from solclear.rpc import HeliusRpc

settings = Settings()
rpc = GatedRpc(HeliusRpc(settings), CreditGate(settings))  # prices before sending

fetch = fetch_window(rpc, address=pool_address, t0_s=t0, end_s=t0 + 1800)

if not fetch.reached_t0:
    raise RuntimeError("partial window — discard it, do not analyse it")

for sig in fetch.signatures:  # ascending block time
    ...
```

`GatedRpc` is optional but recommended: it wraps any `RpcClient` and charges
the credit gate **before** each request is sent, against an append-only on-disk
ledger that survives restarts. A refusal raises before the network is touched
and writes nothing (ADR-003). Wrapping is what makes an unmetered path
structurally unavailable rather than merely discouraged.

## Known limitations, stated

- **Bounded skipped-slot scanning.** `MAX_SKIPPED_SLOT_SCAN = 64` consecutive
  slots. Mainnet skip runs are far shorter, but a chain segment violating it
  **raises** (`RetrievalError`) rather than guessing a block time.
- **No rate-limit pacing.** Method B issues requests as fast as the caller
  drives it. Helius's free tier returned HTTP 429 without pacing on 3 of 6
  addresses (Stage B); pacing is the caller's policy, deliberately, so it is
  not hidden inside the retrieval loop. GeckoTerminal needed 6 s spacing
  against a documented 30/min limit (Stage B addendum) — published limits were
  optimistic on both vendors.
- **`max_pages` bounds pathological in-window volume**, not depth. A window
  holding more than `page_limit × max_pages` signatures reports
  `reached_t0=False`; raise the bound or shorten the window, but do not analyse
  the partial.
- **Errors raise; skipped slots return `None`.** These were conflated in an
  early version — an error silently becoming a data condition — and the fix
  lives in `solclear/rpc.py`. If you write your own `RpcClient`, keep them
  distinct.

## Provenance

Measured in MLCryptoEngine C.22/C.25 (2026-08-06 → 2026-08-07, parent ADR-053);
ported here as ADR-002 and re-verified live in Stages B, C.1, D and E
(2026-08-11 → 2026-08-14) across ~90 pools without a depth-related failure.
