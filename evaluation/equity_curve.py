from __future__ import annotations

from datetime import datetime
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


class EquityCurvePoint(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    trade_number: int = Field(
        ge=1
    )

    trade_id: str = Field(
        min_length=1
    )

    closed_at_utc: datetime

    realized_pnl: Decimal

    cumulative_pnl: Decimal

    peak_cumulative_pnl: Decimal

    drawdown: Decimal = Field(
        ge=0
    )

    equity_after_trade: Decimal | None = None


class EquityCurve(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    starting_equity: Decimal | None

    points: tuple[
        EquityCurvePoint,
        ...,
    ]

    final_cumulative_pnl: Decimal

    max_drawdown: Decimal = Field(
        ge=0
    )

    final_equity: Decimal | None


class EquityCurveEngine:
    def build(
        self,
        outcomes: (
            tuple[TradeOutcome, ...]
            | list[TradeOutcome]
        ),
        *,
        starting_equity: Decimal | None = None,
    ) -> EquityCurve:

        trades = tuple(
            outcomes
        )

        if (
            starting_equity is not None
            and starting_equity <= ZERO
        ):
            raise ValueError(
                "starting_equity must "
                "be greater than zero."
            )

        self._validate_unique_trades(
            trades
        )

        if not trades:
            return EquityCurve(
                starting_equity=(
                    starting_equity
                ),

                points=(),

                final_cumulative_pnl=(
                    ZERO
                ),

                max_drawdown=ZERO,

                final_equity=(
                    starting_equity
                ),
            )

        ordered = tuple(
            sorted(
                trades,
                key=lambda trade:
                trade.closed_at_utc,
            )
        )

        cumulative_pnl = ZERO

        peak_cumulative_pnl = ZERO

        max_drawdown = ZERO

        points: list[
            EquityCurvePoint
        ] = []

        for index, trade in enumerate(
            ordered,
            start=1,
        ):
            cumulative_pnl += (
                trade.realized_pnl
            )

            if (
                cumulative_pnl
                > peak_cumulative_pnl
            ):
                peak_cumulative_pnl = (
                    cumulative_pnl
                )

            drawdown = (
                peak_cumulative_pnl
                - cumulative_pnl
            )

            if (
                drawdown
                > max_drawdown
            ):
                max_drawdown = (
                    drawdown
                )

            if starting_equity is None:
                equity_after_trade = None

            else:
                equity_after_trade = (
                    starting_equity
                    + cumulative_pnl
                )

            points.append(
                EquityCurvePoint(
                    trade_number=index,

                    trade_id=(
                        trade.trade_id
                    ),

                    closed_at_utc=(
                        trade.closed_at_utc
                    ),

                    realized_pnl=(
                        trade.realized_pnl
                    ),

                    cumulative_pnl=(
                        cumulative_pnl
                    ),

                    peak_cumulative_pnl=(
                        peak_cumulative_pnl
                    ),

                    drawdown=(
                        drawdown
                    ),

                    equity_after_trade=(
                        equity_after_trade
                    ),
                )
            )

        final_equity = None

        if starting_equity is not None:
            final_equity = (
                starting_equity
                + cumulative_pnl
            )

        return EquityCurve(
            starting_equity=(
                starting_equity
            ),

            points=tuple(
                points
            ),

            final_cumulative_pnl=(
                cumulative_pnl
            ),

            max_drawdown=(
                max_drawdown
            ),

            final_equity=(
                final_equity
            ),
        )

    @staticmethod
    def _validate_unique_trades(
        trades: tuple[
            TradeOutcome,
            ...,
        ],
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