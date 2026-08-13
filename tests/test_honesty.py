"""Honesty tests: the scope cannot erode without breaking the build.

Four guarantees, each pinned independently:

1. The scope statement — including every measured figure — exists in CLAUDE.md
   AND README.md.
2. The public API exposes no name that reads as rug detection, alarm, or
   safety judgment, and the Clearance verdict's field set is pinned exactly.
3. The documented precision/recall match what the persisted model actually
   produces on the committed holdout — a degraded or swapped model fails here.
4. The snapshot the holdout rests on is byte-identical to its manifest.
"""

from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np

import solclear
from solclear import metrics, pipeline, train
from solclear import scorer as sc

ROOT = Path(__file__).resolve().parent.parent

# Sentences from the scope statement that must survive verbatim, plus every
# measured figure. If any disappears from either document, the scope eroded.
SCOPE_SENTENCES = (
    "will it avoid a hard rug",
    "It does not answer whether a pool is safe",
    "judged on minority-class precision, never accuracy",
)
SCOPE_FIGURES = ("0.984", "0.538", "0.464", "0.574", "98.7")

# Substrings that would read as rug detection / alarm / safety judgment. The
# scan covers every public name in the API modules; adding such a name anywhere
# public breaks the build by design (ADR-001).
FORBIDDEN_NAME_PARTS = (
    "detect",
    "alarm",
    "danger",
    "risk",
    "prob",  # no probability-shaped export in either direction
    "is_rug",
    "rug_score",
    "p_rug",
    "is_safe",
    "safety",
)


def _text(name: str) -> str:
    """Document text with Markdown hard-wrapping and blockquote markers folded.

    The scope sentences must survive verbatim, but a line wrap inside a
    blockquote is formatting, not erosion — so `> ` prefixes are stripped and
    whitespace collapsed before matching.
    """
    raw = (ROOT / name).read_text()
    unquoted = "\n".join(line.removeprefix("> ") for line in raw.splitlines())
    return " ".join(unquoted.split())


def test_scope_statement_exists_in_claude_md_and_readme() -> None:
    for doc in ("CLAUDE.md", "README.md"):
        text = _text(doc)
        for sentence in SCOPE_SENTENCES:
            assert sentence in text, f"{doc} lost the scope sentence: {sentence!r}"
        for figure in SCOPE_FIGURES:
            assert figure in text, f"{doc} lost the measured figure {figure}"


def test_api_exposes_no_rug_detection_shaped_name() -> None:
    modules = (solclear, sc, metrics, pipeline)
    for module in modules:
        public = [n for n in vars(module) if not n.startswith("_")]
        for name in public:
            lowered = name.lower()
            for part in FORBIDDEN_NAME_PARTS:
                assert part not in lowered, (
                    f"{module.__name__}.{name} reads as rug detection/alarm/safety "
                    f"(forbidden substring {part!r}); the API is clearance only (ADR-001)"
                )


def test_clearance_field_set_is_pinned_exactly() -> None:
    # Adding a probability-of-rug field (or any field) to the verdict is an API
    # change that must be made consciously, against this test and ADR-001.
    fields = set(sc.Clearance.__dataclass_fields__)
    assert fields == {"pool", "cleared", "clearance_score", "calibration"}


def test_unscorable_field_set_is_pinned_and_carries_no_score() -> None:
    # ADR-006 (the operator decision ADR-005 deferred): a pool that cannot be
    # honestly scored returns a refusal that is structurally incapable of
    # being read as a low clearance — no score field, no cleared field. This
    # pin is as deliberate as Clearance's own.
    fields = set(sc.Unscorable.__dataclass_fields__)
    assert fields == {"pool", "reason", "missing", "calibration"}
    assert "clearance_score" not in fields
    assert "cleared" not in fields


def test_an_unscoreable_input_returning_a_number_breaks_the_build() -> None:
    # The Stage B defect, held down at the honesty level: an empty feature
    # mapping must never again produce a confident-looking 0.4815.
    verdict = sc.clearance("no-data-anywhere", {})
    assert isinstance(verdict, sc.Unscorable)


def test_calibration_statement_carries_scope_and_misuse_figures() -> None:
    statement = metrics.calibration_statement()
    assert "0.984" in statement and "0.538" in statement
    assert "0.464" in statement  # the misuse direction stays self-refuting
    assert "NOT" in statement


def test_snapshot_is_byte_identical_to_its_manifest() -> None:
    # The holdout below is only meaningful over the immutable snapshot.
    train.verify_snapshot()


def test_documented_figures_match_what_the_persisted_model_produces() -> None:
    """The load-bearing honesty test.

    Recompute the holdout operating points from the committed model and the
    committed matrix; they must round to the documented figures exactly. A
    future change that degrades the model — retraining on different data, a
    library upgrade that shifts the split, a swapped artifact — fails here
    rather than quietly shipping under the old numbers.
    """
    x, y, yr = train.load_matrix()
    te = yr == "2024"
    booster = lgb.Booster(model_file=str(sc.DEFAULT_MODEL))
    p = np.asarray(booster.predict(x[te]), dtype=np.float64)

    clear = train.pr_at_recall((1 - y[te]).astype(np.int_), 1.0 - p)
    flag = train.pr_at_recall(y[te], p)

    assert round(clear["precision"], 3) == metrics.CLEARANCE_PRECISION
    assert round(clear["recall"], 3) == metrics.CLEARANCE_RECALL
    assert round(flag["precision"], 3) == metrics.MISUSE_FLAG_PRECISION


def test_meta_sidecar_matches_the_documented_operating_point() -> None:
    # The sidecar the scorer loads its threshold and calibration from must
    # agree with metrics.py — one source of truth, no drift.
    meta = json.loads(sc.DEFAULT_META.read_text())
    assert round(float(meta["clearance_point"]["precision"]), 3) == metrics.CLEARANCE_PRECISION
    assert round(float(meta["clearance_point"]["recall"]), 3) == metrics.CLEARANCE_RECALL
    assert round(float(meta["misuse_flag_point"]["precision"]), 3) == metrics.MISUSE_FLAG_PRECISION
    assert meta["calibration"] == metrics.calibration_statement()
