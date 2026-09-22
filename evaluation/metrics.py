from __future__ import annotations

from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from evaluation.schema import (
    TradeOutcome,
)


ZERO = Decimal("0")


class PerformanceMetrics(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    trade_count: int = Field(
        ge=0
    )

    winning_trades: int = Field(
        ge=0
    )

    losing_trades: int = Field(
        ge=0
    )

    breakeven_trades: int = Field(
        ge=0
    )

    win_rate: Decimal = Field(
        ge=0,
        le=1,
    )

    total_realized_pnl: Decimal

    gross_profit: Decimal = Field(
        ge=0
    )

    gross_loss: Decimal = Field(
        ge=0
    )

    average_win: Decimal | None

    average_loss: Decimal | None

    profit_factor: Decimal | None

    expectancy_per_trade: Decimal | None

    average_r_multiple: Decimal | None

    best_trade_pnl: Decimal | None

    worst_trade_pnl: Decimal | None

    max_drawdown: Decimal = Field(
        ge=0
    )

    max_consecutive_losses: int = Field(
        ge=0
    )


class PerformanceMetricsEngine:
    def calculate(
        self,
        outcomes:
        tuple[TradeOutcome, ...]
        | list[TradeOutcome],
    ) -> PerformanceMetrics:

        trades = tuple(
            outcomes
        )

        self._validate_unique_trades(
            trades
        )

        if not trades:
            return PerformanceMetrics(
                trade_count=0,
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
                win_rate=ZERO,
                total_realized_pnl=ZERO,
                gross_profit=ZERO,
                gross_loss=ZERO,
                average_win=None,
                average_loss=None,
                profit_factor=None,
                expectancy_per_trade=None,
                average_r_multiple=None,
                best_trade_pnl=None,
                worst_trade_pnl=None,
                max_drawdown=ZERO,
                max_consecutive_losses=0,
            )

        ordered = tuple(
            sorted(
                trades,
                key=lambda trade:
                trade.closed_at_utc,
            )
        )

        winners = tuple(
            trade
            for trade in ordered
            if trade.is_win
        )

        losers = tuple(
            trade
            for trade in ordered
            if trade.is_loss
        )

        breakeven = tuple(
            trade
            for trade in ordered
            if trade.is_breakeven
        )

        trade_count = len(
            ordered
        )

        winning_count = len(
            winners
        )

        losing_count = len(
            losers
        )

        gross_profit = sum(
            (
                trade.realized_pnl
                for trade in winners
            ),
            ZERO,
        )

        gross_loss = abs(
            sum(
                (
                    trade.realized_pnl
                    for trade in losers
                ),
                ZERO,
            )
        )

        total_pnl = sum(
            (
                trade.realized_pnl
                for trade in ordered
            ),
            ZERO,
        )

        average_win = (
            gross_profit
            / Decimal(winning_count)
            if winning_count > 0
            else None
        )

        average_loss = (
            gross_loss
            / Decimal(losing_count)
            if losing_count > 0
            else None
        )

        # None means the denominator is zero.
        #
        # We avoid inventing an artificial
        # "infinity" value when no losing
        # trades exist yet.
        profit_factor = (
            gross_profit
            / gross_loss
            if gross_loss > ZERO
            else None
        )

        expectancy = (
            total_pnl
            / Decimal(trade_count)
        )

        average_r_multiple = (
            sum(
                (
                    trade.r_multiple
                    for trade in ordered
                ),
                ZERO,
            )
            / Decimal(trade_count)
        )

        pnl_values = [
            trade.realized_pnl
            for trade in ordered
        ]

        return PerformanceMetrics(
            trade_count=trade_count,

            winning_trades=(
                winning_count
            ),

            losing_trades=(
                losing_count
            ),

            breakeven_trades=(
                len(breakeven)
            ),

            win_rate=(
                Decimal(winning_count)
                / Decimal(trade_count)
            ),

            total_realized_pnl=(
                total_pnl
            ),

            gross_profit=(
                gross_profit
            ),

            gross_loss=(
                gross_loss
            ),

            average_win=(
                average_win
            ),

            average_loss=(
                average_loss
            ),

            profit_factor=(
                profit_factor
            ),

            expectancy_per_trade=(
                expectancy
            ),

            average_r_multiple=(
                average_r_multiple
            ),

            best_trade_pnl=max(
                pnl_values
            ),

            worst_trade_pnl=min(
                pnl_values
            ),

            max_drawdown=(
                self._calculate_max_drawdown(
                    ordered
                )
            ),

            max_consecutive_losses=(
                self
                ._calculate_max_consecutive_losses(
                    ordered
                )
            ),
        )

    @staticmethod
    def _validate_unique_trades(
        trades:
        tuple[TradeOutcome, ...],
    ) -> None:

        seen: set[str] = set()

        for trade in trades:
            if trade.trade_id in seen:
                raise ValueError(
                    "Duplicate trade_id "
                    "detected: "
                    f"{trade.trade_id}"
                )

            seen.add(
                trade.trade_id
            )

    @staticmethod
    def _calculate_max_drawdown(
        trades:
        tuple[TradeOutcome, ...],
    ) -> Decimal:

        equity = ZERO
        peak = ZERO
        max_drawdown = ZERO

        for trade in trades:
            equity += (
                trade.realized_pnl
            )

            if equity > peak:
                peak = equity

            drawdown = (
                peak - equity
            )

            if (
                drawdown
                > max_drawdown
            ):
                max_drawdown = (
                    drawdown
                )

        return max_drawdown

    @staticmethod
    def _calculate_max_consecutive_losses(
        trades:
        tuple[TradeOutcome, ...],
    ) -> int:

        current = 0
        maximum = 0

        for trade in trades:
            if trade.is_loss:
                current += 1

                maximum = max(
                    maximum,
                    current,
                )

            else:
                current = 0

        return maximum