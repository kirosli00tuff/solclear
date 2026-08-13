"""ADR-005 refusal semantics, registered before the implementation exists.

Written and committed in Stage C Task 0, ahead of Task 1's implementation, so
the assertions could not be shaped by the code they judge. Tests of
behaviour that does not exist yet are marked ``xfail(strict=True)``: the
build FAILS if any of them passes early (a strict xfail that passes is an
error), and Task 1's commit removes the marks in the same change that makes
them true. The two fail-closed known-answer tests at the bottom pass today
and run on every test pass from now on.

Access to the not-yet-existing names is dynamic (``importlib``/``getattr``)
so ``mypy --strict`` stays green while the assertions stay executable.
"""

from __future__ import annotations

import csv
import importlib
from pathlib import Path
from typing import Any

import pytest

import solclear
from solclear import scorer as sc

SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "snapshots" / "features_c23.csv"

# Registered fail-closed exemplar: a documented in-holdout hard rug whose
# snapshot row carries all 10 features as real values (no sentinel), scoring
# 0.4978 against the registered threshold 0.5963 — not cleared.
DOCUMENTED_HARD_RUG = "7CSWFsrB3gPc5o5hxKTJCUbFDq4QyTWpjVG76S1Xpump"

xfail_unimplemented = pytest.mark.xfail(
    strict=True,
    reason="registered in Stage C Task 0 before the implementation; ADR-005 lands in Task 1",
)


def _unscorable_type() -> Any:
    return importlib.import_module("solclear.scorer").Unscorable


def _snapshot_row(mint: str) -> dict[str, float | None]:
    with SNAPSHOT.open() as fh:
        for row in csv.DictReader(fh):
            if row["mint"] == mint:
                return {k: (None if row[k] in ("", "None") else float(row[k])) for k in sc.FEATURES}
    raise AssertionError(f"{mint} not in snapshot")


# ------------- registered refusal semantics (xfail until Task 1) ------------ #


@xfail_unimplemented
def test_the_refusal_type_exists_and_is_exported() -> None:
    unscorable = _unscorable_type()
    assert "Unscorable" in solclear.__all__
    assert unscorable is importlib.import_module("solclear").Unscorable


@xfail_unimplemented
def test_empty_feature_mapping_refuses_instead_of_scoring() -> None:
    # The exact defect Stage B measured, frozen: clearance(pool, {}) returned
    # cleared=False, clearance_score=0.4815 — a confident-looking number where
    # the truthful answer is "no answer at all".
    verdict: Any = sc.clearance("pool-with-NO-data", {})
    assert isinstance(verdict, _unscorable_type())
    assert not hasattr(verdict, "clearance_score")
    assert not hasattr(verdict, "cleared")


@xfail_unimplemented
def test_partial_feature_mapping_refuses_naming_every_missing_field() -> None:
    verdict: Any = sc.clearance("pool-partial", {"top5_concentration_wend": 0.5})
    assert isinstance(verdict, _unscorable_type())
    missing = set(verdict.missing)
    assert missing == set(sc.FEATURES) - {"top5_concentration_wend"}


@xfail_unimplemented
def test_explicit_none_value_counts_as_absent() -> None:
    features: dict[str, float | None] = dict.fromkeys(sc.FEATURES, 0.0)
    features["n_early_holders"] = None
    verdict: Any = sc.clearance("pool-none-valued", features)
    assert isinstance(verdict, _unscorable_type())
    assert tuple(verdict.missing) == ("n_early_holders",)


@xfail_unimplemented
def test_refusal_carries_reason_and_the_calibration_statement() -> None:
    verdict: Any = sc.clearance("pool-with-NO-data", {})
    assert verdict.reason == "missing_features"
    assert "0.984" in verdict.calibration


@xfail_unimplemented
def test_incomplete_retrieval_refuses_at_the_pipeline_level() -> None:
    # A fetch stopped by the page bound is a corrupted partial (ADR-002): the
    # pipeline must refuse it before any feature is computed.
    from solclear.method_b import WindowFetch

    pipeline = importlib.import_module("solclear.pipeline")
    fetch = WindowFetch(
        address="pool-truncated",
        t0_s=1_700_000_000,
        end_s=1_700_001_800,
        signatures=(),
        pages=40,
        reached_t0=False,
    )
    verdict = pipeline.score_pool(
        fetch=fetch,
        txs=[],
        parse_report=pipeline.ParseReport(total=0, parsed=0, ignored=0, unparseable=0),
        token_security=dict.fromkeys(("freezable", "mintable", "nontransf", "thook"), 0.0),
        creator="creator",
    )
    assert isinstance(verdict, _unscorable_type())
    assert verdict.reason == "retrieval_incomplete"


@xfail_unimplemented
def test_unparseable_transactions_refuse_at_the_pipeline_level() -> None:
    # A parse that cannot account for every fetched transaction is upstream
    # truncation in new clothes: refusal, never a quiet drop.
    from solclear.method_b import WindowFetch

    pipeline = importlib.import_module("solclear.pipeline")
    fetch = WindowFetch(
        address="pool-unparseable",
        t0_s=1_700_000_000,
        end_s=1_700_001_800,
        signatures=(),
        pages=1,
        reached_t0=True,
    )
    verdict = pipeline.score_pool(
        fetch=fetch,
        txs=[],
        parse_report=pipeline.ParseReport(total=3, parsed=2, ignored=0, unparseable=1),
        token_security=dict.fromkeys(("freezable", "mintable", "nontransf", "thook"), 0.0),
        creator="creator",
    )
    assert isinstance(verdict, _unscorable_type())
    assert verdict.reason == "parse_incomplete"


# ---------------- fail-closed known-answer tests (pass today) --------------- #


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
