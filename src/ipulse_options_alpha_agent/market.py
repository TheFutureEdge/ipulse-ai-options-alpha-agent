"""Alpaca market-data normalization and liquid option selection."""

from __future__ import annotations

import asyncio
import math
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from .strategy import StrategySignal

if TYPE_CHECKING:
    from .mcp_client import AlpacaMcpClient


class MarketSignalUnavailable(RuntimeError):
    """Raised when market evidence is insufficient for a safe proposal."""


@dataclass(frozen=True)
class OptionCandidate:
    """Normalized, execution-relevant option snapshot."""

    symbol: str
    bid: float
    ask: float
    midpoint: float
    spread_pct: float
    delta: float
    implied_volatility_pct: float
    daily_volume: int
    quote_timestamp_utc: str | None


@dataclass(frozen=True)
class MarketEvaluation:
    """Normalized signal plus the selected contract and source timing."""

    signal: StrategySignal
    selected_option: OptionCandidate
    underlying_midpoint: float


def extract_bars(payload: object, symbol: str) -> list[dict[str, Any]]:
    """Extract one symbol's chronological bar list from Alpaca MCP data."""

    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    bars = data.get("bars")
    if not isinstance(bars, dict):
        return []
    records = bars.get(symbol)
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def extract_quote_midpoint(payload: object, symbol: str) -> float:
    """Return the current stock quote midpoint."""

    if not isinstance(payload, dict):
        raise MarketSignalUnavailable("Stock quote response is not an object.")
    data = payload.get("data")
    quotes = data.get("quotes") if isinstance(data, dict) else None
    quote = quotes.get(symbol) if isinstance(quotes, dict) else None
    if not isinstance(quote, dict):
        raise MarketSignalUnavailable(f"No stock quote is available for {symbol}.")
    bid = _positive_float(quote.get("bp"))
    ask = _positive_float(quote.get("ap"))
    if bid is None or ask is None or ask < bid:
        raise MarketSignalUnavailable(f"Invalid stock quote for {symbol}.")
    return (bid + ask) / 2


def compute_regime(bars: list[dict[str, Any]]) -> tuple[float, float, float]:
    """Compute one-day, five-day, and annualized realized-volatility evidence."""

    closes: list[float] = []
    for bar in bars:
        close = _positive_float(bar.get("c"))
        if close is not None:
            closes.append(close)
    if len(closes) < 10:
        raise MarketSignalUnavailable("At least ten valid daily bars are required.")

    fast_return_pct = ((closes[-1] / closes[-2]) - 1) * 100
    slow_return_pct = ((closes[-1] / closes[-6]) - 1) * 100
    recent_closes = closes[-21:]
    daily_returns = [
        (current / previous) - 1
        for previous, current in zip(
            recent_closes, recent_closes[1:], strict=False
        )
    ]
    realized_volatility_pct = statistics.stdev(daily_returns) * math.sqrt(252) * 100
    return fast_return_pct, slow_return_pct, realized_volatility_pct


def extract_option_candidates(payload: object) -> list[OptionCandidate]:
    """Normalize valid option-chain snapshots and ignore malformed records."""

    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    snapshots = data.get("snapshots") if isinstance(data, dict) else None
    if not isinstance(snapshots, dict):
        return []

    candidates: list[OptionCandidate] = []
    for symbol, snapshot in snapshots.items():
        if not isinstance(symbol, str) or not isinstance(snapshot, dict):
            continue
        quote = snapshot.get("latestQuote")
        greeks = snapshot.get("greeks")
        daily_bar = snapshot.get("dailyBar")
        if not isinstance(quote, dict) or not isinstance(greeks, dict):
            continue
        bid = _positive_float(quote.get("bp"))
        ask = _positive_float(quote.get("ap"))
        delta = _finite_float(greeks.get("delta"))
        iv = _positive_float(snapshot.get("impliedVolatility"))
        if bid is None or ask is None or delta is None or iv is None or ask < bid:
            continue
        midpoint = (bid + ask) / 2
        if midpoint <= 0:
            continue
        volume_value = daily_bar.get("v", 0) if isinstance(daily_bar, dict) else 0
        try:
            daily_volume = max(0, int(float(str(volume_value))))
        except ValueError:
            daily_volume = 0
        quote_timestamp = quote.get("t")
        candidates.append(
            OptionCandidate(
                symbol=symbol,
                bid=bid,
                ask=ask,
                midpoint=midpoint,
                spread_pct=((ask - bid) / midpoint) * 100,
                delta=delta,
                implied_volatility_pct=iv * 100,
                daily_volume=daily_volume,
                quote_timestamp_utc=(
                    str(quote_timestamp) if quote_timestamp is not None else None
                ),
            )
        )
    return candidates


def select_option(
    candidates: list[OptionCandidate], *, direction: str
) -> OptionCandidate:
    """Select a liquid, near-0.50-delta contract under the loss budget."""

    filtered = [
        candidate
        for candidate in candidates
        if candidate.spread_pct <= 8
        and candidate.midpoint * 100 <= 500
        and 0.35 <= abs(candidate.delta) <= 0.65
        and (
            (direction == "call" and candidate.delta > 0)
            or (direction == "put" and candidate.delta < 0)
        )
    ]
    if not filtered:
        raise MarketSignalUnavailable(
            "No liquid near-0.50-delta option satisfied the risk budget."
        )
    return min(
        filtered,
        key=lambda candidate: (
            abs(abs(candidate.delta) - 0.50),
            candidate.spread_pct,
            -candidate.daily_volume,
        ),
    )


class AlpacaMarketAdapter:
    """Build normalized strategy evidence from official Alpaca MCP tools."""

    def __init__(self, client: AlpacaMcpClient) -> None:
        """Initialize with an already-connected MCP client."""

        self.client = client

    async def build_evaluation(
        self, underlying: str = "SPY", *, reversal: bool = False
    ) -> MarketEvaluation:
        """Fetch and preserve a normalized signal, contract, and source timing."""

        symbol = underlying.upper()
        fast_return, slow_return, realized_volatility = await self._fetch_regime(
            symbol
        )
        return await self._build_contract_evaluation(
            symbol,
            fast_return=fast_return,
            slow_return=slow_return,
            realized_volatility=realized_volatility,
            reversal=reversal,
        )

    async def build_reversal_evaluation(
        self, underlyings: tuple[str, ...] = ("SPY", "QQQ", "IWM")
    ) -> MarketEvaluation:
        """Select the strongest qualifying frozen reversal before option lookup."""

        normalized = tuple(symbol.upper() for symbol in underlyings)
        regimes = await asyncio.gather(
            *(self._fetch_regime(symbol) for symbol in normalized)
        )
        qualified = [
            (symbol, *regime)
            for symbol, regime in zip(normalized, regimes, strict=True)
            if regime[2] <= 25
            and (
                (regime[0] >= 0.50 and regime[1] >= 3.00)
                or (regime[0] <= -0.50 and regime[1] <= -3.00)
            )
        ]
        if not qualified:
            raise MarketSignalUnavailable(
                "No SPY/QQQ/IWM signal meets the frozen exhaustion-reversal rule."
            )
        symbol, fast_return, slow_return, realized_volatility = max(
            qualified, key=lambda item: abs(item[1]) + abs(item[2])
        )
        return await self._build_contract_evaluation(
            symbol,
            fast_return=fast_return,
            slow_return=slow_return,
            realized_volatility=realized_volatility,
            reversal=True,
        )

    async def _fetch_regime(self, symbol: str) -> tuple[float, float, float]:
        """Fetch one symbol's adjusted daily bars and compute its regime."""

        bars_payload = await self.client.call_json(
            "get_stock_bars",
            {
                "symbols": symbol,
                "timeframe": "1Day",
                "days": 45,
                "feed": "iex",
                "adjustment": "all",
                "limit": 100,
            },
        )
        return compute_regime(extract_bars(bars_payload, symbol))

    async def _build_contract_evaluation(
        self,
        symbol: str,
        *,
        fast_return: float,
        slow_return: float,
        realized_volatility: float,
        reversal: bool,
    ) -> MarketEvaluation:
        """Select an option contract after the underlying rule qualifies."""

        quote_payload = await self.client.call_json(
            "get_stock_latest_quote", {"symbols": symbol, "feed": "iex"}
        )
        momentum_direction = "call" if slow_return >= 0 else "put"
        direction = (
            "put" if momentum_direction == "call" else "call"
        ) if reversal else momentum_direction
        price_anchor = extract_quote_midpoint(quote_payload, symbol)
        today = datetime.now(UTC).date()
        chain_payload = await self.client.call_json(
            "get_option_chain",
            {
                "underlying_symbol": symbol,
                "type": direction,
                "strike_price_gte": round(price_anchor * 0.97, 2),
                "strike_price_lte": round(price_anchor * 1.03, 2),
                "expiration_date_gte": str(today + timedelta(days=7)),
                "expiration_date_lte": str(today + timedelta(days=30)),
                "feed": "indicative",
                "limit": 250,
            },
        )
        candidate = select_option(
            extract_option_candidates(chain_payload), direction=direction
        )
        trend_strength = min(abs(slow_return) / 4, 0.15)
        spread_quality = max(0, (8 - candidate.spread_pct) / 160)
        confidence = min(0.90, 0.68 + trend_strength + spread_quality)
        return MarketEvaluation(
            signal=StrategySignal(
                underlying=symbol,
                option_symbol=candidate.symbol,
                option_limit_price=round(candidate.midpoint, 2),
                fast_return_pct=fast_return,
                slow_return_pct=slow_return,
                realized_volatility_pct=realized_volatility,
                option_spread_pct=candidate.spread_pct,
                confidence=confidence,
            ),
            selected_option=candidate,
            underlying_midpoint=price_anchor,
        )

    async def build_signal(self, underlying: str = "SPY") -> StrategySignal:
        """Compatibility wrapper returning only the normalized strategy signal."""

        return (await self.build_evaluation(underlying)).signal


def _finite_float(value: object) -> float | None:
    """Return a finite float or None."""

    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive_float(value: object) -> float | None:
    """Return a positive finite float or None."""

    number = _finite_float(value)
    return number if number is not None and number > 0 else None
