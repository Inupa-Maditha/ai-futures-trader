from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from decision_engine.schema import (
    DecisionAction,
    DecisionProposal,
)

from risk_manager.engine import (
    DeterministicRiskEngine,
)

from risk_manager.schema import (
    RiskDecision,
    RiskEvaluationInput,
    RiskEvaluationResult,
    RiskSide,
)


class RiskBridgeStatus(str, Enum):
    NO_TRADE = "NO_TRADE"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"


class AccountRiskState(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    account_equity: Decimal = Field(
        gt=0
    )

    available_balance: Decimal = Field(
        ge=0
    )

    open_position_count: int = Field(
        ge=0
    )

    daily_realized_pnl: Decimal = Decimal(
        "0"
    )


class DecisionRiskBridgeResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    status: RiskBridgeStatus

    risk_result: (
        RiskEvaluationResult | None
    ) = None

    no_trade_reason: (
        str | None
    ) = None

    @model_validator(
        mode="after"
    )
    def validate_result(self):
        if (
            self.status
            == RiskBridgeStatus.NO_TRADE
        ):
            if self.risk_result is not None:
                raise ValueError(
                    "NO_TRADE must not contain "
                    "a risk evaluation result."
                )

            if not self.no_trade_reason:
                raise ValueError(
                    "NO_TRADE requires "
                    "a no_trade_reason."
                )

            return self

        if self.no_trade_reason is not None:
            raise ValueError(
                "Risk-evaluated decisions "
                "must not contain "
                "no_trade_reason."
            )

        if self.risk_result is None:
            raise ValueError(
                "Risk-evaluated decisions "
                "require a risk_result."
            )

        if (
            self.status
            == RiskBridgeStatus.RISK_APPROVED
            and self.risk_result.decision
            != RiskDecision.APPROVE
        ):
            raise ValueError(
                "RISK_APPROVED requires "
                "an approved risk result."
            )

        if (
            self.status
            == RiskBridgeStatus.RISK_REJECTED
            and self.risk_result.decision
            != RiskDecision.REJECT
        ):
            raise ValueError(
                "RISK_REJECTED requires "
                "a rejected risk result."
            )

        return self


class DecisionRiskBridge:
    def __init__(
        self,
        risk_engine: DeterministicRiskEngine,
    ):
        self.risk_engine = risk_engine

    def evaluate(
        self,
        proposal: DecisionProposal,
        account: AccountRiskState,
    ) -> DecisionRiskBridgeResult:

        # -----------------------------------------
        # 1. NO_TRADE never enters risk sizing
        # -----------------------------------------

        if (
            proposal.action
            == DecisionAction.NO_TRADE
        ):
            return DecisionRiskBridgeResult(
                status=RiskBridgeStatus.NO_TRADE,
                risk_result=None,
                no_trade_reason=(
                    proposal.no_trade_reason
                ),
            )

        # -----------------------------------------
        # 2. Fail closed if trade prices
        #    somehow do not exist.
        #
        # DecisionProposal already validates this,
        # but keep this boundary defensive.
        # -----------------------------------------

        if (
            proposal.entry_price is None
            or proposal.stop_loss is None
            or proposal.take_profit is None
        ):
            raise ValueError(
                "Trade proposal is missing "
                "entry, stop loss, or "
                "take profit."
            )

        # -----------------------------------------
        # 3. Map LLM action to deterministic side
        # -----------------------------------------

        if (
            proposal.action
            == DecisionAction.LONG
        ):
            side = RiskSide.LONG

        elif (
            proposal.action
            == DecisionAction.SHORT
        ):
            side = RiskSide.SHORT

        else:
            raise ValueError(
                "Unsupported decision action."
            )

        # -----------------------------------------
        # 4. Build deterministic risk input
        #
        # IMPORTANT:
        # Decimal(str(...)), never Decimal(float).
        # -----------------------------------------

        risk_input = RiskEvaluationInput(
            symbol=proposal.symbol,
            side=side,

            entry_price=Decimal(
                str(proposal.entry_price)
            ),

            stop_loss=Decimal(
                str(proposal.stop_loss)
            ),

            take_profit=Decimal(
                str(proposal.take_profit)
            ),

            account_equity=(
                account.account_equity
            ),

            available_balance=(
                account.available_balance
            ),

            open_position_count=(
                account.open_position_count
            ),

            daily_realized_pnl=(
                account.daily_realized_pnl
            ),
        )

        # -----------------------------------------
        # 5. Deterministic authority
        # -----------------------------------------

        risk_result = (
            self.risk_engine.evaluate(
                risk_input
            )
        )

        if (
            risk_result.decision
            == RiskDecision.APPROVE
        ):
            status = (
                RiskBridgeStatus
                .RISK_APPROVED
            )

        else:
            status = (
                RiskBridgeStatus
                .RISK_REJECTED
            )

        return DecisionRiskBridgeResult(
            status=status,
            risk_result=risk_result,
            no_trade_reason=None,
        )