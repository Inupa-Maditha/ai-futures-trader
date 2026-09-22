from __future__ import annotations

from collections import defaultdict

from journal.schema import (
    JournalEvent,
    JournalEventType,
)

from journal.store import (
    JournalStore,
)


class JournalQuery:
    def __init__(
        self,
        store: JournalStore,
    ):
        self.store = store

    def get_all_runs(
        self,
    ) -> dict[
        str,
        tuple[JournalEvent, ...],
    ]:
        events = self.store.read_events()

        grouped: dict[
            str,
            list[JournalEvent],
        ] = defaultdict(list)

        for event in events:
            grouped[event.run_id].append(
                event
            )

        result: dict[
            str,
            tuple[JournalEvent, ...],
        ] = {}

        for run_id, run_events in grouped.items():
            ordered = sorted(
                run_events,
                key=lambda item:
                item.timestamp_utc,
            )

            result[run_id] = tuple(
                ordered
            )

        return result

    def get_latest_run(
        self,
    ) -> tuple[
        JournalEvent,
        ...,
    ]:

        runs = self.get_all_runs()

        if not runs:
            return ()

        latest_events: (
            tuple[
                JournalEvent,
                ...,
            ]
            | None
        ) = None

        latest_timestamp = None

        for events in runs.values():
            if not events:
                continue

            started = [
                event
                for event in events
                if (
                    event.event_type
                    == JournalEventType
                    .RUN_STARTED
                )
            ]

            if started:
                candidate_timestamp = (
                    started[0]
                    .timestamp_utc
                )

            else:
                candidate_timestamp = (
                    events[0]
                    .timestamp_utc
                )

            if (
                latest_timestamp is None
                or candidate_timestamp
                > latest_timestamp
            ):
                latest_timestamp = (
                    candidate_timestamp
                )

                latest_events = (
                    events
                )

        if latest_events is None:
            return ()

        return latest_events

    def get_run(
        self,
        run_id: str,
    ) -> tuple[
        JournalEvent,
        ...,
    ]:

        return self.store.read_events(
            run_id=run_id
        )