"""Tests for public-safe competition account telemetry."""

from __future__ import annotations

import unittest
from dataclasses import asdict

from ipulse_options_alpha_agent.competition import build_competition_snapshot


def account(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "secret-account-uuid",
        "account_number": "PA1234567890",
        "created_at": "2026-08-28T03:19:04Z",
        "status": "ACTIVE",
        "currency": "USD",
        "equity": "100250.50",
        "cash": "97500",
        "buying_power": "97500",
        "options_trading_level": 3,
        "trading_blocked": False,
    }
    payload.update(overrides)
    return payload


class CompetitionSnapshotTests(unittest.TestCase):
    def test_builds_sanitized_ready_snapshot(self) -> None:
        snapshot = build_competition_snapshot(
            account={"data": account()},
            positions={"result": [{"symbol": "SPY260904C00700000", "qty": "1"}]},
            orders={
                "result": [
                    {
                        "id": "order-1",
                        "symbol": "SPY260904C00700000",
                        "status": "filled",
                    },
                    {"id": "order-2", "symbol": "SPY", "status": "canceled"},
                ]
            },
            activities={
                "result": [
                    {"activity_type": "JNLC", "net_amount": "100000"}
                ]
            },
            captured_at_utc="2026-08-28T15:00:00Z",
        )

        self.assertTrue(snapshot.baseline_ready)
        self.assertTrue(snapshot.paper_account)
        self.assertEqual(snapshot.open_positions, 1)
        self.assertEqual(snapshot.filled_orders, 1)
        self.assertEqual(snapshot.canceled_orders, 1)
        self.assertAlmostEqual(snapshot.cumulative_pnl_usd, 250.5)
        serialized = str(asdict(snapshot))
        self.assertNotIn("secret-account-uuid", serialized)
        self.assertNotIn("PA1234567890", serialized)

    def test_fails_baseline_for_live_blocked_or_unfunded_account(self) -> None:
        snapshot = build_competition_snapshot(
            account=account(
                account_number="LIVE123",
                status="INACTIVE",
                currency="EUR",
                options_trading_level=0,
                trading_blocked=True,
                created_at="",
            ),
            positions=[],
            orders=[],
            activities=[],
            captured_at_utc="2026-08-28T15:00:00Z",
        )

        self.assertFalse(snapshot.baseline_ready)
        self.assertEqual(len(snapshot.issues), 7)


if __name__ == "__main__":
    unittest.main()
