from config.settings import SYMBOL

from risk_manager.instrument_rules import (
    BybitInstrumentRulesClient,
)


def main():
    print(
        "=== Bybit Instrument Rules ==="
    )

    client = (
        BybitInstrumentRulesClient()
    )

    rules = (
        client.get_linear_rules(
            SYMBOL
        )
    )

    print(
        f"Symbol: {rules.symbol}"
    )

    print(
        f"Status: {rules.status}"
    )

    print(
        f"Contract: "
        f"{rules.contract_type}"
    )

    print(
        f"Tick Size: "
        f"{rules.tick_size}"
    )

    print(
        f"Qty Step: "
        f"{rules.qty_step}"
    )

    print(
        f"Min Qty: "
        f"{rules.min_order_qty}"
    )

    print(
        f"Max Limit Qty: "
        f"{rules.max_order_qty}"
    )

    print(
        f"Max Market Qty: "
        f"{rules.max_market_order_qty}"
    )

    print(
        f"Min Notional: "
        f"{rules.min_notional_value}"
    )

    print(
        f"Leverage: "
        f"{rules.min_leverage}"
        f" -> "
        f"{rules.max_leverage}"
    )

    print(
        f"Leverage Step: "
        f"{rules.leverage_step}"
    )


if __name__ == "__main__":
    main()