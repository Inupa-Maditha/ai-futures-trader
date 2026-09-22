from decimal import Decimal

from risk_manager.engine import (
    DeterministicRiskEngine,
)

from risk_manager.instrument_rules import (
    InstrumentRules,
)

from risk_manager.schema import (
    RiskDecision,
    RiskEvaluationInput,
    RiskSide,
)


def make_rules():
    return InstrumentRules(
        symbol="BTCUSDT",
        status="Trading",
        contract_type="LinearPerpetual",

        tick_size=Decimal("0.10"),

        min_price=Decimal("0.10"),
        max_price=Decimal("1999999.80"),

        qty_step=Decimal("0.001"),

        min_order_qty=Decimal("0.001"),

        max_order_qty=Decimal("1500"),

        max_market_order_qty=Decimal(
            "150"
        ),

        min_notional_value=Decimal("5"),

        min_leverage=Decimal("1"),

        max_leverage=Decimal("150"),

        leverage_step=Decimal("0.01"),
    )


def make_engine():
    return DeterministicRiskEngine(
        instrument_rules=make_rules()
    )


def make_long_input(
    *,
    entry: str = "86000",
    stop: str = "85000",
    target: str = "88000",
    equity: str = "10000",
    balance: str = "10000",
    open_positions: int = 0,
    daily_pnl: str = "0",
):
    return RiskEvaluationInput(
        symbol="BTCUSDT",
        side=RiskSide.LONG,

        entry_price=Decimal(entry),
        stop_loss=Decimal(stop),
        take_profit=Decimal(target),

        account_equity=Decimal(equity),
        available_balance=Decimal(
            balance
        ),

        open_position_count=(
            open_positions
        ),

        daily_realized_pnl=Decimal(
            daily_pnl
        ),
    )


def make_short_input():
    return RiskEvaluationInput(
        symbol="BTCUSDT",
        side=RiskSide.SHORT,

        entry_price=Decimal("86000"),
        stop_loss=Decimal("87000"),
        take_profit=Decimal("84000"),

        account_equity=Decimal("10000"),

        available_balance=Decimal(
            "10000"
        ),

        open_position_count=0,

        daily_realized_pnl=Decimal(
            "0"
        ),
    )


def test_valid_long_is_approved():
    result = (
        make_engine()
        .evaluate(
            make_long_input()
        )
    )

    assert (
        result.decision
        == RiskDecision.APPROVE
    )

    assert result.plan is not None


def test_long_position_size_is_correct():
    result = (
        make_engine()
        .evaluate(
            make_long_input()
        )
    )

    plan = result.plan

    assert plan is not None

    assert (
        plan.risk_amount
        == Decimal("50")
    )

    assert (
        plan.stop_distance
        == Decimal("1000")
    )

    assert (
        plan.raw_quantity
        == Decimal("0.05")
    )

    assert (
        plan.executable_quantity
        == Decimal("0.050")
    )

    assert (
        plan.actual_risk_amount
        == Decimal("50")
    )

    assert (
        plan.position_notional
        == Decimal("4300")
    )


def test_reward_risk_is_correct():
    result = (
        make_engine()
        .evaluate(
            make_long_input()
        )
    )

    assert result.plan is not None

    assert (
        result.plan.reward_risk_ratio
        == Decimal("2")
    )


def test_valid_short_is_approved():
    result = (
        make_engine()
        .evaluate(
            make_short_input()
        )
    )

    assert (
        result.decision
        == RiskDecision.APPROVE
    )


def test_low_reward_risk_is_rejected():
    result = (
        make_engine()
        .evaluate(
            make_long_input(
                target="87000",
            )
        )
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "Reward-risk ratio"
        in reason
        for reason in result.reasons
    )


def test_stop_too_tight_is_rejected():
    result = (
        make_engine()
        .evaluate(
            make_long_input(
                stop="85950",
                target="86200",
            )
        )
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "minimum allowed distance"
        in reason
        for reason in result.reasons
    )


def test_stop_too_wide_is_rejected():
    result = (
        make_engine()
        .evaluate(
            make_long_input(
                stop="83000",
                target="92000",
            )
        )
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "maximum allowed distance"
        in reason
        for reason in result.reasons
    )


def test_existing_position_rejected():
    result = (
        make_engine()
        .evaluate(
            make_long_input(
                open_positions=1,
            )
        )
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "open-position"
        in reason
        for reason in result.reasons
    )


def test_daily_loss_limit_rejected():
    result = (
        make_engine()
        .evaluate(
            make_long_input(
                daily_pnl="-200",
            )
        )
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "Daily loss limit"
        in reason
        for reason in result.reasons
    )


def test_remaining_daily_budget_rejected():
    # Daily loss limit:
    #
    # $10,000 * 2% = $200
    #
    # Already lost:
    # $175
    #
    # Remaining:
    # $25
    #
    # New trade risk:
    # $50

    result = (
        make_engine()
        .evaluate(
            make_long_input(
                daily_pnl="-175",
            )
        )
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "remaining daily"
        in reason
        for reason in result.reasons
    )


def test_zero_available_balance_rejected():
    result = (
        make_engine()
        .evaluate(
            make_long_input(
                balance="0",
            )
        )
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "Available balance is zero"
        in reason
        for reason in result.reasons
    )


def test_excessive_leverage_rejected():
    # Position notional is around $4300.
    #
    # Available balance = $1000
    #
    # Required leverage ~= 4.3x
    #
    # Risk policy max = 3x.

    result = (
        make_engine()
        .evaluate(
            make_long_input(
                balance="1000",
            )
        )
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "risk-policy leverage"
        in reason
        for reason in result.reasons
    )