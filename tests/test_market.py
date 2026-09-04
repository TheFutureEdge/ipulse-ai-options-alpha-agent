"""Unit tests for Alpaca market-data normalization."""

from __future__ import annotations

import unittest

from ipulse_options_alpha_agent.market import (
    AlpacaMarketAdapter,
    MarketSignalUnavailable,
    compute_regime,
    extract_option_candidates,
    extract_quote_midpoint,
    select_option,
)


class MarketTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_reversal_scan_selects_strongest_signal_and_opposite_contract(
        self,
    ) -> None:
        class FakeClient:
            def __init__(self) -> None:
                self.option_request: dict[str, object] | None = None

            async def call_json(
                self, tool_name: str, arguments: dict[str, object]
            ) -> dict[str, object]:
                if tool_name == "get_stock_bars":
                    symbol = str(arguments["symbols"])
                    closes = [100.0] * 20
                    closes.extend(
                        [101.0, 102.0, 103.0, 104.0, 106.0]
                        if symbol == "QQQ"
                        else [100.1, 100.2, 100.3, 100.4, 100.6]
                    )
                    return {
                        "data": {
                            "bars": {
                                symbol: [
                                    {"c": close} for close in closes
                                ]
                            }
                        }
                    }
                if tool_name == "get_stock_latest_quote":
                    return {
                        "data": {
                            "quotes": {"QQQ": {"bp": 105.9, "ap": 106.1}}
                        }
                    }
                if tool_name == "get_option_chain":
                    self.option_request = arguments
                    return {
                        "data": {
                            "snapshots": {
                                "QQQ260911P00106000": {
                                    "latestQuote": {
                                        "bp": 2.45,
                                        "ap": 2.55,
                                        "t": "2026-09-04T14:00:00Z",
                                    },
                                    "greeks": {"delta": -0.50},
                                    "impliedVolatility": 0.22,
                                    "dailyBar": {"v": 500},
                                }
                            }
                        }
                    }
                raise AssertionError(tool_name)

        client = FakeClient()
        evaluation = await AlpacaMarketAdapter(client).build_reversal_evaluation()
        self.assertEqual(evaluation.signal.underlying, "QQQ")
        self.assertIn("P", evaluation.signal.option_symbol[-9:])
        self.assertEqual(client.option_request and client.option_request["type"], "put")


if __name__ == "__main__":
    unittest.main()
