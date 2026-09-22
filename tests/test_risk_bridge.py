from decimal import Decimal

from decision_engine.schema import (
    DecisionAction,
    DecisionProposal,
    EvidenceDirection,
    EvidenceItem,
    SetupQuality,
)

from risk_manager.bridge import (
    AccountRiskState,
    DecisionRiskBridge,
    RiskBridgeStatus,
)

from risk_manager.engine import (
    DeterministicRiskEngine,
)

from risk_manager.instrument_rules import (
    InstrumentRules,
)

from risk_manager.schema import (
    RiskDecision,
    RiskEvaluationResult,
)


def make_rules():
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


def make_account(
    *,
    equity="10000",
    balance="10000",
    open_positions=0,
    daily_pnl="0",
):
    return AccountRiskState(
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


def make_evidence():
    return [
        EvidenceItem(
            context_path=(
                "technical.trend_alignment"
            ),

            value="BULLISH_ALIGNED",

            direction=(
                EvidenceDirection.BULLISH
            ),

            interpretation=(
                "Trend alignment is bullish."
            ),
        )
    ]


def make_long_proposal(
    *,
    symbol="BTCUSDT",
    entry=86000,
    stop=85000,
    target=88000,
):
    return DecisionProposal(
        schema_version="1.0",

        symbol=symbol,

        action=DecisionAction.LONG,

        setup_quality=SetupQuality.HIGH,

        confidence=0.8,

        thesis="Bullish setup.",

        evidence=make_evidence(),

        entry_price=entry,
        stop_loss=stop,
        take_profit=target,

        invalidation_reason=(
            "Price reaches stop loss."
        ),

        no_trade_reason=None,
    )


def make_short_proposal():
    return DecisionProposal(
        schema_version="1.0",

        symbol="BTCUSDT",

        action=DecisionAction.SHORT,

        setup_quality=SetupQuality.HIGH,

        confidence=0.8,

        thesis="Bearish setup.",

        evidence=[
            EvidenceItem(
                context_path=(
                    "technical.trend_alignment"
                ),

                value="BEARISH_ALIGNED",

                direction=(
                    EvidenceDirection.BEARISH
                ),

                interpretation=(
                    "Trend alignment "
                    "is bearish."
                ),
            )
        ],

        entry_price=86000,
        stop_loss=87000,
        take_profit=84000,

        invalidation_reason=(
            "Price reaches stop loss."
        ),

        no_trade_reason=None,
    )


def make_no_trade_proposal():
    return DecisionProposal(
        schema_version="1.0",

        symbol="BTCUSDT",

        action=DecisionAction.NO_TRADE,

        setup_quality=SetupQuality.LOW,

        confidence=0.2,

        thesis=(
            "Evidence is insufficient."
        ),

        evidence=make_evidence(),

        entry_price=None,
        stop_loss=None,
        take_profit=None,

        invalidation_reason=None,

        no_trade_reason=(
            "No sufficiently clear setup."
        ),
    )


def make_bridge():
    engine = DeterministicRiskEngine(
        instrument_rules=make_rules()
    )

    return DecisionRiskBridge(
        risk_engine=engine
    )


def test_valid_long_reaches_risk_approval():
    result = make_bridge().evaluate(
        make_long_proposal(),
        make_account(),
    )

    assert (
        result.status
        == RiskBridgeStatus.RISK_APPROVED
    )

    assert result.risk_result is not None

    assert (
        result.risk_result.decision
        == RiskDecision.APPROVE
    )

    assert (
        result.risk_result.plan
        is not None
    )


def test_valid_short_reaches_risk_approval():
    result = make_bridge().evaluate(
        make_short_proposal(),
        make_account(),
    )

    assert (
        result.status
        == RiskBridgeStatus.RISK_APPROVED
    )

    assert result.risk_result is not None

    assert (
        result.risk_result.decision
        == RiskDecision.APPROVE
    )


def test_low_reward_risk_is_rejected():
    proposal = make_long_proposal(
        target=87000
    )

    result = make_bridge().evaluate(
        proposal,
        make_account(),
    )

    assert (
        result.status
        == RiskBridgeStatus.RISK_REJECTED
    )

    assert result.risk_result is not None

    assert (
        result.risk_result.decision
        == RiskDecision.REJECT
    )

    assert any(
        "Reward-risk ratio"
        in reason
        for reason
        in result.risk_result.reasons
    )


def test_wrong_symbol_is_rejected():
    result = make_bridge().evaluate(
        make_long_proposal(
            symbol="ETHUSDT"
        ),
        make_account(),
    )

    assert (
        result.status
        == RiskBridgeStatus.RISK_REJECTED
    )

    assert result.risk_result is not None

    assert any(
        "Symbol"
        in reason
        for reason
        in result.risk_result.reasons
    )


class MustNotRunEngine:
    def evaluate(self, data):
        raise AssertionError(
            "Risk engine must not run "
            "for NO_TRADE."
        )


def test_no_trade_skips_risk_engine():
    bridge = DecisionRiskBridge(
        risk_engine=MustNotRunEngine()
    )

    result = bridge.evaluate(
        make_no_trade_proposal(),
        make_account(),
    )

    assert (
        result.status
        == RiskBridgeStatus.NO_TRADE
    )

    assert result.risk_result is None

    assert (
        result.no_trade_reason
        == "No sufficiently clear setup."
    )


class CapturingRejectEngine:
    def __init__(self):
        self.received = None

    def evaluate(self, data):
        self.received = data

        return RiskEvaluationResult(
            decision=RiskDecision.REJECT,
            reasons=("Test rejection.",),
            plan=None,
        )


def test_prices_are_converted_to_decimal_safely():
    engine = CapturingRejectEngine()

    bridge = DecisionRiskBridge(
        risk_engine=engine
    )

    proposal = make_long_proposal(
        entry=86000.1,
        stop=85000.1,
        target=88000.1,
    )

    bridge.evaluate(
        proposal,
        make_account(),
    )

    assert (
        engine.received.entry_price
        == Decimal("86000.1")
    )

    assert (
        engine.received.stop_loss
        == Decimal("85000.1")
    )

    assert (
        engine.received.take_profit
        == Decimal("88000.1")
    )