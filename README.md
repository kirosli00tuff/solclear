# solclear

Clears Solana liquidity pools as **not-a-hard-rug** from their first 30 minutes
of launch-window state. That is the whole product, and the boundary is measured.

## What this answers, and what it does not

This library answers one question: given a Solana liquidity pool at launch,
will it avoid a hard rug, meaning near-total liquidity removal. Measured at
**0.984 precision and 0.538 recall on a 2024 time-split holdout** (train
≤ 2023, test Jan–Nov 2024, n=194, SolRPDS-labelled pools) using pre-event
launch-window state.

It does not answer whether a pool is safe. C.23 measured the boundary between
honest launches and soft or slow rugs as absent from launch-window state at
0.574 against a 0.500 base rate. A cleared pool can still dev-dump or bleed
out over months. Used in the opposite direction, as a hard-rug alarm, the same
model scores 0.464 precision, so it is wrong more often than right that way.

The base rate makes this worse rather than better. Roughly 98.7 percent of
pump.fun tokens show scam-adjacent characteristics, so predicting rug on
everything scores 98.7 percent accuracy and is useless. This scorer is a
filter for a small honest minority, judged on minority-class precision, never
accuracy.

The API encodes that scope rather than only stating it: the entry point is
`clearance()`, it returns a `Clearance` carrying its calibration statement
(never a bare number), and no probability of danger is exposed. The honesty
tests (`tests/test_honesty.py`) assert this scope exists here and in
CLAUDE.md, that the API exposes nothing named like rug detection, and that the
persisted model still reproduces 0.984 / 0.538 on the committed holdout — so
scope erosion or model degradation breaks the build.

## Usage

```python
from solclear import clearance

verdict = clearance(pool_mint, features)  # features from your retrieval pipeline
verdict.cleared  # bool, at the registered operating point
verdict.clearance_score  # clearance evidence only — NOT a safety score
verdict.calibration  # the scope statement, attached to every verdict
```

`features` is the launch-window feature dict produced by
`solclear.features.features()` over a Method B fetch (below) plus GoPlus
token-security flags. See `solclear/scorer.py` for the exact feature names.

## The retrieval library (Method B)

`solclear.method_b` retrieves a pool's launch-window signature history at
**~33 weighted credits per pool regardless of pool depth**: binary-search
`getBlockTime` to resolve the window end to a slot, seed a signature from that
block, page `getSignaturesForAddress(before=seed)` backward to the window
start.

Why this matters is correctness, not performance: the naive from-now walk
costs unbounded credits and silently fails on deep pools — C.25 measured it
**excluding 57% of the honest class**, because thriving pools are deep and get
truncated, which biases any sample toward faded pools. Method B was verified
against the from-now walk at Jaccard 1.0 on every pool where both reached.

Every request is priced through the credit gate (`solclear.gate`) before it is
sent: append-only ledger, restart-proof cumulative total, and a refusal that
names the arithmetic and writes nothing.

## Install & develop

```
make install    # uv sync + pre-commit hooks
make lint       # ruff format --check + ruff check
make typecheck  # mypy --strict
make test       # pytest, including the honesty tests
make train      # regenerate the model from the immutable snapshot
```

Copy `.env.example` to `.env` for the (optional) Helius key. Scoring from
already-computed features needs no key at all.

## Provenance

Everything here was measured in MLCryptoEngine stages C.19–C.26 (2026-08-06 →
2026-08-07). The committed holdout matrix (`data/snapshots/features_c23.csv`,
sha256-pinned) derives from immutable SolRPDS snapshots plus Helius
launch-window fetches; the model artifact is regenerable from it via
`make train`. The measured negatives — which are the most useful part —
travel in [FINDINGS.md](FINDINGS.md).
