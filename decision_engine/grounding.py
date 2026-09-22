from __future__ import annotations

from dataclasses import dataclass

from context_engine.market_context import (
    MarketContextSnapshot,
)

from decision_engine.evidence_catalog import (
    build_evidence_catalog,
)

from decision_engine.schema import (
    DecisionProposal,
)


@dataclass(
    frozen=True,
    slots=True,
)
class GroundingValidationResult:
    valid: bool
    reasons: tuple[str, ...]


class EvidenceGroundingValidator:
    def validate(
        self,
        proposal: DecisionProposal,
        context: MarketContextSnapshot,
    ) -> GroundingValidationResult:

        catalog = build_evidence_catalog(
            context
        )

        reasons: list[str] = []

        for index, evidence in enumerate(
            proposal.evidence
        ):
            path = evidence.context_path

            if path not in catalog:
                reasons.append(
                    f"Evidence {index}: "
                    f"unsupported context path "
                    f"'{path}'."
                )
                continue

            expected = catalog[path]
            claimed = evidence.value

            if (
                not isinstance(
                    claimed,
                    str,
                )
                or claimed != expected
            ):
                reasons.append(
                    f"Evidence {index}: "
                    f"value mismatch for "
                    f"'{path}'. "
                    f"Expected {expected!r}, "
                    f"got {claimed!r}."
                )

        return GroundingValidationResult(
            valid=len(reasons) == 0,
            reasons=tuple(reasons),
        )