# FINDINGS.md — the measured negatives

These findings travel with this repository because they are its most useful
output for anyone else working on rug detection. Each was measured in
MLCryptoEngine (stages C.19–C.26, 2026-08-06 → 2026-08-07) with pre-registered
bars; the working lives in that project's `report.md`. Negative results are
recorded at the same standard as the positive one this repo ships, because the
expensive mistake in this domain is re-testing a settled question.

## 1. The honest-versus-soft/slow-rug boundary is absent at T0+30min (C.23)

**Decontaminated honest-class precision 0.574 against a 0.500 base rate** —
+0.07 above chance — on the 2024 time-split fold (n=194), LightGBM, no search,
pre-event launch-window features only. The controls that make this
signal-absent rather than sample-limited or feature-limited:

- **Same fold, same train, v0 labels separate at 0.984** — the pipeline learns
  a separable target when one exists, so the sample is not the limiter.
- **The decon PR curve is flat** (max precision at recall 1.0) — the base-rate
  signature; v0's curve climbs as the threshold tightens.
- **Creator repeat-offender history does not move it** (0.574 → 0.570 at 42.7%
  coverage, leak-guarded) and actively *hurts* the v0 direction out of sample
  (0.984 → 0.648) — an in-sample-attractive, out-of-sample-inert feature class.

Consequence for this repo: the scorer clears hard rugs only. Nothing at
T0+30min separates honest launches from soft or slow rugs, and that is a
measured property of the feature space, not a modeling gap.

## 2. The post-launch behavioural lift fell to +0.032 with a CI including zero (C.24 → C.26)

Post-launch trading behaviour at T0+6h initially cleared the honest bar
(precision 0.654, lift +0.097 over base — C.24). It then survived
depth-unbiasing **at half the magnitude** (v0 lift +0.115 → +0.047, C.25),
with the high-activity stratum's lift collapsing +0.156 → +0.015 — a
reachability artifact of the from-now walk, not signal. The surviving
mid-activity-stratum lift (+0.051) met the pre-registered genuine-discrimination
bar but was marginal (~0.8 SE). Firming with 92 more unbiased pools (C.26)
moved it **down, not up: +0.032, SE 0.039, 95% CI [−0.045, +0.109] — including
zero**, at a near-base-rate operating point.

Honest reading: the behavioural signal is real in direction, consistent across
stages, small, and **unconfirmed**. It is not shipped here and must not be
represented as a working discriminator.

## 3. The decontaminated-unbiased confirmation is measured-unaffordable (C.26)

The one measurement that would settle finding 2 — decontaminated labels on the
depth-unbiased sample — was **priced at ≈ 124,764 weighted credits, roughly 2×
the parent project's entire 60,000 cap** (53 thriving pools at ~2,000 each
dominate; a single active pool needs ~7,970 for its 30-day insider-sell
detail). The cheaper restructure — querying the creator address instead of the
pool — was **blocked on identification, not cost: 0 of 8 pools resolved a
creator** from launch-window data, because the token mint generally predates
the pool-activity T0. Recorded as *measured-unaffordable, not untested*: the
question has a price, and it was declined deliberately. It reopens on an
affordable decontaminated label (e.g. a live forward-recorded cohort), not on
a better model.

## 4. RugCheck's `rugged` flag returned False on all four documented rugs tested (C.19)

Named plainly because it is a specific claim about a tool people trust.

**Test method:** four media-attested rugs — LIBRA (2025-02, Meteora insider LP
pull), HAWK (2024-12, launch-time insider concentration and dump), the kid's
QUANT (2024-11, pump.fun dev-allocation dump), and M3M3 (2024-12,
lawsuit-attested insider pre-accumulation) — were resolved on-chain by symbol
plus launch date via DexScreener, and their full RugCheck reports fetched
keyless on 2026-08-06 (~0.85 s/report, all four served complete reports for
the dead tokens).

**Result: `rugged` = False on every one of the four, including LIBRA.**
0-of-4 recovery disqualifies the flag as ground truth for any labeling
scheme. RugCheck's *heuristic fields* (authorities, LP-lock state, holder
lists) remain usable as feature inputs; its verdict field does not. This
repo's label construction (`solclear/labels.py`) discards the flag entirely
and builds labels per mechanism from SolRPDS liquidity aggregates and GoPlus
token-extension state instead.

## 5. The naive from-now walk excludes the pools that matter most (C.25)

Paging `getSignaturesForAddress` backward from *now* to reach a historical
launch costs O(the pool's entire subsequent history). Measured on 14 random
honest-2024 pools: **8 of 14 were too deep** for a 40-page cap (mean 73.6
pages/pool), so the naive method had **excluded 57% of the honest class** —
specifically the thriving survivors, biasing any sample toward faded pools
that look rug-like. This is why Method B (`solclear/method_b.py`) exists and
why it is a correctness fix, not an optimization: on the corrected sample,
half of a measured behavioural lift disappeared (finding 2). Method B was
accepted only after matching the from-now walk at Jaccard 1.0 on every pool
where both reached, at ~33 weighted credits per pool regardless of depth.

## 6. A cleared basket does not beat holding SOL, and the reason is the population (Stage E, 2026-08-14)

Measured on a 77-pool retrospective cohort (creations 2025-09 → 2026-07,
pool-creation anchoring per ADR-011, all bars pre-registered): **every one
of the 18 cleared pools realized −100% net at both 30 and 90 days** — all
died on their launch venue without graduating (audited against venue
migration: 0 of 35 launch-venue positions ever graduated). Every comparison
(vs SOL, cash, not-cleared, random) sat at p_raw = 1.0 in the adverse
direction, and the pre-registered underpowered rule fired (cleared 18 < 20),
so no significance is claimed either way. Two structural facts carry the
explanation and outlast the cohort:

- **Birth-ordered new pools die almost regardless of anything**: 97.5% of
  the birth-ordered subset was dead within 30 days (100% by 90), because a
  pool-creation feed is dominated by pre-graduation bonding curves. The
  scorer separates hard rugs from honest launches *among pools with real
  liquidity* (its training population); it does not and cannot answer
  does-it-even-graduate. Scanning raw births with it is a category error —
  the population, not the model, decides the outcome.
- **Attention-selected enumeration inflates survival by 60–79 percentage
  points** (attention-crawled sub-sample: 18.75% dead at 30 d vs 97.5%
  birth-ordered). A cohort built from crawled/listed coins would have
  manufactured a decent-looking basket out of selection bias alone. Any
  future outcome study that cannot enumerate births unbiased should not be
  run.

Also measured in passing: execution cost (300–600 bps round trip) is
immaterial at these death rates; the parse vocabulary's first real gap is
SPL `BURN` transactions (8 of 54,202 payloads, refused correctly); and the
scorer cleared 45% of birth-ordered pools against the ~18% its holdout base
rates predict — the anchor-shift warning of ADR-011 showing up in scoring
behaviour. One cohort, one regime, anchor-shifted scores: this finding
scopes what a scanner must be pointed at (graduated/AMM pools), not whether
the clearance boundary itself survives — that question is still open at
ADR-011's calibration caveat.
