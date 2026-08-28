"""Tests for the read-only iPulse ETF fundamentals adapter."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime

from ipulse_options_alpha_agent.ipulse_evidence import (
    IPulseEvidenceUnavailable,
    fund_evidence_from_snapshot,
    fund_valuation_evidence_from_snapshot,
)


def snapshot_row() -> dict[str, object]:
    return {
        "snapshot_id": "snapshot-spy-1",
        "provider_updated_date": "2026-08-26",
        "observed_at_utc": "2026-08-27 03:07:53",
        "fund_profile_json": json.dumps(
            {
                "NetExpenseRatio": "0.00095",
                "AnnualHoldingsTurnover": "0.02000",
                "TotalAssets": "807460814119.00",
                "Holdings_Count": 500,
            }
        ),
        "fund_composition_json": json.dumps(
            {
                "Asset_Allocation": {"Cash": {"Net_Assets_%": "0.1036"}},
                "Sector_Weights_Top5": [
                    {"label": "Technology", "Equity_%": "37.50019"},
                    {"label": "Financial Services", "Equity_%": "12.22452"},
                ],
            }
        ),
        "curated_payload_json": json.dumps(
            {
                "Top_10_Holdings": {
                    "NVDA.US": {"Assets_%": 7.66247},
                    "AAPL.US": {"Assets_%": 6.91673},
                    "MSFT.US": {"Assets_%": 5.4931},
                },
                "FundValuationGrowth": {
                    "Valuations_Rates_Portfolio": {
                        "Price/Prospective Earnings": "18",
                        "Price/Cash Flow": "12",
                    },
                    "Valuations_Rates_To_Category": {
                        "Price/Prospective Earnings": "20",
                        "Price/Cash Flow": "14",
                    },
                    "Growth_Rates_Portfolio": {
                        "Long-Term Projected Earnings Growth": "11",
                        "Historical Earnings Growth": "8",
                        "Sales Growth": "7",
                        "Cash-Flow Growth": "8",
                    },
                    "Growth_Rates_To_Category": {
                        "Long-Term Projected Earnings Growth": "9"
                    },
                },
            }
        ),
    }


class IPulseEvidenceTests(unittest.TestCase):
    def test_maps_curated_snapshot_to_fund_audit(self) -> None:
        evidence = fund_evidence_from_snapshot(
            snapshot_row(),
            now=datetime(2026, 8, 28, 14, 0, tzinfo=UTC),
        )
        self.assertAlmostEqual(evidence.expense_ratio_pct, 0.095)
        self.assertAlmostEqual(evidence.annual_turnover_pct, 2)
        self.assertAlmostEqual(evidence.top_10_weight_pct, 20.0723, places=3)
        self.assertEqual(evidence.largest_sector_weight_pct, 37.50019)
        self.assertEqual(evidence.source_ids, ("ipulse-bigquery:snapshot-spy-1",))

    def test_rejects_stale_snapshot(self) -> None:
        row = snapshot_row()
        row["provider_updated_date"] = "2025-01-01"
        with self.assertRaisesRegex(IPulseEvidenceUnavailable, "stale"):
            fund_evidence_from_snapshot(
                row,
                now=datetime(2026, 8, 28, 14, 0, tzinfo=UTC),
            )

    def test_maps_curated_fund_relative_value(self) -> None:
        evidence = fund_valuation_evidence_from_snapshot(
            snapshot_row(),
            now=datetime(2026, 8, 28, 14, 0, tzinfo=UTC),
        )
        self.assertEqual(evidence.prospective_pe, 18)
        self.assertEqual(evidence.category_prospective_pe, 20)
        self.assertAlmostEqual(evidence.cash_flow_yield_pct, 100 / 12)
        self.assertEqual(evidence.cash_flow_growth_pct, 8)


if __name__ == "__main__":
    unittest.main()
