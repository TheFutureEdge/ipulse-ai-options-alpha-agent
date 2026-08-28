"""Unit tests for the fail-closed paper execution adapter."""

from __future__ import annotations

import unittest
from typing import Any

from ipulse_options_alpha_agent.agent import AgentDecision
from ipulse_options_alpha_agent.domain import (
    AssetClass,
    TradeProposal,
    TradeSide,
)
from ipulse_options_alpha_agent.execution import (
    ExecutionBlockedError,
    ExecutionMode,
    ExecutionPolicy,
    PaperOrderExecutor,
    build_order_request,
)
from ipulse_options_alpha_agent.risk import RiskDecision
from ipulse_options_alpha_agent.safety import OperationalSafetyDecision


def approved_equity_decision() -> AgentDecision:
    """Return a bounded one-share smoke decision."""

    proposal = TradeProposal(
        client_order_id="ipulse-paper-smoke-test",
        strategy_name="paper_connectivity_smoke_v0",
        underlying="SPY",
        symbol="SPY",
        asset_class=AssetClass.EQUITY,
        side=TradeSide.BUY,
        quantity=1,
        order_type="limit",
        time_in_force="day",
        estimated_entry_price=1.0,
        max_loss_amount=1.0,
        confidence=1.0,
        rationale="Non-marketable paper-only connectivity proof.",
    )
    return AgentDecision(
        action="APPROVE",
        proposal=proposal,
        risk=RiskDecision(
            approved=True,
            reasons=(),
            estimated_notional=1.0,
            max_allowed_loss=500.0,
        ),
        explanation="Risk gate approved.",
    )


class FakeClient:
    """Capture a broker call without a network connection."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_json(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        self.calls.append((tool_name, arguments))
        return {"order": {"id": "paper-order-id", "status": "accepted"}}


class ExecutionTests(unittest.IsolatedAsyncioTestCase):
    """Verify explicit authority and exact paper-order mapping."""

    async def test_disabled_switch_prevents_broker_call(self) -> None:
        client = FakeClient()
        executor = PaperOrderExecutor(client)
        with self.assertRaisesRegex(ExecutionBlockedError, "switch is disabled"):
            await executor.submit(approved_equity_decision(), ExecutionPolicy())
        self.assertEqual(client.calls, [])

    def test_live_environment_is_forbidden(self) -> None:
        with self.assertRaisesRegex(ExecutionBlockedError, "Live trading"):
            build_order_request(
                approved_equity_decision(),
                ExecutionPolicy(enabled=True, paper_environment=False),
            )

    async def test_approved_paper_order_uses_bounded_limit_request(self) -> None:
        client = FakeClient()
        receipt = await PaperOrderExecutor(client).submit(
            approved_equity_decision(),
            ExecutionPolicy(
                enabled=True,
                paper_environment=True,
                mode=ExecutionMode.CONNECTIVITY_SMOKE,
            ),
        )
        self.assertEqual(receipt.broker_order_id, "paper-order-id")
        self.assertEqual(
            client.calls,
            [
                (
                    "place_stock_order",
                    {
                        "symbol": "SPY",
                        "side": "buy",
                        "qty": "1",
                        "type": "limit",
                        "time_in_force": "day",
                        "limit_price": "1.00",
                        "client_order_id": "ipulse-paper-smoke-test",
                        "extended_hours": False,
                    },
                )
            ],
        )

    def test_strategy_order_requires_operational_safety_evidence(self) -> None:
        with self.assertRaisesRegex(ExecutionBlockedError, "safety evidence"):
            build_order_request(
                approved_equity_decision(),
                ExecutionPolicy(enabled=True, paper_environment=True),
            )

    def test_strategy_order_accepts_approved_operational_safety(self) -> None:
        tool, _ = build_order_request(
            approved_equity_decision(),
            ExecutionPolicy(
                enabled=True,
                paper_environment=True,
                operational_safety=OperationalSafetyDecision(
                    approved=True, reasons=()
                ),
            ),
        )
        self.assertEqual(tool, "place_stock_order")


if __name__ == "__main__":
    unittest.main()
