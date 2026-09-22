from time import (
    perf_counter,
    sleep,
)

from config.settings import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    validate_groq_settings,
)

from context_engine.market_context import (
    MarketContextBuilder,
)

from decision_engine.llm_service import (
    LLMDecisionService,
)

from decision_engine.providers.groq_provider import (
    GroqProvider,
)

from market_data.runner import (
    MarketDataRunner,
)


def main():
    print(
        "=== Sprint 3 — "
        "GroqCloud Decision Verification ==="
    )

    validate_groq_settings()

    runner = MarketDataRunner(
        rest_poll_seconds=60,
    )

    try:
        runner.start()

        print(
            "\nCollecting live market data..."
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
            "\nContext:"
        )

        print(
            "Alignment:",
            context.technical
            .trend_alignment.value,
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

        provider = GroqProvider(
            api_key=GROQ_API_KEY,
            model=GROQ_MODEL,
            base_url=GROQ_BASE_URL,
        )

        service = LLMDecisionService(
            provider=provider,
        )

        print(
            f"\nCalling Groq model: "
            f"{GROQ_MODEL}"
        )

        start = perf_counter()

        result = service.decide(
            context
        )

        elapsed = (
            perf_counter()
            - start
        )

        print(
            f"\nResponse Time: "
            f"{elapsed:.2f}s"
        )

        print(
            f"Accepted: "
            f"{result.accepted}"
        )

        if result.error:
            print(
                f"Error: "
                f"{result.error}"
            )

        if (
            result.validation
            is not None
        ):
            print(
                "Validation Reasons:",
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

        print(
            "\nEvidence:"
        )

        for item in proposal.evidence:
            print(
                f"- [{item.direction.value}] "
                f"{item.context_path} = "
                f"{item.value} | "
                f"{item.interpretation}"
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
                proposal
                .invalidation_reason,
            )

        print(
            "\nGroqCloud decision "
            "verification complete."
        )

    finally:
        runner.stop()


if __name__ == "__main__":
    main()