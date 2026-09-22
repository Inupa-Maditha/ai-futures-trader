from datetime import datetime, timezone

from indicators.technical import (
    TechnicalIndicatorEngine,
)

from market_data.candles import CandleService


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
        "Technical Indicator Verification ==="
    )

    candle_service = CandleService()

    engine = TechnicalIndicatorEngine()

    for timeframe in (
        "15m",
        "1h",
        "4h",
    ):
        print(
            f"\n[{timeframe}]"
        )

        candles = (
            candle_service
            .fetch_closed_candles(
                timeframe=timeframe,
                limit=250,
            )
        )

        print(
            f"Closed candles: "
            f"{len(candles)}"
        )

        snapshot = engine.calculate(
            candles
        )

        print(
            "Latest candle:",
            format_timestamp(
                snapshot.candle_start_ts_ms
            ),
        )

        print(
            f"Close: {snapshot.close:.2f}"
        )

        print(
            f"EMA 20: "
            f"{snapshot.ema_20:.2f}"
        )

        print(
            f"EMA 50: "
            f"{snapshot.ema_50:.2f}"
        )

        print(
            f"EMA 200: "
            f"{snapshot.ema_200:.2f}"
        )

        print(
            f"RSI 14: "
            f"{snapshot.rsi_14:.2f}"
        )

        print(
            f"ATR 14: "
            f"{snapshot.atr_14:.2f}"
        )

        print(
            f"ATR %: "
            f"{snapshot.atr_percent:.4f}%"
        )

    print(
        "\nTechnical indicator "
        "verification: OK"
    )


if __name__ == "__main__":
    main()