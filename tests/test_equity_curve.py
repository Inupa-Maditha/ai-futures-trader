from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

import pytest

from evaluation.equity_curve import (
    EquityCurveEngine,
)

from evaluation.schema import (
    TradeExitReason,
    TradeOutcome,
    TradeSide,
)


BASE_TIME = datetime(
    2026,
    9,
    22,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_trade(
    *,
    trade_id,
    pnl,
    close_offset,
):
    return TradeOutcome(
        trade_id=trade_id,

        run_id=(
            f"run-{trade_id}"
        ),

        symbol="BTCUSDT",

        side=TradeSide.LONG,

        opened_at_utc=(
            BASE_TIME
        ),

        closed_at_utc=(
            BASE_TIME
            + timedelta(
                hours=close_offset
            )
        ),

        entry_price=Decimal(
            "85000"
        ),

        exit_price=Decimal(
            "86000"
        ),

        quantity=Decimal(
            "0.01"
        ),

        initial_risk_amount=Decimal(
            "50"
        ),

        realized_pnl=Decimal(
            pnl
        ),

        exit_reason=(
            TradeExitReason
            .OTHER
        ),
    )


def test_empty_curve():
    curve = (
        EquityCurveEngine()
        .build([])
    )

    assert curve.points == ()

    assert (
        curve.final_cumulative_pnl
        == Decimal("0")
    )

    assert (
        curve.max_drawdown
        == Decimal("0")
    )


def test_cumulative_pnl_curve():
    trades = [
        make_trade(
            trade_id="1",
            pnl="100",
            close_offset=1,
        ),

        make_trade(
            trade_id="2",
            pnl="-40",
            close_offset=2,
        ),

        make_trade(
            trade_id="3",
            pnl="25",
            close_offset=3,
        ),
    ]

    curve = (
        EquityCurveEngine()
        .build(trades)
    )

    assert [
        point.cumulative_pnl
        for point in curve.points
    ] == [
        Decimal("100"),
        Decimal("60"),
        Decimal("85"),
    ]

    assert (
        curve.final_cumulative_pnl
        == Decimal("85")
    )


def test_drawdown_curve():
    trades = [
        make_trade(
            trade_id="1",
            pnl="100",
            close_offset=1,
        ),

        make_trade(
            trade_id="2",
            pnl="-40",
            close_offset=2,
        ),

        make_trade(
            trade_id="3",
            pnl="-30",
            close_offset=3,
        ),

        make_trade(
            trade_id="4",
            pnl="20",
            close_offset=4,
        ),
    ]

    curve = (
        EquityCurveEngine()
        .build(trades)
    )

    assert [
        point.drawdown
        for point in curve.points
    ] == [
        Decimal("0"),
        Decimal("40"),
        Decimal("70"),
        Decimal("50"),
    ]

    assert (
        curve.max_drawdown
        == Decimal("70")
    )


def test_trades_are_sorted_by_close_time():
    trades = [
        make_trade(
            trade_id="second",
            pnl="20",
            close_offset=2,
        ),

        make_trade(
            trade_id="first",
            pnl="10",
            close_offset=1,
        ),
    ]

    curve = (
        EquityCurveEngine()
        .build(trades)
    )

    assert [
        point.trade_id
        for point in curve.points
    ] == [
        "first",
        "second",
    ]


def test_starting_equity_curve():
    trades = [
        make_trade(
            trade_id="1",
            pnl="100",
            close_offset=1,
        ),

        make_trade(
            trade_id="2",
            pnl="-50",
            close_offset=2,
        ),
    ]

    curve = (
        EquityCurveEngine()
        .build(
            trades,

            starting_equity=(
                Decimal("10000")
            ),
        )
    )

    assert (
        curve.points[0]
        .equity_after_trade
        == Decimal("10100")
    )

    assert (
        curve.points[1]
        .equity_after_trade
        == Decimal("10050")
    )

    assert (
        curve.final_equity
        == Decimal("10050")
    )


def test_duplicate_trade_id_rejected():
    trades = [
        make_trade(
            trade_id="same",
            pnl="100",
            close_offset=1,
        ),

        make_trade(
            trade_id="same",
            pnl="-50",
            close_offset=2,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="Duplicate",
    ):
        (
            EquityCurveEngine()
            .build(trades)
        )


def test_invalid_starting_equity():
    with pytest.raises(
        ValueError,
        match="starting_equity",
    ):
        (
            EquityCurveEngine()
            .build(
                [],
                starting_equity=(
                    Decimal("0")
                ),
            )
        )