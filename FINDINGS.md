# FINDINGS.md — the measured negatives, with sample sizes

These findings travel with this repository because they are its most useful
output for anyone else working on rug detection or memecoin outcome studies.
Each was measured against bars registered **before** the measurement existed —
in MLCryptoEngine (stages C.19–C.26, 2026-08-06 → 2026-08-07, working in that
project's `report.md`) or here (stages B–E, 2026-08-11 → 2026-08-14, working in
[progress.md](progress.md)).

**Every claim below carries its sample size in the same sentence as its
number.** A negative result with a hidden n is not a result, and the expensive
mistake in this domain is re-testing a settled question — or trusting a settled
question that rested on eight pools.

### Sample sizes at a glance

| § | Finding | n |
|---|---|---|
| 1 | A cleared basket did not beat holding SOL; it went to zero | 18 cleared (30 d), 4 (90 d), from a 77-pool cohort |
| 2 | Crawler-selected enumeration manufactures survivorship | 40 birth-ordered vs 16 attention-crawled |
| 3 | The honest-vs-soft/slow-rug boundary is absent at T0+30min | 194 (2024 time-split fold) |
| 4 | The training windows open *after* the launch storm | 10 mints (lag), 6 mints (window populations) |
| 5 | The naive from-now walk excludes 57% of the honest class | 14 probed pools |
| 6 | RugCheck's `rugged` flag returned False on documented rugs | 4 |
| 7 | The post-launch behavioural lift is unconfirmed | 194 → 286 pools across three stages |
| 8 | The confirming measurement is priced out, not untested | 8 pools probed for the cheap route |

> **Section numbering changed in Stage F** (this file was reorganised to lead
> with the outcome study and the crawler-bias result). `DECISIONS.md` is
> append-only and cites the old numbers: old §1 → new §3, old §2 → new §7,
> old §3 → new §8, old §4 → new §6, old §5 → new §5 (unchanged), old §6 →
> new §1 and §2. New §4 is content promoted here from ADR-010 and the Stage D
> record.

---

## 1. A cleared basket did not beat holding SOL — it went to zero (Stage E, 2026-08-14)

This is the question the project existed to reach, and the answer is negative.

**Cohort:** 77 pools, creations 2025-09-01 → 2026-07-14, pool-creation
anchoring per ADR-011, every bar (entry, weighting, exit, death rule, execution
cost, trial count, deflation, underpowered rule) registered in commit `8a49833`
before any enumeration ran. Scoring split the cohort into **18 cleared / 37
not-cleared / 18 skipped at the 6,000-credit per-pool ceiling / 4 refused**
(all four `parse_incomplete`).

**Result: every one of the 18 cleared pools realized −100% net at 30 days, and
all 4 of the cleared pools with a realized 90-day horizon did the same.** Share
ever above entry: **0% of 18**. Median days to peak: 0.

| horizon | cleared | not-cleared | SOL, same windows | cash @4%/yr |
|---|---|---|---|---|
| 30 d net mean | **−100%** (n = 18) | +84.1% (n = 35) | −0.2% | +0.33% |
| 30 d net median | −100% (n = 18) | **−100%** (n = 35) | — | — |
| 30 d total-loss share | 100% (18 of 18) | 65.7% (23 of 35) | — | — |
| 90 d net mean | **−100%** (n = 4) | +588.6% (n = 28) | +0.8% | +0.99% |
| 90 d net median | −100% (n = 4) | **−100%** (n = 28) | — | — |
| 90 d total-loss share | 100% (4 of 4) | 71.4% (20 of 28) | — | — |

**Read the not-cleared column by its median, not its mean.** Both positive
means are carried entirely by a handful of attention-crawled survivors sitting
over a −100% median and a 65.7% / 71.4% total-loss share (n = 35 / n = 28).
The distribution is the object; the registration required reporting it
precisely so a fat-tailed mean could not be mistaken for a working basket.

**Clearance carried no selection value on this population**, and on it the
cleared basket was worse than the not-cleared basket. All four comparisons (vs
SOL, vs cash, vs not-cleared, vs random) returned **p_raw = 1.0 in the adverse
direction** across 10,000 bootstrap resamples of basket membership — the
cleared basket sits at the very bottom of every draw. The registered
underpowered rule then fired (18 cleared < 20 at 30 d; 4 at 90 d), so **no
significance is claimed in either direction**: the direction is not in doubt,
the inference is.

**The mechanism, which outlasts this cohort.** Hard-rug clearance does not
contain the does-it-even-graduate question. The scorer separates hard rugs from
honest launches *among pools that had real liquidity and an indexed life* —
that is its training population. A birth-ordered pool-creation feed is instead
dominated by pre-graduation bonding curves with no liquidity to remove: **16 of
the 18 cleared pools were pump.fun curves, and 0 of 35 audited launch-venue
positions had ever graduated** (keyless graduation-state audit, so the −100%
figures are not a venue-migration artifact; ADR-013). Pointing a launch-window
scorer at raw births is a category error — the population, not the model,
decides the outcome.

**Measured in passing, each with its n:**

- **Execution cost is immaterial at these death rates.** The registered 450 bps
  round trip and its 300 / 600 bps sensitivity bounds moved the cleared
  basket's outcome not at all (n = 18): a total loss cannot be deepened.
  Execution cannot be blamed for this result (ADR-014).
- **The parse vocabulary's first real gap is SPL `BURN`: 8 unparseable of
  54,202 payloads examined (99.985% coverage)**, and all 8 refused correctly
  rather than dropping silently (ADR-009).
- **The scorer cleared 45% of birth-ordered pools (18 of 40) against the ~18%
  its holdout base rates predict**, and cleared **0 of the 16 scored graduated
  coins** — the anchor-shift warning of §4 and ADR-011 showing up directly in
  scoring behaviour.

**Scope of this finding, stated so it is not over-read.** One cohort, one
regime, 77 pools against a registered target of 300 (keyless enumeration
sources were exhausted), scores anchor-shifted. It establishes what a scanner
must be pointed at — graduated/AMM pools with real liquidity — not whether the
clearance boundary itself survives on that population. That question is still
open at ADR-011's calibration caveat.

## 2. Archived-page sampling manufactures survivorship, by 60–79 points (Stage E, 2026-08-14)

**This is the most transferable finding in the repository, and it generalizes
well past this project.** It is not about clearance, rugs, or this model. It is
about how a memecoin cohort gets built.

Stage E enumerated its cohort two ways and registered, before seeing any
outcome, that a gap of more than 15 percentage points between them would mean
the headline rests on the birth-ordered subset alone. The rule fired at full
force:

| enumeration | n | dead at 30 d | dead at 90 d | median peak-to-last drawdown |
|---|---|---|---|---|
| **birth-ordered** (Wayback captures of a `new_pools` feed) | 40 (20 at 90 d) | **97.5%** | 100% | −100% |
| **attention-crawled** (archived per-coin pages) | 16 (15 at 90 d) | **18.75%** | 40% | −50.2% |

**A 60-point gap at 30 days and a 79-point gap at 90 days, produced by nothing
but which pages a crawler chose to archive.** An archive keeps the pages
someone looked at; someone looks at coins that are doing something; coins doing
something are the survivors. The selection happens upstream of any analysis and
leaves no trace in the data itself.

**The consequence, stated directly: archived-page sampling manufactures
survivorship and invalidates memecoin studies built that way.** A cohort drawn
from crawled or listed coins would have produced a decent-looking basket out of
selection bias alone — on this cohort, an 18.75% death rate instead of 97.5%,
from the same chain, over the same months. Any outcome study that cannot
enumerate births unbiased should not be run, and any published memecoin
survival figure sourced from an archive, a listing site, or a "top coins" page
should be read as a statement about crawler attention first and about the chain
second.

## 3. The honest-versus-soft/slow-rug boundary is absent at T0+30min (C.23)

**Decontaminated honest-class precision 0.574 against a 0.500 base rate on
n = 194** — +0.07 above chance — on the 2024 time-split fold, LightGBM, no
hyperparameter search, pre-event launch-window features only. Three controls
make this signal-absent rather than sample-limited or feature-limited, each on
the same n = 194 fold:

- **Same fold, same training set, the v0 hard-rug labels separate at 0.984** —
  the pipeline learns a separable target when one exists, so the sample is not
  the limiter.
- **The decontaminated PR curve is flat**, with maximum precision at recall
  1.0 — the base-rate signature. The v0 curve climbs as the threshold tightens.
- **Creator repeat-offender history does not move it**: 0.574 → 0.570 at 42.7%
  feature coverage, leak-guarded, and it actively *hurts* the v0 direction out
  of sample (0.984 → 0.648) — an in-sample-attractive, out-of-sample-inert
  feature class.

**Consequence for this repository:** the scorer clears hard rugs only. Nothing
at T0+30min separates honest launches from soft or slow rugs, and that is a
measured property of the feature space at that horizon, not a modeling gap to
be closed with a better estimator.

## 4. The training windows open *after* the launch storm, and the live anchor is a different instant (Stage D, 2026-08-13)

Read from the parent project's own source rather than inferred — which is how
an earlier hypothesis (ADR-007's token-launch guess) came to be refuted:

- `research/detection/labels.py:81` —
  `first_ts=_ts(row.get("FIRST_POOL_ACTIVITY_TIMESTAMP"))`
- report C.22, verbatim — *"filtering signatures whose blockTime lands in
  [T0−60s, T0+1800s]"*

**The parent anchored at SolRPDS's first-recorded pool activity with a
60-second pre-roll — not at token launch and not at pool creation.** That
pre-roll explains the snapshot's negative time-to-first-sell values directly:
all three negative values among the inspected rows (−58, −30, −1 seconds; 3 of
4 rows) sit inside [−60, 0].

**SolRPDS's own timestamp lags true pool creation by +18 minutes to +13.3 days,
median ≈ 1.5 hours (measured per mint on n = 10 2024 mints)** against
GeckoTerminal's pool-creation time. The lag is an indexing artifact and is
heterogeneous per pool — each training window starts at whatever moment the
dataset first indexed that pool. **The training windows therefore
systematically opened after the launch storm**, which is visible in the window
populations: on n = 6 mints compared under both anchors, the parent's windows
held 1 / 4 / 1,123 / 135 / 221 / 693 signatures where pool-creation windows on
the same mints held 1,843 / 6,529 / 9,808 / 83 / 1,466 / 1,515.

**Consequence, and it is the caveat on every live score this repository can
produce.** The two anchors select different event sets on every pool compared.
A formal materiality ruling was **withheld**: the registration demanded ≥ 4 of
6 both-anchor pairs and only 2 were affordable (the other four priced
2,000–11,100 enhanced credits and were skipped before any call, rather than
adjusting the bar). Both measured pairs came in at **7 of 10 features in-band
against a registered 90% requirement**, with the same window-derived trio out
of band each time. The evidence points DISTINCT; the bar simply was not allowed
to rule. Per ADR-011 the scanner anchors at pool creation and **holdout
calibration is not represented as transferring** — live and retrospective
scores ship labelled **anchor-shifted**, and a caller does not inherit the
0.984 figure by running this against the chain.

Two dead ends recorded so nobody re-walks them: DAS `getAsset` returns **no
creation-time field** (10 credits/call, probed on 6 mints; the only time-like
key is `last_indexed_slot`), and from-now signature paging reached a mint's
oldest signature on **1 of 6 mints** inside a 15-page cap — the from-now
pathology of §5 again. Neither is a usable token-launch T0 source, and per
ADR-010 none is needed: the parent's exact per-mint T0 is recoverable at zero
credits from the archived SolRPDS CSVs.

## 5. The naive from-now walk excludes the pools that matter most (C.25)

Paging `getSignaturesForAddress` backward from *now* to reach a historical
launch costs O(the pool's entire subsequent history). Measured on **n = 14
random honest-2024 pools: 8 of 14 were too deep** for a 40-page cap (mean 73.6
pages per pool), so the naive method had **excluded 57% of the honest class** —
specifically the thriving survivors, biasing any sample toward faded pools that
look rug-like.

This is a **correctness** failure, not a performance cost, and it has a
measured price: on the corrected sample, half of a previously measured
behavioural lift disappeared (§7). This is why Method B exists. Method B was
accepted only after matching the from-now walk at **Jaccard 1.0 on every pool
where both reached**, at ~33 weighted credits per pool regardless of depth — a
cheaper method returning *different* history would have been a correctness
failure, not a win. See [METHOD_B.md](METHOD_B.md).

## 6. RugCheck's `rugged` flag returned False on all four documented rugs tested (C.19)

Named plainly because it is a specific claim about a tool people trust, and
scoped just as plainly: **n = 4**.

**Test method.** Four media-attested rugs — LIBRA (2025-02, Meteora insider LP
pull), HAWK (2024-12, launch-time insider concentration and dump), the kid's
QUANT (2024-11, pump.fun dev-allocation dump), and M3M3 (2024-12,
lawsuit-attested insider pre-accumulation) — were resolved on-chain by symbol
plus launch date via DexScreener, and their full RugCheck reports fetched
keyless on 2026-08-06 (~0.85 s per report; all four served complete reports for
the dead tokens, so this is a wrong answer, not a missing one).

**Result: `rugged` = False on every one of the four, including LIBRA.**

**What this supports, and what it does not.** 0-of-4 recovery disqualifies the
flag as ground truth for a labeling scheme — the use this project needed it
for — and this repository's label construction (`solclear/labels.py`)
accordingly discards the flag entirely, building labels per mechanism from
SolRPDS liquidity aggregates and GoPlus token-extension state instead. **No
inference about the tool in general is drawn from n = 4.** RugCheck's heuristic
fields (authorities, LP-lock state, holder lists) were not tested here and
remain usable as feature inputs. The claim is exactly as wide as the sample.

## 7. The post-launch behavioural lift fell to +0.032 with a CI including zero (C.24 → C.26)

Post-launch trading behaviour at T0+6h initially cleared the honest bar
(precision 0.654, lift +0.097 over base, n = 194 — C.24). It then survived
depth-unbiasing **at half the magnitude** (v0 lift +0.115 → +0.047, C.25), with
the high-activity stratum's lift collapsing +0.156 → +0.015 — a reachability
artifact of the from-now walk (§5), not signal. The surviving mid-activity
stratum lift (+0.051) met the pre-registered genuine-discrimination bar but was
marginal at ~0.8 SE. Firming with **92 additional unbiased pools (n = 286
total, C.26)** moved it **down, not up: +0.032, SE 0.039, 95% CI [−0.045,
+0.109] — including zero**, at a near-base-rate operating point.

Honest reading: the behavioural signal is real in direction, consistent across
three stages, small, and **unconfirmed**. It is **not shipped** in this package
and must not be represented as a working discriminator.

## 8. The measurement that would settle §7 is priced out, not untested (C.26)

The one measurement that would settle §7 — decontaminated labels on the
depth-unbiased sample — was **priced at ≈ 124,764 weighted credits, roughly 2×
the parent project's entire 60,000-credit cap**, dominated by 53 thriving pools
at ~2,000 each (a single active pool needs ~7,970 for its 30-day insider-sell
detail). The cheaper restructure — querying the creator address instead of the
pool — was **blocked on identification rather than cost: 0 of 8 pools resolved
a creator** from launch-window data, because the token mint generally predates
the pool-activity T0.

Recorded as **measured-unaffordable, not untested**: the question has a price
and the price was declined deliberately. It reopens on an affordable
decontaminated label — a live forward-recorded cohort — not on a better model.
