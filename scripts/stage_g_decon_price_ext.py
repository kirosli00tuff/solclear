"""Stage G Task 2, declared extension: sharpen the probe, leave the bar alone.

Run with the key in .env:  uv run python scripts/stage_g_decon_price_ext.py

**Why this exists, stated before its numbers.** The registered probe was 12
pools, four per tercile, and it returned a point estimate of 5,108,814 weighted
against a 745,915 affordability threshold — decisive on its face. But its own
bootstrap interval is **[366,564, 13,252,764]**, which straddles the threshold
with ~10% of draws below it: the registered estimator cannot defend the decision
at n = 4 per stratum, because the per-pool cost distribution is heavy-tailed and
the committed 6h transaction count turns out not to predict it.

So the probe is extended. **The registered affordability bar is untouched**, and
the trigger for extending is a stated, checkable property of the *input* — a
bootstrap interval spanning the threshold — not which side of the threshold the
point estimate landed on. Extending can move the answer either way, which is
why doing it after seeing an interval is not bar-bending. The declared deviation
is the probe *size* (12 -> up to 48); the registered probe **sub-budget of 2,500
weighted is not exceeded**, and the original twelve draws stay in the sample
exactly as drawn — the extension samples the remainder under its own seed and
never redraws.
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path
from typing import Any

from scripts.stage_g_decon_price import (
    DECON_HORIZON_S,
    PROBE_BUDGET,
    PROBE_MAX_PAGES,
    PROBE_SEED,
    RETRIEVAL_PER_POOL,
    WINDOW_S,
    _t0_seconds,
    load_population,
)
from solclear.config import STAGE_G_CREDIT_CAP, Settings
from solclear.enhanced import calls_needed
from solclear.gate import CreditCapError, CreditGate
from solclear.method_b import GatedRpc, fetch_window
from solclear.rpc import HeliusRpc

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "data" / "vendor"

EXTENSION_SEED = PROBE_SEED + 1
EXTENSION_PER_TERCILE = 12
# Leave room for one page-capped pool (~195 weighted) so the guard never stops
# mid-fetch on a pool it has already started paying for.
GUARD_RESERVE = 250
BOOTSTRAP_DRAWS = 20_000


def _strata(pop: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], float, float]:
    counts = sorted(p["six_h_n_tx"] for p in pop)
    lo_b, hi_b = counts[len(counts) // 3], counts[2 * len(counts) // 3]
    out: dict[str, list[dict[str, Any]]] = {"low": [], "mid": [], "high": []}
    for p in pop:
        name = "low" if p["six_h_n_tx"] < lo_b else ("mid" if p["six_h_n_tx"] < hi_b else "high")
        out[name].append(p)
    return out, lo_b, hi_b


def _bootstrap(by: dict[str, list[int]], sizes: dict[str, int], retrieval: int) -> list[float]:
    rng = random.Random(PROBE_SEED)
    draws: list[float] = []
    for _ in range(BOOTSTRAP_DRAWS):
        total = float(retrieval)
        for name, costs in by.items():
            total += statistics.fmean(rng.choices(costs, k=len(costs))) * sizes[name]
        draws.append(total)
    draws.sort()
    return draws


def main() -> None:
    settings = Settings(helius_credit_cap=STAGE_G_CREDIT_CAP)
    key = settings.require_helius_key().get_secret_value()
    gate = CreditGate(settings)
    rpc = GatedRpc(HeliusRpc(key), gate)

    prior = json.loads((VENDOR / "stage_g_decon_price.json").read_text())
    already = {p["mint"] for p in prior["probes"] if "sigs_30d" in p}
    spent_on_probe = int(prior["probe_credits"])
    pop = load_population()
    strata, _lo_b, _hi_b = _strata(pop)

    rng = random.Random(EXTENSION_SEED)
    extension: list[dict[str, Any]] = []
    for name in ("low", "mid", "high"):
        remainder = sorted(
            (p for p in strata[name] if p["mint"] not in already), key=lambda p: p["mint"]
        )
        k = min(EXTENSION_PER_TERCILE, len(remainder))
        extension.extend((p | {"stratum": name}) for p in rng.sample(remainder, k))

    start = gate.spent()
    probes: list[dict[str, Any]] = list(prior["probes"])
    print(
        f"extension: {len(extension)} pools; registered sub-budget {PROBE_BUDGET}, "
        f"{spent_on_probe} already spent on the registered twelve"
    )
    try:
        for p in extension:
            used = spent_on_probe + (gate.spent() - start)
            if used > PROBE_BUDGET - GUARD_RESERVE:
                print(f"[ext] sub-budget guard hit at {used}/{PROBE_BUDGET}; stopping")
                break
            t0 = _t0_seconds(p["first_activity"])
            before = gate.spent()
            fetch = fetch_window(
                rpc, p["pool"], t0 + WINDOW_S, t0 + DECON_HORIZON_S, max_pages=PROBE_MAX_PAGES
            )
            n_sigs = len(fetch.signatures)
            probes.append(
                {
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
                    "extension": True,
                }
            )
            print(
                f"[ext] {p['stratum']:>4} {p['mint'][:8]}… 6h={p['six_h_n_tx']:.0f} "
                f"30d_sigs={n_sigs}{'' if fetch.reached_t0 else ' (FLOOR)'} "
                f"cost={probes[-1]['enhanced_credits_corrected']}"
            )
    except CreditCapError as refusal:
        prior["extension_gate_refusal"] = str(refusal)
        print(f"GATE REFUSED (a refusal is a working gate): {refusal}")

    measured = [e for e in probes if "sigs_30d" in e]
    sizes = {k: len(v) for k, v in strata.items()}
    by = {
        s: [e["enhanced_credits_corrected"] for e in measured if e["stratum"] == s]
        for s in ("low", "mid", "high")
    }
    retrieval = RETRIEVAL_PER_POOL * len(pop)
    per_stratum = {
        s: {
            "n_probed": len(by[s]),
            "n_population": sizes[s],
            "mean_enhanced_credits": round(statistics.fmean(by[s]), 1),
            "median_enhanced_credits": statistics.median(by[s]),
            "min_enhanced_credits": min(by[s]),
            "max_enhanced_credits": max(by[s]),
            "n_floor_capped": sum(1 for e in measured if e["stratum"] == s and not e["complete"]),
            "stratum_total_enhanced": round(statistics.fmean(by[s]) * sizes[s]),
        }
        for s in ("low", "mid", "high")
    }
    total_enhanced = sum(v["stratum_total_enhanced"] for v in per_stratum.values())
    draws = _bootstrap(by, sizes, retrieval)
    ci = (draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws))])

    prior.update(
        probes=probes,
        extension_seed=EXTENSION_SEED,
        extension_per_tercile=EXTENSION_PER_TERCILE,
        probe_credits=spent_on_probe + (gate.spent() - start),
        n_probed_total=len(measured),
        per_stratum=per_stratum,
        corrected_total_enhanced=total_enhanced,
        corrected_total_retrieval=retrieval,
        corrected_total=total_enhanced + retrieval,
        bootstrap_ci_95=[round(ci[0]), round(ci[1])],
        spent_at_end=gate.spent(),
    )
    (VENDOR / "stage_g_decon_price.json").write_text(json.dumps(prior, indent=1) + "\n")

    print()
    for s in ("low", "mid", "high"):
        print(f"  {s}: {per_stratum[s]}")
    print(f"\nn probed: {len(measured)} of {len(pop)}")
    print(f"corrected total: {prior['corrected_total']:,} weighted")
    print(f"bootstrap 95% interval: [{ci[0]:,.0f}, {ci[1]:,.0f}]")
    print(f"probe spent {prior['probe_credits']} of {PROBE_BUDGET}; ledger {gate.spent()}")


if __name__ == "__main__":
    main()
