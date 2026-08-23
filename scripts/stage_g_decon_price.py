"""Stage G Task 2: re-price the decon-unbiased test under corrected weights.

Run with the key in .env:  uv run python scripts/stage_g_decon_price.py

The parent priced the decontaminated-unbiased test at **124,764 weighted** under
a ledger that carried ``enhanced`` at **10 credits per call** (MLCE C.26 §2,
ADR-054 there). solclear corrected that weight to the vendor's published **100
credits per call** in Stage C, before the first enhanced call this repository
ever made. The *request plan* is unchanged by the correction — same pools, same
100-signature batch semantics, same 30-day insider-sell horizon — so the
arithmetic floor of the correction is x10. This script does not stop at the
multiplication: it **measures**, the way the Stage B addendum measured
retrieval, and multiplies out from measurement.

What the decon test actually needs, per the parent's committed estimator
(``research/detection/history.py::decontaminate``): for every honest pool,
enough transaction detail over ``(T0 + 1800 s, T0 + 30 d]`` on the **pool**
address to see whether the insider set sold >= 70% of its window-end holdings.
That is ``ceil(signatures / 100) * 100`` weighted credits of enhanced detail per
pool, plus Method B retrieval.

Population: the honest class of the parent's committed ``behavior_c25.csv``
(read-only), whose pool address and T0 resolve from the archived SolRPDS CSVs at
**zero credits**. Probe: 12 pools, four drawn from each tercile of the committed
6h transaction count under a fixed seed, each pool's 30-day signature count
*measured* rather than extrapolated. A pool that hits the page cap is reported
as a **lower bound**, which can only understate the price — so a no-go read off
these numbers is a floor, not a guess.
"""

from __future__ import annotations

import csv
import json
import random
import statistics
from pathlib import Path
from typing import Any

from solclear.config import STAGE_G_CREDIT_CAP, Settings
from solclear.enhanced import calls_needed
from solclear.gate import CreditCapError, CreditGate
from solclear.method_b import GatedRpc, fetch_window
from solclear.rpc import HeliusRpc

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "data" / "vendor"
PARENT = Path.home() / "Documents" / "GitHub" / "MLCryptoEngine"

WINDOW_S = 1_800
DECON_HORIZON_S = 30 * 86_400  # history.SLOW_RUG_HORIZON_S — the parent's, unchanged
PROBE_BUDGET = 2_500
PROBE_PER_TERCILE = 4
PROBE_SEED = 20_260_822
# 150 pages x 1,000 signatures. A pool that hits it reports reached_t0=False and
# its count is a floor; the price computed from a floor is itself a floor.
PROBE_MAX_PAGES = 150
# Measured Method B retrieval cost per window, Stage G Task 1: 33-44 weighted.
RETRIEVAL_PER_POOL = 38


def load_population() -> list[dict[str, Any]]:
    """Honest class of the committed matrix, joined to archived pool address + T0."""
    resolved = json.loads((VENDOR / "stage_g_decon_population.json").read_text())["resolved"]
    matrix = PARENT / "data" / "processed" / "detection" / "behavior_c25.csv"
    with matrix.open(newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["cls"] == "honest_candidate"]
    out: list[dict[str, Any]] = []
    for r in rows:
        info = resolved[r["mint"]]
        out.append(
            {
                "mint": r["mint"],
                "pool": info["pool"],
                "first_activity": info["first_activity"],
                "source": r["source"],
                "year": r["year"],
                "six_h_n_tx": float(r["6h_n_tx"]),
                "has_decon_label": bool(r["decon"]),
            }
        )
    return out


def _t0_seconds(stamp: str) -> int:
    from datetime import UTC, datetime

    return int(datetime.strptime(stamp[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC).timestamp())


def main() -> None:
    settings = Settings(helius_credit_cap=STAGE_G_CREDIT_CAP)
    key = settings.require_helius_key().get_secret_value()
    gate = CreditGate(settings)
    rpc = GatedRpc(HeliusRpc(key), gate)

    pop = load_population()
    counts = sorted(p["six_h_n_tx"] for p in pop)
    lo_b, hi_b = counts[len(counts) // 3], counts[2 * len(counts) // 3]
    strata: dict[str, list[dict[str, Any]]] = {"low": [], "mid": [], "high": []}
    for p in pop:
        key_ = "low" if p["six_h_n_tx"] < lo_b else ("mid" if p["six_h_n_tx"] < hi_b else "high")
        strata[key_].append(p)

    rng = random.Random(PROBE_SEED)
    probe_set: list[dict[str, Any]] = []
    for name in ("low", "mid", "high"):
        pool_list = sorted(strata[name], key=lambda p: p["mint"])
        probe_set.extend((p | {"stratum": name}) for p in rng.sample(pool_list, PROBE_PER_TERCILE))

    start = gate.spent()
    results: dict[str, Any] = {
        "population_n": len(pop),
        "tercile_bounds_6h_tx": [lo_b, hi_b],
        "stratum_sizes": {k: len(v) for k, v in strata.items()},
        "probe_seed": PROBE_SEED,
        "probe_budget": PROBE_BUDGET,
        "probe_max_pages": PROBE_MAX_PAGES,
        "spent_at_start": start,
    }
    print(f"population {len(pop)} honest; terciles at {lo_b:.0f}/{hi_b:.0f} 6h tx")
    print(f"stratum sizes: {results['stratum_sizes']}")

    probes: list[dict[str, Any]] = []
    try:
        for p in probe_set:
            if gate.spent() - start > PROBE_BUDGET - 200:
                print(f"[probe] budget guard hit before {p['mint'][:8]}")
                probes.append({"mint": p["mint"], "skipped": "probe budget guard"})
                continue
            t0 = _t0_seconds(p["first_activity"])
            before = gate.spent()
            fetch = fetch_window(
                rpc,
                p["pool"],
                t0 + WINDOW_S,
                t0 + DECON_HORIZON_S,
                max_pages=PROBE_MAX_PAGES,
            )
            n_sigs = len(fetch.signatures)
            entry = {
                "mint": p["mint"],
                "pool": p["pool"],
                "stratum": p["stratum"],
                "six_h_n_tx": p["six_h_n_tx"],
                "sigs_30d": n_sigs,
                "complete": fetch.reached_t0,
                "pages": fetch.pages,
                "probe_credits": gate.spent() - before,
                "enhanced_calls": calls_needed(n_sigs),
                "enhanced_credits_corrected": calls_needed(n_sigs) * 100,
            }
            probes.append(entry)
            print(
                f"[probe] {p['stratum']:>4} {p['mint'][:8]}… 6h={p['six_h_n_tx']:.0f} "
                f"30d_sigs={n_sigs}{'' if fetch.reached_t0 else ' (FLOOR: page cap)'} "
                f"pages={fetch.pages} probe_cost={entry['probe_credits']} "
                f"decon_cost={entry['enhanced_credits_corrected']}"
            )
    except CreditCapError as refusal:
        results["gate_refusal"] = str(refusal)
        print(f"GATE REFUSED (a refusal is a working gate): {refusal}")

    results["probes"] = probes
    results["probe_credits"] = gate.spent() - start

    # ------------------------- multiply out, per stratum ------------------------ #
    measured = [e for e in probes if "sigs_30d" in e]
    per_stratum: dict[str, Any] = {}
    total_enhanced = 0.0
    for name in ("low", "mid", "high"):
        got = [e for e in measured if e["stratum"] == name]
        if not got:
            per_stratum[name] = {"n_probed": 0, "note": "not probed"}
            continue
        costs = [e["enhanced_credits_corrected"] for e in got]
        mean_cost = statistics.fmean(costs)
        stratum_total = mean_cost * len(strata[name])
        total_enhanced += stratum_total
        per_stratum[name] = {
            "n_probed": len(got),
            "n_population": len(strata[name]),
            "sigs_30d": [e["sigs_30d"] for e in got],
            "any_floor": any(not e["complete"] for e in got),
            "mean_enhanced_credits": round(mean_cost, 1),
            "median_enhanced_credits": statistics.median(costs),
            "min_enhanced_credits": min(costs),
            "max_enhanced_credits": max(costs),
            "stratum_total_enhanced": round(stratum_total),
        }
    retrieval_total = RETRIEVAL_PER_POOL * len(pop)
    results["per_stratum"] = per_stratum
    results["corrected_total_enhanced"] = round(total_enhanced)
    results["corrected_total_retrieval"] = retrieval_total
    results["corrected_total"] = round(total_enhanced) + retrieval_total
    results["parent_figure_old_weights"] = 124_764
    results["spent_at_end"] = gate.spent()

    out = VENDOR / "stage_g_decon_price.json"
    out.write_text(json.dumps(results, indent=1) + "\n")
    print()
    for name in ("low", "mid", "high"):
        print(f"  {name}: {per_stratum[name]}")
    print(
        f"\ncorrected total: {results['corrected_total']:,} weighted "
        f"({results['corrected_total_enhanced']:,} enhanced + {retrieval_total:,} retrieval)"
    )
    print(f"probe spent {results['probe_credits']} of {PROBE_BUDGET}; ledger {gate.spent()}")
    print(f"results: {out}")


if __name__ == "__main__":
    main()
