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
