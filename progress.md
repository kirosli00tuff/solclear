# progress.md — running log

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
