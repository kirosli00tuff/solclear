"""Thin Helius JSON-RPC transport implementing the Method B client protocol.

Does no pricing of its own — wrap it in :class:`solclear.method_b.GatedRpc` so
every request is charged before it is sent. Transport errors are re-raised as
:class:`RpcError` carrying the method name only: the request URL embeds the
API key and must never appear in an exception message or a log line.
"""

from __future__ import annotations

from typing import Any

import httpx

from solclear.method_b import SigInfo

DEFAULT_BASE_URL = "https://mainnet.helius-rpc.com"
DEFAULT_TIMEOUT_S = 30.0


class RpcError(RuntimeError):
    """An RPC call failed. The message names the method, never the URL."""


class HeliusRpc:
    """Synchronous JSON-RPC client for the four calls Method B needs."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout_s)
        self._path = f"/?api-key={api_key}"

    def close(self) -> None:
        self._client.close()

    def _call(self, method: str, params: list[Any]) -> Any:
        try:
            resp = self._client.post(
                self._path,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            )
        except httpx.HTTPError as exc:  # redact: httpx messages can embed the URL
            raise RpcError(f"{method}: transport error ({type(exc).__name__})") from None
        if resp.status_code != 200:
            raise RpcError(f"{method}: HTTP {resp.status_code}")
        payload = resp.json()
        if "error" in payload:
            return {"__rpc_error__": payload["error"].get("code")}
        return payload.get("result")

    def latest_slot(self) -> int:
        result = self._call("getSlot", [])
        if not isinstance(result, int):
            raise RpcError("getSlot: non-integer result")
        return result

    def block_time(self, slot: int) -> int | None:
        """Unix seconds, or None when the slot was skipped or not yet available."""
        result = self._call("getBlockTime", [slot])
        if isinstance(result, dict) or result is None:  # RPC error => treat as skipped
            return None
        return int(result)

    def block_signatures(self, slot: int) -> list[str]:
        """Signatures in a block; empty when the slot was skipped."""
        result = self._call(
            "getBlock",
            [
                slot,
                {
                    "transactionDetails": "signatures",
                    "rewards": False,
                    "maxSupportedTransactionVersion": 0,
                },
            ],
        )
        if not isinstance(result, dict) or "__rpc_error__" in result:
            return []
        return [str(s) for s in result.get("signatures", [])]

    def signatures_for_address(self, address: str, before: str | None, limit: int) -> list[SigInfo]:
        opts: dict[str, Any] = {"limit": limit}
        if before is not None:
            opts["before"] = before
        result = self._call("getSignaturesForAddress", [address, opts])
        if not isinstance(result, list):
            raise RpcError("getSignaturesForAddress: non-list result")
        return [
            SigInfo(
                signature=str(item["signature"]),
                slot=int(item["slot"]),
                block_time_s=int(item["blockTime"]) if item.get("blockTime") is not None else None,
                err=item.get("err") is not None,
            )
            for item in result
        ]
