from datetime import datetime, timezone

from market_data.candles import CandleService


def format_timestamp(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc,
    ).isoformat()


def main():
    print(
        "=== Sprint 1 — Historical Candle Verification ==="
    )

    service = CandleService()

    for timeframe in ["15m", "1h", "4h"]:

        print(f"\n[{timeframe}] Fetching candles...")

        candles = service.fetch_closed_candles(
            timeframe=timeframe,
            limit=10,
        )

        print(f"Closed candles received: {len(candles)}")

        if not candles:
            print("ERROR: No closed candles returned.")
            continue

        latest = candles[-1]

        print(f"Symbol: {latest.symbol}")
        print(f"Timeframe: {latest.timeframe}")

        print(
            "Start:",
            format_timestamp(latest.start_ts_ms),
        )

        print(
            "End:",
            format_timestamp(latest.end_ts_ms),
        )

        print(f"Open: {latest.open}")
        print(f"High: {latest.high}")
        print(f"Low: {latest.low}")
        print(f"Close: {latest.close}")
        print(f"Volume: {latest.volume}")

        print(f"Confirmed: {latest.confirmed}")

    print("\nCandle verification complete.")


if __name__ == "__main__":
    main()