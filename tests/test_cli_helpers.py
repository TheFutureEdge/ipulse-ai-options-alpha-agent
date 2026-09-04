"""Tests for fail-closed broker-state normalization helpers."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from ipulse_options_alpha_agent.cli import (
    count_filled_orders,
    count_session_fills,
    duplicate_option_signal,
    extract_order_records,
    minutes_since_last_fill,
)


class CliHelperTests(unittest.TestCase):
    def test_extracts_and_summarizes_recent_orders(self) -> None:
        payload = {
            "orders": [
                {
                    "id": "order-1",
                    "status": "filled",
                    "symbol": "SPY260904C00772000",
                    "filled_at": "2026-08-28T13:45:00Z",
                },
                {
                    "id": "order-2",
                    "status": "canceled",
                    "symbol": "QQQ260904C00600000",
                },
            ]
        }
        records = extract_order_records(payload)
        self.assertEqual(count_filled_orders(records), 1)
        self.assertEqual(
            count_session_fills(
                records, now=datetime(2026, 8, 28, 14, 0, tzinfo=UTC)
            ),
            1,
        )
        self.assertEqual(
            count_session_fills(
                records, now=datetime(2026, 8, 29, 14, 0, tzinfo=UTC)
            ),
            0,
        )
        self.assertTrue(duplicate_option_signal(records, "SPY260904C00772000"))
        self.assertEqual(
            minutes_since_last_fill(
                records, now=datetime(2026, 8, 28, 14, 0, tzinfo=UTC)
            ),
            15,
        )


if __name__ == "__main__":
    unittest.main()
