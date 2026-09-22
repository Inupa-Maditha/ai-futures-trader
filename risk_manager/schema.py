from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class RiskSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class RiskDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class RiskEvaluationInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    symbol: str
    side: RiskSide

    entry_price: Decimal = Field(gt=0)
    stop_loss: Decimal = Field(gt=0)
    take_profit: Decimal = Field(gt=0)

    account_equity: Decimal = Field(gt=0)
    available_balance: Decimal = Field(ge=0)

    open_position_count: int = Field(ge=0)

    daily_realized_pnl: Decimal = Decimal("0")

    @model_validator(mode="after")
    def validate_price_structure(self):
        if self.side == RiskSide.LONG:
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

        if self.side == RiskSide.SHORT:
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


class ApprovedRiskPlan(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    symbol: str
    side: RiskSide

    # Exchange-aligned prices.
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal

    # Maximum configured risk budget.
    risk_amount: Decimal

    stop_distance: Decimal
    stop_distance_fraction: Decimal

    reward_distance: Decimal
    reward_risk_ratio: Decimal

    # Quantity before exchange rounding.
    raw_quantity: Decimal

    # Final exchange-safe BTC quantity.
    executable_quantity: Decimal

    # Actual risk after quantity rounding.
    actual_risk_amount: Decimal

    position_notional: Decimal

    required_margin: Decimal

    # Exchange-step-aligned leverage.
    leverage: Decimal


class RiskEvaluationResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    decision: RiskDecision

    reasons: tuple[str, ...]

    plan: ApprovedRiskPlan | None = None

    @model_validator(mode="after")
    def validate_result(self):
        if (
            self.decision
            == RiskDecision.APPROVE
            and self.plan is None
        ):
            raise ValueError(
                "APPROVE requires an "
                "ApprovedRiskPlan."
            )

        if (
            self.decision
            == RiskDecision.REJECT
            and self.plan is not None
        ):
            raise ValueError(
                "REJECT must not contain "
                "an ApprovedRiskPlan."
            )

        if (
            self.decision
            == RiskDecision.REJECT
            and not self.reasons
        ):
            raise ValueError(
                "REJECT requires at least "
                "one reason."
            )

        return self