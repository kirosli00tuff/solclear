"""ADR-005 refusal semantics: registered in Task 0, implemented in Task 1.

These assertions were committed BEFORE the implementation existed (Stage C
Task 0, commit e38b185, as strict-xfail marks), so they could not be shaped
by the code they judge. Task 1 removed the marks in the same change that
made them true. The two fail-closed known-answer tests at the bottom run on
every test pass from now on:

- the documented hard rug ``7CSWFsrB…pump`` must never clear, and
- an empty feature mapping must refuse rather than produce the 0.4815 that
  Stage B measured — the exact defect, frozen as a regression test.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

import solclear
from solclear import scorer as sc
from solclear.method_b import WindowFetch
from solclear.pipeline import ParseReport, score_pool
from solclear.scorer import Unscorable

SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "snapshots" / "features_c23.csv"

# Registered fail-closed exemplar: a documented in-holdout hard rug whose
# snapshot row carries all 10 features as real values (no sentinel), scoring
# 0.4978 against the registered threshold 0.5963 — not cleared.
DOCUMENTED_HARD_RUG = "7CSWFsrB3gPc5o5hxKTJCUbFDq4QyTWpjVG76S1Xpump"

TOKEN_SECURITY_OK: dict[str, float | None] = dict.fromkeys(
    ("freezable", "mintable", "nontransf", "thook"), 0.0
)


def _snapshot_row(mint: str) -> dict[str, float | None]:
    with SNAPSHOT.open() as fh:
        for row in csv.DictReader(fh):
            if row["mint"] == mint:
                return {k: (None if row[k] in ("", "None") else float(row[k])) for k in sc.FEATURES}
    raise AssertionError(f"{mint} not in snapshot")


def _fetch(address: str, *, reached_t0: bool, pages: int = 1) -> WindowFetch:
    return WindowFetch(
        address=address,
        t0_s=1_700_000_000,
        end_s=1_700_001_800,
        signatures=(),
        pages=pages,
        reached_t0=reached_t0,
    )


# ----------------------- registered refusal semantics ----------------------- #


def test_the_refusal_type_exists_and_is_exported() -> None:
    assert "Unscorable" in solclear.__all__
    assert solclear.Unscorable is Unscorable


def test_empty_feature_mapping_refuses_instead_of_scoring() -> None:
    # The exact defect Stage B measured, frozen: clearance(pool, {}) returned
    # cleared=False, clearance_score=0.4815 — a confident-looking number where
    # the truthful answer is "no answer at all".
    verdict = sc.clearance("pool-with-NO-data", {})
    assert isinstance(verdict, Unscorable)
    assert not hasattr(verdict, "clearance_score")
    assert not hasattr(verdict, "cleared")


def test_partial_feature_mapping_refuses_naming_every_missing_field() -> None:
    verdict = sc.clearance("pool-partial", {"top5_concentration_wend": 0.5})
    assert isinstance(verdict, Unscorable)
    assert set(verdict.missing) == set(sc.FEATURES) - {"top5_concentration_wend"}


def test_explicit_none_value_counts_as_absent() -> None:
    features: dict[str, float | None] = dict.fromkeys(sc.FEATURES, 0.0)
    features["n_early_holders"] = None
    verdict = sc.clearance("pool-none-valued", features)
    assert isinstance(verdict, Unscorable)
    assert verdict.missing == ("n_early_holders",)


def test_refusal_carries_reason_and_the_calibration_statement() -> None:
    verdict = sc.clearance("pool-with-NO-data", {})
    assert isinstance(verdict, Unscorable)
    assert verdict.reason == "missing_features"
    assert "0.984" in verdict.calibration


def test_explicit_sentinel_float_passes_through_as_the_trained_encoding() -> None:
    # Registered boundary: -1.0 is the model's trained missing-encoding and
    # collides with legitimate negative TTFS values in real snapshot rows, so
    # it scores; only absent-or-None refuses. The live path never fabricates
    # it — an unavailable live feature is None.
    features: dict[str, float | None] = dict.fromkeys(sc.FEATURES, -1.0)
    verdict = sc.clearance("pool-sentinel-row", features)
    assert isinstance(verdict, sc.Clearance)


def test_incomplete_retrieval_refuses_at_the_pipeline_level() -> None:
    # A fetch stopped by the page bound is a corrupted partial (ADR-002): the
    # pipeline must refuse it before any feature is computed.
    verdict = score_pool(
        fetch=_fetch("pool-truncated", reached_t0=False, pages=40),
        txs=[],
        parse_report=ParseReport(total=0, parsed=0, ignored=0, unparseable=0),
        token_security=TOKEN_SECURITY_OK,
        creator="creator",
    )
    assert isinstance(verdict, Unscorable)
    assert verdict.reason == "retrieval_incomplete"


def test_unparseable_transactions_refuse_at_the_pipeline_level() -> None:
    # A parse that cannot account for every fetched transaction is upstream
    # truncation in new clothes: refusal, never a quiet drop.
    verdict = score_pool(
        fetch=_fetch("pool-unparseable", reached_t0=True),
        txs=[],
        parse_report=ParseReport(total=3, parsed=2, ignored=0, unparseable=1),
        token_security=TOKEN_SECURITY_OK,
        creator="creator",
    )
    assert isinstance(verdict, Unscorable)
    assert verdict.reason == "parse_incomplete"


def test_complete_pipeline_input_with_empty_window_still_refuses_on_features() -> None:
    # An empty-but-complete window parses to no events, so required features
    # (e.g. creator_allocation_t0) come out None: the SCORER refuses — the
    # sentinel-only row can never reach the booster.
    verdict = score_pool(
        fetch=_fetch("pool-empty-window", reached_t0=True),
        txs=[],
        parse_report=ParseReport(total=0, parsed=0, ignored=0, unparseable=0),
        token_security=TOKEN_SECURITY_OK,
        creator="creator",
    )
    assert isinstance(verdict, Unscorable)
    assert verdict.reason == "missing_features"
    assert "creator_allocation_t0" in verdict.missing


# ---------------------- fail-closed known-answer tests ---------------------- #


def test_documented_hard_rug_from_the_holdout_does_not_clear() -> None:
    # 2024 holdout hard rug with every feature real: the persisted model must
    # keep refusing to clear it on every test pass from now on.
    features = _snapshot_row(DOCUMENTED_HARD_RUG)
    assert all(v is not None for v in features.values())

    verdict = sc.clearance(DOCUMENTED_HARD_RUG, features)

    assert isinstance(verdict, sc.Clearance)
    assert verdict.cleared is False
    assert verdict.clearance_score < 0.55  # well under the 0.5963 threshold


def test_credit_gate_refusal_is_a_different_fact_and_stays_unchanged(tmp_path: Path) -> None:
    # CreditCapError before any request is sent is not a scoring refusal and
    # must not be conflated with one (registered distinction, Stage C Task 0).
    from solclear.config import Settings
    from solclear.gate import CreditCapError, CreditGate

    gate = CreditGate(Settings(helius_credit_cap=1, data_root=tmp_path), tmp_path / "l.jsonl")
    with pytest.raises(CreditCapError):
        gate.charge("rpc", 2, "over cap")
    assert gate.spent() == 0
