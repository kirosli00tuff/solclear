# progress.md — running log

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
