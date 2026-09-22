from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class ExecutionSide(str, Enum):
    BUY = "Buy"
    SELL = "Sell"


class ExecutionStatus(str, Enum):
    ACKNOWLEDGED = "ACKNOWLEDGED"


class DemoExecutionRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    approval_id: str = Field(
        min_length=1
    )

    order_link_id: str = Field(
        min_length=1,
        max_length=36,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    symbol: str

    side: ExecutionSide

    quantity: Decimal = Field(
        gt=0
    )

    entry_price: Decimal = Field(
        gt=0
    )

    stop_loss: Decimal = Field(
        gt=0
    )

    take_profit: Decimal = Field(
        gt=0
    )

    leverage: Decimal = Field(
        ge=1
    )

    @model_validator(
        mode="after"
    )
    def validate_price_structure(self):
        if self.side == ExecutionSide.BUY:
            if not (
                self.stop_loss
                < self.entry_price
                < self.take_profit
            ):
                raise ValueError(
                    "BUY requires "
                    "stop_loss < entry_price "
                    "< take_profit."
                )

        if self.side == ExecutionSide.SELL:
            if not (
                self.take_profit
                < self.entry_price
                < self.stop_loss
            ):
                raise ValueError(
                    "SELL requires "
                    "take_profit < entry_price "
                    "< stop_loss."
                )

        return self


class DemoExecutionAck(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    status: ExecutionStatus

    approval_id: str

    order_id: str = Field(
        min_length=1
    )

    order_link_id: str = Field(
        min_length=1
    )

    symbol: str

    side: ExecutionSide

    quantity: Decimal

    leverage: Decimal

    leverage_changed: bool