from datetime import (
    datetime,
    timedelta,
    timezone,
)

from journal.query import (
    JournalQuery,
)

from journal.schema import (
    JournalEvent,
    JournalEventType,
)

from journal.store import (
    JournalStore,
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
    *,
    run_id,
    event_type,
    seconds,
):
    return JournalEvent.create(
        run_id=run_id,

        event_type=event_type,

        symbol="BTCUSDT",

        payload={},

        timestamp_utc=(
            BASE_TIME
            + timedelta(
                seconds=seconds
            )
        ),
    )


def test_no_runs_returns_empty(
    tmp_path,
):
    query = JournalQuery(
        JournalStore(
            tmp_path
        )
    )

    assert (
        query.get_latest_run()
        == ()
    )


def test_get_run_by_id(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    store.append(
        make_event(
            run_id="run-a",
            event_type=(
                JournalEventType
                .RUN_STARTED
            ),
            seconds=0,
        )
    )

    store.append(
        make_event(
            run_id="run-b",
            event_type=(
                JournalEventType
                .RUN_STARTED
            ),
            seconds=10,
        )
    )

    query = JournalQuery(
        store
    )

    events = query.get_run(
        "run-a"
    )

    assert len(events) == 1

    assert (
        events[0].run_id
        == "run-a"
    )


def test_latest_run_selected(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    store.append(
        make_event(
            run_id="old-run",
            event_type=(
                JournalEventType
                .RUN_STARTED
            ),
            seconds=0,
        )
    )

    store.append(
        make_event(
            run_id="new-run",
            event_type=(
                JournalEventType
                .RUN_STARTED
            ),
            seconds=100,
        )
    )

    query = JournalQuery(
        store
    )

    latest = query.get_latest_run()

    assert len(latest) == 1

    assert (
        latest[0].run_id
        == "new-run"
    )


def test_latest_run_events_are_ordered(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    store.append(
        make_event(
            run_id="run-a",
            event_type=(
                JournalEventType
                .DECISION
            ),
            seconds=2,
        )
    )

    store.append(
        make_event(
            run_id="run-a",
            event_type=(
                JournalEventType
                .RUN_STARTED
            ),
            seconds=0,
        )
    )

    store.append(
        make_event(
            run_id="run-a",
            event_type=(
                JournalEventType
                .MARKET_CONTEXT
            ),
            seconds=1,
        )
    )

    query = JournalQuery(
        store
    )

    events = query.get_latest_run()

    assert [
        event.event_type
        for event in events
    ] == [
        JournalEventType.RUN_STARTED,
        JournalEventType.MARKET_CONTEXT,
        JournalEventType.DECISION,
    ]


def test_get_all_runs_groups_events(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    store.append(
        make_event(
            run_id="run-a",
            event_type=(
                JournalEventType
                .RUN_STARTED
            ),
            seconds=0,
        )
    )

    store.append(
        make_event(
            run_id="run-a",
            event_type=(
                JournalEventType
                .RUN_FINISHED
            ),
            seconds=1,
        )
    )

    store.append(
        make_event(
            run_id="run-b",
            event_type=(
                JournalEventType
                .RUN_STARTED
            ),
            seconds=10,
        )
    )

    query = JournalQuery(
        store
    )

    runs = query.get_all_runs()

    assert set(
        runs.keys()
    ) == {
        "run-a",
        "run-b",
    }

    assert len(
        runs["run-a"]
    ) == 2

    assert len(
        runs["run-b"]
    ) == 1