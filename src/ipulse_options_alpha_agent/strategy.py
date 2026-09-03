"""Initial deterministic strategy used to test the autonomous workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .domain import AssetClass, TradeProposal, TradeSide


@dataclass(frozen=True)
class StrategySignal:
    """Normalized market evidence consumed by the strategy."""

    underlying: str
    option_symbol: str
    option_limit_price: float
    fast_return_pct: float
    slow_return_pct: float
    realized_volatility_pct: float
    option_spread_pct: float
    confidence: float


class MomentumRegimeStrategy:
    """Propose a bounded long option only when trend and regime agree."""

    name = "momentum_regime_v0"

    def propose(self, signal: StrategySignal) -> TradeProposal | None:
        """Return a CALL, PUT, or no-trade decision from normalized evidence."""

        if signal.confidence < 0.65:
            return None
        if signal.realized_volatility_pct > 45:
            return None
        if signal.option_spread_pct > 8:
            return None
        if signal.option_limit_price <= 0:
            return None

        direction: str | None = None
        if signal.fast_return_pct >= 0.35 and signal.slow_return_pct >= 0.50:
            direction = "CALL"
        elif signal.fast_return_pct <= -0.35 and signal.slow_return_pct <= -0.50:
            direction = "PUT"
        if direction is None:
            return None

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        rationale = (
            f"{direction} candidate: fast return {signal.fast_return_pct:.2f}%, "
            f"slow return {signal.slow_return_pct:.2f}%, realized volatility "
            f"{signal.realized_volatility_pct:.2f}%, spread "
            f"{signal.option_spread_pct:.2f}%."
        )
        return TradeProposal(
            client_order_id=f"ipulse-{self.name}-{signal.underlying.lower()}-{timestamp}",
            strategy_name=self.name,
            underlying=signal.underlying,
            symbol=signal.option_symbol,
            asset_class=AssetClass.OPTION,
            side=TradeSide.BUY,
            quantity=1,
            order_type="limit",
            time_in_force="day",
            estimated_entry_price=signal.option_limit_price,
            max_loss_amount=signal.option_limit_price * 100,
            confidence=signal.confidence,
            rationale=rationale,
            source_signals={
                "fast_return_pct": signal.fast_return_pct,
                "slow_return_pct": signal.slow_return_pct,
                "realized_volatility_pct": signal.realized_volatility_pct,
                "option_spread_pct": signal.option_spread_pct,
            },
        )


class ExhaustionReversalStrategy:
    """Trade a frozen two-session reversal only after extreme aligned moves."""

    name = "exhaustion_reversal_v1"

    def propose(self, signal: StrategySignal) -> TradeProposal | None:
        """Return the opposite direction after a validated exhaustion event."""

        if signal.confidence < 0.65:
            return None
        if signal.realized_volatility_pct > 25:
            return None
        if signal.option_spread_pct > 8:
            return None
        if signal.option_limit_price <= 0:
            return None

        direction: str | None = None
        if signal.fast_return_pct >= 0.50 and signal.slow_return_pct >= 3.00:
            direction = "PUT"
        elif signal.fast_return_pct <= -0.50 and signal.slow_return_pct <= -3.00:
            direction = "CALL"
        if direction is None:
            return None
        expected_marker = "P" if direction == "PUT" else "C"
        if expected_marker not in signal.option_symbol[-9:]:
            return None

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return TradeProposal(
            client_order_id=(
                f"ipulse-{self.name}-{signal.underlying.lower()}-{timestamp}"
            ),
            strategy_name=self.name,
            underlying=signal.underlying,
            symbol=signal.option_symbol,
            asset_class=AssetClass.OPTION,
            side=TradeSide.BUY,
            quantity=1,
            order_type="limit",
            time_in_force="day",
            estimated_entry_price=signal.option_limit_price,
            max_loss_amount=signal.option_limit_price * 100,
            confidence=signal.confidence,
            rationale=(
                f"{direction} exhaustion reversal: fast return "
                f"{signal.fast_return_pct:.2f}%, slow return "
                f"{signal.slow_return_pct:.2f}%, realized volatility "
                f"{signal.realized_volatility_pct:.2f}%, spread "
                f"{signal.option_spread_pct:.2f}%."
            ),
            source_signals={
                "fast_return_pct": signal.fast_return_pct,
                "slow_return_pct": signal.slow_return_pct,
                "realized_volatility_pct": signal.realized_volatility_pct,
                "option_spread_pct": signal.option_spread_pct,
                "holding_sessions": 2,
            },
        )
