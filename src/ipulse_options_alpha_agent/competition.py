"""Sanitized Alpaca competition-account and performance telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any


STARTING_BALANCE_USD = 100_000.0


@dataclass(frozen=True)
class CompetitionSnapshot:
    """Public-safe evidence for account eligibility and paper performance."""

    captured_at_utc: str
    account_fingerprint: str
    account_created_at_utc: str
    account_status: str
    currency: str
    paper_account: bool
    starting_balance_usd: float
    equity_usd: float
    cash_usd: float
    buying_power_usd: float
    cumulative_pnl_usd: float
    cumulative_return_pct: float
    options_trading_level: int
    open_positions: int
    open_orders: int
    filled_orders: int
    canceled_orders: int
    baseline_ready: bool
    issues: tuple[str, ...]


def _find_value(payload: object, key: str) -> object | None:
    if isinstance(payload, dict):
        if key in payload:
            return payload[key]
        for value in payload.values():
            found = _find_value(value, key)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_value(value, key)
            if found is not None:
                return found
    return None


def _records(payload: object, required_keys: frozenset[str]) -> tuple[dict[str, Any], ...]:
    found: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        if required_keys.issubset(payload):
            found.append(payload)
        else:
            for value in payload.values():
                found.extend(_records(value, required_keys))
    elif isinstance(payload, list):
        for value in payload:
            found.extend(_records(value, required_keys))
    return tuple(found)


def _number(payload: object, key: str) -> float:
    value = _find_value(payload, key)
    if value is None:
        raise ValueError(f"Alpaca account response is missing {key}.")
    return float(str(value))


def _integer(payload: object, key: str) -> int:
    value = _find_value(payload, key)
    if value is None:
        raise ValueError(f"Alpaca account response is missing {key}.")
    return int(str(value))


def _boolean(payload: object, key: str) -> bool:
    value = _find_value(payload, key)
    if isinstance(value, bool):
        return value
    return str(value).lower() == "true"


def _fingerprint(account: object) -> str:
    account_id = str(_find_value(account, "id") or "")
    account_number = str(_find_value(account, "account_number") or "")
    if not account_id or not account_number:
        raise ValueError("Alpaca account identity is incomplete.")
    digest = sha256(f"{account_id}:{account_number}".encode()).hexdigest()
    return f"sha256:{digest[:16]}"


def build_competition_snapshot(
    *,
    account: object,
    positions: object,
    orders: object,
    activities: object,
    captured_at_utc: str,
    starting_balance_usd: float = STARTING_BALANCE_USD,
) -> CompetitionSnapshot:
    """Normalize broker state without retaining raw account identifiers."""

    account_number = str(_find_value(account, "account_number") or "")
    status = str(_find_value(account, "status") or "UNKNOWN")
    currency = str(_find_value(account, "currency") or "UNKNOWN")
    created_at = str(_find_value(account, "created_at") or "")
    equity = _number(account, "equity")
    cash = _number(account, "cash")
    buying_power = _number(account, "buying_power")
    options_level = _integer(account, "options_trading_level")
    paper_account = account_number.startswith("PA")
    position_records = _records(positions, frozenset({"symbol", "qty"}))
    order_records = _records(orders, frozenset({"id", "status", "symbol"}))
    activity_records = _records(
        activities, frozenset({"activity_type", "net_amount"})
    )

    initial_funding_visible = any(
        str(item.get("activity_type", "")).upper() == "JNLC"
        and abs(float(str(item.get("net_amount", "0"))) - starting_balance_usd)
        < 0.01
        for item in activity_records
    )
    issues: list[str] = []
    if not paper_account:
        issues.append("Account number is not identified as an Alpaca paper account.")
    if status != "ACTIVE":
        issues.append("Alpaca account is not active.")
    if currency != "USD":
        issues.append("Competition account currency is not USD.")
    if _boolean(account, "trading_blocked"):
        issues.append("Trading is blocked on the competition account.")
    if options_level < 1:
        issues.append("Options trading is not approved on the competition account.")
    if not created_at:
        issues.append("Account creation time is unavailable.")
    if not initial_funding_visible:
        issues.append("The required $100,000 initial funding activity is not visible.")

    pnl = equity - starting_balance_usd
    return CompetitionSnapshot(
        captured_at_utc=captured_at_utc,
        account_fingerprint=_fingerprint(account),
        account_created_at_utc=created_at,
        account_status=status,
        currency=currency,
        paper_account=paper_account,
        starting_balance_usd=starting_balance_usd,
        equity_usd=equity,
        cash_usd=cash,
        buying_power_usd=buying_power,
        cumulative_pnl_usd=pnl,
        cumulative_return_pct=(pnl / starting_balance_usd) * 100,
        options_trading_level=options_level,
        open_positions=len(position_records),
        open_orders=sum(
            str(item.get("status", "")).lower()
            in {"new", "accepted", "pending_new", "partially_filled"}
            for item in order_records
        ),
        filled_orders=sum(
            str(item.get("status", "")).lower() == "filled"
            for item in order_records
        ),
        canceled_orders=sum(
            str(item.get("status", "")).lower() in {"canceled", "expired"}
            for item in order_records
        ),
        baseline_ready=not issues,
        issues=tuple(issues),
    )
