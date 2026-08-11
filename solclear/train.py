"""Regenerate and persist the clearance model from the immutable snapshot.

Reads the committed launch-window feature matrix (``data/snapshots/``,
sha256-pinned by ``MANIFEST.json`` — verified before anything trains), fits a
LightGBM booster to separate hard rugs from other launches on the registered
time split (train <= 2023, test 2024), evaluates BOTH directions on the 2024
fold — clearance, the shipped one, and the misuse flag, documented so it stays
self-refuting — and persists the booster plus a meta sidecar carrying the
operating point and the calibration statement. Run:

    make train

Model class and hyperparameters match the parent's C.23 run exactly — no
search. ``tests/test_honesty.py`` asserts the persisted artifact reproduces
the documented operating point on this same holdout, so a regeneration that
degrades the model breaks the build rather than quietly shipping.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import numpy.typing as npt

from solclear import metrics
from solclear.scorer import DEFAULT_META, DEFAULT_MODEL, FEATURES, MISSING

SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "snapshots" / "features_c23.csv"
MANIFEST = SNAPSHOT.parent / "MANIFEST.json"


class SnapshotIntegrityError(RuntimeError):
    """The snapshot on disk does not match its manifest: nothing trains on it."""


def snapshot_sha256(path: Path = SNAPSHOT) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_snapshot(path: Path = SNAPSHOT, manifest_path: Path = MANIFEST) -> str:
    """The snapshot is immutable; a drifted hash is a hard failure, not a warning."""
    manifest = json.loads(manifest_path.read_text())
    expected = str(manifest[path.name]["sha256"])
    actual = snapshot_sha256(path)
    if actual != expected:
        raise SnapshotIntegrityError(
            f"{path.name}: sha256 {actual} does not match manifest {expected}; "
            "the snapshot is immutable — restore it, never retrain on a mutated copy"
        )
    return actual


def _vec(row: dict[str, str]) -> list[float]:
    out: list[float] = []
    for k in FEATURES:
        v = row.get(k, "")
        out.append(MISSING if v in ("", "None") else float(v))
    return out


def load_matrix(
    path: Path = SNAPSHOT,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.int_], npt.NDArray[np.str_]]:
    """Feature matrix, hard-rug indicator (positive class), and year vector."""
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    x = np.array([_vec(r) for r in rows], dtype=np.float64)
    y = np.array([1 if r["cls"] == "hard_rug" else 0 for r in rows], dtype=np.int_)
    yr = np.array([r["year"] for r in rows])
    return x, y, yr


def pr_at_recall(
    y: npt.NDArray[np.int_], p: npt.NDArray[np.float64], min_recall: float = 0.5
) -> dict[str, float]:
    """Max-precision operating point subject to recall >= ``min_recall``."""
    order = np.argsort(-p)
    ys = y[order]
    tp = np.cumsum(ys)
    fp = np.cumsum(1 - ys)
    prec = tp / (tp + fp)
    rec = tp / max(1, int(ys.sum()))
    ok = rec >= min_recall
    if not ok.any():
        return {"precision": 0.0, "recall": 0.0, "threshold": 1.0}
    i = int(np.argmax(np.where(ok, prec, -1.0)))
    return {"precision": float(prec[i]), "recall": float(rec[i]), "threshold": float(p[order][i])}


def main() -> None:
    import lightgbm as lgb

    sha = verify_snapshot()
    x, y, yr = load_matrix()
    tr = yr != "2024"
    te = ~tr
    model = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, verbose=-1)
    model.fit(x[tr], y[tr])
    p = np.asarray(model.predict_proba(x[te]), dtype=np.float64)[:, 1]
    # Two directions on the same separator. CLEAR (predict honest, score = 1-P)
    # is the shipped one; FLAG is evaluated and persisted only so the misuse
    # direction stays documented as self-refuting.
    clear = pr_at_recall((1 - y[te]).astype(np.int_), 1.0 - p)
    flag = pr_at_recall(y[te], p)
    DEFAULT_MODEL.parent.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(DEFAULT_MODEL))
    meta = {
        "features": list(FEATURES),
        "snapshot": SNAPSHOT.name,
        "snapshot_sha256": sha,
        "train_n": int(tr.sum()),
        "test_n": int(te.sum()),
        "test_hard_rug": int(y[te].sum()),
        "holdout": metrics.HOLDOUT,
        "clearance_point": {k: round(v, 4) for k, v in clear.items()},
        "misuse_flag_point": {k: round(v, 4) for k, v in flag.items()},
        "calibration": metrics.calibration_statement(),
    }
    DEFAULT_META.write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
