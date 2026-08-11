# CLAUDE.md — solclear operating manual

Read this file at the start of every coding session. It is the contract for how
work happens in this repository.

## The scope statement (non-negotiable rule 1)

This scope is permanent. It is asserted by `tests/test_honesty.py` — eroding it
breaks the build. Every figure below was measured in the parent project
(MLCryptoEngine, stages C.19–C.26) and travels with this repo in FINDINGS.md.

> This library answers one question: given a Solana liquidity pool at launch,
> will it avoid a hard rug, meaning near-total liquidity removal. Measured at
> 0.984 precision and 0.538 recall on a 2024 time-split holdout using
> pre-event launch-window state.
>
> It does not answer whether a pool is safe. C.23 measured the boundary
> between honest launches and soft or slow rugs as absent from launch-window
> state at 0.574 against a 0.500 base rate. A cleared pool can still dev-dump
> or bleed out over months. Used in the opposite direction, as a hard-rug
> alarm, the same model scores 0.464 precision, so it is wrong more often than
> right that way.
>
> The base rate makes this worse rather than better. Roughly 98.7 percent of
> pump.fun tokens show scam-adjacent characteristics, so predicting rug on
> everything scores 98.7 percent accuracy and is useless. This scorer is a
> filter for a small honest minority, judged on minority-class precision,
> never accuracy.

The scope is encoded in the API, not only in prose: the entry point is named
for **clearance**, returns a `Clearance` with a calibration statement
attached (never a bare number), and exposes no probability that reads
naturally as danger. The misuse direction — a rug alarm — is deliberately
awkward to reach, and the honesty tests pin the API surface so a
detection-shaped name cannot appear without breaking the build.

## Non-negotiable rules

1. **The scope statement above.** No function, doc, or release may promise
   safety judgment, soft/slow-rug detection, or a rug alarm.
2. **Secrets never enter the repo.** No API keys, tokens, or passwords in
   source, config, fixtures, or history. Secrets come only from environment
   variables (see `.env.example`); the config layer raises naming the missing
   variable. The only key this project uses is a read-only Helius indexer key
   — it cannot move money or place an order.
3. **Every metered request goes through the credit gate** (ADR-003): priced
   before sending, append-only ledger, restart-proof cumulative total, refusal
   writes nothing. The cap is self-imposed; raising it is a deliberate
   operator decision made before a sweep, never mid-sweep.
4. **The snapshot matrix is immutable** (`data/snapshots/`, sha256-pinned in
   `MANIFEST.json`). The model artifact is regenerable from it via
   `make train` and from nothing else.

## Standing practices (ported from the parent project, defect-earned)

- **Pre-register bars before computing results.** Decide the threshold, the
  split, and the end condition before the data is seen; a result read against
  a bar chosen afterward is not a result.
- **Known-answer tests before trusting a pipeline.** A new retrieval or
  scoring path must reproduce a previously measured answer before its output
  is believed (Method B shipped only after matching the from-now walk at
  Jaccard 1.0).
- **Leakage suites are wired before the first feature.** The window guard,
  prefix invariance, and the planted-future canary in `tests/test_leakage.py`
  predate any real feature computation and must stay green. A canary that
  cannot fire proves nothing — the suite includes a test that the detector
  catches a deliberately leaky feature.
- **Union time intervals before summing.** Never add durations from a list of
  windows that might overlap; three separate parent-project defects came from
  exactly that shape (a list, a `sum()`, no union — it never raises, it just
  returns a number that is too large). Any new interval arithmetic here must
  merge first and carry a test with at least one overlapping pair.
- **Never trust append order across processes.** Two processes appending to
  one file interleave; order by the recorded clock, never by file position.
  The gate ledger's `spent()` sums rather than assuming order for this reason.

## Directory map

```
solclear/            The package
  config.py          Env-backed settings; secrets fail fast, naming the variable
  gate.py            Credit gate: price before send, append-only ledger, refusal writes nothing
  method_b.py        Depth-independent launch-window retrieval (slot binary search + before= paging)
  rpc.py             Thin Helius JSON-RPC transport (key never appears in errors or logs)
  labels.py          Four-class label construction (hard_rug / honest_candidate / residual; honeypot on the mint)
  features.py        Launch-window features + decontamination rules; leak-guarded by construction
  scorer.py          The clearance API: Clearance with calibration attached, never a bare number
  train.py           Regenerate the model from the immutable snapshot (verifies sha256 first)
  metrics.py         Single source of truth for the documented figures
  artifacts/         Persisted model + meta sidecar (regenerable via make train)
data/snapshots/      Immutable holdout matrix + sha256 MANIFEST
data/vendor/         Machine-local credit ledger (gitignored, append-only)
tests/               Pytest suite; test_leakage.py and test_honesty.py are load-bearing
```

## Coding standards

- Python 3.12+; type hints on all function signatures; `ruff format`,
  `ruff check`, and `mypy --strict` must pass clean.
- Anything with logic gets a pytest test. Real tests, not smoke tests.
- Errors are handled explicitly; never silently swallow an exception.
- Immutable data patterns: frozen dataclasses, pure functions over records.

## Git commit conventions

Conventional commits: `<type>: <description>` with type in
`feat, fix, refactor, docs, test, chore, perf, ci`. Imperative mood, lower
case, no trailing period. One deliverable or coherent change per commit.

## Read these first

- `README.md` — what the tool answers and what it does not.
- `FINDINGS.md` — the measured negatives; the most useful thing here for
  anyone extending this work.
- `DECISIONS.md` — append-only ADR log; read before revisiting any settled
  question.
- `progress.md` — where the project is right now.
