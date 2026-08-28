"""Unit tests for Alpaca market-data normalization."""

from __future__ import annotations

import unittest

from ipulse_options_alpha_agent.market import (
    MarketSignalUnavailable,
    compute_regime,
    extract_option_candidates,
    extract_quote_midpoint,
    select_option,
)


class MarketTests(unittest.TestCase):
    """Verify deterministic market parsing and contract selection."""

    def test_extracts_quote_midpoint(self) -> None:
        payload = {
            "data": {"quotes": {"SPY": {"bp": 499.8, "ap": 500.2}}}
        }
        self.assertEqual(extract_quote_midpoint(payload, "SPY"), 500.0)

    def test_computes_positive_regime(self) -> None:
        bars = [{"c": 100 + index} for index in range(25)]
        fast, slow, volatility = compute_regime(bars)
        self.assertGreater(fast, 0)
        self.assertGreater(slow, 0)
        self.assertGreaterEqual(volatility, 0)

    def test_selects_liquid_near_half_delta_contract(self) -> None:
        payload = {
            "data": {
                "snapshots": {
                    "SPY_CALL_WIDE": {
                        "latestQuote": {"bp": 2.0, "ap": 3.0},
                        "greeks": {"delta": 0.50},
                        "impliedVolatility": 0.20,
                        "dailyBar": {"v": 100},
                    },
                    "SPY_CALL_LIQUID": {
                        "latestQuote": {"bp": 2.45, "ap": 2.55},
                        "greeks": {"delta": 0.52},
                        "impliedVolatility": 0.21,
                        "dailyBar": {"v": 500},
                    },
                }
            }
        }
        candidate = select_option(
            extract_option_candidates(payload), direction="call"
        )
        self.assertEqual(candidate.symbol, "SPY_CALL_LIQUID")
        self.assertAlmostEqual(candidate.midpoint, 2.50)

    def test_rejects_contracts_above_risk_budget(self) -> None:
        payload = {
            "data": {
                "snapshots": {
                    "SPY_CALL_EXPENSIVE": {
                        "latestQuote": {"bp": 8.9, "ap": 9.1},
                        "greeks": {"delta": 0.50},
                        "impliedVolatility": 0.20,
                        "dailyBar": {"v": 1000},
                    }
                }
            }
        }
        with self.assertRaises(MarketSignalUnavailable):
            select_option(extract_option_candidates(payload), direction="call")


if __name__ == "__main__":
    unittest.main()
