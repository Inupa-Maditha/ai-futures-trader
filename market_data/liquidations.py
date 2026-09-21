from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock


@dataclass(frozen=True, slots=True)
class LiquidationEvent:
    symbol: str
    position_side: str

    quantity: Decimal
    bankruptcy_price: Decimal

    exchange_event_ts_ms: int
    system_ts_ms: int

    local_receive_ts_utc: datetime


class LiquidationFlow:
    def __init__(
        self,
        symbol: str,
        window_seconds: int = 60,
    ):
        self.symbol = symbol
        self.window_seconds = window_seconds

        self._events: deque[LiquidationEvent] = deque()

        self.message_count = 0
        self.total_event_count = 0

        self._latest_event_ts_ms: int | None = None

        self._lock = Lock()

    def process_message(self, message: dict) -> None:
        data = message.get("data", [])

        if not isinstance(data, list):
            return

        system_ts_ms = int(message.get("ts", 0))
        local_receive_ts = datetime.now(timezone.utc)

        with self._lock:
            self.message_count += 1

            for item in data:
                if item.get("s") != self.symbol:
                    continue

                event = LiquidationEvent(
                    symbol=self.symbol,
                    position_side=item["S"],
                    quantity=Decimal(item["v"]),
                    bankruptcy_price=Decimal(item["p"]),
                    exchange_event_ts_ms=int(item["T"]),
                    system_ts_ms=system_ts_ms,
                    local_receive_ts_utc=local_receive_ts,
                )

                self._events.append(event)
                self.total_event_count += 1

                if (
                    self._latest_event_ts_ms is None
                    or event.exchange_event_ts_ms
                    > self._latest_event_ts_ms
                ):
                    self._latest_event_ts_ms = (
                        event.exchange_event_ts_ms
                    )

            self._remove_expired_events()

    def _remove_expired_events(self) -> None:
        if self._latest_event_ts_ms is None:
            return

        cutoff_ms = (
            self._latest_event_ts_ms
            - self.window_seconds * 1000
        )

        while (
            self._events
            and self._events[0].exchange_event_ts_ms
            < cutoff_ms
        ):
            self._events.popleft()

    def get_recent_events(self) -> list[LiquidationEvent]:
        with self._lock:
            return list(self._events)

    def latest_event(self) -> LiquidationEvent | None:
        with self._lock:
            if not self._events:
                return None

            return self._events[-1]

    def long_liquidation_volume(self) -> Decimal:
        with self._lock:
            return sum(
                (
                    event.quantity
                    for event in self._events
                    if event.position_side == "Buy"
                ),
                Decimal("0"),
            )

    def short_liquidation_volume(self) -> Decimal:
        with self._lock:
            return sum(
                (
                    event.quantity
                    for event in self._events
                    if event.position_side == "Sell"
                ),
                Decimal("0"),
            )

    def total_liquidation_volume(self) -> Decimal:
        return (
            self.long_liquidation_volume()
            + self.short_liquidation_volume()
        )

    def recent_event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def has_live_events(self) -> bool:
        with self._lock:
            return len(self._events) > 0