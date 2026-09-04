# iPulse AI Options Alpha Agent

## AI logic, risk gates, and Alpaca infrastructure

**Category:** autonomous options paper-trading agent
**Positioning:** inspectable multi-advisor research with deterministic execution
authority
**Environment:** Alpaca paper trading only

### The buyer and business value

The starting users are U.S. investment-adviser research teams, family offices,
and sophisticated investment teams that want AI-scale evidence synthesis without
allowing a probabilistic model to control capital. The U.S. SEC reports 22,932
investment advisers and USD 177 trillion in regulatory assets under management
for 2025. At an explicit, illustrative USD 12,000 annual contract assumption,
that implies a roughly USD 275 million U.S. software opportunity. This is an
assumption for market framing, not a forecast.

The commercial path combines team SaaS, private enterprise deployment with
firm-specific risk policies, and a usage-based evidence API. AI is essential for
interpreting heterogeneous market, news, financial, valuation, and contrary
evidence; deterministic software remains essential for capital control.

### The problem

Many trading-agent demonstrations optimize for activity. That makes them easy to
watch and difficult to audit. iPulse AI Options Alpha Agent treats a rejected
trade or a decision to WAIT as useful evidence. A judge can inspect what the
agent saw, how its advisors disagreed, which rules were applied, and what Alpaca
accepted or rejected.

### Autonomous decision loop

Each bounded cycle reads the Alpaca paper account, market clock, recent orders,
positions, daily bars, stock quote, news, and a narrow option-chain snapshot.
Strict adapters can add fresh iPulse AI financial, fund-structure, and relative-
value evidence. Every input is normalized and given a stable evidence ID.

Six independent advisors then return a typed CALL, PUT, WAIT, or ABSTAIN view:

1. **Technical regime** checks fast and slow price direction and volatility.
2. **News catalyst** scores recent, symbol-matched news and contrary evidence.
3. **Options liquidity** checks spread, open interest, delta, expiry, and loss.
4. **Financials auditor** tests cash conversion, accruals, leverage, dilution,
   restatements, auditor opinion, or ETF fund structure.
5. **Value framework** tests margin of safety and peer-relative valuation.
6. **Risk critic** challenges market state, stale inputs, broker state, and
   portfolio limits.

Every advisor cites evidence, states confidence, includes contrary evidence,
defines an invalidation condition, and proposes only a bounded action. Missing
or stale evidence produces ABSTAIN or WAIT. Rules-based reasoning is the
reproducible baseline; optional LLM reasoning must satisfy the same strict JSON
contract and cannot access execution tools.

### Consensus and deterministic authority

Consensus requires technical and options-liquidity agreement, preserves
dissent, and respects every hard veto. A probabilistic advisor can recommend a
trade; it cannot authorize one.

The final gate independently enforces:

- Alpaca paper environment and two explicit execution switches;
- open regular session and quote freshness of 120 seconds or less;
- no unknown or duplicate order state;
- no pending order, repeated contract, or cooldown violation;
- long premium only, one contract, limit order, and maximum defined loss of
  USD 500;
- daily loss circuit breaker, position cap, and recent-fill limit;
- idempotent client order IDs and post-submission broker verification.

Any failed check returns WAIT or REJECT. The agent never substitutes a market
order, increases size, or falls back to live trading.

### Alpaca and MCP architecture

The application talks to Alpaca's official MCP server over stdio. It uses
structured tools for account and position state, the market clock, IEX bars and
quotes, options snapshots and Greeks, recent orders, order submission, and
broker verification. The local launcher forwards only an allowlist of runtime
variables and forces `ALPACA_PAPER_TRADE=true`. Credentials never enter the
repository, journal, dashboard, video, or submission text.

The dedicated competition account was created on 28 August 2026 with a
USD 100,000 paper balance, active status, options level 3, and no initial
positions or fills. A deliberately non-marketable USD 1 equity limit order
verified connectivity and was canceled without a fill. During the competition
session, three exploratory v0 one-contract long-call limit orders filled on
AAPL, XLF, and AMZN. They demonstrate bounded paper execution but are not v1
performance. Combined premium paid, and therefore maximum defined premium risk,
was USD 825. The captured paper mark showed USD 99,986.91 equity and -USD 13.09
cumulative P&L. Competition snapshots retain only sanitized metrics; public
artifacts contain no raw account ID.

### Inspectability and performance

Every cycle appends a machine-readable record containing evidence lineage,
advisor views, disagreement, consensus, deterministic gate results, proposed
order, Alpaca receipt, and account performance. The public HTML dashboard
renders the same trace for judges. Starting equity, current equity, cumulative
paper P&L, return, positions, orders, fills, and cancellations reconcile to the
dedicated Alpaca account.

The original v0 momentum strategy failed its untouched holdout and remains
reported as a negative result. A frozen exhaustion-reversal challenger selected
only on development data then produced 127 signals, a 55.9% win rate, +0.218%
average signed move, 1.39 profit factor, and a 0.88 event-frequency-adjusted
Sharpe proxy on the untouched 2024-2026 holdout. A non-overlapping audit retains
81 signals, a 56.8% win rate, +0.377% average signed move, and 1.87 profit factor.
The headline win-rate 95% Wilson interval is 47.2%-64.2%. These are
underlying-direction diagnostics, not option P&L; they exclude option spreads,
decay, fees, and execution costs.

This is research software operating with simulated funds. Paper fills and a
historical directional diagnostic do not establish live profitability, and the
project is not investment advice.

### Public judge evidence

- Deployed dashboard: <https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/>
- Public MIT repository: <https://github.com/TheFutureEdge/ipulse-ai-options-alpha-agent>
- Final 4:54 video: <https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/ipulse-options-alpha-agent-judge-demo-v03.mp4>
- Final ten-slide deck: <https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/2026-09-04_ipulse-ai-options-alpha-agent_judge-deck_v06.pdf>
- Editable deck: <https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/2026-09-04_ipulse-ai-options-alpha-agent_judge-deck_v06.pptx>
