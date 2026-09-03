"""Tests for leakage-resistant historical signal scoring."""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from ipulse_options_alpha_agent.backtest import (
    ReversalConfig,
    build_scorecard,
    generate_signal_outcomes,
)


def bars(closes: list[float]) -> list[dict[str, object]]:
    """Build minimal deterministic daily bars."""

    start = date(2023, 11, 1)
    return [
        {"timestamp": (start + timedelta(days=index)).isoformat(), "close": close}
        for index, close in enumerate(closes)
    ]


class BacktestTests(unittest.TestCase):
    """Verify timing, reversal direction, and holdout separation."""

    def test_positive_exhaustion_creates_put_scored_two_sessions_later(self) -> None:
        closes = [100 + index * 0.05 for index in range(21)]
        closes.extend([104.0, 102.0, 101.0])
        outcomes = generate_signal_outcomes(
            {"SPY": bars(closes)},
            ReversalConfig(max_realized_volatility_pct=100),
        )
        self.assertTrue(outcomes)
        first = outcomes[0]
        self.assertEqual(first.direction, "PUT")
        self.assertGreater(first.signed_return_pct, 0)
        self.assertEqual(first.exit_date, bars(closes)[23]["timestamp"])

    def test_selection_uses_signal_strength_not_future_return(self) -> None:
        base = [100 + index * 0.02 for index in range(21)]
        weaker = base + [104.0, 103.0, 102.0]
        stronger = base + [106.0, 108.0, 110.0]
        outcomes = generate_signal_outcomes(
            {"SPY": bars(weaker), "QQQ": bars(stronger)},
            ReversalConfig(max_realized_volatility_pct=100),
        )
        self.assertEqual(outcomes[0].symbol, "QQQ")

    def test_scorecard_keeps_holdout_separate(self) -> None:
        closes = [100 + index * 0.05 for index in range(65)]
        closes[21] = 106
        closes[22] = 104
        closes[23] = 103
        scorecard = build_scorecard(
            {"SPY": bars(closes)},
            ReversalConfig(
                max_realized_volatility_pct=100,
                development_cutoff="2023-12-01",
            ),
        )
        self.assertIn("development", scorecard)
        self.assertIn("holdout", scorecard)
        self.assertEqual(
            scorecard["methodology"]["interpretation"],
            "Directional signal proxy; not executable option P&L.",
        )


if __name__ == "__main__":
    unittest.main()
