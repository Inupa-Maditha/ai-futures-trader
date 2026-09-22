from config.settings import (
    BYBIT_DEMO_API_KEY,
    BYBIT_DEMO_API_SECRET,
    SYMBOL,
    validate_bybit_demo_settings,
)

from account_data.bybit_demo import (
    BybitDemoAccountClient,
)


def main():
    print(
        "=== Bybit Demo "
        "Account Verification ==="
    )

    validate_bybit_demo_settings()

    client = BybitDemoAccountClient(
        api_key=BYBIT_DEMO_API_KEY,
        api_secret=(
            BYBIT_DEMO_API_SECRET
        ),
    )

    snapshot = client.get_snapshot(
        SYMBOL
    )

    print(
        f"Equity: "
        f"{snapshot.account_equity}"
    )

    print(
        f"Available Balance: "
        f"{snapshot.available_balance}"
    )

    print(
        f"Open BTCUSDT Positions: "
        f"{snapshot.open_position_count}"
    )

    if not snapshot.positions:
        print(
            "Positions: none returned"
        )

    for index, position in enumerate(
        snapshot.positions,
        start=1,
    ):
        print(
            f"\nPosition {index}:"
        )

        print(
            f"  Symbol: "
            f"{position.symbol}"
        )

        print(
            f"  Side: "
            f"{position.side}"
        )

        print(
            f"  Size: "
            f"{position.size}"
        )

        print(
            f"  Avg Price: "
            f"{position.avg_price}"
        )

        print(
            f"  Leverage: "
            f"{position.leverage}"
        )

        print(
            f"  Unrealised PnL: "
            f"{position.unrealised_pnl}"
        )


if __name__ == "__main__":
    main()