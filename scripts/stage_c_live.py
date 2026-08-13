"""Stage C live measurements: T0 tolerance, enhanced batch semantics, the KAT.

Operator harness — run with the key in the environment (or .env):

    uv run python scripts/stage_c_live.py

Three phases, each inside its registered sub-budget (progress.md, Stage C
pre-registration; total ledger cap ``STAGE_C_CREDIT_CAP`` = 5,000):

A. **T0 tolerance** (≤ 400): for the six addendum pools, fetch the POOL
   address over [claimed_t0 - 1 h, claimed_t0 + 30 min) via Method B and
   measure the offset between claimed creation and earliest on-chain
   activity — the claim is external and the tolerance is measured, never
   assumed zero.
B. **Enhanced batch semantics** (≤ 400): probes with 1, 100, and 101 real
   signatures against POST /v0/transactions — the 101 probe goes through a
   raw client because the library client refuses oversized batches by
   design, and it is priced conservatively as 2 calls before sending.
C. **Per-pool enhanced cost + the system KAT** (≤ 3,400 enhanced): fetch
   each registered KAT mint's launch window, order pools sparse-first by
   in-window signature count, price each pool's whole enhanced sweep before
   its first call (skip and report what does not fit), parse, merge the
   live token-security flags, score through the refusal-first pipeline, and
   compare field-by-field against the committed snapshot under the
   registered tolerance.

A gate refusal anywhere stops the run and is REPORTED as a working gate;
nothing raises the cap. Results land in data/vendor/stage_c_live_results.json.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx

from solclear import scorer as sc
from solclear.config import STAGE_C_CREDIT_CAP, Settings
from solclear.enhanced import (
    DEFAULT_ENHANCED_BASE_URL,
    MAX_SIGNATURES_PER_CALL,
    EnhancedClient,
    GatedEnhanced,
    calls_needed,
)
from solclear.gate import CreditCapError, CreditGate
from solclear.method_b import GatedRpc, WindowFetch, fetch_window
from solclear.parse import ParsedWindow, parse_window
from solclear.pipeline import score_pool
from solclear.rpc import HeliusRpc
from solclear.scorer import Clearance, Unscorable

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "data" / "vendor"
SNAPSHOT = ROOT / "data" / "snapshots" / "features_c23.csv"

WINDOW_S = 1_800
PRE_WINDOW_S = 3_600
PHASE_A_BUDGET = 400
PHASE_B_BUDGET = 400
PHASE_C_ENHANCED_BUDGET = 3_400
PER_POOL_RETRIEVAL_GUARD = 60  # stop a phase when < this remains of its budget

# Registered samples (progress.md, Stage C pre-registration).
TOLERANCE_MINTS = (
    "Hp4XeAZ5EhKnFGm8Yv5GhZYmspNXGWV8SoRXPz91ZUab",
    "UutVe14D7KVKdLzDtbKmWet2jo6wVfw8aMHovr6wMs5",
    "7CSWFsrB3gPc5o5hxKTJCUbFDq4QyTWpjVG76S1Xpump",
    "CP1KFKft4HtvNgNx5PDPrsmZbBs9fDFoVbJAKfiRAUde",
    "gYgUiBNGMgHiKC2aReo12JTp5rJP4WpR892hFcbpump",
    "36gmCN9HLE5s6j8FdEYUCywByZU2KKKYy3UnAShmpump",
)
KAT_MINTS = (
    "CP1KFKft4HtvNgNx5PDPrsmZbBs9fDFoVbJAKfiRAUde",
    "2E6SSuVKVrQ6113KpWvzvhfY9yQ647E83V6e656fpump",
    "12WRu4BdJk1yM3Nk433yg3S9GnxniUdueeu29iMPpump",
    "2ZpmY9iSdbSZVkuv64Y467FcQ5vJegbUTTMr4YJyjb2X",
    "8BnZ17s9pAd3g7s7jSPr2efXLEdKHMajqPYEkcSjmdm1",
    "Hp4XeAZ5EhKnFGm8Yv5GhZYmspNXGWV8SoRXPz91ZUab",
    "7CSWFsrB3gPc5o5hxKTJCUbFDq4QyTWpjVG76S1Xpump",
)

COUNT_FIELDS = ("n_early_holders", "insider_funded_early_holders")
SHARE_FIELDS = ("creator_allocation_t0", "top5_concentration_wend")
NOW_STATE_FIELDS = ("freezable", "mintable", "nontransf", "thook")


def _snapshot_rows() -> dict[str, dict[str, float | None]]:
    rows: dict[str, dict[str, float | None]] = {}
    with SNAPSHOT.open() as fh:
        for row in csv.DictReader(fh):
            rows[row["mint"]] = {
                k: (None if row[k] in ("", "None") else float(row[k])) for k in sc.FEATURES
            }
    return rows


def _classify_field(name: str, snap: float | None, live: float | None) -> str:
    """Provenance-first classification, per the registered tolerance."""
    if snap is None and live is None:
        return "agree_absent"
    if snap is None:
        return "snapshot_absent_live_present"
    if live is None:
        return "live_absent"  # feeds a refusal; agreement class when snapshot also thin
    if name == "authority_revoked_in_window":
        return "agree_exact" if snap == live else "GENUINE_MISMATCH"
    if name in COUNT_FIELDS:
        return "agree_within_1" if abs(snap - live) <= 1.0 else "GENUINE_MISMATCH"
    if name in SHARE_FIELDS:
        return "agree_within_0.01" if abs(snap - live) <= 0.01 else "GENUINE_MISMATCH"
    if name == "creator_time_to_first_sell_s":
        return "agree_within_60s" if abs(snap - live) <= 60.0 else "GENUINE_MISMATCH"
    if name in NOW_STATE_FIELDS:
        if snap == live:
            return "agree_exact"
        if name in ("freezable", "mintable") and live == 0.0 and snap == 1.0:
            return "monotonic_unknowable"  # revocable after the window
        return "GENUINE_MISMATCH"
    return "unclassified"


def _verdict_dict(verdict: Clearance | Unscorable) -> dict[str, Any]:
    if isinstance(verdict, Clearance):
        return {
            "kind": "clearance",
            "cleared": verdict.cleared,
            "clearance_score": round(verdict.clearance_score, 4),
        }
    return {"kind": "unscorable", "reason": verdict.reason, "missing": list(verdict.missing)}


def _live_features(
    parsed: ParsedWindow, sec_features: dict[str, float | None], fetch: WindowFetch
) -> dict[str, float | None]:
    """The live feature mapping exactly as the pipeline assembles it."""
    from solclear.features import features as compute

    assembled: dict[str, float | None] = dict(
        compute(list(parsed.events), float(fetch.t0_s), parsed.creator or "", None)
    )
    assembled.update(sec_features)
    return assembled


def main() -> None:
    settings = Settings(helius_credit_cap=STAGE_C_CREDIT_CAP)
    key = settings.require_helius_key().get_secret_value()
    gate = CreditGate(settings)
    rpc = GatedRpc(HeliusRpc(key), gate)
    enhanced = GatedEnhanced(EnhancedClient(key), gate)

    claims: dict[str, dict[str, Any] | None] = json.loads(
        (VENDOR / "stage_c_t0_claims.json").read_text()
    )
    token_security: dict[str, dict[str, Any] | None] = json.loads(
        (VENDOR / "stage_c_token_security.json").read_text()
    )
    snapshot = _snapshot_rows()
    results: dict[str, Any] = {"cap": STAGE_C_CREDIT_CAP, "spent_at_start": gate.spent()}
    print(f"ledger at start: {results['spent_at_start']} / cap {STAGE_C_CREDIT_CAP}")

    try:
        # ------------------------- Phase A: T0 tolerance ------------------------- #
        phase_a_start = gate.spent()
        tolerance: list[dict[str, Any]] = []
        sig_bank: list[str] = []  # real signatures for the phase B probes
        for mint in TOLERANCE_MINTS:
            if gate.spent() - phase_a_start > PHASE_A_BUDGET - PER_POOL_RETRIEVAL_GUARD:
                tolerance.append({"mint": mint, "skipped": "phase A sub-budget"})
                continue
            claim = claims.get(mint)
            if claim is None:
                tolerance.append({"mint": mint, "skipped": "unresolved claim"})
                continue
            t0c = int(claim["claimed_t0_s"])
            before = gate.spent()
            fetch = fetch_window(
                rpc, str(claim["pool_address"]), t0c - PRE_WINDOW_S, t0c + WINDOW_S
            )
            earliest = fetch.signatures[0].block_time_s if fetch.signatures else None
            offset = None if earliest is None else earliest - t0c
            sig_bank.extend(s.signature for s in fetch.signatures)
            tolerance.append(
                {
                    "mint": mint,
                    "pool": claim["pool_address"],
                    "claimed_t0_s": t0c,
                    "earliest_seen_s": earliest,
                    "offset_s": offset,
                    "reached_t0": fetch.reached_t0,
                    "in_window_sigs": len(fetch.signatures),
                    "credits": gate.spent() - before,
                }
            )
            print(
                f"[A] {mint[:8]}… offset={offset} reached={fetch.reached_t0} "
                f"sigs={len(fetch.signatures)} credits={gate.spent() - before}"
            )
        results["phase_a_t0_tolerance"] = tolerance
        results["phase_a_credits"] = gate.spent() - phase_a_start

        # -------------------- Phase B: enhanced batch semantics ------------------ #
        phase_b_start = gate.spent()
        probes: list[dict[str, Any]] = []
        raw = httpx.Client(base_url=DEFAULT_ENHANCED_BASE_URL, timeout=30.0)
        try:
            for n, charge_calls in ((1, 1), (100, 1), (101, 2)):
                if len(sig_bank) < n:
                    probes.append({"n": n, "skipped": f"only {len(sig_bank)} sigs available"})
                    continue
                if gate.spent() - phase_b_start + charge_calls * 100 > PHASE_B_BUDGET:
                    probes.append({"n": n, "skipped": "phase B sub-budget"})
                    continue
                gate.charge("enhanced", charge_calls, f"batch-probe n={n}")
                resp = raw.post(
                    f"/v0/transactions?api-key={key}", json={"transactions": sig_bank[:n]}
                )
                body_len = len(resp.json()) if resp.status_code == 200 else None
                interesting = {
                    k: v
                    for k, v in resp.headers.items()
                    if any(t in k.lower() for t in ("credit", "usage", "limit", "remaining"))
                }
                probes.append(
                    {
                        "n": n,
                        "status": resp.status_code,
                        "returned": body_len,
                        "headers": interesting,
                    }
                )
                print(
                    f"[B] n={n} -> HTTP {resp.status_code}, returned={body_len}, "
                    f"headers={interesting}"
                )
        finally:
            raw.close()
        results["phase_b_probes"] = probes
        results["phase_b_credits"] = gate.spent() - phase_b_start

        # ------------- Phase C: per-pool enhanced cost + the system KAT ---------- #
        phase_c_start = gate.spent()
        fetches: dict[str, WindowFetch] = {}
        for mint in KAT_MINTS:
            claim = claims.get(mint)
            if claim is None:
                continue
            t0c = int(claim["claimed_t0_s"])
            before = gate.spent()
            fetches[mint] = fetch_window(rpc, mint, t0c, t0c + WINDOW_S)
            print(
                f"[C:fetch] {mint[:8]}… sigs={len(fetches[mint].signatures)} "
                f"reached={fetches[mint].reached_t0} credits={gate.spent() - before}"
            )
        results["phase_c_retrieval_credits"] = gate.spent() - phase_c_start

        kat: list[dict[str, Any]] = []
        enhanced_spent = 0
        # Sparse-first by in-window signature count, per the registration.
        for mint in sorted(fetches, key=lambda m: len(fetches[m].signatures)):
            fetch = fetches[mint]
            claim = claims[mint]
            assert claim is not None
            n_sigs = len(fetch.signatures)
            cost = calls_needed(n_sigs) * 100 if n_sigs else 0
            entry: dict[str, Any] = {
                "mint": mint,
                "in_window_sigs": n_sigs,
                "reached_t0": fetch.reached_t0,
                "enhanced_cost_priced": cost,
            }
            if enhanced_spent + cost > PHASE_C_ENHANCED_BUDGET:
                entry["skipped"] = "phase C enhanced sub-budget (priced before first call)"
                kat.append(entry)
                print(f"[C] {mint[:8]}… SKIPPED: {cost} would exceed the sub-budget")
                continue
            payloads: list[dict[str, Any]] = []
            sigs = [s.signature for s in fetch.signatures]
            for i in range(0, len(sigs), MAX_SIGNATURES_PER_CALL):
                payloads.extend(enhanced.transactions(sigs[i : i + MAX_SIGNATURES_PER_CALL]))
            enhanced_spent += cost
            parsed = parse_window(
                payloads,
                mint=mint,
                pool_address=str(claim["pool_address"]),
                t0_s=float(fetch.t0_s),
                end_s=float(fetch.end_s),
            )
            entry["parse_report"] = asdict(parsed.report)
            entry["creator"] = parsed.creator
            sec = token_security.get(mint)
            sec_features: dict[str, float | None] = (
                {k: sec[k] for k in NOW_STATE_FIELDS} if sec else dict.fromkeys(NOW_STATE_FIELDS)
            )
            live_verdict = score_pool(
                fetch=fetch,
                txs=list(parsed.events),
                parse_report=parsed.report,
                token_security=sec_features,
                creator=parsed.creator or "",
            )
            snap_row = snapshot[mint]
            offline_verdict = sc.clearance(mint, snap_row)
            live_feats = _live_features(parsed, sec_features, fetch)
            entry["fields"] = {
                name: {
                    "snapshot": snap_row.get(name),
                    "live": live_feats.get(name),
                    "class": _classify_field(name, snap_row.get(name), live_feats.get(name)),
                }
                for name in sc.FEATURES
            }
            entry["offline_verdict"] = _verdict_dict(offline_verdict)
            entry["live_verdict"] = _verdict_dict(live_verdict)
            kat.append(entry)
            print(
                f"[C] {mint[:8]}… live={entry['live_verdict']} offline={entry['offline_verdict']}"
            )
        results["phase_c_kat"] = kat
        results["phase_c_enhanced_credits"] = enhanced_spent
    except CreditCapError as refusal:
        results["gate_refusal"] = str(refusal)
        print(f"GATE REFUSED (a refusal is a working gate): {refusal}")

    results["spent_at_end"] = gate.spent()
    out = VENDOR / "stage_c_live_results.json"
    out.write_text(json.dumps(results, indent=1) + "\n")
    print(f"ledger at end: {results['spent_at_end']} / cap {STAGE_C_CREDIT_CAP}")
    print(f"results: {out}")


if __name__ == "__main__":
    main()
