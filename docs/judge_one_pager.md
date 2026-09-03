# iPulse AI Options Alpha Agent

## AI logic, risk gates, and Alpaca infrastructure

**Category:** autonomous options paper-trading agent
**Positioning:** inspectable multi-advisor research with deterministic execution
authority
**Environment:** Alpaca paper trading only

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
verified connectivity and was canceled without a fill. Competition snapshots
retain only a salted account fingerprint and sanitized performance metrics.

### Inspectability and performance

Every cycle appends a machine-readable record containing evidence lineage,
advisor views, disagreement, consensus, deterministic gate results, proposed
order, Alpaca receipt, and account performance. The public HTML dashboard
renders the same trace for judges. Starting equity, current equity, cumulative
paper P&L, return, positions, orders, fills, and cancellations reconcile to the
dedicated Alpaca account.

This is research software operating with simulated funds. Paper fills do not
establish live profitability, and the project is not investment advice.
