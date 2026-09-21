from time import sleep

from config.settings import SYMBOL
from market_data.orderbook import OrderBook
from market_data.public_ws import BybitPublicWebSocket


def main():
    print("=== Sprint 1 — Order Book Verification ===")

    orderbook = OrderBook(
        symbol=SYMBOL,
        depth=50,
    )

    ws = BybitPublicWebSocket()

    print("Connecting to Bybit public WebSocket...")

    ws.subscribe_orderbook(orderbook)

    print("Collecting L50 order-book data for 5 seconds...")

    sleep(5)

    print()

    if not orderbook.is_ready():
        raise RuntimeError(
            "Order book did not receive a valid snapshot."
        )

    bid = orderbook.best_bid()
    ask = orderbook.best_ask()
    spread = orderbook.spread()

    print(f"Symbol: {SYMBOL}")
    print(f"Snapshot received: {orderbook.has_snapshot}")
    print(f"Messages processed: {orderbook.message_count}")

    print(f"Update ID: {orderbook.update_id}")
    print(f"Sequence: {orderbook.sequence}")

    print(f"Best Bid: {bid}")
    print(f"Best Ask: {ask}")
    print(f"Spread: {spread}")

    print(f"Bid levels stored: {len(orderbook.get_bids())}")
    print(f"Ask levels stored: {len(orderbook.get_asks())}")

    print(
        f"Exchange timestamp: "
        f"{orderbook.exchange_ts_ms}"
    )

    print(
        f"Matching-engine timestamp: "
        f"{orderbook.matching_engine_ts_ms}"
    )

    print(
        f"Local receive time: "
        f"{orderbook.local_receive_ts_utc}"
    )

    print("\nOrder-book verification: OK")


if __name__ == "__main__":
    main()