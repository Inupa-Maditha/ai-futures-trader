from time import sleep

from config.settings import SYMBOL
from data_quality.freshness import (
    build_default_health_monitor,
)
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
from market_data.trades import TradeFlow


def main():
    print(
        "=== Sprint 1 — Live Health Integration ==="
    )

    monitor = build_default_health_monitor()

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
        health_monitor=monitor,
    )

    print("\nSubscribing to live streams...")

    ws.subscribe_orderbook(orderbook)
    ws.subscribe_trades(trades)
    ws.subscribe_liquidations(
        liquidations
    )
    ws.subscribe_klines(candles)

    print(
        "Collecting live data for 10 seconds..."
    )

    sleep(10)

    print("\nHealth Summary:")

    summary = monitor.summary()

    for name, status in summary.items():
        print(
            f"{name:<22} {status}"
        )

    print()

    critical_sources = [
        "orderbook",
        "public_trades",
        "kline_15m",
        "kline_1h",
        "kline_4h",
    ]

    critical_ok = monitor.critical_ok(
        critical_sources
    )

    print(
        f"Critical live sources healthy: "
        f"{critical_ok}"
    )

    print()
    print(
        f"Order-book messages: "
        f"{orderbook.message_count}"
    )

    print(
        f"Public trades: "
        f"{trades.total_trade_count}"
    )

    print(
        f"Kline messages: "
        f"{candles.message_count}"
    )

    print(
        f"Liquidation events: "
        f"{liquidations.total_event_count}"
    )

    if not critical_ok:
        raise RuntimeError(
            "One or more critical live "
            "data sources are unhealthy."
        )

    print(
        "\nLive health integration: OK"
    )


if __name__ == "__main__":
    main()