from __future__ import annotations

import csv
import json
import os

from pathlib import Path
from threading import Lock

from journal.schema import (
    JournalEvent,
    JournalEventType,
)


class JournalStore:
    CSV_FIELDS = (
        "schema_version",
        "event_id",
        "run_id",
        "timestamp_utc",
        "event_type",
        "symbol",
        "payload_json",
    )

    def __init__(
        self,
        base_dir: str | Path = (
            "data/journal"
        ),
    ):
        self.base_dir = Path(
            base_dir
        )

        self.base_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.jsonl_path = (
            self.base_dir
            / "events.jsonl"
        )

        self.csv_path = (
            self.base_dir
            / "events.csv"
        )

        self._lock = Lock()

    def append(
        self,
        event: JournalEvent,
    ) -> None:

        with self._lock:
            self._append_jsonl(
                event
            )

            self._append_csv(
                event
            )

    def read_events(
        self,
        *,
        run_id: str | None = None,
        event_type:
        JournalEventType | None = None,
    ) -> tuple[JournalEvent, ...]:

        if not self.jsonl_path.exists():
            return ()

        events: list[
            JournalEvent
        ] = []

        with self.jsonl_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            for line_number, line in enumerate(
                file,
                start=1,
            ):
                stripped = line.strip()

                if not stripped:
                    continue

                try:
                    event = (
                        JournalEvent
                        .model_validate_json(
                            stripped
                        )
                    )

                except Exception as exc:
                    raise RuntimeError(
                        "Invalid journal JSONL "
                        f"record at line "
                        f"{line_number}."
                    ) from exc

                if (
                    run_id is not None
                    and event.run_id
                    != run_id
                ):
                    continue

                if (
                    event_type
                    is not None
                    and event.event_type
                    != event_type
                ):
                    continue

                events.append(
                    event
                )

        return tuple(
            events
        )

    def _append_jsonl(
        self,
        event: JournalEvent,
    ) -> None:

        with self.jsonl_path.open(
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                event.model_dump_json()
            )

            file.write(
                "\n"
            )

            file.flush()

            os.fsync(
                file.fileno()
            )

    def _append_csv(
        self,
        event: JournalEvent,
    ) -> None:

        needs_header = (
            not self.csv_path.exists()
            or self.csv_path.stat().st_size
            == 0
        )

        with self.csv_path.open(
            "a",
            encoding="utf-8",
            newline="",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=(
                    self.CSV_FIELDS
                ),
            )

            if needs_header:
                writer.writeheader()

            writer.writerow(
                {
                    "schema_version":
                    event.schema_version,

                    "event_id":
                    event.event_id,

                    "run_id":
                    event.run_id,

                    "timestamp_utc":
                    event.timestamp_utc
                    .isoformat(),

                    "event_type":
                    event.event_type.value,

                    "symbol":
                    event.symbol,

                    "payload_json":
                    json.dumps(
                        event.payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(
                            ",",
                            ":",
                        ),
                    ),
                }
            )

            file.flush()

            os.fsync(
                file.fileno()
            )