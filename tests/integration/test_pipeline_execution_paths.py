from __future__ import annotations

from dataclasses import dataclass

from journal.lifecycle import (
    JournalRunLifecycle,
)

from journal.schema import (
    JournalEventType,
)

from journal.store import (
    JournalStore,
)

from journal.trading_journal import (
    TradingRunJournal,
)

from journal.validator import (
    JournalRunValidator,
)

from orchestration.pipeline import (
    TradingPipeline,
)


# =========================================================
# Sample integration-domain objects
# =========================================================


@dataclass(
    frozen=True,
)
class SampleContext:
    symbol: str = "BTCUSDT"

    health: str = "HEALTHY"


@dataclass(
    frozen=True,
)
class SampleProposal:
    action: str

    confidence: float = 0.8

    setup_quality: str = "HIGH"

    entry_price: str = "85000"

    stop_loss: str = "84000"

    take_profit: str = "87000"


@dataclass(
    frozen=True,
)
class SampleDecisionResult:
    accepted: bool

    proposal: SampleProposal | None

    error: str | None = None


@dataclass(
    frozen=True,
)
class SampleRiskResult:
    status: str

    no_trade_reason: str | None = None

    risk_result: dict | None = None


@dataclass(
    frozen=True,
)
class SampleApprovalRequest:
    approval_id: str

    symbol: str = "BTCUSDT"


@dataclass(
    frozen=True,
)
class SampleApprovalResult:
    approval_id: str

    decision: str


@dataclass(
    frozen=True,
)
class SampleExecutionRequest:
    approval_id: str

    order_link_id: str

    symbol: str = "BTCUSDT"

    side: str = "Buy"

    quantity: str = "0.001"

    entry_price: str = "85000"

    stop_loss: str = "84000"

    take_profit: str = "87000"

    leverage: str = "1"


@dataclass(
    frozen=True,
)
class SampleObservedOrder:
    order_id: str

    order_link_id: str

    order_status: str

    side: str

    quantity: str

    price: str


@dataclass(
    frozen=True,
)
class SampleExecutionResult:
    status: str

    observed_order:SampleObservedOrder


class SampleExecutionUncertainError(
    RuntimeError
):
    pass


class CallCounter:
    def __init__(
        self,
    ):
        self.market = 0
        self.decision = 0
        self.risk = 0
        self.approval = 0
        self.request = 0
        self.execution = 0


# =========================================================
# Shared helpers
# =========================================================


def build_journal(
    tmp_path,
    *,
    run_id="integration-execution-run",
):
    store = JournalStore(
        tmp_path
    )

    journal = TradingRunJournal(
        store=store,
        symbol="BTCUSDT",
        run_id=run_id,
    )

    journal.start(
        mode="BYBIT_DEMO"
    )

    return (
        store,
        journal,
    )


def approved_risk_result():
    return SampleRiskResult(
        status="RISK_APPROVED",

        risk_result={
            "decision":
            "APPROVE",

            "reasons": [],

            "plan": {
                "side":
                "LONG",

                "entry_price":
                "85000",

                "stop_loss":
                "84000",

                "take_profit":
                "87000",

                "executable_quantity":
                "0.001",

                "actual_risk_amount":
                "1.00",

                "leverage":
                "1",
            },
        },
    )


def build_trade_decision():
    return SampleDecisionResult(
        accepted=True,

        proposal=(
            SampleProposal(
                action="LONG"
            )
        ),
    )


def validate_run(
    store,
    run_id,
):
    events = store.read_events(
        run_id=run_id
    )

    result = (
        JournalRunValidator()
        .validate(
            events
        )
    )

    return (
        events,
        result,
    )


# =========================================================
# IT-005
# Risk approved -> human rejects -> no execution
# =========================================================


def test_manual_rejection_stops_execution(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path,
        run_id="manual-reject-run",
    )

    calls = CallCounter()

    def market_provider():
        calls.market += 1

        return SampleContext()

    def decision_provider(
        context,
    ):
        calls.decision += 1

        return build_trade_decision()

    def risk_provider(
        proposal,
    ):
        calls.risk += 1

        return approved_risk_result()

    def approval_provider(
        risk_result,
    ):
        calls.approval += 1

        request = (
            SampleApprovalRequest(
                approval_id="approval-1"
            )
        )

        result = (
            SampleApprovalResult(
                approval_id="approval-1",
                decision="REJECT",
            )
        )

        return (
            request,
            result,
        )

    def execution_request_provider(
        approval_request,
        approval_result,
    ):
        calls.request += 1

        raise AssertionError(
            "Execution request must not "
            "be created after manual "
            "rejection."
        )

    def execution_provider(
        request,
    ):
        calls.execution += 1

        raise AssertionError(
            "Execution must not run "
            "after manual rejection."
        )

    pipeline = TradingPipeline(
        journal=journal,

        market_context_provider=(
            market_provider
        ),

        decision_provider=(
            decision_provider
        ),

        risk_provider=(
            risk_provider
        ),

        execution_enabled_provider=(
            lambda: True
        ),

        approval_provider=(
            approval_provider
        ),

        execution_request_provider=(
            execution_request_provider
        ),

        execution_provider=(
            execution_provider
        ),
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    outcome = lifecycle.run(
        pipeline.run
    )

    assert (
        outcome.status
        == "MANUALLY_REJECTED"
    )

    assert calls.market == 1
    assert calls.decision == 1
    assert calls.risk == 1
    assert calls.approval == 1

    assert calls.request == 0
    assert calls.execution == 0

    events, validation = validate_run(
        store,
        journal.run_id,
    )

    assert validation.valid is True

    assert (
        validation.status
        == "MANUALLY_REJECTED"
    )

    assert [
        event.event_type
        for event in events
    ] == [
        JournalEventType.RUN_STARTED,
        JournalEventType.MARKET_CONTEXT,
        JournalEventType.DECISION,
        JournalEventType.RISK_RESULT,
        JournalEventType.MANUAL_APPROVAL,
        JournalEventType.RUN_FINISHED,
    ]


# =========================================================
# IT-006
# Full approved Demo execution path
# =========================================================


def test_full_approved_execution_path(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path,
        run_id="successful-execution-run",
    )

    calls = CallCounter()

    def market_provider():
        calls.market += 1

        return SampleContext()

    def decision_provider(
        context,
    ):
        calls.decision += 1

        return build_trade_decision()

    def risk_provider(
        proposal,
    ):
        calls.risk += 1

        return approved_risk_result()

    def approval_provider(
        risk_result,
    ):
        calls.approval += 1

        request = (
            SampleApprovalRequest(
                approval_id="approval-2"
            )
        )

        result = (
            SampleApprovalResult(
                approval_id="approval-2",
                decision="APPROVE",
            )
        )

        return (
            request,
            result,
        )

    def request_provider(
        approval_request,
        approval_result,
    ):
        calls.request += 1

        assert (
            approval_request
            .approval_id
            == approval_result
            .approval_id
        )

        return (
            SampleExecutionRequest(
                approval_id=(
                    approval_request
                    .approval_id
                ),

                order_link_id=(
                    "aft-v1-integration-001"
                ),
            )
        )

    def execution_provider(
        request,
    ):
        calls.execution += 1

        assert (
            request.order_link_id
            == "aft-v1-integration-001"
        )

        return SampleExecutionResult(
            status="SUBMITTED_CONFIRMED",

            observed_order=(
                SampleObservedOrder(
                    order_id=(
                        "demo-order-001"
                    ),

                    order_link_id=(
                        request
                        .order_link_id
                    ),

                    order_status="New",

                    side="Buy",

                    quantity="0.001",

                    price="85000",
                )
            ),
        )

    pipeline = TradingPipeline(
        journal=journal,

        market_context_provider=(
            market_provider
        ),

        decision_provider=(
            decision_provider
        ),

        risk_provider=(
            risk_provider
        ),

        execution_enabled_provider=(
            lambda: True
        ),

        approval_provider=(
            approval_provider
        ),

        execution_request_provider=(
            request_provider
        ),

        execution_provider=(
            execution_provider
        ),
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    outcome = lifecycle.run(
        pipeline.run
    )

    assert (
        outcome.status
        == "DEMO_ORDER_CONFIRMED"
    )

    assert calls.market == 1
    assert calls.decision == 1
    assert calls.risk == 1
    assert calls.approval == 1
    assert calls.request == 1
    assert calls.execution == 1

    assert (
        outcome.execution_result
        is not None
    )

    assert (
        outcome
        .execution_result
        .observed_order
        .order_id
        == "demo-order-001"
    )

    events, validation = validate_run(
        store,
        journal.run_id,
    )

    assert validation.valid is True

    assert (
        validation.status
        == "DEMO_ORDER_CONFIRMED"
    )

    assert [
        event.event_type
        for event in events
    ] == [
        JournalEventType.RUN_STARTED,
        JournalEventType.MARKET_CONTEXT,
        JournalEventType.DECISION,
        JournalEventType.RISK_RESULT,
        JournalEventType.MANUAL_APPROVAL,
        JournalEventType.EXECUTION_RESULT,
        JournalEventType.RUN_FINISHED,
    ]


# =========================================================
# IT-506 / IT-507
# Execution state uncertain -> journal safely
# =========================================================


def test_execution_uncertain_path(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path,
        run_id="uncertain-execution-run",
    )

    calls = CallCounter()

    def approval_provider(
        risk_result,
    ):
        calls.approval += 1

        return (
            SampleApprovalRequest(
                approval_id="approval-3"
            ),

            SampleApprovalResult(
                approval_id="approval-3",
                decision="APPROVE",
            ),
        )

    def request_provider(
        approval_request,
        approval_result,
    ):
        calls.request += 1

        return (
            SampleExecutionRequest(
                approval_id="approval-3",

                order_link_id=(
                    "aft-v1-integration-uncertain"
                ),
            )
        )

    def execution_provider(
        request,
    ):
        calls.execution += 1

        raise (
            SampleExecutionUncertainError(
                "Order state could not "
                "be reconciled."
            )
        )

    pipeline = TradingPipeline(
        journal=journal,

        market_context_provider=(
            lambda: SampleContext()
        ),

        decision_provider=(
            lambda context:
            build_trade_decision()
        ),

        risk_provider=(
            lambda proposal:
            approved_risk_result()
        ),

        execution_enabled_provider=(
            lambda: True
        ),

        approval_provider=(
            approval_provider
        ),

        execution_request_provider=(
            request_provider
        ),

        execution_provider=(
            execution_provider
        ),

        execution_uncertain_exceptions=(
            SampleExecutionUncertainError,
        ),
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    outcome = lifecycle.run(
        pipeline.run
    )

    assert (
        outcome.status
        == "EXECUTION_UNCERTAIN"
    )

    assert calls.approval == 1
    assert calls.request == 1
    assert calls.execution == 1

    assert (
        outcome.execution_result
        is None
    )

    events, validation = validate_run(
        store,
        journal.run_id,
    )

    assert validation.valid is True

    assert (
        validation.status
        == "EXECUTION_UNCERTAIN"
    )

    assert [
        event.event_type
        for event in events
    ] == [
        JournalEventType.RUN_STARTED,
        JournalEventType.MARKET_CONTEXT,
        JournalEventType.DECISION,
        JournalEventType.RISK_RESULT,
        JournalEventType.MANUAL_APPROVAL,
        JournalEventType.ERROR,
        JournalEventType.RUN_FINISHED,
    ]

    error_event = events[-2]

    assert (
        error_event
        .payload["stage"]
        == "EXECUTION"
    )

    assert (
        error_event
        .payload["error_type"]
        == (
            "SampleExecutionUncertainError"
        )
    )


# =========================================================
# Decision validation failure
# =========================================================


def test_rejected_decision_stops_pipeline(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path,
        run_id="decision-rejected-run",
    )

    calls = CallCounter()

    def risk_provider(
        proposal,
    ):
        calls.risk += 1

        raise AssertionError(
            "Risk must not run after "
            "decision rejection."
        )

    pipeline = TradingPipeline(
        journal=journal,

        market_context_provider=(
            lambda: SampleContext()
        ),

        decision_provider=(
            lambda context:
            SampleDecisionResult(
                accepted=False,
                proposal=None,
                error=(
                    "Malformed LLM response"
                ),
            )
        ),

        risk_provider=(
            risk_provider
        ),

        execution_enabled_provider=(
            lambda: True
        ),
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    outcome = lifecycle.run(
        pipeline.run
    )

    assert (
        outcome.status
        == "DECISION_REJECTED"
    )

    assert calls.risk == 0

    events, validation = validate_run(
        store,
        journal.run_id,
    )

    assert validation.valid is True

    assert (
        validation.status
        == "DECISION_REJECTED"
    )

    assert [
        event.event_type
        for event in events
    ] == [
        JournalEventType.RUN_STARTED,
        JournalEventType.MARKET_CONTEXT,
        JournalEventType.DECISION,
        JournalEventType.RUN_FINISHED,
    ]