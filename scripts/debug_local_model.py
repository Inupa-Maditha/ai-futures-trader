from time import sleep

from config.settings import (
    LM_STUDIO_BASE_URL,
)

from context_engine.market_context import (
    MarketContextBuilder,
)

from decision_engine.parser import (
    DecisionParseError,
    DecisionResponseParser,
)

from decision_engine.prompt_builder import (
    DecisionPromptBuilder,
)

from decision_engine.providers.lmstudio_provider import (
    LMStudioProvider,
)

from market_data.runner import (
    MarketDataRunner,
)


MODEL = "qwen2.5-3b-instruct"


def main():
    print(
        "=== Local Model Debug ==="
    )

    runner = MarketDataRunner(
        rest_poll_seconds=60,
    )

    try:
        runner.start()

        print(
            "\nCollecting market data..."
        )

        sleep(5)

        context = (
            MarketContextBuilder(
                runner=runner,
                orderbook_depth_levels=10,
            )
            .build(
                require_healthy=True
            )
        )

        print(
            "\nActual deterministic trends:"
        )

        print(
            "15m:",
            context.technical
            .timeframe_15m.trend.value,
        )

        print(
            "1h:",
            context.technical
            .timeframe_1h.trend.value,
        )

        print(
            "4h:",
            context.technical
            .timeframe_4h.trend.value,
        )

        package = (
            DecisionPromptBuilder()
            .build(context)
        )

        provider = LMStudioProvider(
            base_url=LM_STUDIO_BASE_URL,
            model=MODEL,
        )

        print(
            f"\nCalling: {MODEL}"
        )

        raw = provider.generate(
            package
        )

        print(
            "\n=== RAW MODEL OUTPUT ==="
        )

        print(raw)

        print(
            "\n=== PARSER RESULT ==="
        )

        parser = (
            DecisionResponseParser()
        )

        try:
            proposal = parser.parse(
                raw
            )

            print(
                "VALID"
            )

            print(
                proposal.model_dump_json(
                    indent=2
                )
            )

        except DecisionParseError as exc:
            print(
                "INVALID"
            )

            print(exc)

    finally:
        runner.stop()


if __name__ == "__main__":
    main()