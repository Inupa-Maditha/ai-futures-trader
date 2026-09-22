from time import perf_counter, sleep

from config.settings import (
    LM_STUDIO_BASE_URL,
)

from context_engine.market_context import (
    MarketContextBuilder,
)

from decision_engine.llm_service import (
    LLMDecisionService,
)

from decision_engine.providers.lmstudio_provider import (
    LMStudioProvider,
)

from market_data.runner import (
    MarketDataRunner,
)


MODELS = [
    "qwen2.5-3b-instruct",
    "google/gemma-3-4b",
]


def run_model(
    model: str,
    context,
):
    provider = LMStudioProvider(
        base_url=LM_STUDIO_BASE_URL,
        model=model,
    )

    service = LLMDecisionService(
        provider=provider,
    )

    start = perf_counter()

    result = service.decide(
        context
    )

    elapsed = (
        perf_counter() - start
    )

    return result, elapsed


def print_result(
    model: str,
    result,
    elapsed: float,
):
    print(
        "\n"
        + "=" * 70
    )

    print(
        f"MODEL: {model}"
    )

    print(
        f"Response Time: "
        f"{elapsed:.2f}s"
    )

    print(
        f"Accepted: "
        f"{result.accepted}"
    )

    if result.error:
        print(
            f"Error: {result.error}"
        )

    if result.validation:
        print(
            "Validation Reasons:",
            result.validation.reasons,
        )

    proposal = result.proposal

    if proposal is None:
        print(
            "No valid proposal."
        )
        return

    print(
        f"Action: "
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
        f"\nThesis:\n"
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
            "\nNo Trade Reason:"
        )

        print(
            proposal.no_trade_reason
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


def main():
    print(
        "=== Sprint 3 — "
        "Local Model Comparison ==="
    )

    runner = MarketDataRunner(
        rest_poll_seconds=60,
    )

    try:
        runner.start()

        print(
            "\nCollecting live market data..."
        )

        sleep(5)

        # Build ONCE so both models receive
        # the exact same market context.
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
            f"\nContext generated at: "
            f"{context.generated_at_utc.isoformat()}"
        )

        print(
            "Trend Alignment:",
            context.technical
            .trend_alignment.value,
        )

        for model in MODELS:
            print(
                f"\nCalling {model}..."
            )

            result, elapsed = run_model(
                model,
                context,
            )

            print_result(
                model,
                result,
                elapsed,
            )

        print(
            "\n"
            + "=" * 70
        )

        print(
            "Local model comparison complete."
        )

    finally:
        runner.stop()


if __name__ == "__main__":
    main()