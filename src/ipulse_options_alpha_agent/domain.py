"""Domain models for proposals and paper portfolio state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class AssetClass(StrEnum):
    """Supported paper-trading asset classes."""

    EQUITY = "equity"
    OPTION = "option"


class TradeSide(StrEnum):
    """Supported order sides."""

    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Minimal paper portfolio state required by the risk gate."""

    equity: float
    cash: float
    buying_power: float
    daily_pnl: float
    open_positions: int


@dataclass(frozen=True)
class TradeProposal:
    """A strategy proposal that has not yet been approved for execution."""

    client_order_id: str
    strategy_name: str
    underlying: str
    symbol: str
    asset_class: AssetClass
    side: TradeSide
    quantity: int
    order_type: str
    time_in_force: str
    estimated_entry_price: float
    max_loss_amount: float
    confidence: float
    rationale: str
    source_signals: Mapping[str, float] = field(default_factory=dict)

    @property
    def estimated_notional(self) -> float:
        """Return estimated order notional using the options multiplier."""

        multiplier = 100 if self.asset_class is AssetClass.OPTION else 1
        return self.estimated_entry_price * self.quantity * multiplier
