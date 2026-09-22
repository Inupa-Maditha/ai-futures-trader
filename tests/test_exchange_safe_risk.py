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


def make_rules(
    *,
    min_qty="0.001",
    max_market_qty="150",
    min_notional="5",
    max_leverage="150",
):
    return InstrumentRules(
        symbol="BTCUSDT",
        status="Trading",
        contract_type="LinearPerpetual",

        tick_size=Decimal("0.10"),

        min_price=Decimal("0.10"),
        max_price=Decimal(
            "1999999.80"
        ),

        qty_step=Decimal("0.001"),

        min_order_qty=Decimal(min_qty),

        max_order_qty=Decimal("1500"),

        max_market_order_qty=Decimal(
            max_market_qty
        ),

        min_notional_value=Decimal(
            min_notional
        ),

        min_leverage=Decimal("1"),

        max_leverage=Decimal(
            max_leverage
        ),

        leverage_step=Decimal("0.01"),
    )


def make_input(
    *,
    entry="86000.06",
    stop="85000.06",
    target="88000.06",
    equity="10000",
    balance="10000",
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

        open_position_count=0,

        daily_realized_pnl=Decimal(
            "0"
        ),
    )


def test_prices_are_exchange_aligned():
    engine = DeterministicRiskEngine(
        instrument_rules=make_rules()
    )

    result = engine.evaluate(
        make_input()
    )

    assert (
        result.decision
        == RiskDecision.APPROVE
    )

    plan = result.plan

    assert (
        plan.entry_price
        == Decimal("86000.10")
    )

    assert (
        plan.stop_loss
        == Decimal("85000.00")
    )

    assert (
        plan.take_profit
        == Decimal("88000.00")
    )


def test_quantity_rounds_down():
    engine = DeterministicRiskEngine(
        instrument_rules=make_rules()
    )

    result = engine.evaluate(
        make_input(
            entry="86000",
            stop="85050",
            target="88000",
        )
    )

    assert (
        result.decision
        == RiskDecision.APPROVE
    )

    plan = result.plan

    assert (
        plan.executable_quantity
        <= plan.raw_quantity
    )

    assert (
        plan.actual_risk_amount
        <= plan.risk_amount
    )


def test_minimum_quantity_rejected():
    engine = DeterministicRiskEngine(
        instrument_rules=make_rules(
            min_qty="1"
        )
    )

    result = engine.evaluate(
        make_input()
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "minimum order quantity"
        in reason
        for reason in result.reasons
    )


def test_minimum_notional_rejected():
    engine = DeterministicRiskEngine(
        instrument_rules=make_rules(
            min_notional="100000"
        )
    )

    result = engine.evaluate(
        make_input()
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "minimum notional"
        in reason
        for reason in result.reasons
    )


def test_market_quantity_limit_rejected():
    engine = DeterministicRiskEngine(
        instrument_rules=make_rules(
            max_market_qty="0.01"
        )
    )

    result = engine.evaluate(
        make_input()
    )

    assert (
        result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "maximum order quantity"
        in reason
        for reason in result.reasons
    )


def test_policy_leverage_limit_still_wins():
    engine = DeterministicRiskEngine(
        instrument_rules=make_rules(
            max_leverage="150"
        )
    )

    result = engine.evaluate(
        make_input(
            balance="1000"
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


def test_leverage_is_exchange_step_aligned():
    engine = DeterministicRiskEngine(
        instrument_rules=make_rules()
    )

    result = engine.evaluate(
        make_input(
            balance="3000"
        )
    )

    assert (
        result.decision
        == RiskDecision.APPROVE
    )

    leverage = result.plan.leverage

    assert (
        leverage % Decimal("0.01")
        == Decimal("0")
    )