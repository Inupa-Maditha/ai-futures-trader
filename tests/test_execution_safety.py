from decimal import Decimal

import pytest

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


def make_order_record(
    *,
    link_id="aft-v1-test",
    status="New",
    reduce_only=False,
):
    return {
        "orderId": "order-123",
        "orderLinkId": link_id,

        "symbol": "BTCUSDT",

        "side": "Buy",

        "orderStatus": status,

        "qty": "0.050",

        "price": "86000.10",

        "positionIdx": 0,

        "reduceOnly": reduce_only,
    }


def make_request():
    return DemoExecutionRequest(
        approval_id="approval-1",

        order_link_id=(
            "aft-v1-test"
        ),

        symbol="BTCUSDT",

        side=ExecutionSide.BUY,

        quantity=Decimal(
            "0.050"
        ),

        entry_price=Decimal(
            "86000.10"
        ),

        stop_loss=Decimal(
            "85000.00"
        ),

        take_profit=Decimal(
            "88000.00"
        ),

        leverage=Decimal(
            "1"
        ),
    )


class BaseSession:
    def get_positions(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [
                    {
                        "symbol": (
                            "BTCUSDT"
                        ),

                        "positionIdx": 0,

                        "side": "",

                        "size": "0",
                    }
                ]
            },
        }

    def get_open_orders(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [],

                "nextPageCursor": "",
            },
        }

    def get_order_history(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [],

                "nextPageCursor": "",
            },
        }


class RealtimeOrderSession(
    BaseSession
):
    def get_open_orders(
        self,
        **kwargs,
    ):
        if (
            "orderLinkId"
            in kwargs
        ):
            return {
                "retCode": 0,

                "result": {
                    "list": [
                        make_order_record()
                    ],

                    "nextPageCursor": "",
                },
            }

        return super().get_open_orders(
            **kwargs
        )


def test_realtime_order_lookup():
    repository = (
        BybitDemoOrderRepository(
            RealtimeOrderSession()
        )
    )

    order = (
        repository
        .find_by_link_id(
            symbol="BTCUSDT",

            order_link_id=(
                "aft-v1-test"
            ),
        )
    )

    assert order is not None

    assert (
        order.order_id
        == "order-123"
    )

    assert (
        order.quantity
        == Decimal("0.050")
    )


class HistoryFallbackSession(
    BaseSession
):
    def get_order_history(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [
                    make_order_record(
                        status="Filled"
                    )
                ],

                "nextPageCursor": "",
            },
        }


def test_history_fallback_lookup():
    repository = (
        BybitDemoOrderRepository(
            HistoryFallbackSession()
        )
    )

    order = (
        repository
        .find_by_link_id(
            symbol="BTCUSDT",

            order_link_id=(
                "aft-v1-test"
            ),
        )
    )

    assert order is not None

    assert (
        order.order_status
        == "Filled"
    )


def test_missing_order_returns_none():
    repository = (
        BybitDemoOrderRepository(
            BaseSession()
        )
    )

    order = (
        repository
        .find_by_link_id(
            symbol="BTCUSDT",

            order_link_id=(
                "aft-v1-test"
            ),
        )
    )

    assert order is None


class WrongLinkSession(
    BaseSession
):
    def get_open_orders(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [
                    make_order_record(
                        link_id="wrong-id"
                    )
                ],

                "nextPageCursor": "",
            },
        }


def test_wrong_link_id_fails_closed():
    repository = (
        BybitDemoOrderRepository(
            WrongLinkSession()
        )
    )

    with pytest.raises(
        RuntimeError
    ):
        repository.find_by_link_id(
            symbol="BTCUSDT",

            order_link_id=(
                "aft-v1-test"
            ),
        )


def test_one_way_empty_position_passes():
    session = BaseSession()

    repository = (
        BybitDemoOrderRepository(
            session
        )
    )

    preflight = (
        DemoExecutionPreflight(
            session=session,

            order_repository=(
                repository
            ),
        )
    )

    preflight.validate(
        make_request()
    )


class HedgeModeSession(
    BaseSession
):
    def get_positions(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [
                    {
                        "symbol": (
                            "BTCUSDT"
                        ),

                        "positionIdx": 1,

                        "side": "Buy",

                        "size": "0",
                    },

                    {
                        "symbol": (
                            "BTCUSDT"
                        ),

                        "positionIdx": 2,

                        "side": "Sell",

                        "size": "0",
                    },
                ]
            },
        }


def test_hedge_mode_rejected():
    session = HedgeModeSession()

    preflight = (
        DemoExecutionPreflight(
            session=session,

            order_repository=(
                BybitDemoOrderRepository(
                    session
                )
            ),
        )
    )

    with pytest.raises(
        RuntimeError,
        match="One-Way",
    ):
        preflight.validate(
            make_request()
        )


class OpenPositionSession(
    BaseSession
):
    def get_positions(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [
                    {
                        "symbol": (
                            "BTCUSDT"
                        ),

                        "positionIdx": 0,

                        "side": "Buy",

                        "size": "0.05",
                    }
                ]
            },
        }


def test_position_appearing_before_execution_rejected():
    session = OpenPositionSession()

    preflight = (
        DemoExecutionPreflight(
            session=session,

            order_repository=(
                BybitDemoOrderRepository(
                    session
                )
            ),
        )
    )

    with pytest.raises(
        RuntimeError,
        match="open BTCUSDT",
    ):
        preflight.validate(
            make_request()
        )


class ActiveEntryOrderSession(
    BaseSession
):
    def get_open_orders(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [
                    make_order_record(
                        link_id=(
                            "another-order"
                        )
                    )
                ],

                "nextPageCursor": "",
            },
        }


def test_existing_entry_order_rejected():
    session = (
        ActiveEntryOrderSession()
    )

    preflight = (
        DemoExecutionPreflight(
            session=session,

            order_repository=(
                BybitDemoOrderRepository(
                    session
                )
            ),
        )
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "active "
            "non-reduce-only"
        ),
    ):
        preflight.validate(
            make_request()
        )


class ReduceOnlyOrderSession(
    BaseSession
):
    def get_open_orders(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [
                    make_order_record(
                        link_id="protective",

                        reduce_only=True,
                    )
                ],

                "nextPageCursor": "",
            },
        }


def test_reduce_only_order_does_not_block():
    session = ReduceOnlyOrderSession()

    preflight = (
        DemoExecutionPreflight(
            session=session,

            order_repository=(
                BybitDemoOrderRepository(
                    session
                )
            ),
        )
    )

    preflight.validate(
        make_request()
    )


class OrderApiErrorSession(
    BaseSession
):
    def get_open_orders(
        self,
        **kwargs,
    ):
        return {
            "retCode": 10001,
            "retMsg": "error",
        }


def test_order_api_error_fails_closed():
    repository = (
        BybitDemoOrderRepository(
            OrderApiErrorSession()
        )
    )

    with pytest.raises(
        RuntimeError
    ):
        repository.list_active_orders(
            symbol="BTCUSDT"
        )


class PositionApiErrorSession(
    BaseSession
):
    def get_positions(
        self,
        **kwargs,
    ):
        return {
            "retCode": 10001,
            "retMsg": "error",
        }


def test_position_api_error_fails_closed():
    session = (
        PositionApiErrorSession()
    )

    preflight = (
        DemoExecutionPreflight(
            session=session,

            order_repository=(
                BybitDemoOrderRepository(
                    session
                )
            ),
        )
    )

    with pytest.raises(
        RuntimeError
    ):
        preflight.validate(
            make_request()
        )