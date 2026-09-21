from __future__ import annotations

import json

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import TextIO

from config.settings import BASE_DIR


class JsonlMarketDataRecorder:
    def __init__(
        self,
        base_dir: Path | None = None,
    ):
        self.base_dir = (
            base_dir
            if base_dir is not None
            else BASE_DIR / "data" / "raw"
        )

        self._handles: dict[
            str,
            tuple[str, TextIO],
        ] = {}

        self._lock = Lock()

    def record(
        self,
        source: str,
        payload: dict,
    ) -> None:

        receive_time = datetime.now(timezone.utc)

        envelope = {
            "source": source,
            "local_receive_ts_utc": (
                receive_time.isoformat()
            ),
            "payload": payload,
        }

        line = json.dumps(
            envelope,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )

        with self._lock:
            handle = self._get_handle(
                source=source,
                receive_time=receive_time,
            )

            handle.write(line + "\n")

            # V1 prioritizes durability over maximum
            # write throughput.
            handle.flush()

    def _get_handle(
        self,
        source: str,
        receive_time: datetime,
    ) -> TextIO:

        date_key = receive_time.strftime(
            "%Y-%m-%d"
        )

        current = self._handles.get(source)

        if current is not None:
            current_date, handle = current

            if current_date == date_key:
                return handle

            handle.close()

        directory = self.base_dir / source

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = directory / f"{date_key}.jsonl"

        handle = path.open(
            mode="a",
            encoding="utf-8",
            buffering=1,
        )

        self._handles[source] = (
            date_key,
            handle,
        )

        return handle

    def get_file_path(
        self,
        source: str,
        receive_time: datetime | None = None,
    ) -> Path:

        if receive_time is None:
            receive_time = datetime.now(
                timezone.utc
            )

        date_key = receive_time.strftime(
            "%Y-%m-%d"
        )

        return (
            self.base_dir
            / source
            / f"{date_key}.jsonl"
        )

    def close(self) -> None:
        with self._lock:
            for _, handle in self._handles.values():
                handle.close()

            self._handles.clear()