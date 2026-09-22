from __future__ import annotations

from context_engine.market_context import (
    MarketContextSnapshot,
)


def _number(
    value: float,
    digits: int,
) -> str:
    result = f"{value:.{digits}f}"

    if "." in result:
        result = result.rstrip("0").rstrip(".")

    if result == "-0":
        return "0"

    return result


def _optional_number(
    value: float | None,
    digits: int,
) -> str:
    if value is None:
        return "null"

    return _number(
        value,
        digits,
    )


def _optional_text(
    value: str | None,
) -> str:
    if value is None:
        return "null"

    return value


def build_evidence_catalog(
    context: MarketContextSnapshot,
) -> dict[str, str]:

    tech = context.technical

    catalog: dict[str, str] = {
        "technical.trend_alignment": (
            tech.trend_alignment.value
        ),

        "derivatives.open_interest": _number(
            context.derivatives.open_interest,
            3,
        ),

        "derivatives.oi_change_percent": (
            _optional_number(
                context.derivatives
                .oi_change_percent,
                4,
            )
        ),

        "derivatives.funding_rate": _number(
            context.derivatives
            .current_funding_rate,
            8,
        ),

        "derivatives.long_account_ratio": (
            _number(
                context.derivatives
                .long_account_ratio,
                4,
            )
        ),

        "derivatives.short_account_ratio": (
            _number(
                context.derivatives
                .short_account_ratio,
                4,
            )
        ),

        "derivatives.long_short_account_ratio": (
            _optional_number(
                context.derivatives
                .long_short_account_ratio,
                4,
            )
        ),

        "order_flow.signed_volume_imbalance": (
            _number(
                context.trade_flow
                .signed_volume_imbalance,
                4,
            )
        ),

        "order_flow.trade_count": str(
            context.trade_flow.trade_count
        ),

        "orderbook.mid_price": _number(
            context.orderbook.mid_price,
            2,
        ),

        "orderbook.spread": _number(
            context.orderbook.spread,
            4,
        ),

        "orderbook.spread_bps": _number(
            context.orderbook.spread_bps,
            4,
        ),

        "orderbook.depth_levels": str(
            context.orderbook.depth_levels
        ),

        "orderbook.depth_imbalance": (
            _number(
                context.orderbook
                .depth_imbalance,
                4,
            )
        ),

        "liquidations.event_count": str(
            context.liquidations.event_count
        ),

        "liquidations.long_liquidation_volume": (
            _number(
                context.liquidations
                .long_liquidation_volume,
                3,
            )
        ),

        "liquidations.short_liquidation_volume": (
            _number(
                context.liquidations
                .short_liquidation_volume,
                3,
            )
        ),

        "health.all_required_healthy": (
            "true"
            if context.health
            .all_required_healthy
            else "false"
        ),
    }

    for name, snapshot in (
        ("15m", tech.timeframe_15m),
        ("1h", tech.timeframe_1h),
        ("4h", tech.timeframe_4h),
    ):
        prefix = f"technical.{name}"

        catalog.update(
            {
                f"{prefix}.close": _number(
                    snapshot.latest_close,
                    2,
                ),

                f"{prefix}.trend": (
                    snapshot.trend.value
                ),

                f"{prefix}.structure": (
                    _optional_text(
                        snapshot
                        .latest_structure_label
                    )
                ),

                f"{prefix}.ema_20": _number(
                    snapshot.indicators.ema_20,
                    2,
                ),

                f"{prefix}.ema_50": _number(
                    snapshot.indicators.ema_50,
                    2,
                ),

                f"{prefix}.ema_200": _number(
                    snapshot.indicators.ema_200,
                    2,
                ),

                f"{prefix}.rsi_14": _number(
                    snapshot.indicators.rsi_14,
                    2,
                ),

                f"{prefix}.atr_14": _number(
                    snapshot.indicators.atr_14,
                    2,
                ),

                f"{prefix}.atr_percent": _number(
                    snapshot.indicators
                    .atr_percent,
                    4,
                ),

                f"{prefix}.latest_swing_high": (
                    _optional_number(
                        snapshot
                        .latest_swing_high,
                        2,
                    )
                ),

                f"{prefix}.latest_swing_low": (
                    _optional_number(
                        snapshot
                        .latest_swing_low,
                        2,
                    )
                ),

                f"{prefix}.latest_break": (
                    snapshot
                    .latest_break_type.value
                    if snapshot
                    .latest_break_type
                    is not None
                    else "null"
                ),

                f"{prefix}.latest_break_level": (
                    _optional_number(
                        snapshot
                        .latest_break_level,
                        2,
                    )
                ),
            }
        )

    return catalog