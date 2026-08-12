# progress.md — running log

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
