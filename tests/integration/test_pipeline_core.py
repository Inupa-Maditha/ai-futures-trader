from __future__ import annotations

from dataclasses import dataclass

import pytest

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


class CallCounter:
    def __init__(
        self,
    ):
        self.market = 0
        self.decision = 0
        self.risk = 0
        self.approval = 0
        self.execution = 0


def build_journal(
    tmp_path,
    *,
    run_id="integration-run",
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


def validate_run(
    store,
    run_id,
):
    events = store.read_events(
        run_id=run_id
    )

    validation = (
        JournalRunValidator()
        .validate(
            events
        )
    )

    return (
        events,
        validation,
    )


def test_no_trade_stops_before_risk(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path
    )

    calls = CallCounter()

    def market_context_provider():
        calls.market += 1

        return SampleContext()

    def decision_provider(
        context,
    ):
        calls.decision += 1

        assert (
            context.symbol
            == "BTCUSDT"
        )

        return SampleDecisionResult(
            accepted=True,

            proposal=(
                SampleProposal(
                    action="NO_TRADE"
                )
            ),
        )

    def risk_provider(
        proposal,
    ):
        calls.risk += 1

        raise AssertionError(
            "Risk stage must not run "
            "after NO_TRADE."
        )

    pipeline = TradingPipeline(
        journal=journal,

        market_context_provider=(
            market_context_provider
        ),

        decision_provider=(
            decision_provider
        ),

        risk_provider=(
            risk_provider
        ),

        execution_enabled_provider=(
            lambda: False
        ),
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    outcome = lifecycle.run(
        pipeline.run
    )

    assert outcome.status == "NO_TRADE"

    assert calls.market == 1
    assert calls.decision == 1
    assert calls.risk == 0
    assert calls.approval == 0
    assert calls.execution == 0

    events, validation = validate_run(
        store,
        journal.run_id,
    )

    assert validation.valid is True

    assert (
        validation.status
        == "NO_TRADE"
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


def test_risk_rejection_stops_before_approval(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path
    )

    calls = CallCounter()

    def risk_provider(
        proposal,
    ):
        calls.risk += 1

        assert (
            proposal.action
            == "LONG"
        )

        return SampleRiskResult(
            status="RISK_REJECTED",

            risk_result={
                "decision":
                "REJECT",

                "reasons": [
                    "R:R below minimum"
                ],
            },
        )

    def approval_provider(
        risk_result,
    ):
        calls.approval += 1

        raise AssertionError(
            "Approval must not run "
            "after risk rejection."
        )

    pipeline = TradingPipeline(
        journal=journal,

        market_context_provider=(
            lambda: SampleContext()
        ),

        decision_provider=(
            lambda context:
            SampleDecisionResult(
                accepted=True,

                proposal=(
                    SampleProposal(
                        action="LONG"
                    )
                ),
            )
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
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    outcome = lifecycle.run(
        pipeline.run
    )

    assert (
        outcome.status
        == "RISK_REJECTED"
    )

    assert calls.risk == 1
    assert calls.approval == 0
    assert calls.execution == 0

    events, validation = validate_run(
        store,
        journal.run_id,
    )

    assert validation.valid is True

    assert (
        validation.status
        == "RISK_REJECTED"
    )

    assert [
        event.event_type
        for event in events
    ] == [
        JournalEventType.RUN_STARTED,
        JournalEventType.MARKET_CONTEXT,
        JournalEventType.DECISION,
        JournalEventType.RISK_RESULT,
        JournalEventType.RUN_FINISHED,
    ]


def test_risk_approved_but_execution_disabled(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path
    )

    calls = CallCounter()

    def risk_provider(
        proposal,
    ):
        calls.risk += 1

        return SampleRiskResult(
            status="RISK_APPROVED",

            risk_result={
                "decision":
                "APPROVE",

                "plan": {
                    "actual_risk_amount":
                    "50"
                },
            },
        )

    def approval_provider(
        risk_result,
    ):
        calls.approval += 1

        raise AssertionError(
            "Approval must not run while "
            "Demo execution is disabled."
        )

    pipeline = TradingPipeline(
        journal=journal,

        market_context_provider=(
            lambda: SampleContext()
        ),

        decision_provider=(
            lambda context:
            SampleDecisionResult(
                accepted=True,

                proposal=(
                    SampleProposal(
                        action="SHORT"
                    )
                ),
            )
        ),

        risk_provider=(
            risk_provider
        ),

        execution_enabled_provider=(
            lambda: False
        ),

        approval_provider=(
            approval_provider
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
        == "DEMO_EXECUTION_DISABLED"
    )

    assert calls.risk == 1
    assert calls.approval == 0
    assert calls.execution == 0

    events, validation = validate_run(
        store,
        journal.run_id,
    )

    assert validation.valid is True

    assert (
        validation.status
        == "DEMO_EXECUTION_DISABLED"
    )

    assert [
        event.event_type
        for event in events
    ] == [
        JournalEventType.RUN_STARTED,
        JournalEventType.MARKET_CONTEXT,
        JournalEventType.DECISION,
        JournalEventType.RISK_RESULT,
        JournalEventType.RUN_FINISHED,
    ]


def test_unhandled_pipeline_error_is_closed_safely(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path
    )

    calls = CallCounter()

    def market_context_provider():
        calls.market += 1

        raise RuntimeError(
            "Simulated public API failure"
        )

    pipeline = TradingPipeline(
        journal=journal,

        market_context_provider=(
            market_context_provider
        ),

        decision_provider=(
            lambda context:
            pytest.fail(
                "Decision stage must not run."
            )
        ),

        risk_provider=(
            lambda proposal:
            pytest.fail(
                "Risk stage must not run."
            )
        ),

        execution_enabled_provider=(
            lambda: False
        ),
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Simulated public API failure"
        ),
    ):
        lifecycle.run(
            pipeline.run
        )

    assert calls.market == 1

    events, validation = validate_run(
        store,
        journal.run_id,
    )

    assert validation.valid is True

    assert (
        validation.status
        == "UNHANDLED_ERROR"
    )

    assert [
        event.event_type
        for event in events
    ] == [
        JournalEventType.RUN_STARTED,
        JournalEventType.ERROR,
        JournalEventType.RUN_FINISHED,
    ]

    assert (
        events[1]
        .payload["stage"]
        == "UNHANDLED_PIPELINE"
    )

    assert (
        events[1]
        .payload["error_type"]
        == "RuntimeError"
    )

    assert (
        events[1]
        .payload["message"]
        == "Simulated public API failure"
    )