# Final submission package

Prepared: 4 September 2026

## Deadline

- Official event end: 4 September 2026 at 15:00 UTC
- Dubai equivalent: 4 September 2026 at 19:00 Gulf Standard Time
- Internal submission target: as soon as the final Lablab confirmation is given

## Basic information

**Submission title**

iPulse AI Options Alpha Agent

**Short description**

Inspectable six-advisor options research with deterministic risk gates,
broker-verified Alpaca paper fills, and honest out-of-sample validation.

**Long description**

Most trading-agent demos optimize for activity. iPulse AI Options Alpha Agent
optimizes for falsifiable, inspectable decisions. Six independent advisors
examine technical regime, news, options liquidity, financial quality, value,
and risk. Each records evidence, dissent, confidence, and invalidation. AI may
propose; deterministic safety alone authorizes execution.

The agent connects through Alpaca's official MCP server, reads a dedicated paper
portfolio, scans SPY, QQQ, and IWM, and selects a liquid near-0.50-delta option
only after the frozen rule qualifies. It permits only one-contract, long-premium
limit orders with at most USD 500 defined loss. Paper-only switches,
market-hours, quote-freshness, duplicate, position, and drawdown gates fail
closed to WAIT or REJECT.

Alpaca broker-verified three exploratory v0 buy-to-open paper fills: AAPL, XLF,
and AMZN calls. Their combined premium and maximum risk was USD 825, 0.825% of
starting equity. The captured mark showed USD 99,986.91 equity and -USD 13.09
P&L. We publish the loss rather than hide it. Those fills prove bounded paper
execution, not strategy profitability.

We also publish failed research: momentum v0 did not survive validation. A frozen
exhaustion-reversal challenger, selected only on 2021-2023 development data, was
evaluated on untouched 2024-2026 data: 127 signals, 55.9% wins, +0.218% average
signed two-session underlying move, 1.39 profit factor, and a 0.88
event-frequency-adjusted Sharpe proxy. Its 95% Wilson win-rate interval is
47.2%-64.2%. A non-overlapping audit retained 81 signals, with 56.8% wins and
1.87 profit factor. These are underlying-direction diagnostics, not options
P&L; spreads, decay, fees, and slippage are excluded.

Judges can inspect the public code, 59 passing tests, complete scored outcomes,
sanitized broker receipts, dashboard, video, and seven-slide deck. The project
is MIT licensed, Alpaca paper-only, and not investment advice.

## Classification

- Category: Finance
- Technology: Alpaca

## Public links

- Repository: https://github.com/TheFutureEdge/ipulse-ai-options-alpha-agent
- Hosted judge dashboard: https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/
- 49-second demo: https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/ipulse-options-alpha-agent-49s-pitch.mp4
- Seven-slide judge deck: https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/2026-09-03_ipulse-ai-options-alpha-agent_judge-deck_v02.pdf
- Team page: https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon/ipulse-ai-open-lab

## Private judging field

The dedicated Alpaca paper account ID must be entered only in Lablab's private
judging field. It must not appear in the repository, dashboard, video, deck, or
social posts.

## Final disclosure

This is a research and simulated paper-trading project, not investment advice.
Paper fills and historical directional diagnostics do not establish live
profitability or predict future returns.
