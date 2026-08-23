# progress.md — running log

*Newest stage first. Within a stage, the pre-registration precedes its results,
because that is the order they were written in.*

## Stage G — pre-registration: post-closure confirmations, the anchor verdict and the decon re-price — 2026-08-22

*Committed before any Stage G measurement and before any live call. Disclosure,
as always: the whole repository, the Stage D record, ADR-011, the Stage F
closure, and the parent's C.23–C.26 sections were read before writing this. The
bars below are set against measurements not yet taken: the four skipped
both-anchor pairs are unmeasured, the decon request plan is unpriced under
corrected weights, and no Stage G request has been sent.*

**Why the closed artifact reopens, and how narrowly.** ADR-015 closed this
project and named the one thing that would reopen the *outcome* question — a
different population. This stage does not touch that. It closes two items ADR-015
explicitly left standing **because they were priced out, not because they were
answered**, and both are now plausibly affordable against a measured
1,000,000-credit monthly allowance:

1. the anchor-materiality ruling Stage D **withheld** at 2 of 6 pairs against a
   registered minimum of 4 (ADR-011, standing item 1);
2. the decon-unbiased confirmation the parent recorded as
   **measured-unaffordable** at 124,764 weighted against a 60,000 cap (FINDINGS
   §8, parent ADR-054).

Neither is a new capability, a new model, or a new cohort. Both are
confirmations of already-registered questions against already-registered bars.
The stage re-closes the artifact when they are answered, whichever way they go.

### The vendor's position, reported before the cap is set

Helius exposes no usage endpoint reachable without a key, so this is **derived
from the append-only ledger against an operator-measured allowance, not read
from a vendor API** — the same honesty ADR-003 requires of every credit figure
here.

- **Operator-measured allowance: 1,000,000 weighted credits per month**, with
  nothing else drawing on the account.
- **Ledger spend to date: 67,606 weighted across 5,173 requests**, every row
  timestamped inside 2026-08 (2026-08-11 → 2026-08-14).
- **Remaining this cycle: 932,394** on the conservative reading — a calendar
  month cycle with no reset since 2026-08-14. If the billing cycle has already
  rolled the figure is up to 1,000,000. **Every affordability test in this stage
  uses 932,394**, because assuming the larger number would be assuming a reset
  nobody measured.
- Registered as a free by-product: the first live response of Task 1 has its
  **headers inspected for any vendor-published credit or quota field**, and
  whatever is found — including nothing — is reported. `gate.py` asserts that no
  such endpoint exists; that assertion gets evidence or gets corrected.

### Stage cap

- **Stage cap: 567,606 weighted credits total ledger cumulative**
  (`STAGE_G_CREDIT_CAP`) — opening position 67,606, so the **stage allowance is
  exactly 500,000**. Every request priced before sending; a refusal writes
  nothing (ADR-003). The cap is self-imposed and binds well before the vendor's
  932,394 does, which is the point of it. It is not raised mid-stage.
- **Sub-budgets.** Task 1 ≤ **25,000** (the four skipped pairs were priced
  2,000 / 2,300 / 6,700 / 11,100 enhanced in Stage D = 22,100, plus ≤ 400
  retrieval for eight windows and slack; every pair re-priced before its first
  call and skipped, not truncated, if it no longer fits). Task 2 probe ≤
  **2,500**. Task 3 is budgeted only if Task 2 returns GO, and then only inside
  whatever the stage allowance still holds.

### Task 1 — the anchor verdict procedure, quoted rather than re-derived

The thresholds are **Stage D Task 0's, verbatim**, applied unchanged across all
six pairs once the four skipped ones are measured. No re-derivation, no
adjustment, no new tolerance:

> The two anchors are **INTERCHANGEABLE** iff, across every pool compared
> under both anchors: (a) **zero clearance flips** — the `cleared` boolean
> identical wherever both anchors score, and a refusal under one anchor
> matching a refusal with the same reason under the other; (b) |Δ
> clearance_score| ≤ 0.01 on every scored pair; and (c) ≥ 90% of individual
> feature comparisons inside the Stage B tolerance bands
> (`authority_revoked_in_window` exact; counts ± 1; shares ± 0.01 absolute;
> TTFS ± 60 s). Otherwise they are **DISTINCT**, the scanner must anchor at
> token launch, and Task 2's cost becomes a hard input to scanner economics.
> **Minimum decision coverage: ≥ 4 of the 6 pre-registered pools compared
> under both anchors** — below that the stage reports insufficient coverage
> rather than deciding. The threshold is not adjusted after the measurement.

One clause of that quotation is already superseded and is flagged here rather
than silently edited: *"the scanner must anchor at token launch"* was overtaken
by ADR-010 (no affordable token-launch T0 source exists, and none is needed) and
ADR-011 (the scanner anchors at pool creation). **The decision rule (a)/(b)/(c)
and the coverage minimum are untouched** — only that consequence clause no
longer describes what a DISTINCT verdict implies. What DISTINCT now implies is
recorded below.

**What each verdict does, decided now:**

- **INTERCHANGEABLE** — the anchor-shifted labelling is retired. README.md and
  FINDINGS.md drop the anchor-shift caveat, ADR-011 is superseded by a Stage G
  ADR, and the honesty-test pin on the anchor-shift sentences is removed **in
  the same commit as the text**, deliberately, per the Stage F pattern.
- **DISTINCT** — the anchor-shifted labelling stays and stops being a
  precaution. README.md and FINDINGS.md are edited to say the shift is a
  **measured fact at full registered coverage**, not a withheld ruling, and the
  honesty pins are extended to the new sentence in the same commit. ADR-011
  moves from *withheld-with-evidence* to *measured*.
- **INSUFFICIENT COVERAGE** (fewer than 4 of 6 pairs actually complete, e.g. a
  gate refusal or an unreachable window) — the withheld status stands exactly as
  it is, and the stage reports which pairs failed and why.

### Task 2 — the decon re-price, and the affordability rule

**What is being corrected.** The parent priced the decon-unbiased test at
**124,764 weighted** under a ledger that carried `enhanced` at **10 credits per
call**. solclear corrected that weight to the vendor's published **100 credits
per call** in Stage C (commit `ad453f9`, before the first enhanced call this
repository ever made). The *request plan* is unchanged by the correction — same
pools, same 100-signature batch semantics, same 30-day insider-sell horizon —
only the price per call moves, so the arithmetic floor of the correction is
**×10**.

**Method: measure, then multiply** — the Stage B addendum pattern, not a
re-assertion of the parent's estimate.

- **Population: the parent's committed decon pool list** — the honest class of
  `data/processed/detection/behavior_c25.csv` in MLCryptoEngine, read-only. Its
  composition is reported as measured, and any divergence from the counts the
  parent's report states is reported as a finding rather than reconciled away.
- **Per-pool request plan**: enhanced detail over `(T0 + 1800 s, T0 + 30 d]` on
  the **pool** address — the horizon `decontaminate()` needs to see insider
  sells (`SLOW_RUG_HORIZON_S = 30 * 86_400`) — at
  `ceil(signatures / 100) × 100` weighted credits, plus Method B retrieval at
  the measured ~33–38 per pool.
- **The probe: 12 pools, four from each tercile of the committed 6h transaction
  count**, sub-budget 2,500 weighted, pool address and T0 resolved at **zero
  credits** from the read-only SolRPDS archive in the parent repository. Each
  probe pool's 30-day signature count is *measured*, not extrapolated; the
  stratum means then multiply out to the full population.
- **Reported**: the corrected total, the per-pool distribution — typical and
  extreme — the way Stage B reported retrieval, and the residual uncertainty of
  the multiply-out stated as an interval, not hidden in a point estimate.

**The affordability rule, fixed before the number exists.** GO iff the corrected
total (enhanced + retrieval) is **≤ the stage allowance still remaining at that
moment** *and* **≤ 80% of the vendor's 932,394 remaining monthly balance** —
leaving a fifth of the cycle's credits unspent is a floor on caution, not a
target to spend to. Otherwise **NO-GO**, recorded in FINDINGS.md as
**measured-unaffordable-at-corrected-weights with the number**, replacing the
stale 124,764 framing, and **the stage ends at Task 2 as a valid outcome**. A
no-go is not a failure of this stage; it is the answer.

### Task 3 — the decon confirmation bars, registered unconditionally

Registered now, in full, whether or not Task 2 ever lets Task 3 run — so that
nothing below can be chosen after a number is seen.

**The quantity under confirmation.** The post-launch behavioural lift in the
**6h mid-activity stratum**: **+0.032, SE 0.039, 95% CI [−0.045, +0.109]**. One
provenance correction, stated so the citation is right: that figure is
**C.26's firmed estimate** (n = 103 in the mid stratum, 166 unbiased pools
added), which *superseded* C.25's +0.051 (n = 84); it is the last value the
parent published and the one this stage confirms. It was measured on **v0**
labels because decontaminated labels did not fit the parent's budget — which is
precisely the gap this task closes.

**The estimator and the strata are the parent's, not new ones.**

- Features: `research/detection/behavior.py::behavioral_features` at cutoff
  **T0+6h** — `n_tx`, `tx_per_min`, `rate_decay`, `unique_active_minutes`,
  `max_gap_s`, `time_since_last_at_cutoff_s`, `err_fraction` — every value read
  strictly before the cutoff, with `cutoff_end` refusing any pool whose label
  event lands at or before it (survivor conditioning enforced, never clamped).
- Labels: `research/detection/history.py::decontaminate` unchanged — insider set
  = creator plus wallets whose first inbound funding came from the creator;
  **≥ 70%** of window-end insider holdings sold within **72 h** is `soft_rug`,
  within **30 d** is `slow_rug`, otherwise `honest_candidate`.
- Model and split: LightGBM, **no hyperparameter search**, train ≤ 2023 / test
  2024-Jan–Nov.
- Metric: decontaminated honest-class **precision at the max-precision point
  subject to recall ≥ 0.50**; **lift = precision − the stratum's base rate**.
  Never accuracy.
- Strata: the test fold split by **6h transaction count into terciles**, the
  parent's registered decomposition. **Mid** is the middle tercile and is the
  only stratum the bar reads; low and high are reported for continuity.
- **Interval construction, registered:** 95% normal approximation on the stratum
  precision, `SE = sqrt(p̂(1 − p̂) / n_mid)`, carried to the lift by treating the
  stratum base rate as fixed — `lift ± 1.96 · SE`. This is the construction that
  reproduces the parent's published [−0.045, +0.109] from +0.032 and SE 0.039,
  and it is not changed afterwards.
- **Answerable-cell floor: 30** decontaminated honest pools in the mid stratum's
  2024 test fold, the parent's floor, unchanged. Below it the cell is
  **unanswerable** and no precision figure is reported for it.

**The two outcomes, defined before the run:**

- **CONFIRMS INDISTINGUISHABLE FROM ZERO** — the decon mid-stratum lift's 95%
  interval **includes zero**. FINDINGS §7 changes from *unconfirmed* to
  *confirmed indistinguishable from zero under decontaminated labels*, with the
  n. The signal stays **not shipped**.
- **ESTABLISHES A REAL LIFT** — **all three** of: (i) the 95% interval's **lower
  bound > 0.02**, the parent's noise floor carried unchanged; (ii) precision
  **≥ 0.60 at recall ≥ 0.50**, the parent's honest bar carried unchanged; (iii)
  **≥ 30** decon-honest in the mid stratum. Any weaker combination — including
  an interval that excludes zero but whose lower bound sits at or below 0.02 —
  is recorded as **directionally positive, below the registered noise floor**,
  and is *not* a real lift.

**The not-shipped rule, registered so it cannot be decided afterwards.** The
behavioural signal's **not-shipped** status changes **only** on ESTABLISHES A
REAL LIFT, and even then the change is exactly this: FINDINGS §7 and README
record the signal as **confirmed and shippable**, and shipping itself is
deferred to a separate registered stage, because packaging a discriminator is a
build and this stage is a confirmation. **Every other outcome leaves "not
shipped" untouched** — no partial upgrade, no "promising", no softening of the
README line.

**The anchor branches, both stated in advance.**

- If Task 1 returns **INTERCHANGEABLE**, the confirmation runs on the parent's
  own anchor (SolRPDS first-recorded activity with the 60 s pre-roll) and is
  reported as an **exact replication** of the C.25/C.26 decon-unbiased test.
- If Task 1 returns **DISTINCT**, the confirmation runs on **pool-creation
  anchoring per ADR-011** and is reported as **a confirmation under the
  corrected anchor, not an exact replication of C.25**. Registered comparability
  language, fixed now: *the two anchors select different event sets on every
  pool compared, so a decon lift measured on pool-creation windows measures the
  same construct on the anchor a scanner can actually observe, and its point
  estimate is not a like-for-like replacement for +0.032.* A DISTINCT verdict
  does not change any bar above; it changes only what the result may be called.
- If Task 1 returns **INSUFFICIENT COVERAGE**, the parent anchor is used and the
  result inherits ADR-011's open caveat verbatim.

**Refusals (Task 3), and when the population is too reduced to estimate on.**
Refusals are honoured and reported **per class** — `retrieval_incomplete`,
`parse_incomplete`, gate-priced skips, and pools whose label event precedes the
cutoff (excluded by survivor conditioning, which is a design exclusion, not a
refusal). **If more than 20% of the registered decon population is unavailable
for any reason, the result is reported as measured on a materially reduced
population**, with the reduction and its composition stated in the same sentence
as the estimate — never silently estimated on the remainder.

### Trial accounting

**This stage adds one confirmation of one already-reported quantity, judged
against one registered bar.** Nothing here is a search. Specifically: no
additional observation cutoffs, no additional strata, no threshold retuning, no
alternative estimator, no second label scheme, and no re-reading of the anchor
thresholds. Task 1 reads six pairs against one rule fixed in Stage D; Task 3, if
it runs, reads one number against one bar fixed above. No multiplicity
correction is owed because no multiplicity is created, and this paragraph exists
so that claim is checkable rather than asserted at the end.

### Standing constraints

MLCryptoEngine is **read-only** for the whole stage; solattn is not touched. The
scope statement and every honesty pin hold — any sentence those tests assert
changes only together with its test, deliberately, in the same commit (the
Stage F pattern). The behavioural signal stays not shipped unless the rule above
fires. ADR-015's reopening condition for the *outcome* question is untouched by
this stage: it still requires a different population, not a different model.

### ETAs

T0 ~40 m, T1 ~70 m, T2 ~60 m, T3 ~3–4 h **only on a GO**, T4 ~75 m — so ≈ 4 h
on a no-go at Task 2, ≈ 8 h if the confirmation runs. Baseline: Stage F's
estimates held; Stage D's Task 4 overran ~90 m against ~40 m on enumeration
dead-ends, which is the failure mode to watch here too.

## Stage F — the project is complete — 2026-08-14

**The project is closed.** Stage E answered the question it existed to reach
and answered it negatively; Stage F ships the work as a documented public
artifact with the negatives in front, and extends nothing. **No new capability
was built and zero credits were spent** — every figure published in this stage
was already recorded.

### What this project established

- **A hard-rug clearance boundary exists at launch and is measurable**:
  0.984 precision at 0.538 recall on a 2024 time-split holdout (n = 194), from
  pre-event launch-window state only. This is the one positive result, and it
  is recomputed from the committed model and matrix on every test run.
- **Depth-independent historical retrieval is achievable and necessary.**
  Method B costs ~33–38 weighted credits per pool regardless of depth and
  matched the naive walk at Jaccard 1.0 where both reached. Necessary, not
  merely cheaper: the naive from-now walk excluded 57% of the honest class
  (n = 14), and correcting that bias erased half of a previously measured
  behavioural lift.
- **Refusal can be structural rather than documentary.** A pool that cannot be
  honestly scored returns a type carrying no number, so a truncated fetch
  cannot be misread as weak clearance. On first live contact all four pools
  refused, correctly (Stage C.1).
- **Enumeration bias dominates memecoin outcome studies.** Birth-ordered pools
  died at 97.5% within 30 days (n = 40) against 18.75% for attention-crawled
  (n = 16) — a 60–79 point gap produced by nothing but which pages a crawler
  archived. This is the most transferable thing the project produced.
- **Clearance does not select things that go up.** Every one of the 18 cleared
  pools realized −100% at both horizons on a birth-ordered cohort, and the
  cause is population mismatch: hard-rug clearance does not contain the
  does-it-even-graduate question.

### What this project did not establish

- **That a cleared pool is safe.** The honest-versus-soft/slow-rug boundary was
  measured absent at T0+30min (0.574 against a 0.500 base rate, n = 194), with
  three controls making it signal-absent rather than sample-limited.
- **That the holdout calibration transfers to a live anchor.** The materiality
  question closed at 2 of 6 pairs against a registered minimum of 4; the bar
  was withheld rather than bent. Scores ship anchor-shifted (ADR-011), and the
  two cheapest unmeasured pairs still price ~4,300 enhanced credits.
- **That the post-launch behavioural signal is real.** +0.032, SE 0.039, 95%
  CI [−0.045, +0.109] — not shipped, across every stage.
- **Anything about the graduated/AMM population**, which is the
  training-adjacent one. This cohort produced zero clears among 16 scored
  graduated coins; that is a fact about 16 coins, not a result.

### What would reopen the outcome question

**A genuinely different population — not a different model.** Specifically:
graduated or AMM pools carrying real liquidity, enumerated without survivorship
bias. The enumeration is the hard part and must come first, because the 60–79
point crawler-bias gap means a cohort drawn from archived or listed coins
manufactures a decent-looking basket out of selection bias alone. A successor
that cannot enumerate births unbiased should not run the study at all.
Retuning the threshold, adding features, or swapping the estimator addresses
none of this, and would produce a better-looking number on the same broken
population. Recorded as ADR-015.

### Deliverables

1. **README.md rewritten for a cold reader** — what it answers and does not,
   before any capability description; ADR-011's anchor shift and Stage E's
   outcome sitting high rather than buried; the base rate and what it implies;
   the credit reality (~1,450 credits/pool all-in, ~690 pools/month against a
   free 1M tier) stated before a reader spends anything.
2. **FINDINGS.md completed with sample sizes attached to every claim**, led by
   the Stage E outcome and the crawler-bias measurement, and reordered — the
   old→new section map sits in that file's header, because DECISIONS.md is
   append-only and cites it by number.
3. **METHOD_B.md** — Method B documented as a standalone reusable component,
   with the correctness argument rather than only the algorithm.
4. **Honesty tests extended and still load-bearing** — the Stage E result and
   the ADR-011 anchor-shift statement must now be present in both README.md
   and FINDINGS.md, with a canary asserting the presence-checker itself fires.
5. **Usable by someone else**: MIT `LICENSE` with the not-financial-advice
   statement attached; `pyproject.toml` metadata corrected from `Proprietary`;
   install, minimal usage example and full suite verified from a clean
   checkout (`uv sync` clean, suite green, the example scores a real holdout
   row and demonstrates the refusal, no key needed).
6. **Secret hygiene re-verified**: `.env` gitignored and untracked; no
   key-shaped string in any tracked file or anywhere in `git log -p --all`;
   `.env.example` lists `SOLCLEAR_HELIUS_API_KEY` with no value — and a blank
   value now counts as absent, so copying the template and running fails fast
   naming the variable instead of sending unauthenticated requests. That is
   the one behavioural change in this stage, and it carries tests.

### The credit ledger's final position

**67,606 weighted credits, cumulative, across 5,173 metered requests** —
4,536 `rpc` (4,536 credits), 630 `enhanced` (63,000), 7 `das` (70). Every one
priced before it was sent against an append-only on-disk ledger; no refusal
ever wrote a row. Per stage: A/B 339 → C.1 4,220 → D 6,782 → E 67,606 → **F
67,606, unchanged**. The gate fired as designed throughout — three pools
skipped by sub-budget in Stage C.1 and 18 by the per-pool ceiling in Stage E,
each priced before its first call rather than truncated mid-fetch.

### Verification

`make lint` (40 files formatted, all ruff checks passed), `make typecheck`
(mypy --strict, 34 source files, no issues) and `make test` (**97 passed**, up
from 90 — +3 honesty, +4 config/secret) all green. Two things were verified by
running them rather than by assertion:

- **From a clean checkout** (tracked files only, no `.env`): `uv sync --group
  dev` resolved clean, the full suite passed, and a minimal usage example
  scored a real holdout row (`0.4978`, `cleared=False` — matching the
  documented known-answer for that pool) and demonstrated the empty-mapping
  refusal, with no API key present. Both the missing-key and blank-key paths
  raised `MissingSecretError` naming the variable.
- **The new honesty pins fail when a negative is deleted.** Each class was
  mutated in a scratch copy and the build broke as designed: removing the
  Stage E sentence from README.md, removing the ADR-011 anchor-shift statement
  from FINDINGS.md, and changing the 18.75 crawler-bias figure each produced a
  named assertion failure. This matters because the test's document reader
  folds hard-wrapping — a check that passes for the wrong reason would have
  been indistinguishable from one that works.

ETAs (estimated T1 35 m, T2 40 m, T3 30 m, T4 30 m, T5 45 m, T6 35 m ≈ 3 h
35 m): held. T5 absorbed the most unplanned work — the blank-key defect and
the clean-checkout run — and T4 gained the mutation checks above, which were
not in the estimate and were worth the time.

### Standing items, left open deliberately

1. ADR-011 materiality: ~4,300 enhanced credits for the two cheapest unmeasured
   both-anchor pairs. Open, priced, and needed by nothing that ships.
2. SPL `BURN` parse vocabulary gap (8 of 54,202 payloads). Refused correctly;
   an extension would be reviewed against ADR-009, never slipped in under a
   closing commit.
3. The behavioural signal stays not shipped.
4. Cohort enumeration before 2025-09 needs a keyed source or a wider archive
   sweep.

## Stage E — pre-registration: does a cleared basket beat holding SOL — 2026-08-14

*Committed before any enumeration. The operator's benchmark — holding SOL or
cash — was chosen before any of this was measured and does not move in this
stage. Disclosure: all prior results were read; nothing below was set after
seeing any Stage E measurement, because none exists yet.*

### Cap, cohort, and yield expectation

- **Stage cap: 600,000 weighted credits total ledger cumulative**
  (`STAGE_E_CREDIT_CAP`); opening position 6,782. Measured per-pool cost
  ≈ 1,450 (retrieval ~38 + enhanced typical ~1,400), so a 300-pool cohort
  prices ≈ 435k with headroom for reruns and probes.
- **Per-pool enhanced ceiling: 6,000 credits** (60 calls, ≤ 6,000-signature
  windows). Pools above it are recorded with their signature counts and
  reported as a composition caveat — busy launches correlate with
  attention/survival, so this skip is a *bias to declare*, never silent.
- **Target cohort: 300 pools**, creations 2025-09-01 → 2026-07-14.
  **Underpowered rule: a cleared basket below 20 positions at a horizon is
  declared underpowered for that horizon rather than reported as a result.**
- **Registered yield expectation:** with hard rugs near two-thirds among
  real-liquidity pools and clearance recall 0.538 on the honest class, 300
  pools should yield a cleared basket near **50–60**. A materially smaller
  yield is a finding about the tool on this anchor, not a nuisance.

### ADR-012, decided now, before scoring (and grounded in the parent's encoder)

C.1/D measured pool-anchored windows refusing on
`creator_time_to_first_sell_s = None` — but in a **complete** window
(reached_t0 true, parse fully accounted), "the creator never sold" is a
**measured absence**, which the parent's own training encoder maps to the
−1.0 sentinel (`train.py` maps empty to MISSING; the committed snapshot
itself carries −1.0 rows for `creator_allocation_t0` and `top5`). Therefore:
window features that are None from a complete window encode to the trained
sentinel before scoring; **source unavailability still refuses** —
truncation, unparseable payloads, and vendor (GoPlus) None are unchanged.
The refusal tests are updated deliberately in the Task 0 commit. Without
this correction the registered yield expectation above is unreachable for a
semantic misclassification, not a property of pools.

### Basket rules (registered in full; not tuned afterwards)

- **Entry**: at the close of the pool's day-0 candle — the first candle
  whose period ends at or after score time (T0 + 30 min). A scanner cannot
  buy before it has scored, and daily granularity makes day-0 close the
  first honestly available mark. No candle within 3 days of creation → the
  position is unentered and excluded (count reported).
- **Weighting**: equal, one unit per position.
- **Exit**: at the last candle with timestamp ≤ entry + H days (H ∈ {30,
  90}), or earlier under the death rule.
- **Death rule (registered before any outcome is seen):** a position
  realizes **−100%** if the pool has no candle in the 14 days ending at its
  horizon date, **or** its exit mark is **below 1% of entry price** — a
  1e-9 dust close has no exit liquidity, and marking to it manufactures a
  recovery that could not be realized. Dead pools stay in the basket with
  their realized terminal outcome, never dropped.
- **Cash rate**: 4% annual (≈ +0.33% at 30 d, +0.99% at 90 d).

### Execution cost (registered central figure and sensitivity)

External evidence puts all-in Solana memecoin round trips near 300–600 bps
(bot fees, priority fees, slippage, sandwich exposure). Registered:
**central 450 bps round trip, charged 225 bps on entry and 225 bps on
exit**, on every leg of every basket including the random and not-cleared
baskets; sensitivity reported at 300 and 600 bps round trip. Gross and net
reported separately at every comparison so the cost's effect is visible. A
death position nets exactly −100% (entry cost cannot deepen a total loss
beyond the stake).

### Trials and deflation

The grid is **2 horizons × 3 comparisons = 6 registered trials** (cleared
vs SOL, cleared vs cash, cleared vs not-cleared, at 30 d and 90 d, with
cleared-vs-random as the null for the significance machinery). Sensitivity
variants (300/600 bps) are direction-checks, not additional trials.
Significance: bootstrap p-values (10,000 resamples of basket membership
from the same cohort), **Bonferroni-deflated over 6 trials — the reported
threshold is p < 0.0083**, and every p is reported deflated and raw. The
best cell of the grid is never reported without the rest of the grid.

### Enumeration priority and bias measurement (Task 1, registered order)

Birth-ordered Wayback captures of GT `new_pools` first (capture-timestamp
count and pool yield reported); per-coin archived pages and the live
pump.fun v3 created-DESC slice (offset-capped to recent weeks;
birth-ordered, declared) top up. Every pool carries its enumeration source;
the two sub-samples are compared on death rate, peak-to-last drawdown, and
survival at each horizon. **A material gap (any of those differing by more
than 15 percentage points) means the headline rests on the birth-ordered
subset and the top-up is reported separately.**

ETAs (baseline: Stage C/D actuals): T1 ~60 m, T2 ~2 h wall, T3 ~50 m,
T4 ~30 m, T5 ~45 m. The archived-unparseable note travels in Task 2: the D
harness recorded the count but not the payload (a defect, recorded); the
cohort scorer persists unparseable payloads so the ADR-009 vocabulary
review runs on real objects.

## Stage E — results: NO, and the reason is the population, not the execution — 2026-08-14

**The answer, in one sentence: on this cohort a cleared basket does not
beat holding SOL — every one of the 18 cleared pools realized −100% net at
both horizons (all died on their launch venue without graduating, audited,
not a migration artifact) — and the scorer does not separate outcomes in
the survivable direction either, because on birth-ordered pools ~97.5% of
EVERYTHING dies within 30 days and clearance concentrated in exactly that
population.** The registered underpowered rule also fires (cleared 18 < 20
at 30 d; 4 at 90 d), so no formal significance is claimed — with every
comparison at p_raw = 1.0 in the adverse direction, there is nothing
deflation could rescue anyway.

### Enumeration and its measured bias (the lead, as briefed)

- Birth-ordered first, as registered: **6 distinct Wayback capture
  timestamps of GT `new_pools` → 40 in-span birth-ordered pools**; 37 more
  from archived per-coin pages (attention-crawled); the live created-DESC
  tail yielded 0 (its offset window sits past the span cutoff). Cohort
  **77** (9 dropped at anchoring) vs the registered target 300 — keyless
  sources exhausted; the shortfall is an enumeration limit, recorded.
- **The registered >15 pp bias rule fires at full force**: birth-ordered
  death rate **97.5%** at 30 d (100% at 90 d) vs attention-crawled
  **18.75%** (40%) — a ~60–79 pp gap. The headline therefore rests on the
  birth-ordered subset, and the measured gap is itself a first-class
  finding: an attention-selected cohort would have manufactured a
  decent-looking basket out of crawler bias.

### Scoring distribution (Task 2)

18 cleared / 37 not-cleared / 18 skipped at the registered 6,000-credit
ceiling (**all 18 skips are attention-crawled coins** — attention correlates
with launch-window volume, the declared composition bias) / 4 refused, all
`parse_incomplete`. Parse coverage: **54,202 payloads, 8 unparseable
(99.985%)** — and the ADR-009 review ran on the persisted objects: all 8
are **SPL BURN transactions**, a precisely-named vocabulary gap (extension
candidate `burn`; the refusals were correct behaviour). Notable: the
birth-ordered clearance rate was 45% (18/40) against the registered ~18%
expectation — the anchor-shift ADR-011 warned about, visible in scoring
behaviour; and **zero cleared** among the 16 scored graduated
(attention-crawled) coins. Credits: 60,824 spent, ledger 6,782 → 67,606 of
the 600,000 cap (~1,031/pool — under the 1,450 estimate; sparse windows
dominated).

### Outcomes and the three comparisons (Tasks 3–4), gross and net

| | cleared (n=18 @30d, 4 @90d) | not-cleared (n=35 / 28) | SOL same-windows | cash |
|---|---|---|---|---|
| 30 d net mean | **−100%** (median −100%, q75 −100%, total-loss 100%, ever-above-entry 0%) | +84.1% (median **−100%**, q75 −86%, total-loss 65.7%) | −0.2% | +0.33% |
| 90 d net mean | **−100%** | +588.6% (median **−100%**, total-loss 71.4%) | +0.8% | +0.99% |

Gross equals net for the cleared basket (a total loss cannot be deepened);
the 300/600 bps sensitivity is identical — **at these death rates execution
cost is immaterial, measured**. The not-cleared means are carried entirely
by a few attention-crawled survivors over a −100% median — the
distribution, not the mean, is the object, exactly why the registration
required it. All comparisons (vs SOL, cash, not-cleared, random)
p_raw = 1.0 — the cleared basket sits at the very bottom of every draw —
and all are **declared underpowered per the registered rule**, not
reported as significant findings in either direction.

### What this establishes for Stage F

The failure is *population mismatch*, not execution: the model was trained
on SolRPDS-indexed pools — pools that had real liquidity and an indexed
life — while a birth-ordered feed at pool creation is dominated by
pre-graduation bonding curves (16/18 cleared were pump.fun curves; 0/35
audited launch-venue positions ever graduated) whose ~97.5% 30-day death
rate no launch-window scorer can out-select. The hard-rug clearance
question does not contain the does-it-even-graduate question. A Stage F
scanner would have to score the *graduated/AMM* population (the
training-adjacent one) — where this cohort produced zero clears among
scored coins, itself the open calibration question of ADR-011.

Standing caveats, unsoftened: scores are anchor-shifted and holdout
calibration is not claimed to transfer; the cohort starts at 2025-09
(earlier births unreachable) and is 77 pools against a 300 target; one
cohort over one regime proves less than it appears to. Artifacts:
`stage_e_cohort.json`, `stage_e_scores.jsonl`, `stage_e_candles.jsonl`,
`stage_e_analysis.json`, `stage_e_migration_audit.json` (machine-local).
ADR-013 (basket rules, incl. the venue-migration nuance the audit ruled
out here), ADR-014 (execution-cost model). FINDINGS.md §6 records the
negative. `make lint`, `make typecheck`, `make test` green. ETAs: T1 60→~75 m
(archive pacing), T2 est 2 h → ~27 m (77 pools, not 300), T3+T4 ~50 m
including the interrupted-and-resumed candle fetch, T5 ~45 m.

## Stage D — pre-registration: T0-basis resolution and cohort-window probe — 2026-08-13

*Committed before any Stage D measurement. Disclosure, as always: the
repository and every prior result — including Stage C.1's indirect evidence
of a basis mismatch — were read before writing this. The bars below are set
against measurements not yet taken: the parent's code has not been read, no
both-anchors comparison exists, and no cohort probe has run.*

### Cap and sub-budgets

- **Stage cap: 7,200 weighted credits total ledger cumulative**
  (`STAGE_D_CREDIT_CAP`) — opening position 4,220, so ≤ 2,980 for this
  stage. Every request priced before sending.
- **Sub-budgets:** Task 2 probes ≤ **200** (DAS `getAsset` priced at the
  vendor's published 10 credits/call — a new `das` gate weight to be added
  with a sourced comment; mint-paging probes capped at **15 pages per
  mint**, so the probe measures cost *scaling* without unbounded spend).
  Task 3 ≤ **2,600** (retrieval ≤ 500; enhanced ≤ 2,100), pool-anchor
  pairs processed sparse-first with each pair's full enhanced sweep priced
  before its first call — a pair that does not fit is skipped and reported.
  Task 4 is keyless: **zero credits**; ≤ 80 paced HTTP probes. Slack ~180.

### Task 3 materiality threshold (fixed before the comparison exists)

The two anchors are **INTERCHANGEABLE** iff, across every pool compared
under both anchors: (a) **zero clearance flips** — the `cleared` boolean
identical wherever both anchors score, and a refusal under one anchor
matching a refusal with the same reason under the other; (b) |Δ
clearance_score| ≤ 0.01 on every scored pair; and (c) ≥ 90% of individual
feature comparisons inside the Stage B tolerance bands
(`authority_revoked_in_window` exact; counts ± 1; shares ± 0.01 absolute;
TTFS ± 60 s). Otherwise they are **DISTINCT**, the scanner must anchor at
token launch, and Task 2's cost becomes a hard input to scanner economics.
**Minimum decision coverage: ≥ 4 of the 6 pre-registered pools compared
under both anchors** — below that the stage reports insufficient coverage
rather than deciding. The threshold is not adjusted after the measurement.

### Stage E go conditions (fixed before the cohort probe)

- **Sample**: 12–16 pools with creation dates spanning 2025-04 → 2026-07,
  enumerated by a method that includes pools dead today (methods tried in
  order, the one used recorded); **≥ 30% of the sample must be dead now**
  (no candle in the last 14 days, or reserve < $1k) — less than that is
  selection on survival and GO is withheld regardless of other numbers.
- **GO at horizon H ∈ {30, 90} days** iff: ≥ 80% of the sample resolves;
  first candle within **3 days** of `pool_created_at` for ≥ 70% of
  resolved; and ≥ 70% of resolved show either **≥ H/3 daily candles inside
  days 0..H** or a **terminal-death signature** (last candle inside days
  0..H closing ≤ 10% of that pool's peak) — observable death counts as
  coverage, because total loss is the outcome that matters most.
- **Benchmark leg**: Binance SOLUSDT daily must cover from 90 days before
  the earliest sampled creation through today.
- Reported either way: the latest creation date carrying a full realized
  90 days, and the latest carrying 30.

ETAs (baseline: C.1 held its estimates except enhanced pacing): T1 ~30 m,
T2 ~25 m, T3 ~45 m, T4 ~40 m, T5 ~35 m. Standing constraints: behavioural
signal not shipped; MLCryptoEngine is read-only for Task 1.

## Stage D — results: the basis is resolved from the parent's code, the anchors are distinct-by-evidence, and the cohort window is GO — 2026-08-13

*Ledger: opened 4,220, closed **6,782** of the 7,200 cap — 2,562 spent
(probe phase 140 + a 10-credit failed first DAS call, retrieval 412,
enhanced 2,000). The cohort probe spent zero credits and ~90 keyless HTTP
probes against the registered ≤ 80 — an overrun of ~10, declared: two metric
artifacts found in the first pass required one corrective re-run, and a
corrected number beats an in-budget wrong one. ETAs: T1–T3 and T5 held;
T4 ran ~90 m against ~40 (enumeration dead-ends + the corrective re-run).
`make lint`, `make typecheck`, `make test` green.*

### Task 1 — the training basis, from the parent's code, quoted

- `research/detection/labels.py:81`:
  `first_ts=_ts(row.get("FIRST_POOL_ACTIVITY_TIMESTAMP"))`
- report C.22: *"filtering signatures whose blockTime lands in [T0−60s,
  T0+1800s]"*

**The parent anchored at SolRPDS's first-recorded pool activity with a 60 s
pre-roll — not at token launch.** The snapshot's negative TTFS values (−58,
−30, −1) all sit inside [−60, 0]: explained exactly by the pre-roll, and the
C.1 token-launch hypothesis is **refuted** (ADR-010, superseding ADR-007's
hypothesis). Measured per mint on all 10 checked: SolRPDS's T0 **lags** true
pool creation by +18 min to +13.3 d (median ~1.5 h) — an indexing artifact,
heterogeneous per pool — which is why C.1's pool-creation windows saw launch
storms where the parent's windows were quiet. The parent's per-mint T0 is
reachable from solclear at **zero credits** (read-only SolRPDS CSVs in the
parent repo; extracted to `data/vendor/stage_d_parent_t0.json`).

### Task 2 — token-launch anchoring: not obtainable affordably, and not needed

- **DAS `getAsset`** (10 credits/call, weight added to the gate with the
  vendor citation before any call): returns **no creation-time field** —
  the only time-like key is `last_indexed_slot`. The first call cost 10
  credits to a parameter-shape error that RAISED per the Stage C transport
  contract; recorded, not hidden.
- **From-now signature paging** (capped 15 pages/mint so scaling is
  measured, not suffered): reached the mint's oldest signature on **1 of
  6** (CP1KFKft, 10 pages); the rest exceeded 15,000 signatures of
  post-launch depth — cost scales with depth, the exact from-now pathology
  ADR-002 exists to avoid. One probe defect recorded: gYgU hit
  end-of-history at page 10 but the harness failed to capture the final
  batch's timestamp.

Per Task 1, no token-launch source is needed: the reconciliation anchor is
SolRPDS, free.

### Task 3 — the both-anchors comparison, against the registered threshold

**Formal decision: WITHHELD — coverage 2 of 6 against the registered
minimum of 4.** Four pairs priced 2,000–11,100 enhanced credits and were
skipped by the sub-budget before any call. The threshold was not adjusted.

What the two measured pairs (CP1KFKft, gYgUiBNG) show, identically: **7/10
features in-band — 70% against the registered 90%** — with the out-of-band
fields the same window-derived trio both times (`creator_allocation_t0`,
`top5_concentration_wend`, `n_early_holders`) and *different derived
creators per anchor*. No clearance flip was observable (both anchors refuse
both pools on absent TTFS, same reason). Window populations across all six
pools: parent-anchor 1 / 4 / 1,123 / 135 / 221 / 693 signatures vs
pool-anchor 1,843 / 6,529 / 9,808 / 83 / 1,466 / 1,515 — the anchors select
different event sets on every pool. **The evidence points DISTINCT; the
registered rule simply wasn't allowed to rule on two pairs.** ADR-011
records the consequence: the scanner anchors at pool creation, and holdout
calibration is not represented as transferring — scores ship
*anchor-shifted* until the question closes (the two cheapest unmeasured
pairs price ≈ 4,300 enhanced, a deliberate future spend) or Stage E's own
outcomes stand in.

Also from this run: the **first wild unparseable payload** (1 of 1,466 in
gYgU's pool window — 99.93% coverage; archived in the results JSON;
pipeline-level scoring would refuse it as `parse_incomplete` — the harness
scored at scorer level to compute both-anchor features, stated). And the
GoPlus gap for gYgU/UutV/36gm was closed keyless — **UutVe14D reads
`mintable = 1` today, which by monotonicity proves mintable at launch**:
the first live leak-free present-now signal observed.

### Task 4 — the retrospective cohort window: GO, with named gaps

Enumeration record (five methods, failures kept — see
`scripts/stage_d_cohort.py`): GT has no creation sort; the old pump.fun
host is dead; pump.fun v3's created-ascending list is offset-capped ≈5,000
(reaches only 2024-Q1); Wayback GT `new_pools` snapshots yielded one usable
birth capture; **used: Wayback-archived pump.fun per-coin JSONs** (103
pages, 30 fetched under a fixed seed — each carries its own
`created_timestamp`, so dead coins are enumerable) plus the birth capture.
Declared: attention-crawl bias; **no births reachable for 2025-04..08**;
sample 8 vs the registered 12–16.

Sample: 8 pools, creations 2025-09 → 2026-06, measured via GT daily OHLCV
(raw candles preserved in the results for recomputation). Two metric
corrections were made in the declared re-run: GT day-candles are stamped at
00:00 (day-of-creation candles sit at negative offsets), and coin-sourced
entries' `created` is the *bonding* start, so horizons anchor at first
candle ≈ pool birth — the anchor Stage E scores at (bonding→graduation lag
measured at 104 and 160 d on the two affected coins).

Against the registered go conditions: **resolution 8/8 (1.00 ≥ 0.80 ✓);
dead-today 4/8 (0.50 ≥ 0.30 ✓ — not survival-selected); first candle
within 3 d: 6/8 (0.75 ≥ 0.70 ✓; the two misses are graduation lag, their
pools have birth candles); pool-anchored coverage h30 7/8 (0.88 ≥ 0.70 ✓),
h90 6/8 (0.75 ≥ 0.70 ✓)** — terminal deaths are observable (one pool died
at ~day 22 closing ≤ 10% of peak: exactly the outcome class that matters
most, captured). Latest sampled creation with a full realized 90 d:
**2026-03-02**; with 30 d: **2026-06-02** (calendar bounds are ~today−90/−30:
≈ 2026-05-15 and ≈ 2026-07-14). Binance SOLUSDT daily confirmed from
2025-01-01. **GO at both horizons**, on the measured sample, with the gaps
above named.

### Decision — Stage E can proceed, and how

**Anchor: pool creation** (ADR-011), scores labeled anchor-shifted, window
artifacts retained for parent-basis re-scoring. **Cohort: creations from
2025-09 (earlier if enumeration improves) through ~2026-07**, horizons 30 d
(creations ≤ ~2026-07-14) and 90 d (≤ ~2026-05-15). **Cost fits the
two-week constraint**: the tier ladder killed *continuous* scanning, not a
bounded cohort — at measured per-pool cost (~38 retrieval + ~1,400 enhanced
typical), a 100-pool retrospective cohort prices ≈ **145k credits, inside
even the free tier's 1M/month**; the tier decision for continuous scanning
remains open per ADR-008 and is not needed for Stage E.

### Open (consolidated; supersedes the Stage C.1 list)

1. **Materiality closure**: two more both-anchor pairs ≈ 4,300 enhanced — a
   deliberate spend when the operator chooses; until then ADR-011's
   anchor-shifted labeling stands.
2. **One unparseable payload** archived (gYgU pool window) — vocabulary
   review against ADR-009 before the Stage E cohort run.
3. **Cohort enumeration for 2025-04..08** needs a keyed source or a wider
   archive sweep; the Stage E cohort starts at 2025-09 without it.
4. Probe-budget overrun (~90 vs ≤ 80) and the two metric corrections are
   recorded above; the cohort script now preserves raw candles so future
   metric changes need no re-probing.
5. The behavioural signal stays not shipped (+0.032, CI includes zero).

## Stage C — pre-registration: bars before the live path is built — 2026-08-13

*Committed before any Stage C code exists and before any live call. Stage C
builds the links ADR-004 named (T0 acquisition, enhanced client, parse,
token-security source), implements ADR-005's refusal first, and ends with the
system-level known-answer test. Disclosure as before: the repository and all
prior results were read before writing this; every bar below is set against
measurements not yet taken.*

### Cap and sub-budgets

- **Stage cap: 5,000 weighted credits, total ledger cumulative**
  (`STAGE_C_CREDIT_CAP` in config.py) — 339 already spent, so ≤ 4,661 for
  this stage, every request priced before sending as always.
- **Sub-budgets, fixed so one busy pool cannot eat the stage:**
  T0-tolerance measurement ≤ **400**; enhanced batch-semantics probes ≤
  **400**; per-pool enhanced fetches (Tasks 5 + 8 combined) ≤ **3,400**,
  pools processed sparse-first by in-window signature count, each pool's
  enhanced sweep priced at ceil(n_sigs/100) × 100 and checked against the
  sub-budget *before its first enhanced call* — a pool that does not fit is
  skipped and reported, never partially fetched; ~460 slack. The stage stops
  at the cap. A refusal is a working gate, and if the measured enhanced cost
  makes even the known-answer test exceed the cap, the stage stops and
  reports per the gate rather than raising anything.

### Reproduction tolerance (carried from Stage B; amendments stated now, not after)

Carried unchanged: clearance |Δ| ≤ 0.01 absolute and the `cleared` boolean
identical on ≥ 90% of pools scored; `authority_revoked_in_window` exact
(computed from in-window events by both paths); `n_early_holders` and
`insider_funded_early_holders` ± 1; `creator_allocation_t0` and
`top5_concentration_wend` ± 0.01 absolute; `creator_time_to_first_sell_s`
± 60 s.

- **Amendment 1** (reason: the monotonicity analysis postdates Stage B's
  registration): the four GoPlus token-security fields are *now-state*, so
  they compare directionally. Live **present** (1) must agree with the
  snapshot — an authority present now was present at launch. Live **absent**
  (0) against snapshot 1 is classified **monotonic-unknowable** (an authority
  can be revoked after the window), a provenance category, not a defect.
- **Amendment 2** (reason: the committed snapshot carries no label-event
  time): the live path passes `label_event_s=None`. The window guard's
  refusal protected label construction at training time; it cannot be
  re-checked retrospectively, and this is declared now rather than
  discovered later.
- **Refusal-refusal agreement:** a pool whose snapshot row lacks a required
  feature (encoded −1.0 there) is *expected* to produce a live `Unscorable`
  naming the same absent fields — that outcome is agreement under the new
  contract, not a mismatch.
- **The refusal boundary, exactly:** `clearance()` refuses when a required
  feature key is **absent or None**. An explicit float −1.0 passes through
  as the model's trained missing-encoding — the sentinel collides with
  legitimate negative `creator_time_to_first_sell_s` values, snapshot rows
  carry it, and the live path never fabricates it (an unavailable live
  feature is None, which refuses).
- The tolerance is not adjusted to fit any result. A genuine mismatch on a
  field both paths should compute identically stops the stage with the cause
  reported.

### Enhanced-cost decision thresholds (fixed before Task 5 can measure)

Let **E** = measured per-pool enhanced credits. With the retrieval floor
37.8/pool and the addendum's measured rates against Helius's published tiers
(free 1M, Developer 10M, Business 100M per month):

| scanner scope | rate/day | free tier iff | Developer $49 iff | Business $499 iff |
|---|---|---|---|---|
| graduations, public band low | 80 | E ≤ 373 | — | — |
| graduations, public band high | 269 | E ≤ 84 | E ≤ 1,185 | — |
| graduations, sample rate | 665 | E ≤ 11 | E ≤ 456 | — |
| AMM pools only | 1,330 | never (floor exceeds) | E ≤ 209 | — |
| full feed | 9,017 | never | never (floor exceeds) | E ≤ 327 |

Since one enhanced call is 100 credits, "free tier, graduations-only"
survives only at the public-band-low rate or with zero enhanced calls per
pool. These thresholds could not see Task 5's number.

### The Task 8 pool set, registered

The Stage B five — `CP1KFKft4HtvNgNx5PDPrsmZbBs9fDFoVbJAKfiRAUde`,
`2E6SSuVKVrQ6113KpWvzvhfY9yQ647E83V6e656fpump`,
`12WRu4BdJk1yM3Nk433yg3S9GnxniUdueeu29iMPpump`,
`2ZpmY9iSdbSZVkuv64Y467FcQ5vJegbUTTMr4YJyjb2X`,
`8BnZ17s9pAd3g7s7jSPr2efXLEdKHMajqPYEkcSjmdm1` (hard_rug) — plus hard rugs
`Hp4XeAZ5EhKnFGm8Yv5GhZYmspNXGWV8SoRXPz91ZUab` and
`7CSWFsrB3gPc5o5hxKTJCUbFDq4QyTWpjVG76S1Xpump` from the addendum's resolved
sample. T0 comes from the Task 4 resolver; a mint that fails to resolve is
reported and excluded, never substituted.

### Definitions registered before the components exist

- **creator** := the recipient wallet of the first `mint_to` event inside
  the window; if the window contains none, the fee payer of the earliest
  in-window transaction. (creator_* features depend on this; fixed now.)
- **Refusal semantics** are registered as executable assertions in
  `tests/test_refusal.py`, strict-xfail until Task 1 implements them: an
  empty or partial feature mapping returns an `Unscorable` (a distinct type
  with *no* `clearance_score` and *no* `cleared` attribute) carrying the
  reason, the missing field names, and the calibration statement; a
  `reached_t0=False` fetch refuses at the pipeline level
  (`solclear.pipeline.score_pool`); a parse reporting unparseable
  transactions refuses. The credit-gate refusal (`CreditCapError` before any
  request) is a different fact and stays unchanged.
- **Fail-closed known-answer tests pinned:**
  `7CSWFsrB3gPc5o5hxKTJCUbFDq4QyTWpjVG76S1Xpump` (documented in-holdout hard
  rug, all 10 features real, offline score 0.4978 < threshold 0.5963) must
  never clear; an empty feature mapping must refuse rather than produce the
  0.4815 Stage B measured. Both run on every test pass from now on.

### ETAs (measured baseline: Stage B ~1.5 h for six tasks; the addendum held its registration)

T0 20 m, T1 45 m, T2 10 m, T3 40 m, T4 45 m, T5 50 m, T6 60 m, T7 30 m,
T8 45 m, T9 40 m — ≈ 6.5 h. Standing constraints: the behavioural signal
stays not shipped; work in this repository only.

## Stage C.1 — live execution: the path runs end to end and fails closed; the KAT is blocked by a measured T0-basis mismatch, not a defect — 2026-08-13

*Executed against the bars registered in the Stage C pre-registration above
(e38b185). Opening ledger position: **339**. Closing: **4,220** of the 5,000
cap — 3,881 spent this stage (phase A 294, phase B 400, phase C retrieval
253, phase C enhanced 2,900, refusal demo 34), every request priced before
sending. The registered sub-budgets held: phase B closed at exactly its 400;
phase C's pricing-before-first-call skipped three pools rather than
overrunning. `make lint`, `make typecheck`, `make test` green (95 passed).
ETAs held (~55 m measurement wall time against the ~27 m estimated for
tasks 3–5, the overshoot being enhanced-call pacing; report ~35 m).*

### Task 1 — credential and gate

The operator authorised the second on-disk copy Stage B deferred:
`SOLCLEAR_HELIUS_API_KEY` written into `.env` by line transformation from
the MLCryptoEngine `.env` (never echoed to history, log, or commit). Checks
before proceeding, all passed: `.env` gitignored and untracked; an in-memory
scan found the key in **no tracked file and nowhere in `git log -p --all`**;
`require_helius_key()` returns `SecretStr('**********')`. Cap 5,000 in
force; `enhanced` prices at 100 (vendor page) not the old 10; `rpc` at 1.

### Task 2 — refusal behaviour on live objects

What a caller receives, in each case — none is a number:

1. Empty feature mapping → `Unscorable(reason='missing_features')` naming
   all 10 fields. The object has **no** `clearance_score` and no `cleared`
   attribute; reading one is an `AttributeError`, not a low clearance.
2. A **real** truncation (2ZpmY9iS… re-fetched with `page_limit=25`,
   `max_pages=1`: `reached_t0=False`, 34 credits) →
   `Unscorable(reason='retrieval_incomplete')`.
3. A **real** parsed window with one token-security field withheld (the
   withholding is the one synthetic step, stated as such) →
   `Unscorable(reason='missing_features', missing=('creator_time_to_first_sell_s', 'thook'))` —
   every absent field named.
4. The documented holdout hard rug (7CSWFsrB…pump, all features real) →
   `Clearance(cleared=False, clearance_score=0.4978)` with the 874-char
   calibration statement attached. Not cleared, and not a refusal.

### Task 3 — T0 acquisition and its measured tolerance

The resolver resolved **6/6** pre-registered addendum mints — all via
GeckoTerminal (the addendum's finding stands: DexScreener has forgotten
five of the six; resolution source is recorded per claim in
`data/vendor/stage_c_t0_claims.json`). Claimed `pool_created_at` against
earliest on-chain pool activity over [T0c − 1 h, T0c + 30 min):

| pool (mint) | offset s | reached_t0 | in-window sigs | credits |
|---|---|---|---|---|
| Hp4XeAZ5… | −1 | True | 3,299 | 42 |
| UutVe14D… | −27 | True | 12,793 | 55 |
| 7CSWFsrB… | 0 | True | 18,099 | 53 |
| CP1KFKft… | −1 | True | 220 | 47 |
| gYgUiBNG… | −1 | True | 2,705 | 45 |
| 36gmCN9H… | 0 | True | 9,008 | 52 |

**Distribution: median −1 s, range [−27, 0].** The window derives as
[claimed_t0, claimed_t0 + 1,800 s); a worst-case −27 s claim error is 1.5%
of the window length, so the derivation is sound **for pool-creation
anchoring**. What Task 5 then measured is that pool-creation anchoring is
the wrong basis for the *snapshot* — see below; the claim itself is
accurate about what it claims.

### Task 4 — enhanced pricing, measured (the stage's most consequential number)

**Batch semantics by measurement:** 1 signature → HTTP 200 (1 returned);
100 → HTTP 200 (100 returned); **101 → HTTP 400. The acceptance boundary is
exactly 100.** No credit/usage headers exist on any response, so per-call
billing is vendor-documented (100/call flat, docs read 2026-08-13) rather
than response-observable; the ledger's raw counts remain the operator's
reconciliation path (ADR-003).

**Per-pool enhanced cost** = 100 × ceil(in-window sigs / 100), priced for
all seven registered pools, executed sparse-first for four:

| pool | sigs | priced | run |
|---|---|---|---|
| CP1KFKft… | 83 | 100 | ✓ |
| 2E6SSuVK… | 288 | 300 | ✓ |
| 8BnZ17s9… | 1,050 | 1,100 | ✓ |
| 2ZpmY9iS… | 1,337 | 1,400 | ✓ |
| Hp4XeAZ5… | 1,843 | 1,900 | skipped by sub-budget, priced before first call |
| 12WRu4Bd… | 1,916 | 2,000 | skipped likewise |
| 7CSWFsrB… | 9,808 | 9,900 | skipped likewise |

Stage-B-style figures: **typical ≈ 1,400/pool** (median of the seven
priced; mean excluding the extreme 1,283), **conservative ≈ 2,000**,
extreme observed **9,900** — that is **35–260× the ~38-credit retrieval
floor**. Read against the registered thresholds, unsoftened:

- **Free tier: dead for any enhanced-bearing scan.** Every scope's free
  threshold (E ≤ 373 at best) is below even the cheapest measured pool.
- **Graduations-only:** Developer $49 survives only at the public-band-low
  80/day (needs E ≤ ~4,074 — typical and conservative fit; the 9,900 tail
  does not); at 269/day Developer needs E ≤ 1,185, which typical 1,400
  misses — **Business $499**; at the 665/day sample rate, Business.
- **AMM-only (1,330/day):** Business (its E ≤ ~2,435 covers typical and
  conservative; not the tail).
- **Full feed (9,017/day):** Business needs E ≤ 327 and Professional
  E ≤ ~692 — both fail at typical cost. **Beyond Professional.**

Structural note: E cannot be cut by fetching fewer of a window's
transactions — that is truncation, and ADR-006 makes truncation refuse.
The honest cost lever is scope (which pools), not depth (how much of each
window). The tier decision is Stage D's, from these numbers.

### Task 5 — the system-level known-answer test, and what it found

Four pools ran the full path: resolve T0 → Method B fetch (34–43
credits/pool across 83–9,808-sig windows — depth independence again) →
enhanced fetch → parse → features → score. **Parse coverage, first-class:
2,758 payloads examined, 1,561 parsed to known kinds, 1,197 ignored as
understood-irrelevant (failed transactions, other mints' transfers,
native-SOL-only movements), 0 unparseable.** Per pool
(total/parsed/ignored/unparseable): CP1K 83/75/8/0; 2E6S 288/133/155/0;
8BnZ 1,050/1,049/1/0; 2Zpm 1,337/304/1,033/0.

**Verdicts:** live path returned `Unscorable(missing_features:
creator_time_to_first_sell_s …)` on all four; offline snapshot rows scored
0.4815–0.5963 (2ZpmY9iS offline `cleared=True`). The registered
clearance-reproduction bar (|Δ| ≤ 0.01, same `cleared`, ≥ 90% of pools) is
therefore **not met — reported, with the cause, and the tolerance not
adjusted.**

**The cause, identified mechanically rather than guessed — the two paths do
not share an input basis:**

- The snapshot's own `creator_time_to_first_sell_s` values are −58, −30,
  −1, +33 s: three of four are **negative**, meaning the parent's feature
  events include activity **before its T0** — structurally impossible under
  a [T0, T0+30 min) window anchored at pool creation.
- 8BnZ17s9's snapshot window saw **0 early holders** while the live
  pool-creation window is a 1,049-event storm; 2Zpm 5 vs 704; CP1K 8 vs 60.
  The parent anchored at **token launch** (mint/bonding start — FINDINGS.md
  §3 already recorded that the mint generally predates the pool), the live
  path anchored at **pool creation**, and Task 3 proved the pool-creation
  claim itself accurate to seconds. Different basis, not wrong arithmetic.
- The classification confirms the split exactly: **every basis-independent
  field agrees — `authority_revoked_in_window` 4/4 exact, the four
  token-security fields 16/16 exact, `insider_funded_early_holders` 3/4
  within ±1, `creator_allocation_t0` exact on the one pool whose snapshot
  value is basis-free (0.0)** — and every disagreement (top5 3, n_early 4,
  alloc 2, insider 1, TTFS-absent 4) sits on a window-derived field. Two
  comparisons additionally hit snapshot −1.0 sentinels (parent-absent) that
  the harness classifier compared as values; noted as a classifier
  artifact, raw JSON preserved unsmoothed
  (`data/vendor/stage_c_live_results.json`).
- No monotonic field disagreed. No monotonic-unknowable case occurred (all
  four GoPlus flags are 0 in both eras). **Zero genuine mismatches survive
  on any field whose inputs the paths actually share.**

Under the old contract, these wrong-basis windows would each have produced
a confident-looking score. Under ADR-006 all four **refused**, naming the
absent field — the fail-closed design did exactly its job on first live
contact.

### Does the live scoring path work end to end?

**Mechanically: yes.** Resolve → fetch → parse → features →
score-or-refuse ran against the live chain with every link present, 0
unparseable transactions, gate-priced spending, and refusals exactly where
honesty required them. This is the question Stage B could not reach, and
the answer is yes.

**As a reproduction of the committed snapshot: no — and the blocker is
named.** Retrospective reproduction requires the parent's T0 (token
launch), which precedes pool creation; the resolver's pool_created_at is
accurate but answers a different question. Per the registered outcome map
the stage stops at this finding. The scorer's holdout figures and Method
B's cost claim are untouched by it (both re-verified in this run); the
forward scanner is also untouched — a live scanner observes the true
launch first-party (`LiveT0Source`), so the basis problem is
retrospective-only.

### Open (consolidated; supersedes the Stage C list)

1. **Retrospective T0 basis**: the KAT needs token-launch T0, not
   pool-creation T0. Candidate recoveries, unmeasured: page the mint
   address backward from the pool anchor (cost O(bonding history) —
   measure before trusting), or a bonding-era source. Until then the
   retrospective KAT stands blocked at the basis finding.
2. **Tier decision (Stage D's)**, from measured numbers: free tier dead for
   scanning; Developer $49 only for graduations at the 80/day band;
   Business $499 for graduations/AMM-only at realistic rates; full feed
   beyond Professional. Scope is the cost lever; depth is not (ADR-006).
3. Harness classifier: treat snapshot −1.0 sentinels as parent-absent in
   the next comparison run (report artifact only; JSON preserved).
4. The behavioural signal stays not shipped (+0.032, CI includes zero).

## Stage B addendum — pre-registration: scanner cost model and outcome-study feasibility — 2026-08-12

*Committed before any probe. The Stage B entry below covered Tasks 0–3 and the
misuse check; two measurements from the stage brief remain — the scanner cost
model and the outcome-study feasibility check — and their bars are fixed here
first. Disclosure, same as the parent registration: the repository and the
Stage B results were read before writing this; the bars below are set against
external measurements not yet taken.*

### Cap and scope for this addendum

- **Zero weighted Helius credits.** Both measurements use keyless public
  endpoints only; the gate is untouched and the ledger must end this addendum
  at its current cumulative 339. If any step turns out to require a Helius
  call, the addendum stops and reports that instead.
- **Probe budget: ≤ 40 keyless HTTP requests**, paced to each source's
  published rate limit (GeckoTerminal: 30 req/min → ≥ 2 s spacing).

### Task 4 bars — scanner cost model (measure, then multiply)

- **Population**: pools the scanner would score = newly created Solana DEX
  pools as indexed by GeckoTerminal's public `new_pools` feed (all Solana
  DEXes it tracks). Measured, not quoted: retrieve the newest N ≥ 100 pools,
  rate = N ÷ (retrieval time − oldest `pool_created_at` among them), converted
  to pools/day. Source URL and retrieval timestamp recorded.
- **Cross-check**: at least one independent public figure (e.g. pump.fun
  graduations/day, a known subset). Disagreement > 2× with the measurement is
  reported as a disagreement, never averaged away.
- **Per-pool cost**: the Stage B measured figures only — 37.8 weighted
  credits/pool typical (the five snapshot addresses), 44.8 conservative
  (including the deep control). Stated as a **floor**: the enhanced-parse and
  token-security steps are NOT-WIRED (ADR-004) and their cost is unmeasured —
  it is not projected. Noted equally: a real-time scanner observes T0 as it
  happens and may not pay the measured ~34–41-credit anchor; that saving is
  also unmeasured, so the projection keeps the measured figure.
- **Allowance**: Helius's published free-tier monthly credit allowance, read
  today from the public pricing/docs page; figure and URL recorded.
- **Verdict arithmetic, fixed now**: daily burn = pools/day × per-pool cost;
  monthly = daily × 30.4. A shortfall exists iff monthly burn > the free
  allowance. If one exists, report: (a) the affordable coverage fraction =
  allowance ÷ monthly burn; (b) the cheapest paid tier that covers it; (c) a
  liquidity-threshold cut only if the feed exposes per-pool liquidity, so the
  cut is measured on the same sample rather than assumed.

### Task 6 bars — outcome-study feasibility (identifiers and price history)

- **Sample, fixed before probing** — first rows in file order per class among
  `year == 2024` in the committed snapshot, no cherry-picking:
  hard_rug: `Hp4XeAZ5EhKnFGm8Yv5GhZYmspNXGWV8SoRXPz91ZUab`,
  `UutVe14D7KVKdLzDtbKmWet2jo6wVfw8aMHovr6wMs5`,
  `7CSWFsrB3gPc5o5hxKTJCUbFDq4QyTWpjVG76S1Xpump`;
  honest_candidate: `CP1KFKft4HtvNgNx5PDPrsmZbBs9fDFoVbJAKfiRAUde`,
  `gYgUiBNGMgHiKC2aReo12JTp5rJP4WpR892hFcbpump`,
  `36gmCN9HLE5s6j8FdEYUCywByZU2KKKYy3UnAShmpump`.
- **Resolution bar**: a mint *resolves* iff a keyless endpoint (DexScreener
  `/latest/dex/tokens/{mint}`, else GeckoTerminal token→pools) returns ≥ 1
  pool whose base token is the mint.
- **History bar**: the outcome study is *feasible* iff daily candles from a
  free source span **≥ 30 days from the token's first recorded candle for
  ≥ 5 of 6 mints, and ≥ 90 days for ≥ 4 of 6 — in each case including at
  least 2 of the 3 hard_rug mints.** Dead tokens are the point of the study;
  a source that only remembers survivors fails this bar regardless of the
  overall counts, and the specific gap is reported rather than smoothed.
- **Benchmark leg**: a free daily SOL/USD series covering 2024 with ≥ 90-day
  horizon must exist and is named with its URL (candidate: Binance public
  klines, keyless).

ETAs against a measured baseline (Stage B ran ~1.5 h for six tasks): Task 4
~25 min, Task 6 ~20 min, report + `make lint/typecheck/test` ~15 min.

## Stage B addendum — results: the scanner fits free tier only at graduation scope, and the 2024 outcome study has no free launch-era price source — 2026-08-13

*Bars registered in de95281. **Zero Helius credits spent** (ledger cumulative
unchanged at 339); 35 of the budgeted 40 keyless probes. `make lint`,
`make typecheck`, `make test` (39 passed) green. The registered ETAs held
(~25/~20/~15 min). No new ADR: nothing here changes an architectural decision —
it prices one (ADR-003's placeholder weights) and scopes a future stage.*

### Task 4 — scanner cost model (measured 2026-08-13T05:15–05:35Z)

**Population rate, measured not quoted.** GeckoTerminal `new_pools` for
Solana, 122 unique pools (deduped by id; pages shift under the pager, so
missed pools bias the rate *down* — conservative) spanning
05:15:37Z–05:28:09Z against retrieval at 05:35:06Z → **~9,000 new pools/day**
by the registered formula (the newest−oldest variant gives ~14,000; same
order). Composition is the finding: **101/122 are pump.fun bonding curves.**
The AMM-pool subset this scorer actually targets (pumpswap 9,
meteora-damm-v2 6, meteora 1, raydium 1, fluxbeam 1) is 18/122 ≈
**~1,330/day**; the pumpswap-only (graduation-proxy) rate is ~665/day.

**Cross-check — a registered >2× disagreement, reported, not averaged.**
Public 2026 figures put pump.fun graduations at **80–269/day**
(dextools.io/news/pump-fun-graduation-collapse-solana-fees-2026;
cryptopolitan.com/pump-fun-token-graduations-six-month-high;
bitget.com/news/detail/12560605208670 — all retrieved 2026-08-13). The
sample's 665/day rests on n=9 (Poisson 95% CI ≈ [300, 1,260]) and
new-pumpswap-pools ⊋ graduations, so the public band is likely nearer the
truth for graduations specifically.

**Allowance, read from the vendor today** (helius.dev/pricing, 2026-08-13):
Free **1M credits/month at 10 RPS**; Developer $49/10M; Business $499/100M;
Professional $999/200M. Per-pool cost: Stage B's measured retrieval figures —
37.8 typical, 44.8 conservative — used as a **floor** (the parse and
token-security steps are NOT-WIRED, ADR-004; their cost is unmeasured and not
projected).

| coverage | pools/day | credits/mo @37.8 | against the free 1M |
|---|---|---|---|
| full feed | 9,017 | 10.36M | 9.7% affordable; needs Business $499 (Developer's 10M just misses) |
| AMM pools only | ~1,330 | ~1.53M | 65% affordable; Developer $49 covers 6.5× |
| reserve ≥ $10k (4.9% of feed, measured) | ~444 | ~0.51M | fits free, ~2× headroom |
| pumpswap pools (sample rate) | ~665 | ~0.76M | fits free at 1.3× headroom (0.91M @44.8 — barely) |
| graduations (public band) | 80–269 | 0.09–0.31M | fits free comfortably |

**The shortfall, plainly:** full-feed continuous coverage is ~10× the free
tier. The natural scopes for this tool — AMM pools at launch, or graduations
only — fit the free tier (or $49/mo) **at the retrieval floor only**. And the
floor caveat is load-bearing, because the same pricing page prices **Enhanced
Transactions API calls at 100 credits each — 10× the gate's placeholder
weight of 10** (ADR-003 declared its weights unverified; the vendor figure
now exists). One enhanced call per pool adds ≥ 100 credits (≥ 3.6× the
floor); one per launch-window transaction would dominate everything else.
**The scanner tier decision is therefore not decidable until the wiring stage
prices the enhanced step** — nothing above should be read as "free tier
suffices". Rate limit does not bind: even the full feed at ~35 requests/pool
averages ~3.7 req/s against the free tier's 10 RPS. Credits bind.

Operational note, the same lesson as Stage B's Helius 429s: GeckoTerminal
429'd mid-run at the registered 2.5 s pacing despite a documented 30/min
limit; 6 s pacing held. Raw samples preserved in
`data/vendor/stage_b_addendum_*.json` (machine-local, like the ledger).

### Task 6 — outcome study: identifiers resolve 6/6; launch-era price history exists in no free keyless source measured

**Resolution: 6/6 pre-registered mints resolve to pools with 2024
`pool_created_at`.** One via DexScreener (7CSWFsrB…pump — the only one still
carrying liquidity); the other five only via the registered GeckoTerminal
fallback: **DexScreener's token endpoint has forgotten the dead pairs;
GeckoTerminal remembers dead pools** and is the resolver a study should use.

**History: the registered bar passes literally — 6/6 span ≥ 30 d and ≥ 90 d
from the first recorded candle, 3/3 hard_rug included — and the bar was
mis-specified, which is recorded rather than papered over** (the stage's
second mis-specified bar, after the depth sub-bar). The study needs
launch→launch+30/90 d; the first candle sits months to a year after pool
creation on every one of the six:

| mint | class | pool created | first candle | last candle | daily candles |
|---|---|---|---|---|---|
| Hp4XeAZ5… | hard_rug | 2024-05-23 | 2025-03-12 | 2026-07-21 | 65 |
| UutVe14D… | hard_rug | 2024-05-02 | 2024-09-19 | 2025-08-09 | 4 |
| 7CSWFsrB… | hard_rug | 2024-10-11 | 2025-03-14 | 2026-08-12 | 57 |
| CP1KFKft… | honest | 2024-09-25 | 2025-03-14 | 2026-07-21 | 35 |
| gYgUiBNG… | honest | 2024-07-03 | 2025-04-14 | 2026-07-06 | 18 |
| 36gmCN9H… | honest | 2024-09-25 | 2025-03-28 | 2026-05-12 | 37 |

**Launch→+90 d coverage: 0/6.** Four of six first candles cluster in
2025-03-12→28 while creations span May–Oct 2024 — consistent with a rolling
daily-candle retention horizon (~17 months back from today), though UutV's
2024-09-19 start shows it is not a hard cutoff, so the mechanism is stated as
observed, not asserted. What exists is sparse late-life dust trading (4–65
non-contiguous candles over 300–500-day spans; last closes 1e-6–1e-9 USD —
all six near-worthless today, the three honest_candidates included, which is
the scope statement's cleared ≠ safe visible in data).

Consequences, both directions:

- **Retrospective on the 2024 holdout: not feasible from the free keyless
  sources measured.** DexScreener has no history endpoint and forgets dead
  pairs; GeckoTerminal's daily OHLCV misses the launch era for this cohort.
  Paths that exist but were not verified here (accounts/keys needed):
  reconstruction from on-chain DEX swaps via free-tier SQL warehouses (Dune,
  Flipside), or paid history (Birdeye). Dead tokens are exactly the outcomes
  that matter most, so this gap decides the study design, and it is reported
  as a gap, not smoothed.
- **Forward, on a live cleared cohort: feasible.** A pool cleared today has
  its launch inside any plausible retention window, so the same free daily
  candles cover launch→+90 d (or can be snapshotted as they occur). This
  converges with FINDINGS.md §3's reopening condition — "a live
  forward-recorded cohort" — which is now also the affordable outcomes path.
- **Benchmark leg exists:** Binance public klines, keyless
  (api.binance.com/api/v3/klines, SOLUSDT daily), verified from 2024-01-01
  (first close 109.91) — full coverage of any 2024 horizon for the
  hold-SOL comparison; cash is a constant.

### Open (consolidated; supersedes the Stage B list above)

1. **The live scoring path is NOT WIRED** (ADR-004): T0 acquisition,
   enhanced-detail client, parse to `features.Tx`, and a token-security
   source, in that order, before any pool can be scored from the chain.
2. **An unscoreable pool currently returns a score** (ADR-005): implementation
   of the refusal is the next code stage's first change.
3. **The gate's `enhanced` weight (10) is 10× under the vendor's published
   price (100/call**, helius.dev/pricing, 2026-08-13). Correct it before any
   enhanced client exists — it under-gates exactly the step about to be
   built. The ledger records raw counts, so reconciliation needs no history
   rewrite (ADR-003's design).
4. Method B rate-limit pacing and the `block_time` error-vs-skipped-slot
   conflation (Stage B), both unchanged.
5. **Scanner tier decision deferred** until the enhanced step is priced: at
   the retrieval floor, graduations-only fits the free tier and the full feed
   needs ~$499/mo, but the floor is a known underestimate.
6. **Outcome study**: forward cohort design is the measured-feasible path;
   the 2024 retrospective needs an on-chain-swap reconstruction source
   (Dune/Flipside, unverified) or paid history. The behavioural signal stays
   not shipped (+0.032, CI includes zero), untouched throughout.

## Stage B — pre-registration: bars for the live end-to-end validation — 2026-08-12

*Committed before any live call. Stage A left the live path (Method B fetch →
enhanced-detail parse → features → clearance) unrun; this stage runs it against
the chain and judges it against bars fixed here.*

**Disclosure, so this registration is not mistaken for a blind one.** The
repository's source was read before these bars were written — that is static
inspection, not results, and the bars below are set against measurements not
yet taken. But a bar written only for the disagree-case would let a *missing
component* pass as a pass, so the outcome map below carries **NOT-WIRED** as a
first-class outcome.

### The stage cap and scope

- **Credit cap for Stage B: 400 weighted credits** (`SOLCLEAR_HELIUS_CREDIT_CAP=400`),
  against the parent project's measured ~33 weighted credits per pool for
  Method B — roughly 12 pools of headroom.
- **Pool count: ≤ 8 addresses** for the Method B live validation (Task 2),
  **≤ 6 pools** for the known-answer comparison (Task 3). A refusal by the gate
  is a working gate; the stage stops rather than raising the cap mid-run.

### Reproduction tolerance (live path vs the persisted offline snapshot)

Same mint, live-path features and clearance against the committed snapshot row:

- **Clearance score: |Δ| ≤ 0.01 absolute**, and the `cleared` boolean identical,
  on **≥ 90%** of pools scored.
- **Per feature**: `authority_revoked_in_window` must agree **exactly** (it is
  monotonic — present now proves present at launch); `n_early_holders` and
  `insider_funded_early_holders` within **±1**; `creator_allocation_t0` and
  `top5_concentration_wend` within **±0.01 absolute**;
  `creator_time_to_first_sell_s` within **±60 s**.

### Depth-independence bar (Method B, live)

The library's central correctness argument. On live data, over addresses
spanning depth including at least one known-deep address:

- Weighted credits for the **deepest** address ≤ **1.5×** the shallowest, and
- mean cost per pool within **±50%** of the parent's measured **~33**.

Failing either is a **finding to report, not a number to smooth**. `reached_t0`
false cases are reported per pool and never dropped, since silent truncation is
the exact bias Method B exists to remove.

### Outcome map — what counts as broken, fixed before the result

- **NOT-WIRED (broken, and distinct from disagreement).** A component the live
  path requires does not exist in the repository, so no live score can be
  produced at all. This is a *harder* failure than disagreement: Stage A's open
  item claimed the pipeline was "wired as a library but has not been run", and
  a missing component means that claim was wrong. If this fires, the stage
  reports the exact missing links and **stops** — it does not build them.
  Building a missing component and then validating it in the same stage would
  be reading a result against a bar its builder could see, which this project's
  known-answer discipline forbids.
- **BROKEN (wired, wrong).** Any of: a **monotonic** field disagrees with the
  snapshot; the `cleared` boolean flips on **> 10%** of pools; live Method B
  cost exceeds **2×** the parent's ~33/pool; or `reached_t0=False` on a pool
  whose window the parent reached.
- **MERELY DIFFERENT (not broken).** Disagreement confined to **non-monotonic**
  fields — the class the parent project classified as contaminated (e.g.
  `lp_locked_pct`, which for that reason should not be feeding the model at
  all, making a disagreement there a design question rather than a bug);
  continuous features drifting inside the tolerances above; or a feature
  unavailable live because its source is a vendor this repo has no client for.
- **The tolerance is not adjusted to fit the result.** If the live path misses
  it, the stage stops and reports the cause.

### Standing constraints for this stage

Validation only: no new signal, and specifically **not** the behavioural
signal, which concluded at +0.032 lift with a CI including zero
(FINDINGS.md §2). No push to any public remote.

## Stage B — live validation: Method B holds, the scoring path is NOT WIRED — 2026-08-12

**Verdict against the outcome map registered above: NOT-WIRED.** Method B —
the retrieval half — works against the live chain and reproduces its measured
cost. The scoring half cannot run at all, because three components the live
path requires do not exist in this repository. Stage A's open item recorded
the pipeline as "wired as a library but has not been run"; that was wrong, and
the correction is the main output of this stage.

Spend: **339 of the registered 400 weighted credits**, 339 ledger entries
(267 `getBlockTime`, 55 `getSignaturesForAddress`, 10 `getSlot`, 7 `getBlock`).
ETAs (from a measured 30 ms median TLS RTT and 101 ms first round trip) were
~10/10/20/20/10/25 min per task against ~1.5 h actual — held, except Task 3,
which finished early because it terminated on a missing component rather than
a comparison.

### Task 1 — key, gate, balance

The variable the repo declares is `SOLCLEAR_HELIUS_API_KEY` (read from
`.env.example`, not assumed). It was supplied **through the environment at
call time rather than by writing a `.env`**, deliberately: the operator's key
already exists elsewhere on this machine, and creating a second on-disk copy
of a credential is a decision for the operator, not a side effect of a
validation stage. `pydantic-settings` reads the environment natively, so the
key still arrives through the config layer — `require_helius_key()` returned a
`SecretStr` whose repr redacts to `**********`.

`.env` is ignored (`.gitignore:2`) and untracked; `data/vendor/` (the ledger)
is ignored (`.gitignore:10`); no key-shaped string appears in any tracked file
or anywhere in git history. The gate charged before every send and the ledger
survived across four separate processes.

**Free-tier balance: not retrievable.** Helius documents no endpoint returning
remaining credits — usage is dashboard-only (checked 2026-08-12 against the
RPC docs). This *confirms* ADR-003's premise rather than merely inheriting it:
cost must be derived, and the 339 figure above is this repo's own derived
accounting, not a reading from the vendor.

### Task 2 — Method B on live data: the cost claim reproduces

Identical 30-minute window (2024-06-15T12:00Z) for every address, so cost
differences cannot come from window width. `anchor` = the depth-independent
part (slot binary search + seed), separated from paging:

| address | newest signature (depth proxy) | reached_t0 | pages | in-window sigs | credits | anchor |
|---|---|---|---|---|---|---|
| CP1KFKft… honest/soft_rug | 2026-07-18 | True | 1 | 0 | 43 | 41 |
| 2E6SSuVK… honest/honest | 2026-08-10 | True | 1 | 0 | 36 | 34 |
| 12WRu4Bd… honest/honest | 2026-07-25 | True | 1 | 0 | 36 | 34 |
| 2ZpmY9iS… honest/soft_rug | 2026-08-09 | True | 1 | 0 | 38 | 36 |
| 8BnZ17s9… hard_rug/hard_rug | 2026-06-24 | True | 1 | 0 | 36 | 34 |
| **EPjFWdd5… USDC mint (known-deep)** | 2026-08-12 | **False** | **40** | **40,000** | **80** | **39** |

**The headline: the anchor cost is 34–41 across all six addresses, a 1.21×
spread, including one whose subsequent history is larger by orders of
magnitude.** Mean total cost 44.8 against the parent project's ~33 — inside
the registered ±50% band (16.5–49.5), and 37.8 excluding the deep control.
The parent's ~33/pool reproduces on live data.

**One registered sub-bar failed, and it is reported rather than moved.** The
bar said the deepest address's weighted credits must be ≤ 1.5× the
shallowest; measured **2.22×** (80 vs 36). The decomposition says why: every
credit of the excess is **paging over 40,000 signatures inside the window**,
not depth. Method B's cost is O(log chain) + O(in-window volume), and only the
first term is what the naive from-now walk pays as O(depth). **The bar was
mis-specified — it should have been written on anchor cost — and that is a
defect in my registration, not in the method.** The correctly-specified
quantity passes at 1.21× ≤ 1.5×. Recording both, because a bar rewritten after
seeing the result is not a bar.

Two honest limits on this test. The five snapshot mints had **zero in-window
activity** (the fixed window does not overlap their launches), so for them the
comparison is anchor-versus-anchor and paging was never exercised. And the
depth proxy shows **all six addresses still active in 2026**, so all have
substantial post-window history — USDC's is vastly larger by volume, which is
the contrast the control was chosen for, but "shallow" here means "less deep",
not "dead".

**`reached_t0=False` fired exactly as designed**, on USDC: 40 pages, 40,000
signatures, window start never reached. The library reported the partial
rather than returning a truncated window as if it were complete — the failure
mode FINDINGS.md §5 exists to prevent, observed working on live data.

**A defect found on the way: the free tier rate-limits, and Method B has no
pacing.** The first run took HTTP 429 on 3 of 6 addresses mid-binary-search.
The harness now paces requests (150 ms), which is a property of the key's
tier rather than of the algorithm — so it lives in `scripts/live_validation.py`,
not in the library, where a hidden sleep would conceal an operational
constraint from callers. Related and worth naming: `HeliusRpc.block_time`
maps a JSON-RPC error to `None`, which `slot_at_or_after` cannot distinguish
from a legitimately skipped slot, so a transient node error during the binary
search would be silently absorbed as "slot skipped" and the search would scan
on. It did not misfire here (the 429s surfaced as HTTP errors, which do
raise), but conflating an error with a data condition is the shape CLAUDE.md
forbids. Left unfixed deliberately — see the scope note below.

### Task 3 — the system-level known-answer test could not run: NOT-WIRED

The comparison this stage exists to perform requires live features. It cannot
be reached, and the gap is mechanical rather than a matter of judgement:

1. **No transaction parse step exists.** Method B returns `WindowFetch` of
   `SigInfo` (`signature`, `slot`, `block_time_s`, `err`).
   `features.features()` consumes `list[Tx]` (`ts_s`, `kind` ∈ {mint_to,
   transfer, sell, revoke_authority}, `wallet`, `amount`, `source`). A scan of
   every function in the package finds **zero returning `Tx`** — the only
   `Tx` construction anywhere in the repo is synthetic, inside
   `tests/test_leakage.py`. Nothing converts signatures into balance-changing
   events.
2. **No enhanced-detail client exists.** `HeliusRpc` exposes exactly
   `latest_slot`, `block_time`, `block_signatures`, `signatures_for_address`.
   Nothing calls Helius's Enhanced Transactions API. The credit gate prices an
   `enhanced` kind at weight 10 — **a weight no client method can currently
   incur**, which is the clearest single sign the step was designed and never
   built.
3. **Four of the ten model features have no live source at all.** The model
   requires `freezable`, `mintable`, `nontransf`, `thook` — GoPlus
   token-security fields in the parent project. `features.features()` produces
   six features; those four are produced by nothing in this repo, and there is
   no GoPlus client.

A fourth obstacle sits behind those three: **the committed snapshot carries no
launch T0**. Its columns are `mint, year, cls, decon` + 10 features + 5
creator-history columns. Method B needs a window start, so even with a parser
and a GoPlus client, the specific holdout pools could not be re-fetched
without first recovering each pool's T0 — which is the expensive
page-back-from-now operation Method B exists to avoid. (An earlier automated
check of mine reported a T0 column present; that was a false positive from
substring-matching `creator_time_to_first_sell_s`, and is corrected here.)

The docstring on `scorer.clearance` states the assumption that failed:
"`features` comes from the caller's retrieval pipeline (Method B fetch →
`solclear.features.features`)". Those two ends do not connect — the types do
not meet and nothing bridges them.

**The stage stops here rather than building the missing links**, per the
registered outcome map. Building three components and then validating them
against a known answer in the same stage would be reading a result against a
bar their builder could see, which is the discipline in CLAUDE.md that this
project's own known-answer rule exists to enforce.

What *is* verified offline stands unchanged: the persisted model reproduces
0.984 precision / 0.538 recall on the committed holdout, asserted by
`tests/test_honesty.py` against the sha256-pinned matrix. The scorer half is
sound; it is the path *to* the scorer that does not exist.

### Task 4 — the misuse check, and a real hazard

Confirmed good on live objects: the returned `Clearance` carries the full
874-character calibration statement; its field set is exactly
`{pool, cleared, clearance_score, calibration}`; and no attribute reads as
detection, alarm, danger, risk, probability, or safety.

**The hazard: an unscoreable pool returns a score, not a refusal.**
`clearance("pool-with-NO-data", {})` — an empty feature mapping, i.e. nothing
known about the pool whatsoever — returns `cleared=False,
clearance_score=0.4815`. Every absent feature becomes the `MISSING = -1.0`
sentinel, the model scores the sentinel row, and the caller receives a
confident-looking number. This is precisely the failure Task 4 names: **a
caller reads 0.48 as weak clearance evidence when the truthful answer is "no
answer at all".** And the two failure sources this stage measured both land
there: a `reached_t0=False` truncation (observed live on USDC) and a
partially-available feature set produce a *number*, because
`solclear/scorer.py` contains no reference to `reached_t0` or `WindowFetch` —
there is no structural link between "the retrieval was incomplete" and "this
must not be scored".

By contrast the **credit-refusal** failure case is unambiguous and correct: the
gate raises `CreditCapError` naming the arithmetic before any request is sent,
and writes nothing. A caller cannot mistake that for a verdict.

Not fixed in this stage, and the reason is not timidity: the fix changes the
`Clearance` field set, which ADR-001 pins deliberately and
`tests/test_honesty.py` asserts exactly. That makes it an ADR-level decision
for the operator rather than a drive-by edit inside a validation stage — see
ADR-005, which records the decision and leaves the implementation to the next
stage.

### Open

- **The live scoring path is not wired.** Three components must be built
  before any pool can be scored from the chain: an enhanced-detail
  transaction client, a parse from parsed transactions to `features.Tx`, and a
  token-security source for `freezable`/`mintable`/`nontransf`/`thook`. A
  fourth question precedes them: how a pool's launch T0 is obtained, given the
  snapshot does not carry it. See ADR-004.
- **An unscoreable pool currently returns a score.** ADR-005 records the
  decision that it must not; the implementation is the next stage's.
- **Two smaller live-path defects**, both named above and neither fixed here:
  Method B has no rate-limit pacing (the free tier 429s without it), and
  `HeliusRpc.block_time` cannot distinguish an RPC error from a skipped slot.
- The behavioural (post-launch) signal remains **not shipped** — +0.032 lift
  with a CI including zero (FINDINGS.md §2), unchanged by this stage and
  deliberately untouched by it.

## Stage A — scaffold, retrieval library, scorer, honesty tests — 2026-08-11

Repository created from the MLCryptoEngine detection track's concluded outputs
(stages C.19–C.26). Nothing new was measured; everything shipped here carries
its parent-project provenance and figures.

Done:

- **Scaffold**: CLAUDE.md (scope statement verbatim as non-negotiable rule 1,
  directory map, standing practices), README.md (leads with what the tool
  answers and what it does not, figures + holdout attached), FINDINGS.md (the
  five measured negatives, RugCheck 0-of-4 named plainly with the test
  method), DECISIONS.md (ADR-001 clearance framing, ADR-002 Method B, ADR-003
  credit gate). Tooling: uv, ruff, mypy --strict, pytest, pre-commit,
  Makefile; .gitignore excludes .env and credential-shaped filenames;
  .env.example carries the Helius variable commented and valueless.
- **Retrieval library**: `solclear/method_b.py` — depth-independent
  launch-window retrieval (slot binary search on getBlockTime, foreign-seed
  `before=` paging), with known-answer tests including a depth-independence
  test (identical request count against a much deeper pool) and honest
  partial reporting (`reached_t0=False`). `solclear/gate.py` — the credit
  gate: priced before sending, append-only ledger, restart-proof, refusal
  writes nothing. `solclear/rpc.py` — thin Helius transport; the key never
  appears in errors.
- **Scorer**: `solclear/features.py` (launch-window features +
  decontamination rules), `solclear/labels.py` (four-class construction,
  RugCheck `rugged` discarded), `solclear/scorer.py` (clearance API:
  `Clearance` with calibration statement attached, no danger-reading
  probability exposed), `solclear/train.py` (regenerates the model from the
  sha256-pinned immutable snapshot). Leakage suite wired as first-class
  tests: window-leak refusal, prefix invariance, and a planted-future canary
  proven to have teeth.
- **Honesty tests**: scope statement asserted verbatim in CLAUDE.md and
  README.md; API surface pinned against rug-detection-shaped names; the
  documented 0.984 / 0.538 (and the 0.464 misuse figure) asserted against
  what the persisted model actually produces on the committed 2024 holdout.
- make lint, make typecheck, make test green; git initialized and committed.
  Not pushed to any public remote (per Stage A instruction).

Open (deliberately, matching the measured record):

- The behavioural (post-launch) signal is NOT shipped — it concluded at
  +0.032 lift with a CI including zero (FINDINGS.md §2) and would need an
  affordable decontaminated label to confirm (FINDINGS.md §3).
- Live scoring pipeline (Method B fetch → enhanced-detail parse → features →
  clearance) is wired as a library but has not been run end-to-end against
  the live chain from this repo; doing so needs a Helius key in .env and
  spends credits through the gate.

  **Correction (Stage B, 2026-08-12): "wired as a library" was wrong.** The
  retrieval end (Method B) and the scoring end (the persisted model) each
  work, but nothing connects them — there is no enhanced-detail client, no
  parse from transactions to `features.Tx`, and no source for 4 of the 10
  model features. The claim was made from the presence of the two ends rather
  than from a traced path between them. Left above verbatim, because the log
  is append-only and an overstated claim is worth being able to see. See the
  Stage B entry and ADR-004.
