from time import sleep

from config.settings import SYMBOL
from market_data.live_candles import LiveCandleStore
from market_data.public_ws import BybitPublicWebSocket


def verify_parser():
    print("[1] Testing live candle parser...")

    store = LiveCandleStore(SYMBOL)

    forming_message = {
        "topic": f"kline.15.{SYMBOL}",
        "type": "snapshot",
        "ts": 1000000,
        "data": [
            {
                "start": 900000,
                "end": 1799999,
                "interval": "15",
                "open": "85000",
                "high": "85200",
                "low": "84900",
                "close": "85100",
                "volume": "10.5",
                "turnover": "893550",
                "confirm": False,
                "timestamp": 999900,
            }
        ],
    }

    store.process_message(forming_message)

    assert store.current_forming("15m") is not None
    assert store.closed_count_for("15m") == 0

    closed_message = {
        "topic": f"kline.15.{SYMBOL}",
        "type": "snapshot",
        "ts": 1800000,
        "data": [
            {
                "start": 900000,
                "end": 1799999,
                "interval": "15",
                "open": "85000",
                "high": "85300",
                "low": "84900",
                "close": "85250",
                "volume": "12.5",
                "turnover": "1065625",
                "confirm": True,
                "timestamp": 1799999,
            }
        ],
    }

    store.process_message(closed_message)

    assert store.current_forming("15m") is None
    assert store.closed_count_for("15m") == 1

    latest = store.latest_closed("15m")

    assert latest is not None
    assert latest.confirmed is True
    assert latest.close == 85250

    print("Live candle parser: OK")


def verify_live_stream():
    print(
        "\n[2] Connecting to Bybit live Kline streams..."
    )

    store = LiveCandleStore(SYMBOL)
    ws = BybitPublicWebSocket()

    ws.subscribe_klines(store)

    print(
        "Listening to 15m / 1h / 4h Klines "
        "for 10 seconds..."
    )

    sleep(10)

    print()

    print(f"Messages received: {store.message_count}")

    for timeframe in ["15m", "1h", "4h"]:
        forming = store.current_forming(timeframe)

        print(f"\n[{timeframe}]")

        if forming is None:
            print("No forming candle received yet.")
        else:
            print(f"Open: {forming.open}")
            print(f"High: {forming.high}")
            print(f"Low: {forming.low}")
            print(f"Close: {forming.close}")
            print(f"Volume: {forming.volume}")
            print(f"Confirmed: {forming.confirmed}")

        print(
            f"Closed candles received live: "
            f"{store.closed_count_for(timeframe)}"
        )

    if store.message_count == 0:
        raise RuntimeError(
            "No live Kline messages were received."
        )

    print("\nLive Kline verification: OK")


def main():
    print(
        "=== Sprint 1 — Live Kline Verification ==="
    )

    verify_parser()
    verify_live_stream()


if __name__ == "__main__":
    main()