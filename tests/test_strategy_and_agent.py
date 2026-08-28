"""Unit tests for strategy decisions and agent orchestration."""

from __future__ import annotations

import unittest

from ipulse_options_alpha_agent import OptionsAlphaAgent, PortfolioSnapshot
from ipulse_options_alpha_agent.strategy import MomentumRegimeStrategy, StrategySignal


def signal(**overrides: float | str) -> StrategySignal:
    """Create a strong but bounded CALL signal."""

    values: dict[str, float | str] = {
        "underlying": "SPY",
        "option_symbol": "SPY_TEST_CALL",
        "option_limit_price": 2.0,
        "fast_return_pct": 0.5,
        "slow_return_pct": 0.8,
        "realized_volatility_pct": 20.0,
        "option_spread_pct": 3.0,
        "confidence": 0.75,
    }
    values.update(overrides)
    return StrategySignal(**values)  # type: ignore[arg-type]


class StrategyAndAgentTests(unittest.TestCase):
    """Verify no-trade and approved paths."""

    def setUp(self) -> None:
        """Create an empty development paper portfolio."""

        self.portfolio = PortfolioSnapshot(
            equity=100_000,
            cash=100_000,
            buying_power=400_000,
            daily_pnl=0,
            open_positions=0,
        )

    def test_strategy_waits_on_low_confidence(self) -> None:
        """Weak evidence must not create an order proposal."""

        proposal = MomentumRegimeStrategy().propose(signal(confidence=0.40))
        self.assertIsNone(proposal)

    def test_agent_approves_strong_bounded_paper_signal(self) -> None:
        """Aligned evidence plus safe risk should produce APPROVE."""

        decision = OptionsAlphaAgent().decide(
            signal(), self.portfolio, paper_environment=True
        )
        self.assertEqual(decision.action, "APPROVE")
        self.assertIsNotNone(decision.proposal)
        self.assertTrue(decision.risk and decision.risk.approved)

    def test_agent_waits_when_direction_is_not_aligned(self) -> None:
        """Mixed trends should produce WAIT rather than forced trading."""

        decision = OptionsAlphaAgent().decide(
            signal(fast_return_pct=0.5, slow_return_pct=-0.8),
            self.portfolio,
            paper_environment=True,
        )
        self.assertEqual(decision.action, "WAIT")
        self.assertIsNone(decision.proposal)


if __name__ == "__main__":
    unittest.main()
