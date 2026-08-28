"""Tests for evidence-aware consensus and end-to-end advisory orchestration."""

from __future__ import annotations

import unittest

from ipulse_options_alpha_agent.advisors import (
    ResearchAdvisor,
    default_rule_advisors,
)
from ipulse_options_alpha_agent.consensus import ConsensusEngine
from ipulse_options_alpha_agent.domain import PortfolioSnapshot
from ipulse_options_alpha_agent.pipeline import MultiAdvisorPipeline
from ipulse_options_alpha_agent.research import (
    AdvisoryAction,
    AdvisorName,
    AdvisorOpinion,
    FinancialEvidence,
    OperationalState,
    ResearchContext,
    ValuationEvidence,
)
from ipulse_options_alpha_agent.strategy import StrategySignal


def opinion(
    advisor: AdvisorName,
    action: AdvisoryAction,
    confidence: float,
    *,
    veto: bool = False,
) -> AdvisorOpinion:
    return AdvisorOpinion(
        advisor=advisor,
        action=action,
        confidence=confidence,
        thesis="test opinion",
        evidence_refs=("market:fast_return_pct",),
        hard_veto=veto,
    )


def demo_context() -> ResearchContext:
    return ResearchContext(
        underlying="SPY",
        signal=StrategySignal(
            underlying="SPY",
            option_symbol="SPY260904C00772000",
            option_limit_price=2.50,
            fast_return_pct=0.60,
            slow_return_pct=1.10,
            realized_volatility_pct=18,
            option_spread_pct=3,
            confidence=0.82,
        ),
        as_of_utc="2026-08-28T14:00:00Z",
        operational=OperationalState(
            market_open=True,
            quote_age_seconds=5,
            daily_trade_count=0,
            duplicate_signal=False,
            open_order_count=0,
            minutes_since_last_trade=None,
        ),
        financials=FinancialEvidence(
            as_of_date="2026-06-30",
            source_ids=("filing:10q",),
            revenue_growth_pct=10,
            gross_margin_pct=50,
            operating_margin_pct=20,
            free_cash_flow_margin_pct=15,
            cash_conversion_pct=90,
            accrual_ratio_pct=2,
            net_debt_to_ebitda=1,
            share_count_growth_pct=0,
            roic_pct=12,
        ),
        valuation=ValuationEvidence(
            as_of_date="2026-08-27",
            source_ids=("valuation:model-v1",),
            market_price=80,
            estimated_fair_value=100,
            forward_pe=15,
            sector_median_forward_pe=20,
            ev_to_ebitda=10,
            sector_median_ev_to_ebitda=12,
            free_cash_flow_yield_pct=5,
            earnings_growth_pct=8,
        ),
    )


class ConsensusTests(unittest.IsolatedAsyncioTestCase):
    def test_consensus_requires_technical_and_options_agreement(self) -> None:
        result = ConsensusEngine().evaluate(
            (
                opinion(AdvisorName.TECHNICAL_REGIME, AdvisoryAction.CALL, 0.8),
                opinion(AdvisorName.OPTIONS_LIQUIDITY, AdvisoryAction.PUT, 0.8),
            )
        )
        self.assertEqual(result.action, AdvisoryAction.WAIT)

    def test_hard_veto_forces_wait(self) -> None:
        result = ConsensusEngine().evaluate(
            (
                opinion(AdvisorName.TECHNICAL_REGIME, AdvisoryAction.CALL, 0.8),
                opinion(AdvisorName.OPTIONS_LIQUIDITY, AdvisoryAction.CALL, 0.8),
                opinion(AdvisorName.RISK_CRITIC, AdvisoryAction.WAIT, 1, veto=True),
            )
        )
        self.assertEqual(result.action, AdvisoryAction.WAIT)
        self.assertTrue(result.hard_vetoes)

    async def test_pipeline_approves_aligned_six_advisor_context(self) -> None:
        run = await MultiAdvisorPipeline(default_rule_advisors()).run(
            demo_context(),
            PortfolioSnapshot(
                equity=100_000,
                cash=100_000,
                buying_power=400_000,
                daily_pnl=0,
                open_positions=0,
            ),
            paper_environment=True,
        )
        self.assertEqual(run.consensus.action, AdvisoryAction.CALL)
        self.assertEqual(run.decision.action, "APPROVE")
        self.assertEqual(
            run.decision.proposal and run.decision.proposal.strategy_name,
            "multi_advisor_consensus_v0",
        )

    async def test_deterministic_safety_overrides_permissive_risk_advisor(self) -> None:
        class PermissiveRiskAdvisor:
            name = AdvisorName.RISK_CRITIC

            async def analyze(self, context: ResearchContext) -> AdvisorOpinion:
                return AdvisorOpinion(
                    advisor=self.name,
                    action=AdvisoryAction.ABSTAIN,
                    confidence=1,
                    thesis="Incorrectly permissive model output.",
                    abstention_reason="No risk identified.",
                    reasoning_source="test_model",
                )

        base = default_rule_advisors()
        advisors: tuple[ResearchAdvisor, ...] = (
            *base[:-1],
            PermissiveRiskAdvisor(),
        )
        open_context = demo_context()
        closed_context = ResearchContext(
            underlying=open_context.underlying,
            signal=open_context.signal,
            as_of_utc=open_context.as_of_utc,
            operational=OperationalState(
                market_open=False,
                quote_age_seconds=5,
                daily_trade_count=0,
                duplicate_signal=False,
                open_order_count=0,
                minutes_since_last_trade=None,
            ),
            financials=open_context.financials,
            valuation=open_context.valuation,
        )
        run = await MultiAdvisorPipeline(advisors).run(
            closed_context,
            PortfolioSnapshot(100_000, 100_000, 400_000, 0, 0),
            paper_environment=True,
        )
        risk_opinion = next(
            item
            for item in run.opinions
            if item.advisor is AdvisorName.RISK_CRITIC
        )
        self.assertTrue(risk_opinion.hard_veto)
        self.assertFalse(run.operational_safety.approved)
        self.assertEqual(run.decision.action, "WAIT")


if __name__ == "__main__":
    unittest.main()
