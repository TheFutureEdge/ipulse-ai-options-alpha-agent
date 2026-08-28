"""Strict adapters for externally produced research evidence.

The hackathon agent does not own filing ingestion or valuation-model execution.
It accepts only a small, versioned, normalized document and fails closed when
that evidence is malformed, mismatched, stale, or from the future.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from .research import (
    FinancialEvidence,
    FundEvidence,
    FundValuationEvidence,
    NewsEvidence,
    ValuationEvidence,
)


class EvidenceLoadError(ValueError):
    """Raised when normalized research evidence cannot be trusted."""


@dataclass(frozen=True)
class EvidenceFreshnessPolicy:
    """Maximum evidence ages used by the file adapter."""

    max_document_age: timedelta = timedelta(days=1)
    max_news_age: timedelta = timedelta(days=7)
    max_financial_age: timedelta = timedelta(days=400)
    max_valuation_age: timedelta = timedelta(days=31)
    future_clock_skew: timedelta = timedelta(minutes=5)
    max_document_bytes: int = 1_000_000


@dataclass(frozen=True)
class ResearchEvidenceBundle:
    """Validated external inputs plus reproducible document lineage."""

    underlying: str
    generated_at_utc: str
    document_sha256: str
    news: tuple[NewsEvidence, ...]
    financials: FinancialEvidence | None
    fund: FundEvidence | None
    valuation: ValuationEvidence | None
    fund_valuation: FundValuationEvidence | None


def _require_exact_keys(
    payload: Mapping[str, Any],
    *,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
    label: str,
) -> None:
    keys = frozenset(payload)
    missing = required.difference(keys)
    unknown = keys.difference(required.union(optional))
    if missing:
        raise EvidenceLoadError(f"{label} is missing fields: {sorted(missing)}")
    if unknown:
        raise EvidenceLoadError(f"{label} has unknown fields: {sorted(unknown)}")


def _parse_datetime(value: object, *, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceLoadError(f"{label} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise EvidenceLoadError(f"{label} must include a timezone.")
    return parsed.astimezone(UTC)


def _parse_date(value: object, *, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise EvidenceLoadError(f"{label} must be an ISO-8601 date.") from exc


def _number(
    payload: Mapping[str, Any],
    field: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    value = payload[field]
    if isinstance(value, bool):
        raise EvidenceLoadError(f"{field} must be numeric.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise EvidenceLoadError(f"{field} must be numeric.") from exc
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise EvidenceLoadError(
            f"{field} must be finite and between {minimum} and {maximum}."
        )
    return number


def _source_ids(value: object, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise EvidenceLoadError(f"{label} must be a non-empty list.")
    result = tuple(str(item).strip() for item in value)
    if any(not item or len(item) > 240 for item in result):
        raise EvidenceLoadError(f"{label} contains an invalid source identifier.")
    if len(set(result)) != len(result):
        raise EvidenceLoadError(f"{label} contains duplicate source identifiers.")
    return result


def _ensure_fresh_datetime(
    observed: datetime,
    *,
    now: datetime,
    maximum_age: timedelta,
    future_skew: timedelta,
    label: str,
) -> None:
    if observed > now + future_skew:
        raise EvidenceLoadError(f"{label} is too far in the future.")
    if now - observed > maximum_age:
        raise EvidenceLoadError(f"{label} is stale.")


def _ensure_fresh_date(
    observed: date,
    *,
    now: datetime,
    maximum_age: timedelta,
    label: str,
) -> None:
    observed_at = datetime.combine(observed, datetime.min.time(), tzinfo=UTC)
    if observed_at.date() > now.date():
        raise EvidenceLoadError(f"{label} is in the future.")
    if now - observed_at > maximum_age + timedelta(days=1):
        raise EvidenceLoadError(f"{label} is stale.")


def _parse_news(
    payload: object,
    *,
    now: datetime,
    policy: EvidenceFreshnessPolicy,
) -> tuple[NewsEvidence, ...]:
    if not isinstance(payload, list) or len(payload) > 20:
        raise EvidenceLoadError("news must be a list containing at most 20 items.")
    results: list[NewsEvidence] = []
    for index, raw in enumerate(payload):
        if not isinstance(raw, dict):
            raise EvidenceLoadError(f"news[{index}] must be an object.")
        _require_exact_keys(
            raw,
            required=frozenset(
                {
                    "evidence_id",
                    "headline",
                    "summary",
                    "source",
                    "published_at_utc",
                    "sentiment_score",
                }
            ),
            label=f"news[{index}]",
        )
        published = _parse_datetime(
            raw["published_at_utc"], label=f"news[{index}].published_at_utc"
        )
        _ensure_fresh_datetime(
            published,
            now=now,
            maximum_age=policy.max_news_age,
            future_skew=policy.future_clock_skew,
            label=f"news[{index}].published_at_utc",
        )
        evidence_id = str(raw["evidence_id"]).strip()
        if not evidence_id.startswith("news:") or len(evidence_id) > 240:
            raise EvidenceLoadError("News evidence IDs must begin with 'news:'.")
        headline = str(raw["headline"]).strip()
        summary = str(raw["summary"]).strip()
        source = str(raw["source"]).strip()
        if not headline or len(headline) > 500:
            raise EvidenceLoadError("News headlines must contain 1-500 characters.")
        if not summary or len(summary) > 4_000:
            raise EvidenceLoadError("News summaries must contain 1-4000 characters.")
        if not source or len(source) > 240:
            raise EvidenceLoadError("News sources must contain 1-240 characters.")
        results.append(
            NewsEvidence(
                evidence_id=evidence_id,
                headline=headline,
                summary=summary,
                source=source,
                published_at_utc=published.isoformat(),
                sentiment_score=_number(
                    raw, "sentiment_score", minimum=-1, maximum=1
                ),
            )
        )
    ids = [item.evidence_id for item in results]
    if len(set(ids)) != len(ids):
        raise EvidenceLoadError("News evidence IDs must be unique.")
    return tuple(results)


def _parse_financials(
    payload: object,
    *,
    now: datetime,
    policy: EvidenceFreshnessPolicy,
) -> FinancialEvidence | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise EvidenceLoadError("financials must be an object or null.")
    required = frozenset(
        {
            "as_of_date",
            "source_ids",
            "revenue_growth_pct",
            "gross_margin_pct",
            "operating_margin_pct",
            "free_cash_flow_margin_pct",
            "cash_conversion_pct",
            "accrual_ratio_pct",
            "net_debt_to_ebitda",
            "share_count_growth_pct",
            "roic_pct",
            "restatement_count",
            "auditor_opinion",
        }
    )
    _require_exact_keys(payload, required=required, label="financials")
    as_of = _parse_date(payload["as_of_date"], label="financials.as_of_date")
    _ensure_fresh_date(
        as_of,
        now=now,
        maximum_age=policy.max_financial_age,
        label="financials.as_of_date",
    )
    restatements = payload["restatement_count"]
    if isinstance(restatements, bool) or not isinstance(restatements, int):
        raise EvidenceLoadError("restatement_count must be an integer.")
    if not 0 <= restatements <= 100:
        raise EvidenceLoadError("restatement_count must be between 0 and 100.")
    opinion = str(payload["auditor_opinion"]).strip().lower()
    allowed_opinions = {
        "unqualified",
        "qualified",
        "adverse",
        "going_concern",
        "disclaimer",
        "unknown",
    }
    if opinion not in allowed_opinions:
        raise EvidenceLoadError("auditor_opinion is not a supported normalized value.")
    return FinancialEvidence(
        as_of_date=as_of.isoformat(),
        source_ids=_source_ids(payload["source_ids"], label="financials.source_ids"),
        revenue_growth_pct=_number(
            payload, "revenue_growth_pct", minimum=-100, maximum=1_000
        ),
        gross_margin_pct=_number(
            payload, "gross_margin_pct", minimum=-200, maximum=100
        ),
        operating_margin_pct=_number(
            payload, "operating_margin_pct", minimum=-500, maximum=100
        ),
        free_cash_flow_margin_pct=_number(
            payload, "free_cash_flow_margin_pct", minimum=-500, maximum=100
        ),
        cash_conversion_pct=_number(
            payload, "cash_conversion_pct", minimum=-1_000, maximum=1_000
        ),
        accrual_ratio_pct=_number(
            payload, "accrual_ratio_pct", minimum=-200, maximum=200
        ),
        net_debt_to_ebitda=_number(
            payload, "net_debt_to_ebitda", minimum=-100, maximum=100
        ),
        share_count_growth_pct=_number(
            payload, "share_count_growth_pct", minimum=-100, maximum=1_000
        ),
        roic_pct=_number(payload, "roic_pct", minimum=-500, maximum=1_000),
        restatement_count=restatements,
        auditor_opinion=opinion,
    )


def _parse_valuation(
    payload: object,
    *,
    now: datetime,
    policy: EvidenceFreshnessPolicy,
) -> ValuationEvidence | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise EvidenceLoadError("valuation must be an object or null.")
    required = frozenset(
        {
            "as_of_date",
            "source_ids",
            "market_price",
            "estimated_fair_value",
            "forward_pe",
            "sector_median_forward_pe",
            "ev_to_ebitda",
            "sector_median_ev_to_ebitda",
            "free_cash_flow_yield_pct",
            "earnings_growth_pct",
        }
    )
    _require_exact_keys(payload, required=required, label="valuation")
    as_of = _parse_date(payload["as_of_date"], label="valuation.as_of_date")
    _ensure_fresh_date(
        as_of,
        now=now,
        maximum_age=policy.max_valuation_age,
        label="valuation.as_of_date",
    )
    return ValuationEvidence(
        as_of_date=as_of.isoformat(),
        source_ids=_source_ids(payload["source_ids"], label="valuation.source_ids"),
        market_price=_number(payload, "market_price", minimum=0.0001, maximum=10_000_000),
        estimated_fair_value=_number(
            payload, "estimated_fair_value", minimum=0.0001, maximum=10_000_000
        ),
        forward_pe=_number(payload, "forward_pe", minimum=-10_000, maximum=10_000),
        sector_median_forward_pe=_number(
            payload, "sector_median_forward_pe", minimum=0.0001, maximum=10_000
        ),
        ev_to_ebitda=_number(
            payload, "ev_to_ebitda", minimum=-10_000, maximum=10_000
        ),
        sector_median_ev_to_ebitda=_number(
            payload, "sector_median_ev_to_ebitda", minimum=0.0001, maximum=10_000
        ),
        free_cash_flow_yield_pct=_number(
            payload, "free_cash_flow_yield_pct", minimum=-10_000, maximum=10_000
        ),
        earnings_growth_pct=_number(
            payload, "earnings_growth_pct", minimum=-1_000, maximum=10_000
        ),
    )


def _parse_fund(
    payload: object,
    *,
    now: datetime,
    policy: EvidenceFreshnessPolicy,
) -> FundEvidence | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise EvidenceLoadError("fund must be an object or null.")
    required = frozenset(
        {
            "as_of_date",
            "source_ids",
            "expense_ratio_pct",
            "annual_turnover_pct",
            "total_assets_usd",
            "holdings_count",
            "top_10_weight_pct",
            "largest_holding_weight_pct",
            "largest_sector_weight_pct",
            "cash_weight_pct",
        }
    )
    _require_exact_keys(payload, required=required, label="fund")
    as_of = _parse_date(payload["as_of_date"], label="fund.as_of_date")
    _ensure_fresh_date(
        as_of,
        now=now,
        maximum_age=policy.max_financial_age,
        label="fund.as_of_date",
    )
    holdings_count = payload["holdings_count"]
    if isinstance(holdings_count, bool) or not isinstance(holdings_count, int):
        raise EvidenceLoadError("holdings_count must be an integer.")
    if not 1 <= holdings_count <= 1_000_000:
        raise EvidenceLoadError("holdings_count is outside the supported range.")
    return FundEvidence(
        as_of_date=as_of.isoformat(),
        source_ids=_source_ids(payload["source_ids"], label="fund.source_ids"),
        expense_ratio_pct=_number(
            payload, "expense_ratio_pct", minimum=0, maximum=100
        ),
        annual_turnover_pct=_number(
            payload, "annual_turnover_pct", minimum=0, maximum=10_000
        ),
        total_assets_usd=_number(
            payload, "total_assets_usd", minimum=0, maximum=1e16
        ),
        holdings_count=holdings_count,
        top_10_weight_pct=_number(
            payload, "top_10_weight_pct", minimum=0, maximum=100
        ),
        largest_holding_weight_pct=_number(
            payload, "largest_holding_weight_pct", minimum=0, maximum=100
        ),
        largest_sector_weight_pct=_number(
            payload, "largest_sector_weight_pct", minimum=0, maximum=100
        ),
        cash_weight_pct=_number(
            payload, "cash_weight_pct", minimum=-100, maximum=100
        ),
    )


def _parse_fund_valuation(
    payload: object,
    *,
    now: datetime,
    policy: EvidenceFreshnessPolicy,
) -> FundValuationEvidence | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise EvidenceLoadError("fund_valuation must be an object or null.")
    required = frozenset(
        {
            "as_of_date",
            "source_ids",
            "prospective_pe",
            "category_prospective_pe",
            "price_to_cash_flow",
            "category_price_to_cash_flow",
            "long_term_earnings_growth_pct",
            "category_long_term_earnings_growth_pct",
            "historical_earnings_growth_pct",
            "sales_growth_pct",
            "cash_flow_growth_pct",
        }
    )
    _require_exact_keys(payload, required=required, label="fund_valuation")
    as_of = _parse_date(
        payload["as_of_date"], label="fund_valuation.as_of_date"
    )
    _ensure_fresh_date(
        as_of,
        now=now,
        maximum_age=policy.max_valuation_age,
        label="fund_valuation.as_of_date",
    )
    return FundValuationEvidence(
        as_of_date=as_of.isoformat(),
        source_ids=_source_ids(
            payload["source_ids"], label="fund_valuation.source_ids"
        ),
        prospective_pe=_number(
            payload, "prospective_pe", minimum=0.0001, maximum=10_000
        ),
        category_prospective_pe=_number(
            payload, "category_prospective_pe", minimum=0.0001, maximum=10_000
        ),
        price_to_cash_flow=_number(
            payload, "price_to_cash_flow", minimum=0.0001, maximum=10_000
        ),
        category_price_to_cash_flow=_number(
            payload,
            "category_price_to_cash_flow",
            minimum=0.0001,
            maximum=10_000,
        ),
        long_term_earnings_growth_pct=_number(
            payload,
            "long_term_earnings_growth_pct",
            minimum=-1_000,
            maximum=10_000,
        ),
        category_long_term_earnings_growth_pct=_number(
            payload,
            "category_long_term_earnings_growth_pct",
            minimum=-1_000,
            maximum=10_000,
        ),
        historical_earnings_growth_pct=_number(
            payload,
            "historical_earnings_growth_pct",
            minimum=-1_000,
            maximum=10_000,
        ),
        sales_growth_pct=_number(
            payload, "sales_growth_pct", minimum=-1_000, maximum=10_000
        ),
        cash_flow_growth_pct=_number(
            payload, "cash_flow_growth_pct", minimum=-1_000, maximum=10_000
        ),
    )


def load_json_research_evidence(
    path: Path,
    *,
    underlying: str,
    now: datetime | None = None,
    policy: EvidenceFreshnessPolicy | None = None,
) -> ResearchEvidenceBundle:
    """Load one normalized evidence document without accepting credentials."""

    effective_policy = policy or EvidenceFreshnessPolicy()
    effective_now = (now or datetime.now(UTC)).astimezone(UTC)
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise EvidenceLoadError(f"Cannot read research evidence file: {path}") from exc
    if not raw_bytes or len(raw_bytes) > effective_policy.max_document_bytes:
        raise EvidenceLoadError("Research evidence file is empty or exceeds the size limit.")
    try:
        payload = json.loads(raw_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceLoadError("Research evidence file is not valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise EvidenceLoadError("Research evidence root must be an object.")
    _require_exact_keys(
        payload,
        required=frozenset(
            {
                "schema_version",
                "underlying",
                "generated_at_utc",
                "news",
                "financials",
                "valuation",
            }
        ),
        optional=frozenset({"fund", "fund_valuation"}),
        label="research evidence",
    )
    if payload["schema_version"] != 1:
        raise EvidenceLoadError("Only research evidence schema_version 1 is supported.")
    document_underlying = str(payload["underlying"]).strip().upper()
    if document_underlying != underlying.strip().upper():
        raise EvidenceLoadError("Research evidence underlying does not match the run.")
    generated = _parse_datetime(
        payload["generated_at_utc"], label="generated_at_utc"
    )
    _ensure_fresh_datetime(
        generated,
        now=effective_now,
        maximum_age=effective_policy.max_document_age,
        future_skew=effective_policy.future_clock_skew,
        label="generated_at_utc",
    )
    return ResearchEvidenceBundle(
        underlying=document_underlying,
        generated_at_utc=generated.isoformat(),
        document_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        news=_parse_news(
            payload["news"], now=effective_now, policy=effective_policy
        ),
        financials=_parse_financials(
            payload["financials"], now=effective_now, policy=effective_policy
        ),
        fund=_parse_fund(
            payload.get("fund"), now=effective_now, policy=effective_policy
        ),
        valuation=_parse_valuation(
            payload["valuation"], now=effective_now, policy=effective_policy
        ),
        fund_valuation=_parse_fund_valuation(
            payload.get("fund_valuation"),
            now=effective_now,
            policy=effective_policy,
        ),
    )
