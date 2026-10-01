from __future__ import annotations

from dataclasses import replace
from time import sleep

from context_engine.market_context import (
    MarketContextBuilder,
)

from market_data.runner import (
    MarketDataRunner,
)

from scripts.run_sprint5_demo_execution import (
    build_decision_service,
    print_proposal,
)


def enum_value(
    current,
    value: str,
):
    return type(current)(value)


def make_timeframe(
    timeframe,
    *,
    bullish: bool,
    price: float,
):
    indicators = timeframe.indicators

    if bullish:
        indicators = replace(
            indicators,
            ema_20=price * 0.995,
            ema_50=price * 0.990,
            ema_200=price * 0.980,
            rsi_14=62.0,
        )

        break_type = (
            enum_value(
                timeframe.latest_break_type,
                "BOS_BULLISH",
            )
            if timeframe.latest_break_type
            is not None
            else None
        )

        return replace(
            timeframe,
            latest_close=price,
            trend=enum_value(
                timeframe.trend,
                "BULLISH",
            ),
            latest_structure_label="HH",
            indicators=indicators,
            latest_swing_high=(
                price * 1.010
            ),
            latest_swing_low=(
                price * 0.990
            ),
            latest_break_type=break_type,
            latest_break_level=(
                price * 0.990
            ),
        )

    indicators = replace(
        indicators,
        ema_20=price * 1.005,
        ema_50=price * 1.010,
        ema_200=price * 1.020,
        rsi_14=38.0,
    )

    break_type = (
        enum_value(
            timeframe.latest_break_type,
            "BOS_BEARISH",
        )
        if timeframe.latest_break_type
        is not None
        else None
    )

    return replace(
        timeframe,
        latest_close=price,
        trend=enum_value(
            timeframe.trend,
            "BEARISH",
        ),
        latest_structure_label="LL",
        indicators=indicators,
        latest_swing_high=(
            price * 1.010
        ),
        latest_swing_low=(
            price * 0.990
        ),
        latest_break_type=break_type,
        latest_break_level=(
            price * 1.010
        ),
    )


def make_synthetic_context(
    base,
    *,
    bullish: bool,
):
    price = base.orderbook.mid_price

    technical = base.technical

    timeframe_15m = make_timeframe(
        technical.timeframe_15m,
        bullish=bullish,
        price=price,
    )

    timeframe_1h = make_timeframe(
        technical.timeframe_1h,
        bullish=bullish,
        price=price,
    )

    timeframe_4h = make_timeframe(
        technical.timeframe_4h,
        bullish=bullish,
        price=price,
    )

    alignment = enum_value(
        technical.trend_alignment,
        (
            "BULLISH_ALIGNED"
            if bullish
            else "BEARISH_ALIGNED"
        ),
    )

    technical = replace(
        technical,
        trend_alignment=alignment,
        timeframe_15m=timeframe_15m,
        timeframe_1h=timeframe_1h,
        timeframe_4h=timeframe_4h,
    )

    if bullish:
        derivatives = replace(
            base.derivatives,
            oi_change_percent=1.20,
            current_funding_rate=0.00003,
            long_account_ratio=0.56,
            short_account_ratio=0.44,
            long_short_account_ratio=1.2727,
        )

        trade_flow = replace(
            base.trade_flow,
            aggressive_buy_volume=80.0,
            aggressive_sell_volume=20.0,
            signed_volume_imbalance=0.60,
            trade_count=500,
        )

        orderbook = replace(
            base.orderbook,
            depth_imbalance=0.55,
        )

        liquidations = replace(
            base.liquidations,
            long_liquidation_volume=1.0,
            short_liquidation_volume=12.0,
            total_liquidation_volume=13.0,
            event_count=8,
        )

    else:
        derivatives = replace(
            base.derivatives,
            oi_change_percent=1.20,
            current_funding_rate=-0.00003,
            long_account_ratio=0.42,
            short_account_ratio=0.58,
            long_short_account_ratio=0.7241,
        )

        trade_flow = replace(
            base.trade_flow,
            aggressive_buy_volume=20.0,
            aggressive_sell_volume=80.0,
            signed_volume_imbalance=-0.60,
            trade_count=500,
        )

        orderbook = replace(
            base.orderbook,
            depth_imbalance=-0.55,
        )

        liquidations = replace(
            base.liquidations,
            long_liquidation_volume=12.0,
            short_liquidation_volume=1.0,
            total_liquidation_volume=13.0,
            event_count=8,
        )

    return replace(
        base,
        technical=technical,
        derivatives=derivatives,
        trade_flow=trade_flow,
        orderbook=orderbook,
        liquidations=liquidations,
    )


def run_scenario(
    name: str,
    context,
):
    print(
        "\n"
        "========================================"
    )

    print(
        f"SCENARIO: {name}"
    )

    print(
        "========================================"
    )

    result = (
        build_decision_service()
        .decide(context)
    )

    print(
        f"Accepted: {result.accepted}"
    )

    if not result.accepted:
        print(
            f"Error: {result.error}"
        )
        return

    if result.proposal is None:
        print(
            "Proposal: None"
        )
        return

    print_proposal(
        result.proposal
    )


def main():
    print(
        "=== LLM LONG/SHORT "
        "REACHABILITY TEST ==="
    )

    print(
        "\nThis test does NOT execute trades."
    )

    runner = MarketDataRunner(
        rest_poll_seconds=60,
    )

    try:
        runner.start()

        print(
            "\nCollecting live base context..."
        )

        sleep(5)

        base_context = (
            MarketContextBuilder(
                runner=runner,
                orderbook_depth_levels=10,
            )
            .build(
                require_healthy=True
            )
        )

        bullish_context = (
            make_synthetic_context(
                base_context,
                bullish=True,
            )
        )

        bearish_context = (
            make_synthetic_context(
                base_context,
                bullish=False,
            )
        )

        run_scenario(
            "CLEAR BULLISH",
            bullish_context,
        )

        run_scenario(
            "CLEAR BEARISH",
            bearish_context,
        )

    finally:
        runner.stop()


if __name__ == "__main__":
    main()