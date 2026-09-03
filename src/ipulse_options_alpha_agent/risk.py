"""Deterministic portfolio risk gates for paper execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from .domain import AssetClass, PortfolioSnapshot, TradeProposal, TradeSide


@dataclass(frozen=True)
class RiskLimits:
    """Conservative limits for the first hackathon execution phase."""

    allowed_underlyings: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "SPY",
                "QQQ",
                "IWM",
                "DIA",
                "XLK",
                "XLF",
                "XLE",
                "TLT",
                "GLD",
                "SLV",
                "AAPL",
                "MSFT",
                "NVDA",
                "AMZN",
                "META",
                "GOOGL",
                "AVGO",
            }
        )
    )
    max_daily_loss_pct: float = 0.02
    max_loss_per_trade_pct: float = 0.005
    max_notional_per_trade: float = 1_000.0
    max_open_positions: int = 5
    max_option_contracts: int = 1
    max_equity_smoke_quantity: int = 1


@dataclass(frozen=True)
class RiskDecision:
    """Auditable output from the deterministic risk gate."""

    approved: bool
    reasons: tuple[str, ...]
    estimated_notional: float
    max_allowed_loss: float


class RiskGate:
    """Fail-closed paper-trading risk controller."""

    def __init__(self, limits: RiskLimits | None = None) -> None:
        """Initialize the gate with explicit or conservative default limits."""

        self.limits = limits or RiskLimits()

    def evaluate(
        self,
        proposal: TradeProposal,
        portfolio: PortfolioSnapshot,
        *,
        paper_environment: bool,
    ) -> RiskDecision:
        """Approve only bounded proposals that satisfy every configured limit."""

        reasons: list[str] = []
        limits = self.limits
        max_allowed_loss = portfolio.equity * limits.max_loss_per_trade_pct

        if not paper_environment:
            reasons.append("Live trading is forbidden.")
        if proposal.underlying not in limits.allowed_underlyings:
            reasons.append("Underlying is outside the approved liquid universe.")
        if proposal.quantity <= 0:
            reasons.append("Quantity must be positive.")
        if proposal.estimated_entry_price <= 0:
            reasons.append("Estimated entry price must be positive.")
        if proposal.max_loss_amount <= 0:
            reasons.append("Maximum loss must be explicitly bounded.")
        if proposal.max_loss_amount > max_allowed_loss:
            reasons.append("Maximum loss exceeds the per-trade equity limit.")
        if proposal.estimated_notional > limits.max_notional_per_trade:
            reasons.append("Estimated notional exceeds the per-trade limit.")
        if proposal.estimated_notional > portfolio.buying_power:
            reasons.append("Estimated notional exceeds current buying power.")
        if portfolio.open_positions >= limits.max_open_positions:
            reasons.append("Maximum open position count has been reached.")
        if portfolio.daily_pnl <= -(portfolio.equity * limits.max_daily_loss_pct):
            reasons.append("Daily loss circuit breaker is active.")
        if proposal.order_type != "limit":
            reasons.append("Initial execution requires a limit order.")

        if proposal.asset_class is AssetClass.OPTION:
            if proposal.side is not TradeSide.BUY:
                reasons.append("Initial options execution permits long premium only.")
            if proposal.quantity > limits.max_option_contracts:
                reasons.append("Option quantity exceeds the one-contract limit.")
        elif proposal.asset_class is AssetClass.EQUITY:
            if proposal.side is not TradeSide.BUY:
                reasons.append("Equity smoke tests permit buy orders only.")
            if proposal.quantity > limits.max_equity_smoke_quantity:
                reasons.append("Equity smoke-test quantity exceeds one share.")
        else:
            reasons.append("Unsupported asset class.")

        return RiskDecision(
            approved=not reasons,
            reasons=tuple(reasons),
            estimated_notional=proposal.estimated_notional,
            max_allowed_loss=max_allowed_loss,
        )
