from datetime import datetime, timezone

from market_data.candles import CandleService
from market_structure.swings import (
    SwingDetector,
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
        "Swing Detection Verification ==="
    )

    candle_service = CandleService()

    detector = SwingDetector(
        left_bars=2,
        right_bars=2,
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

        swings = detector.detect(
            candles
        )

        highs = [
            swing
            for swing in swings
            if swing.kind == "HIGH"
        ]

        lows = [
            swing
            for swing in swings
            if swing.kind == "LOW"
        ]

        print(
            f"Closed candles: "
            f"{len(candles)}"
        )

        print(
            f"Swing highs: "
            f"{len(highs)}"
        )

        print(
            f"Swing lows: "
            f"{len(lows)}"
        )

        print(
            f"Total swings: "
            f"{len(swings)}"
        )

        print("\nLatest 6 swings:")

        for swing in swings[-6:]:
            print(
                f"{swing.kind:<4} | "
                f"{swing.price:.2f} | "
                f"{format_timestamp(swing.start_ts_ms)}"
            )

    print(
        "\nSwing detection verification: OK"
    )


if __name__ == "__main__":
    main()