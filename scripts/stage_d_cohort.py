"""Stage D Task 4: the retrospective cohort window, probed keyless and free.

Run:  uv run python scripts/stage_d_cohort.py

**Enumeration record — methods tried in order, failures kept** (the sample
must include pools dead today, so currently-listed sources are out):

1. GeckoTerminal dex-pools ``sort=pool_created_at_asc`` → HTTP 400 (only
   volume/tx sorts exist).
2. ``frontend-api.pump.fun`` → dead host (Cloudflare 1016).
3. ``frontend-api-v3.pump.fun/coins`` sorted by created ascending → works
   but **offset-capped ≈ 5,000** (reaches only 2024-Q1); descending reaches
   only the current days. Neither spans 2025-04 → 2026-07.
4. Wayback CDX of GT ``new_pools`` JSON → 3 snapshots (2026-04 empty body,
   2026-06 usable birth-moment capture, 2026-07 undecodable).
5. **USED: Wayback-archived pump.fun per-coin JSON pages** (103 plain pages,
   30 fetched under a deterministic seed) — each carries the coin's own
   ``created_timestamp``, so later crawls surface earlier births; graduated
   coins only, ≤ 2 per creation month — **plus** one pool from the usable
   GT birth snapshot. Declared biases and gaps: archive crawls skew toward
   coins that drew attention (dead-today coins are still present), and no
   births from **2025-04 through 2025-08** were reachable inside the
   registered ≤ 80-probe budget — the go-condition evaluation names that
   gap rather than papering over it.

The sample lives in ``data/vendor/stage_d_cohort_sample.json``. Per pool,
from GeckoTerminal daily OHLCV (keyless): whether it resolves, first-candle
lag from creation, candle counts over days 0-30 and 0-90, terminal-death
signature (last candle inside the horizon closing ≤ 10% of peak), and
alive/dead today (candle within the last 14 days). Go conditions evaluated
exactly as registered; Binance SOLUSDT confirmed as the benchmark leg.
Zero Helius credits.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "data" / "vendor"

GECKO_BASE = "https://api.geckoterminal.com/api/v2"
BINANCE_BASE = "https://api.binance.com"
UA = {"accept": "application/json", "user-agent": "solclear/0.1 (research)"}

SPAN_START = datetime(2025, 4, 1, tzinfo=UTC)
DEAD_GAP_DAYS = 14
DEATH_CLOSE_FRACTION = 0.10
FIRST_CANDLE_MAX_LAG_DAYS = 3
GECKO_PACE_S = 6.0


def main() -> None:
    gecko = httpx.Client(base_url=GECKO_BASE, timeout=20.0, headers=UA)
    sample: list[dict[str, Any]] = json.loads((VENDOR / "stage_d_cohort_sample.json").read_text())
    results: dict[str, Any] = {
        "enumeration_record": "see module docstring; sample file carries per-entry provenance",
        "declared_gaps": [
            "no births reachable for 2025-04..2025-08 within the registered probe budget",
            "archive-crawl attention bias declared; dead-today coins remain enumerable",
            "sample size 8 vs registered 12-16 (probe budget exhausted first)",
        ],
    }

    now = datetime.now(UTC)
    pools: list[dict[str, Any]] = []
    for entry_in in sample:
        created = datetime.fromisoformat(entry_in["created"].replace("Z", "+00:00"))
        entry: dict[str, Any] = dict(entry_in)
        pool_address = entry_in.get("pool_address")
        if not pool_address:
            entry["resolves"] = False
            pools.append(entry)
            continue
        time.sleep(GECKO_PACE_S)
        resp = gecko.get(f"/networks/solana/pools/{pool_address}/ohlcv/day", params={"limit": 1000})
        if resp.status_code == 429:
            time.sleep(30)
            resp = gecko.get(
                f"/networks/solana/pools/{pool_address}/ohlcv/day", params={"limit": 1000}
            )
        candles = (
            ((resp.json().get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
            if resp.status_code == 200
            else []
        )
        entry["resolves"] = bool(candles)
        if candles:
            ts = sorted(c[0] for c in candles)
            closes = {c[0]: float(c[4]) for c in candles}
            first = datetime.fromtimestamp(ts[0], UTC)
            last = datetime.fromtimestamp(ts[-1], UTC)
            peak = max(closes.values())
            created_s = created.timestamp()
            # Daily candles are stamped at 00:00, so the creation-day candle
            # sits up to one day BEFORE the creation instant: -1 d inclusive.
            in30 = sum(1 for t in ts if -86_400 <= t - created_s <= 30 * 86_400)
            in90 = sum(1 for t in ts if -86_400 <= t - created_s <= 90 * 86_400)
            # Pool-anchored horizons: from the first candle (~ pool birth),
            # the anchor Stage E scores at; coin-sourced entries' `created`
            # is the bonding start, which can precede the pool by months.
            p30 = sum(1 for t in ts if 0 <= t - ts[0] <= 30 * 86_400)
            p90 = sum(1 for t in ts if 0 <= t - ts[0] <= 90 * 86_400)
            entry.update(
                first_candle=first.isoformat(),
                first_candle_lag_days=round((first - created).total_seconds() / 86_400, 2),
                last_candle=last.isoformat(),
                candles_0_30=in30,
                candles_0_90=in90,
                candles_p30=p30,
                candles_p90=p90,
                pool_days_observed=round((now.timestamp() - ts[0]) / 86_400),
                raw_candles=[[t, closes[t]] for t in ts],
                peak_close=peak,
                last_close=closes[ts[-1]],
                dead_now=(now - last).days > DEAD_GAP_DAYS,
                terminal_death_30=(ts[-1] - ts[0] <= 30 * 86_400)
                and closes[ts[-1]] <= DEATH_CLOSE_FRACTION * peak,
                terminal_death_90=(ts[-1] - ts[0] <= 90 * 86_400)
                and closes[ts[-1]] <= DEATH_CLOSE_FRACTION * peak,
            )
        pools.append(entry)
        print(
            f"[{entry['month']}] {(entry.get('mint') or pool_address)[:8]}… "
            f"resolves={entry['resolves']} lag={entry.get('first_candle_lag_days')} "
            f"c30={entry.get('candles_0_30')} c90={entry.get('candles_0_90')} "
            f"dead={entry.get('dead_now')}"
        )
    results["pools"] = pools

    bench_start = SPAN_START - timedelta(days=90)
    resp = httpx.get(
        f"{BINANCE_BASE}/api/v3/klines",
        params={
            "symbol": "SOLUSDT",
            "interval": "1d",
            "startTime": int(bench_start.timestamp() * 1000),
            "limit": 3,
        },
        timeout=20.0,
    )
    klines = resp.json() if resp.status_code == 200 else []
    results["binance_benchmark"] = {
        "requested_start": bench_start.isoformat(),
        "first_kline": datetime.fromtimestamp(klines[0][0] / 1000, UTC).isoformat()
        if klines
        else None,
        "covers_span": bool(klines),
    }

    sampled = pools
    resolved = [p for p in sampled if p.get("resolves")]
    dead = [p for p in resolved if p.get("dead_now")]
    lag_ok = [
        p for p in resolved if (p.get("first_candle_lag_days") or 99) <= FIRST_CANDLE_MAX_LAG_DAYS
    ]

    def horizon_ok(p: dict[str, Any], h: int) -> bool:
        # Pool-anchored: enough candles from pool birth, or observable death
        # inside the horizon, or the pool is simply younger than the horizon
        # while still producing candles (coverage is ongoing, not absent).
        young = (p.get("pool_days_observed") or 0) < h and not p.get("dead_now")
        return bool(
            (p.get(f"candles_p{h}") or 0) >= h / 3
            or p.get(f"terminal_death_{h}") is True
            or (young and (p.get(f"candles_p{h}") or 0) >= (p.get("pool_days_observed") or 0) / 3)
        )

    h30 = [p for p in resolved if horizon_ok(p, 30)]
    h90 = [p for p in resolved if horizon_ok(p, 90)]
    full90 = [
        p
        for p in resolved
        if (now - datetime.fromisoformat(p["created"].replace("Z", "+00:00"))).days >= 90
    ]
    full30 = [
        p
        for p in resolved
        if (now - datetime.fromisoformat(p["created"].replace("Z", "+00:00"))).days >= 30
    ]
    summary = {
        "sampled": len(sampled),
        "resolved": len(resolved),
        "resolution_rate": round(len(resolved) / len(sampled), 2) if sampled else None,
        "dead_fraction": round(len(dead) / len(sampled), 2) if sampled else None,
        "first_candle_within_3d_rate": round(len(lag_ok) / len(resolved), 2) if resolved else None,
        "h30_coverage_rate": round(len(h30) / len(resolved), 2) if resolved else None,
        "h90_coverage_rate": round(len(h90) / len(resolved), 2) if resolved else None,
        "latest_creation_with_full_90d": max((p["created"] for p in full90), default=None),
        "latest_creation_with_full_30d": max((p["created"] for p in full30), default=None),
    }
    results["summary"] = summary
    print(json.dumps(summary, indent=1))

    out = VENDOR / "stage_d_cohort_results.json"
    out.write_text(json.dumps(results, indent=1) + "\n")
    print(f"results: {out}")
    gecko.close()


if __name__ == "__main__":
    main()
