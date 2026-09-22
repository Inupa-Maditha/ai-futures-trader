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


def build_journal(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    journal = TradingRunJournal(
        store=store,
        symbol="BTCUSDT",
        run_id="test-run",
    )

    journal.start(
        mode="BYBIT_DEMO"
    )

    return store, journal


def test_successful_finished_run_passes(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    def operation():
        journal.finish(
            status="NO_TRADE"
        )

        return "done"

    result = lifecycle.run(
        operation
    )

    assert result == "done"

    events = store.read_events(
        run_id="test-run"
    )

    assert (
        events[-1].event_type
        == JournalEventType
        .RUN_FINISHED
    )


def test_unhandled_error_is_recorded(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    def operation():
        raise RuntimeError(
            "Groq unavailable"
        )

    with pytest.raises(
        RuntimeError,
        match="Groq unavailable",
    ):
        lifecycle.run(
            operation
        )

    events = store.read_events(
        run_id="test-run"
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
        .payload["message"]
        == "Groq unavailable"
    )

    assert (
        events[-1]
        .payload["status"]
        == "UNHANDLED_ERROR"
    )


def test_unhandled_error_run_is_valid(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    def operation():
        raise ValueError(
            "market context failed"
        )

    with pytest.raises(
        ValueError
    ):
        lifecycle.run(
            operation
        )

    events = store.read_events(
        run_id="test-run"
    )

    validation = (
        JournalRunValidator()
        .validate(events)
    )

    assert validation.valid is True

    assert (
        validation.status
        == "UNHANDLED_ERROR"
    )


def test_normal_return_without_finish_is_closed(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    def operation():
        return "forgot-to-finish"

    with pytest.raises(
        RuntimeError,
        match="terminal journal",
    ):
        lifecycle.run(
            operation
        )

    events = store.read_events(
        run_id="test-run"
    )

    assert (
        events[-2].event_type
        == JournalEventType.ERROR
    )

    assert (
        events[-1].payload["status"]
        == "PIPELINE_INCOMPLETE"
    )

    validation = (
        JournalRunValidator()
        .validate(events)
    )

    assert validation.valid is True


def test_exception_after_finish_does_not_modify_run(
    tmp_path,
):
    store, journal = build_journal(
        tmp_path
    )

    lifecycle = JournalRunLifecycle(
        journal
    )

    def operation():
        journal.finish(
            status="NO_TRADE"
        )

        raise RuntimeError(
            "post-finish display error"
        )

    with pytest.raises(
        RuntimeError,
        match="post-finish",
    ):
        lifecycle.run(
            operation
        )

    events = store.read_events(
        run_id="test-run"
    )

    assert len(events) == 2

    assert (
        events[-1].event_type
        == JournalEventType
        .RUN_FINISHED
    )

    assert (
        events[-1]
        .payload["status"]
        == "NO_TRADE"
    )