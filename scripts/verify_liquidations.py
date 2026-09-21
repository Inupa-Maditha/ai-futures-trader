from datetime import datetime, timezone
from decimal import Decimal
from time import sleep

from config.settings import SYMBOL
from market_data.liquidations import LiquidationFlow
from market_data.public_ws import BybitPublicWebSocket


def format_timestamp(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc,
    ).isoformat()


def verify_parser():
    print("[1] Testing liquidation parser...")

    flow = LiquidationFlow(
        symbol=SYMBOL,
        window_seconds=60,
    )

    sample_message = {
        "topic": f"allLiquidation.{SYMBOL}",
        "type": "snapshot",
        "ts": 1000000,
        "data": [
            {
                "T": 999900,
                "s": SYMBOL,
                "S": "Buy",
                "v": "0.250",
                "p": "85000",
            },
            {
                "T": 999950,
                "s": SYMBOL,
                "S": "Sell",
                "v": "0.400",
                "p": "85100",
            },
        ],
    }

    flow.process_message(sample_message)

    assert flow.long_liquidation_volume() == Decimal("0.250")
    assert flow.short_liquidation_volume() == Decimal("0.400")
    assert flow.total_liquidation_volume() == Decimal("0.650")

    print("Liquidation parser: OK")


def verify_live_stream():
    print(
        "\n[2] Connecting to Bybit "
        "All Liquidation stream..."
    )

    flow = LiquidationFlow(
        symbol=SYMBOL,
        window_seconds=60,
    )

    ws = BybitPublicWebSocket()

    ws.subscribe_liquidations(flow)

    print(
        "Listening for liquidation events "
        "for 10 seconds..."
    )

    sleep(10)

    print()

    print(f"Symbol: {SYMBOL}")
    print(f"Messages received: {flow.message_count}")
    print(
        f"Liquidation events received: "
        f"{flow.total_event_count}"
    )

    print(
        f"Long liquidation volume: "
        f"{flow.long_liquidation_volume()} BTC"
    )

    print(
        f"Short liquidation volume: "
        f"{flow.short_liquidation_volume()} BTC"
    )

    print(
        f"Total liquidation volume: "
        f"{flow.total_liquidation_volume()} BTC"
    )

    latest = flow.latest_event()

    if latest is None:
        print(
            "\nNo BTCUSDT liquidation occurred "
            "during this observation window."
        )
        print(
            "This is not an error; "
            "the live subscription was started."
        )

    else:
        print()
        print(
            f"Latest position side: "
            f"{latest.position_side}"
        )
        print(
            f"Latest quantity: "
            f"{latest.quantity}"
        )
        print(
            f"Latest bankruptcy price: "
            f"{latest.bankruptcy_price}"
        )
        print(
            "Latest event time:",
            format_timestamp(
                latest.exchange_event_ts_ms
            ),
        )
        print(
            f"Local receive time: "
            f"{latest.local_receive_ts_utc}"
        )

    print("\nLiquidation verification complete.")


def main():
    print(
        "=== Sprint 1 — Liquidation Verification ==="
    )

    verify_parser()
    verify_live_stream()


if __name__ == "__main__":
    main()