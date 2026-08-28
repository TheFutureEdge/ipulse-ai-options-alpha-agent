# iPulse AI Options Alpha Agent

## Problem

Autonomous trading agents can place orders faster than people can audit their
reasoning. A profitable paper result is not enough if the decision path, risk
limits, and failures cannot be inspected.

## Solution

iPulse AI Options Alpha Agent separates probabilistic research from
deterministic execution authority. Independent advisors will produce structured
market views. A consensus layer proposes one bounded options action or WAIT. A
hard risk gate then approves or rejects the proposal using portfolio state and
explicit limits.

## AI logic

Real Alpaca bars, quotes, and option-chain data feed six independent roles:
technical regime, news catalyst, options liquidity, financials forensic auditor,
value framework, and risk critic. Each returns evidence references, confidence,
contrary evidence, invalidation conditions, and CALL, PUT, WAIT, or ABSTAIN.
Rules-based and strict-schema OpenAI implementations share the same contract.
Consensus can recommend; it cannot bypass deterministic safety or risk gates.

The forensic auditor challenges cash conversion, accruals, leverage, dilution,
ROIC, restatements, and auditor opinion. The value framework requires an explicit
margin of safety supported by cash yield, growth, and relative multiples.
For ETF underlyings, the forensic role switches to a fund-appropriate audit of
cost, scale, turnover, diversification, concentration, and cash drag.

## Risk gates

- Paper trading only
- Liquid ETF universe
- Long premium or later defined-risk spreads only
- One contract in the first execution phase
- Limit orders only
- 0.5 percent paper-equity maximum loss per trade
- 2 percent daily loss circuit breaker
- Five-position cap
- Fresh quote, three-trade daily cap, duplicate-contract protection, pending
  order veto, and cooldown
- Stale or incomplete external evidence is rejected rather than guessed
- Append-only decision and rejection journal

## Alpaca infrastructure

The agent uses Alpaca's official MCP server for account state, market clock,
asset discovery, daily bars, stock quotes, option chains, option market data,
and paper orders. The development account is separate from the fresh
competition account required for judging.

## Demonstration

The demo shows one complete trace: evidence -> six opinions -> consensus ->
operational safety -> portfolio risk -> Alpaca paper order -> broker verification.
Rejected and abstaining views remain visible because restraint is part of agent
quality.

The trace is also rendered as a self-contained HTML report: advisor cards,
evidence lineage, dissent, vetoes, and deterministic safety in one judge-friendly
view.

## Limitations

Paper fills are simulated. Short-horizon performance does not establish live
profitability. Market-data plan limits, spread assumptions, latency, and model
errors are disclosed in the evidence log.
