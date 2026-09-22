from time import sleep

from context_engine.market_context import (
    MarketContextBuilder,
)

from decision_engine.prompt_builder import (
    DecisionPromptBuilder,
)

from market_data.runner import (
    MarketDataRunner,
)


def main():
    print(
        "=== Sprint 3 — "
        "LLM Prompt Package Verification ==="
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

        context_builder = (
            MarketContextBuilder(
                runner=runner,
                orderbook_depth_levels=10,
            )
        )

        context = context_builder.build(
            require_healthy=True,
        )

        prompt_builder = (
            DecisionPromptBuilder()
        )

        package = prompt_builder.build(
            context
        )

        user_json = package.user_json()

        print(
            f"\nPrompt Version: "
            f"{package.prompt_version}"
        )

        print(
            f"System Prompt Length: "
            f"{len(package.system_prompt)}"
        )

        print(
            f"User Context Length: "
            f"{len(user_json)}"
        )

        market = (
            package.user_payload[
                "market_context"
            ]
        )

        print(
            "\nTrend Alignment:",
            market["technical"]
            ["trend_alignment"],
        )

        print(
            "15m:",
            market["technical"]
            ["15m"]["trend"],
        )

        print(
            "1h:",
            market["technical"]
            ["1h"]["trend"],
        )

        print(
            "4h:",
            market["technical"]
            ["4h"]["trend"],
        )

        print(
            "\nMid Price:",
            market["orderbook"]
            ["mid_price"],
        )

        print(
            "Trade Imbalance:",
            market["order_flow"]
            ["signed_volume_imbalance"],
        )

        print(
            "OI Change %:",
            market["derivatives"]
            ["oi_change_percent"],
        )

        print(
            "Funding:",
            market["derivatives"]
            ["funding_rate"],
        )

        print(
            "\nAll Required Healthy:",
            market["health"]
            ["all_required_healthy"],
        )

        print(
            "\nLLM prompt package "
            "verification: OK"
        )

    finally:
        runner.stop()


if __name__ == "__main__":
    main()