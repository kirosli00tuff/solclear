"""Credit gate: refuse past the cap, survive restarts, never write on refusal.

These pin the three properties that make the gate trustworthy (ADR-003), plus
the config layer's fail-fast secret accessor. The gate's production record in
the parent project — a correct budget stop at a sweep boundary and a refusal
of an unaffordable purchase — rests on exactly these behaviours.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from solclear.config import MissingSecretError, Settings
from solclear.gate import CREDIT_WEIGHTS, CreditCapError, CreditGate


def _gate(tmp_path: Path, cap: int) -> CreditGate:
    settings = Settings(helius_credit_cap=cap, data_root=tmp_path)
    return CreditGate(settings, ledger_path=tmp_path / "ledger.jsonl")


def test_gate_refuses_when_estimate_exceeds_cap_and_writes_nothing(tmp_path: Path) -> None:
    # Arrange — cap 100; a 20-request enhanced sweep weighs 200.
    gate = _gate(tmp_path, cap=100)

    # Act / Assert — refusal names the arithmetic and leaves no ledger behind.
    with pytest.raises(CreditCapError, match="REFUSED"):
        gate.check_estimate(gate.estimate(20, "enhanced"), "sweep")
    with pytest.raises(CreditCapError):
        gate.charge("enhanced", 20, "sweep")
    assert not (tmp_path / "ledger.jsonl").exists()
    assert gate.spent() == 0


def test_gate_ledger_survives_a_restart(tmp_path: Path) -> None:
    # Arrange — charge through one instance, read through a fresh one.
    first = _gate(tmp_path, cap=1_000)
    first.charge("enhanced", 3, "probe")  # 30 weighted
    first.charge("rpc", 5, "health")  # 5 weighted

    # Act — a new process constructs a new gate over the same file.
    second = _gate(tmp_path, cap=1_000)

    # Assert
    assert second.spent() == 3 * CREDIT_WEIGHTS["enhanced"] + 5 * CREDIT_WEIGHTS["rpc"]
    assert second.remaining() == 1_000 - 35


def test_many_small_requests_cannot_walk_past_the_cap(tmp_path: Path) -> None:
    """The failure a per-request-only check would miss."""
    gate = _gate(tmp_path, cap=10)
    for _ in range(10):
        gate.charge("rpc", 1, "small")
    assert gate.spent() == 10

    # Each request is individually trivial; cumulatively they are at the cap.
    with pytest.raises(CreditCapError):
        gate.charge("rpc", 1, "one too many")
    assert gate.spent() == 10  # the refused request wrote nothing


def test_charge_at_exactly_the_boundary_is_allowed_then_next_refused(tmp_path: Path) -> None:
    # The cap is inclusive: spending TO the cap is permitted, past it is not.
    gate = _gate(tmp_path, cap=10)
    gate.charge("enhanced", 1, "exactly the cap")  # 10 weighted
    assert gate.remaining() == 0
    with pytest.raises(CreditCapError):
        gate.charge("rpc", 1, "past it")


def test_require_helius_key_raises_naming_the_variable() -> None:
    # Arrange — force the absent state explicitly (explicit kwargs beat env).
    settings = Settings(helius_api_key=None)

    # Act / Assert
    with pytest.raises(MissingSecretError) as err:
        settings.require_helius_key()
    assert err.value.missing == ["SOLCLEAR_HELIUS_API_KEY"]
