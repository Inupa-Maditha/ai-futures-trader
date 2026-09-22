from __future__ import annotations

from pybit.exceptions import (
    InvalidRequestError,
)

from pybit.unified_trading import HTTP

from execution.schema import (
    DemoExecutionAck,
    DemoExecutionRequest,
    ExecutionStatus,
)


LEVERAGE_NOT_MODIFIED_CODE = 110043


class BybitDemoExecutionClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        session=None,
    ):
        if not api_key:
            raise ValueError(
                "api_key is required."
            )

        if not api_secret:
            raise ValueError(
                "api_secret is required."
            )

        self.session = (
            session
            if session is not None
            else HTTP(
                testnet=False,
                demo=True,
                api_key=api_key,
                api_secret=api_secret,
            )
        )

    def submit(
        self,
        request: DemoExecutionRequest,
    ) -> DemoExecutionAck:

        leverage_changed = (
            self._set_leverage(
                request
            )
        )

        response = (
            self.session.place_order(
                category="linear",

                symbol=request.symbol,

                side=request.side.value,

                orderType="Limit",

                qty=str(
                    request.quantity
                ),

                price=str(
                    request.entry_price
                ),

                timeInForce="GTC",

                positionIdx=0,

                reduceOnly=False,

                orderLinkId=(
                    request.order_link_id
                ),

                takeProfit=str(
                    request.take_profit
                ),

                stopLoss=str(
                    request.stop_loss
                ),

                tpslMode="Full",

                tpOrderType="Market",

                slOrderType="Market",

                tpTriggerBy="MarkPrice",

                slTriggerBy="MarkPrice",
            )
        )

        self._validate_response(
            response=response,
            operation="place order",
        )

        result = response.get(
            "result",
            {},
        )

        order_id = result.get(
            "orderId"
        )

        returned_link_id = (
            result.get(
                "orderLinkId"
            )
        )

        if not order_id:
            raise RuntimeError(
                "Bybit place-order "
                "response did not contain "
                "orderId."
            )

        if (
            returned_link_id
            != request.order_link_id
        ):
            raise RuntimeError(
                "Bybit returned an "
                "unexpected orderLinkId."
            )

        return DemoExecutionAck(
            status=(
                ExecutionStatus
                .ACKNOWLEDGED
            ),

            approval_id=(
                request.approval_id
            ),

            order_id=order_id,

            order_link_id=(
                returned_link_id
            ),

            symbol=request.symbol,

            side=request.side,

            quantity=(
                request.quantity
            ),

            leverage=(
                request.leverage
            ),

            leverage_changed=(
                leverage_changed
            ),
        )

    def _set_leverage(
        self,
        request: DemoExecutionRequest,
    ) -> bool:

        leverage = str(
            request.leverage
        )

        try:
            response = (
                self.session
                .set_leverage(
                    category="linear",

                    symbol=(
                        request.symbol
                    ),

                    # V1 assumes one-way mode.
                    buyLeverage=leverage,
                    sellLeverage=leverage,
                )
            )

        except InvalidRequestError as exc:
            # Bybit 110043 means the
            # requested leverage is already
            # configured. Desired state is
            # therefore already satisfied.
            if (
                str(
                    getattr(
                        exc,
                        "status_code",
                        "",
                    )
                )
                == str(
                    LEVERAGE_NOT_MODIFIED_CODE
                )
            ):
                return False

            raise RuntimeError(
                "Bybit set-leverage "
                f"request failed: {exc}"
            ) from exc

        ret_code = response.get(
            "retCode"
        )

        if ret_code == 0:
            return True

        if (
            ret_code
            == LEVERAGE_NOT_MODIFIED_CODE
        ):
            return False

        raise RuntimeError(
            "Bybit set-leverage "
            f"request failed: {response}"
        )

    @staticmethod
    def _validate_response(
        *,
        response: dict,
        operation: str,
    ) -> None:
        if response.get("retCode") != 0:
            raise RuntimeError(
                f"Bybit {operation} "
                f"failed: {response}"
            )