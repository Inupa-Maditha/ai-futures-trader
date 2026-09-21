from time import sleep

from config.settings import SYMBOL

from market_data.liquidations import (
    LiquidationFlow,
)

from market_data.live_candles import (
    LiveCandleStore,
)

from market_data.orderbook import OrderBook

from market_data.public_ws import (
    BybitPublicWebSocket,
)

from market_data.recorder import (
    JsonlMarketDataRecorder,
)

from market_data.trades import TradeFlow


def count_lines(path) -> int:
    if not path.exists():
        return 0

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return sum(1 for _ in file)


def main():
    print(
        "=== Sprint 1 — Raw Data Recording Verification ==="
    )

    recorder = JsonlMarketDataRecorder()

    orderbook = OrderBook(
        symbol=SYMBOL,
        depth=50,
    )

    trades = TradeFlow(
        symbol=SYMBOL,
        window_seconds=60,
    )

    liquidations = LiquidationFlow(
        symbol=SYMBOL,
        window_seconds=60,
    )

    candles = LiveCandleStore(
        symbol=SYMBOL,
    )

    ws = BybitPublicWebSocket(
        recorder=recorder,
    )

    print("\nStarting public streams...")

    ws.subscribe_orderbook(orderbook)
    ws.subscribe_trades(trades)
    ws.subscribe_liquidations(
        liquidations
    )
    ws.subscribe_klines(candles)

    print(
        "Recording raw market data "
        "for 5 seconds..."
    )

    sleep(5)

    recorder.close()

    print("\nRecorded files:")

    sources = [
        "orderbook",
        "public_trades",
        "kline_15m",
        "kline_1h",
        "kline_4h",
        "liquidations",
    ]

    for source in sources:
        path = recorder.get_file_path(
            source
        )

        lines = count_lines(path)

        print(
            f"{source:<22} "
            f"{lines:>6} lines"
        )

        if path.exists():
            print(
                f"  -> {path}"
            )

    required_sources = [
        "orderbook",
        "public_trades",
        "kline_15m",
        "kline_1h",
        "kline_4h",
    ]

    for source in required_sources:
        path = recorder.get_file_path(
            source
        )

        if count_lines(path) == 0:
            raise RuntimeError(
                f"No raw data recorded "
                f"for {source}."
            )

    print(
        "\nRaw market-data recording: OK"
    )


if __name__ == "__main__":
    main()