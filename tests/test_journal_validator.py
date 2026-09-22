from datetime import (
    datetime,
    timedelta,
    timezone,
)

from journal.schema import (
    JournalEvent,
    JournalEventType,
)

from journal.validator import (
    JournalRunValidator,
)


BASE_TIME = datetime(
    2026,
    9,
    22,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_event(
    event_type,
    *,
    index,
    run_id="run-1",
    symbol="BTCUSDT",
    payload=None,
):
    return JournalEvent.create(
        run_id=run_id,

        event_type=event_type,

        symbol=symbol,

        payload=(
            payload
            if payload is not None
            else {}
        ),

        timestamp_utc=(
            BASE_TIME
            + timedelta(
                seconds=index
            )
        ),
    )


def test_valid_no_trade_run():
    events = (
        make_event(
            JournalEventType
            .RUN_STARTED,
            index=0,
        ),

        make_event(
            JournalEventType
            .MARKET_CONTEXT,
            index=1,
        ),

        make_event(
            JournalEventType
            .DECISION,
            index=2,
        ),

        make_event(
            JournalEventType
            .RUN_FINISHED,
            index=3,
            payload={
                "status":
                "NO_TRADE"
            },
        ),
    )

    result = (
        JournalRunValidator()
        .validate(events)
    )

    assert result.valid is True

    assert (
        result.status
        == "NO_TRADE"
    )


def test_missing_finished_event_invalid():
    events = (
        make_event(
            JournalEventType
            .RUN_STARTED,
            index=0,
        ),

        make_event(
            JournalEventType
            .MARKET_CONTEXT,
            index=1,
        ),

        make_event(
            JournalEventType
            .DECISION,
            index=2,
        ),
    )

    result = (
        JournalRunValidator()
        .validate(events)
    )

    assert result.valid is False

    assert any(
        "RUN_FINISHED"
        in error
        for error
        in result.errors
    )


def test_duplicate_decision_invalid():
    events = (
        make_event(
            JournalEventType
            .RUN_STARTED,
            index=0,
        ),

        make_event(
            JournalEventType
            .MARKET_CONTEXT,
            index=1,
        ),

        make_event(
            JournalEventType
            .DECISION,
            index=2,
        ),

        make_event(
            JournalEventType
            .DECISION,
            index=3,
        ),

        make_event(
            JournalEventType
            .RUN_FINISHED,
            index=4,
            payload={
                "status":
                "NO_TRADE"
            },
        ),
    )

    result = (
        JournalRunValidator()
        .validate(events)
    )

    assert result.valid is False

    assert any(
        "DECISION"
        in error
        for error
        in result.errors
    )


def test_no_trade_cannot_have_execution():
    events = (
        make_event(
            JournalEventType
            .RUN_STARTED,
            index=0,
        ),

        make_event(
            JournalEventType
            .MARKET_CONTEXT,
            index=1,
        ),

        make_event(
            JournalEventType
            .DECISION,
            index=2,
        ),

        make_event(
            JournalEventType
            .EXECUTION_RESULT,
            index=3,
        ),

        make_event(
            JournalEventType
            .RUN_FINISHED,
            index=4,
            payload={
                "status":
                "NO_TRADE"
            },
        ),
    )

    result = (
        JournalRunValidator()
        .validate(events)
    )

    assert result.valid is False

    assert any(
        "EXECUTION_RESULT"
        in error
        for error
        in result.errors
    )


def test_valid_risk_rejected_run():
    events = (
        make_event(
            JournalEventType
            .RUN_STARTED,
            index=0,
        ),

        make_event(
            JournalEventType
            .MARKET_CONTEXT,
            index=1,
        ),

        make_event(
            JournalEventType
            .DECISION,
            index=2,
        ),

        make_event(
            JournalEventType
            .RISK_RESULT,
            index=3,
        ),

        make_event(
            JournalEventType
            .RUN_FINISHED,
            index=4,
            payload={
                "status":
                "RISK_REJECTED"
            },
        ),
    )

    result = (
        JournalRunValidator()
        .validate(events)
    )

    assert result.valid is True


def test_valid_demo_order_confirmed():
    events = (
        make_event(
            JournalEventType
            .RUN_STARTED,
            index=0,
        ),

        make_event(
            JournalEventType
            .MARKET_CONTEXT,
            index=1,
        ),

        make_event(
            JournalEventType
            .DECISION,
            index=2,
        ),

        make_event(
            JournalEventType
            .RISK_RESULT,
            index=3,
        ),

        make_event(
            JournalEventType
            .MANUAL_APPROVAL,
            index=4,
        ),

        make_event(
            JournalEventType
            .EXECUTION_RESULT,
            index=5,
        ),

        make_event(
            JournalEventType
            .RUN_FINISHED,
            index=6,
            payload={
                "status":
                "DEMO_ORDER_CONFIRMED"
            },
        ),
    )

    result = (
        JournalRunValidator()
        .validate(events)
    )

    assert result.valid is True


def test_symbol_change_invalid():
    events = (
        make_event(
            JournalEventType
            .RUN_STARTED,
            index=0,
        ),

        make_event(
            JournalEventType
            .MARKET_CONTEXT,
            index=1,
            symbol="ETHUSDT",
        ),

        make_event(
            JournalEventType
            .DECISION,
            index=2,
        ),

        make_event(
            JournalEventType
            .RUN_FINISHED,
            index=3,
            payload={
                "status":
                "NO_TRADE"
            },
        ),
    )

    result = (
        JournalRunValidator()
        .validate(events)
    )

    assert result.valid is False

    assert any(
        "Symbol changed"
        in error
        for error
        in result.errors
    )


def test_unknown_terminal_status_invalid():
    events = (
        make_event(
            JournalEventType
            .RUN_STARTED,
            index=0,
        ),

        make_event(
            JournalEventType
            .MARKET_CONTEXT,
            index=1,
        ),

        make_event(
            JournalEventType
            .DECISION,
            index=2,
        ),

        make_event(
            JournalEventType
            .RUN_FINISHED,
            index=3,
            payload={
                "status":
                "UNKNOWN_STATUS"
            },
        ),
    )

    result = (
        JournalRunValidator()
        .validate(events)
    )

    assert result.valid is False

    assert any(
        "Unknown terminal status"
        in error
        for error
        in result.errors
    )