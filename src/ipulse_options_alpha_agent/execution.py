"""Fail-closed Alpaca paper-order execution adapter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from .agent import AgentDecision
from .domain import AssetClass
from .safety import OperationalSafetyDecision


class JsonToolClient(Protocol):
    """Minimal broker interface required by the execution adapter."""

    async def call_json(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a broker tool and return a JSON object."""


class ExecutionMode(StrEnum):
    """Separate strategy execution from the bounded connectivity smoke path."""

    STRATEGY = "strategy"
    CONNECTIVITY_SMOKE = "connectivity_smoke"


@dataclass(frozen=True)
class ExecutionPolicy:
    """Explicit authority required in addition to an approved decision."""

    enabled: bool = False
    paper_environment: bool = True
    mode: ExecutionMode = ExecutionMode.STRATEGY
    operational_safety: OperationalSafetyDecision | None = None


@dataclass(frozen=True)
class ExecutionReceipt:
    """Sanitized evidence returned after the broker accepts an order."""

    tool_name: str
    broker_order_id: str | None
    client_order_id: str
    symbol: str
    status: str | None
    order_type: str
    limit_price: str
    quantity: str


class ExecutionBlockedError(RuntimeError):
    """Raised when any execution precondition fails closed."""


def find_value(payload: object, key: str) -> object | None:
    """Find the first matching key in a nested broker response."""

    if isinstance(payload, dict):
        if key in payload:
            return payload[key]
        for value in payload.values():
            found = find_value(value, key)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = find_value(value, key)
            if found is not None:
                return found
    return None


def build_order_request(
    decision: AgentDecision, policy: ExecutionPolicy
) -> tuple[str, dict[str, Any]]:
    """Map one approved decision to an Alpaca MCP tool call."""

    if not policy.enabled:
        raise ExecutionBlockedError("Paper execution switch is disabled.")
    if not policy.paper_environment:
        raise ExecutionBlockedError("Live trading is forbidden.")
    if decision.action != "APPROVE":
        raise ExecutionBlockedError("Only APPROVE decisions may be submitted.")
    if decision.proposal is None or decision.risk is None:
        raise ExecutionBlockedError("Decision is missing proposal or risk evidence.")
    if not decision.risk.approved or decision.risk.reasons:
        raise ExecutionBlockedError("Risk evidence is not fully approved.")

    proposal = decision.proposal
    if policy.mode is ExecutionMode.STRATEGY:
        safety = policy.operational_safety
        if safety is None:
            raise ExecutionBlockedError("Operational safety evidence is missing.")
        if not safety.approved or safety.reasons:
            raise ExecutionBlockedError("Operational safety gate rejected execution.")
    elif policy.mode is ExecutionMode.CONNECTIVITY_SMOKE:
        if not (
            proposal.asset_class is AssetClass.EQUITY
            and proposal.quantity == 1
            and proposal.order_type == "limit"
            and proposal.estimated_entry_price <= 1
            and proposal.client_order_id.startswith("ipulse-paper-smoke-")
        ):
            raise ExecutionBlockedError("Connectivity smoke constraints were violated.")
    else:
        raise ExecutionBlockedError("Unknown execution mode.")

    arguments: dict[str, Any] = {
        "symbol": proposal.symbol,
        "side": proposal.side.value,
        "qty": str(proposal.quantity),
        "type": proposal.order_type,
        "time_in_force": proposal.time_in_force,
        "limit_price": f"{proposal.estimated_entry_price:.2f}",
        "client_order_id": proposal.client_order_id,
    }
    if proposal.asset_class is AssetClass.OPTION:
        arguments["position_intent"] = "buy_to_open"
        return "place_option_order", arguments
    if proposal.asset_class is AssetClass.EQUITY:
        arguments["extended_hours"] = False
        return "place_stock_order", arguments
    raise ExecutionBlockedError("Unsupported asset class.")


class PaperOrderExecutor:
    """Submit an already-approved order through Alpaca MCP."""

    def __init__(self, client: JsonToolClient) -> None:
        """Initialize with an externally configured broker client."""

        self.client = client

    async def submit(
        self, decision: AgentDecision, policy: ExecutionPolicy
    ) -> ExecutionReceipt:
        """Submit once and return only non-sensitive receipt fields."""

        tool_name, arguments = build_order_request(decision, policy)
        response = await self.client.call_json(tool_name, arguments)
        proposal = decision.proposal
        if proposal is None:
            raise ExecutionBlockedError("Decision proposal disappeared.")
        return ExecutionReceipt(
            tool_name=tool_name,
            broker_order_id=_as_optional_string(find_value(response, "id")),
            client_order_id=proposal.client_order_id,
            symbol=proposal.symbol,
            status=_as_optional_string(find_value(response, "status")),
            order_type=proposal.order_type,
            limit_price=f"{proposal.estimated_entry_price:.2f}",
            quantity=str(proposal.quantity),
        )


def _as_optional_string(value: object | None) -> str | None:
    """Normalize a broker scalar without leaking the full response."""

    return None if value is None else str(value)
