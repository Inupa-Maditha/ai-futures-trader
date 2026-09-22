from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from time import sleep
from uuid import uuid4

from pybit.unified_trading import HTTP

from config.settings import (
    BYBIT_DEMO_API_KEY,
    BYBIT_DEMO_API_SECRET,
    SYMBOL,
    validate_bybit_demo_settings,
    validate_demo_execution_enabled,
)

from execution.order_repository import (
    BybitDemoOrderRepository,
)


def floor_to_step(
    value: Decimal,
    step: Decimal,
) -> Decimal:
    if value <= 0:
        raise ValueError(
            "value must be greater than zero."
        )

    if step <= 0:
        raise ValueError(
            "step must be greater than zero."
        )

    units = (
        value / step
    ).to_integral_value(
        rounding=ROUND_DOWN
    )

    return units * step


def get_market_and_rules():
    session = HTTP(
        testnet=False
    )

    ticker_response = session.get_tickers(
        category="linear",
        symbol=SYMBOL,
    )

    if ticker_response.get("retCode") != 0:
        raise RuntimeError(
            f"Ticker request failed: "
            f"{ticker_response}"
        )

    ticker_list = (
        ticker_response
        .get("result", {})
        .get("list", [])
    )

    if len(ticker_list) != 1:
        raise RuntimeError(
            "Expected exactly one ticker."
        )

    ticker = ticker_list[0]

    if ticker.get("symbol") != SYMBOL:
        raise RuntimeError(
            "Unexpected ticker symbol."
        )

    last_price = Decimal(
        str(ticker["lastPrice"])
    )

    instrument_response = (
        session.get_instruments_info(
            category="linear",
            symbol=SYMBOL,
        )
    )

    if (
        instrument_response.get(
            "retCode"
        )
        != 0
    ):
        raise RuntimeError(
            "Instrument-info request "
            f"failed: {instrument_response}"
        )

    instruments = (
        instrument_response
        .get("result", {})
        .get("list", [])
    )

    if len(instruments) != 1:
        raise RuntimeError(
            "Expected exactly one "
            "instrument record."
        )

    instrument = instruments[0]

    if instrument.get("symbol") != SYMBOL:
        raise RuntimeError(
            "Unexpected instrument symbol."
        )

    price_filter = instrument[
        "priceFilter"
    ]

    lot_filter = instrument[
        "lotSizeFilter"
    ]

    tick_size = Decimal(
        str(price_filter["tickSize"])
    )

    qty_step = Decimal(
        str(lot_filter["qtyStep"])
    )

    min_qty = Decimal(
        str(lot_filter["minOrderQty"])
    )

    return (
        last_price,
        tick_size,
        qty_step,
        min_qty,
    )


def get_exact_raw_order(
    session,
    order_link_id: str,
) -> dict | None:
    response = session.get_open_orders(
        category="linear",
        symbol=SYMBOL,
        orderLinkId=order_link_id,
        limit=1,
    )

    if response.get("retCode") != 0:
        raise RuntimeError(
            "Open-order query failed: "
            f"{response}"
        )

    records = (
        response
        .get("result", {})
        .get("list", [])
    )

    if not records:
        return None

    if len(records) != 1:
        raise RuntimeError(
            "Expected exactly one "
            "matching order."
        )

    record = records[0]

    if (
        record.get("orderLinkId")
        != order_link_id
    ):
        raise RuntimeError(
            "Unexpected orderLinkId "
            "returned."
        )

    if record.get("symbol") != SYMBOL:
        raise RuntimeError(
            "Unexpected order symbol."
        )

    return record


def confirm_cancelled(
    repository:
    BybitDemoOrderRepository,

    order_link_id: str,
) -> str:
    last_status = "UNKNOWN"

    for _ in range(10):
        order = (
            repository.find_by_link_id(
                symbol=SYMBOL,
                order_link_id=(
                    order_link_id
                ),
            )
        )

        if order is not None:
            last_status = (
                order.order_status
            )

            if (
                last_status
                == "Cancelled"
            ):
                return last_status

            if (
                last_status
                == "Filled"
            ):
                return last_status

        sleep(0.5)

    return last_status


def main():
    print(
        "=== Bybit Demo "
        "Order Lifecycle Verification ==="
    )

    print(
        "\nTEST-ONLY DEMO ORDER."
    )

    print(
        "NO REAL-MONEY ORDER "
        "CAN BE PLACED."
    )

    validate_bybit_demo_settings()
    validate_demo_execution_enabled()

    print(
        "\nFetching live BTCUSDT "
        "market information..."
    )

    (
        last_price,
        tick_size,
        qty_step,
        min_qty,
    ) = get_market_and_rules()

    quantity = floor_to_step(
        min_qty,
        qty_step,
    )

    # Buy limit 1% below current price.
    #
    # Combined with PostOnly this is intended
    # to remain resting rather than immediately
    # becoming a taker order.
    entry_price = floor_to_step(
        last_price * Decimal("0.99"),
        tick_size,
    )

    stop_loss = floor_to_step(
        entry_price * Decimal("0.99"),
        tick_size,
    )

    take_profit = floor_to_step(
        entry_price * Decimal("1.02"),
        tick_size,
    )

    order_link_id = (
        "aft-demo-"
        + uuid4().hex[:20]
    )

    print(
        "\n=== TEST ORDER PLAN ==="
    )

    print(
        f"Last Price: {last_price}"
    )

    print(
        f"Quantity: {quantity} BTC"
    )

    print(
        f"Entry: {entry_price}"
    )

    print(
        f"Stop Loss: {stop_loss}"
    )

    print(
        f"Take Profit: {take_profit}"
    )

    print(
        f"OrderLinkId: {order_link_id}"
    )

    print(
        "\nThis is an isolated "
        "Bybit Demo API test."
    )

    print(
        "Type exactly:"
    )

    print(
        "EXECUTE DEMO TEST"
    )

    confirmation = input(
        "> "
    ).strip()

    if (
        confirmation
        != "EXECUTE DEMO TEST"
    ):
        print(
            "\nTEST CANCELLED."
        )

        print(
            "No order submitted."
        )

        return

    demo_session = HTTP(
        testnet=False,
        demo=True,
        api_key=BYBIT_DEMO_API_KEY,
        api_secret=(
            BYBIT_DEMO_API_SECRET
        ),
    )

    repository = (
        BybitDemoOrderRepository(
            session=demo_session
        )
    )

    # -----------------------------------------
    # Read-only safety checks
    # -----------------------------------------

    positions_response = (
        demo_session.get_positions(
            category="linear",
            symbol=SYMBOL,
        )
    )

    if (
        positions_response.get(
            "retCode"
        )
        != 0
    ):
        raise RuntimeError(
            "Unable to verify "
            "Demo positions."
        )

    positions = (
        positions_response
        .get("result", {})
        .get("list", [])
    )

    if not positions:
        raise RuntimeError(
            "Unable to verify "
            "position mode."
        )

    for position in positions:
        if (
            int(
                position["positionIdx"]
            )
            != 0
        ):
            raise RuntimeError(
                "Demo test requires "
                "One-Way mode."
            )

        size = Decimal(
            str(
                position.get(
                    "size",
                    "0",
                )
            )
        )

        if size > 0:
            raise RuntimeError(
                "Existing BTCUSDT "
                "position detected. "
                "Demo test blocked."
            )

    active_orders = (
        repository.list_active_orders(
            symbol=SYMBOL
        )
    )

    conflicts = [
        order
        for order in active_orders
        if not order.reduce_only
    ]

    if conflicts:
        raise RuntimeError(
            "Existing active entry "
            "order detected. "
            "Demo test blocked."
        )

    print(
        "\nSafety checks passed."
    )

    # -----------------------------------------
    # Place isolated Demo order
    # -----------------------------------------

    print(
        "\nSubmitting PostOnly "
        "Demo order..."
    )

    response = (
        demo_session.place_order(
            category="linear",
            symbol=SYMBOL,
            side="Buy",
            orderType="Limit",
            qty=str(quantity),
            price=str(entry_price),
            timeInForce="PostOnly",
            positionIdx=0,
            reduceOnly=False,
            orderLinkId=order_link_id,
            takeProfit=str(
                take_profit
            ),
            stopLoss=str(
                stop_loss
            ),
            tpslMode="Full",
            tpOrderType="Market",
            slOrderType="Market",
            tpTriggerBy="MarkPrice",
            slTriggerBy="MarkPrice",
        )
    )

    if response.get("retCode") != 0:
        raise RuntimeError(
            "Demo order submission "
            f"failed: {response}"
        )

    result = response.get(
        "result",
        {},
    )

    order_id = result.get(
        "orderId"
    )

    returned_link_id = result.get(
        "orderLinkId"
    )

    if not order_id:
        raise RuntimeError(
            "No orderId returned."
        )

    if (
        returned_link_id
        != order_link_id
    ):
        raise RuntimeError(
            "Returned orderLinkId "
            "does not match."
        )

    print(
        "\nOrder ACK received."
    )

    print(
        f"Order ID: {order_id}"
    )

    # -----------------------------------------
    # Wait for exchange-side visibility
    # -----------------------------------------

    raw_order = None

    for _ in range(10):
        raw_order = (
            get_exact_raw_order(
                demo_session,
                order_link_id,
            )
        )

        if raw_order is not None:
            break

        sleep(0.5)

    if raw_order is None:
        raise RuntimeError(
            "Order was acknowledged "
            "but could not be found."
        )

    status = raw_order.get(
        "orderStatus"
    )

    print(
        "\n=== EXCHANGE ORDER ==="
    )

    print(
        f"Status: {status}"
    )

    print(
        f"Exchange TP: "
        f"{raw_order.get('takeProfit')}"
    )

    print(
        f"Exchange SL: "
        f"{raw_order.get('stopLoss')}"
    )

    print(
        f"TP/SL Mode: "
        f"{raw_order.get('tpslMode')}"
    )

    exchange_tp = Decimal(
        str(
            raw_order[
                "takeProfit"
            ]
        )
    )

    exchange_sl = Decimal(
        str(
            raw_order[
                "stopLoss"
            ]
        )
    )

    if exchange_tp != take_profit:
        raise RuntimeError(
            "Exchange take-profit "
            "does not match the "
            "submitted value."
        )

    if exchange_sl != stop_loss:
        raise RuntimeError(
            "Exchange stop-loss "
            "does not match the "
            "submitted value."
        )

    if (
        raw_order.get("tpslMode")
        != "Full"
    ):
        raise RuntimeError(
            "Unexpected TP/SL mode."
        )

    print(
        "\nExchange-side TP/SL "
        "verification: PASSED"
    )

    # -----------------------------------------
    # Cancel test order immediately
    # -----------------------------------------

    if status == "Filled":
        print(
            "\nWARNING:"
        )

        print(
            "The Demo order filled "
            "before cancellation."
        )

        print(
            "Cancellation skipped."
        )

        print(
            "Check the Demo position "
            "manually."
        )

        return

    print(
        "\nCancelling Demo "
        "test order..."
    )

    cancel_response = (
        demo_session.cancel_order(
            category="linear",
            symbol=SYMBOL,
            orderLinkId=(
                order_link_id
            ),
        )
    )

    if (
        cancel_response.get(
            "retCode"
        )
        != 0
    ):
        raise RuntimeError(
            "Cancel request failed: "
            f"{cancel_response}"
        )

    final_status = confirm_cancelled(
        repository,
        order_link_id,
    )

    print(
        "\n=== FINAL RESULT ==="
    )

    print(
        f"Final Order Status: "
        f"{final_status}"
    )

    if final_status != "Cancelled":
        raise RuntimeError(
            "Demo order cancellation "
            "was not confirmed."
        )

    print(
        "Order creation: PASSED"
    )

    print(
        "Exchange TP/SL: PASSED"
    )

    print(
        "Order reconciliation: PASSED"
    )

    print(
        "Order cancellation: PASSED"
    )

    print(
        "\nDEMO ORDER LIFECYCLE "
        "VERIFICATION COMPLETE."
    )


if __name__ == "__main__":
    main()