from time import sleep

from config.settings import SYMBOL

from data_quality.freshness import (
    build_default_health_monitor,
)

from derivatives.bybit_derivatives import (
    BybitDerivativesService,
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
        "=== Sprint 1 — Unified Market Data Health ==="
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

    derivatives = BybitDerivativesService(
        health_monitor=monitor,
    )

    print("\n[1] Starting WebSocket sources...")

    ws.subscribe_orderbook(orderbook)
    ws.subscribe_trades(trades)
    ws.subscribe_liquidations(
        liquidations
    )
    ws.subscribe_klines(candles)

    print(
        "Collecting live WebSocket data..."
    )

    sleep(5)

    print("\n[2] Fetching REST derivatives...")

    oi = derivatives.get_open_interest(
        interval="15min"
    )

    funding = derivatives.get_funding()

    positioning = derivatives.get_positioning(
        period="15min"
    )

    print(
        f"Open Interest: {oi.current} BTC"
    )

    print(
        f"Current Funding Rate: "
        f"{funding.current_funding_rate}"
    )

    print(
        f"Long Account Ratio: "
        f"{positioning.account_holder_long_ratio}"
    )

    print(
        f"Short Account Ratio: "
        f"{positioning.account_holder_short_ratio}"
    )

    print("\n[3] Health Summary")

    summary = monitor.summary()

    for name, status in summary.items():
        print(
            f"{name:<22} {status}"
        )

    critical_sources = [
        "orderbook",
        "public_trades",
        "kline_15m",
        "kline_1h",
        "kline_4h",
        "liquidations",
        "open_interest",
        "funding",
        "account_positioning",
    ]

    critical_ok = monitor.critical_ok(
        critical_sources
    )

    print()

    print(
        f"All critical market data healthy: "
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
            "Critical market-data health "
            "check failed."
        )

    print(
        "\nUnified market-data health: OK"
    )


if __name__ == "__main__":
    main()