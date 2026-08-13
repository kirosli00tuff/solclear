"""The Helius credit gate: refuse first, spend second, ledger everything.

Ported from MLCryptoEngine (ADR-046 there, ADR-003 here) with its record
intact: it fired correctly at a sweep boundary in C.21 (budget stop at 178 of
200 tokens, exactly as registered) and refused an unaffordable purchase in
C.26 (the decon-unbiased test at ~2x the entire cap). The properties that make
it trustworthy, each pinned by test:

- **Every request is priced before it is sent.** ``charge`` runs the cap
  arithmetic first; a refusal raises before any network call can happen.
- **The ledger is append-only and on disk**, so the cumulative total survives
  a process restart — many small requests cannot walk past a cap none
  individually breaches.
- **A refusal writes nothing.** The ledger only ever records spend that was
  approved.

Pricing method, stated because honesty demands it: Helius exposes no usage
endpoint reachable without a key, so cost is **derived from request counts
against a weighted schedule** rather than read from an API. The weights below
are conservative placeholders dated 2026-08-06 (inherited from the parent) and
are **unverified against the dashboard** — the ledger records raw request
counts precisely so the operator can reconcile real credit burn and correct
the weights with one edit. Never loosen them mid-sweep.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from solclear.config import Settings

LEDGER_NAME = "helius_credit_ledger.jsonl"
# Request-weighted credits. `rpc` = 1 matches the vendor's standard-call
# price. `enhanced` = 100 per the vendor's published pricing (
# https://www.helius.dev/pricing, read 2026-08-13: "Enhanced Transactions API
# and Mint API calls are 100 credits") — corrected in Stage C Task 2 from the
# inherited placeholder of 10, which under-gated by 10x; no enhanced call was
# ever made under the old weight (the ledger records raw counts per kind, so
# this is checkable, and reconciliation needs no history rewrite: ADR-003).
CREDIT_WEIGHTS: dict[str, int] = {"rpc": 1, "enhanced": 100}


class CreditCapError(RuntimeError):
    """A request (or sweep estimate) would breach the registered credit cap."""


@dataclass(frozen=True)
class Charge:
    ts: str
    kind: str
    n: int
    weighted: int
    cumulative: int
    note: str


class CreditGate:
    """Hard credit ceiling enforced against an append-only on-disk ledger."""

    def __init__(self, settings: Settings, ledger_path: Path | None = None) -> None:
        self.cap = int(settings.helius_credit_cap)
        self.path = ledger_path or (settings.data_root / "vendor" / LEDGER_NAME)

    def spent(self) -> int:
        """Cumulative weighted credits, re-read from disk so restarts count."""
        if not self.path.is_file():
            return 0
        total = 0
        with self.path.open("rb") as fh:
            for line in fh:
                if line.strip():
                    total += int(json.loads(line)["weighted"])
        return total

    def remaining(self) -> int:
        return max(0, self.cap - self.spent())

    def estimate(self, n_requests: int, kind: str) -> int:
        return n_requests * CREDIT_WEIGHTS[kind]

    def check_estimate(self, weighted: int, what: str) -> None:
        """Refuse a planned sweep before its first request, by arithmetic."""
        spent = self.spent()
        if spent + weighted > self.cap:
            raise CreditCapError(
                f"REFUSED {what}: estimated {weighted} weighted credits + {spent} already "
                f"spent exceeds the cap of {self.cap} (ADR-003). Nothing was sent. Shrink "
                "the sweep or raise SOLCLEAR_HELIUS_CREDIT_CAP by operator edit."
            )

    def charge(self, kind: str, n_requests: int = 1, note: str = "") -> Charge:
        """Charge BEFORE the request: a refusal must leave the ledger unchanged."""
        weighted = self.estimate(n_requests, kind)
        self.check_estimate(weighted, note or f"{n_requests}x {kind}")
        entry = Charge(
            ts=datetime.now(UTC).isoformat(),
            kind=kind,
            n=n_requests,
            weighted=weighted,
            cumulative=self.spent() + weighted,
            note=note,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as fh:
            fh.write(json.dumps(entry.__dict__).encode() + b"\n")
        return entry
