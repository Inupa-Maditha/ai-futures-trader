from time import sleep

from config.settings import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    validate_openai_settings,
)

from context_engine.market_context import (
    MarketContextBuilder,
)

from decision_engine.llm_service import (
    LLMDecisionService,
)

from decision_engine.providers.openai_provider import (
    OpenAIResponsesProvider,
)

from market_data.runner import (
    MarketDataRunner,
)


def main():
    print(
        "=== Sprint 3 — "
        "Real LLM Decision Verification ==="
    )

    validate_openai_settings()

    runner = MarketDataRunner(
        rest_poll_seconds=60,
    )

    try:
        runner.start()

        print(
            "\nCollecting live market data..."
        )

        sleep(5)

        context_builder = (
            MarketContextBuilder(
                runner=runner,
                orderbook_depth_levels=10,
            )
        )

        context = context_builder.build(
            require_healthy=True,
        )

        provider = OpenAIResponsesProvider(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
        )

        service = LLMDecisionService(
            provider=provider,
        )

        print(
            f"\nCalling model: "
            f"{OPENAI_MODEL}"
        )

        result = service.decide(
            context
        )

        print(
            f"\nAccepted: "
            f"{result.accepted}"
        )

        if result.error:
            print(
                f"Error: {result.error}"
            )

        if result.validation:
            print(
                "Validation reasons:",
                result.validation.reasons,
            )

        proposal = result.proposal

        if proposal is None:
            print(
                "\nNo valid proposal produced."
            )
            return

        print(
            f"\nAction: "
            f"{proposal.action.value}"
        )

        print(
            f"Setup Quality: "
            f"{proposal.setup_quality.value}"
        )

        print(
            f"Confidence: "
            f"{proposal.confidence}"
        )

        print(
            f"Thesis: "
            f"{proposal.thesis}"
        )

        print("\nEvidence:")

        for item in proposal.evidence:
            print(
                f"- [{item.direction.value}] "
                f"{item.source}: "
                f"{item.observation}"
            )

        if (
            proposal.action.value
            == "NO_TRADE"
        ):
            print(
                "\nNo Trade Reason:",
                proposal.no_trade_reason,
            )

        else:
            print(
                f"\nEntry: "
                f"{proposal.entry_price}"
            )

            print(
                f"Stop Loss: "
                f"{proposal.stop_loss}"
            )

            print(
                f"Take Profit: "
                f"{proposal.take_profit}"
            )

            print(
                "Invalidation:",
                proposal.invalidation_reason,
            )

        print(
            "\nReal LLM decision "
            "verification complete."
        )

    finally:
        runner.stop()


if __name__ == "__main__":
    main()