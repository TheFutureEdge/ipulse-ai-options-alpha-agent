# Final submission package

Prepared: 4 September 2026

Submission status: **successfully submitted and publicly verified**

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

iPulse AI Options Alpha Agent makes options research and Alpaca paper trading
inspectable. It solves AI-trading governance: can a team reconstruct why capital
moved?

Six independent advisors analyze technical regime, news, options liquidity,
financial quality, value, and risk. Each records evidence, contrary evidence,
confidence, and invalidation. AI proposes CALL, PUT, WAIT, or ABSTAIN;
deterministic policy alone authorizes execution.

Using Alpaca's official MCP server, the agent reads a dedicated paper account,
SPY/QQQ/IWM bars, quotes, and option chains. A near-0.50-delta contract is
considered only after the frozen rule qualifies. Paper-only, session, freshness,
duplicate, cooldown, position, drawdown, and sizing gates fail closed. Orders are
one-contract, long-premium limits with at most USD 500 defined loss; the broker
is re-read and a sanitized receipt retained.

Three exploratory v0 paper fills—AAPL, XLF, and AMZN calls—prove the bounded
broker path. Combined maximum premium risk was USD 825; the captured mark showed
USD 99,986.91 equity and -USD 13.09 P&L. We publish the loss and do not claim v1
performance.

We also publish a failed momentum v0 strategy. Exhaustion-reversal v1 was
selected on 2021-2023 development data, frozen, then tested on untouched
2024-2026 data: 127 signals, 55.9% directional wins, +0.218% average signed
two-session underlying move, 1.39 profit factor, and a 0.88 event-frequency
Sharpe proxy. Its 95% Wilson interval is 47.2%-64.2%. These are underlying
diagnostics, not option returns.

The commercial wedge is evidence-governed research for U.S. advisers. The SEC
reports 22,932 investment advisers and USD 177T regulatory AUM in 2025. Team
SaaS, enterprise private deployment, and an evidence API provide revenue paths.

Judges can inspect the deployed dashboard, MIT repository, 59 tests, full
ledger, 4:54 demo, ten-slide deck, and latest frozen WAIT. No raw account ID or
credentials appear publicly. Paper only; not investment advice.

## Classification

- Category: Finance
- Technology: Alpaca

## Public links

- Repository: https://github.com/TheFutureEdge/ipulse-ai-options-alpha-agent
- Hosted judge dashboard: https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/
- 4:54 judge demo: https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/ipulse-options-alpha-agent-judge-demo-v03.mp4
- Ten-slide judge deck: https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/2026-09-04_ipulse-ai-options-alpha-agent_judge-deck_v06.pdf
- Team page: https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon/ipulse-ai-open-lab
- Published submission: https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon/ipulse-ai-open-lab/ipulse-ai-options-alpha-agent

## Additional information

Judge path: 1) watch the 4:54 video; 2) open the dashboard; 3) inspect six
advisor views, dissent, and the safety replay; 4) compare broker proof with the
frozen holdout; 5) review the MIT repository, 59 tests, and scored ledger.

Why it matters: investment teams cannot govern black-box agents. iPulse AI makes
the chain reconstructable. Technical regime, news catalyst, options liquidity,
financials forensic audit, value framework, and risk critic each cite evidence,
contrary evidence, confidence, and invalidation. Consensus may propose CALL,
PUT, WAIT, or ABSTAIN. AI synthesizes uncertainty; code controls capital.

Safety is fail-closed: Alpaca paper only, open session, fresh quote, complete
broker state, duplicate/idempotency protection, cooldown, position and drawdown
limits, one contract, long premium, limit order, and USD 500 max loss. Orders
are re-read from Alpaca and retained as sanitized receipts.

We separate evidence types. Three exploratory v0 paper fills in AAPL, XLF, and
AMZN prove the bounded broker path. Combined maximum premium risk was USD 825;
captured P&L was -USD 13.09. We publish the loss and make no v1 performance
claim. Momentum v0 failed and remains public. Exhaustion-reversal v1 was selected
on 2021-2023 development data, frozen, then tested on untouched 2024-2026 data:
127 signals, 55.9% directional wins, +0.218% average signed two-session
underlying move, 1.39 profit factor, and a 0.88 event-frequency Sharpe proxy.
These are underlying diagnostics, not option returns. The latest v1 scan
produced WAIT and no order.

Business wedge: evidence-governed research for U.S. adviser teams. SEC 2025
statistics report 22,932 advisers and USD 177T regulatory AUM. Team SaaS,
enterprise private deployment, and a usage-based evidence API are the revenue
path.

Final release: commit f1830d9, deployed dashboard, captioned demo, ten-slide
deck, sanitized evidence, and source. No public credentials or raw account ID.
Paper only; not investment advice.

## Private judging field

The dedicated Alpaca paper account ID must be entered only in Lablab's private
judging field. It must not appear in the repository, dashboard, video, deck, or
social posts.

## Final disclosure

This is a research and simulated paper-trading project, not investment advice.
Paper fills and historical directional diagnostics do not establish live
profitability or predict future returns.
