"""Tests for execution-time market and churn protections."""

from __future__ import annotations

import unittest

from ipulse_options_alpha_agent.research import OperationalState
from ipulse_options_alpha_agent.safety import OperationalSafetyGate


class SafetyTests(unittest.TestCase):
    def test_approves_fresh_unique_open_market_state(self) -> None:
        decision = OperationalSafetyGate().evaluate(
            OperationalState(True, 10, 0, False, 0, None)
        )
        self.assertTrue(decision.approved)

    def test_rejects_closed_stale_duplicate_state(self) -> None:
        decision = OperationalSafetyGate().evaluate(
            OperationalState(False, 500, 3, True, 1, 2)
        )
        self.assertFalse(decision.approved)
        self.assertGreaterEqual(len(decision.reasons), 5)

    def test_rejects_unknown_order_and_duplicate_state(self) -> None:
        decision = OperationalSafetyGate().evaluate(
            OperationalState(True, 10, None, None, None, None)
        )
        self.assertFalse(decision.approved)
        self.assertEqual(len(decision.reasons), 3)


if __name__ == "__main__":
    unittest.main()
