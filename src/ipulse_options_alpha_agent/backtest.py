"""Leakage-resistant walk-forward scorecards for directional option signals."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ReversalConfig:
    """Frozen challenger selected on the development period only."""

    fast_threshold_pct: float = 0.50
    slow_threshold_pct: float = 3.00
    max_realized_volatility_pct: float = 25.00
    holding_sessions: int = 2
    development_cutoff: str = "2024-01-01"


@dataclass(frozen=True)
class SignalOutcome:
    """One decision made at close t and scored at close t+horizon."""

    signal_date: str
    exit_date: str
    symbol: str
    direction: str
    fast_return_pct: float
    slow_return_pct: float
    realized_volatility_pct: float
    underlying_return_pct: float
    signed_return_pct: float
    selection_score: float


def _number(value: object) -> float:
    number = float(str(value))
    if not math.isfinite(number) or number <= 0:
        raise ValueError("Bar closes must be positive finite numbers.")
    return number


def _bar_value(bar: Mapping[str, Any], *keys: str) -> object:
    for key in keys:
        if key in bar:
            return bar[key]
    raise ValueError(f"Bar is missing one of {keys!r}.")


def _normalize_bars(
    rows: Sequence[Mapping[str, Any]],
) -> list[tuple[str, float]]:
    normalized: list[tuple[str, float]] = []
    for row in rows:
        timestamp = str(_bar_value(row, "timestamp", "t"))
        parsed_date = date.fromisoformat(timestamp[:10]).isoformat()
        normalized.append((parsed_date, _number(_bar_value(row, "close", "c"))))
    normalized.sort(key=lambda item: item[0])
    if len({item[0] for item in normalized}) != len(normalized):
        raise ValueError("Daily bars contain duplicate dates.")
    return normalized


def generate_signal_outcomes(
    bars_by_symbol: Mapping[str, Sequence[Mapping[str, Any]]],
    config: ReversalConfig | None = None,
) -> tuple[SignalOutcome, ...]:
    """Generate one highest-conviction decision per date without lookahead."""

    policy = config or ReversalConfig()
    candidates_by_date: dict[str, SignalOutcome] = {}
    for symbol, raw_rows in bars_by_symbol.items():
        rows = _normalize_bars(raw_rows)
        closes = [item[1] for item in rows]
        for index in range(20, len(rows) - policy.holding_sessions):
            fast = ((closes[index] / closes[index - 1]) - 1) * 100
            slow = ((closes[index] / closes[index - 5]) - 1) * 100
            returns = [
                (current / previous) - 1
                for previous, current in zip(
                    closes[index - 20 : index],
                    closes[index - 19 : index + 1],
                    strict=True,
                )
            ]
            realized_volatility = statistics.stdev(returns) * math.sqrt(252) * 100
            exhausted_direction = 0
            if (
                fast >= policy.fast_threshold_pct
                and slow >= policy.slow_threshold_pct
            ):
                exhausted_direction = 1
            elif (
                fast <= -policy.fast_threshold_pct
                and slow <= -policy.slow_threshold_pct
            ):
                exhausted_direction = -1
            if not exhausted_direction:
                continue
            if realized_volatility > policy.max_realized_volatility_pct:
                continue

            direction = -exhausted_direction
            exit_index = index + policy.holding_sessions
            underlying_return = ((closes[exit_index] / closes[index]) - 1) * 100
            outcome = SignalOutcome(
                signal_date=rows[index][0],
                exit_date=rows[exit_index][0],
                symbol=symbol.upper(),
                direction="CALL" if direction > 0 else "PUT",
                fast_return_pct=fast,
                slow_return_pct=slow,
                realized_volatility_pct=realized_volatility,
                underlying_return_pct=underlying_return,
                signed_return_pct=direction * underlying_return,
                selection_score=abs(fast) + abs(slow),
            )
            prior = candidates_by_date.get(outcome.signal_date)
            if prior is None or outcome.selection_score > prior.selection_score:
                candidates_by_date[outcome.signal_date] = outcome
    return tuple(candidates_by_date[key] for key in sorted(candidates_by_date))


def summarize(outcomes: Sequence[SignalOutcome]) -> dict[str, int | float | None]:
    """Summarize directional outcomes without presenting them as option P&L."""

    returns = [item.signed_return_pct for item in outcomes]
    if not returns:
        return {
            "signals": 0,
            "win_rate_pct": 0.0,
            "sum_signed_return_points": 0.0,
            "average_signed_return_pct": 0.0,
            "profit_factor": None,
            "sharpe_proxy": None,
            "max_drawdown_points": 0.0,
        }
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    average = statistics.mean(returns)
    deviation = statistics.stdev(returns) if len(returns) > 1 else 0.0
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
    gross_loss = -sum(losses)
    return {
        "signals": len(returns),
        "win_rate_pct": round(len(wins) / len(returns) * 100, 1),
        "sum_signed_return_points": round(sum(returns), 2),
        "average_signed_return_pct": round(average, 3),
        "profit_factor": round(sum(wins) / gross_loss, 2) if gross_loss else None,
        "sharpe_proxy": round(average / deviation * math.sqrt(252), 2)
        if deviation
        else None,
        "max_drawdown_points": round(max_drawdown, 2),
    }


def build_scorecard(
    bars_by_symbol: Mapping[str, Sequence[Mapping[str, Any]]],
    config: ReversalConfig | None = None,
) -> dict[str, Any]:
    """Build development, untouched holdout, and full-period evidence."""

    policy = config or ReversalConfig()
    outcomes = generate_signal_outcomes(bars_by_symbol, policy)
    development = [
        item for item in outcomes if item.signal_date < policy.development_cutoff
    ]
    holdout = [
        item for item in outcomes if item.signal_date >= policy.development_cutoff
    ]
    return {
        "strategy": "exhaustion_reversal_v1",
        "config": asdict(policy),
        "methodology": {
            "signal_timing": "Signal uses daily closes through close t only.",
            "selection": "Choose the highest absolute fast-plus-slow move among qualifying symbols.",
            "scoring": "Score direction against underlying close t+2.",
            "interpretation": "Directional signal proxy; not executable option P&L.",
        },
        "development": summarize(development),
        "holdout": summarize(holdout),
        "full_period": summarize(outcomes),
        "outcomes": [asdict(item) for item in outcomes],
    }


def load_alpaca_bars(path: Path) -> Mapping[str, Sequence[Mapping[str, Any]]]:
    """Load either the connector shape or Alpaca's nested API shape."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Alpaca bar export must be a JSON object.")
    bars = payload.get("bars")
    if not isinstance(bars, dict):
        data = payload.get("data")
        bars = data.get("bars") if isinstance(data, dict) else None
    if not isinstance(bars, dict):
        raise ValueError("Alpaca bar export contains no bars mapping.")
    return {
        str(symbol): rows
        for symbol, rows in bars.items()
        if isinstance(rows, list)
    }


def main() -> None:
    """Create a scorecard from a saved Alpaca daily-bar response."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scorecard = build_scorecard(load_alpaca_bars(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), **scorecard["holdout"]}, indent=2))


if __name__ == "__main__":
    main()
