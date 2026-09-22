from __future__ import annotations

from enum import Enum
from typing import Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class DecisionAction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"


class SetupQuality(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


EvidenceValue = Union[
    str,
    float,
    int,
    bool,
    None,
]


class EvidenceItem(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    context_path: str = Field(
        min_length=1,
        max_length=120,
    )

    value: EvidenceValue

    direction: EvidenceDirection

    interpretation: str = Field(
        min_length=1,
        max_length=500,
    )


class DecisionProposal(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    schema_version: str = "1.0"

    symbol: str

    action: DecisionAction

    setup_quality: SetupQuality

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    thesis: str = Field(
        min_length=1,
        max_length=1500,
    )

    evidence: list[EvidenceItem] = Field(
        min_length=1,
        max_length=10,
    )

    entry_price: float | None = Field(
        default=None,
        gt=0,
    )

    stop_loss: float | None = Field(
        default=None,
        gt=0,
    )

    take_profit: float | None = Field(
        default=None,
        gt=0,
    )

    invalidation_reason: str | None = Field(
        default=None,
        max_length=500,
    )

    no_trade_reason: str | None = Field(
        default=None,
        max_length=1000,
    )

    @model_validator(
        mode="after"
    )
    def validate_trade_logic(
        self,
    ):
        if (
            self.action
            == DecisionAction.NO_TRADE
        ):
            if any(
                value is not None
                for value in (
                    self.entry_price,
                    self.stop_loss,
                    self.take_profit,
                )
            ):
                raise ValueError(
                    "NO_TRADE must not contain "
                    "entry, stop-loss, or "
                    "take-profit prices."
                )

            if not self.no_trade_reason:
                raise ValueError(
                    "NO_TRADE requires "
                    "no_trade_reason."
                )

            return self

        if any(
            value is None
            for value in (
                self.entry_price,
                self.stop_loss,
                self.take_profit,
            )
        ):
            raise ValueError(
                "LONG/SHORT decisions require "
                "entry_price, stop_loss, "
                "and take_profit."
            )

        if not self.invalidation_reason:
            raise ValueError(
                "LONG/SHORT decisions require "
                "invalidation_reason."
            )

        if (
            self.action
            == DecisionAction.LONG
        ):
            if not (
                self.stop_loss
                < self.entry_price
                < self.take_profit
            ):
                raise ValueError(
                    "LONG requires "
                    "stop_loss < entry_price "
                    "< take_profit."
                )

        if (
            self.action
            == DecisionAction.SHORT
        ):
            if not (
                self.take_profit
                < self.entry_price
                < self.stop_loss
            ):
                raise ValueError(
                    "SHORT requires "
                    "take_profit < entry_price "
                    "< stop_loss."
                )

        return self