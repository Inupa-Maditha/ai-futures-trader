from __future__ import annotations

from dataclasses import dataclass

from context_engine.market_context import (
    MarketContextSnapshot,
)

from decision_engine.parser import (
    DecisionParseError,
    DecisionResponseParser,
)

from decision_engine.schema import (
    DecisionProposal,
)

from decision_engine.validator import (
    DecisionValidationResult,
    DecisionValidator,
)


@dataclass(
    frozen=True,
    slots=True,
)
class DecisionPipelineResult:
    accepted: bool

    proposal: DecisionProposal | None

    validation: (
        DecisionValidationResult | None
    )

    error: str | None


class DecisionPipeline:
    def __init__(
        self,
        parser: DecisionResponseParser | None = None,
        validator: DecisionValidator | None = None,
    ):
        self.parser = (
            parser
            or DecisionResponseParser()
        )

        self.validator = (
            validator
            or DecisionValidator()
        )

    def process(
        self,
        raw_response: str,
        context: MarketContextSnapshot,
    ) -> DecisionPipelineResult:

        try:
            proposal = self.parser.parse(
                raw_response
            )

        except DecisionParseError as exc:
            return DecisionPipelineResult(
                accepted=False,
                proposal=None,
                validation=None,
                error=str(exc),
            )

        validation = (
            self.validator.validate(
                proposal,
                context,
            )
        )

        if not validation.accepted:
            return DecisionPipelineResult(
                accepted=False,
                proposal=proposal,
                validation=validation,
                error=(
                    "Decision proposal failed "
                    "deterministic validation."
                ),
            )

        return DecisionPipelineResult(
            accepted=True,
            proposal=proposal,
            validation=validation,
            error=None,
        )