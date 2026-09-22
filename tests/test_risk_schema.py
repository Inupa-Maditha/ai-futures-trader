from decimal import Decimal

import pytest

from pydantic import ValidationError

from risk_manager.policy import (
    RiskPolicy,
)

from risk_manager.schema import (
    ApprovedRiskPlan,
    RiskDecision,
    RiskEvaluationInput,
    RiskEvaluationResult,
    RiskSide,
)


def test_default_policy_is_valid():
    policy = RiskPolicy()

    assert (
        policy.risk_per_trade_fraction
        == Decimal("0.005")
    )

    assert (
        policy.minimum_reward_risk
        == Decimal("1.5")
    )

    assert (
        policy.max_leverage
        == Decimal("3")
    )


def test_invalid_policy_rejected():
    with pytest.raises(ValueError):
        RiskPolicy(
            risk_per_trade_fraction=Decimal(
                "1.5"
            )
        )


def test_valid_long_input():
    data = RiskEvaluationInput(
        symbol="BTCUSDT",
        side=RiskSide.LONG,
        entry_price=Decimal("86000"),
        stop_loss=Decimal("85000"),
        take_profit=Decimal("88000"),
        account_equity=Decimal("10000"),
        available_balance=Decimal("9000"),
        open_position_count=0,
    )

    assert data.side == RiskSide.LONG


def test_valid_short_input():
    data = RiskEvaluationInput(
        symbol="BTCUSDT",
        side=RiskSide.SHORT,
        entry_price=Decimal("86000"),
        stop_loss=Decimal("87000"),
        take_profit=Decimal("84000"),
        account_equity=Decimal("10000"),
        available_balance=Decimal("9000"),
        open_position_count=0,
    )

    assert data.side == RiskSide.SHORT


def test_invalid_long_price_structure():
    with pytest.raises(
        ValidationError
    ):
        RiskEvaluationInput(
            symbol="BTCUSDT",
            side=RiskSide.LONG,
            entry_price=Decimal("86000"),
            stop_loss=Decimal("87000"),
            take_profit=Decimal("88000"),
            account_equity=Decimal("10000"),
            available_balance=Decimal("9000"),
            open_position_count=0,
        )


def make_plan():
    return ApprovedRiskPlan(
        symbol="BTCUSDT",
        side=RiskSide.LONG,
        entry_price=Decimal("86000"),
        stop_loss=Decimal("85000"),
        take_profit=Decimal("88000"),
        risk_amount=Decimal("50"),
        stop_distance=Decimal("1000"),
        stop_distance_fraction=Decimal(
            "0.0116279"
        ),
        reward_distance=Decimal("2000"),
        reward_risk_ratio=Decimal("2"),
        raw_quantity=Decimal("0.05"),
        executable_quantity=Decimal("0.05"),
        actual_risk_amount=Decimal("50"),
        position_notional=Decimal("4300"),
        required_margin=Decimal(
            "1433.333333"
        ),
        leverage=Decimal("3"),
    )


def test_approve_requires_plan():
    with pytest.raises(
        ValidationError
    ):
        RiskEvaluationResult(
            decision=RiskDecision.APPROVE,
            reasons=(),
            plan=None,
        )


def test_reject_cannot_have_plan():
    with pytest.raises(
        ValidationError
    ):
        RiskEvaluationResult(
            decision=RiskDecision.REJECT,
            reasons=("Rejected.",),
            plan=make_plan(),
        )


def test_valid_approved_result():
    result = RiskEvaluationResult(
        decision=RiskDecision.APPROVE,
        reasons=(),
        plan=make_plan(),
    )

    assert (
        result.decision
        == RiskDecision.APPROVE
    )


def test_valid_rejected_result():
    result = RiskEvaluationResult(
        decision=RiskDecision.REJECT,
        reasons=(
            "Reward-risk ratio too low.",
        ),
        plan=None,
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )