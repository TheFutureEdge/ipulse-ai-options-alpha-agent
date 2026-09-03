"""Bounded orchestration for autonomous paper-trading sessions."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SessionPolicy:
    """Finite runtime limits for one autonomous market session."""

    max_cycles: int = 12
    interval_seconds: int = 300

    def validate(self) -> None:
        if not 1 <= self.max_cycles <= 78:
            raise ValueError("max_cycles must be between 1 and 78.")
        if not 60 <= self.interval_seconds <= 1_800:
            raise ValueError("interval_seconds must be between 60 and 1800.")


async def run_bounded_session(
    cycle: Callable[[int], Awaitable[Mapping[str, Any]]],
    policy: SessionPolicy,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> tuple[Mapping[str, Any], ...]:
    """Run a finite number of fail-closed cycles with a fixed cooldown."""

    policy.validate()
    results: list[Mapping[str, Any]] = []
    for index in range(1, policy.max_cycles + 1):
        results.append(await cycle(index))
        if index < policy.max_cycles:
            await sleep(policy.interval_seconds)
    return tuple(results)
