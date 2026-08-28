"""Read-only adapter from iPulse BigQuery ETF snapshots to research evidence."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Mapping, Protocol

from .research import FundEvidence, FundValuationEvidence


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,200}$")
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9.-]{1,20}$")


class IPulseEvidenceUnavailable(RuntimeError):
    """Raised when a trustworthy iPulse snapshot cannot be produced."""


class SnapshotQueryRunner(Protocol):
    """Minimal injectable query interface for the evidence adapter."""

    def latest_fund_snapshot(self, provider_symbol: str) -> Mapping[str, Any] | None:
        """Return the latest normalized ETF snapshot row."""


@dataclass(frozen=True)
class IPulseFundResearchEvidence:
    """Fund structure plus optional valuation from the same snapshot."""

    fund: FundEvidence
    valuation: FundValuationEvidence | None


@dataclass(frozen=True)
class BqCliSnapshotQueryRunner:
    """Execute one parameterized read-only query through the existing bq CLI."""

    project_id: str
    dataset: str
    timeout_seconds: float = 30

    def __post_init__(self) -> None:
        if not IDENTIFIER_PATTERN.fullmatch(self.project_id):
            raise ValueError("Invalid BigQuery project identifier.")
        if not IDENTIFIER_PATTERN.fullmatch(self.dataset):
            raise ValueError("Invalid BigQuery dataset identifier.")

    def latest_fund_snapshot(self, provider_symbol: str) -> Mapping[str, Any] | None:
        if not SYMBOL_PATTERN.fullmatch(provider_symbol):
            raise ValueError("Invalid provider symbol.")
        table = f"{self.project_id}.{self.dataset}.fundamental_subject_snapshots"
        sql = (
            "SELECT snapshot_id, provider_updated_date, observed_at_utc, "
            "fund_profile_json, fund_composition_json, curated_payload_json "
            f"FROM `{table}` "
            "WHERE symbol_at_provider_eodhd = @provider_symbol "
            "ORDER BY observed_at_utc DESC LIMIT 1"
        )
        command = [
            "bq",
            "query",
            f"--project_id={self.project_id}",
            "--use_legacy_sql=false",
            "--format=json",
            f"--parameter=provider_symbol:STRING:{provider_symbol}",
            sql,
        ]
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise IPulseEvidenceUnavailable(
                "The read-only iPulse BigQuery snapshot query failed."
            ) from exc
        try:
            rows = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise IPulseEvidenceUnavailable(
                "The iPulse BigQuery query did not return JSON."
            ) from exc
        if not isinstance(rows, list):
            raise IPulseEvidenceUnavailable("The iPulse BigQuery result is malformed.")
        if not rows:
            return None
        row = rows[0]
        if not isinstance(row, dict):
            raise IPulseEvidenceUnavailable("The iPulse BigQuery row is malformed.")
        return row


def _json_object(value: object, *, label: str) -> dict[str, Any]:
    try:
        decoded = json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise IPulseEvidenceUnavailable(f"{label} is not valid JSON.") from exc
    if not isinstance(decoded, dict):
        raise IPulseEvidenceUnavailable(f"{label} is not a JSON object.")
    return decoded


def _finite_number(value: object, *, label: str) -> float:
    try:
        number = float(str(value))
    except (TypeError, ValueError) as exc:
        raise IPulseEvidenceUnavailable(f"{label} is not numeric.") from exc
    if not math.isfinite(number):
        raise IPulseEvidenceUnavailable(f"{label} is not finite.")
    return number


def _ratio_as_pct(value: object, *, label: str) -> float:
    number = _finite_number(value, label=label)
    return number * 100 if abs(number) <= 1 else number


def fund_evidence_from_snapshot(
    row: Mapping[str, Any],
    *,
    now: datetime | None = None,
    maximum_age: timedelta = timedelta(days=31),
) -> FundEvidence:
    """Convert one curated iPulse ETF row without inventing absent metrics."""

    effective_now = (now or datetime.now(UTC)).astimezone(UTC)
    try:
        as_of = date.fromisoformat(str(row["provider_updated_date"]))
    except (KeyError, ValueError) as exc:
        raise IPulseEvidenceUnavailable(
            "The fund snapshot has no valid provider update date."
        ) from exc
    age = effective_now - datetime.combine(as_of, datetime.min.time(), tzinfo=UTC)
    if as_of > effective_now.date() or age > maximum_age + timedelta(days=1):
        raise IPulseEvidenceUnavailable("The fund snapshot is stale or future-dated.")

    profile = _json_object(row.get("fund_profile_json"), label="fund_profile_json")
    composition = _json_object(
        row.get("fund_composition_json"), label="fund_composition_json"
    )
    curated = _json_object(
        row.get("curated_payload_json"), label="curated_payload_json"
    )
    top_holdings = curated.get("Top_10_Holdings")
    if not isinstance(top_holdings, dict) or not top_holdings:
        raise IPulseEvidenceUnavailable("The fund snapshot has no top holdings.")
    holding_weights = [
        _finite_number(value.get("Assets_%"), label="holding weight")
        for value in top_holdings.values()
        if isinstance(value, dict) and value.get("Assets_%") is not None
    ]
    if not holding_weights:
        raise IPulseEvidenceUnavailable("The fund snapshot has no holding weights.")
    sectors = composition.get("Sector_Weights_Top5")
    if not isinstance(sectors, list) or not sectors:
        raise IPulseEvidenceUnavailable("The fund snapshot has no sector weights.")
    sector_weights = [
        _finite_number(value.get("Equity_%"), label="sector weight")
        for value in sectors
        if isinstance(value, dict) and value.get("Equity_%") is not None
    ]
    allocations = composition.get("Asset_Allocation")
    cash = allocations.get("Cash") if isinstance(allocations, dict) else None
    if not isinstance(cash, dict):
        raise IPulseEvidenceUnavailable("The fund snapshot has no cash allocation.")
    snapshot_id = str(row.get("snapshot_id", "")).strip()
    if not snapshot_id:
        raise IPulseEvidenceUnavailable("The fund snapshot has no lineage ID.")
    holdings_count = int(
        _finite_number(profile.get("Holdings_Count"), label="holdings count")
    )
    if holdings_count <= 0:
        raise IPulseEvidenceUnavailable("The fund holdings count is invalid.")
    return FundEvidence(
        as_of_date=as_of.isoformat(),
        source_ids=(f"ipulse-bigquery:{snapshot_id}",),
        expense_ratio_pct=_ratio_as_pct(
            profile.get("NetExpenseRatio"), label="expense ratio"
        ),
        annual_turnover_pct=_ratio_as_pct(
            profile.get("AnnualHoldingsTurnover"), label="annual turnover"
        ),
        total_assets_usd=_finite_number(
            profile.get("TotalAssets"), label="total assets"
        ),
        holdings_count=holdings_count,
        top_10_weight_pct=sum(holding_weights),
        largest_holding_weight_pct=max(holding_weights),
        largest_sector_weight_pct=max(sector_weights),
        cash_weight_pct=_finite_number(
            cash.get("Net_Assets_%"), label="cash weight"
        ),
    )


def fund_valuation_evidence_from_snapshot(
    row: Mapping[str, Any],
    *,
    now: datetime | None = None,
    maximum_age: timedelta = timedelta(days=31),
) -> FundValuationEvidence:
    """Map provider portfolio/category comparisons from a curated ETF row."""

    # Reuse the structural parser's lineage and freshness validation.
    fund = fund_evidence_from_snapshot(row, now=now, maximum_age=maximum_age)
    curated = _json_object(
        row.get("curated_payload_json"), label="curated_payload_json"
    )
    root = curated.get("FundValuationGrowth")
    if not isinstance(root, dict) or not root:
        raise IPulseEvidenceUnavailable(
            "The fund snapshot has no curated valuation-growth evidence."
        )
    portfolio_value = root.get("Valuations_Rates_Portfolio")
    category_value = root.get("Valuations_Rates_To_Category")
    portfolio_growth = root.get("Growth_Rates_Portfolio")
    category_growth = root.get("Growth_Rates_To_Category")
    if not all(
        isinstance(value, dict)
        for value in (
            portfolio_value,
            category_value,
            portfolio_growth,
            category_growth,
        )
    ):
        raise IPulseEvidenceUnavailable(
            "The fund valuation-growth groups are incomplete."
        )
    assert isinstance(portfolio_value, dict)
    assert isinstance(category_value, dict)
    assert isinstance(portfolio_growth, dict)
    assert isinstance(category_growth, dict)
    return FundValuationEvidence(
        as_of_date=fund.as_of_date,
        source_ids=fund.source_ids,
        prospective_pe=_finite_number(
            portfolio_value.get("Price/Prospective Earnings"),
            label="portfolio prospective P/E",
        ),
        category_prospective_pe=_finite_number(
            category_value.get("Price/Prospective Earnings"),
            label="category prospective P/E",
        ),
        price_to_cash_flow=_finite_number(
            portfolio_value.get("Price/Cash Flow"),
            label="portfolio price to cash flow",
        ),
        category_price_to_cash_flow=_finite_number(
            category_value.get("Price/Cash Flow"),
            label="category price to cash flow",
        ),
        long_term_earnings_growth_pct=_finite_number(
            portfolio_growth.get("Long-Term Projected Earnings Growth"),
            label="portfolio long-term earnings growth",
        ),
        category_long_term_earnings_growth_pct=_finite_number(
            category_growth.get("Long-Term Projected Earnings Growth"),
            label="category long-term earnings growth",
        ),
        historical_earnings_growth_pct=_finite_number(
            portfolio_growth.get("Historical Earnings Growth"),
            label="portfolio historical earnings growth",
        ),
        sales_growth_pct=_finite_number(
            portfolio_growth.get("Sales Growth"),
            label="portfolio sales growth",
        ),
        cash_flow_growth_pct=_finite_number(
            portfolio_growth.get("Cash-Flow Growth"),
            label="portfolio cash-flow growth",
        ),
    )


def configured_bq_runner() -> BqCliSnapshotQueryRunner:
    """Build a runner only from explicit non-secret environment configuration."""

    project_id = os.environ.get("IPULSE_BQ_PROJECT_ID", "").strip()
    dataset = os.environ.get("IPULSE_BQ_FUNDAMENTAL_DATASET", "").strip()
    if not project_id or not dataset:
        raise IPulseEvidenceUnavailable(
            "IPULSE_BQ_PROJECT_ID and IPULSE_BQ_FUNDAMENTAL_DATASET are required."
        )
    return BqCliSnapshotQueryRunner(project_id=project_id, dataset=dataset)


def load_ipulse_fund_evidence(
    underlying: str,
    *,
    runner: SnapshotQueryRunner | None = None,
    now: datetime | None = None,
) -> FundEvidence:
    """Load a fresh ETF structural audit record for one US symbol."""

    symbol = underlying.strip().upper()
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise IPulseEvidenceUnavailable("Underlying symbol is invalid.")
    effective_runner = runner or configured_bq_runner()
    row = effective_runner.latest_fund_snapshot(f"{symbol}.US")
    if row is None:
        raise IPulseEvidenceUnavailable("No iPulse fund snapshot was found.")
    return fund_evidence_from_snapshot(row, now=now)


def load_ipulse_fund_research_evidence(
    underlying: str,
    *,
    runner: SnapshotQueryRunner | None = None,
    now: datetime | None = None,
) -> IPulseFundResearchEvidence:
    """Load one snapshot once and map every supported fund research view."""

    symbol = underlying.strip().upper()
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise IPulseEvidenceUnavailable("Underlying symbol is invalid.")
    effective_runner = runner or configured_bq_runner()
    row = effective_runner.latest_fund_snapshot(f"{symbol}.US")
    if row is None:
        raise IPulseEvidenceUnavailable("No iPulse fund snapshot was found.")
    fund = fund_evidence_from_snapshot(row, now=now)
    try:
        valuation = fund_valuation_evidence_from_snapshot(row, now=now)
    except IPulseEvidenceUnavailable:
        valuation = None
    return IPulseFundResearchEvidence(fund=fund, valuation=valuation)
