"""Evidence-aware consensus that rewards agreement and preserves dissent."""

from __future__ import annotations

from dataclasses import dataclass, field

from .research import AdvisoryAction, AdvisorName, AdvisorOpinion


@dataclass(frozen=True)
class ConsensusDecision:
    """Auditable aggregation of independent advisor opinions."""

    action: AdvisoryAction
    confidence: float
    rationale: str
    supporting_advisors: tuple[AdvisorName, ...]
    dissenting_advisors: tuple[AdvisorName, ...]
    evidence_refs: tuple[str, ...]
    hard_vetoes: tuple[str, ...]


@dataclass(frozen=True)
class ConsensusConfig:
    """Explicit advisor weights; risk is a veto role, not an alpha vote."""

    weights: dict[AdvisorName, float] = field(
        default_factory=lambda: {
            AdvisorName.TECHNICAL_REGIME: 1.30,
            AdvisorName.OPTIONS_LIQUIDITY: 1.30,
            AdvisorName.NEWS_CATALYST: 0.70,
            AdvisorName.FINANCIALS_FORENSIC_AUDITOR: 1.00,
            AdvisorName.VALUE_FRAMEWORK: 1.00,
            AdvisorName.RISK_CRITIC: 0.00,
        }
    )
    minimum_confidence: float = 0.60
    maximum_opposition_ratio: float = 0.55


class ConsensusEngine:
    """Require technical/options agreement and fail closed on strong conflict."""

    def __init__(self, config: ConsensusConfig | None = None) -> None:
        self.config = config or ConsensusConfig()

    def evaluate(self, opinions: tuple[AdvisorOpinion, ...]) -> ConsensusDecision:
        """Return CALL, PUT, or WAIT without creating an order."""

        vetoes = tuple(
            f"{opinion.advisor.value}: {opinion.thesis}"
            for opinion in opinions
            if opinion.hard_veto
        )
        if vetoes:
            return self._wait(
                "At least one independent advisor issued a hard veto.",
                opinions,
                hard_vetoes=vetoes,
            )

        by_name = {opinion.advisor: opinion for opinion in opinions}
        technical = by_name.get(AdvisorName.TECHNICAL_REGIME)
        options = by_name.get(AdvisorName.OPTIONS_LIQUIDITY)
        if technical is None or options is None:
            return self._wait("Required technical or options opinion is missing.", opinions)
        directional = {AdvisoryAction.CALL, AdvisoryAction.PUT}
        if technical.action not in directional or options.action not in directional:
            return self._wait(
                "Technical and options advisors must both be directional.", opinions
            )
        if technical.action is not options.action:
            return self._wait(
                "Technical and options advisors disagree on direction.", opinions
            )

        direction = technical.action
        opposing_direction = (
            AdvisoryAction.PUT if direction is AdvisoryAction.CALL else AdvisoryAction.CALL
        )
        support_score = 0.0
        opposition_score = 0.0
        wait_score = 0.0
        supporting: list[AdvisorName] = []
        dissenting: list[AdvisorName] = []
        evidence: set[str] = set()

        for opinion in opinions:
            weight = self.config.weights.get(opinion.advisor, 0)
            if opinion.action is direction:
                support_score += weight * opinion.confidence
                supporting.append(opinion.advisor)
                evidence.update(opinion.evidence_refs)
            elif opinion.action is opposing_direction:
                opposition_score += weight * opinion.confidence
                dissenting.append(opinion.advisor)
            elif opinion.action is AdvisoryAction.WAIT:
                wait_score += weight * opinion.confidence * 0.50
                dissenting.append(opinion.advisor)

        fundamental = by_name.get(AdvisorName.FINANCIALS_FORENSIC_AUDITOR)
        value = by_name.get(AdvisorName.VALUE_FRAMEWORK)
        if (
            fundamental is not None
            and value is not None
            and fundamental.action is opposing_direction
            and value.action is opposing_direction
        ):
            return self._wait(
                "Financial quality and value framework both oppose the trade.",
                opinions,
            )

        if support_score <= 0:
            return self._wait("No weighted directional support is available.", opinions)
        if opposition_score / support_score > self.config.maximum_opposition_ratio:
            return self._wait("Weighted opposition is too strong.", opinions)

        denominator = support_score + opposition_score + wait_score
        confidence = support_score / denominator if denominator else 0
        confidence = min(confidence, min(technical.confidence, options.confidence))
        if confidence < self.config.minimum_confidence:
            return self._wait("Consensus confidence is below the threshold.", opinions)

        return ConsensusDecision(
            action=direction,
            confidence=confidence,
            rationale=(
                f"{direction.value} consensus: technical and options evidence agree; "
                f"weighted support {support_score:.2f}, opposition {opposition_score:.2f}."
            ),
            supporting_advisors=tuple(supporting),
            dissenting_advisors=tuple(dissenting),
            evidence_refs=tuple(sorted(evidence)),
            hard_vetoes=(),
        )

    def _wait(
        self,
        rationale: str,
        opinions: tuple[AdvisorOpinion, ...],
        *,
        hard_vetoes: tuple[str, ...] = (),
    ) -> ConsensusDecision:
        """Build a consistent no-trade consensus while retaining evidence."""

        dissenting = tuple(
            opinion.advisor
            for opinion in opinions
            if opinion.action not in {AdvisoryAction.ABSTAIN}
        )
        evidence = tuple(
            sorted({ref for opinion in opinions for ref in opinion.evidence_refs})
        )
        return ConsensusDecision(
            action=AdvisoryAction.WAIT,
            confidence=1,
            rationale=rationale,
            supporting_advisors=(),
            dissenting_advisors=dissenting,
            evidence_refs=evidence,
            hard_vetoes=hard_vetoes,
        )
