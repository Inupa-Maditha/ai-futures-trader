from __future__ import annotations

from decimal import Decimal

from execution.order_repository import (
    BybitDemoOrderRepository,
)

from execution.schema import (
    DemoExecutionRequest,
)


ZERO = Decimal("0")


class DemoExecutionPreflight:
    def __init__(
        self,
        session,
        order_repository:
        BybitDemoOrderRepository,
    ):
        self.session = session

        self.order_repository = (
            order_repository
        )

    def validate(
        self,
        request:
        DemoExecutionRequest,

        ignore_order_link_id:
        str | None = None,
    ) -> None:

        # -----------------------------------------
        # 1. Verify position mode AGAIN
        # -----------------------------------------

        self._validate_position_state(
            request.symbol
        )

        # -----------------------------------------
        # 2. Check for pending exposure
        #
        # Block another non-reduce-only order
        # from creating duplicate exposure.
        # -----------------------------------------

        active_orders = (
            self.order_repository
            .list_active_orders(
                symbol=request.symbol
            )
        )

        conflicts = []

        for order in active_orders:

            # Protective closing orders do not
            # count as new directional exposure.
            if order.reduce_only:
                continue

            # Used later by reconciliation path.
            if (
                ignore_order_link_id
                is not None
                and
                order.order_link_id
                == ignore_order_link_id
            ):
                continue

            conflicts.append(
                order
            )

        if conflicts:
            raise RuntimeError(
                "Execution blocked: "
                f"{len(conflicts)} active "
                "non-reduce-only order(s) "
                f"already exist for "
                f"{request.symbol}."
            )

    def _validate_position_state(
        self,
        symbol: str,
    ) -> None:

        response = (
            self.session
            .get_positions(
                category="linear",
                symbol=symbol,
            )
        )

        if response.get(
            "retCode"
        ) != 0:
            raise RuntimeError(
                "Bybit execution-preflight "
                "position request failed: "
                f"{response}"
            )

        positions = (
            response
            .get("result", {})
            .get("list", [])
        )

        if not positions:
            raise RuntimeError(
                "Execution blocked: "
                "unable to verify "
                "BTCUSDT position mode."
            )

        for position in positions:
            if (
                position.get("symbol")
                != symbol
            ):
                raise RuntimeError(
                    "Execution blocked: "
                    "unexpected position "
                    "symbol returned."
                )

            try:
                position_idx = int(
                    position[
                        "positionIdx"
                    ]
                )
            except Exception as exc:
                raise RuntimeError(
                    "Execution blocked: "
                    "invalid positionIdx."
                ) from exc

            # V1 explicitly requires
            # One-Way mode.
            if position_idx != 0:
                raise RuntimeError(
                    "Execution blocked: "
                    "BTCUSDT is not in "
                    "One-Way position mode."
                )

            try:
                size = Decimal(
                    str(
                        position.get(
                            "size",
                            "0",
                        )
                    )
                )
            except Exception as exc:
                raise RuntimeError(
                    "Execution blocked: "
                    "invalid position size."
                ) from exc

            # Important TOCTOU protection:
            #
            # The risk engine may have seen
            # zero positions earlier, but a
            # position could appear before
            # actual execution.
            if size > ZERO:
                raise RuntimeError(
                    "Execution blocked: "
                    "an open BTCUSDT "
                    "position appeared "
                    "before order submission."
                )