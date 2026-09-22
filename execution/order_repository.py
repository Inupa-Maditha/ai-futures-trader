from __future__ import annotations

from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ObservedOrder(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    symbol: str

    order_id: str = Field(
        min_length=1
    )

    order_link_id: str

    side: str

    order_status: str

    quantity: Decimal = Field(
        gt=0
    )

    price: Decimal | None

    position_idx: int

    reduce_only: bool


class BybitDemoOrderRepository:
    MAX_PAGES = 20
    PAGE_LIMIT = 50

    def __init__(
        self,
        session,
    ):
        self.session = session

    def find_by_link_id(
        self,
        *,
        symbol: str,
        order_link_id: str,
    ) -> ObservedOrder | None:

        # -----------------------------------------
        # 1. Realtime lookup first
        # -----------------------------------------

        response = (
            self.session
            .get_open_orders(
                category="linear",
                symbol=symbol,
                orderLinkId=order_link_id,
                limit=1,
            )
        )

        self._validate_response(
            response,
            operation=(
                "realtime order lookup"
            ),
        )

        records = (
            response
            .get("result", {})
            .get("list", [])
        )

        realtime = (
            self._extract_exact_order(
                records=records,
                symbol=symbol,
                order_link_id=(
                    order_link_id
                ),
            )
        )

        if realtime is not None:
            return realtime

        # -----------------------------------------
        # 2. History fallback
        #
        # Useful after a Bybit service restart
        # or when the order has moved out of
        # realtime storage.
        # -----------------------------------------

        response = (
            self.session
            .get_order_history(
                category="linear",
                symbol=symbol,
                orderLinkId=order_link_id,
                limit=1,
            )
        )

        self._validate_response(
            response,
            operation=(
                "order history lookup"
            ),
        )

        records = (
            response
            .get("result", {})
            .get("list", [])
        )

        return self._extract_exact_order(
            records=records,
            symbol=symbol,
            order_link_id=(
                order_link_id
            ),
        )

    def list_active_orders(
        self,
        *,
        symbol: str,
    ) -> tuple[ObservedOrder, ...]:

        orders: list[ObservedOrder] = []

        cursor: str | None = None

        seen_cursors: set[str] = set()

        for _ in range(
            self.MAX_PAGES
        ):
            params = {
                "category": "linear",
                "symbol": symbol,
                "openOnly": 0,
                "limit": self.PAGE_LIMIT,
            }

            if cursor:
                params["cursor"] = cursor

            response = (
                self.session
                .get_open_orders(
                    **params
                )
            )

            self._validate_response(
                response,
                operation=(
                    "active-order lookup"
                ),
            )

            result = response.get(
                "result",
                {},
            )

            records = result.get(
                "list",
                [],
            )

            for record in records:
                order = self._parse_order(
                    record
                )

                if (
                    order.symbol
                    != symbol
                ):
                    raise RuntimeError(
                        "Bybit returned an "
                        "unexpected active-order "
                        "symbol."
                    )

                orders.append(
                    order
                )

            next_cursor = (
                result.get(
                    "nextPageCursor"
                )
                or ""
            )

            if not next_cursor:
                break

            if (
                next_cursor
                in seen_cursors
            ):
                raise RuntimeError(
                    "Active-order pagination "
                    "cursor repeated."
                )

            seen_cursors.add(
                next_cursor
            )

            cursor = next_cursor

        else:
            raise RuntimeError(
                "Active-order pagination "
                "exceeded safety limit."
            )

        return tuple(
            orders
        )

    def _extract_exact_order(
        self,
        *,
        records: list[dict],
        symbol: str,
        order_link_id: str,
    ) -> ObservedOrder | None:

        if not records:
            return None

        matches = []

        for record in records:
            order = self._parse_order(
                record
            )

            if (
                order.symbol
                != symbol
            ):
                raise RuntimeError(
                    "Order lookup returned "
                    "an unexpected symbol."
                )

            if (
                order.order_link_id
                != order_link_id
            ):
                raise RuntimeError(
                    "Order lookup returned "
                    "an unexpected "
                    "orderLinkId."
                )

            matches.append(
                order
            )

        if len(matches) != 1:
            raise RuntimeError(
                "Expected exactly one "
                "order for orderLinkId "
                f"'{order_link_id}', "
                f"got {len(matches)}."
            )

        return matches[0]

    @staticmethod
    def _parse_order(
        record: dict,
    ) -> ObservedOrder:

        order_id = record.get(
            "orderId"
        )

        if not order_id:
            raise RuntimeError(
                "Order record is missing "
                "orderId."
            )

        order_link_id = record.get(
            "orderLinkId"
        )

        if order_link_id is None:
            raise RuntimeError(
                "Order record is missing "
                "orderLinkId."
            )

        symbol = record.get(
            "symbol"
        )

        if not symbol:
            raise RuntimeError(
                "Order record is missing "
                "symbol."
            )

        side = record.get(
            "side"
        )

        if side not in (
            "Buy",
            "Sell",
        ):
            raise RuntimeError(
                "Order record contains "
                "an invalid side."
            )

        order_status = record.get(
            "orderStatus"
        )

        if not order_status:
            raise RuntimeError(
                "Order record is missing "
                "orderStatus."
            )

        try:
            quantity = Decimal(
                str(
                    record["qty"]
                )
            )
        except Exception as exc:
            raise RuntimeError(
                "Invalid order quantity."
            ) from exc

        if quantity <= 0:
            raise RuntimeError(
                "Order quantity must be "
                "greater than zero."
            )

        raw_price = record.get(
            "price"
        )

        if raw_price in (
            None,
            "",
        ):
            price = None

        else:
            try:
                price = Decimal(
                    str(raw_price)
                )
            except Exception as exc:
                raise RuntimeError(
                    "Invalid order price."
                ) from exc

        try:
            position_idx = int(
                record[
                    "positionIdx"
                ]
            )
        except Exception as exc:
            raise RuntimeError(
                "Invalid positionIdx."
            ) from exc

        reduce_only = record.get(
            "reduceOnly"
        )

        if not isinstance(
            reduce_only,
            bool,
        ):
            raise RuntimeError(
                "Invalid reduceOnly value."
            )

        return ObservedOrder(
            symbol=symbol,

            order_id=order_id,

            order_link_id=(
                order_link_id
            ),

            side=side,

            order_status=(
                order_status
            ),

            quantity=quantity,

            price=price,

            position_idx=(
                position_idx
            ),

            reduce_only=reduce_only,
        )

    @staticmethod
    def _validate_response(
        response: dict,
        *,
        operation: str,
    ) -> None:

        if response.get(
            "retCode"
        ) != 0:
            raise RuntimeError(
                f"Bybit {operation} "
                f"failed: {response}"
            )