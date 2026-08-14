"""Stage E Tasks 3-4: realized outcomes and the three comparisons, as registered.

Run:  uv run python scripts/stage_e_outcomes.py     (keyless; zero credits)

Implements the registered rules verbatim (progress.md, Stage E
pre-registration) — none is tuned here: entry at the day-0 candle close;
equal weight; exit at horizon; the death rule (no candle in the 14 days
ending at horizon, or exit mark < 1% of entry -> realized -100%); execution
cost 450 bps round trip central (225 per leg) with 300/600 sensitivity,
charged on every memecoin leg of every basket; SOL is the operator's
HOLDING benchmark and carries no memecoin cost; cash at 4%/yr. Horizons are
realized-only. Bootstrap 10,000; Bonferroni over the registered 6 trials
(threshold p < 0.0083). Candles are cached append-only so reruns re-probe
nothing.
"""

from __future__ import annotations

import json
import random
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "data" / "vendor"
SCORES = VENDOR / "stage_e_scores.jsonl"
CANDLES = VENDOR / "stage_e_candles.jsonl"
OUT = VENDOR / "stage_e_analysis.json"

GECKO_BASE = "https://api.geckoterminal.com/api/v2"
UA = {"accept": "application/json", "user-agent": "solclear/0.1 (research)"}
GECKO_PACE_S = 6.0

DAY = 86_400
HORIZONS = (30, 90)
ENTRY_MAX_LAG_DAYS = 3
DEATH_GAP_DAYS = 14
DEATH_FLOOR_FRACTION = 0.01
COST_LEG_CENTRAL = 0.0225
COST_RT_SENSITIVITY = (0.030, 0.060)
CASH_ANNUAL = 0.04
BOOTSTRAP = 10_000
TRIALS = 6

random.seed(41)


def _load_scores() -> list[dict[str, Any]]:
    with SCORES.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _cached_candles() -> dict[str, list[list[float]]]:
    out: dict[str, list[list[float]]] = {}
    if CANDLES.is_file():
        with CANDLES.open() as fh:
            for line in fh:
                row = json.loads(line)
                out[row["pool_address"]] = row["candles"]
    return out


def _fetch_candles(pools: list[str]) -> dict[str, list[list[float]]]:
    cache = _cached_candles()
    todo = [p for p in pools if p not in cache]
    print(f"candles: {len(cache)} cached, {len(todo)} to fetch")
    client = httpx.Client(base_url=GECKO_BASE, timeout=20.0, headers=UA)
    for i, pool in enumerate(todo):
        time.sleep(GECKO_PACE_S)
        resp = client.get(f"/networks/solana/pools/{pool}/ohlcv/day", params={"limit": 1000})
        if resp.status_code == 429:
            time.sleep(30)
            resp = client.get(f"/networks/solana/pools/{pool}/ohlcv/day", params={"limit": 1000})
        rows = (
            ((resp.json().get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
            if resp.status_code == 200
            else []
        )
        candles = sorted([float(c[0]), float(c[4])] for c in rows)
        cache[pool] = candles
        with CANDLES.open("a") as fh:
            fh.write(json.dumps({"pool_address": pool, "candles": candles}) + "\n")
        if i % 20 == 0:
            print(f"  ... fetched {i + 1}/{len(todo)}")
    client.close()
    return cache


def _sol_series() -> dict[int, float]:
    """SOLUSDT daily closes keyed by day-start epoch, spanning the cohort."""
    out: dict[int, float] = {}
    start = int(datetime(2025, 8, 1, tzinfo=UTC).timestamp() * 1000)
    client = httpx.Client(timeout=20.0)
    while True:
        resp = client.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": "SOLUSDT", "interval": "1d", "startTime": start, "limit": 1000},
        )
        rows = resp.json() if resp.status_code == 200 else []
        if not rows:
            break
        for r in rows:
            out[int(r[0] // 1000)] = float(r[4])
        start = int(rows[-1][6]) + 1
        if len(rows) < 1000:
            break
    client.close()
    return out


def _position(
    candles: list[list[float]], t0_s: float, horizon_d: int, now_s: float
) -> dict[str, Any] | None:
    """Realized position under the registered rules, or None if not evaluable."""
    if not candles:
        return {"status": "no_candles"}
    entry = next((c for c in candles if c[0] + DAY >= t0_s + 1_800), None)
    if entry is None or entry[0] > t0_s + ENTRY_MAX_LAG_DAYS * DAY:
        return {"status": "unentered"}
    entry_ts, entry_px = entry
    if entry_px <= 0:
        return {"status": "unentered"}
    horizon_ts = entry_ts + horizon_d * DAY
    if horizon_ts > now_s:
        return None  # horizon not realized for this pool
    window = [c for c in candles if entry_ts <= c[0] <= horizon_ts]
    post = [c for c in window if c[0] > entry_ts]
    last_in_window = window[-1] if window else [entry_ts, entry_px]
    peak = max((c[1] for c in window), default=entry_px)
    peak_ts = next((c[0] for c in window if c[1] == peak), entry_ts)
    dead = (
        not any(horizon_ts - DEATH_GAP_DAYS * DAY <= c[0] <= horizon_ts for c in candles)
        or last_in_window[1] < DEATH_FLOOR_FRACTION * entry_px
    )
    exit_px = 0.0 if dead else last_in_window[1]
    gross = exit_px / entry_px - 1.0
    return {
        "status": "realized",
        "entry_ts": entry_ts,
        "entry_px": entry_px,
        "exit_ts": last_in_window[0],
        "exit_px": exit_px,
        "gross": gross,
        "dead": dead,
        "ever_above_entry": any(c[1] > entry_px for c in post),
        "days_to_peak": round((peak_ts - entry_ts) / DAY, 1),
        "peak_to_last_dd": 0.0 if peak <= 0 else (last_in_window[1] / peak - 1.0),
    }


def _net(gross: float, cost_leg: float) -> float:
    if gross <= -1.0:
        return -1.0
    return (1.0 + gross) * (1.0 - cost_leg) / (1.0 + cost_leg) - 1.0


def _dist(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0}
    xs = sorted(values)
    n = len(xs)

    def q(p: float) -> float:
        i = min(n - 1, max(0, round(p * (n - 1))))
        return xs[i]

    return {
        "n": n,
        "mean": sum(xs) / n,
        "median": q(0.5),
        "q25": q(0.25),
        "q75": q(0.75),
        "share_total_loss": sum(1 for x in xs if x <= -0.99) / n,
    }


def _boot_p_greater(sample: list[float], benchmark: float) -> float:
    """P(resampled mean <= benchmark): small = basket reliably beats it."""
    n = len(sample)
    if n == 0:
        return 1.0
    hits = 0
    for _ in range(BOOTSTRAP):
        m = sum(random.choice(sample) for _ in range(n)) / n
        if m <= benchmark:
            hits += 1
    return hits / BOOTSTRAP


def main() -> None:
    scores = _load_scores()
    now_s = datetime.now(UTC).timestamp()
    measurable = [s for s in scores if s.get("outcome") in ("cleared", "not_cleared", "refused")]
    candles = _fetch_candles([s["pool_address"] for s in measurable])
    sol = _sol_series()

    positions: dict[int, list[dict[str, Any]]] = {h: [] for h in HORIZONS}
    for s in measurable:
        t0 = datetime.fromisoformat(s["pool_created_at"].replace("Z", "+00:00")).timestamp()
        for h in HORIZONS:
            pos = _position(candles.get(s["pool_address"], []), t0, h, now_s)
            if pos is None or pos.get("status") != "realized":
                if pos is not None:
                    positions[h].append({**pos, "outcome": s["outcome"], "source": s["source"]})
                continue
            entry_day = int(pos["entry_ts"])
            exit_day = int(pos["exit_ts"])
            sol_ret = None
            if entry_day in sol and exit_day in sol and sol[entry_day] > 0:
                sol_ret = sol[exit_day] / sol[entry_day] - 1.0
            positions[h].append(
                {
                    **pos,
                    "outcome": s["outcome"],
                    "source": s["source"],
                    "net": _net(pos["gross"], COST_LEG_CENTRAL),
                    "net_lo": _net(pos["gross"], COST_RT_SENSITIVITY[0] / 2),
                    "net_hi": _net(pos["gross"], COST_RT_SENSITIVITY[1] / 2),
                    "sol_ret": sol_ret,
                }
            )

    analysis: dict[str, Any] = {"registered": {"trials": TRIALS, "deflated_alpha": 0.05 / TRIALS}}
    for h in HORIZONS:
        realized = [p for p in positions[h] if p.get("status") == "realized"]
        cleared = [p for p in realized if p["outcome"] == "cleared"]
        not_cleared = [p for p in realized if p["outcome"] == "not_cleared"]
        cash = CASH_ANNUAL * h / 365.0
        sol_marks = [p["sol_ret"] for p in cleared if p["sol_ret"] is not None]
        sol_mean = sum(sol_marks) / len(sol_marks) if sol_marks else None

        cleared_net = [p["net"] for p in cleared]
        nc_net = [p["net"] for p in not_cleared]
        all_net = [p["net"] for p in realized]
        n_cl = len(cleared_net)
        random_means: list[float] = []
        if n_cl and len(all_net) > n_cl:
            for _ in range(BOOTSTRAP):
                random_means.append(sum(random.sample(all_net, n_cl)) / n_cl)
        cl_mean = sum(cleared_net) / n_cl if n_cl else None

        block: dict[str, Any] = {
            "underpowered": n_cl < 20,
            "counts": {
                "realized": len(realized),
                "cleared": n_cl,
                "not_cleared": len(nc_net),
                "unentered": sum(1 for p in positions[h] if p.get("status") == "unentered"),
                "no_candles": sum(1 for p in positions[h] if p.get("status") == "no_candles"),
            },
            "cleared_gross": _dist([p["gross"] for p in cleared]),
            "cleared_net": _dist(cleared_net),
            "cleared_extras": {
                "share_ever_above_entry": (
                    sum(1 for p in cleared if p["ever_above_entry"]) / n_cl if n_cl else None
                ),
                "median_days_to_peak": _dist([p["days_to_peak"] for p in cleared]).get("median"),
                "net_sensitivity_means": {
                    "rt300": sum(p["net_lo"] for p in cleared) / n_cl if n_cl else None,
                    "rt600": sum(p["net_hi"] for p in cleared) / n_cl if n_cl else None,
                },
            },
            "not_cleared_net": _dist(nc_net),
            "benchmarks": {"sol_mean_same_windows": sol_mean, "cash": cash},
        }
        if n_cl and cl_mean is not None:
            block["comparisons"] = {
                "vs_sol": {
                    "delta_net": None if sol_mean is None else cl_mean - sol_mean,
                    "p_raw": None if sol_mean is None else _boot_p_greater(cleared_net, sol_mean),
                },
                "vs_cash": {
                    "delta_net": cl_mean - cash,
                    "p_raw": _boot_p_greater(cleared_net, cash),
                },
                "vs_not_cleared": {
                    "delta_net": (None if not nc_net else cl_mean - sum(nc_net) / len(nc_net)),
                    "p_raw": (
                        None
                        if not nc_net
                        else _boot_p_greater(cleared_net, sum(nc_net) / len(nc_net))
                    ),
                },
                "vs_random": {
                    "p_raw": (
                        None
                        if not random_means
                        else sum(1 for m in random_means if m >= cl_mean) / len(random_means)
                    ),
                },
            }
        # Source-split bias measurement (registered: >15pp gap -> split headline).
        split: dict[str, Any] = {}
        for tag, group in (
            (
                "birth_ordered",
                [p for p in realized if p["source"] in ("gt_birth_capture", "live_desc")],
            ),
            ("wayback_coin", [p for p in realized if p["source"] == "wayback_coin"]),
        ):
            split[tag] = {
                "n": len(group),
                "death_rate": (sum(1 for p in group if p["dead"]) / len(group) if group else None),
                "median_peak_to_last_dd": _dist([p["peak_to_last_dd"] for p in group]).get(
                    "median"
                ),
                "survival": (
                    sum(1 for p in group if not p["dead"]) / len(group) if group else None
                ),
            }
        block["source_split"] = split
        analysis[f"h{h}"] = block

    OUT.write_text(json.dumps(analysis, indent=1) + "\n")
    print(json.dumps(analysis, indent=1))
    print(f"analysis: {OUT}")


if __name__ == "__main__":
    main()
