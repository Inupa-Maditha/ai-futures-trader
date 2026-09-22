from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class TradeSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class TradeExitReason(str, Enum):
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    MANUAL = "MANUAL"
    OTHER = "OTHER"


class TradeOutcome(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    trade_id: str = Field(
        min_length=1
    )

    run_id: str = Field(
        min_length=1
    )

    symbol: str = Field(
        min_length=1
    )

    side: TradeSide

    opened_at_utc: datetime

    closed_at_utc: datetime

    entry_price: Decimal = Field(
        gt=0
    )

    exit_price: Decimal = Field(
        gt=0
    )

    quantity: Decimal = Field(
        gt=0
    )

    initial_risk_amount: Decimal = Field(
        gt=0
    )

    realized_pnl: Decimal

    exit_reason: TradeExitReason

    @model_validator(
        mode="after"
    )
    def validate_outcome(
        self,
    ):
        for field_name in (
            "opened_at_utc",
            "closed_at_utc",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise ValueError(
                    f"{field_name} must be "
                    "timezone-aware."
                )

            setattr(
                self,
                field_name,
                value.astimezone(
                    timezone.utc
                ),
            )

        if (
            self.closed_at_utc
            <= self.opened_at_utc
        ):
            raise ValueError(
                "closed_at_utc must be "
                "later than opened_at_utc."
            )

        return self

    @property
    def r_multiple(
        self,
    ) -> Decimal:
        return (
            self.realized_pnl
            / self.initial_risk_amount
        )

    @property
    def is_win(
        self,
    ) -> bool:
        return self.realized_pnl > 0

    @property
    def is_loss(
        self,
    ) -> bool:
        return self.realized_pnl < 0

    @property
    def is_breakeven(
        self,
    ) -> bool:
        return self.realized_pnl == 0