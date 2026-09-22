from config.settings import (
    BYBIT_DEMO_API_KEY,
    BYBIT_DEMO_API_SECRET,
    SYMBOL,
    validate_bybit_demo_settings,
)

from account_data.bybit_demo import (
    BybitDemoAccountClient,
)

from account_data.closed_pnl import (
    BybitDemoClosedPnlClient,
)

from risk_manager.account_state_provider import (
    DemoRiskStateProvider,
)


def main():
    print(
        "=== Bybit Demo "
        "Risk State Verification ==="
    )

    validate_bybit_demo_settings()

    account_client = (
        BybitDemoAccountClient(
            api_key=(
                BYBIT_DEMO_API_KEY
            ),
            api_secret=(
                BYBIT_DEMO_API_SECRET
            ),
        )
    )

    pnl_client = (
        BybitDemoClosedPnlClient(
            api_key=(
                BYBIT_DEMO_API_KEY
            ),
            api_secret=(
                BYBIT_DEMO_API_SECRET
            ),
        )
    )

    provider = DemoRiskStateProvider(
        account_client=(
            account_client
        ),

        closed_pnl_client=(
            pnl_client
        ),
    )

    state = provider.get_state(
        SYMBOL
    )

    print(
        f"Symbol: {SYMBOL}"
    )

    print(
        f"Account Equity: "
        f"{state.account_equity}"
    )

    print(
        f"Available Balance: "
        f"{state.available_balance}"
    )

    print(
        f"Open Positions: "
        f"{state.open_position_count}"
    )

    print(
        f"Today's Realized PnL "
        f"(UTC): "
        f"{state.daily_realized_pnl}"
    )


if __name__ == "__main__":
    main()