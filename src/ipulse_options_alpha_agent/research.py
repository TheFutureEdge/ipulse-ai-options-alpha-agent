"""Structured research evidence and advisor outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from .strategy import StrategySignal


class AdvisoryAction(StrEnum):
    """Actions an advisor may recommend without placing an order."""

    CALL = "CALL"
    PUT = "PUT"
    WAIT = "WAIT"
    ABSTAIN = "ABSTAIN"


class AdvisorName(StrEnum):
    """Stable identities for independently evaluated research roles."""

    TECHNICAL_REGIME = "technical_regime"
    NEWS_CATALYST = "news_catalyst"
    OPTIONS_LIQUIDITY = "options_liquidity"
    FINANCIALS_FORENSIC_AUDITOR = "financials_forensic_auditor"
    VALUE_FRAMEWORK = "value_framework"
    RISK_CRITIC = "risk_critic"


@dataclass(frozen=True)
class NewsEvidence:
    """One timestamped news item with externally derived sentiment."""

    evidence_id: str
    headline: str
    summary: str
    source: str
    published_at_utc: str
    sentiment_score: float


@dataclass(frozen=True)
class FinancialEvidence:
    """Normalized filing evidence used by the forensic auditor."""

    as_of_date: str
    source_ids: tuple[str, ...]
    revenue_growth_pct: float
    gross_margin_pct: float
    operating_margin_pct: float
    free_cash_flow_margin_pct: float
    cash_conversion_pct: float
    accrual_ratio_pct: float
    net_debt_to_ebitda: float
    share_count_growth_pct: float
    roic_pct: float
    restatement_count: int = 0
    auditor_opinion: str = "unqualified"


@dataclass(frozen=True)
class FundEvidence:
    """Normalized ETF structure evidence used instead of company accounts."""

    as_of_date: str
    source_ids: tuple[str, ...]
    expense_ratio_pct: float
    annual_turnover_pct: float
    total_assets_usd: float
    holdings_count: int
    top_10_weight_pct: float
    largest_holding_weight_pct: float
    largest_sector_weight_pct: float
    cash_weight_pct: float


@dataclass(frozen=True)
class ValuationEvidence:
    """Normalized valuation inputs for an explicit value framework."""

    as_of_date: str
    source_ids: tuple[str, ...]
    market_price: float
    estimated_fair_value: float
    forward_pe: float
    sector_median_forward_pe: float
    ev_to_ebitda: float
    sector_median_ev_to_ebitda: float
    free_cash_flow_yield_pct: float
    earnings_growth_pct: float

    @property
    def margin_of_safety_pct(self) -> float:
        """Return discount to fair value; negative means overvaluation."""

        if self.estimated_fair_value <= 0:
            return float("-inf")
        return ((self.estimated_fair_value - self.market_price) / self.estimated_fair_value) * 100


@dataclass(frozen=True)
class FundValuationEvidence:
    """ETF portfolio valuation and growth relative to its provider category."""

    as_of_date: str
    source_ids: tuple[str, ...]
    prospective_pe: float
    category_prospective_pe: float
    price_to_cash_flow: float
    category_price_to_cash_flow: float
    long_term_earnings_growth_pct: float
    category_long_term_earnings_growth_pct: float
    historical_earnings_growth_pct: float
    sales_growth_pct: float
    cash_flow_growth_pct: float

    @property
    def cash_flow_yield_pct(self) -> float:
        return 100 / self.price_to_cash_flow if self.price_to_cash_flow > 0 else 0

    @property
    def category_cash_flow_yield_pct(self) -> float:
        denominator = self.category_price_to_cash_flow
        return 100 / denominator if denominator > 0 else 0


@dataclass(frozen=True)
class OperationalState:
    """Execution-time state that must pass deterministic safety checks."""

    market_open: bool
    quote_age_seconds: float
    daily_trade_count: int | None
    duplicate_signal: bool | None
    open_order_count: int | None
    minutes_since_last_trade: float | None


@dataclass(frozen=True)
class EvidenceRecord:
    """Prompt-safe evidence item with an addressable identifier."""

    evidence_id: str
    category: str
    value: Any
    unit: str | None
    source: str
    as_of_utc: str


@dataclass(frozen=True)
class ResearchContext:
    """Complete bounded input supplied to independent advisors."""

    underlying: str
    signal: StrategySignal
    as_of_utc: str
    operational: OperationalState
    news: tuple[NewsEvidence, ...] = ()
    financials: FinancialEvidence | None = None
    fund: FundEvidence | None = None
    valuation: ValuationEvidence | None = None
    fund_valuation: FundValuationEvidence | None = None

    def evidence_catalog(self) -> Mapping[str, EvidenceRecord]:
        """Return every permitted evidence ID; advisors may cite only these."""

        records: dict[str, EvidenceRecord] = {}

        def add(
            evidence_id: str,
            category: str,
            value: Any,
            unit: str | None,
            source: str,
            as_of: str | None = None,
        ) -> None:
            records[evidence_id] = EvidenceRecord(
                evidence_id=evidence_id,
                category=category,
                value=value,
                unit=unit,
                source=source,
                as_of_utc=as_of or self.as_of_utc,
            )

        signal = self.signal
        add("market:fast_return_pct", "technical", signal.fast_return_pct, "%", "alpaca")
        add("market:slow_return_pct", "technical", signal.slow_return_pct, "%", "alpaca")
        add(
            "market:realized_volatility_pct",
            "technical",
            signal.realized_volatility_pct,
            "% annualized",
            "alpaca",
        )
        add("option:symbol", "options", signal.option_symbol, None, "alpaca")
        add("option:limit_price", "options", signal.option_limit_price, "USD", "alpaca")
        add("option:spread_pct", "options", signal.option_spread_pct, "%", "alpaca")
        add("option:signal_confidence", "options", signal.confidence, "0-1", "ipulse")
        add("ops:market_open", "operations", self.operational.market_open, None, "alpaca")
        add(
            "ops:quote_age_seconds",
            "operations",
            self.operational.quote_age_seconds,
            "seconds",
            "ipulse",
        )
        add(
            "ops:daily_trade_count",
            "operations",
            self.operational.daily_trade_count,
            "count",
            "alpaca",
        )
        add(
            "ops:duplicate_signal",
            "operations",
            self.operational.duplicate_signal,
            None,
            "ipulse",
        )
        add(
            "ops:open_order_count",
            "operations",
            self.operational.open_order_count,
            "count",
            "alpaca",
        )
        add(
            "ops:minutes_since_last_trade",
            "operations",
            self.operational.minutes_since_last_trade,
            "minutes",
            "alpaca",
        )

        for item in self.news:
            add(
                item.evidence_id,
                "news",
                {
                    "headline": item.headline,
                    "summary": item.summary,
                    "sentiment_score": item.sentiment_score,
                },
                None,
                item.source,
                item.published_at_utc,
            )

        if self.financials is not None:
            financials = self.financials
            for field_name, unit in (
                ("revenue_growth_pct", "%"),
                ("gross_margin_pct", "%"),
                ("operating_margin_pct", "%"),
                ("free_cash_flow_margin_pct", "%"),
                ("cash_conversion_pct", "%"),
                ("accrual_ratio_pct", "%"),
                ("net_debt_to_ebitda", "x"),
                ("share_count_growth_pct", "%"),
                ("roic_pct", "%"),
                ("restatement_count", "count"),
                ("auditor_opinion", None),
            ):
                add(
                    f"financial:{field_name}",
                    "financials",
                    getattr(financials, field_name),
                    unit,
                    ",".join(financials.source_ids),
                    financials.as_of_date,
                )

        if self.fund is not None:
            fund = self.fund
            for field_name, unit in (
                ("expense_ratio_pct", "%"),
                ("annual_turnover_pct", "%"),
                ("total_assets_usd", "USD"),
                ("holdings_count", "count"),
                ("top_10_weight_pct", "%"),
                ("largest_holding_weight_pct", "%"),
                ("largest_sector_weight_pct", "%"),
                ("cash_weight_pct", "%"),
            ):
                add(
                    f"fund:{field_name}",
                    "financials",
                    getattr(fund, field_name),
                    unit,
                    ",".join(fund.source_ids),
                    fund.as_of_date,
                )

        if self.valuation is not None:
            valuation = self.valuation
            for field_name, unit in (
                ("market_price", "USD"),
                ("estimated_fair_value", "USD"),
                ("forward_pe", "x"),
                ("sector_median_forward_pe", "x"),
                ("ev_to_ebitda", "x"),
                ("sector_median_ev_to_ebitda", "x"),
                ("free_cash_flow_yield_pct", "%"),
                ("earnings_growth_pct", "%"),
                ("margin_of_safety_pct", "%"),
            ):
                value = (
                    valuation.margin_of_safety_pct
                    if field_name == "margin_of_safety_pct"
                    else getattr(valuation, field_name)
                )
                add(
                    f"valuation:{field_name}",
                    "valuation",
                    value,
                    unit,
                    ",".join(valuation.source_ids),
                    valuation.as_of_date,
                )

        if self.fund_valuation is not None:
            valuation = self.fund_valuation
            for field_name, unit in (
                ("prospective_pe", "x"),
                ("category_prospective_pe", "x"),
                ("price_to_cash_flow", "x"),
                ("category_price_to_cash_flow", "x"),
                ("cash_flow_yield_pct", "%"),
                ("category_cash_flow_yield_pct", "%"),
                ("long_term_earnings_growth_pct", "%"),
                ("category_long_term_earnings_growth_pct", "%"),
                ("historical_earnings_growth_pct", "%"),
                ("sales_growth_pct", "%"),
                ("cash_flow_growth_pct", "%"),
            ):
                add(
                    f"fund_valuation:{field_name}",
                    "valuation",
                    getattr(valuation, field_name),
                    unit,
                    ",".join(valuation.source_ids),
                    valuation.as_of_date,
                )
        return records

    def prompt_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible, evidence-only advisor payload."""

        return {
            "underlying": self.underlying,
            "as_of_utc": self.as_of_utc,
            "evidence": [asdict(item) for item in self.evidence_catalog().values()],
        }


@dataclass(frozen=True)
class AdvisorOpinion:
    """Auditable structured output from one independent advisor."""

    advisor: AdvisorName
    action: AdvisoryAction
    confidence: float
    thesis: str
    evidence_refs: tuple[str, ...] = ()
    contrary_evidence: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()
    max_entry_price: float | None = None
    hard_veto: bool = False
    abstention_reason: str | None = None
    reasoning_source: str = "deterministic"

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("Advisor confidence must be between zero and one.")
        if self.hard_veto and self.action is not AdvisoryAction.WAIT:
            raise ValueError("A hard veto must use the WAIT action.")
        if self.action is AdvisoryAction.ABSTAIN and not self.abstention_reason:
            raise ValueError("An abstention requires a reason.")

    @classmethod
    def from_mapping(
        cls,
        advisor: AdvisorName,
        payload: Mapping[str, Any],
        *,
        allowed_evidence_ids: frozenset[str],
        reasoning_source: str,
    ) -> "AdvisorOpinion":
        """Validate a model-produced opinion against the evidence catalog."""

        refs = tuple(str(item) for item in payload.get("evidence_refs", ()))
        unknown = set(refs).difference(allowed_evidence_ids)
        if unknown:
            raise ValueError("Advisor cited evidence outside the supplied catalog.")
        action = AdvisoryAction(str(payload["action"]))
        if action is not AdvisoryAction.ABSTAIN and not refs:
            raise ValueError("A directional or WAIT opinion must cite evidence.")
        max_entry_raw = payload.get("max_entry_price")
        max_entry = None if max_entry_raw is None else float(max_entry_raw)
        return cls(
            advisor=advisor,
            action=action,
            confidence=float(payload["confidence"]),
            thesis=str(payload["thesis"]),
            evidence_refs=refs,
            contrary_evidence=tuple(
                str(item) for item in payload.get("contrary_evidence", ())
            ),
            invalidation_conditions=tuple(
                str(item) for item in payload.get("invalidation_conditions", ())
            ),
            max_entry_price=max_entry,
            hard_veto=bool(payload.get("hard_veto", False)),
            abstention_reason=(
                None
                if payload.get("abstention_reason") is None
                else str(payload["abstention_reason"])
            ),
            reasoning_source=reasoning_source,
        )
