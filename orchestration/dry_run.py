from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from decision_engine.llm_service import (
    LLMDecisionService,
)

from risk_manager.account_state_provider import (
    DemoRiskStateProvider,
)

from risk_manager.bridge import (
    DecisionRiskBridge,
    DecisionRiskBridgeResult,
    RiskBridgeStatus,
)


class DryRunStatus(str, Enum):
    DECISION_REJECTED = (
        "DECISION_REJECTED"
    )

    NO_TRADE = "NO_TRADE"

    RISK_REJECTED = "RISK_REJECTED"

    RISK_APPROVED = "RISK_APPROVED"


@dataclass(
    frozen=True,
    slots=True,
)
class DryRunResult:
    status: DryRunStatus

    decision_result: object

    risk_bridge_result: (
        DecisionRiskBridgeResult | None
    )

    error: str | None


class TradingDryRun:
    def __init__(
        self,
        decision_service:
        LLMDecisionService,

        account_state_provider:
        DemoRiskStateProvider,

        risk_bridge:
        DecisionRiskBridge,
    ):
        self.decision_service = (
            decision_service
        )

        self.account_state_provider = (
            account_state_provider
        )

        self.risk_bridge = (
            risk_bridge
        )

    def run(
        self,
        context,
    ) -> DryRunResult:

        # -----------------------------------------
        # 1. LLM decision layer
        # -----------------------------------------

        decision_result = (
            self.decision_service.decide(
                context
            )
        )

        if (
            not decision_result.accepted
            or decision_result.proposal
            is None
        ):
            return DryRunResult(
                status=(
                    DryRunStatus
                    .DECISION_REJECTED
                ),

                decision_result=(
                    decision_result
                ),

                risk_bridge_result=None,

                error=(
                    decision_result.error
                    or
                    "Decision proposal "
                    "was rejected."
                ),
            )

        proposal = (
            decision_result.proposal
        )

        # -----------------------------------------
        # 2. NO_TRADE
        #
        # Let bridge process it so the same
        # boundary remains tested.
        # Account data is intentionally NOT
        # fetched for NO_TRADE.
        # -----------------------------------------

        if (
            proposal.action.value
            == "NO_TRADE"
        ):
            bridge_result = (
                self.risk_bridge.evaluate(
                    proposal=proposal,

                    account=(
                        self._dummy_account_not_used()
                    ),
                )
            )

            return DryRunResult(
                status=(
                    DryRunStatus.NO_TRADE
                ),

                decision_result=(
                    decision_result
                ),

                risk_bridge_result=(
                    bridge_result
                ),

                error=None,
            )

        # -----------------------------------------
        # 3. LONG / SHORT:
        #    fetch live Demo risk state
        # -----------------------------------------

        account_state = (
            self.account_state_provider
            .get_state(
                proposal.symbol
            )
        )

        # -----------------------------------------
        # 4. Deterministic risk authority
        # -----------------------------------------

        bridge_result = (
            self.risk_bridge.evaluate(
                proposal=proposal,
                account=account_state,
            )
        )

        if (
            bridge_result.status
            == RiskBridgeStatus
            .RISK_APPROVED
        ):
            status = (
                DryRunStatus.RISK_APPROVED
            )

        else:
            status = (
                DryRunStatus.RISK_REJECTED
            )

        return DryRunResult(
            status=status,

            decision_result=(
                decision_result
            ),

            risk_bridge_result=(
                bridge_result
            ),

            error=None,
        )

    @staticmethod
    def _dummy_account_not_used():
        # Imported locally so NO_TRADE
        # remains clearly isolated from
        # account-state retrieval.
        from decimal import Decimal

        from risk_manager.bridge import (
            AccountRiskState,
        )

        return AccountRiskState(
            account_equity=Decimal("1"),

            available_balance=(
                Decimal("0")
            ),

            open_position_count=0,

            daily_realized_pnl=(
                Decimal("0")
            ),
        )