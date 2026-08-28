"""Autonomous decision orchestration with a deterministic risk authority."""

from __future__ import annotations

from dataclasses import dataclass

from .domain import PortfolioSnapshot, TradeProposal
from .risk import RiskDecision, RiskGate
from .strategy import MomentumRegimeStrategy, StrategySignal


@dataclass(frozen=True)
class AgentDecision:
    """Complete inspectable decision before any broker action."""

    action: str
    proposal: TradeProposal | None
    risk: RiskDecision | None
    explanation: str


class OptionsAlphaAgent:
    """Coordinate strategy generation and final deterministic risk approval."""

    def __init__(
        self,
        strategy: MomentumRegimeStrategy | None = None,
        risk_gate: RiskGate | None = None,
    ) -> None:
        """Initialize the agent with replaceable strategy and risk components."""

        self.strategy = strategy or MomentumRegimeStrategy()
        self.risk_gate = risk_gate or RiskGate()

    def decide(
        self,
        signal: StrategySignal,
        portfolio: PortfolioSnapshot,
        *,
        paper_environment: bool,
    ) -> AgentDecision:
        """Produce an approved proposal or an explicit no-trade decision."""

        proposal = self.strategy.propose(signal)
        if proposal is None:
            return AgentDecision(
                action="WAIT",
                proposal=None,
                risk=None,
                explanation="Strategy evidence did not satisfy the entry threshold.",
            )

        risk = self.risk_gate.evaluate(
            proposal,
            portfolio,
            paper_environment=paper_environment,
        )
        if not risk.approved:
            return AgentDecision(
                action="REJECT",
                proposal=proposal,
                risk=risk,
                explanation="Risk gate rejected the proposal.",
            )
        return AgentDecision(
            action="APPROVE",
            proposal=proposal,
            risk=risk,
            explanation="Strategy and every deterministic risk gate approved.",
        )
