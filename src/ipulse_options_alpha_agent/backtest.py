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


def _elapsed_years(outcomes: Sequence[SignalOutcome]) -> float | None:
    """Return the observed signal-to-exit span in calendar years."""

    if len(outcomes) < 2:
        return None
    start = date.fromisoformat(min(item.signal_date for item in outcomes))
    end = date.fromisoformat(max(item.exit_date for item in outcomes))
    elapsed_days = (end - start).days
    return elapsed_days / 365.2425 if elapsed_days > 0 else None


def _wilson_interval(successes: int, observations: int) -> tuple[float, float]:
    """Return a dependency-free 95% Wilson interval for a hit rate."""

    if observations <= 0:
        return 0.0, 0.0
    z = 1.959963984540054
    rate = successes / observations
    denominator = 1 + (z * z / observations)
    center = (rate + (z * z / (2 * observations))) / denominator
    half_width = (
        z
        * math.sqrt(
            (rate * (1 - rate) / observations)
            + (z * z / (4 * observations * observations))
        )
        / denominator
    )
    return center - half_width, center + half_width


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
            "observed_signals_per_year": None,
            "win_rate_wilson_95pct_low": 0.0,
            "win_rate_wilson_95pct_high": 0.0,
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
    elapsed_years = _elapsed_years(outcomes)
    signals_per_year = len(returns) / elapsed_years if elapsed_years else None
    win_rate_low, win_rate_high = _wilson_interval(len(wins), len(returns))
    return {
        "signals": len(returns),
        "win_rate_pct": round(len(wins) / len(returns) * 100, 1),
        "sum_signed_return_points": round(sum(returns), 2),
        "average_signed_return_pct": round(average, 3),
        "profit_factor": round(sum(wins) / gross_loss, 2) if gross_loss else None,
        "sharpe_proxy": round(
            average / deviation * math.sqrt(signals_per_year), 2
        )
        if deviation and signals_per_year
        else None,
        "observed_signals_per_year": round(signals_per_year, 1)
        if signals_per_year
        else None,
        "win_rate_wilson_95pct_low": round(win_rate_low * 100, 1),
        "win_rate_wilson_95pct_high": round(win_rate_high * 100, 1),
        "max_drawdown_points": round(max_drawdown, 2),
    }


def _non_overlapping(
    outcomes: Sequence[SignalOutcome],
) -> tuple[SignalOutcome, ...]:
    """Greedily keep signals whose holding windows do not overlap."""

    selected: list[SignalOutcome] = []
    latest_exit: str | None = None
    for outcome in sorted(outcomes, key=lambda item: item.signal_date):
        if latest_exit is None or outcome.signal_date > latest_exit:
            selected.append(outcome)
            latest_exit = outcome.exit_date
    return tuple(selected)


def _group_summaries(
    outcomes: Sequence[SignalOutcome], *, attribute: str
) -> dict[str, dict[str, int | float | None]]:
    """Summarize outcome stability by one explicit outcome attribute."""

    grouped: dict[str, list[SignalOutcome]] = {}
    for outcome in outcomes:
        raw_key = getattr(outcome, attribute)
        key = raw_key[:4] if attribute == "signal_date" else raw_key
        grouped.setdefault(key, []).append(outcome)
    return {key: summarize(grouped[key]) for key in sorted(grouped)}


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
            "sharpe_proxy": "Event-level mean/stdev scaled by observed signals per calendar year; not a portfolio Sharpe ratio.",
            "robustness": "Non-overlapping holdout greedily accepts a signal only after the prior selected holding window exits.",
        },
        "development": summarize(development),
        "holdout": summarize(holdout),
        "holdout_non_overlapping": summarize(_non_overlapping(holdout)),
        "holdout_by_year": _group_summaries(holdout, attribute="signal_date"),
        "holdout_by_symbol": _group_summaries(holdout, attribute="symbol"),
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
