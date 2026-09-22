from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest

from approval.gate import (
    ManualApprovalGate,
)

from approval.schema import (
    ManualApprovalDecision,
)

from risk_manager.bridge import (
    DecisionRiskBridgeResult,
    RiskBridgeStatus,
)

from risk_manager.schema import (
    ApprovedRiskPlan,
    RiskDecision,
    RiskEvaluationResult,
    RiskSide,
)


def make_plan():
    return ApprovedRiskPlan(
        symbol="BTCUSDT",

        side=RiskSide.LONG,

        entry_price=Decimal(
            "86000"
        ),

        stop_loss=Decimal(
            "85000"
        ),

        take_profit=Decimal(
            "88000"
        ),

        risk_amount=Decimal(
            "50"
        ),

        stop_distance=Decimal(
            "1000"
        ),

        stop_distance_fraction=Decimal(
            "0.0116279"
        ),

        reward_distance=Decimal(
            "2000"
        ),

        reward_risk_ratio=Decimal(
            "2"
        ),

        raw_quantity=Decimal(
            "0.05"
        ),

        executable_quantity=Decimal(
            "0.050"
        ),

        actual_risk_amount=Decimal(
            "50"
        ),

        position_notional=Decimal(
            "4300"
        ),

        required_margin=Decimal(
            "4300"
        ),

        leverage=Decimal(
            "1"
        ),
    )


def make_approved_bridge():
    risk_result = (
        RiskEvaluationResult(
            decision=(
                RiskDecision.APPROVE
            ),

            reasons=(),

            plan=make_plan(),
        )
    )

    return DecisionRiskBridgeResult(
        status=(
            RiskBridgeStatus
            .RISK_APPROVED
        ),

        risk_result=risk_result,

        no_trade_reason=None,
    )


def test_create_manual_approval_request():
    gate = ManualApprovalGate()

    request = gate.create_request(
        make_approved_bridge()
    )

    assert request.approval_id

    assert (
        request.risk_plan.symbol
        == "BTCUSDT"
    )

    assert (
        request.created_at_utc.tzinfo
        is not None
    )


def test_manual_approve():
    gate = ManualApprovalGate()

    request = gate.create_request(
        make_approved_bridge()
    )

    result = gate.record_decision(
        request=request,

        decision=(
            ManualApprovalDecision.APPROVE
        ),
    )

    assert (
        result.decision
        == ManualApprovalDecision.APPROVE
    )

    assert (
        result.approval_id
        == request.approval_id
    )


def test_manual_reject():
    gate = ManualApprovalGate()

    request = gate.create_request(
        make_approved_bridge()
    )

    result = gate.record_decision(
        request=request,

        decision=(
            ManualApprovalDecision.REJECT
        ),
    )

    assert (
        result.decision
        == ManualApprovalDecision.REJECT
    )


def test_risk_rejected_cannot_request_approval():
    bridge = DecisionRiskBridgeResult(
        status=(
            RiskBridgeStatus
            .RISK_REJECTED
        ),

        risk_result=(
            RiskEvaluationResult(
                decision=(
                    RiskDecision.REJECT
                ),

                reasons=(
                    "Test rejection.",
                ),

                plan=None,
            )
        ),

        no_trade_reason=None,
    )

    with pytest.raises(
        RuntimeError
    ):
        (
            ManualApprovalGate()
            .create_request(
                bridge
            )
        )


def test_no_trade_cannot_request_approval():
    bridge = DecisionRiskBridgeResult(
        status=(
            RiskBridgeStatus.NO_TRADE
        ),

        risk_result=None,

        no_trade_reason=(
            "No trade."
        ),
    )

    with pytest.raises(
        RuntimeError
    ):
        (
            ManualApprovalGate()
            .create_request(
                bridge
            )
        )