"""Tests for strict, freshness-aware external research evidence loading."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ipulse_options_alpha_agent.evidence_sources import (
    EvidenceLoadError,
    load_json_research_evidence,
)


NOW = datetime(2026, 8, 28, 14, 0, tzinfo=UTC)


def document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "underlying": "SPY",
        "generated_at_utc": (NOW - timedelta(minutes=2)).isoformat(),
        "news": [
            {
                "evidence_id": "news:primary:1",
                "headline": "Aggregate earnings revisions improved",
                "summary": "A bounded normalized news summary.",
                "source": "primary-source",
                "published_at_utc": (NOW - timedelta(hours=2)).isoformat(),
                "sentiment_score": 0.3,
            }
        ],
        "financials": {
            "as_of_date": "2026-06-30",
            "source_ids": ["ipulse:facts:spy:2026q2"],
            "revenue_growth_pct": 10,
            "gross_margin_pct": 50,
            "operating_margin_pct": 20,
            "free_cash_flow_margin_pct": 15,
            "cash_conversion_pct": 90,
            "accrual_ratio_pct": 2,
            "net_debt_to_ebitda": 1,
            "share_count_growth_pct": 0,
            "roic_pct": 12,
            "restatement_count": 0,
            "auditor_opinion": "unqualified",
        },
        "fund": None,
        "fund_valuation": None,
        "valuation": {
            "as_of_date": "2026-08-27",
            "source_ids": ["ipulse:value:spy:2026-08-27"],
            "market_price": 80,
            "estimated_fair_value": 100,
            "forward_pe": 15,
            "sector_median_forward_pe": 20,
            "ev_to_ebitda": 10,
            "sector_median_ev_to_ebitda": 12,
            "free_cash_flow_yield_pct": 5,
            "earnings_growth_pct": 8,
        },
    }


class EvidenceSourceTests(unittest.TestCase):
    def load(self, payload: dict[str, object]):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_json_research_evidence(path, underlying="SPY", now=NOW)

    def test_loads_complete_normalized_bundle_with_hash(self) -> None:
        bundle = self.load(document())
        self.assertEqual(bundle.underlying, "SPY")
        self.assertEqual(len(bundle.news), 1)
        self.assertIsNotNone(bundle.financials)
        self.assertIsNone(bundle.fund)
        self.assertIsNone(bundle.fund_valuation)
        self.assertIsNotNone(bundle.valuation)
        self.assertEqual(len(bundle.document_sha256), 64)

    def test_rejects_underlying_mismatch(self) -> None:
        payload = document()
        payload["underlying"] = "QQQ"
        with self.assertRaisesRegex(EvidenceLoadError, "does not match"):
            self.load(payload)

    def test_rejects_stale_document(self) -> None:
        payload = document()
        payload["generated_at_utc"] = (NOW - timedelta(days=2)).isoformat()
        with self.assertRaisesRegex(EvidenceLoadError, "stale"):
            self.load(payload)

    def test_rejects_unknown_fields(self) -> None:
        payload = document()
        financials = payload["financials"]
        assert isinstance(financials, dict)
        financials["invented_metric"] = 1
        with self.assertRaisesRegex(EvidenceLoadError, "unknown fields"):
            self.load(payload)

    def test_rejects_duplicate_news_ids(self) -> None:
        payload = document()
        news = payload["news"]
        assert isinstance(news, list)
        news.append(dict(news[0]))
        with self.assertRaisesRegex(EvidenceLoadError, "must be unique"):
            self.load(payload)


if __name__ == "__main__":
    unittest.main()
