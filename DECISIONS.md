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
