"""Independent deterministic research advisors and fail-closed abstention."""

from __future__ import annotations

from typing import Protocol

from .research import (
    AdvisoryAction,
    AdvisorName,
    AdvisorOpinion,
    ResearchContext,
)
from .safety import OperationalSafetyGate


class ResearchAdvisor(Protocol):
    """Common asynchronous contract for rules-based and LLM advisors."""

    name: AdvisorName

    async def analyze(self, context: ResearchContext) -> AdvisorOpinion:
        """Return one bounded opinion without any broker authority."""


def signal_direction(context: ResearchContext) -> AdvisoryAction:
    """Return the frozen exhaustion-reversal direction."""

    signal = context.signal
    if signal.realized_volatility_pct > 25:
        return AdvisoryAction.WAIT
    if signal.fast_return_pct >= 0.50 and signal.slow_return_pct >= 3.00:
        return AdvisoryAction.PUT
    if signal.fast_return_pct <= -0.50 and signal.slow_return_pct <= -3.00:
        return AdvisoryAction.CALL
    return AdvisoryAction.WAIT


class TechnicalRegimeAdvisor:
    """Assess direction, trend agreement, and realized-volatility regime."""

    name = AdvisorName.TECHNICAL_REGIME

    async def analyze(self, context: ResearchContext) -> AdvisorOpinion:
        action = signal_direction(context)
        signal = context.signal
        return AdvisorOpinion(
            advisor=self.name,
            action=action,
            confidence=signal.confidence if action is not AdvisoryAction.WAIT else 0.75,
            thesis=(
                "Fast and slow moves meet the frozen exhaustion-reversal rule in an acceptable volatility regime."
                if action in {AdvisoryAction.CALL, AdvisoryAction.PUT}
                else "Trend alignment or volatility regime is insufficient."
            ),
            evidence_refs=(
                "market:fast_return_pct",
                "market:slow_return_pct",
                "market:realized_volatility_pct",
            ),
            contrary_evidence=(
                "A historical reversal pattern can fail or continue trending.",
            ),
            invalidation_conditions=(
                "Fast or slow return no longer meets the frozen exhaustion threshold.",
                "Realized volatility rises above 25 percent.",
            ),
            max_entry_price=context.signal.option_limit_price,
        )


class OptionsLiquidityAdvisor:
    """Assess option cost, spread, and whether the contract matches direction."""

    name = AdvisorName.OPTIONS_LIQUIDITY

    async def analyze(self, context: ResearchContext) -> AdvisorOpinion:
        signal = context.signal
        action = signal_direction(context)
        if signal.option_spread_pct > 8 or signal.option_limit_price * 100 > 500:
            action = AdvisoryAction.WAIT
        expected_marker = "C" if action is AdvisoryAction.CALL else "P"
        if action in {AdvisoryAction.CALL, AdvisoryAction.PUT}:
            option_tail = signal.option_symbol[-9:]
            if expected_marker not in option_tail:
                action = AdvisoryAction.WAIT
        return AdvisorOpinion(
            advisor=self.name,
            action=action,
            confidence=(
                max(0.55, min(0.92, 0.90 - signal.option_spread_pct / 20))
                if action in {AdvisoryAction.CALL, AdvisoryAction.PUT}
                else 0.85
            ),
            thesis=(
                "The selected contract is directionally consistent and inside the spread and loss budget."
                if action in {AdvisoryAction.CALL, AdvisoryAction.PUT}
                else "The selected option fails direction, spread, or maximum-loss requirements."
            ),
            evidence_refs=(
                "option:symbol",
                "option:limit_price",
                "option:spread_pct",
            ),
            contrary_evidence=("Indicative option quotes may differ from executable OPRA quotes.",),
            invalidation_conditions=(
                "Spread widens above 8 percent.",
                "One-contract premium exceeds USD 500.",
            ),
            max_entry_price=signal.option_limit_price,
        )


class NewsCatalystAdvisor:
    """Evaluate timestamped news while abstaining when coverage is absent."""

    name = AdvisorName.NEWS_CATALYST

    async def analyze(self, context: ResearchContext) -> AdvisorOpinion:
        if not context.news:
            return AdvisorOpinion(
                advisor=self.name,
                action=AdvisoryAction.ABSTAIN,
                confidence=0,
                thesis="No timestamped news evidence was supplied.",
                abstention_reason="News coverage is unavailable for this run.",
            )
        average = sum(item.sentiment_score for item in context.news) / len(context.news)
        action = (
            AdvisoryAction.CALL
            if average >= 0.20
            else AdvisoryAction.PUT
            if average <= -0.20
            else AdvisoryAction.WAIT
        )
        return AdvisorOpinion(
            advisor=self.name,
            action=action,
            confidence=min(0.85, 0.55 + abs(average) / 2),
            thesis="Recent timestamped catalysts were evaluated without overriding market evidence.",
            evidence_refs=tuple(item.evidence_id for item in context.news),
            contrary_evidence=("Headline sentiment may not capture priced-in expectations.",),
            invalidation_conditions=("A material contradictory catalyst is published.",),
        )


class FinancialsForensicAuditor:
    """Audit cash conversion, accruals, leverage, dilution, and filing flags."""

    name = AdvisorName.FINANCIALS_FORENSIC_AUDITOR

    async def analyze(self, context: ResearchContext) -> AdvisorOpinion:
        financials = context.financials
        if financials is None and context.fund is not None:
            return self._analyze_fund(context)
        if financials is None:
            return AdvisorOpinion(
                advisor=self.name,
                action=AdvisoryAction.ABSTAIN,
                confidence=0,
                thesis="No normalized filing evidence was supplied.",
                abstention_reason="Financial statements or aggregate ETF fundamentals are unavailable.",
            )

        hard_flags: list[str] = []
        soft_flags: list[str] = []
        if financials.restatement_count > 0:
            hard_flags.append("A financial restatement is present.")
        if financials.auditor_opinion.lower() in {"adverse", "going_concern", "disclaimer"}:
            hard_flags.append("The auditor opinion contains a severe qualification.")
        if financials.accrual_ratio_pct > 10:
            soft_flags.append("Accruals are high relative to the evidence threshold.")
        if financials.cash_conversion_pct < 70:
            soft_flags.append("Cash conversion is weak.")
        if financials.net_debt_to_ebitda > 4:
            soft_flags.append("Leverage is elevated.")
        if financials.share_count_growth_pct > 5:
            soft_flags.append("Share dilution is elevated.")

        refs = (
            "financial:free_cash_flow_margin_pct",
            "financial:cash_conversion_pct",
            "financial:accrual_ratio_pct",
            "financial:net_debt_to_ebitda",
            "financial:share_count_growth_pct",
            "financial:restatement_count",
            "financial:auditor_opinion",
        )
        if hard_flags:
            return AdvisorOpinion(
                advisor=self.name,
                action=AdvisoryAction.WAIT,
                confidence=0.98,
                thesis="Forensic filing checks identified a hard governance or reporting veto.",
                evidence_refs=refs,
                contrary_evidence=tuple(hard_flags + soft_flags),
                invalidation_conditions=(
                    "A verified amended filing resolves the reported issue.",
                ),
                hard_veto=True,
            )

        action = (
            AdvisoryAction.PUT
            if len(soft_flags) >= 3
            else AdvisoryAction.CALL
            if financials.free_cash_flow_margin_pct > 0
            and financials.cash_conversion_pct >= 80
            and financials.roic_pct > 8
            else AdvisoryAction.WAIT
        )
        return AdvisorOpinion(
            advisor=self.name,
            action=action,
            confidence=0.78 if action is not AdvisoryAction.WAIT else 0.65,
            thesis=(
                "Cash generation, conversion, and returns pass the forensic framework."
                if action is AdvisoryAction.CALL
                else "Multiple accounting-quality flags weaken the financial evidence."
                if action is AdvisoryAction.PUT
                else "Financial quality is mixed and does not justify a directional vote."
            ),
            evidence_refs=refs,
            contrary_evidence=tuple(soft_flags) or ("Financial statements are backward-looking.",),
            invalidation_conditions=(
                "Cash conversion falls below 70 percent.",
                "Accrual ratio rises above 10 percent.",
            ),
        )

    def _analyze_fund(self, context: ResearchContext) -> AdvisorOpinion:
        """Audit ETF cost, scale, diversification, concentration, and cash drag."""

        fund = context.fund
        if fund is None:
            raise ValueError("Fund evidence is required.")
        flags: list[str] = []
        if fund.expense_ratio_pct > 0.75:
            flags.append("Fund expense ratio is elevated.")
        if fund.total_assets_usd < 500_000_000:
            flags.append("Fund assets are below the scale threshold.")
        if fund.holdings_count < 30:
            flags.append("Fund holdings are insufficiently diversified.")
        if fund.top_10_weight_pct > 55:
            flags.append("Top-ten concentration is elevated.")
        if fund.largest_holding_weight_pct > 15:
            flags.append("Single-holding concentration is elevated.")
        if fund.largest_sector_weight_pct > 50:
            flags.append("Single-sector concentration is elevated.")
        if fund.cash_weight_pct > 10:
            flags.append("Cash allocation creates material tracking drag.")
        refs = (
            "fund:expense_ratio_pct",
            "fund:annual_turnover_pct",
            "fund:total_assets_usd",
            "fund:holdings_count",
            "fund:top_10_weight_pct",
            "fund:largest_holding_weight_pct",
            "fund:largest_sector_weight_pct",
            "fund:cash_weight_pct",
        )
        action = (
            AdvisoryAction.PUT
            if len(flags) >= 3
            else AdvisoryAction.CALL
            if not flags
            else AdvisoryAction.WAIT
        )
        return AdvisorOpinion(
            advisor=self.name,
            action=action,
            confidence=0.78 if action is AdvisoryAction.CALL else 0.70,
            thesis=(
                "Fund cost, scale, diversification, and concentration pass the structural audit."
                if action is AdvisoryAction.CALL
                else "Multiple fund-structure weaknesses oppose the trade."
                if action is AdvisoryAction.PUT
                else "Fund structure is investable but contains a material concentration or cost flag."
            ),
            evidence_refs=refs,
            contrary_evidence=tuple(flags)
            or ("ETF structure does not determine short-horizon direction.",),
            invalidation_conditions=(
                "Top-ten concentration rises above 55 percent.",
                "Fund assets fall below USD 500 million.",
                "Expense ratio rises above 0.75 percent.",
            ),
        )


class ValueFrameworkAdvisor:
    """Compare price, fair value, cash yield, growth, and peer multiples."""

    name = AdvisorName.VALUE_FRAMEWORK

    async def analyze(self, context: ResearchContext) -> AdvisorOpinion:
        valuation = context.valuation
        if valuation is None and context.fund_valuation is not None:
            return self._analyze_fund_value(context)
        if valuation is None:
            return AdvisorOpinion(
                advisor=self.name,
                action=AdvisoryAction.ABSTAIN,
                confidence=0,
                thesis="No normalized valuation evidence was supplied.",
                abstention_reason="Fair-value and comparable-multiple inputs are unavailable.",
            )
        margin = valuation.margin_of_safety_pct
        valid_multiples = valuation.forward_pe > 0 and valuation.ev_to_ebitda > 0
        cheap_relative = (
            valid_multiples
            and valuation.forward_pe <= valuation.sector_median_forward_pe * 0.90
            and valuation.ev_to_ebitda <= valuation.sector_median_ev_to_ebitda * 0.95
        )
        expensive_relative = (
            valid_multiples
            and valuation.forward_pe >= valuation.sector_median_forward_pe * 1.20
            and valuation.ev_to_ebitda >= valuation.sector_median_ev_to_ebitda * 1.15
        )
        action = (
            AdvisoryAction.CALL
            if margin >= 15
            and cheap_relative
            and valuation.free_cash_flow_yield_pct >= 4
            and valuation.earnings_growth_pct > 0
            else AdvisoryAction.PUT
            if margin <= -20 and expensive_relative and valuation.free_cash_flow_yield_pct < 3
            else AdvisoryAction.WAIT
        )
        refs = (
            "valuation:market_price",
            "valuation:estimated_fair_value",
            "valuation:margin_of_safety_pct",
            "valuation:forward_pe",
            "valuation:sector_median_forward_pe",
            "valuation:ev_to_ebitda",
            "valuation:sector_median_ev_to_ebitda",
            "valuation:free_cash_flow_yield_pct",
            "valuation:earnings_growth_pct",
        )
        return AdvisorOpinion(
            advisor=self.name,
            action=action,
            confidence=0.80 if action is not AdvisoryAction.WAIT else 0.62,
            thesis=(
                "Price offers a material margin of safety with supportive cash yield and relative multiples."
                if action is AdvisoryAction.CALL
                else "Price embeds a premium unsupported by cash yield and relative multiples."
                if action is AdvisoryAction.PUT
                else "Valuation evidence is not extreme enough for a directional vote."
            ),
            evidence_refs=refs,
            contrary_evidence=(
                "Fair value is model-dependent and can change with discount rates or growth assumptions.",
            ),
            invalidation_conditions=(
                "Margin of safety falls below 10 percent for a CALL thesis.",
                "Earnings growth turns negative.",
            ),
            max_entry_price=context.signal.option_limit_price,
        )

    def _analyze_fund_value(self, context: ResearchContext) -> AdvisorOpinion:
        """Compare an ETF portfolio with its provider-defined category."""

        valuation = context.fund_valuation
        if valuation is None:
            raise ValueError("Fund valuation evidence is required.")
        if (
            valuation.prospective_pe <= 0
            or valuation.category_prospective_pe <= 0
            or valuation.price_to_cash_flow <= 0
            or valuation.category_price_to_cash_flow <= 0
        ):
            action = AdvisoryAction.WAIT
            pe_discount = 0.0
            cash_flow_discount = 0.0
        else:
            pe_discount = (
                (
                    valuation.category_prospective_pe
                    - valuation.prospective_pe
                )
                / valuation.category_prospective_pe
                * 100
            )
            cash_flow_discount = (
                (
                    valuation.category_price_to_cash_flow
                    - valuation.price_to_cash_flow
                )
                / valuation.category_price_to_cash_flow
                * 100
            )
            growth_supportive = (
                valuation.long_term_earnings_growth_pct
                >= valuation.category_long_term_earnings_growth_pct
                and valuation.cash_flow_growth_pct > 0
            )
            action = (
                AdvisoryAction.CALL
                if pe_discount >= 8
                and cash_flow_discount >= 5
                and growth_supportive
                else AdvisoryAction.PUT
                if pe_discount <= -20
                and cash_flow_discount <= -15
                and not growth_supportive
                else AdvisoryAction.WAIT
            )
        refs = (
            "fund_valuation:prospective_pe",
            "fund_valuation:category_prospective_pe",
            "fund_valuation:price_to_cash_flow",
            "fund_valuation:category_price_to_cash_flow",
            "fund_valuation:cash_flow_yield_pct",
            "fund_valuation:category_cash_flow_yield_pct",
            "fund_valuation:long_term_earnings_growth_pct",
            "fund_valuation:category_long_term_earnings_growth_pct",
            "fund_valuation:historical_earnings_growth_pct",
            "fund_valuation:sales_growth_pct",
            "fund_valuation:cash_flow_growth_pct",
        )
        return AdvisorOpinion(
            advisor=self.name,
            action=action,
            confidence=0.76 if action is not AdvisoryAction.WAIT else 0.64,
            thesis=(
                "ETF portfolio valuation is discounted to category with supportive growth and cash-flow yield."
                if action is AdvisoryAction.CALL
                else "ETF portfolio trades at an unsupported premium to its category."
                if action is AdvisoryAction.PUT
                else "ETF portfolio valuation and growth do not provide a sufficient relative-value edge."
            ),
            evidence_refs=refs,
            contrary_evidence=(
                f"Prospective P/E discount to category: {pe_discount:.2f}%.",
                f"Price-to-cash-flow discount to category: {cash_flow_discount:.2f}%.",
                "Provider category comparisons and projections can change.",
            ),
            invalidation_conditions=(
                "Prospective P/E discount falls below 5 percent.",
                "Cash-flow growth turns negative.",
                "Category classification changes.",
            ),
            max_entry_price=context.signal.option_limit_price,
        )


class RiskCriticAdvisor:
    """Challenge operational readiness without replacing deterministic gates."""

    name = AdvisorName.RISK_CRITIC

    def __init__(self, safety_gate: OperationalSafetyGate | None = None) -> None:
        self.safety_gate = safety_gate or OperationalSafetyGate()

    async def analyze(self, context: ResearchContext) -> AdvisorOpinion:
        decision = self.safety_gate.evaluate(context.operational)
        refs = (
            "ops:market_open",
            "ops:quote_age_seconds",
            "ops:daily_trade_count",
            "ops:duplicate_signal",
            "ops:open_order_count",
            "ops:minutes_since_last_trade",
        )
        if not decision.approved:
            return AdvisorOpinion(
                advisor=self.name,
                action=AdvisoryAction.WAIT,
                confidence=1,
                thesis="Operational risk conditions forbid a new order.",
                evidence_refs=refs,
                contrary_evidence=decision.reasons,
                invalidation_conditions=("Every operational safety reason is cleared.",),
                hard_veto=True,
            )
        return AdvisorOpinion(
            advisor=self.name,
            action=AdvisoryAction.ABSTAIN,
            confidence=1,
            thesis="No operational veto was found; the risk critic supplies no alpha vote.",
            evidence_refs=refs,
            abstention_reason="Operational checks passed, so no directional risk vote is needed.",
        )


def default_rule_advisors() -> tuple[ResearchAdvisor, ...]:
    """Return all six independent advisors in stable evaluation order."""

    return (
        TechnicalRegimeAdvisor(),
        NewsCatalystAdvisor(),
        OptionsLiquidityAdvisor(),
        FinancialsForensicAuditor(),
        ValueFrameworkAdvisor(),
        RiskCriticAdvisor(),
    )
