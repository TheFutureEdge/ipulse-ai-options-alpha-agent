"""Prompted independent advisors constrained to a supplied evidence catalog."""

from __future__ import annotations

from dataclasses import dataclass

from .advisors import ResearchAdvisor
from .reasoning import StructuredReasoningClient
from .research import (
    AdvisoryAction,
    AdvisorName,
    AdvisorOpinion,
    ResearchContext,
)


OPINION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "action": {"type": "string", "enum": ["CALL", "PUT", "WAIT", "ABSTAIN"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "thesis": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "contrary_evidence": {"type": "array", "items": {"type": "string"}},
        "invalidation_conditions": {"type": "array", "items": {"type": "string"}},
        "max_entry_price": {"type": ["number", "null"]},
        "hard_veto": {"type": "boolean"},
        "abstention_reason": {"type": ["string", "null"]},
    },
    "required": [
        "action",
        "confidence",
        "thesis",
        "evidence_refs",
        "contrary_evidence",
        "invalidation_conditions",
        "max_entry_price",
        "hard_veto",
        "abstention_reason",
    ],
}


@dataclass(frozen=True)
class AdvisorSpec:
    """Prompt scope and evidence prerequisites for one research role."""

    name: AdvisorName
    objective: str
    required_category: str | None = None


SPECS = (
    AdvisorSpec(
        AdvisorName.TECHNICAL_REGIME,
        "Assess trend agreement and volatility regime. Prefer WAIT when signals conflict.",
        "technical",
    ),
    AdvisorSpec(
        AdvisorName.NEWS_CATALYST,
        "Assess only timestamped news catalysts, priced-in expectations, and contradictions.",
        "news",
    ),
    AdvisorSpec(
        AdvisorName.OPTIONS_LIQUIDITY,
        "Assess option direction, premium, liquidity, spread, and execution fragility.",
        "options",
    ),
    AdvisorSpec(
        AdvisorName.FINANCIALS_FORENSIC_AUDITOR,
        "Audit cash conversion, accruals, leverage, dilution, restatements, and auditor opinion. Issue a hard WAIT veto for severe reporting integrity concerns.",
        "financials",
    ),
    AdvisorSpec(
        AdvisorName.VALUE_FRAMEWORK,
        "Evaluate margin of safety, cash yield, growth, fair value, and relative multiples without treating a low multiple as sufficient evidence.",
        "valuation",
    ),
    AdvisorSpec(
        AdvisorName.RISK_CRITIC,
        "Challenge stale data, closed markets, duplicates, pending orders, trade frequency, and unsupported assumptions. Risk supplies vetoes, not alpha.",
        "operations",
    ),
)


class PromptedResearchAdvisor:
    """One isolated LLM role that cannot cite evidence outside the run."""

    def __init__(
        self,
        spec: AdvisorSpec,
        client: StructuredReasoningClient,
    ) -> None:
        self.spec = spec
        self.client = client
        self.name = spec.name

    async def analyze(self, context: ResearchContext) -> AdvisorOpinion:
        """Run one strict structured analysis or fail closed to ABSTAIN."""

        catalog = context.evidence_catalog()
        if self.spec.required_category and not any(
            record.category == self.spec.required_category for record in catalog.values()
        ):
            return self._abstain(
                f"No {self.spec.required_category} evidence was supplied."
            )
        instructions = (
            "You are one independent investment research advisor. You have no broker "
            "tools and no authority to place orders. Use only supplied evidence IDs. "
            "Do not infer missing financial figures, filings, prices, dates, or news. "
            "Return ABSTAIN when required evidence is missing. Return WAIT when evidence "
            "is conflicting or insufficient. A hard_veto is allowed only with WAIT and "
            "must be grounded in cited evidence. Preserve contrary evidence and define "
            "falsifiable invalidation conditions. "
            f"Your specialized objective: {self.spec.objective}"
        )
        try:
            payload = await self.client.complete_json(
                schema_name=f"{self.name.value}_opinion",
                instructions=instructions,
                input_payload=context.prompt_payload(),
                schema=OPINION_SCHEMA,
            )
            return AdvisorOpinion.from_mapping(
                self.name,
                payload,
                allowed_evidence_ids=frozenset(catalog),
                reasoning_source="openai_responses",
            )
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            return self._abstain(
                f"Structured advisor output failed validation: {type(exc).__name__}."
            )

    def _abstain(self, reason: str) -> AdvisorOpinion:
        return AdvisorOpinion(
            advisor=self.name,
            action=AdvisoryAction.ABSTAIN,
            confidence=0,
            thesis="The advisor did not produce a validated opinion.",
            abstention_reason=reason,
            reasoning_source="openai_responses",
        )


def create_prompted_advisors(
    client: StructuredReasoningClient,
) -> tuple[ResearchAdvisor, ...]:
    """Create all six isolated prompted advisors over one shared client."""

    return tuple(PromptedResearchAdvisor(spec, client) for spec in SPECS)
