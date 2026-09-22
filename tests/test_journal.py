from datetime import (
    datetime,
    timedelta,
    timezone,
)

import csv
import json

import pytest

from journal.schema import (
    JournalEvent,
    JournalEventType,
)

from journal.store import (
    JournalStore,
)


def make_event(
    *,
    run_id="run-1",
    event_type=(
        JournalEventType.DECISION
    ),
):
    return JournalEvent.create(
        run_id=run_id,

        event_type=event_type,

        symbol="BTCUSDT",

        payload={
            "action": "NO_TRADE",
            "confidence": 0.4,
        },

        timestamp_utc=datetime(
            2026,
            9,
            22,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_naive_timestamp_rejected():
    with pytest.raises(
        ValueError
    ):
        JournalEvent.create(
            run_id="run-1",

            event_type=(
                JournalEventType
                .RUN_STARTED
            ),

            symbol="BTCUSDT",

            payload={},

            timestamp_utc=datetime(
                2026,
                9,
                22,
                12,
                0,
            ),
        )


def test_timestamp_is_normalized_to_utc():
    offset = timezone(
        timedelta(
            hours=5,
            minutes=30,
        )
    )

    event = JournalEvent.create(
        run_id="run-1",

        event_type=(
            JournalEventType.RUN_STARTED
        ),

        symbol="BTCUSDT",

        payload={},

        timestamp_utc=datetime(
            2026,
            9,
            22,
            17,
            30,
            tzinfo=offset,
        ),
    )

    assert (
        event.timestamp_utc.utcoffset()
        == timedelta(0)
    )

    assert (
        event.timestamp_utc.hour
        == 12
    )


def test_append_creates_jsonl_and_csv(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    event = make_event()

    store.append(
        event
    )

    assert (
        store.jsonl_path.exists()
    )

    assert (
        store.csv_path.exists()
    )


def test_jsonl_round_trip(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    original = make_event()

    store.append(
        original
    )

    events = store.read_events()

    assert len(events) == 1

    restored = events[0]

    assert (
        restored.event_id
        == original.event_id
    )

    assert (
        restored.payload
        == original.payload
    )

    assert (
        restored.event_type
        == JournalEventType.DECISION
    )


def test_csv_header_is_not_duplicated(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    store.append(
        make_event()
    )

    store.append(
        make_event(
            event_type=(
                JournalEventType
                .RUN_FINISHED
            )
        )
    )

    with store.csv_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.reader(
                file
            )
        )

    assert len(rows) == 3

    assert rows[0].count(
        "event_id"
    ) == 1


def test_csv_payload_is_valid_json(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    store.append(
        make_event()
    )

    with store.csv_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(
                file
            )
        )

    assert len(rows) == 1

    payload = json.loads(
        rows[0][
            "payload_json"
        ]
    )

    assert (
        payload["action"]
        == "NO_TRADE"
    )

    assert (
        payload["confidence"]
        == 0.4
    )


def test_read_events_filters(
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
        )
    )

    store.append(
        make_event(
            run_id="run-b",
            event_type=(
                JournalEventType
                .ERROR
            ),
        )
    )

    filtered = (
        store.read_events(
            run_id="run-a",

            event_type=(
                JournalEventType
                .DECISION
            ),
        )
    )

    assert len(filtered) == 1

    assert (
        filtered[0].run_id
        == "run-a"
    )