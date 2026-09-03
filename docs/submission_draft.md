# Hackathon Submission Draft

## Project

iPulse AI Options Alpha Agent

## Tagline

An inspectable AI research agent that can say WAIT, propose one bounded options
trade, and prove why the paper broker accepted or rejected it.

## Submission summary

Most trading-agent demos optimize for activity. We optimize for falsifiable,
inspectable
decisions. The agent collects Alpaca market and portfolio evidence, selects a
liquid option, records a structured thesis, and passes the proposal through a
deterministic risk authority. Probabilistic advisors may recommend; they cannot
bypass the execution limits.

The competition build is operational. It connects to Alpaca's official
MCP server, reads a paper portfolio, normalizes SPY daily bars and quotes,
queries a narrow option chain, selects a near-0.50-delta contract within a USD
500 maximum-loss budget, and records the complete decision. On 3 September it
also produced three broker-verified strategy fills: one AAPL 11 September $330
call bought to open at $4.15 and one XLF 11 September $59 call bought to open
at $0.30, plus one AMZN 11 September $260 call bought to open at $3.80, with
$825 combined maximum long-premium risk. A separate USD 1
maximum-loss equity order proved the paper-order path, was verified by broker
order ID, and was canceled before fill.

## What makes it different

- WAIT and rejected trades are first-class evidence, not hidden failures.
- Every order has an idempotent client order ID and a deterministic risk trace.
- The execution adapter requires two independent paper-only switches.
- Credentials remain outside the repository and evidence stream.
- Strategy performance, paper-fill limitations, stale data, and model errors
  are disclosed rather than marketed away.
- The original momentum experiment failed historical validation; the public
  artifact says so instead of laundering it into a winning-looking backtest.
- A frozen exhaustion-reversal challenger was selected on 2021–2023
  development data and tested on untouched 2024–2026 data.

## Historical validation

The challenger uses only data available through close t, selects the strongest
qualifying SPY/QQQ/IWM exhaustion event, and scores the opposite direction at
close t+2. The untouched holdout contains 127 signals with a 55.9% directional
win rate, 1.39 profit factor, +0.218% average signed underlying move, and a 2.01
per-trade Sharpe proxy. These are directional diagnostics—not options P&L—and
exclude spreads, option decay and broker slippage.

## AI and autonomous logic

Six independent advisors are implemented: technical regime, news catalyst,
options liquidity, financials forensic auditor, value framework, and risk
critic. Every output includes cited evidence, confidence, contrary evidence,
invalidation tests, and a bounded action. Rules-based reasoning is the
reproducible baseline; optional OpenAI Responses reasoning uses the same strict
JSON contract. Consensus may create a proposal, but deterministic operational
and portfolio gates remain final authority.

The financials auditor checks cash conversion, accruals, leverage, dilution,
ROIC, restatements, and auditor opinion. The value advisor applies margin of
safety, cash yield, growth, forward P/E, and EV/EBITDA against peer medians.
For ETF trades, the auditor uses real fund structure instead of invented company
accounts: expense ratio, turnover, assets, diversification, concentration, and
cash allocation.

## Alpaca usage

- Official Alpaca MCP server over stdio
- Paper account and positions
- Market clock and asset state
- IEX daily bars and stock quotes
- Indicative option-chain snapshots, Greeks, implied volatility, and spreads
- Paper limit-order submission and order verification

## Options logic

- SPY, QQQ, and IWM initial universe
- Direction requires aligned fast and slow returns
- Volatility and spread filters can force WAIT
- Near-0.50-delta contract selection
- Long premium only in phase one
- One contract, limit order, maximum USD 500 defined loss

## Demonstration flow

1. Show sanitized paper account status and normalized external evidence lineage.
2. Run all six advisors over the real-market context.
3. Open their evidence citations, disagreements, and consensus.
4. Show the operational and portfolio risk decisions.
5. Enable the explicit paper switches and submit one bounded order during
   market hours.
6. Re-read the order from Alpaca and show the append-only evidence trace.
7. Show a forensic veto, an oversized rejection, and a stale-data WAIT.

## Evidence already available

- Fifty-six passing unit tests
- Paper account MCP connectivity and options-data access
- Dedicated competition account created on 28 August 2026 with a verified
  USD 100,000 baseline, active status, options level 3, and zero initial fills
- Paper trading tools enabled only after read-only validation
- One accepted, broker-verified, and canceled non-marketable paper smoke order
- Three broker-filled paper options: AAPL at $4.15, XLF at $0.30, and AMZN at $3.80
- Reproducible walk-forward engine and complete scored-outcome ledger
- One real-data SPY call proposal approved but intentionally not executed while
  validating the market pipeline
- One real-data six-advisor evaluation that correctly chose WAIT when the market
  was closed and its option quote was stale
- Strict normalized evidence adapter for iPulse AI financials and valuation data
- Live Alpaca news normalization and one production iPulse SPY fund snapshot in
  the advisor evidence catalog
- Self-contained static HTML report for the latest complete decision cycle
- Finite autonomous runner with bounded cycle count, cooldown, failure stop, and
  no path around the normal execution gates
- Sanitized competition performance journal with no raw account identifiers

## Required links before final submission

- Public repository: https://github.com/TheFutureEdge/ipulse-ai-options-alpha-agent
- Hosted demo: https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/
- Demo video: https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/ipulse-options-alpha-agent-49s-pitch.mp4
- Judge deck: https://thefutureedge.github.io/ipulse-ai-options-alpha-agent/assets/2026-09-03_ipulse-ai-options-alpha-agent_judge-deck_v02.pdf
- Team page: iPulse AI Open Lab

## Disclosure

This is a research and simulated paper-trading project, not investment advice.
Paper fills do not establish live profitability.
