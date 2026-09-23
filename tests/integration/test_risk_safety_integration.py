from __future__ import annotations

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


def d(
    value: str,
) -> Decimal:
    return Decimal(value)


# =========================================================
# Shared helpers
# =========================================================


def make_rules(
    **overrides,
) -> InstrumentRules:

    values = {
        "symbol": "BTCUSDT",

        "status": "Trading",

        "contract_type":
        "LinearPerpetual",

        "tick_size":
        d("0.10"),

        "min_price":
        d("0.10"),

        "max_price":
        d("2000000"),

        "qty_step":
        d("0.001"),

        "min_order_qty":
        d("0.001"),

        "max_order_qty":
        d("100"),

        "max_market_order_qty":
        d("100"),

        "min_notional_value":
        d("5"),

        "min_leverage":
        d("1"),

        "max_leverage":
        d("100"),

        "leverage_step":
        d("0.01"),
    }

    values.update(
        overrides
    )

    return InstrumentRules(
        **values
    )


def make_engine(
    **rule_overrides,
) -> DeterministicRiskEngine:

    return (
        DeterministicRiskEngine(
            instrument_rules=(
                make_rules(
                    **rule_overrides
                )
            )
        )
    )


def make_long_input(
    *,
    entry=d("85000"),
    stop=d("84000"),
    target=d("87000"),
    equity=d("10000"),
    balance=d("10000"),
    open_positions=0,
    daily_pnl=d("0"),
) -> RiskEvaluationInput:

    return RiskEvaluationInput(
        symbol="BTCUSDT",

        side=RiskSide.LONG,

        entry_price=entry,

        stop_loss=stop,

        take_profit=target,

        account_equity=equity,

        available_balance=balance,

        open_position_count=(
            open_positions
        ),

        daily_realized_pnl=(
            daily_pnl
        ),
    )


def assert_rejected(
    result,
    expected_reason: str,
):
    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert result.plan is None

    assert any(
        expected_reason
        in reason
        for reason in result.reasons
    )


# =========================================================
# Baseline safe scenario
# =========================================================


def test_valid_safe_trade_is_approved():
    engine = make_engine()

    result = engine.evaluate(
        make_long_input()
    )

    assert (
        result.decision
        == RiskDecision.APPROVE
    )

    assert result.plan is not None

    assert (
        result.plan.symbol
        == "BTCUSDT"
    )

    assert (
        result.plan.side
        == RiskSide.LONG
    )

    assert (
        result.plan.actual_risk_amount
        <= result.plan.risk_amount
    )

    assert (
        result.plan.reward_risk_ratio
        >= engine.policy
        .minimum_reward_risk
    )

    assert (
        result.plan.leverage
        <= engine.policy.max_leverage
    )


# =========================================================
# Existing-position protection
# =========================================================


def test_existing_position_is_rejected():
    engine = make_engine()

    result = engine.evaluate(
        make_long_input(
            open_positions=1
        )
    )

    assert_rejected(
        result,

        "Maximum open-position "
        "limit reached.",
    )


# =========================================================
# Daily loss limit
# =========================================================


def test_daily_loss_limit_reached_is_rejected():
    engine = make_engine()

    equity = d("10000")

    daily_limit = (
        equity
        * engine.policy
        .max_daily_loss_fraction
    )

    result = engine.evaluate(
        make_long_input(
            equity=equity,

            daily_pnl=(
                -daily_limit
            ),
        )
    )

    assert_rejected(
        result,

        "Daily loss limit has "
        "already been reached.",
    )


# =========================================================
# Remaining daily risk budget
# =========================================================


def test_remaining_daily_budget_is_rejected():
    engine = make_engine()

    equity = d("10000")

    daily_limit = (
        equity
        * engine.policy
        .max_daily_loss_fraction
    )

    # Baseline valid trade risks
    # approximately $50.
    #
    # Leave only $10 of today's
    # risk budget available.
    current_loss = (
        daily_limit
        - d("10")
    )

    result = engine.evaluate(
        make_long_input(
            equity=equity,

            daily_pnl=(
                -current_loss
            ),
        )
    )

    assert_rejected(
        result,

        "Proposed trade risk exceeds "
        "the remaining daily "
        "risk budget.",
    )


# =========================================================
# Zero available balance
# =========================================================


def test_zero_available_balance_is_rejected():
    engine = make_engine()

    result = engine.evaluate(
        make_long_input(
            balance=d("0")
        )
    )

    assert_rejected(
        result,

        "Available balance is zero.",
    )


# =========================================================
# Excessive required leverage
# =========================================================


def test_required_leverage_above_policy_is_rejected():
    engine = make_engine()

    # Baseline position notional is
    # about $4,250.
    #
    # $1,000 available balance
    # requires > 4x leverage.
    #
    # Default deterministic policy
    # allows less than that.
    result = engine.evaluate(
        make_long_input(
            balance=d("1000")
        )
    )

    assert_rejected(
        result,

        "Required leverage exceeds "
        "the maximum allowed "
        "risk-policy leverage.",
    )


# =========================================================
# Exchange minimum quantity
# =========================================================


def test_exchange_minimum_quantity_violation_is_rejected():
    engine = make_engine(
        min_order_qty=d("1")
    )

    result = engine.evaluate(
        make_long_input()
    )

    assert_rejected(
        result,

        "Executable quantity is below "
        "Bybit minimum order quantity.",
    )


# =========================================================
# Exchange minimum notional
# =========================================================


def test_exchange_minimum_notional_violation_is_rejected():
    engine = make_engine(
        min_notional_value=(
            d("100000")
        )
    )

    result = engine.evaluate(
        make_long_input()
    )

    assert_rejected(
        result,

        "Position notional is below "
        "Bybit minimum notional value.",
    )


# =========================================================
# Extreme-volatility safety
#
# The risk engine does not receive a
# "volatility" variable directly.
#
# We represent the dangerous result of
# extreme volatility as a stop distance
# beyond the deterministic policy limit.
# =========================================================


def test_extreme_volatility_wide_stop_is_rejected():
    engine = make_engine()

    entry = d("85000")

    excessive_fraction = (
        engine.policy
        .max_stop_distance_fraction
        + d("0.02")
    )

    stop_distance = (
        entry
        * excessive_fraction
    )

    stop = (
        entry
        - stop_distance
    )

    # Keep reward:risk healthy so the
    # rejection specifically tests the
    # excessive-stop safety rule.
    target = (
        entry
        + (
            stop_distance
            * d("2")
        )
    )

    result = engine.evaluate(
        make_long_input(
            entry=entry,
            stop=stop,
            target=target,
        )
    )

    assert_rejected(
        result,

        "Stop distance exceeds "
        "the maximum allowed distance.",
    )