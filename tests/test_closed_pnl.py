from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from account_data.closed_pnl import (
    BybitDemoClosedPnlClient,
)


FIXED_NOW = datetime(
    2026,
    9,
    22,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


def ms(
    hour: int,
) -> str:
    value = datetime(
        2026,
        9,
        22,
        hour,
        0,
        0,
        tzinfo=timezone.utc,
    )

    return str(
        int(
            value.timestamp()
            * 1000
        )
    )


class FakeSession:
    def __init__(self):
        self.calls = 0

    def get_closed_pnl(
        self,
        **kwargs,
    ):
        self.calls += 1

        assert (
            kwargs["category"]
            == "linear"
        )

        assert (
            kwargs["symbol"]
            == "BTCUSDT"
        )

        assert kwargs["limit"] == 100

        if self.calls == 1:
            assert (
                "cursor"
                not in kwargs
            )

            return {
                "retCode": 0,

                "result": {
                    "list": [
                        {
                            "symbol": (
                                "BTCUSDT"
                            ),
                            "closedPnl": "-10",
                            "updatedTime": (
                                ms(2)
                            ),
                        },

                        {
                            "symbol": (
                                "BTCUSDT"
                            ),
                            "closedPnl": "25.5",
                            "updatedTime": (
                                ms(6)
                            ),
                        },
                    ],

                    "nextPageCursor": (
                        "page-2"
                    ),
                },
            }

        assert (
            kwargs["cursor"]
            == "page-2"
        )

        return {
            "retCode": 0,

            "result": {
                "list": [
                    {
                        "symbol": (
                            "BTCUSDT"
                        ),
                        "closedPnl": "-5",
                        "updatedTime": (
                            ms(10)
                        ),
                    }
                ],

                "nextPageCursor": "",
            },
        }


def make_client(session):
    return BybitDemoClosedPnlClient(
        api_key="test-key",
        api_secret="test-secret",
        session=session,
    )


def test_today_realized_pnl():
    client = make_client(
        FakeSession()
    )

    snapshot = (
        client
        .get_today_realized_pnl(
            symbol="BTCUSDT",
            now_utc=FIXED_NOW,
        )
    )

    assert (
        snapshot.realized_pnl
        == Decimal("10.5")
    )

    assert (
        snapshot.record_count
        == 3
    )

    assert (
        snapshot.start_utc.hour
        == 0
    )


class EmptySession:
    def get_closed_pnl(
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


def test_no_closed_trades_returns_zero():
    snapshot = (
        make_client(
            EmptySession()
        )
        .get_today_realized_pnl(
            symbol="BTCUSDT",
            now_utc=FIXED_NOW,
        )
    )

    assert (
        snapshot.realized_pnl
        == Decimal("0")
    )

    assert snapshot.record_count == 0


class ApiErrorSession:
    def get_closed_pnl(
        self,
        **kwargs,
    ):
        return {
            "retCode": 10001,
            "retMsg": "error",
        }


def test_api_error_fails_closed():
    with pytest.raises(
        RuntimeError
    ):
        (
            make_client(
                ApiErrorSession()
            )
            .get_today_realized_pnl(
                symbol="BTCUSDT",
                now_utc=FIXED_NOW,
            )
        )


class WrongSymbolSession:
    def get_closed_pnl(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [
                    {
                        "symbol": "ETHUSDT",
                        "closedPnl": "5",
                        "updatedTime": ms(5),
                    }
                ],

                "nextPageCursor": "",
            },
        }


def test_wrong_symbol_fails_closed():
    with pytest.raises(
        RuntimeError
    ):
        (
            make_client(
                WrongSymbolSession()
            )
            .get_today_realized_pnl(
                symbol="BTCUSDT",
                now_utc=FIXED_NOW,
            )
        )


def test_naive_datetime_rejected():
    with pytest.raises(
        ValueError
    ):
        (
            make_client(
                EmptySession()
            )
            .get_today_realized_pnl(
                symbol="BTCUSDT",

                now_utc=datetime(
                    2026,
                    9,
                    22,
                    12,
                    0,
                    0,
                ),
            )
        )