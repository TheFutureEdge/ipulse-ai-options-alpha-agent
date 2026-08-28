"""Tests for strict structured-output validation without network calls."""

from __future__ import annotations

import unittest
from typing import Any, Mapping

from ipulse_options_alpha_agent.llm_advisors import AdvisorSpec, PromptedResearchAdvisor
from ipulse_options_alpha_agent.reasoning import _extract_output_text
from ipulse_options_alpha_agent.research import (
    AdvisoryAction,
    AdvisorName,
    OperationalState,
    ResearchContext,
)
from ipulse_options_alpha_agent.strategy import StrategySignal


class FakeReasoningClient:
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = payload

    async def complete_json(self, **_: Any) -> Mapping[str, Any]:
        return self.payload


def context() -> ResearchContext:
    return ResearchContext(
        underlying="SPY",
        signal=StrategySignal(
            underlying="SPY",
            option_symbol="SPY260904C00772000",
            option_limit_price=2,
            fast_return_pct=0.5,
            slow_return_pct=0.8,
            realized_volatility_pct=20,
            option_spread_pct=3,
            confidence=0.75,
        ),
        as_of_utc="2026-08-28T14:00:00Z",
        operational=OperationalState(True, 5, 0, False, 0, None),
    )


class ReasoningTests(unittest.IsolatedAsyncioTestCase):
    def test_extracts_responses_output_text(self) -> None:
        result = _extract_output_text(
            {"output": [{"content": [{"type": "output_text", "text": "{}"}]}]}
        )
        self.assertEqual(result, "{}")

    async def test_unknown_evidence_reference_fails_closed(self) -> None:
        advisor = PromptedResearchAdvisor(
            AdvisorSpec(AdvisorName.TECHNICAL_REGIME, "test", "technical"),
            FakeReasoningClient(
                {
                    "action": "CALL",
                    "confidence": 0.8,
                    "thesis": "test",
                    "evidence_refs": ["invented:source"],
                    "contrary_evidence": [],
                    "invalidation_conditions": ["test"],
                    "max_entry_price": 2,
                    "hard_veto": False,
                    "abstention_reason": None,
                }
            ),
        )
        result = await advisor.analyze(context())
        self.assertEqual(result.action, AdvisoryAction.ABSTAIN)


if __name__ == "__main__":
    unittest.main()
