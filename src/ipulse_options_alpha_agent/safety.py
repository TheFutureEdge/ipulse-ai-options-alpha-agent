"""Deterministic operational safety gates independent of advisor reasoning."""

from __future__ import annotations

from dataclasses import dataclass

from .research import OperationalState


@dataclass(frozen=True)
class OperationalSafetyLimits:
    """Conservative execution limits for the initial autonomous loop."""

    max_quote_age_seconds: float = 120
    max_daily_trades: int = 3
    max_open_orders: int = 0
    min_minutes_between_trades: float = 15


@dataclass(frozen=True)
class OperationalSafetyDecision:
    """Auditable safety result that the LLM cannot modify."""

    approved: bool
    reasons: tuple[str, ...]


class OperationalSafetyGate:
    """Fail closed on market timing, stale data, duplication, or churn."""

    def __init__(self, limits: OperationalSafetyLimits | None = None) -> None:
        self.limits = limits or OperationalSafetyLimits()

    def evaluate(self, state: OperationalState) -> OperationalSafetyDecision:
        """Return approval only when every execution-time condition passes."""

        reasons: list[str] = []
        limits = self.limits
        if not state.market_open:
            reasons.append("Regular market session is closed.")
        if state.quote_age_seconds < 0:
            reasons.append("Quote age cannot be negative.")
        elif state.quote_age_seconds > limits.max_quote_age_seconds:
            reasons.append("Option quote is stale.")
        if state.daily_trade_count is None:
            reasons.append("Daily trade count is unavailable.")
        elif state.daily_trade_count >= limits.max_daily_trades:
            reasons.append("Maximum daily trade count has been reached.")
        if state.duplicate_signal is None:
            reasons.append("Duplicate-signal state is unavailable.")
        elif state.duplicate_signal:
            reasons.append("An equivalent signal was already processed.")
        if state.open_order_count is None:
            reasons.append("Open-order count is unavailable.")
        elif state.open_order_count > limits.max_open_orders:
            reasons.append("An open order is already pending.")
        if (
            state.minutes_since_last_trade is not None
            and state.minutes_since_last_trade < limits.min_minutes_between_trades
        ):
            reasons.append("Trade cooldown is still active.")
        return OperationalSafetyDecision(approved=not reasons, reasons=tuple(reasons))
