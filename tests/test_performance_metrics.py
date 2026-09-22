from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

import pytest

from evaluation.metrics import (
    PerformanceMetricsEngine,
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
    risk="50",
    close_offset=1,
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
            risk
        ),
        realized_pnl=Decimal(
            pnl
        ),
        exit_reason=(
            TradeExitReason
            .TAKE_PROFIT
        ),
    )


def test_trade_outcome_r_multiple():
    trade = make_trade(
        trade_id="1",
        pnl="100",
        risk="50",
    )

    assert (
        trade.r_multiple
        == Decimal("2")
    )


def test_invalid_trade_times_rejected():
    with pytest.raises(
        ValueError
    ):
        TradeOutcome(
            trade_id="1",
            run_id="run-1",
            symbol="BTCUSDT",
            side=TradeSide.LONG,
            opened_at_utc=BASE_TIME,
            closed_at_utc=BASE_TIME,
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
                "100"
            ),
            exit_reason=(
                TradeExitReason
                .TAKE_PROFIT
            ),
        )


def test_empty_metrics():
    metrics = (
        PerformanceMetricsEngine()
        .calculate([])
    )

    assert metrics.trade_count == 0

    assert (
        metrics.total_realized_pnl
        == Decimal("0")
    )

    assert (
        metrics.profit_factor
        is None
    )


def test_win_rate_and_total_pnl():
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
        make_trade(
            trade_id="3",
            pnl="0",
            close_offset=3,
        ),
        make_trade(
            trade_id="4",
            pnl="150",
            close_offset=4,
        ),
    ]

    metrics = (
        PerformanceMetricsEngine()
        .calculate(trades)
    )

    assert (
        metrics.trade_count
        == 4
    )

    assert (
        metrics.winning_trades
        == 2
    )

    assert (
        metrics.losing_trades
        == 1
    )

    assert (
        metrics.breakeven_trades
        == 1
    )

    assert (
        metrics.win_rate
        == Decimal("0.5")
    )

    assert (
        metrics.total_realized_pnl
        == Decimal("200")
    )


def test_profit_factor():
    trades = [
        make_trade(
            trade_id="1",
            pnl="100",
            close_offset=1,
        ),
        make_trade(
            trade_id="2",
            pnl="50",
            close_offset=2,
        ),
        make_trade(
            trade_id="3",
            pnl="-50",
            close_offset=3,
        ),
    ]

    metrics = (
        PerformanceMetricsEngine()
        .calculate(trades)
    )

    assert (
        metrics.gross_profit
        == Decimal("150")
    )

    assert (
        metrics.gross_loss
        == Decimal("50")
    )

    assert (
        metrics.profit_factor
        == Decimal("3")
    )


def test_expectancy_and_average_r():
    trades = [
        make_trade(
            trade_id="1",
            pnl="100",
            risk="50",
            close_offset=1,
        ),
        make_trade(
            trade_id="2",
            pnl="-50",
            risk="50",
            close_offset=2,
        ),
    ]

    metrics = (
        PerformanceMetricsEngine()
        .calculate(trades)
    )

    assert (
        metrics.expectancy_per_trade
        == Decimal("25")
    )

    assert (
        metrics.average_r_multiple
        == Decimal("0.5")
    )


def test_max_drawdown():
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

    metrics = (
        PerformanceMetricsEngine()
        .calculate(trades)
    )

    assert (
        metrics.max_drawdown
        == Decimal("70")
    )


def test_max_consecutive_losses():
    trades = [
        make_trade(
            trade_id="1",
            pnl="-10",
            close_offset=1,
        ),
        make_trade(
            trade_id="2",
            pnl="-20",
            close_offset=2,
        ),
        make_trade(
            trade_id="3",
            pnl="50",
            close_offset=3,
        ),
        make_trade(
            trade_id="4",
            pnl="-10",
            close_offset=4,
        ),
        make_trade(
            trade_id="5",
            pnl="-20",
            close_offset=5,
        ),
        make_trade(
            trade_id="6",
            pnl="-30",
            close_offset=6,
        ),
    ]

    metrics = (
        PerformanceMetricsEngine()
        .calculate(trades)
    )

    assert (
        metrics.max_consecutive_losses
        == 3
    )


def test_best_and_worst_trade():
    trades = [
        make_trade(
            trade_id="1",
            pnl="120",
            close_offset=1,
        ),
        make_trade(
            trade_id="2",
            pnl="-75",
            close_offset=2,
        ),
        make_trade(
            trade_id="3",
            pnl="25",
            close_offset=3,
        ),
    ]

    metrics = (
        PerformanceMetricsEngine()
        .calculate(trades)
    )

    assert (
        metrics.best_trade_pnl
        == Decimal("120")
    )

    assert (
        metrics.worst_trade_pnl
        == Decimal("-75")
    )


def test_no_losses_profit_factor_is_none():
    trades = [
        make_trade(
            trade_id="1",
            pnl="100",
            close_offset=1,
        ),
        make_trade(
            trade_id="2",
            pnl="50",
            close_offset=2,
        ),
    ]

    metrics = (
        PerformanceMetricsEngine()
        .calculate(trades)
    )

    assert (
        metrics.profit_factor
        is None
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
            PerformanceMetricsEngine()
            .calculate(trades)
        )