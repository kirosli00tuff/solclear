# DECISIONS.md — architecture decision records

Append-only. Read before revisiting any settled question. Parent-project ADR
numbers are cited where a decision was inherited rather than made here.

## ADR-001: The API is clearance, and only clearance

**Date:** 2026-08-11 · **Status:** accepted

**Context.** The underlying model separates hard rugs from other launches on
launch-window state. The same separator has two readings, and they are not
symmetric: as a *clearance* (a low P(hard_rug) clears a pool as
not-a-hard-rug) it measured **0.984 precision at 0.538 recall** on the 2024
holdout; as a *rug alarm* (a high P(hard_rug) flags a pool) it measured
**0.464 precision** — wrong more often than right, because honest pools also
launch concentrated. The wild base rate (~98.7% of pump.fun launches
scam-adjacent) makes the alarm reading worse still, and makes accuracy a
meaningless metric for anything in this domain (parent C.23/C.24, ADR-050
there).

**Decision.** The public API exposes exactly one direction. The entry point is
`clearance()`; it returns a `Clearance` dataclass whose fields are `pool`,
`cleared`, `clearance_score`, and `calibration` — the calibration statement is
attached to every verdict, and no bare number is ever returned. **No
probability of danger is exposed anywhere public.** The misuse direction is
made awkward deliberately: reaching P(hard_rug) requires going around the
public API, and `tests/test_honesty.py` pins the exported names, the
`Clearance` field set, and the documented figures against the persisted
model's holdout performance, so scope erosion or silent model degradation
breaks the build.

**Consequences.** Users cannot mistake the tool for a rug detector or a
safety scorer without ignoring text delivered inside the return value itself.
The cost is flexibility: an integrator who wants a raw probability must fork
consciously, which is the point. The documented figures live in one place
(`solclear/metrics.py`) so docs, meta sidecar, and tests cannot drift apart.

## ADR-002: Method B is the only supported retrieval path for historical windows

**Date:** 2026-08-11 · **Status:** accepted · inherits parent ADR-053

**Context.** The naive retrieval pages `getSignaturesForAddress` backward from
now, costing O(pool's entire history) per pool. The parent project measured
the consequence (C.25): a 40-page cap silently **excluded 57% of the honest
class** — the deep, thriving pools — biasing samples toward faded pools and
inflating a behavioural lift by 2× (the high-activity stratum's lift was
+0.156 biased, +0.015 unbiased). This is a correctness failure, not a
performance cost.

**Decision.** Port Method B as this repo's standalone retrieval module:
resolve the window end to a slot by binary-searching `getBlockTime`, seed a
signature from that block via `getBlock` (`before` accepts a foreign
signature — measured, not assumed), then page
`getSignaturesForAddress(before=seed)` backward to the window start.
**~33 weighted credits per pool regardless of depth.** Correctness bar
inherited from parent C.22: a cheaper method must return the *same* history —
Method B matched the from-now walk at **Jaccard 1.0** on every pool where
both reached. A fetch stopped by the page bound reports `reached_t0=False`
and must be discarded as a corrupted partial, never used silently.

**Consequences.** Unbiased historical sampling is affordable; the from-now
wall that shaped parent stages C.23–C.24 does not exist here. The known
limitation: block-time binary search assumes bounded skipped-slot runs
(`MAX_SKIPPED_SLOT_SCAN`); a chain segment violating it raises rather than
guessing.

## ADR-003: Every metered request passes a credit gate that refuses first

**Date:** 2026-08-11 · **Status:** accepted · inherits parent ADR-046

**Context.** Helius credits are a real budget, and the failure mode is not one
big request but many small ones that individually look free. The parent
project's gate fired correctly twice in production: the C.21 sweep budget stop
(halted at 178 of 200 tokens, exactly as registered) and the C.26 refusal of a
purchase priced at ~2× the entire cap. Helius exposes no keyless usage
endpoint, so cost must be derived, not read.

**Decision.** Port the gate unchanged in shape: **every request is priced
before it is sent** (`charge()` runs the cap arithmetic first; `GatedRpc`
wraps any transport so unpriced calls are structurally unavailable); the
ledger is **append-only on disk** and `spent()` re-reads it, so the cumulative
total survives restarts and many small requests cannot walk past the cap; **a
refusal names the arithmetic and writes nothing.** Weights ({rpc: 1,
enhanced: 10}) are conservative placeholders, stated as unverified against the
dashboard; the ledger records raw counts so the operator can reconcile and
correct them with one edit. The cap (default 30,000) is self-imposed, not a
tier limit; raising it is a deliberate operator decision made before a sweep,
never mid-sweep.

**Consequences.** A runaway loop, a mispriced sweep, or a restart cannot
overspend silently. The cost is friction: transports must be wrapped, and
tests must construct a gate — which is exactly the friction that keeps an
unmetered path from creeping in.

## ADR-004: The live scoring path is not wired; the three missing links are named, not built

**Date:** 2026-08-12 · **Status:** accepted

**Context.** Stage A recorded the live pipeline (Method B fetch →
enhanced-detail parse → features → clearance) as "wired as a library but has
not been run". Stage B's live validation established that this was wrong, by
mechanical check rather than judgement:

1. **No parse step.** Method B returns `WindowFetch` of `SigInfo`
   (signature/slot/block_time/err); `features.features()` consumes `list[Tx]`
   (balance-changing events). No function in the package returns `Tx` — the
   only construction anywhere is synthetic, in `tests/test_leakage.py`.
2. **No enhanced-detail client.** `HeliusRpc` exposes four plain RPC methods
   and nothing that calls the Enhanced Transactions API. The credit gate
   prices an `enhanced` kind at weight 10 that **no client method can incur** —
   the step was designed and never built.
3. **No source for 4 of the 10 model features.** `freezable`, `mintable`,
   `nontransf`, `thook` come from GoPlus token-security in the parent project;
   this repo has no client for them, and `features.features()` produces the
   other six only.

A fourth question sits behind these: the committed snapshot carries **no
launch T0**, so re-fetching a specific holdout pool needs its window start
recovered first — by exactly the page-back-from-now operation Method B exists
to avoid (ADR-002, FINDINGS.md §5).

**Decision.** Stage B **stops at the finding and does not build the missing
links.** Building three components and then validating them against a known
answer inside the same stage would be reading a result against a bar their
builder could see, which is the failure the project's known-answer discipline
exists to prevent (CLAUDE.md, standing practices). The components are named
here so the next stage can register bars for them **before** they exist, in
that order: (a) T0 acquisition, since it gates everything; (b) enhanced-detail
fetch and parse to `Tx`, whose correctness bar is that it reproduces the
committed snapshot's six launch-window features on pools whose offline values
are known; (c) a token-security source for the remaining four.

**Consequences.** The retrieval half is validated and the scoring half is
validated, and the repository ships neither a working end-to-end path nor a
claim to have one — `README.md` already scopes the tool to a scorer over
supplied features, which remains accurate. Two smaller live-path defects are
recorded rather than fixed for the same scope reason: Method B carries no
rate-limit pacing (the free tier returns HTTP 429 without it, measured on 3 of
6 addresses), and `HeliusRpc.block_time` maps a JSON-RPC error to `None`,
which `slot_at_or_after` cannot distinguish from a legitimately skipped slot —
an error silently becoming a data condition, the shape CLAUDE.md forbids.

## ADR-005: A pool that cannot be scored must not return a score

**Date:** 2026-08-12 · **Status:** accepted · implementation deferred to the next stage

**Context.** Stage B measured what a caller sees when scoring cannot honestly
happen: `clearance("pool-with-no-data", {})` returns `cleared=False,
clearance_score=0.4815`. Every absent feature becomes the `MISSING = -1.0`
sentinel, the model scores that row, and the caller receives a plausible
number. The same applies to a `reached_t0=False` truncation — observed live on
a deep address, 40 pages and the window start never reached — because
`solclear/scorer.py` references neither `reached_t0` nor `WindowFetch`: there
is no structural link between "retrieval was incomplete" and "this must not be
scored".

For a library whose entire premise is not being misread, **0.48 read as weak
clearance evidence when the truth is "no answer" is the most consequential
misuse route found so far** — worse than the rug-alarm inversion ADR-001
guards against, because it requires no misuse at all, only a partial fetch.

**Decision.** An unscoreable pool must be **structurally incapable of
returning a clearance score**. The verdict type must be able to express "no
answer", and the required feature set must be checked before the booster is
consulted, so a sentinel-only row cannot reach it. Retrieval completeness is
part of scoreability: a fetch reporting `reached_t0=False` is a corrupted
partial (ADR-002) and must not be scoreable either.

**Consequences.** This changes the `Clearance` field set, which ADR-001 pins
deliberately and `tests/test_honesty.py` asserts exactly — so it is an
ADR-level decision made consciously, which is why it is recorded here rather
than applied as a drive-by edit inside a validation stage. The honesty tests
must be extended in the same change: an unscoreable input returning a number
should break the build, exactly as a rug-detection-shaped name does. The new
field must not read as danger (ADR-001's forbidden-name scan still applies),
which points at a name describing *evidence sufficiency* rather than risk.

## ADR-006: The verdict is Clearance or Unscorable; a refusal carries no number

**Date:** 2026-08-13 · **Status:** accepted · implements ADR-005, extends ADR-001

**Context.** Stage B measured the hazard (ADR-005): `clearance(pool, {})`
returned `cleared=False, clearance_score=0.4815` — every absent feature became
the trained −1.0 sentinel, the model scored the sentinel row, and a caller
read a number where the truth was "no answer". ADR-001 pins the `Clearance`
field set deliberately, so closing this required an ADR-level contract change,
which the Stage C brief sanctioned as the operator decision ADR-005 deferred.
The change was registered before it was implemented: the refusal semantics
were committed as strict-xfail assertions (Stage C Task 0, e38b185) that the
implementation then made true.

**Decision.** `clearance()` returns `Clearance | Unscorable`. `Unscorable` is
a frozen dataclass pinned to exactly `{pool, reason, missing, calibration}` —
**no `clearance_score`, no `cleared`** — so mistaking a refusal for a low
clearance is a type error, not a misreading. `reason` ∈ `missing_features` /
`retrieval_incomplete` / `parse_incomplete`. The refusal boundary is
**absent-or-None**: an explicit −1.0 float passes through as the model's
trained missing-encoding, because the sentinel collides with legitimate
negative `creator_time_to_first_sell_s` values in real snapshot rows, and the
live path never fabricates it (an unavailable live feature is None).
`solclear.pipeline.score_pool` is the only sanctioned path from a retrieved
window to a verdict: it refuses `reached_t0=False` (a corrupted partial,
ADR-002) and any unparseable-transaction count before features are computed.
The credit-gate refusal (`CreditCapError` before any request) remains a
separate exception — a budget fact, not a scoring fact. The honesty tests pin
the `Unscorable` field set exactly as they pin `Clearance`'s, assert an
unscoreable input returns no number, and scan `pipeline` for
detection-shaped names.

**Consequences.** Callers must narrow the union before touching a score,
which is the point: the most consequential misuse route Stage B found — a
truncated fetch or empty mapping read as weak clearance — is now closed by
the type system rather than by documentation. The cost is that snapshot rows
whose own features are absent-encoded refuse under the live contract; the
Stage C registration classifies live-refusal-on-snapshot-absent as agreement,
not mismatch.

## ADR-007: T0 is per-path — a first-party observation live, an external claim retrospectively, and the snapshot's basis is token launch, not pool creation

**Date:** 2026-08-13 · **Status:** accepted

**Context.** ADR-004 named T0 acquisition as the question preceding the rest
of the live path. Stage C built two paths: the scanner's (`LiveT0Source`,
interface only — creation observed as it happens, first-party, free) and the
retrospective resolver (GeckoTerminal token→pools, earliest
`pool_created_at`, keyless). Stage C.1 measured the claim against on-chain
first pool activity on six 2024 pools: **median −1 s, range [−27, 0]** —
accurate to seconds. The same run's KAT then found that accuracy answers the
wrong question for the snapshot: three of four snapshot
`creator_time_to_first_sell_s` values are *negative* and one snapshot window
saw 0 holders where the pool-creation window holds 1,049 events, so the
parent project anchored its feature windows at **token launch**
(mint/bonding start, which FINDINGS.md §3 already noted predates the pool),
not at pool creation.

**Decision.** T0 is typed and treated per path. Retrospective T0 is a
`T0Claim` — stamped with source, URL, and retrieval time, never trusted
untested (its tolerance is a measured quantity). Pool-creation T0 is the
correct anchor for **scoring a pool at launch going forward** and for any
claim about the pool itself. It is the **wrong basis for reproducing the
committed snapshot**, whose windows are token-launch-anchored; the
retrospective KAT therefore stands blocked until a token-launch T0 source is
built and measured (candidate: paging the mint backward from the pool
anchor, cost O(bonding history) — priced before trusted, like everything
else). Neither the scorer's holdout figures nor Method B is touched by this;
the live scanner is untouched because it observes the true launch
first-party.

**Consequences.** No retrospective clearance may be represented as a
snapshot reproduction until the basis matches. The KAT's zero genuine
mismatches on basis-independent fields (authority 4/4, token-security 16/16)
plus systematic divergence on window-derived fields is the measured evidence
this split is real rather than a modeling excuse.

## ADR-008: Enhanced pricing is measured — the boundary is 100/call, and the cost lever is scope, never depth

**Date:** 2026-08-13 · **Status:** accepted

**Context.** The gate priced `enhanced` at the vendor's published 100/call
before the client existed (Stage C Task 2). Stage C.1 measured the batch
semantics with real signatures: 100 accepted, **101 → HTTP 400** — the
boundary is exactly the documented 100. No response carries credit/usage
headers, so per-call billing stays vendor-documented and the ledger's raw
counts remain the only reconciliation path (ADR-003 confirmed again).
Measured per-pool enhanced cost over seven launch windows spanning
83–9,808 signatures: **typical ≈ 1,400 credits, conservative ≈ 2,000,
extreme 9,900 — 35–260× the ~38-credit retrieval floor.** Against the
pre-registered thresholds: the free tier is dead for any enhanced-bearing
scan; Developer $49 survives only graduations at the 80/day band; Business
$499 covers graduations and AMM-only at typical cost; the full feed exceeds
Professional.

**Decision.** Per-pool enhanced cost is `100 × ceil(window_sigs / 100)` and
every pool's whole sweep is priced against its budget **before its first
call** (the Stage C.1 run skipped three pools this way rather than
overrunning — the discipline is now precedent, not aspiration). Because
ADR-006 makes truncation refuse, **cost cannot be reduced by fetching part
of a window**: the only honest lever is which pools to score, never how much
of each window to read. The tier decision belongs to Stage D and must be
made from these measured numbers.

**Consequences.** Scanner economics are now a scoping decision with measured
prices attached. Any future proposal to "sample" a window's transactions is
a proposal to un-do ADR-006 and must be argued as such, in an ADR, not
slipped in as an optimization.

## ADR-009: The parse event vocabulary, with direction judged relative to the pool

**Date:** 2026-08-13 · **Status:** accepted

**Context.** ADR-004's second missing link: nothing converted enhanced
payloads into `features.Tx`. The vocabulary any conversion chooses IS the
feature semantics, so it is recorded here rather than only in docstrings.

**Decision.** Relative to scored mint M and launch pool P: `mint_to` = a
token transfer of M with no sender (creation); **`sell` = M flowing INTO P,
by the sender — direction is judged relative to the pool**, whatever the
counter-asset did; buys (M out of P) are `transfer` events with
`source = P`, so pool-funded buyers can never enter the creator-funded
insider set; wallet-to-wallet movements of M are `transfer` with the sender
as source; `revoke_authority` = a SET_AUTHORITY payload referencing M, with
its stated approximation (an authority *transfer* would also match — the
feature is binary presence and the approximation is recorded, not hidden).
Every payload lands in exactly one of parsed / ignored (understood,
deliberately no event) / unparseable, and **any unparseable count refuses
scoring** (ADR-006). The leakage suite runs through the parse: prefix
invariance plus a planted canary that clamps out-of-window timestamps
inward — the realistic leak shape, since `features()` re-clamps its own
window and mere inclusion cannot leak.

**Consequences.** First live contact measured **0 unparseable across 2,758
real payloads** (1,561 parsed, 1,197 understood-ignored), so the vocabulary
covers the wild shapes seen so far; the day it meets one it does not
understand, the answer is a refusal and a vocabulary extension reviewed
against this ADR — never a silent drop.

## ADR-010: The snapshot's basis, resolved from the parent's own code — ADR-007's token-launch hypothesis is superseded

**Date:** 2026-08-13 · **Status:** accepted · supersedes the basis hypothesis in ADR-007

**Context.** ADR-007 inferred token-launch anchoring from the snapshot's
negative TTFS values. Stage D Task 1 read the parent instead of inferring:
`research/detection/labels.py:81` sets
`first_ts=_ts(row.get("FIRST_POOL_ACTIVITY_TIMESTAMP"))` — SolRPDS's
first-recorded pool activity — and the C.22 report fixes the fetch window
verbatim: *"filtering signatures whose blockTime lands in [T0−60s,
T0+1800s]"*. The negative TTFS values (−58, −30, −1) all sit inside the
**60-second pre-roll**; no token-launch anchoring is needed to explain them,
and the hypothesis is refuted. Measured per mint against GeckoTerminal's
pool creation on all 10 checked 2024 mints: **SolRPDS's T0 lags true pool
creation by +18 minutes to +13.3 days** — an indexing artifact of the
dataset, heterogeneous per pool, not a semantic anchor. That lag is why
Stage C.1's pool-creation windows saw launch storms (1,466–9,808
signatures) where the parent's windows were nearly empty (1–1,123 on the
same mints): the parent's windows started after the rush.

**Decision.** The snapshot's basis is recorded as **SolRPDS
first-recorded-activity with a 60 s pre-roll**, and the parent's exact
per-mint T0 is recoverable at zero credits from the SolRPDS CSVs archived in
the parent repository (`data/vendor/archive/solrpds/`, read-only). Any
retrospective KAT reconciliation must anchor there — not at token launch,
not at pool creation. ADR-007's resolver-accuracy measurement stands
unchanged; only its basis hypothesis is superseded.

**Consequences.** The retrospective KAT is unblocked in principle (the
anchor is obtainable and free), but the training windows are now known to
be **lag-heterogeneous** — each starts at whatever moment SolRPDS first
indexed the pool — which is a property of the training data worth knowing
before any recalibration argument, and it travels here rather than in a
footnote. Mint-creation recovery, for completeness (Stage D Task 2,
measured): DAS `getAsset` returns no creation-time field (10 credits/call,
flat), and from-now signature paging reaches the mint's oldest signature
only on shallow histories (1 of 6 inside a 15-page cap; cost scales with
post-launch depth — the from-now pathology of ADR-002). Neither route is a
usable token-launch T0 source, and per this ADR none is needed.

## ADR-011: The scanner anchors at pool creation; calibration transfer stays an open, measured question

**Date:** 2026-08-13 · **Status:** accepted

**Context.** The Stage D registration fixed a materiality rule for whether
the pool-creation and parent anchors are interchangeable, with minimum
decision coverage of 4 of 6 pools. The measured coverage was **2 of 6** —
the four other pairs priced 2,000–11,100 enhanced credits and were skipped
by the sub-budget before any call — so the rule's formal decision is
**withheld per the registration**. What the two measured pairs show, both:
7/10 features in-band (aggregate 70% against the registered 90%), with the
out-of-band fields the same window-derived trio each time
(`creator_allocation_t0`, `top5_concentration_wend`, `n_early_holders`) and
different derived creators per anchor. Combined with the window-population
evidence (parent windows 1–1,123 signatures vs pool windows 1,466–9,808 on
the same mints), the anchors demonstrably select different event sets. The
evidence points DISTINCT; the registered bar simply wasn't allowed to rule
on 2 pairs.

**Decision.** The forward scanner **anchors at pool creation** — the only
instant observable first-party and live, measured accurate to seconds
(ADR-007). But the model's holdout calibration (0.984/0.538) **must not be
represented as transferring to pool-creation windows**: until either the
materiality question closes on ≥ 4 pairs (the two cheapest unmeasured pairs
priced ~2,000 and ~2,300 enhanced — a deliberate future spend) or Stage E
accumulates its own forward outcome data, a pool-creation-window clearance
is reported as *anchor-shifted* alongside the calibration statement. Stage
E's design therefore: observe and score at pool creation, retain each
window's raw artifacts so parent-basis re-scoring stays possible, and let
the forward cohort's realized outcomes stand in for the calibration the
snapshot cannot provide on this anchor. This fits the operator's ~two-week
constraint because outcome accrual starts immediately rather than waiting
on the basis question.

**Consequences.** No score ships on an anchor the model never saw without
saying so on the object itself; the cost is one more caveat travelling with
early Stage E output, which is exactly the honesty the scope statement
demands.

## ADR-012: Measured absence encodes to the trained sentinel; only source unavailability refuses

**Date:** 2026-08-14 · **Status:** accepted · refines ADR-006's boundary at the pipeline

**Context.** ADR-006 made the scorer refuse any absent-or-None required
feature. Stages C.1 and D then measured the consequence on real
pool-anchored windows: every scored pool refused on
`creator_time_to_first_sell_s = None` — because the creator *did not sell*
inside a complete window. That is not missing data; it is a measurement
whose value is "no event". The parent's own encoder settles how such values
were trained: `train.py` maps empty cells to the −1.0 MISSING sentinel, and
the committed snapshot carries −1.0 rows for `creator_allocation_t0` and
`top5_concentration_wend` — the model was *trained on* sentinel-encoded
measured absence. Refusing it live is a semantic misclassification that
would refuse most of any real cohort (C.1: 4 of 4) and make Stage E's
registered yield expectation unreachable for a reason that has nothing to do
with pools. Decided in the Stage E Task 0 registration, before any
enumeration or outcome was seen.

**Decision.** In `pipeline.score_pool`, once both completeness gates have
passed (retrieval reached T0; the parse accounted for every payload), a
window-derived feature that is None is a **measured absence** and encodes to
the trained −1.0 sentinel before scoring. **Source unavailability still
refuses, unchanged**: `reached_t0=False`, any unparseable payload, and a
vendor (token-security) None all remain `Unscorable` — those are absent
*data*, not measured absence. The scorer-level boundary of ADR-006 is
untouched: a caller passing an incomplete mapping still gets a refusal,
because the scorer cannot see completeness; only the pipeline, which can,
is entitled to encode.

**Consequences.** An empty-but-complete window now scores as the trained
all-sentinel row (the same encoding the holdout contains) instead of
refusing — the refusal tests are updated deliberately in the same commit,
with the vendor-None refusal pinned alongside. The hazard ADR-005 closed
stays closed: a truncated fetch, a lossy parse, or a missing vendor read
still cannot produce a number.

## ADR-013: The outcome-basket rules, registered before enumeration, with the venue-migration nuance stated

**Date:** 2026-08-14 · **Status:** accepted

**Context.** Stage E needed basket rules that could not be tuned after
outcomes were seen. They were registered in the Task 0 commit (8a49833)
before any enumeration: entry at the day-0 candle close (the first mark
available after a score exists); equal weight; exit at horizon (30/90 d);
and the death rule — no candle in the 14 days ending at the horizon, or an
exit mark below 1% of entry, books **−100%**, because a dust close has no
exit liquidity and marking to it manufactures an unrealizable recovery.
Dead pools stay in their baskets.

**Decision.** These rules are the standing outcome-measurement contract.
One mis-specification surfaced and is recorded rather than patched
silently: on launch venues (bonding curves), *graduation* moves liquidity
to a new pool address and would read as death under the rule. Stage E
audited every launch-venue position keylessly (pump.fun graduation state):
**0 of 35 had graduated**, so the registered-rule numbers stand unmodified
for that cohort. Any future cohort containing launch-venue positions must
stitch the price series across graduation (curve candles then AMM-pool
candles) before applying the death rule — declared here, in advance, as
the rule's v2.

**Consequences.** Outcome numbers are comparable across stages because the
rules cannot drift quietly; the migration audit is now a required step for
any launch-venue cohort.

## ADR-014: The execution-cost model — 450 bps round trip central, and at measured death rates it does not matter

**Date:** 2026-08-14 · **Status:** accepted

**Context.** Both predecessor trading projects died partly on unmodelled
execution. External evidence puts all-in Solana memecoin round trips near
300–600 bps (bot fees, priority fees, slippage, sandwich exposure).

**Decision.** Registered central figure **450 bps round trip, charged
225 bps per leg** on every memecoin leg of every basket (cleared,
not-cleared, random alike), with 300 and 600 bps sensitivity bounds; gross
and net always reported side by side; a death position nets exactly −100%
(cost cannot deepen a total loss beyond the stake); holding SOL — the
operator's benchmark — carries no memecoin cost.

**Consequences.** Stage E measured the model's own relevance: with the
cleared basket at −100% and the not-cleared median at −100%, the 300 vs
600 bps sensitivity moved nothing — execution cost is immaterial at these
death rates and cannot be blamed for the negative result. The model stays
in force for any future cohort where survival rates make it bind.

## ADR-015: The project closes as a documented public artifact; reopening requires a different population, not a different model

**Date:** 2026-08-14 · **Status:** accepted · closes the project

**Context.** Stage E asked the question this project existed to reach — does a
cleared basket beat holding SOL — and answered it negatively on a
pre-registered 77-pool cohort: **every one of the 18 cleared pools realized
−100% at both horizons**, with every comparison at p_raw = 1.0 in the adverse
direction and the registered underpowered rule fired. The mechanism was
identified and is structural rather than incidental: hard-rug clearance does
not contain the does-it-even-graduate question, and a birth-ordered
pool-creation feed is dominated by pre-graduation bonding curves that die at
~97.5% within 30 days regardless of any launch-window score. The scorer
detects hard rugs on the population it was trained on; it does not select
things that go up.

Two options existed. Continue — build a graduated/AMM-population scanner,
close the ADR-011 materiality question at ~4,300 enhanced credits, extend the
parse vocabulary for SPL `BURN` — or stop and ship what was measured. The
measurements do not need any of that work to be true, and none of it would
change the negative already recorded; it would only produce a second cohort.

**Decision.** The project is **closed as a documented public artifact**. Stage
F built no new capability and spent no credits. What it did instead:

1. **The negatives lead.** README.md opens with what the tool answers and what
   it does not, and carries the two results a cold reader must have before any
   capability description — ADR-011's anchor shift (live scores do not inherit
   the 0.984 figure) and Stage E's outcome. FINDINGS.md carries every claim
   with its sample size in the same sentence as its number.
2. **The negatives are load-bearing in the build.** `tests/test_honesty.py`
   now pins the Stage E result and the ADR-011 anchor-shift statement in
   **both** README.md and FINDINGS.md, alongside the existing scope pins, with
   a canary asserting the presence-checker itself fires. Deleting a negative
   breaks the build exactly as a rug-detection-shaped name does — a future
   reader, or a future session, cannot quietly remove what makes the tool
   honest.
3. **Method B is documented as a standalone reusable component**
   (`METHOD_B.md`), because it is the piece most useful to anyone else and its
   justification is a correctness argument, not a performance one.
4. **MIT licensed** (`LICENSE`), with the not-financial-advice statement
   attached to the licence itself, and `pyproject.toml` metadata corrected
   from `Proprietary` to match. Installation, a minimal usage example, and the
   full suite were verified from a clean checkout.
5. Two smaller items were fixed rather than left for a reader to discover: a
   blank `SOLCLEAR_HELIUS_API_KEY` now counts as absent (copying
   `.env.example` to `.env` and running previously produced `SecretStr('')`
   and unauthenticated requests instead of the promised fail-fast), and
   FINDINGS.md's section numbering changed, so the old→new map is recorded in
   that file's header because this log is append-only and cites it by number
   (ADR-002's "§5" is unchanged; ADR-010's "§3" is now §8).

**The reopening condition, stated so it is not mistaken for pessimism.** The
outcome question reopens on a **genuinely different population** — graduated
or AMM pools carrying real liquidity, enumerated without survivorship bias —
**not on a different model**. Stage E's own crawler-bias measurement (97.5%
birth-ordered vs 18.75% attention-crawled 30-day death, a 60–79 point gap)
shows why the enumeration is the hard part and why it must come first: a
cohort built from archived or listed coins would manufacture a decent-looking
basket out of selection bias alone. Any successor that cannot enumerate births
unbiased should not run the study at all. Retuning thresholds, adding
features, or swapping the estimator addresses none of this, and would produce
a better-looking number on the same broken population.

**Consequences.** The repository ships one measured capability, a set of
measured negatives, and no promise it did not test. Nothing is left in a state
where a future reader could mistake an unfinished path for a working one: the
behavioural signal stays not shipped (+0.032, CI includes zero), the ADR-011
materiality question stays open with its price attached (~4,300 enhanced
credits for the two cheapest pairs), and the SPL `BURN` vocabulary gap stays
recorded as a correct refusal rather than patched under a closing commit. The
cost of closing here is that the graduated-population question goes
unanswered; the cost of not closing would have been shipping a second cohort
as though it were a different answer.
