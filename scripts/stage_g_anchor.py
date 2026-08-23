"""Stage G Task 1: complete the anchor-materiality measurement Stage D withheld.

Run with the key in .env:  uv run python scripts/stage_g_anchor.py

Stage D measured 2 of the 6 pre-registered both-anchor pairs and the registered
rule demanded >= 4, so its formal decision was **withheld** (ADR-011). The four
skipped pairs priced 2,000 / 2,300 / 6,700 / 11,100 enhanced credits there and
were passed over by the sub-budget before any call. This script measures them.

Each pool's full feature vector is computed under BOTH anchors, exactly as
Stage D did it:

- **pool anchor**: ``[gt_pool_created_at, +1800s)`` — the instant a live scanner
  can observe first-party (ADR-011);
- **parent anchor**: ``[solrpds_first_activity - 60s, +1800s)`` with features at
  ``t0 = solrpds_first_activity`` — the basis Stage D Task 1 read out of the
  parent's own code (``labels.py:81``; report C.22 fixes the window verbatim).

Pairs are re-priced from their freshly fetched windows before the first enhanced
call of each pair — Stage D's prices are inputs to the plan, never a substitute
for pricing now — and a pair that does not fit its sub-budget is skipped and
reported, never truncated. The verdict is then judged across all six pairs
against the Stage D Task 0 threshold, quoted verbatim in the Stage G
pre-registration and not adjusted here.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx

from solclear import scorer as sc
from solclear.config import STAGE_G_CREDIT_CAP, Settings
from solclear.enhanced import (
    MAX_SIGNATURES_PER_CALL,
    EnhancedClient,
    GatedEnhanced,
    calls_needed,
)
from solclear.features import features as compute_features
from solclear.gate import CreditCapError, CreditGate
from solclear.method_b import GatedRpc, WindowFetch, fetch_window
from solclear.parse import parse_window
from solclear.rpc import HeliusRpc
from solclear.scorer import Clearance, Unscorable

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "data" / "vendor"

WINDOW_S = 1_800
PRE_ROLL_S = 60  # the parent's measured pre-roll (MLCE report C.22)
TASK_1_BUDGET = 25_000
RETRIEVAL_BUDGET = 400

# The four pairs Stage D priced and skipped, cheapest-first by its prices.
MINTS_TO_MEASURE = (
    "Hp4XeAZ5EhKnFGm8Yv5GhZYmspNXGWV8SoRXPz91ZUab",  # priced 2,000 in Stage D
    "36gmCN9HLE5s6j8FdEYUCywByZU2KKKYy3UnAShmpump",  # priced 2,300
    "UutVe14D7KVKdLzDtbKmWet2jo6wVfw8aMHovr6wMs5",  # priced 6,700
    "7CSWFsrB3gPc5o5hxKTJCUbFDq4QyTWpjVG76S1Xpump",  # priced 11,100
)
STAGE_D_PRICES = {
    "Hp4XeAZ5EhKnFGm8Yv5GhZYmspNXGWV8SoRXPz91ZUab": 2_000,
    "36gmCN9HLE5s6j8FdEYUCywByZU2KKKYy3UnAShmpump": 2_300,
    "UutVe14D7KVKdLzDtbKmWet2jo6wVfw8aMHovr6wMs5": 6_700,
    "7CSWFsrB3gPc5o5hxKTJCUbFDq4QyTWpjVG76S1Xpump": 11_100,
}

NOW_STATE_FIELDS = ("freezable", "mintable", "nontransf", "thook")
COUNT_FIELDS = ("n_early_holders", "insider_funded_early_holders")
SHARE_FIELDS = ("creator_allocation_t0", "top5_concentration_wend")
# Any response header that could carry a vendor-published credit or quota
# figure. gate.py asserts no keyless usage endpoint exists; this gives that
# assertion evidence instead of leaving it an assertion.
CREDIT_HEADER_TOKENS = ("credit", "quota", "usage", "limit", "remaining", "ratelimit")


def _within_band(name: str, a: float | None, b: float | None) -> bool:
    """The Stage B tolerance bands, unchanged — Stage D's function, verbatim."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if name == "authority_revoked_in_window" or name in NOW_STATE_FIELDS:
        return a == b
    if name in COUNT_FIELDS:
        return abs(a - b) <= 1.0
    if name in SHARE_FIELDS:
        return abs(a - b) <= 0.01
    if name == "creator_time_to_first_sell_s":
        return abs(a - b) <= 60.0
    return a == b


def _verdict(v: Clearance | Unscorable) -> dict[str, Any]:
    if isinstance(v, Clearance):
        return {"kind": "clearance", "cleared": v.cleared, "score": round(v.clearance_score, 4)}
    return {"kind": "unscorable", "reason": v.reason, "missing": list(v.missing)}


def _credit_headers(gate: CreditGate, key: str) -> dict[str, Any]:
    """One gated getHealth, kept only for what its response headers reveal."""
    gate.charge("rpc", 1, "stage-g header probe getHealth")
    client = httpx.Client(base_url="https://mainnet.helius-rpc.com", timeout=30.0)
    try:
        resp = client.post(
            f"/?api-key={key}",
            json={"jsonrpc": "2.0", "id": "1", "method": "getHealth"},
        )
        headers = {k.lower(): v for k, v in resp.headers.items()}
    finally:
        client.close()
    return {
        "status_code": resp.status_code,
        "all_header_names": sorted(headers),
        "credit_like_headers": {
            k: v for k, v in headers.items() if any(t in k for t in CREDIT_HEADER_TOKENS)
        },
    }


def main() -> None:
    settings = Settings(helius_credit_cap=STAGE_G_CREDIT_CAP)
    key = settings.require_helius_key().get_secret_value()
    gate = CreditGate(settings)
    rpc = GatedRpc(HeliusRpc(key), gate)
    enhanced = GatedEnhanced(EnhancedClient(key), gate)

    claims = json.loads((VENDOR / "stage_c_t0_claims.json").read_text())
    parent_t0 = json.loads((VENDOR / "stage_d_parent_t0.json").read_text())
    token_security = json.loads((VENDOR / "stage_c_token_security.json").read_text())

    start = gate.spent()
    results: dict[str, Any] = {
        "cap": STAGE_G_CREDIT_CAP,
        "task_1_budget": TASK_1_BUDGET,
        "spent_at_start": start,
        "stage_d_prices": STAGE_D_PRICES,
    }
    print(f"ledger at start: {start} / cap {STAGE_G_CREDIT_CAP} (task-1 budget {TASK_1_BUDGET})")

    try:
        results["vendor_credit_headers"] = _credit_headers(gate, key)
        print(f"[0] credit-like headers: {results['vendor_credit_headers']['credit_like_headers']}")

        # ----------------------- retrieval, both anchors ---------------------- #
        r_start = gate.spent()
        windows: dict[tuple[str, str], WindowFetch] = {}
        for mint in MINTS_TO_MEASURE:
            gt_t0 = int(claims[mint]["claimed_t0_s"])
            par_t0 = int(parent_t0[mint]["t0_parent_s"])
            for anchor, lo, hi in (
                ("pool", gt_t0, gt_t0 + WINDOW_S),
                ("parent", par_t0 - PRE_ROLL_S, par_t0 + WINDOW_S),
            ):
                if gate.spent() - r_start > RETRIEVAL_BUDGET - 60:
                    print(f"[1] retrieval budget guard hit before {mint[:8]}/{anchor}")
                    break
                before = gate.spent()
                fetch = fetch_window(rpc, mint, lo, hi)
                windows[(mint, anchor)] = fetch
                print(
                    f"[1:fetch] {mint[:8]}…/{anchor} sigs={len(fetch.signatures)} "
                    f"reached={fetch.reached_t0} credits={gate.spent() - before}"
                )
        results["retrieval_credits"] = gate.spent() - r_start
        results["window_populations"] = {
            f"{m}|{a}": len(w.signatures) for (m, a), w in windows.items()
        }

        def pair_cost(mint: str) -> int:
            """Re-priced from the windows fetched now, not from Stage D's number."""
            cost = 0
            for anchor in ("pool", "parent"):
                fetch = windows.get((mint, anchor))
                if fetch is not None and fetch.signatures:
                    cost += calls_needed(len(fetch.signatures)) * 100
            return cost

        # -------------------- both-anchor feature vectors --------------------- #
        comparisons: list[dict[str, Any]] = []
        enhanced_spent = 0
        for mint in sorted(MINTS_TO_MEASURE, key=pair_cost):
            priced = pair_cost(mint)
            entry: dict[str, Any] = {
                "mint": mint,
                "pair_enhanced_priced": priced,
                "stage_d_priced": STAGE_D_PRICES[mint],
            }
            missing = [a for a in ("pool", "parent") if (mint, a) not in windows]
            if missing:
                entry["skipped"] = f"window(s) not fetched: {missing}"
                comparisons.append(entry)
                continue
            spent_here = gate.spent() - start
            if spent_here + priced > TASK_1_BUDGET:
                entry["skipped"] = (
                    f"pair enhanced cost {priced} + {spent_here} spent exceeds the "
                    f"{TASK_1_BUDGET} task budget (priced before any call)"
                )
                comparisons.append(entry)
                print(f"[2] {mint[:8]}… pair SKIPPED at {priced}")
                continue

            sec = token_security.get(mint) or {}
            sec_features = {k: sec.get(k) for k in NOW_STATE_FIELDS}
            anchors: dict[str, dict[str, Any]] = {}
            for anchor in ("pool", "parent"):
                fetch = windows[(mint, anchor)]
                sigs = [s.signature for s in fetch.signatures]
                payloads: list[dict[str, Any]] = []
                for i in range(0, len(sigs), MAX_SIGNATURES_PER_CALL):
                    payloads.extend(enhanced.transactions(sigs[i : i + MAX_SIGNATURES_PER_CALL]))
                enhanced_spent += calls_needed(len(sigs)) * 100 if sigs else 0
                feature_t0 = float(fetch.t0_s if anchor == "pool" else fetch.t0_s + PRE_ROLL_S)
                parsed = parse_window(
                    payloads,
                    mint=mint,
                    pool_address=str(claims[mint]["pool_address"]),
                    t0_s=float(fetch.t0_s),
                    end_s=float(fetch.end_s),
                )
                feats: dict[str, float | None] = dict(
                    compute_features(list(parsed.events), feature_t0, parsed.creator or "", None)
                )
                feats.update(sec_features)
                anchors[anchor] = {
                    "features": feats,
                    "parse_report": asdict(parsed.report),
                    "creator": parsed.creator,
                    "reached_t0": fetch.reached_t0,
                    "in_window_sigs": len(sigs),
                }
            for anchor in ("pool", "parent"):
                anchors[anchor]["verdict"] = _verdict(
                    sc.clearance(mint, anchors[anchor]["features"])
                )
            fields = {}
            for name in sc.FEATURES:
                a = anchors["pool"]["features"].get(name)
                b = anchors["parent"]["features"].get(name)
                fields[name] = {"pool": a, "parent": b, "within_band": _within_band(name, a, b)}
            entry.update(anchors=anchors, fields=fields)
            comparisons.append(entry)
            print(
                f"[2] {mint[:8]}… pool={anchors['pool']['verdict']} "
                f"parent={anchors['parent']['verdict']} "
                f"in_band={sum(1 for f in fields.values() if f['within_band'])}/10"
            )
        results["comparisons"] = comparisons
        results["enhanced_credits"] = enhanced_spent
    except CreditCapError as refusal:
        results["gate_refusal"] = str(refusal)
        print(f"GATE REFUSED (a refusal is a working gate): {refusal}")

    results["spent_at_end"] = gate.spent()
    results["stage_g_task_1_credits"] = gate.spent() - start
    out = VENDOR / "stage_g_anchor_results.json"
    out.write_text(json.dumps(results, indent=1) + "\n")
    print(f"ledger at end: {results['spent_at_end']} (task 1 spent {gate.spent() - start})")
    print(f"results: {out}")


if __name__ == "__main__":
    main()
