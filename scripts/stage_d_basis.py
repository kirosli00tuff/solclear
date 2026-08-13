"""Stage D live measurements: mint-creation probes and the both-anchors comparison.

Run with the key in .env:  uv run python scripts/stage_d_basis.py

Phase 1 (Task 2, ≤ 200 weighted): per pre-registered mint, (a) a DAS
``getAsset`` call (charged at the vendor's 10/call) scanned for any
creation-time-bearing field, and (b) a from-now signature paging probe
capped at 15 pages — the cap makes it a *scaling* measurement, not an
unbounded walk: reaching the oldest signature inside the cap yields the
mint's first-activity instant and its cost; hitting the cap reports how the
cost scales (with post-launch depth, the exact from-now pathology ADR-002
exists to avoid).

Phase 2 (Task 3, ≤ 2,600: retrieval ≤ 500, enhanced ≤ 2,100): for each of
the six pools, the full feature vector under BOTH anchors —

- **pool anchor**: [gt_pool_created_at, +1800s), exactly as Stage C.1
  scored it (CP1KFKft's window is reused from the C.1 results rather than
  re-bought);
- **parent anchor**: [solrpds_first_activity - 60s, +1800s), the basis
  Task 1 established from the parent's own code (labels.py:81 reads
  ``FIRST_POOL_ACTIVITY_TIMESTAMP``; the C.22 report fixes the window to
  "[T0-60s, T0+1800s]"), with features computed at t0 = solrpds_first_activity
  so pre-roll sells can go negative exactly as the snapshot's do.

Pairs are processed sparse-first by combined enhanced cost, each pair priced
before its first enhanced call; a pair that does not fit is skipped and
reported. Verdicts under both anchors are compared per the registered
materiality threshold. A gate refusal ends the run as a reported refusal.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx

from solclear import scorer as sc
from solclear.config import STAGE_D_CREDIT_CAP, Settings
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
PHASE_1_BUDGET = 200
PHASE_2_RETRIEVAL_BUDGET = 500
PHASE_2_ENHANCED_BUDGET = 2_100
PAGING_CAP_PAGES = 15

MINTS = (
    "Hp4XeAZ5EhKnFGm8Yv5GhZYmspNXGWV8SoRXPz91ZUab",
    "UutVe14D7KVKdLzDtbKmWet2jo6wVfw8aMHovr6wMs5",
    "7CSWFsrB3gPc5o5hxKTJCUbFDq4QyTWpjVG76S1Xpump",
    "CP1KFKft4HtvNgNx5PDPrsmZbBs9fDFoVbJAKfiRAUde",
    "gYgUiBNGMgHiKC2aReo12JTp5rJP4WpR892hFcbpump",
    "36gmCN9HLE5s6j8FdEYUCywByZU2KKKYy3UnAShmpump",
)
NOW_STATE_FIELDS = ("freezable", "mintable", "nontransf", "thook")
COUNT_FIELDS = ("n_early_holders", "insider_funded_early_holders")
SHARE_FIELDS = ("creator_allocation_t0", "top5_concentration_wend")

_TIME_KEY_TOKENS = ("time", "created", "slot", "minted", "block")


def _time_like_fields(obj: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            if any(t in str(k).lower() for t in _TIME_KEY_TOKENS):
                found.append(f"{path}={v!r}"[:80])
            found.extend(_time_like_fields(v, path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:3]):
            found.extend(_time_like_fields(v, f"{prefix}[{i}]"))
    return found


def _within_band(name: str, a: float | None, b: float | None) -> bool:
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


def main() -> None:
    settings = Settings(helius_credit_cap=STAGE_D_CREDIT_CAP)
    key = settings.require_helius_key().get_secret_value()
    gate = CreditGate(settings)
    rpc = GatedRpc(HeliusRpc(key), gate)
    # DAS methods take object params, not the JSON-RPC positional list the
    # library client sends -- the probe posts directly.
    das = httpx.Client(base_url="https://mainnet.helius-rpc.com", timeout=30.0)
    enhanced = GatedEnhanced(EnhancedClient(key), gate)

    claims = json.loads((VENDOR / "stage_c_t0_claims.json").read_text())
    parent_t0 = json.loads((VENDOR / "stage_d_parent_t0.json").read_text())
    token_security = json.loads((VENDOR / "stage_c_token_security.json").read_text())
    c1 = json.loads((VENDOR / "stage_c_live_results.json").read_text())
    c1_by_mint = {e["mint"]: e for e in c1.get("phase_c_kat", []) if "fields" in e}

    results: dict[str, Any] = {"cap": STAGE_D_CREDIT_CAP, "spent_at_start": gate.spent()}
    print(f"ledger at start: {results['spent_at_start']} / cap {STAGE_D_CREDIT_CAP}")

    try:
        # ------------------- Phase 1: mint-creation probes ------------------- #
        p1_start = gate.spent()
        probes: list[dict[str, Any]] = []
        for mint in MINTS:
            entry: dict[str, Any] = {"mint": mint}
            before = gate.spent()
            gate.charge("das", 1, f"getAsset {mint}")
            das_resp = das.post(
                f"/?api-key={key}",
                json={"jsonrpc": "2.0", "id": "1", "method": "getAsset", "params": {"id": mint}},
            )
            asset = das_resp.json().get("result") if das_resp.status_code == 200 else None
            entry["das_time_like_fields"] = (
                _time_like_fields(asset) if isinstance(asset, dict) else ["<non-dict result>"]
            )
            entry["das_credits"] = gate.spent() - before

            before = gate.spent()
            oldest_ts: int | None = None
            pages = 0
            cursor: str | None = None
            while pages < PAGING_CAP_PAGES:
                batch = rpc.signatures_for_address(mint, cursor, 1_000)
                pages += 1
                if not batch:
                    break
                cursor = batch[-1].signature
                if len(batch) < 1_000:
                    oldest_ts = batch[-1].block_time_s
                    break
            entry.update(
                paging_pages=pages,
                paging_reached_oldest=oldest_ts is not None,
                oldest_ts=oldest_ts,
                paging_credits=gate.spent() - before,
            )
            probes.append(entry)
            print(
                f"[1] {mint[:8]}… das_time_fields={len(entry['das_time_like_fields'])} "
                f"paging: pages={pages} reached={oldest_ts is not None} "
                f"credits={entry['das_credits'] + entry['paging_credits']}"
            )
            if gate.spent() - p1_start > PHASE_1_BUDGET - 30:
                probes.append({"skipped_remaining": True})
                break
        results["phase_1_probes"] = probes
        results["phase_1_credits"] = gate.spent() - p1_start

        # ---------------- Phase 2: both-anchors feature vectors --------------- #
        p2_start = gate.spent()
        windows: dict[tuple[str, str], WindowFetch] = {}
        for mint in MINTS:
            gt_t0 = int(claims[mint]["claimed_t0_s"])
            par_t0 = int(parent_t0[mint]["t0_parent_s"])
            for anchor, lo, hi in (
                ("pool", gt_t0, gt_t0 + WINDOW_S),
                ("parent", par_t0 - PRE_ROLL_S, par_t0 + WINDOW_S),
            ):
                if anchor == "pool" and mint in c1_by_mint:
                    continue  # reuse the C.1 window rather than re-buying it
                if gate.spent() - p2_start > PHASE_2_RETRIEVAL_BUDGET - 60:
                    print(f"[2] retrieval budget guard hit before {mint[:8]}/{anchor}")
                    break
                before = gate.spent()
                windows[(mint, anchor)] = fetch_window(rpc, mint, lo, hi)
                print(
                    f"[2:fetch] {mint[:8]}…/{anchor} sigs={len(windows[(mint, anchor)].signatures)} "
                    f"reached={windows[(mint, anchor)].reached_t0} credits={gate.spent() - before}"
                )
        results["phase_2_retrieval_credits"] = gate.spent() - p2_start

        def pair_cost(mint: str) -> int:
            cost = 0
            for anchor in ("pool", "parent"):
                fetch = windows.get((mint, anchor))
                if fetch is not None:
                    cost += calls_needed(len(fetch.signatures)) * 100 if fetch.signatures else 0
            return cost

        comparisons: list[dict[str, Any]] = []
        enhanced_spent = 0
        for mint in sorted(MINTS, key=pair_cost):
            entry = {"mint": mint, "pair_enhanced_priced": pair_cost(mint)}
            missing_windows = [
                a
                for a in ("pool", "parent")
                if (mint, a) not in windows and not (a == "pool" and mint in c1_by_mint)
            ]
            if missing_windows:
                entry["skipped"] = f"window(s) not fetched: {missing_windows}"
                comparisons.append(entry)
                continue
            if enhanced_spent + entry["pair_enhanced_priced"] > PHASE_2_ENHANCED_BUDGET:
                entry["skipped"] = "pair enhanced cost exceeds sub-budget (priced before call)"
                comparisons.append(entry)
                print(f"[2] {mint[:8]}… pair SKIPPED at {entry['pair_enhanced_priced']}")
                continue

            sec = token_security.get(mint) or {}
            sec_features = {k: sec.get(k) for k in NOW_STATE_FIELDS}
            anchors: dict[str, dict[str, Any]] = {}
            for anchor in ("pool", "parent"):
                if anchor == "pool" and mint in c1_by_mint:
                    c1e = c1_by_mint[mint]
                    anchors["pool"] = {
                        "reused_from_c1": True,
                        "features": {k: d["live"] for k, d in c1e["fields"].items()},
                        "parse_report": c1e["parse_report"],
                        "reached_t0": c1e["reached_t0"],
                    }
                    continue
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
                fields[name] = {
                    "pool": a,
                    "parent": b,
                    "within_band": _within_band(name, a, b),
                }
            entry.update(anchors=anchors, fields=fields)
            comparisons.append(entry)
            print(
                f"[2] {mint[:8]}… pool={anchors['pool']['verdict']} "
                f"parent={anchors['parent']['verdict']} "
                f"in_band={sum(1 for f in fields.values() if f['within_band'])}/10"
            )
        results["phase_2_comparisons"] = comparisons
        results["phase_2_enhanced_credits"] = enhanced_spent
    except CreditCapError as refusal:
        results["gate_refusal"] = str(refusal)
        print(f"GATE REFUSED (a refusal is a working gate): {refusal}")

    results["spent_at_end"] = gate.spent()
    out = VENDOR / "stage_d_basis_results.json"
    out.write_text(json.dumps(results, indent=1) + "\n")
    print(f"ledger at end: {results['spent_at_end']} / cap {STAGE_D_CREDIT_CAP}")
    print(f"results: {out}")


if __name__ == "__main__":
    main()
