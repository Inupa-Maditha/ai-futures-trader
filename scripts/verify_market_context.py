from time import sleep

from context_engine.market_context import (
    MarketContextBuilder,
)

from market_data.runner import (
    MarketDataRunner,
)


def main():
    print(
        "=== Sprint 3 — "
        "Market Context Verification ==="
    )

    runner = MarketDataRunner(
        rest_poll_seconds=60,
    )

    try:
        runner.start()

        print(
            "\nCollecting live context data..."
        )

        sleep(5)

        builder = MarketContextBuilder(
            runner=runner,
            orderbook_depth_levels=10,
        )

        context = builder.build(
            require_healthy=True,
        )

        print(
            f"\nSymbol: {context.symbol}"
        )

        print(
            f"Schema Version: "
            f"{context.schema_version}"
        )

        print(
            f"Generated: "
            f"{context.generated_at_utc.isoformat()}"
        )

        print(
            "\n[Technical]"
        )

        print(
            "Trend Alignment:",
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

        print(
            "\n[Order Book]"
        )

        print(
            f"Best Bid: "
            f"{context.orderbook.best_bid}"
        )

        print(
            f"Best Ask: "
            f"{context.orderbook.best_ask}"
        )

        print(
            f"Spread: "
            f"{context.orderbook.spread}"
        )

        print(
            f"Spread bps: "
            f"{context.orderbook.spread_bps:.4f}"
        )

        print(
            f"Depth Imbalance: "
            f"{context.orderbook.depth_imbalance:.4f}"
        )

        print(
            "\n[Trade Flow]"
        )

        print(
            f"Buy Volume: "
            f"{context.trade_flow.aggressive_buy_volume}"
        )

        print(
            f"Sell Volume: "
            f"{context.trade_flow.aggressive_sell_volume}"
        )

        print(
            f"Trade Imbalance: "
            f"{context.trade_flow.signed_volume_imbalance:.4f}"
        )

        print(
            "\n[Liquidations]"
        )

        print(
            f"Events: "
            f"{context.liquidations.event_count}"
        )

        print(
            f"Long Liquidations: "
            f"{context.liquidations.long_liquidation_volume}"
        )

        print(
            f"Short Liquidations: "
            f"{context.liquidations.short_liquidation_volume}"
        )

        print(
            "\n[Derivatives]"
        )

        print(
            f"Open Interest: "
            f"{context.derivatives.open_interest}"
        )

        print(
            f"OI Change %: "
            f"{context.derivatives.oi_change_percent}"
        )

        print(
            f"Funding Rate: "
            f"{context.derivatives.current_funding_rate}"
        )

        print(
            f"Long Ratio: "
            f"{context.derivatives.long_account_ratio}"
        )

        print(
            f"Short Ratio: "
            f"{context.derivatives.short_account_ratio}"
        )

        print(
            "\n[Health]"
        )

        print(
            "All Required Healthy:",
            context.health
            .all_required_healthy,
        )

        print(
            "\nJSON serialization:"
        )

        json_output = context.to_json()

        print(
            f"JSON length: "
            f"{len(json_output)} characters"
        )

        print(
            "\nMarket context verification: OK"
        )

    finally:
        runner.stop()


if __name__ == "__main__":
    main()