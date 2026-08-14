"""Stage E Task 1: enumerate the cohort, birth-ordered first, bias measured.

Run:  uv run python scripts/stage_e_enumerate.py            (keyless, no credits)

Sources, in the registered priority order, every entry tagged:

1. ``gt_birth_capture`` — Wayback captures of GeckoTerminal's ``new_pools``
   JSON: birth-ordered snapshots, not attention-selected. Every distinct
   capture timestamp is counted and reported.
2. ``wayback_coin`` — Wayback-archived pump.fun per-coin JSON pages
   (attention-crawled; the bias the registration requires measuring, not
   declaring). Graduated coins only.
3. ``live_desc`` — the live pump.fun v3 list sorted created-DESC, which is
   birth-ordered but offset-capped to recent weeks; used for the 30 d-horizon
   tail (creations ≤ 2026-07-14).

Every kept entry gets a GeckoTerminal pool lookup for the POOL's own
``pool_created_at`` — the scoring anchor per ADR-011 — because coin-sourced
entries' ``created_timestamp`` is the bonding start, which Stage D measured
lagging the pool by 0-160 days. Output: ``data/vendor/stage_e_cohort.json``.
"""

from __future__ import annotations

import gzip
import json
import random
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "data" / "vendor"

CDX = "http://web.archive.org/cdx/search/cdx"
WAYBACK = "https://web.archive.org/web"
GECKO_BASE = "https://api.geckoterminal.com/api/v2"
PUMP_BASE = "https://frontend-api-v3.pump.fun"
UA = {"accept": "application/json", "user-agent": "solclear/0.1 (research)"}

SPAN_LO = "2025-09-01"
SPAN_HI = "2026-07-14"
LIVE_DESC_TARGET = 120
WAYBACK_PACE_S = 1.2
GECKO_PACE_S = 6.0
PUMP_PACE_S = 1.0


def _wayback_json(client: httpx.Client, ts: str, url: str) -> Any | None:
    time.sleep(WAYBACK_PACE_S)
    for attempt in range(3):
        try:
            resp = client.get(f"{WAYBACK}/{ts}id_/{url}")
            raw = resp.content
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return json.loads(raw)
        except Exception:  # archive flakiness: retried, then skipped
            time.sleep(4.0 * (attempt + 1))
    return None


def gt_birth_captures(client: httpx.Client) -> tuple[list[dict[str, Any]], int]:
    """Pools from every archived new_pools capture; (entries, capture_count)."""
    resp = client.get(
        CDX,
        params={
            "url": "api.geckoterminal.com/api/v2/networks/solana/new_pools*",
            "output": "json",
            "filter": "statuscode:200",
            "limit": 200,
        },
        timeout=60.0,
    )
    rows = resp.json()[1:] if resp.status_code == 200 else []
    captures = [(r[1], r[2]) for r in rows]
    entries: list[dict[str, Any]] = []
    seen_pools: set[str] = set()
    for ts, url in captures:
        body = _wayback_json(client, ts, url)
        if body is None:
            continue
        for p in body.get("data", []):
            a = p["attributes"]
            address = str(a["address"])
            created = str(a["pool_created_at"])
            if address in seen_pools or not (SPAN_LO <= created[:10] <= SPAN_HI):
                continue
            seen_pools.add(address)
            base = (p.get("relationships", {}).get("base_token", {}).get("data") or {}).get("id")
            entries.append(
                {
                    "source": "gt_birth_capture",
                    "capture_ts": ts,
                    "pool_address": address,
                    "pool_created_at": created,
                    "mint": str(base).removeprefix("solana_") if base else None,
                    "dex": p["relationships"]["dex"]["data"]["id"],
                }
            )
    return entries, len(captures)


def wayback_coins(client: httpx.Client) -> list[dict[str, Any]]:
    """Graduated coins from ALL archived per-coin pages (attention-crawled)."""
    resp = client.get(
        CDX,
        params={
            "url": "frontend-api-v3.pump.fun/coins-v2/*",
            "output": "json",
            "filter": "statuscode:200",
            "limit": 600,
        },
        timeout=90.0,
    )
    rows = resp.json()[1:] if resp.status_code == 200 else []
    plain = [r for r in rows if "?" not in r[2] and r[2].rstrip("/").count("/") == 4]
    # Deterministic order; every page fetched (the D probe stopped at 30).
    random.seed(41)
    random.shuffle(plain)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in plain:
        coin = _wayback_json(client, r[1], r[2])
        if not isinstance(coin, dict) or not coin.get("mint") or coin["mint"] in seen:
            continue
        seen.add(coin["mint"])
        if not coin.get("complete") or not coin.get("created_timestamp"):
            continue
        created = datetime.fromtimestamp(coin["created_timestamp"] / 1000, UTC)
        pool = coin.get("pump_swap_pool") or coin.get("pool_address") or coin.get("raydium_pool")
        if not pool:
            continue
        out.append(
            {
                "source": "wayback_coin",
                "capture_ts": r[1],
                "mint": coin["mint"],
                "coin_created_at": created.isoformat(),
                "pool_address": pool,
            }
        )
    return out


def live_desc_tail(client: httpx.Client) -> list[dict[str, Any]]:
    """Graduated coins from the live created-DESC list, creations <= SPAN_HI."""
    out: list[dict[str, Any]] = []
    offset = 0
    while len(out) < LIVE_DESC_TARGET and offset < 4_900:
        time.sleep(PUMP_PACE_S)
        resp = client.get(
            f"{PUMP_BASE}/coins",
            params={
                "offset": offset,
                "limit": 50,
                "sort": "created_timestamp",
                "order": "DESC",
                "complete": "true",
            },
        )
        offset += 50
        if resp.status_code != 200:
            continue
        coins = resp.json()
        if not isinstance(coins, list) or not coins:
            break
        for coin in coins:
            created = datetime.fromtimestamp(coin["created_timestamp"] / 1000, UTC)
            if created.isoformat()[:10] > SPAN_HI:
                continue
            pool = (
                coin.get("pump_swap_pool") or coin.get("pool_address") or coin.get("raydium_pool")
            )
            if not pool or not coin.get("mint"):
                continue
            out.append(
                {
                    "source": "live_desc",
                    "mint": coin["mint"],
                    "coin_created_at": created.isoformat(),
                    "pool_address": pool,
                }
            )
            if len(out) >= LIVE_DESC_TARGET:
                break
    return out


def main() -> None:
    wb = httpx.Client(timeout=45.0, headers=UA, follow_redirects=True)
    gecko = httpx.Client(base_url=GECKO_BASE, timeout=20.0, headers=UA)
    pump = httpx.Client(timeout=20.0, headers=UA)

    birth, capture_count = gt_birth_captures(wb)
    print(f"[1] gt_birth_capture: {capture_count} captures -> {len(birth)} in-span pools")
    coins = wayback_coins(wb)
    print(f"[2] wayback_coin: {len(coins)} graduated coins with pools")
    tail = live_desc_tail(pump)
    print(f"[3] live_desc: {len(tail)} graduated coins (creations <= {SPAN_HI})")

    # Merge, dedupe by pool address, then anchor every entry at the POOL's
    # own creation via GT (ADR-011) and drop out-of-span pools.
    merged: dict[str, dict[str, Any]] = {}
    for entry in [*birth, *coins, *tail]:
        merged.setdefault(entry["pool_address"], entry)
    cohort: list[dict[str, Any]] = []
    for i, (address, entry) in enumerate(sorted(merged.items())):
        if "pool_created_at" not in entry or entry.get("mint") is None:
            time.sleep(GECKO_PACE_S)
            resp = gecko.get(f"/networks/solana/pools/{address}", params={"include": "base_token"})
            if resp.status_code == 429:
                time.sleep(30)
                resp = gecko.get(
                    f"/networks/solana/pools/{address}", params={"include": "base_token"}
                )
            if resp.status_code != 200:
                entry["dropped"] = f"gt pool lookup HTTP {resp.status_code}"
                cohort.append(entry)
                continue
            body = resp.json().get("data") or {}
            attrs = body.get("attributes") or {}
            entry["pool_created_at"] = attrs.get("pool_created_at")
            base = (body.get("relationships", {}).get("base_token", {}).get("data") or {}).get("id")
            entry.setdefault("mint", str(base).removeprefix("solana_") if base else None)
        created = str(entry.get("pool_created_at") or "")
        if not created or not (SPAN_LO <= created[:10] <= SPAN_HI):
            entry["dropped"] = f"pool_created_at {created[:10] or 'unknown'} outside span"
        elif not entry.get("mint"):
            entry["dropped"] = "no mint resolvable"
        cohort.append(entry)
        if i % 25 == 0:
            print(f"  ... anchored {i + 1}/{len(merged)}")

    kept = [e for e in cohort if "dropped" not in e]
    out = {
        "capture_timestamps": capture_count,
        "counts": {
            "gt_birth_capture": sum(1 for e in kept if e["source"] == "gt_birth_capture"),
            "wayback_coin": sum(1 for e in kept if e["source"] == "wayback_coin"),
            "live_desc": sum(1 for e in kept if e["source"] == "live_desc"),
            "dropped": len(cohort) - len(kept),
        },
        "entries": cohort,
    }
    (VENDOR / "stage_e_cohort.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"cohort kept: {len(kept)} | {out['counts']}")
    wb.close()
    gecko.close()
    pump.close()


if __name__ == "__main__":
    main()
