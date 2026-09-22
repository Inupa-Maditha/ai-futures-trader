from decimal import Decimal

import pytest

from account_data.bybit_demo import (
    BybitDemoAccountClient,
)


class FakeSession:
    def get_wallet_balance(
        self,
        **kwargs,
    ):
        assert (
            kwargs["accountType"]
            == "UNIFIED"
        )

        return {
            "retCode": 0,
            "retMsg": "OK",

            "result": {
                "list": [
                    {
                        "accountType": (
                            "UNIFIED"
                        ),

                        "totalEquity": (
                            "10000.50"
                        ),

                        "totalAvailableBalance": (
                            "8500.25"
                        ),
                    }
                ]
            },
        }

    def get_positions(
        self,
        **kwargs,
    ):
        assert (
            kwargs["category"]
            == "linear"
        )

        assert (
            kwargs["symbol"]
            == "BTCUSDT"
        )

        return {
            "retCode": 0,
            "retMsg": "OK",

            "result": {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "side": "Buy",
                        "size": "0.05",
                        "avgPrice": "86000",
                        "leverage": "2",
                        "unrealisedPnl": "15.4",
                        "curRealisedPnl": (
                            "-0.25"
                        ),
                    }
                ]
            },
        }


def make_client(session=None):
    return BybitDemoAccountClient(
        api_key="test-key",
        api_secret="test-secret",
        session=(
            session
            if session is not None
            else FakeSession()
        ),
    )


def test_demo_snapshot_parses():
    snapshot = (
        make_client()
        .get_snapshot(
            "BTCUSDT"
        )
    )

    assert (
        snapshot.account_equity
        == Decimal("10000.50")
    )

    assert (
        snapshot.available_balance
        == Decimal("8500.25")
    )

    assert (
        snapshot.open_position_count
        == 1
    )

    assert len(
        snapshot.positions
    ) == 1

    position = (
        snapshot.positions[0]
    )

    assert (
        position.side
        == "Buy"
    )

    assert (
        position.size
        == Decimal("0.05")
    )

    assert (
        position.avg_price
        == Decimal("86000")
    )

    assert (
        position.leverage
        == Decimal("2")
    )

    assert (
        position.unrealised_pnl
        == Decimal("15.4")
    )

    assert (
        position.current_realised_pnl
        == Decimal("-0.25")
    )


class EmptyPositionSession(
    FakeSession
):
    def get_positions(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,
            "retMsg": "OK",

            "result": {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "side": "",
                        "size": "0",
                        "avgPrice": "",
                        "leverage": "",

                        # This matches the live
                        # Bybit Demo behaviour
                        # we observed.
                        "unrealisedPnl": "",
                        "curRealisedPnl": "",
                    }
                ]
            },
        }


def test_empty_position_not_counted():
    snapshot = (
        make_client(
            EmptyPositionSession()
        )
        .get_snapshot(
            "BTCUSDT"
        )
    )

    assert (
        snapshot.open_position_count
        == 0
    )

    assert len(
        snapshot.positions
    ) == 1

    position = (
        snapshot.positions[0]
    )

    assert position.side is None

    assert (
        position.size
        == Decimal("0")
    )

    assert (
        position.avg_price
        is None
    )

    assert (
        position.leverage
        is None
    )

    assert (
        position.unrealised_pnl
        == Decimal("0")
    )

    assert (
        position.current_realised_pnl
        == Decimal("0")
    )


class HedgePositionSession(
    FakeSession
):
    def get_positions(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,
            "retMsg": "OK",

            "result": {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "side": "Buy",
                        "size": "0.01",
                        "avgPrice": "85000",
                        "leverage": "2",
                        "unrealisedPnl": "5",
                        "curRealisedPnl": "0",
                    },

                    {
                        "symbol": "BTCUSDT",
                        "side": "Sell",
                        "size": "0.02",
                        "avgPrice": "87000",
                        "leverage": "2",
                        "unrealisedPnl": "4",
                        "curRealisedPnl": "0",
                    },
                ]
            },
        }


def test_two_open_sides_count_as_two():
    snapshot = (
        make_client(
            HedgePositionSession()
        )
        .get_snapshot(
            "BTCUSDT"
        )
    )

    assert (
        snapshot.open_position_count
        == 2
    )


class WalletErrorSession(
    FakeSession
):
    def get_wallet_balance(
        self,
        **kwargs,
    ):
        return {
            "retCode": 10001,
            "retMsg": "error",
        }


def test_wallet_api_error_fails_closed():
    with pytest.raises(
        RuntimeError
    ):
        (
            make_client(
                WalletErrorSession()
            )
            .get_snapshot(
                "BTCUSDT"
            )
        )


class PositionErrorSession(
    FakeSession
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
    with pytest.raises(
        RuntimeError
    ):
        (
            make_client(
                PositionErrorSession()
            )
            .get_snapshot(
                "BTCUSDT"
            )
        )


class BadSymbolSession(
    FakeSession
):
    def get_positions(
        self,
        **kwargs,
    ):
        response = (
            super()
            .get_positions(
                **kwargs
            )
        )

        response[
            "result"
        ][
            "list"
        ][0][
            "symbol"
        ] = "ETHUSDT"

        return response


def test_wrong_position_symbol_fails_closed():
    with pytest.raises(
        RuntimeError
    ):
        (
            make_client(
                BadSymbolSession()
            )
            .get_snapshot(
                "BTCUSDT"
            )
        )


class EmptyEquitySession(
    FakeSession
):
    def get_wallet_balance(
        self,
        **kwargs,
    ):
        response = (
            super()
            .get_wallet_balance(
                **kwargs
            )
        )

        response[
            "result"
        ][
            "list"
        ][0][
            "totalEquity"
        ] = ""

        return response


def test_missing_equity_fails_closed():
    with pytest.raises(
        RuntimeError
    ):
        (
            make_client(
                EmptyEquitySession()
            )
            .get_snapshot(
                "BTCUSDT"
            )
        )


class OpenPositionMissingPnlSession(
    FakeSession
):
    def get_positions(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,
            "retMsg": "OK",

            "result": {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "side": "Buy",
                        "size": "0.05",
                        "avgPrice": "86000",
                        "leverage": "2",

                        # For an actual open
                        # position, missing PnL
                        # must still fail closed.
                        "unrealisedPnl": "",
                        "curRealisedPnl": "",
                    }
                ]
            },
        }


def test_open_position_missing_pnl_fails_closed():
    with pytest.raises(
        RuntimeError
    ):
        (
            make_client(
                OpenPositionMissingPnlSession()
            )
            .get_snapshot(
                "BTCUSDT"
            )
        )


class ZeroEquitySession(
    FakeSession
):
    def get_wallet_balance(
        self,
        **kwargs,
    ):
        response = (
            super()
            .get_wallet_balance(
                **kwargs
            )
        )

        response[
            "result"
        ][
            "list"
        ][0][
            "totalEquity"
        ] = "0"

        return response


def test_zero_equity_fails_closed():
    with pytest.raises(
        RuntimeError
    ):
        (
            make_client(
                ZeroEquitySession()
            )
            .get_snapshot(
                "BTCUSDT"
            )
        )