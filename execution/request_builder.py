from __future__ import annotations

import hashlib

from approval.schema import (
    ManualApprovalDecision,
    ManualApprovalRequest,
    ManualApprovalResult,
)

from execution.schema import (
    DemoExecutionRequest,
    ExecutionSide,
)

from risk_manager.schema import (
    RiskSide,
)


class DemoExecutionRequestBuilder:
    def build(
        self,
        approval_request:
        ManualApprovalRequest,

        approval_result:
        ManualApprovalResult,
    ) -> DemoExecutionRequest:

        if (
            approval_result.decision
            != ManualApprovalDecision.APPROVE
        ):
            raise RuntimeError(
                "Execution requires explicit "
                "manual APPROVE."
            )

        if (
            approval_result.approval_id
            != approval_request.approval_id
        ):
            raise RuntimeError(
                "Approval result does not "
                "match approval request."
            )

        plan = (
            approval_request.risk_plan
        )

        if plan.side == RiskSide.LONG:
            side = ExecutionSide.BUY

        elif plan.side == RiskSide.SHORT:
            side = ExecutionSide.SELL

        else:
            raise RuntimeError(
                "Unsupported risk-plan side."
            )

        return DemoExecutionRequest(
            approval_id=(
                approval_request.approval_id
            ),

            order_link_id=(
                self._build_order_link_id(
                    approval_request
                    .approval_id
                )
            ),

            symbol=plan.symbol,

            side=side,

            quantity=(
                plan.executable_quantity
            ),

            entry_price=(
                plan.entry_price
            ),

            stop_loss=(
                plan.stop_loss
            ),

            take_profit=(
                plan.take_profit
            ),

            leverage=(
                plan.leverage
            ),
        )

    @staticmethod
    def _build_order_link_id(
        approval_id: str,
    ) -> str:
        digest = hashlib.sha256(
            approval_id.encode(
                "utf-8"
            )
        ).hexdigest()[:24]

        # 31 characters total.
        #
        # Same approval ID always creates
        # the same exchange orderLinkId.
        return (
            f"aft-v1-{digest}"
        )