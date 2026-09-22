from __future__ import annotations

from context_engine.market_context import (
    MarketContextSnapshot,
)

from decision_engine.pipeline import (
    DecisionPipeline,
    DecisionPipelineResult,
)

from decision_engine.prompt_builder import (
    DecisionPromptBuilder,
)

from decision_engine.providers.base import (
    LLMProvider,
)


class LLMDecisionService:
    def __init__(
        self,
        provider: LLMProvider,
        prompt_builder: (
            DecisionPromptBuilder | None
        ) = None,
        pipeline: DecisionPipeline | None = None,
    ):
        self.provider = provider

        self.prompt_builder = (
            prompt_builder
            or DecisionPromptBuilder()
        )

        self.pipeline = (
            pipeline
            or DecisionPipeline()
        )

    def decide(
        self,
        context: MarketContextSnapshot,
    ) -> DecisionPipelineResult:

        if not (
            context.health
            .all_required_healthy
        ):
            return DecisionPipelineResult(
                accepted=False,
                proposal=None,
                validation=None,
                error=(
                    "LLM call blocked: "
                    "market data is unhealthy."
                ),
            )

        package = self.prompt_builder.build(
            context
        )

        try:
            raw_response = (
                self.provider.generate(
                    package
                )
            )

        except Exception as exc:
            return DecisionPipelineResult(
                accepted=False,
                proposal=None,
                validation=None,
                error=(
                    "LLM provider failure: "
                    f"{exc}"
                ),
            )

        return self.pipeline.process(
            raw_response=raw_response,
            context=context,
        )