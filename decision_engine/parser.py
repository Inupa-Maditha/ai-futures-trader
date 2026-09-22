from __future__ import annotations

from pydantic import ValidationError

from decision_engine.schema import (
    DecisionProposal,
)


class DecisionParseError(ValueError):
    pass


class DecisionResponseParser:
    def parse(
        self,
        raw_response: str,
    ) -> DecisionProposal:

        try:
            return (
                DecisionProposal
                .model_validate_json(
                    raw_response
                )
            )

        except ValidationError as exc:
            details = exc.errors(
                include_url=False
            )

            raise DecisionParseError(
                "LLM response failed "
                "DecisionProposal validation. "
                f"Details: {details}"
            ) from exc

        except ValueError as exc:
            raise DecisionParseError(
                "LLM response is not "
                f"valid JSON. Details: {exc}"
            ) from exc