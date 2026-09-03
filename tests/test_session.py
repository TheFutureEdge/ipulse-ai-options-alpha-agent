"""Tests for finite autonomous-session orchestration."""

from __future__ import annotations

import unittest

from ipulse_options_alpha_agent.session import SessionPolicy, run_bounded_session


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_runs_exact_cycle_count_and_cooldowns(self) -> None:
        cycles: list[int] = []
        sleeps: list[float] = []

        async def cycle(index: int) -> dict[str, object]:
            cycles.append(index)
            return {"cycle": index, "action": "WAIT"}

        async def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        results = await run_bounded_session(
            cycle,
            SessionPolicy(max_cycles=3, interval_seconds=60),
            sleep=fake_sleep,
        )

        self.assertEqual(cycles, [1, 2, 3])
        self.assertEqual(sleeps, [60, 60])
        self.assertEqual(len(results), 3)

    async def test_rejects_unbounded_or_overactive_policy(self) -> None:
        async def cycle(_: int) -> dict[str, object]:
            return {}

        with self.assertRaises(ValueError):
            await run_bounded_session(cycle, SessionPolicy(max_cycles=79))
        with self.assertRaises(ValueError):
            await run_bounded_session(
                cycle, SessionPolicy(max_cycles=1, interval_seconds=59)
            )


if __name__ == "__main__":
    unittest.main()
