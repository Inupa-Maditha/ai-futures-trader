from __future__ import annotations

from decimal import Decimal

from pybit.unified_trading import HTTP

from config.settings import (
    BYBIT_DEMO_API_KEY,
    BYBIT_DEMO_API_SECRET,
    SYMBOL,
    validate_bybit_demo_settings,
)

from execution.order_repository import (
    BybitDemoOrderRepository,
)

from execution.preflight import (
    DemoExecutionPreflight,
)

from execution.schema import (
    DemoExecutionRequest,
    ExecutionSide,
)


def build_read_only_probe(
    symbol: str,
) -> DemoExecutionRequest:
    """
    This request is NEVER submitted.

    It only supplies the symbol and a valid
    request shape to the read-only preflight
    validator.
    """

    return DemoExecutionRequest(
        approval_id=(
            "readonly-preflight-check"
        ),

        order_link_id=(
            "aft-v1-readonly-preflight"
        ),

        symbol=symbol,

        side=ExecutionSide.BUY,

        quantity=Decimal("0.001"),

        entry_price=Decimal("100"),

        stop_loss=Decimal("90"),

        take_profit=Decimal("120"),

        leverage=Decimal("1"),
    )


def main():
    print(
        "=== Sprint 5 — "
        "Live Demo Execution Preflight ==="
    )

    print(
        "\nREAD-ONLY CHECK."
    )

    print(
        "NO ORDER WILL BE SUBMITTED."
    )

    validate_bybit_demo_settings()

    session = HTTP(
        testnet=False,
        demo=True,
        api_key=BYBIT_DEMO_API_KEY,
        api_secret=(
            BYBIT_DEMO_API_SECRET
        ),
    )

    repository = (
        BybitDemoOrderRepository(
            session=session
        )
    )

    preflight = DemoExecutionPreflight(
        session=session,
        order_repository=repository,
    )

    # ---------------------------------------------
    # 1. Read current positions
    # ---------------------------------------------

    print(
        "\n=== POSITION STATE ==="
    )

    position_response = (
        session.get_positions(
            category="linear",
            symbol=SYMBOL,
        )
    )

    if (
        position_response.get(
            "retCode"
        )
        != 0
    ):
        raise RuntimeError(
            "Unable to read Demo "
            "position state: "
            f"{position_response}"
        )

    positions = (
        position_response
        .get("result", {})
        .get("list", [])
    )

    if not positions:
        print(
            "No position rows returned."
        )

    for index, position in enumerate(
        positions,
        start=1,
    ):
        print(
            f"Position Row {index}:"
        )

        print(
            f"  Symbol: "
            f"{position.get('symbol')}"
        )

        print(
            f"  PositionIdx: "
            f"{position.get('positionIdx')}"
        )

        print(
            f"  Side: "
            f"{position.get('side')!r}"
        )

        print(
            f"  Size: "
            f"{position.get('size')}"
        )

    # ---------------------------------------------
    # 2. Read active orders
    # ---------------------------------------------

    print(
        "\n=== ACTIVE ORDERS ==="
    )

    active_orders = (
        repository.list_active_orders(
            symbol=SYMBOL
        )
    )

    print(
        f"Active Order Count: "
        f"{len(active_orders)}"
    )

    for order in active_orders:
        print(
            f"- {order.order_id}"
            f" | "
            f"{order.side}"
            f" | "
            f"{order.quantity}"
            f" | "
            f"{order.order_status}"
            f" | reduceOnly="
            f"{order.reduce_only}"
            f" | linkId="
            f"{order.order_link_id}"
        )

    # ---------------------------------------------
    # 3. Verify exact orderLinkId lookup
    #
    # This ID belongs only to the read-only
    # probe and should normally not exist.
    # ---------------------------------------------

    probe = build_read_only_probe(
        SYMBOL
    )

    print(
        "\n=== IDEMPOTENCY LOOKUP ==="
    )

    existing = (
        repository.find_by_link_id(
            symbol=SYMBOL,
            order_link_id=(
                probe.order_link_id
            ),
        )
    )

    if existing is None:
        print(
            "Probe orderLinkId: "
            "NOT FOUND"
        )

    else:
        print(
            "Probe orderLinkId already "
            "exists:"
        )

        print(
            f"  Order ID: "
            f"{existing.order_id}"
        )

        print(
            f"  Status: "
            f"{existing.order_status}"
        )

    # ---------------------------------------------
    # 4. Final live preflight
    # ---------------------------------------------

    print(
        "\n=== EXECUTION PREFLIGHT ==="
    )

    try:
        preflight.validate(
            probe
        )

    except RuntimeError as exc:
        print(
            "Status: BLOCKED"
        )

        print(
            f"Reason: {exc}"
        )

        print(
            "\nNO ORDER WAS SUBMITTED."
        )

        return

    print(
        "Status: READY"
    )

    print(
        "One-Way mode verified."
    )

    print(
        "No conflicting open position "
        "detected."
    )

    print(
        "No conflicting active entry "
        "order detected."
    )

    print(
        "\nDemo account is ready for "
        "a controlled execution test."
    )

    print(
        "\nNO ORDER WAS SUBMITTED."
    )


if __name__ == "__main__":
    main()