# solclear

A clearance scorer for Solana liquidity pools at launch, shipped as a closed
project with its negative results in front of its capability. If you read only
one section, read the next one.

---

## What this answers, and what it does not

**It answers one question.** Given a Solana liquidity pool at launch, will it
avoid a hard rug — meaning near-total (≥ 99%) liquidity removal. Measured at
**0.984 precision and 0.538 recall** on a 2024 time-split holdout (train
≤ 2023, test Jan–Nov 2024, **n = 194** SolRPDS-labelled pools) using pre-event
launch-window state only.

**It does not answer whether a pool is safe.** The boundary between honest
launches and soft or slow rugs was measured **absent** from launch-window
state: 0.574 precision against a 0.500 base rate on the same fold (n = 194),
+0.07 above chance, with a flat PR curve — the base-rate signature. A cleared
pool can still dev-dump or bleed out over months.

**It is not a rug alarm.** Read in the opposite direction — a high P(hard rug)
flagging a pool — the same separator scores **0.464 precision** (n = 194). It
is wrong more often than right that way, so the API does not expose that
direction and the tests forbid a name that suggests it.

**The base rate makes this worse, not better.** Roughly **98.7 percent** of
pump.fun tokens show scam-adjacent characteristics. Predicting "rug" on
everything therefore scores 98.7 percent accuracy and is useless. This scorer
is a filter for a small honest minority and is judged on minority-class
precision, never accuracy.

---

## Two results you need before you read the capability description

These are not caveats buried in an appendix. They decide whether this tool is
useful to you at all.

### 1. Live scores are anchor-shifted — the 0.984 does not travel to the chain

The model was trained on windows anchored at **SolRPDS's first-recorded pool
activity** with a 60-second pre-roll. A live or retrospective scanner can only
anchor at **pool creation**, the one instant observable first-party. Those are
not the same instant: SolRPDS's timestamp lags true pool creation by **18
minutes to 13.3 days, median ≈ 1.5 hours** (measured per mint on n = 10 2024
mints), so the two anchors select different event sets on every pool compared
(parent-anchor windows held 1–1,123 signatures against 1,466–9,808 for
pool-anchor windows on the same six mints).

Therefore, per **ADR-011**: the scanner anchors at pool creation, and **holdout
calibration is not represented as transferring** to pool-creation windows. A
caller running this against the live chain **does not inherit the 0.984
figure**. Live output is labelled *anchor-shifted*.

**Stage G closed this question rather than leaving it open: the anchors are
measured DISTINCT, at full registered coverage.** Stage D could afford only 2
of the 6 registered both-anchor pairs and withheld the ruling rather than bend
the bar; Stage G bought the remaining four (22,100 enhanced credits, re-priced
before sending and matching Stage D's prices exactly) and applied the same
unaltered rule to all six. Only **43 of 60** feature comparisons landed inside
the tolerance bands against a registered ≥ 90% requirement, so the rule returns
DISTINCT — and it is the *same three window-derived fields* out of band every
time (`top5_concentration_wend` 6/6, `n_early_holders` 6/6,
`creator_allocation_t0` 5/6), with a **different derived creator under each
anchor on all 6 of 6 pools**. The anchor-shifted label therefore stays, and it
is now a measured fact rather than a precaution. See [DECISIONS.md](DECISIONS.md)
ADR-010, ADR-011 and ADR-016.

### 2. On a birth-ordered launch cohort, every cleared pool went to zero

Stage E asked the question the project existed to reach — does a cleared basket
beat holding SOL — on a 77-pool retrospective cohort (creations 2025-09 →
2026-07, all bars pre-registered before enumeration). The answer was **no**:

- **Every one of the 18 cleared pools realized −100% net at both 30 and 90
  days** (n = 18 at 30 d, n = 4 at 90 d; share ever above entry: 0%). Against
  SOL over the same windows (−0.2% at 30 d, +0.8% at 90 d) and against cash
  (+0.33% / +0.99%), the cleared basket lost the whole stake.
- **Clearance carried no selection value** on this population, and the cleared
  basket was **worse than the not-cleared basket** on it (not-cleared 30-day net
  mean +84.1%, n = 35 — though that mean is carried by a handful of survivors
  over a −100% *median*; see [FINDINGS.md](FINDINGS.md) §1 for the
  distribution, which is the honest object here).
- Every comparison sat at p_raw = 1.0 in the adverse direction, and the
  pre-registered underpowered rule fired (18 cleared < 20), so **no
  significance is claimed in either direction** — the direction is not in
  doubt, the inference is.

**The mechanism is the population, not the model.** Hard-rug clearance does not
contain the does-it-even-graduate question. A birth-ordered pool feed is
dominated by pre-graduation bonding curves with no liquidity to remove — 97.5%
of the birth-ordered subset was dead within 30 days regardless of any score
(n = 40), and 0 of 35 audited launch-venue positions ever graduated. Pointing
this scorer at raw births is a category error.

And the counterfactual matters more than the result: the same cohort's
attention-crawled sub-sample died at only **18.75%** within 30 days (n = 16) —
a 60-point gap produced by nothing but which pages a crawler archived. Build
this cohort from crawled or listed coins and selection bias alone would have
manufactured a decent-looking basket. That is the most transferable finding
here, and it is [FINDINGS.md](FINDINGS.md) §2.

---

## What is actually in the box

| Piece | What it is | Status |
|---|---|---|
| `solclear.scorer` | The clearance API: `clearance()` → `Clearance \| Unscorable` | Measured, shipped |
| `solclear.method_b` | Depth-independent launch-window retrieval | Measured, shipped, reusable standalone |
| `solclear.gate` | Credit gate: price before send, append-only ledger | Shipped |
| `solclear.pipeline` | The live path's refusal contract | Shipped, anchor-shifted output |
| Post-launch behavioural signal | lift +0.032, 95% CI [−0.045, +0.109] | **Not shipped** — CI includes zero |

The behavioural signal stays not shipped, and now has a measured reason it will
stay that way. The one test that would confirm it — decontaminated labels on the
depth-unbiased sample — was re-priced in Stage G at **4,695,489 weighted
credits** (measured on 43 of 328 pools; 95% interval [1,908,852, 8,138,152])
against a registered affordability threshold of 745,915: **NO-GO**. That is
37.6× the 124,764 the parent project recorded, because its ledger priced
enhanced calls 10× low *and* its cost model stratified on the wrong address's
activity. See [FINDINGS.md](FINDINGS.md) §8.

The API encodes the scope rather than only stating it. The entry point is named
for *clearance*; it returns a `Clearance` carrying its calibration statement
(never a bare number); no probability that reads as danger is exposed anywhere
public; and a pool that cannot be honestly scored returns an `Unscorable` with
**no** score field at all, so mistaking a refusal for weak clearance is a type
error rather than a misreading (ADR-006).

## Usage

```python
from solclear import clearance

verdict = clearance(pool_mint, features)  # features from your retrieval pipeline

if hasattr(verdict, "cleared"):  # Clearance
    verdict.cleared  # bool, at the registered operating point
    verdict.clearance_score  # clearance evidence only — NOT a safety score
    verdict.calibration  # the scope statement, attached to every verdict
else:  # Unscorable — carries no number at all
    verdict.reason  # missing_features | retrieval_incomplete | parse_incomplete
    verdict.missing  # the field names that were absent
```

`features` is the ten-key launch-window mapping produced by
`solclear.features.features()` over a Method B fetch, plus four GoPlus
token-security flags. Exact names and order: `solclear/scorer.py`. Scoring from
already-computed features needs **no API key**.

For the gated live path (retrieval → parse → features → verdict, with refusals
where honesty requires them) use `solclear.pipeline.score_pool` — and read
result 1 above before believing its numbers.

## The retrieval library (Method B) — the most reusable piece here

Retrieving a pool's launch window at **~33–38 weighted credits regardless of
pool depth**: binary-search `getBlockTime` to resolve the window end to a slot,
seed a signature from that block, then page `getSignaturesForAddress` backward
to the window start.

Why it matters is **correctness, not performance**: the naive from-now walk
excluded **57% of the honest class** (n = 14 probed pools, 8 too deep for a
40-page cap), because thriving pools are deep and get truncated — which biases
any sample toward faded pools that look rug-like. Verified against the naive
walk at **Jaccard 1.0** on every pool where both reached.

Full write-up, including how to reuse it outside this package:
**[METHOD_B.md](METHOD_B.md)**.

## What running this costs

Stated plainly so you know before you run it, not after:

- **Retrieval (Method B): ~33–38 weighted credits per pool**, depth-independent.
- **Enhanced transactions (needed for the features): 100 credits per call, 100
  signatures per call** — so `100 × ceil(window_signatures / 100)`. Measured
  over seven launch windows spanning 83–9,808 signatures: **typical ≈ 1,400,
  conservative ≈ 2,000, extreme observed 9,900** per pool.
- **All-in: ≈ 1,450 credits per pool** (retrieval + enhanced, typical). Stage
  E's 77-pool cohort actually averaged ~1,031/pool because sparse windows
  dominated it; budget for the higher figure.
- **Against Helius's free tier (1M credits/month): roughly 690 pools/month** at
  1,450 each. **Continuous scanning does not fit any free tier** — the full
  new-pool feed runs ~9,000 pools/day. Scope is the only honest cost lever:
  ADR-006 makes truncation refuse, so you cannot economise by reading part of a
  window.

Every metered request is priced **before** it is sent, against an append-only
on-disk ledger that survives restarts; a refusal names the arithmetic and
writes nothing (ADR-003). The cap is self-imposed and is raised only by a
deliberate operator edit, never mid-sweep.

## Install & develop

```bash
git clone https://github.com/kirosli00tuff/solclear && cd solclear
make install     # uv sync --group dev + pre-commit hooks
make test        # pytest, including the load-bearing honesty tests
make lint        # ruff format --check + ruff check
make typecheck   # mypy --strict
make train       # regenerate the model from the sha256-pinned snapshot
```

Python 3.12+ and [uv](https://docs.astral.sh/uv/). Copy `.env.example` to
`.env` if you want the live path; the only credential this project uses is a
**read-only** Helius indexer key, which cannot move money or place an order.
`.env` is gitignored, and no key-shaped string exists in any tracked file or
anywhere in this repository's history.

## The honesty tests are load-bearing

`tests/test_honesty.py` is not a formality. It fails the build if:

- any scope sentence or measured figure (0.984, 0.538, 0.464, 0.574, 98.7)
  disappears from README.md or CLAUDE.md;
- **the Stage E negative or the ADR-011 anchor-shift statement disappears from
  README.md or FINDINGS.md** — a future reader, or a future session, cannot
  quietly delete the results that make this tool honest;
- a rug-detection-, alarm-, or safety-shaped name appears anywhere in the
  public API;
- the `Clearance` or `Unscorable` field set changes;
- an unscoreable input produces a number;
- the persisted model stops reproducing 0.984 / 0.538 / 0.464 on the committed
  holdout, or the snapshot stops matching its sha256 manifest.

It also carries its own canary: a test that the presence-checker actually fails
when a required sentence is removed, because a check that cannot fire proves
nothing.

## Status: closed

This project is complete and is not being extended. It established that the
hard-rug clearance boundary is real and measurable on the population it was
trained on, and that clearance does not select things that go up. What would
reopen the outcome question is a **genuinely different population** —
graduated/AMM pools with real liquidity, enumerated without survivorship bias —
not a different model. See the closing entry in [progress.md](progress.md) and
ADR-015 in [DECISIONS.md](DECISIONS.md).

## Read next

- **[FINDINGS.md](FINDINGS.md)** — the measured negatives, every claim with its
  sample size. The most useful thing in this repository for anyone extending
  this work.
- **[METHOD_B.md](METHOD_B.md)** — the reusable retrieval component.
- **[DECISIONS.md](DECISIONS.md)** — append-only ADR log (ADR-001 … ADR-015).
- **[progress.md](progress.md)** — the full stage-by-stage record, including
  every pre-registration written before its results existed.

## Provenance and licence

The holdout figures were measured in MLCryptoEngine stages C.19–C.26
(2026-08-06 → 2026-08-07); the live-path, T0-basis, and outcome measurements
were made here in stages B–E (2026-08-11 → 2026-08-14). The committed holdout
matrix (`data/snapshots/features_c23.csv`, sha256-pinned in `MANIFEST.json`) is
immutable, and the model artifact is regenerable from it via `make train` and
from nothing else.

MIT licensed — see [LICENSE](LICENSE). **Not financial advice.** This is a
research artifact whose headline result is negative; nothing here selects
profitable trades, and the tool's own outcome study says so.
