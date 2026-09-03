# Alpaca hackathon submission runbook

## Hard deadline

- Hackathon: 28 August–4 September 2026
- Submission closes: Friday, 4 September 2026 at 19:00 Gulf Standard Time
- Internal content freeze: Thursday, 3 September at 19:00 GST
- Internal submission target: Friday, 4 September at 16:00 GST

## Eligibility baseline

- Team: iPulse AI Open Lab
- Challenge: Options Alpha Agents
- Dedicated Alpaca paper account: created 28 August 2026
- Starting balance: $100,000
- Account status: active
- Options trading level: 3
- Initial positions and fills: zero
- Connectivity evidence: one canceled, deliberately non-marketable equity smoke
  order; it did not fill or change the starting balance
- Public artifacts must never expose credentials or raw account identifiers
- The raw Alpaca paper account ID is entered only into Lablab's required judging
  field

Run `competition-status` before and after every paper session. It fingerprints
the account, verifies the paper/options/$100,000 baseline, and records equity,
P&L, positions, orders, and fills without retaining the raw account number.

## Required submission matrix

| Requirement | Evidence | Release gate |
| --- | --- | --- |
| Autonomous AI trading agent | Bounded multi-cycle runner and append-only cycle journal | Rehearsal completes without bypassing WAIT or risk vetoes |
| Alpaca Trading API | Account, clock, market, options, order and performance calls | Sanitized trace visible in demo |
| Alpaca MCP or CLI | Official Alpaca MCP stdio client and tool receipts | MCP tool inventory and one verified order receipt |
| Options trading | Long-call/long-put contract selection and paper execution | At least one strategy-generated options order if market evidence approves it |
| P&L performance | Dedicated account performance journal | Starting balance, current equity and return reconcile to Alpaca |
| AI logic/risk/infrastructure | One-page write-up | Matches running code and names all deterministic gates |
| Public repository | MIT-licensed GitHub repository | Clean clone passes tests and contains no secrets/artifacts |
| Demo application | Hosted inspectable HTML dashboard | Public URL loads on desktop/mobile and is indexable |
| Presentation | Cover image, slides and video | Links work without authentication |
| Social engagement | Up to five X/LinkedIn posts tagging both partners | Every submitted link is public and opens correctly |

## Build and competition sequence

### 28 August — baseline and kickoff

1. Preserve the dedicated account; do not reset or reuse it elsewhere.
2. Capture the sanitized baseline and build the public report.
3. Attend the kickoff/Discord Q&A and record any rule clarifications.
4. Run read-only market evaluations before enabling paper execution.

### 29–31 August — evidence and paper performance

1. Rehearse one-cycle execution during regular US market hours.
2. Start only finite autonomous sessions; retain advisor, veto, order and fill
   evidence.
3. Capture competition status after each session.
4. Review P&L, spread, stale-data, daily-trade and drawdown gates daily.
5. Publish build-in-public posts covering architecture, evidence, a rejected
   trade, a completed trade, and final results.

### 1 September — feature freeze

1. Freeze the strategy and risk policy; permit only defect fixes afterward.
2. Run a clean-clone test and secret scan.
3. Reconcile every public claim against the journal and Alpaca account.

### 2 September — presentation package

1. Finalize the hosted dashboard and stable application URL.
2. Record the demo path: account baseline, live evidence, six advisors,
   consensus, deterministic veto, order receipt, and P&L.
3. Finish cover image, slides, one-page write-up and video.

### 3 September — submission rehearsal

1. Freeze content at 19:00 GST.
2. Complete every Lablab field without final submission.
3. Test repository, demo, video, slides and all social links in a signed-out
   browser.
4. Reconcile the exact paper account ID and final performance snapshot.

### 4 September — final audit and submission

1. Capture the last performance snapshot and rebuild the dashboard.
2. Run the complete test suite, secret scan and clean-clone install.
3. Confirm originality, MIT compatibility and paper-only disclosures.
4. Submit by 16:00 GST, preserving a three-hour buffer.
5. Save the submission confirmation page and final URLs.

## Never-do list

- Never point the runtime at a live Alpaca environment.
- Never place an order when evidence is stale, the market is closed, broker
  state is incomplete, consensus is misaligned, or a deterministic gate vetoes.
- Never reset the competition account after performance has begun.
- Never expose API keys, raw account identifiers, private iPulse datasets, or
  production credentials in the repository, dashboard, video, slides, or posts.
- Never claim live-trading performance or imply paper results guarantee returns.
