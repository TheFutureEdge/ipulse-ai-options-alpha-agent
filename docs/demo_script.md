# Three-Minute Demo Script

## 0:00-0:25 - The problem

Trading agents are easy to make active and hard to make accountable. iPulse AI
Options Alpha Agent makes every signal, rejection, risk decision, order, and
result inspectable.

## 0:25-0:55 - Real Alpaca evidence

Show the sanitized account status, then run `evaluate-advisors-market`. Point
out that the agent reads real SPY bars, quotes, portfolio and recent-order state,
a narrow options chain, and hashed external research evidence.

## 0:55-1:30 - Independent research

Show all six opinions. Highlight the financials forensic auditor, value
framework, cited evidence, contrary evidence, and invalidation conditions.
Explain that missing coverage produces ABSTAIN and hard safety flags produce
WAIT.

## 1:30-2:05 - Risk authority

Show consensus disagreement handling, paper-only enforcement, quote freshness,
duplicate protection, cooldown, long-premium rule, one-contract cap, USD 500
maximum loss, daily loss circuit breaker, and position cap. Run one deliberately
oversized test and show REJECT.

## 2:05-2:35 - Paper execution

During market hours, enable the explicit paper switches and run
`run-paper-once`. Re-read the limit order from Alpaca and show the matching
client order ID and sanitized broker status.

## 2:35-3:00 - Inspectability

Open the JSONL evidence trace. Close with: the AI proposes, deterministic risk
decides, Alpaca executes, and the evidence remains inspectable. Then open the
generated `latest_decision.html` report to show the same trace in a judge-friendly
view.

On-screen footer: Research and simulated paper trading only. Not investment
advice.
