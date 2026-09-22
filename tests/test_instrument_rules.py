from decimal import Decimal

import pytest

from risk_manager.instrument_rules import (
    BybitInstrumentRulesClient,
    ceil_to_step,
    floor_to_step,
    nearest_to_step,
)


class FakeSession:
    def get_instruments_info(
        self,
        *,
        category,
        symbol,
    ):
        assert category == "linear"
        assert symbol == "BTCUSDT"

        return {
            "retCode": 0,
            "retMsg": "OK",

            "result": {
                "category": "linear",

                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "status": "Trading",
                        "contractType": (
                            "LinearPerpetual"
                        ),

                        "priceFilter": {
                            "minPrice": "0.10",
                            "maxPrice": (
                                "1999999.80"
                            ),
                            "tickSize": "0.10",
                        },

                        "lotSizeFilter": {
                            "minOrderQty": (
                                "0.001"
                            ),
                            "maxOrderQty": (
                                "1190.000"
                            ),
                            "maxMktOrderQty": (
                                "500.000"
                            ),
                            "qtyStep": "0.001",
                            "minNotionalValue": (
                                "5"
                            ),
                        },

                        "leverageFilter": {
                            "minLeverage": "1",
                            "maxLeverage": (
                                "100.00"
                            ),
                            "leverageStep": (
                                "0.01"
                            ),
                        },
                    }
                ],
            },
        }


def test_instrument_rules_parse():
    client = (
        BybitInstrumentRulesClient(
            session=FakeSession()
        )
    )

    rules = client.get_linear_rules(
        "BTCUSDT"
    )

    assert rules.symbol == "BTCUSDT"

    assert (
        rules.contract_type
        == "LinearPerpetual"
    )

    assert (
        rules.tick_size
        == Decimal("0.10")
    )

    assert (
        rules.qty_step
        == Decimal("0.001")
    )

    assert (
        rules.min_order_qty
        == Decimal("0.001")
    )

    assert (
        rules.min_notional_value
        == Decimal("5")
    )

    assert (
        rules.leverage_step
        == Decimal("0.01")
    )


def test_floor_quantity_to_step():
    result = floor_to_step(
        Decimal("0.053827"),
        Decimal("0.001"),
    )

    assert result == Decimal(
        "0.053"
    )


def test_exact_floor_is_unchanged():
    result = floor_to_step(
        Decimal("0.050"),
        Decimal("0.001"),
    )

    assert result == Decimal(
        "0.050"
    )


def test_ceil_to_leverage_step():
    result = ceil_to_step(
        Decimal("1.4331"),
        Decimal("0.01"),
    )

    assert result == Decimal(
        "1.44"
    )


def test_nearest_price_to_tick():
    result = nearest_to_step(
        Decimal("86000.06"),
        Decimal("0.10"),
    )

    assert result == Decimal(
        "86000.10"
    )


def test_floor_price_to_tick():
    result = floor_to_step(
        Decimal("86000.09"),
        Decimal("0.10"),
    )

    assert result == Decimal(
        "86000.00"
    )


def test_ceil_price_to_tick():
    result = ceil_to_step(
        Decimal("86000.01"),
        Decimal("0.10"),
    )

    assert result == Decimal(
        "86000.10"
    )


def test_zero_step_rejected():
    with pytest.raises(ValueError):
        floor_to_step(
            Decimal("1"),
            Decimal("0"),
        )


def test_negative_value_rejected():
    with pytest.raises(ValueError):
        floor_to_step(
            Decimal("-1"),
            Decimal("0.01"),
        )


class ErrorSession:
    def get_instruments_info(
        self,
        **kwargs,
    ):
        return {
            "retCode": 10001,
            "retMsg": "Bad request",
        }


def test_api_error_fails_closed():
    client = (
        BybitInstrumentRulesClient(
            session=ErrorSession()
        )
    )

    with pytest.raises(
        RuntimeError
    ):
        client.get_linear_rules(
            "BTCUSDT"
        )


class NonTradingSession:
    def get_instruments_info(
        self,
        **kwargs,
    ):
        response = (
            FakeSession()
            .get_instruments_info(
                category="linear",
                symbol="BTCUSDT",
            )
        )

        response["result"]["list"][0][
            "status"
        ] = "Closed"

        return response


def test_non_trading_symbol_rejected():
    client = (
        BybitInstrumentRulesClient(
            session=NonTradingSession()
        )
    )

    with pytest.raises(
        RuntimeError
    ):
        client.get_linear_rules(
            "BTCUSDT"
        )