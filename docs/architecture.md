# Architecture

## Decision path

Alpaca market/portfolio state + normalized external research evidence -> six
independent advisors -> evidence-aware consensus -> deterministic operational
gate -> deterministic portfolio risk gate -> paper-only order adapter ->
append-only evidence journal.

The advisor layer may be rules-based or use structured OpenAI reasoning. It has
no broker authority. The operational and portfolio gates remain deterministic
and final.

## Independent advisors

- Technical regime: frozen exhaustion thresholds, reversal direction, and
  realized-volatility regime.
- News catalyst: timestamped catalyst direction; abstains without coverage.
- Options liquidity: direction, spread, premium, and contract consistency.
- Financials forensic auditor: cash conversion, accruals, leverage, dilution,
  return on invested capital, restatements, and auditor opinion.
- Value framework: fair value and margin of safety, forward P/E, EV/EBITDA,
  free-cash-flow yield, peer medians, and earnings growth.
- Risk critic: market session, quote freshness, churn, duplicate signal, and
  open-order vetoes. It does not cast an alpha vote.

Technical and options opinions must agree. A hard veto always produces WAIT;
aligned financial-quality and valuation opposition also blocks a trade.

## Evidence boundary

External research uses a versioned JSON contract. The adapter verifies symbol,
schema, source IDs, timestamps, field bounds, file size, and a SHA-256 lineage
hash. A document older than 24 hours, news older than seven days, financials
older than 400 days, or valuation inputs older than 31 days is rejected. See
`research_evidence.schema.json`.

This decouples the hackathon agent from iPulse AI's existing BigQuery
fundamental period facts and derived metrics. The upstream platform may produce
the normalized file; the trading process receives no database credentials.

The live selected-underlying path also has two narrow read-only adapters:

- Alpaca news is symbol-matched, freshness-checked, length-bounded, and assigned
  an auditable lexicon sentiment baseline. Article text remains untrusted data.
- iPulse ETF snapshots are queried with a parameterized BigQuery CLI request and
  mapped to a fund-specific forensic audit. Company accounting checks are never
  fabricated for an ETF.

The current curated ETF snapshot does not contain sufficient fair-value or
relative-multiple evidence. Consequently, the live value advisor abstains until
a supported valuation producer supplies those fields through the evidence
contract.

Forward curation support is prepared in the iPulse data-engineering code for
portfolio/category prospective P/E, price-to-cash-flow, and earnings, sales, and
cash-flow growth. After an independently approved upstream release and snapshot
refresh, the adapter will activate the ETF relative-value framework automatically.

## Initial execution policy

- Paper environment required.
- Liquid underlying universe: SPY, QQQ, IWM.
- Maximum one option contract.
- Long premium only; no naked short options.
- Limit orders only.
- Maximum loss per trade: 0.5 percent of paper equity.
- Maximum estimated notional: USD 1,000.
- Daily loss circuit breaker: 2 percent.
- Maximum open positions: five.
- Maximum three filled orders on the current New York trading date.
- No pending order or prior recent order for the same contract.
- Minimum 15 minutes between fills.
- Maximum option quote age: 120 seconds.

## Alpaca integration

The application connects to Alpaca's official MCP server over stdio. Secrets
are injected by the local execution environment and are never accepted as
application arguments or persisted by the evidence journal.

The first MCP phase exposed account, asset, stock-data, options-data, and news
toolsets only. The trading toolset was enabled after the risk-gate tests and
read-only connectivity checks passed. Application execution still fails closed
unless both the paper-environment assertion and explicit execution switch are
present.

## Current development proof

- Alpaca MCP account, stock-data, option-data, and trading schemas verified.
- Real SPY daily bars and quote normalized.
- Narrow option-chain query selects a liquid, near-0.50-delta contract under the
  USD 500 maximum-loss budget.
- One non-marketable, one-share SPY DAY limit order was accepted, re-read by
  order ID, and canceled before fill in the paper account on 2026-08-28.
- The original v0 market evaluation selected a SPY call candidate, but did not
  execute it; it is retained as historical negative-result evidence.
- The production path now scans SPY/QQQ/IWM and executes only the frozen
  `exhaustion_reversal_v1` rule. A 4 September pre-open check found no qualifying
  signal and recorded WAIT without requesting an order.
- Six-advisor demo reaches auditable consensus including forensic financial and
  value-framework evidence.
- A closed-market real-data run produced a hard risk veto and WAIT, as designed.
- A production iPulse SPY snapshot and live Alpaca news item now participate in
  the same evidence catalog.
- A static HTML report renders the latest trace with escaped external text and
  no client-side dependencies.

The one-share order is a connectivity proof, not strategy performance.
