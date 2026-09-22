from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from uuid import uuid4

from approval.schema import (
    ManualApprovalDecision,
    ManualApprovalRequest,
    ManualApprovalResult,
)

from risk_manager.bridge import (
    DecisionRiskBridgeResult,
    RiskBridgeStatus,
)


class ManualApprovalGate:
    def create_request(
        self,
        bridge_result:
        DecisionRiskBridgeResult,
    ) -> ManualApprovalRequest:

        if (
            bridge_result.status
            != RiskBridgeStatus
            .RISK_APPROVED
        ):
            raise RuntimeError(
                "Manual approval can only "
                "be requested for a "
                "RISK_APPROVED proposal."
            )

        if (
            bridge_result.risk_result
            is None
            or bridge_result
            .risk_result.plan
            is None
        ):
            raise RuntimeError(
                "Approved risk plan "
                "is missing."
            )

        return ManualApprovalRequest(
            approval_id=uuid4().hex,

            created_at_utc=datetime.now(
                timezone.utc
            ),

            risk_plan=(
                bridge_result
                .risk_result
                .plan
            ),
        )

    def record_decision(
        self,
        request:
        ManualApprovalRequest,

        decision:
        ManualApprovalDecision,

        note: str | None = None,
    ) -> ManualApprovalResult:

        return ManualApprovalResult(
            approval_id=(
                request.approval_id
            ),

            decision=decision,

            decided_at_utc=datetime.now(
                timezone.utc
            ),

            note=note,
        )