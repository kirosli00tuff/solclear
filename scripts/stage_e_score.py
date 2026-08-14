"""Stage E Task 2: score the cohort through the live path, resume-safe.

Run:  uv run python scripts/stage_e_score.py       (key in .env; gate in force)

Per pool, on pool-creation anchoring (ADR-011, scores anchor-shifted):
Method B fetch of the mint's [t0, t0+30 min) window → enhanced batches
(each pool's whole sweep priced before its first call; pools above the
registered 6,000-credit ceiling are recorded with their signature counts as
a declared composition bias, never silently) → parse (ADR-009; any
unparseable payload is PERSISTED for vocabulary review and the pool
refuses) → live GoPlus token security → ``score_pool`` under ADR-012
(measured absence encodes to the trained sentinel; source unavailability
refuses).

Output is append-only JSONL (``data/vendor/stage_e_scores.jsonl``): a crash
or gate refusal resumes without re-spending — pools already present are
skipped. A ``CreditCapError`` ends the run as a reported refusal.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from solclear.config import STAGE_E_CREDIT_CAP, Settings
from solclear.enhanced import (
    MAX_SIGNATURES_PER_CALL,
    EnhancedClient,
    GatedEnhanced,
    calls_needed,
)
from solclear.gate import CreditCapError, CreditGate
from solclear.goplus import GoPlusClient
from solclear.method_b import GatedRpc, fetch_window
from solclear.parse import parse_window
from solclear.pipeline import score_pool
from solclear.rpc import HeliusRpc
from solclear.scorer import Clearance

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "data" / "vendor"
COHORT = VENDOR / "stage_e_cohort.json"
SCORES = VENDOR / "stage_e_scores.jsonl"

WINDOW_S = 1_800
PER_POOL_ENHANCED_CEILING = 6_000  # registered; skips are declared bias
STOP_WHEN_REMAINING_BELOW = 8_000  # one busy pool + slack; a clean stop, not a refusal
NOW_STATE_FIELDS = ("freezable", "mintable", "nontransf", "thook")


def _iso_to_s(value: str) -> int:
    from datetime import datetime

    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def main() -> None:
    settings = Settings(helius_credit_cap=STAGE_E_CREDIT_CAP)
    key = settings.require_helius_key().get_secret_value()
    gate = CreditGate(settings)
    rpc = GatedRpc(HeliusRpc(key), gate)
    enhanced = GatedEnhanced(EnhancedClient(key), gate)
    goplus = GoPlusClient()

    cohort = json.loads(COHORT.read_text())
    entries = [e for e in cohort["entries"] if "dropped" not in e]
    done: set[str] = set()
    if SCORES.is_file():
        with SCORES.open() as fh:
            done = {json.loads(line)["pool_address"] for line in fh if line.strip()}
    todo = [e for e in entries if e["pool_address"] not in done]
    print(f"cohort {len(entries)} | already scored {len(done)} | todo {len(todo)}")
    print(f"ledger at start: {gate.spent()} / cap {STAGE_E_CREDIT_CAP}")

    for i, entry in enumerate(todo):
        if gate.remaining() < STOP_WHEN_REMAINING_BELOW:
            print(f"clean stop: remaining {gate.remaining()} below guard")
            break
        record: dict[str, Any] = {
            "pool_address": entry["pool_address"],
            "mint": entry["mint"],
            "source": entry["source"],
            "pool_created_at": entry["pool_created_at"],
        }
        try:
            t0 = _iso_to_s(entry["pool_created_at"])
            before = gate.spent()
            fetch = fetch_window(rpc, entry["mint"], t0, t0 + WINDOW_S)
            record["retrieval_credits"] = gate.spent() - before
            record["in_window_sigs"] = len(fetch.signatures)
            record["reached_t0"] = fetch.reached_t0
            cost = calls_needed(len(fetch.signatures)) * 100 if fetch.signatures else 0
            record["enhanced_cost_priced"] = cost
            if cost > PER_POOL_ENHANCED_CEILING:
                record["outcome"] = "skipped_cost_ceiling"
            else:
                sigs = [s.signature for s in fetch.signatures]
                payloads: list[dict[str, Any]] = []
                for j in range(0, len(sigs), MAX_SIGNATURES_PER_CALL):
                    payloads.extend(enhanced.transactions(sigs[j : j + MAX_SIGNATURES_PER_CALL]))
                parsed = parse_window(
                    payloads,
                    mint=entry["mint"],
                    pool_address=entry["pool_address"],
                    t0_s=float(t0),
                    end_s=float(t0 + WINDOW_S),
                )
                record["parse_report"] = asdict(parsed.report)
                record["creator"] = parsed.creator
                if parsed.report.unparseable > 0:
                    # Persist the payloads the vocabulary did not cover
                    # (ADR-009 review runs on real objects, never on counts).
                    culprits = [
                        p
                        for p in payloads
                        if parse_window(
                            [p],
                            mint=entry["mint"],
                            pool_address=entry["pool_address"],
                            t0_s=float(t0),
                            end_s=float(t0 + WINDOW_S),
                        ).report.unparseable
                        == 1
                    ]
                    record["unparseable_payloads"] = culprits[:5]
                sec = goplus.token_security(entry["mint"])
                sec_features: dict[str, float | None] = (
                    sec.as_features() if sec else dict.fromkeys(NOW_STATE_FIELDS)
                )
                verdict = score_pool(
                    fetch=fetch,
                    txs=list(parsed.events),
                    parse_report=parsed.report,
                    token_security=sec_features,
                    creator=parsed.creator or "",
                )
                if isinstance(verdict, Clearance):
                    record["outcome"] = "cleared" if verdict.cleared else "not_cleared"
                    record["clearance_score"] = round(verdict.clearance_score, 4)
                else:
                    record["outcome"] = "refused"
                    record["refusal_reason"] = verdict.reason
                    record["refusal_missing"] = list(verdict.missing)
        except CreditCapError as refusal:
            record["outcome"] = "gate_refusal"
            record["gate_refusal"] = str(refusal)
            with SCORES.open("a") as fh:
                fh.write(json.dumps(record) + "\n")
            print(f"GATE REFUSED at pool {i}: {refusal}")
            break
        except Exception as exc:  # transport failures recorded per pool, run continues
            record["outcome"] = "error"
            record["error"] = f"{type(exc).__name__}: {exc}"[:200]
        with SCORES.open("a") as fh:
            fh.write(json.dumps(record) + "\n")
        print(
            f"[{i + 1}/{len(todo)}] {entry['mint'][:8]}… {record.get('outcome')} "
            f"sigs={record.get('in_window_sigs')} spent={gate.spent()}"
        )

    print(f"ledger at end: {gate.spent()} / cap {STAGE_E_CREDIT_CAP}")
    goplus.close()


if __name__ == "__main__":
    main()
