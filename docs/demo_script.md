# Three-Minute Demo Script

## 0:00-0:25 - The problem

Trading agents are easy to make active and hard to make accountable. iPulse AI
Options Alpha Agent makes every signal, rejection, risk decision, order, and
result inspectable.

## 0:25-0:50 - Real Alpaca evidence

Show the competition panel: dedicated paper account, USD 100,000 starting
equity, three filled long-premium option orders, and no exposed account ID. Then run
`evaluate-advisors-market`. Point out that the agent reads real SPY bars,
quotes, portfolio and recent-order state, a narrow options chain, and hashed
external research evidence.

## 0:50-1:25 - Independent research

Show all six opinions. Highlight the financials forensic auditor, value
framework, cited evidence, contrary evidence, and invalidation conditions.
Explain that missing coverage produces ABSTAIN and hard safety flags produce
WAIT.

## 1:25-1:58 - Risk authority

Show consensus disagreement handling, paper-only enforcement, quote freshness,
duplicate protection, cooldown, long-premium rule, one-contract cap, USD 500
maximum loss, daily loss circuit breaker, and position cap. Run one deliberately
oversized test and show REJECT.

## 1:58-2:30 - Paper execution

Show the three retained paper receipts: AAPL, XLF, and AMZN calls, one contract
each, all limit orders. Reconcile the USD 825 combined premium paid with the
same USD 825 maximum defined premium risk. Explain that the three-entry daily
cap is now binding, so the agent cannot keep trading for a prettier demo.

## 2:30-3:00 - Inspectability and scorecard

Open the JSONL evidence trace and the public dashboard performance panel. Show
starting equity, current equity, paper P&L, fills, and rejected/canceled orders.
Then show the frozen 2024-2026 holdout: 127 signals, 55.9% win rate, +0.218%
average signed underlying move, 1.39 profit factor, and the explicit warning
that these are not option returns. Close with: the AI proposes, deterministic
risk decides, Alpaca executes, and the evidence remains inspectable.

On-screen footer: Research and simulated paper trading only. Not investment
advice.

## Recording gate

- Record only after the repository and dashboard URLs work in a signed-out
  browser.
- Use 1920x1080 capture, readable terminal zoom, and no notification overlays.
- Never show credentials, raw account identifiers, environment files, or
  private iPulse AI data.
- Put repository, hosted demo, and one-page links in the video description.
- Export a public, unlisted-or-public URL that opens without authentication.
