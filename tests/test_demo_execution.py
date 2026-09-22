from decimal import Decimal

import pytest

from approval.gate import (
    ManualApprovalGate,
)

from approval.schema import (
    ManualApprovalDecision,
)

from execution.bybit_demo import (
    BybitDemoExecutionClient,
)

from execution.request_builder import (
    DemoExecutionRequestBuilder,
)

from execution.schema import (
    ExecutionSide,
    ExecutionStatus,
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
            "86000.10"
        ),

        stop_loss=Decimal(
            "85000.00"
        ),

        take_profit=Decimal(
            "88000.00"
        ),

        risk_amount=Decimal(
            "50"
        ),

        stop_distance=Decimal(
            "1000.10"
        ),

        stop_distance_fraction=Decimal(
            "0.011629"
        ),

        reward_distance=Decimal(
            "1999.90"
        ),

        reward_risk_ratio=Decimal(
            "1.9997"
        ),

        raw_quantity=Decimal(
            "0.049995"
        ),

        executable_quantity=Decimal(
            "0.049"
        ),

        actual_risk_amount=Decimal(
            "49.0049"
        ),

        position_notional=Decimal(
            "4214.0049"
        ),

        required_margin=Decimal(
            "4214.0049"
        ),

        leverage=Decimal(
            "1"
        ),
    )


def make_approval():
    bridge = DecisionRiskBridgeResult(
        status=(
            RiskBridgeStatus
            .RISK_APPROVED
        ),

        risk_result=(
            RiskEvaluationResult(
                decision=(
                    RiskDecision.APPROVE
                ),

                reasons=(),

                plan=make_plan(),
            )
        ),

        no_trade_reason=None,
    )

    gate = ManualApprovalGate()

    request = gate.create_request(
        bridge
    )

    result = gate.record_decision(
        request=request,

        decision=(
            ManualApprovalDecision
            .APPROVE
        ),
    )

    return request, result


class FakeSession:
    def __init__(self):
        self.leverage_kwargs = None
        self.order_kwargs = None

    def set_leverage(
        self,
        **kwargs,
    ):
        self.leverage_kwargs = kwargs

        return {
            "retCode": 0,
            "retMsg": "OK",
            "result": {},
        }

    def place_order(
        self,
        **kwargs,
    ):
        self.order_kwargs = kwargs

        return {
            "retCode": 0,
            "retMsg": "OK",

            "result": {
                "orderId": "order-123",

                "orderLinkId": (
                    kwargs[
                        "orderLinkId"
                    ]
                ),
            },
        }


def test_builder_maps_approved_long():
    approval_request, approval_result = (
        make_approval()
    )

    request = (
        DemoExecutionRequestBuilder()
        .build(
            approval_request,
            approval_result,
        )
    )

    assert (
        request.side
        == ExecutionSide.BUY
    )

    assert (
        request.quantity
        == Decimal("0.049")
    )

    assert (
        request.entry_price
        == Decimal("86000.10")
    )


def test_order_link_id_is_deterministic():
    approval_request, approval_result = (
        make_approval()
    )

    builder = (
        DemoExecutionRequestBuilder()
    )

    first = builder.build(
        approval_request,
        approval_result,
    )

    second = builder.build(
        approval_request,
        approval_result,
    )

    assert (
        first.order_link_id
        == second.order_link_id
    )

    assert (
        len(first.order_link_id)
        <= 36
    )


def test_manual_rejection_blocks_execution():
    approval_request, _ = (
        make_approval()
    )

    gate = ManualApprovalGate()

    rejected = gate.record_decision(
        request=approval_request,

        decision=(
            ManualApprovalDecision
            .REJECT
        ),
    )

    with pytest.raises(
        RuntimeError
    ):
        (
            DemoExecutionRequestBuilder()
            .build(
                approval_request,
                rejected,
            )
        )


def test_mismatched_approval_id_blocked():
    approval_request, approval_result = (
        make_approval()
    )

    bad_result = (
        approval_result.model_copy(
            update={
                "approval_id":
                "different-id"
            }
        )
    )

    with pytest.raises(
        RuntimeError
    ):
        (
            DemoExecutionRequestBuilder()
            .build(
                approval_request,
                bad_result,
            )
        )


def test_demo_order_submission():
    approval_request, approval_result = (
        make_approval()
    )

    request = (
        DemoExecutionRequestBuilder()
        .build(
            approval_request,
            approval_result,
        )
    )

    session = FakeSession()

    client = BybitDemoExecutionClient(
        api_key="test-key",
        api_secret="test-secret",
        session=session,
    )

    ack = client.submit(
        request
    )

    assert (
        ack.status
        == ExecutionStatus
        .ACKNOWLEDGED
    )

    assert (
        ack.order_id
        == "order-123"
    )

    assert (
        ack.order_link_id
        == request.order_link_id
    )

    assert ack.leverage_changed is True

    assert (
        session.leverage_kwargs[
            "buyLeverage"
        ]
        == "1"
    )

    assert (
        session.leverage_kwargs[
            "sellLeverage"
        ]
        == "1"
    )

    order = session.order_kwargs

    assert (
        order["category"]
        == "linear"
    )

    assert (
        order["side"]
        == "Buy"
    )

    assert (
        order["orderType"]
        == "Limit"
    )

    assert (
        order["qty"]
        == "0.049"
    )

    assert (
        order["price"]
        == "86000.10"
    )

    assert (
        order["positionIdx"]
        == 0
    )

    assert (
        order["reduceOnly"]
        is False
    )

    assert (
        order["takeProfit"]
        == "88000.00"
    )

    assert (
        order["stopLoss"]
        == "85000.00"
    )


class UnchangedLeverageSession(
    FakeSession
):
    def set_leverage(
        self,
        **kwargs,
    ):
        self.leverage_kwargs = kwargs

        return {
            "retCode": 110043,

            "retMsg": (
                "Set leverage has "
                "not been modified"
            ),

            "result": {},
        }


def test_unchanged_leverage_is_allowed():
    approval_request, approval_result = (
        make_approval()
    )

    request = (
        DemoExecutionRequestBuilder()
        .build(
            approval_request,
            approval_result,
        )
    )

    client = BybitDemoExecutionClient(
        api_key="test-key",
        api_secret="test-secret",
        session=(
            UnchangedLeverageSession()
        ),
    )

    ack = client.submit(
        request
    )

    assert (
        ack.status
        == ExecutionStatus
        .ACKNOWLEDGED
    )

    assert (
        ack.leverage_changed
        is False
    )


class OrderErrorSession(
    FakeSession
):
    def place_order(
        self,
        **kwargs,
    ):
        return {
            "retCode": 10001,
            "retMsg": "order error",
        }


def test_order_error_fails_closed():
    approval_request, approval_result = (
        make_approval()
    )

    request = (
        DemoExecutionRequestBuilder()
        .build(
            approval_request,
            approval_result,
        )
    )

    client = BybitDemoExecutionClient(
        api_key="test-key",
        api_secret="test-secret",
        session=OrderErrorSession(),
    )

    with pytest.raises(
        RuntimeError
    ):
        client.submit(
            request
        )


class WrongLinkIdSession(
    FakeSession
):
    def place_order(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,
            "retMsg": "OK",

            "result": {
                "orderId": "order-123",
                "orderLinkId": "wrong-id",
            },
        }


def test_wrong_returned_link_id_fails():
    approval_request, approval_result = (
        make_approval()
    )

    request = (
        DemoExecutionRequestBuilder()
        .build(
            approval_request,
            approval_result,
        )
    )

    client = BybitDemoExecutionClient(
        api_key="test-key",
        api_secret="test-secret",
        session=(
            WrongLinkIdSession()
        ),
    )

    with pytest.raises(
        RuntimeError
    ):
        client.submit(
            request
        )