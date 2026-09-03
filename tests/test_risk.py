"""Unit tests for fail-closed paper risk gates."""

from __future__ import annotations

import unittest

from ipulse_options_alpha_agent.domain import (
    AssetClass,
    PortfolioSnapshot,
    TradeProposal,
    TradeSide,
)
from ipulse_options_alpha_agent.risk import RiskGate


def proposal(*, price: float = 2.0, quantity: int = 1) -> TradeProposal:
    """Create a valid long-option proposal for one focused test."""

    return TradeProposal(
        client_order_id="risk-test",
        strategy_name="test",
        underlying="SPY",
        symbol="SPY_TEST_CALL",
        asset_class=AssetClass.OPTION,
        side=TradeSide.BUY,
        quantity=quantity,
        order_type="limit",
        time_in_force="day",
        estimated_entry_price=price,
        max_loss_amount=price * quantity * 100,
        confidence=0.8,
        rationale="test",
    )


def portfolio(*, daily_pnl: float = 0, open_positions: int = 0) -> PortfolioSnapshot:
    """Create the default development paper portfolio snapshot."""

    return PortfolioSnapshot(
        equity=100_000,
        cash=100_000,
        buying_power=400_000,
        daily_pnl=daily_pnl,
        open_positions=open_positions,
    )


class RiskGateTests(unittest.TestCase):
    """Verify every critical circuit breaker."""

    def test_accepts_one_bounded_long_option_in_paper(self) -> None:
        """A small defined-loss paper option should pass."""

        decision = RiskGate().evaluate(
            proposal(), portfolio(), paper_environment=True
        )
        self.assertTrue(decision.approved)
        self.assertEqual(decision.reasons, ())

    def test_accepts_aapl_in_the_liquid_options_universe(self) -> None:
        """The expanded liquid universe must remain explicitly allowlisted."""

        candidate = proposal()
        candidate = candidate.__class__(
            **{**candidate.__dict__, "underlying": "AAPL", "symbol": "AAPL_TEST_CALL"}
        )
        decision = RiskGate().evaluate(
            candidate, portfolio(), paper_environment=True
        )
        self.assertTrue(decision.approved)

    def test_rejects_live_environment(self) -> None:
        """The gate must fail closed outside paper trading."""

        decision = RiskGate().evaluate(
            proposal(), portfolio(), paper_environment=False
        )
        self.assertFalse(decision.approved)
        self.assertIn("Live trading is forbidden.", decision.reasons)

    def test_rejects_oversized_maximum_loss(self) -> None:
        """A proposal above the 0.5 percent loss cap should fail."""

        decision = RiskGate().evaluate(
            proposal(price=8.0), portfolio(), paper_environment=True
        )
        self.assertFalse(decision.approved)
        self.assertIn(
            "Maximum loss exceeds the per-trade equity limit.", decision.reasons
        )

    def test_rejects_daily_loss_circuit_breaker(self) -> None:
        """No new risk is allowed after the daily loss limit is reached."""

        decision = RiskGate().evaluate(
            proposal(), portfolio(daily_pnl=-2_000), paper_environment=True
        )
        self.assertFalse(decision.approved)
        self.assertIn("Daily loss circuit breaker is active.", decision.reasons)


if __name__ == "__main__":
    unittest.main()
