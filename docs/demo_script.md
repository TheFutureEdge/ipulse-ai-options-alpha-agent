# 4:54 Judge Demo Script

This script is the narration used by the final ten-slide judge video. The timing
keeps the finished video below Lablab's five-minute limit.

## 0:00-0:17 - The promise

Every trade is a claim. iPulse AI keeps the evidence. This is an inspectable
autonomous options research and Alpaca paper trading agent. Six independent
advisors propose, deterministic risk controls decide, and every broker result
remains reviewable.

## 0:17-0:41 - The user and problem

The real problem is not finding one more signal. Investment teams cannot govern
a black-box trading agent. Reasoning can drift, a confident model can bypass
risk, and missing evidence makes post-trade review guesswork. Our starting users
are adviser research teams, family offices, and sophisticated investors who need
AI-scale synthesis without surrendering policy control.

## 0:41-1:01 - Deployed proof

This is a working deployed product, not a chatbot wrapper. The public dashboard
shows three broker-verified paper option fills, 127 untouched holdout signals for
the frozen challenger, and the latest WAIT decision. Judges can open the
dashboard and repository without authentication and replay the evidence path.

## 1:01-1:37 - Architecture

The architecture separates two kinds of intelligence. Alpaca market and account
data, cited research, financials, and valuation evidence feed six independent
advisors: technical regime, news catalyst, options liquidity, a financials
forensic auditor, a value framework, and a risk critic. Consensus may propose
CALL, PUT, WAIT, or ABSTAIN. Deterministic policy then checks every execution
condition. Only after approval can Alpaca receive a paper order, which is
re-read and stored as a sanitized receipt.

## 1:37-2:08 - Why AI, and where it stops

AI is used where interpretation matters. It synthesizes heterogeneous evidence,
states contrary evidence, expresses confidence, and says what would invalidate
each view. Code controls capital. The paper environment, market session, quote
freshness, one-contract limit, long-premium rule, USD 500 maximum loss,
duplicate protection, cooldown, positions, and drawdown are deterministic. AI
can abstain. AI cannot bypass.

## 2:08-3:01 - Two separate proof tracks

We deliberately separate broker proof from strategy proof. Three exploratory v0
paper fills in AAPL, XLF, and AMZN demonstrate that the bounded execution path
works. Their combined maximum premium risk was USD 825. The captured mark was
down USD 13.09, and we publish that result.

The frozen reversal v1 strategy is evaluated separately on untouched 2024-2026
data: 127 signals, 55.9% directional wins, 1.39 profit factor, and a positive
0.218% average signed two-session underlying move. The 0.88 Sharpe figure is an
event-frequency proxy, not a portfolio Sharpe ratio, and the historical test is
not options P&L.

## 3:01-3:27 - Failure and restraint

Failure and restraint are first-class outputs. Momentum v0 failed its holdout,
so we kept the evidence, retired it, and froze the challenger before the next
test. The latest frozen scan also produced WAIT because none of SPY, QQQ, or IWM
met the rule. No order was requested. A trading agent should be judged by the
decisions it refuses as well as the trades it places.

## 3:27-3:59 - Business value

The business is governance software for investment research teams. The U.S. SEC
reports 22,932 investment advisers and USD 177 trillion in regulatory assets
under management for 2025. At an explicit USD 12,000 annual-contract assumption,
that is an illustrative USD 275 million U.S. software market. The commercial
model combines team SaaS, enterprise private deployment, and a usage-based
evidence API.

## 3:59-4:26 - Originality and moat

The moat is falsifiable research governance, not another signal. Instead of one
model and one answer, we preserve independent views and abstention. Instead of
letting reasoning authorize its own order, deterministic policy controls
execution. Instead of a headline backtest, we publish development, freeze,
untouched holdout, uncertainty, failures, WAIT decisions, broker receipts, and
P&L.

## 4:26-4:54 - Readiness and close

The product is deployed now with 59 passing tests, three broker-verified fills,
and a frozen scored ledger. Next comes continuous paper forward testing,
complete position-lifecycle evidence, broker reconciliation, and evaluation
drift alerts. Then adviser-team shadow mode and private policy deployment.

AI proposes. Deterministic risk decides. Alpaca executes. The evidence remains
inspectable.

On-screen footer: Research and simulated paper trading only. Not investment
advice.

## Publication gate

- Final video: `ipulse-options-alpha-agent-judge-demo-v03.mp4` (4:54).
- English captions: `ipulse-options-alpha-agent-judge-demo-v03.srt`.
- Resolution: 1920x1080; no credentials or raw account identifier appear.
- Repository, dashboard, deck, and video must open without authentication.
