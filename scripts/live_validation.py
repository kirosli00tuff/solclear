"""Stage B live validation harness: Method B against the chain, gated.

Not library API — a standalone driver the operator runs, kept in the repo so
the Stage B measurements are reproducible rather than transcribed. Every
request goes through :class:`solclear.gate.CreditGate` exactly as library
callers must; the cap comes from ``SOLCLEAR_HELIUS_CREDIT_CAP`` and a refusal
stops the run rather than being routed around.

What it measures, per address (progress.md Stage B, Task 2):

- ``reached_t0`` — reported, never dropped. A fetch stopped by the page bound
  is a corrupted partial, and silent truncation is the exact bias Method B
  exists to remove (FINDINGS.md §5).
- request count and weighted credits, read as a **ledger delta** so the number
  is the gate's own accounting rather than a parallel tally that could drift.
- wall time.
- a **depth proxy**: the block time of the address's newest signature. Method B
  claims cost independent of depth — the history *after* the window — so depth
  has to be measured, not asserted. One extra request per address.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from solclear.config import load_settings
from solclear.gate import CreditGate
from solclear.method_b import GatedRpc, RetrievalError, RpcClient, SigInfo, fetch_window
from solclear.rpc import HeliusRpc

# A fixed 30-minute historical window, identical for every address, so cost
# differences between addresses cannot come from window width.
WINDOW_START = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)
WINDOW_SECONDS = 1_800

# Known-deep control: the USDC mint is referenced by an enormous and still-
# growing history, so if Method B's cost tracked depth it would blow up here.
KNOWN_DEEP = ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "USDC mint (known-deep control)")
SNAPSHOT_CSV = Path("data/snapshots/features_c23.csv")
OUT_JSON = Path("data/vendor/stage_b_live_validation.json")


@dataclass(frozen=True)
class AddressResult:
    """One address's live retrieval outcome. Partials are recorded, not dropped."""

    address: str
    label: str
    newest_signature_utc: str | None
    reached_t0: bool | None
    pages: int | None
    signatures_in_window: int | None
    weighted_credits: int
    wall_s: float
    error: str | None = None


def depth_proxy(rpc: RpcClient, address: str) -> str | None:
    """Block time of the address's newest signature — the depth indicator."""
    newest = rpc.signatures_for_address(address, None, 1)
    if not newest or newest[0].block_time_s is None:
        return None
    return datetime.fromtimestamp(newest[0].block_time_s, tz=UTC).isoformat()


class PacedRpc:
    """Delays before each request so a free-tier rate limit is not tripped.

    Measured need, not precaution: without it the first Stage B run took HTTP
    429 on 3 of 6 addresses. This lives in the harness rather than in
    :mod:`solclear.method_b` deliberately — pacing is a property of the key's
    tier, not of the retrieval algorithm, and burying a sleep inside the
    library would hide a real operational constraint from its callers.
    """

    def __init__(self, client: RpcClient, delay_s: float) -> None:
        self._client = client
        self._delay_s = delay_s

    def _pace(self) -> None:
        time.sleep(self._delay_s)

    def latest_slot(self) -> int:
        self._pace()
        return self._client.latest_slot()

    def block_time(self, slot: int) -> int | None:
        self._pace()
        return self._client.block_time(slot)

    def block_signatures(self, slot: int) -> list[str]:
        self._pace()
        return self._client.block_signatures(slot)

    def signatures_for_address(self, address: str, before: str | None, limit: int) -> list[SigInfo]:
        self._pace()
        return self._client.signatures_for_address(address, before, limit)


def measure(rpc: RpcClient, gate: CreditGate, address: str, label: str) -> AddressResult:
    """Depth proxy + one Method B window fetch, priced from the ledger delta."""
    before = gate.spent()
    started = time.perf_counter()
    t0_s = int(WINDOW_START.timestamp())
    try:
        newest = depth_proxy(rpc, address)
        fetched = fetch_window(rpc, address, t0_s, t0_s + WINDOW_SECONDS)
    except (RetrievalError, RuntimeError) as exc:
        return AddressResult(
            address=address,
            label=label,
            newest_signature_utc=None,
            reached_t0=None,
            pages=None,
            signatures_in_window=None,
            weighted_credits=gate.spent() - before,
            wall_s=round(time.perf_counter() - started, 2),
            error=f"{type(exc).__name__}: {exc}",
        )
    return AddressResult(
        address=address,
        label=label,
        newest_signature_utc=newest,
        reached_t0=fetched.reached_t0,
        pages=fetched.pages,
        signatures_in_window=len(fetched.signatures),
        weighted_credits=gate.spent() - before,
        wall_s=round(time.perf_counter() - started, 2),
    )


def snapshot_addresses(n: int) -> list[tuple[str, str]]:
    """``n`` mints spread across the committed 2024 holdout, evenly sampled."""
    rows = [r for r in csv.DictReader(SNAPSHOT_CSV.open()) if r["year"] == "2024"]
    step = max(1, len(rows) // n)
    picked = rows[::step][:n]
    return [(r["mint"], f"snapshot 2024 · {r['cls']}/{r['decon']}") for r in picked]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-pools", type=int, default=5)
    parser.add_argument(
        "--delay-ms",
        type=float,
        default=150.0,
        help="pause before each request; the free tier rate-limits (HTTP 429) without it",
    )
    args = parser.parse_args()

    settings = load_settings()
    gate = CreditGate(settings)
    transport = PacedRpc(
        HeliusRpc(settings.require_helius_key().get_secret_value()), args.delay_ms / 1000.0
    )
    rpc = GatedRpc(transport, gate)

    targets = [*snapshot_addresses(args.snapshot_pools), KNOWN_DEEP]
    # Resume: an address already measured successfully is never re-fetched.
    # Credits are real money and a re-run must not silently re-spend them.
    done: dict[str, AddressResult] = {}
    if OUT_JSON.is_file():
        for row in json.loads(OUT_JSON.read_text())["results"]:
            if row.get("error") is None:
                done[row["address"]] = AddressResult(**row)
    print(f"cap {gate.cap} · already spent {gate.spent()} · {len(targets)} addresses")
    print(f"window {WINDOW_START.isoformat()} +{WINDOW_SECONDS}s (identical for every address)")
    print(f"pacing {args.delay_ms:.0f} ms/request · {len(done)} already measured, not re-fetched\n")

    results: list[AddressResult] = []
    for address, label in targets:
        if address in done:
            results.append(done[address])
            print(f"{address[:12]}… {label:38s} (cached from a prior run, not re-spent)")
            continue
        result = measure(rpc, gate, address, label)
        results.append(result)
        print(
            f"{address[:12]}… {label:38s} reached_t0={result.reached_t0} "
            f"pages={result.pages} sigs={result.signatures_in_window} "
            f"credits={result.weighted_credits} wall={result.wall_s}s"
            + (f" ERROR {result.error}" if result.error else "")
        )

    costs = [r.weighted_credits for r in results if r.error is None]
    payload = {
        "window_start_utc": WINDOW_START.isoformat(),
        "window_seconds": WINDOW_SECONDS,
        "results": [asdict(r) for r in results],
        "cost_min": min(costs) if costs else None,
        "cost_max": max(costs) if costs else None,
        "cost_mean": round(sum(costs) / len(costs), 1) if costs else None,
        "gate_spent_total": gate.spent(),
        "gate_cap": gate.cap,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=1))
    print(
        f"\ncost min/mean/max: {payload['cost_min']}/{payload['cost_mean']}/{payload['cost_max']}"
    )
    print(f"spent {gate.spent()} of {gate.cap} · wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
