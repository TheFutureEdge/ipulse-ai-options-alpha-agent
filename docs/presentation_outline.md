# Seven-Slide Judge Presentation

Format: 16:9
Target speaking time: 2 minutes 40 seconds, leaving 20 seconds for transitions
Visual system: dark iPulse navy, cyan evidence paths, amber vetoes, white type
Rule: one claim and one proof object per slide

## Slide 1 - The agent that can refuse

**Headline:** Options Alpha Agent
**Subhead:** Inspectable autonomous paper trading by iPulse AI
**Proof line:** AI proposes. Deterministic risk decides. Alpaca executes.

Visual: use the final competition cover with the six advisor labels.

Speaker note: Most trading-agent demos optimize for activity. We designed for
accountability, including the ability to WAIT.

## Slide 2 - Why activity is the wrong objective

**Headline:** A trade is not proof of intelligence
**Claim:** If judges cannot reconstruct the evidence, disagreement, vetoes, and
broker result, they cannot distinguish autonomy from unattended execution.

Visual: a single flow split into two outcomes: APPROVE -> bounded paper order;
WAIT/REJECT -> retained evidence. Give both outcomes equal visual weight.

Speaker note: Refused trades are not hidden errors. They are part of the public
record.

## Slide 3 - Six independent views

**Headline:** Never let one AI own the conclusion

Visual: six advisor nodes feeding a consensus ledger:

1. Technical regime
2. News catalyst
3. Options liquidity
4. Financials auditor
5. Value framework
6. Risk critic

Footer: Every view cites evidence, contrary evidence, confidence, and an
invalidation condition.

Speaker note: Advisors may call, put, wait, or abstain. Missing evidence does not
become a guess.

## Slide 4 - Deterministic authority

**Headline:** Reasoning may evolve. Capital boundaries stay explicit.

Visual: three stacked gates.

- Environment: paper-only, two execution switches
- Market: open session, fresh quote, complete broker state, no duplicate
- Portfolio/order: one contract, limit only, long premium, USD 500 maximum loss,
  cooldown, daily-loss and position caps

Speaker note: No advisor or LLM can bypass these rules. Failure produces WAIT or
REJECT.

## Slide 5 - Verified paper execution

**Headline:** Three bounded paper fills. No hidden risk.

Visual: sanitized scorecard.

- Starting equity: USD 100,000
- Filled orders: 3
- Contracts: AAPL, XLF, and AMZN calls
- Maximum combined premium risk: USD 825
- Current equity at the captured mark: USD 99,986.91
- Current paper P&L at the captured mark: -USD 13.09

Speaker note: The raw account ID appears only in the private Lablab judging
field, never in a public artifact. This is a short live paper snapshot, not a
profitability claim.

## Slide 6 - A frozen historical challenger

**Headline:** Out-of-sample evidence, with limitations visible

Visual: holdout scorecard for the exhaustion-reversal challenger.

- Untouched holdout: 2024-2026
- Signals: 127
- Win rate: 55.9%
- Average signed move: +0.218%
- Profit factor: 1.39
- Event-frequency Sharpe proxy: 0.88 (not a portfolio Sharpe ratio)
- Non-overlapping audit: 81 signals, 56.8% wins, +0.377% average, PF 1.87

Speaker note: This is an underlying-direction diagnostic, not option P&L. It
excludes option spreads, decay, fees, and execution costs. The original v0
strategy failed its holdout; that negative result remains public. The headline
win-rate Wilson interval is 47.2%-64.2%, so uncertainty is explicit.

## Slide 7 - What judges can inspect

**Headline:** From evidence to P&L, every step remains reviewable

Visual: four linked proof objects with final public URLs.

- GitHub repository
- Hosted decision dashboard
- Alpaca paper performance scorecard
- 49-second pitch video

Footer: Research and simulated paper trading only. Not investment advice.

Speaker note: Close with the final account result and one limitation learned
during the week. Do not claim that short paper performance predicts live
returns.
