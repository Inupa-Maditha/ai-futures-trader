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


# =========================================================
# Sample domain objects
# =========================================================


@dataclass(
    frozen=True,
)
class SampleTechnicalContext:
    alignment: str

    trend_15m: str

    trend_1h: str

    trend_4h: str


@dataclass(
    frozen=True,
)
class SampleMarketContext:
    symbol: str

    freshness: str

    technical: SampleTechnicalContext


@dataclass(
    frozen=True,
)
class SampleProposal:
    action: str

    confidence: float

    setup_quality: str

    thesis: str

    no_trade_reason: str | None = None


@dataclass(
    frozen=True,
)
class SampleDecisionResult:
    accepted: bool

    proposal: SampleProposal | None

    error: str | None = None


class CallCounter:
    def __init__(
        self,
    ):
        self.market = 0
        self.decision = 0
        self.risk = 0
        self.approval = 0
        self.execution = 0


# =========================================================
# Shared helpers
# =========================================================


def build_journal(
    tmp_path,
    *,
    run_id,
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


def healthy_context():
    return SampleMarketContext(
        symbol="BTCUSDT",

        freshness="FRESH",

        technical=(
            SampleTechnicalContext(
                alignment=(
                    "BULLISH_ALIGNED"
                ),

                trend_15m="BULLISH",

                trend_1h="BULLISH",

                trend_4h="BULLISH",
            )
        ),
    )


def conflicting_context():
    return SampleMarketContext(
        symbol="BTCUSDT",

        freshness="FRESH",

        technical=(
            SampleTechnicalContext(
                alignment="MIXED",

                trend_15m="BULLISH",

                trend_1h="BEARISH",

                trend_4h="BULLISH",
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


def forbidden_risk_provider(
    calls,
):
    def provider(
        proposal,
    ):
        calls.risk += 1

        raise AssertionError(
            "Risk engine must not run "
            "for this failure scenario."
        )

    return provider


# =========================================================
# IT-101
# Public REST / market-data API unavailable
# =========================================================


def test_public_api_failure_fails_closed(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path,
        run_id="api-failure-run",
    )

    calls = CallCounter()

    def market_provider():
        calls.market += 1

        raise RuntimeError(
            "Bybit public REST unavailable"
        )

    def decision_provider(
        context,
    ):
        calls.decision += 1

        raise AssertionError(
            "Decision engine must not run "
            "without market context."
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
            forbidden_risk_provider(
                calls
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
        match="Bybit public REST unavailable",
    ):
        lifecycle.run(
            pipeline.run
        )

    assert calls.market == 1
    assert calls.decision == 0
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


# =========================================================
# IT-103/104/105
# Stale market data must never reach LLM
# =========================================================


def test_stale_market_data_fails_closed(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path,
        run_id="stale-data-run",
    )

    calls = CallCounter()

    def market_provider():
        calls.market += 1

        # Represents the existing
        # require_healthy=True boundary
        # rejecting stale candles/data.
        raise RuntimeError(
            "Market data freshness "
            "validation failed"
        )

    def decision_provider(
        context,
    ):
        calls.decision += 1

        raise AssertionError(
            "Stale data must never reach "
            "the LLM decision engine."
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
            forbidden_risk_provider(
                calls
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
        match="freshness",
    ):
        lifecycle.run(
            pipeline.run
        )

    assert calls.market == 1
    assert calls.decision == 0
    assert calls.risk == 0

    events, validation = validate_run(
        store,
        journal.run_id,
    )

    assert validation.valid is True

    assert (
        validation.status
        == "UNHANDLED_ERROR"
    )

    assert (
        events[-2]
        .event_type
        == JournalEventType.ERROR
    )


# =========================================================
# IT-106
# Mixed / invalid timestamps
# =========================================================


def test_mixed_timestamps_fail_before_decision(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path,
        run_id="timestamp-failure-run",
    )

    calls = CallCounter()

    def market_provider():
        calls.market += 1

        raise ValueError(
            "Mixed market-data timestamps"
        )

    def decision_provider(
        context,
    ):
        calls.decision += 1

        raise AssertionError(
            "Invalid timestamps must "
            "not reach decision stage."
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
            forbidden_risk_provider(
                calls
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
        ValueError,
        match="Mixed market-data timestamps",
    ):
        lifecycle.run(
            pipeline.run
        )

    assert calls.decision == 0
    assert calls.risk == 0

    events, validation = validate_run(
        store,
        journal.run_id,
    )

    assert validation.valid is True

    assert (
        validation.status
        == "UNHANDLED_ERROR"
    )

    assert (
        events[1]
        .payload["error_type"]
        == "ValueError"
    )


# =========================================================
# IT-202
# Malformed LLM output is rejected
# =========================================================


def test_malformed_llm_output_stops_before_risk(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path,
        run_id="malformed-llm-run",
    )

    calls = CallCounter()

    def market_provider():
        calls.market += 1

        return healthy_context()

    def decision_provider(
        context,
    ):
        calls.decision += 1

        # Represents schema/provider pipeline
        # rejecting malformed JSON.
        return SampleDecisionResult(
            accepted=False,

            proposal=None,

            error=(
                "Malformed structured "
                "LLM response"
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
            forbidden_risk_provider(
                calls
            )
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

    assert calls.market == 1
    assert calls.decision == 1
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

    assert (
        events[2]
        .payload["accepted"]
        is False
    )

    assert (
        events[2]
        .payload["error"]
        == (
            "Malformed structured "
            "LLM response"
        )
    )


# =========================================================
# IT-203
# Ungrounded evidence is rejected
# =========================================================


def test_ungrounded_llm_evidence_stops_before_risk(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path,
        run_id="ungrounded-evidence-run",
    )

    calls = CallCounter()

    def decision_provider(
        context,
    ):
        calls.decision += 1

        # Represents the deterministic
        # evidence-grounding validator
        # rejecting invented evidence.
        return SampleDecisionResult(
            accepted=False,

            proposal=None,

            error=(
                "Proposal contains "
                "ungrounded evidence"
            ),
        )

    pipeline = TradingPipeline(
        journal=journal,

        market_context_provider=(
            healthy_context
        ),

        decision_provider=(
            decision_provider
        ),

        risk_provider=(
            forbidden_risk_provider(
                calls
            )
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

    assert calls.decision == 1
    assert calls.risk == 0

    events, validation = validate_run(
        store,
        journal.run_id,
    )

    assert validation.valid is True

    decision_event = events[2]

    assert (
        decision_event.event_type
        == JournalEventType.DECISION
    )

    assert (
        decision_event
        .payload["accepted"]
        is False
    )


# =========================================================
# IT-206
# Conflicting signals must remain operationally safe
# =========================================================


def test_conflicting_signals_can_end_in_safe_no_trade(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path,
        run_id="conflicting-signals-run",
    )

    calls = CallCounter()

    def market_provider():
        calls.market += 1

        return conflicting_context()

    def decision_provider(
        context,
    ):
        calls.decision += 1

        assert (
            context
            .technical
            .alignment
            == "MIXED"
        )

        return SampleDecisionResult(
            accepted=True,

            proposal=(
                SampleProposal(
                    action="NO_TRADE",

                    confidence=0.4,

                    setup_quality="LOW",

                    thesis=(
                        "Conflicting "
                        "multi-timeframe signals."
                    ),

                    no_trade_reason=(
                        "Insufficient directional "
                        "consensus."
                    ),
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
            forbidden_risk_provider(
                calls
            )
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
        == "NO_TRADE"
    )

    assert calls.market == 1
    assert calls.decision == 1

    # Critical safety behavior:
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