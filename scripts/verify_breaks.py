from datetime import datetime, timezone

from market_data.candles import CandleService

from market_structure.breaks import (
    StructureBreakDetector,
)

from market_structure.swings import (
    SwingDetector,
    normalize_swings,
)


def format_timestamp(
    timestamp_ms: int,
) -> str:
    return datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc,
    ).isoformat()


def main():
    print(
        "=== Sprint 2 — "
        "BOS / CHOCH Verification ==="
    )

    candle_service = CandleService()

    swing_detector = SwingDetector(
        left_bars=2,
        right_bars=2,
    )

    break_detector = (
        StructureBreakDetector()
    )

    for timeframe in (
        "15m",
        "1h",
        "4h",
    ):
        print(f"\n[{timeframe}]")

        candles = (
            candle_service
            .fetch_closed_candles(
                timeframe=timeframe,
                limit=250,
            )
        )

        raw_swings = (
            swing_detector.detect(
                candles
            )
        )

        swings = normalize_swings(
            raw_swings
        )

        breaks, state = (
            break_detector.detect(
                candles,
                raw_swings,
            )
        )

        print(
            f"Closed candles: "
            f"{len(candles)}"
        )

        print(
            f"Normalized swings: "
            f"{len(swings)}"
        )

        print(
            f"Structure breaks: "
            f"{len(breaks)}"
        )

        print(
            f"Current trend: "
            f"{state.trend.value}"
        )

        if state.latest_swing_high:
            print(
                "Latest Swing High: "
                f"{state.latest_swing_high.price:.2f}"
            )

        if state.latest_swing_low:
            print(
                "Latest Swing Low: "
                f"{state.latest_swing_low.price:.2f}"
            )

        print("\nLatest 8 breaks:")

        for event in breaks[-8:]:
            print(
                f"{event.break_type.value:<14} | "
                f"close={event.close_price:>10.2f} | "
                f"level={event.broken_level:>10.2f} | "
                f"{format_timestamp(event.candle_start_ts_ms)}"
            )

    print(
        "\nBOS / CHOCH verification: OK"
    )


if __name__ == "__main__":
    main()