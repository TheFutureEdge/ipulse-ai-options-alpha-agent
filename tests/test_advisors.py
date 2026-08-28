"""Tests for independent financial, value, options, and risk advisors."""

from __future__ import annotations

import unittest

from ipulse_options_alpha_agent.advisors import (
    FinancialsForensicAuditor,
    RiskCriticAdvisor,
    ValueFrameworkAdvisor,
)
from ipulse_options_alpha_agent.research import (
    AdvisoryAction,
    FinancialEvidence,
    FundEvidence,
    FundValuationEvidence,
    OperationalState,
    ResearchContext,
    ValuationEvidence,
)
from ipulse_options_alpha_agent.strategy import StrategySignal


def context(
    *,
    financials: FinancialEvidence | None = None,
    valuation: ValuationEvidence | None = None,
    fund: FundEvidence | None = None,
    fund_valuation: FundValuationEvidence | None = None,
    market_open: bool = True,
) -> ResearchContext:
    return ResearchContext(
        underlying="SPY",
        signal=StrategySignal(
            underlying="SPY",
            option_symbol="SPY260904C00772000",
            option_limit_price=2.50,
            fast_return_pct=0.60,
            slow_return_pct=1.20,
            realized_volatility_pct=18,
            option_spread_pct=3,
            confidence=0.80,
        ),
        as_of_utc="2026-08-28T14:00:00Z",
        operational=OperationalState(
            market_open=market_open,
            quote_age_seconds=10,
            daily_trade_count=0,
            duplicate_signal=False,
            open_order_count=0,
            minutes_since_last_trade=None,
        ),
        financials=financials,
        fund=fund,
        valuation=valuation,
        fund_valuation=fund_valuation,
    )


def good_financials(**overrides: object) -> FinancialEvidence:
    values: dict[str, object] = {
        "as_of_date": "2026-06-30",
        "source_ids": ("filing:10q",),
        "revenue_growth_pct": 12.0,
        "gross_margin_pct": 55.0,
        "operating_margin_pct": 22.0,
        "free_cash_flow_margin_pct": 18.0,
        "cash_conversion_pct": 95.0,
        "accrual_ratio_pct": 3.0,
        "net_debt_to_ebitda": 1.2,
        "share_count_growth_pct": 0.5,
        "roic_pct": 14.0,
    }
    values.update(overrides)
    return FinancialEvidence(**values)  # type: ignore[arg-type]


class AdvisorTests(unittest.IsolatedAsyncioTestCase):
    async def test_financials_auditor_abstains_without_filings(self) -> None:
        opinion = await FinancialsForensicAuditor().analyze(context())
        self.assertEqual(opinion.action, AdvisoryAction.ABSTAIN)

    async def test_financials_auditor_vetoes_restatement(self) -> None:
        opinion = await FinancialsForensicAuditor().analyze(
            context(financials=good_financials(restatement_count=1))
        )
        self.assertEqual(opinion.action, AdvisoryAction.WAIT)
        self.assertTrue(opinion.hard_veto)

    async def test_financials_auditor_uses_fund_structure_for_etf(self) -> None:
        opinion = await FinancialsForensicAuditor().analyze(
            context(
                fund=FundEvidence(
                    as_of_date="2026-08-26",
                    source_ids=("ipulse:fund-snapshot:spy",),
                    expense_ratio_pct=0.095,
                    annual_turnover_pct=2,
                    total_assets_usd=807_000_000_000,
                    holdings_count=500,
                    top_10_weight_pct=37,
                    largest_holding_weight_pct=7.7,
                    largest_sector_weight_pct=37.5,
                    cash_weight_pct=0.1,
                )
            )
        )
        self.assertEqual(opinion.action, AdvisoryAction.CALL)
        self.assertIn("fund:expense_ratio_pct", opinion.evidence_refs)

    async def test_value_framework_supports_margin_of_safety(self) -> None:
        opinion = await ValueFrameworkAdvisor().analyze(
            context(
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
                    earnings_growth_pct=10,
                )
            )
        )
        self.assertEqual(opinion.action, AdvisoryAction.CALL)

    async def test_value_framework_does_not_treat_negative_pe_as_cheap(self) -> None:
        opinion = await ValueFrameworkAdvisor().analyze(
            context(
                valuation=ValuationEvidence(
                    as_of_date="2026-08-27",
                    source_ids=("valuation:model-v1",),
                    market_price=80,
                    estimated_fair_value=100,
                    forward_pe=-15,
                    sector_median_forward_pe=20,
                    ev_to_ebitda=-10,
                    sector_median_ev_to_ebitda=12,
                    free_cash_flow_yield_pct=5,
                    earnings_growth_pct=10,
                )
            )
        )
        self.assertEqual(opinion.action, AdvisoryAction.WAIT)

    async def test_value_framework_compares_etf_with_category(self) -> None:
        opinion = await ValueFrameworkAdvisor().analyze(
            context(
                fund_valuation=FundValuationEvidence(
                    as_of_date="2026-08-26",
                    source_ids=("ipulse:fund-value:spy",),
                    prospective_pe=18,
                    category_prospective_pe=20,
                    price_to_cash_flow=12,
                    category_price_to_cash_flow=14,
                    long_term_earnings_growth_pct=11,
                    category_long_term_earnings_growth_pct=9,
                    historical_earnings_growth_pct=8,
                    sales_growth_pct=7,
                    cash_flow_growth_pct=8,
                )
            )
        )
        self.assertEqual(opinion.action, AdvisoryAction.CALL)
        self.assertIn("fund_valuation:prospective_pe", opinion.evidence_refs)

    async def test_risk_critic_vetoes_closed_market(self) -> None:
        opinion = await RiskCriticAdvisor().analyze(context(market_open=False))
        self.assertTrue(opinion.hard_veto)
        self.assertEqual(opinion.action, AdvisoryAction.WAIT)


if __name__ == "__main__":
    unittest.main()
