"""Typed configuration: secrets from the environment only, fail-fast when absent.

Ported practice from the parent project (MLCryptoEngine): no credential ever
enters the repo; the accessor raises naming the exact variable so a missing
secret is a clear startup error, never a silent None threaded downstream. The
only key this project uses is a read-only Helius indexer key — it cannot move
money or place an order, and every request through it is metered by the credit
gate (ADR-003).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MissingSecretError(RuntimeError):
    """A required secret is absent from the environment; names the variable."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            f"missing required secret(s): {', '.join(missing)} — "
            "set in .env or the environment; see .env.example"
        )


class Settings(BaseSettings):
    """Environment-backed settings, prefix ``SOLCLEAR_``."""

    model_config = SettingsConfigDict(env_prefix="SOLCLEAR_", env_file=".env", extra="ignore")

    helius_api_key: SecretStr | None = None
    # Self-imposed spend ceiling in request-weighted credits (ADR-003), dated
    # 2026-08-11. This is not a Helius tier limit: raising it is a deliberate
    # operator decision made before a sweep, never mid-sweep.
    helius_credit_cap: int = 30_000
    data_root: Path = Path("data")

    def require_helius_key(self) -> SecretStr:
        """The key, or a refusal naming the variable. Never returns None."""
        if self.helius_api_key is None:
            raise MissingSecretError(["SOLCLEAR_HELIUS_API_KEY"])
        return self.helius_api_key


def load_settings() -> Settings:
    return Settings()
