from datetime import datetime, timezone

from context_engine.technical_snapshot import (
    MultiTimeframeAnalyzer,
)


def format_timestamp(
    timestamp_ms: int | None,
) -> str:

    if timestamp_ms is None:
        return "None"

    return datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc,
    ).isoformat()


def print_timeframe(
    snapshot,
) -> None:

    print(
        f"\n[{snapshot.timeframe}]"
    )

    print(
        f"Close: "
        f"{snapshot.latest_close:.2f}"
    )

    print(
        f"Trend: "
        f"{snapshot.trend.value}"
    )

    print(
        f"Structure: "
        f"{snapshot.latest_structure_label}"
    )

    print(
        f"EMA 20: "
        f"{snapshot.indicators.ema_20:.2f}"
    )

    print(
        f"EMA 50: "
        f"{snapshot.indicators.ema_50:.2f}"
    )

    print(
        f"EMA 200: "
        f"{snapshot.indicators.ema_200:.2f}"
    )

    print(
        f"RSI 14: "
        f"{snapshot.indicators.rsi_14:.2f}"
    )

    print(
        f"ATR 14: "
        f"{snapshot.indicators.atr_14:.2f}"
    )

    print(
        f"ATR %: "
        f"{snapshot.indicators.atr_percent:.4f}%"
    )

    print(
        f"Latest Swing High: "
        f"{snapshot.latest_swing_high}"
    )

    print(
        f"Latest Swing Low: "
        f"{snapshot.latest_swing_low}"
    )

    if snapshot.latest_break_type is None:
        print(
            "Latest Break: None"
        )

    else:
        print(
            f"Latest Break: "
            f"{snapshot.latest_break_type.value}"
        )

        print(
            f"Broken Level: "
            f"{snapshot.latest_break_level}"
        )

        print(
            "Break Time:",
            format_timestamp(
                snapshot.latest_break_ts_ms
            ),
        )

    print(
        f"Raw / Normalized Swings: "
        f"{snapshot.raw_swing_count} / "
        f"{snapshot.normalized_swing_count}"
    )

    print(
        f"Structure Breaks: "
        f"{snapshot.structure_break_count}"
    )


def main():
    print(
        "=== Sprint 2 — "
        "Multi-Timeframe Analysis Verification ==="
    )

    analyzer = MultiTimeframeAnalyzer()

    snapshot = analyzer.analyze()

    print(
        f"\nSymbol: {snapshot.symbol}"
    )

    print(
        f"Generated: "
        f"{snapshot.generated_at_utc.isoformat()}"
    )

    print(
        f"Trend Alignment: "
        f"{snapshot.trend_alignment.value}"
    )

    print_timeframe(
        snapshot.timeframe_15m
    )

    print_timeframe(
        snapshot.timeframe_1h
    )

    print_timeframe(
        snapshot.timeframe_4h
    )

    print(
        "\nMachine-readable JSON:"
    )

    print(
        snapshot.to_json()
    )

    print(
        "\nMulti-timeframe analysis: OK"
    )


if __name__ == "__main__":
    main()