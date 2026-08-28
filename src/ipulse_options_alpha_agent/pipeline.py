"""Multi-advisor orchestration before deterministic portfolio risk."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace

from .advisors import ResearchAdvisor, RiskCriticAdvisor, default_rule_advisors
from .agent import AgentDecision, OptionsAlphaAgent
from .consensus import ConsensusDecision, ConsensusEngine
from .domain import PortfolioSnapshot
from .research import (
    AdvisoryAction,
    AdvisorName,
    AdvisorOpinion,
    ResearchContext,
)
from .safety import OperationalSafetyDecision, OperationalSafetyGate


@dataclass(frozen=True)
class AdvisoryRun:
    """Complete multi-advisor output for one inspectable decision cycle."""

    opinions: tuple[AdvisorOpinion, ...]
    consensus: ConsensusDecision
    operational_safety: OperationalSafetyDecision
    decision: AgentDecision


class MultiAdvisorPipeline:
    """Run independent advisors concurrently and preserve deterministic authority."""

    def __init__(
        self,
        advisors: tuple[ResearchAdvisor, ...] | None = None,
        consensus_engine: ConsensusEngine | None = None,
        agent: OptionsAlphaAgent | None = None,
        operational_safety_gate: OperationalSafetyGate | None = None,
    ) -> None:
        self.advisors = advisors or default_rule_advisors()
        self.consensus_engine = consensus_engine or ConsensusEngine()
        self.agent = agent or OptionsAlphaAgent()
        self.operational_safety_gate = (
            operational_safety_gate or OperationalSafetyGate()
        )

    async def run(
        self,
        context: ResearchContext,
        portfolio: PortfolioSnapshot,
        *,
        paper_environment: bool,
    ) -> AdvisoryRun:
        """Produce a consensus, then invoke the existing deterministic risk gate."""

        gathered = await asyncio.gather(
            *(advisor.analyze(context) for advisor in self.advisors)
        )
        opinions = tuple(gathered)
        operational_safety = self.operational_safety_gate.evaluate(
            context.operational
        )
        if not operational_safety.approved:
            deterministic_risk_opinion = await RiskCriticAdvisor(
                self.operational_safety_gate
            ).analyze(context)
            opinions = tuple(
                deterministic_risk_opinion
                if opinion.advisor is AdvisorName.RISK_CRITIC
                else opinion
                for opinion in opinions
            )
            if not any(
                opinion.advisor is AdvisorName.RISK_CRITIC for opinion in opinions
            ):
                opinions = (*opinions, deterministic_risk_opinion)
        consensus = self.consensus_engine.evaluate(opinions)
        if consensus.action is AdvisoryAction.WAIT:
            return AdvisoryRun(
                opinions=opinions,
                consensus=consensus,
                operational_safety=operational_safety,
                decision=AgentDecision(
                    action="WAIT",
                    proposal=None,
                    risk=None,
                    explanation=f"Advisor consensus chose WAIT: {consensus.rationale}",
                ),
            )

        signal = replace(
            context.signal,
            confidence=min(context.signal.confidence, consensus.confidence),
        )
        decision = self.agent.decide(
            signal,
            portfolio,
            paper_environment=paper_environment,
        )
        if decision.proposal is not None:
            proposal = replace(
                decision.proposal,
                strategy_name="multi_advisor_consensus_v0",
                confidence=consensus.confidence,
                rationale=consensus.rationale,
                source_signals={
                    **decision.proposal.source_signals,
                    "advisor_consensus_confidence": consensus.confidence,
                },
            )
            decision = replace(decision, proposal=proposal)
        return AdvisoryRun(
            opinions=opinions,
            consensus=consensus,
            operational_safety=operational_safety,
            decision=decision,
        )
