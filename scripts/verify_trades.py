from datetime import datetime, timezone
from time import sleep

from config.settings import SYMBOL
from market_data.public_ws import BybitPublicWebSocket
from market_data.trades import TradeFlow


def format_timestamp(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc,
    ).isoformat()


def main():
    print(
        "=== Sprint 1 — Public Trade Verification ==="
    )

    trade_flow = TradeFlow(
        symbol=SYMBOL,
        window_seconds=60,
    )

    ws = BybitPublicWebSocket()

    print(
        "Connecting to Bybit public WebSocket..."
    )

    ws.subscribe_trades(trade_flow)

    print(
        "Collecting public trades for 5 seconds..."
    )

    sleep(5)

    if not trade_flow.is_ready():
        raise RuntimeError(
            "No public trades were received."
        )

    latest = trade_flow.latest_trade()

    buy_volume = (
        trade_flow.aggressive_buy_volume()
    )

    sell_volume = (
        trade_flow.aggressive_sell_volume()
    )

    imbalance = (
        trade_flow.signed_volume_imbalance()
    )

    print()

    print(f"Symbol: {SYMBOL}")

    print(
        f"Messages received: "
        f"{trade_flow.message_count}"
    )

    print(
        f"Total unique trades received: "
        f"{trade_flow.total_trade_count}"
    )

    print(
        f"Duplicate trades ignored: "
        f"{trade_flow.duplicate_count}"
    )

    print(
        f"Trades currently in 60s window: "
        f"{trade_flow.recent_trade_count()}"
    )

    print()

    print(
        f"Aggressive Buy Volume: {buy_volume} BTC"
    )

    print(
        f"Aggressive Sell Volume: {sell_volume} BTC"
    )

    print(
        f"Signed Volume Imbalance: {imbalance}"
    )

    print()

    print(f"Latest Price: {latest.price}")
    print(f"Latest Quantity: {latest.quantity}")
    print(f"Latest Taker Side: {latest.side}")

    print(
        f"Latest Trade ID: {latest.trade_id}"
    )

    print(
        f"Sequence: {latest.sequence}"
    )

    print(
        "Exchange Trade Time:",
        format_timestamp(
            latest.exchange_event_ts_ms
        ),
    )

    print(
        f"Local Receive Time: "
        f"{latest.local_receive_ts_utc}"
    )

    print(
        "\nPublic trade verification: OK"
    )


if __name__ == "__main__":
    main()