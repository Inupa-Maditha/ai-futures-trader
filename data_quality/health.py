from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import monotonic_ns


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass
class SourceHealth:
    name: str
    stale_after_seconds: float
    event_required: bool = True

    connection_ok: bool = False
    sequence_ok: bool = True

    last_event_ts_ms: int | None = None
    last_receive_monotonic_ns: int | None = None

    reason: str | None = None

    def mark_connected(self) -> None:
        self.connection_ok = True
        self.reason = None

    def mark_disconnected(self) -> None:
        self.connection_ok = False
        self.reason = "CONNECTION_LOST"

    def mark_sequence_invalid(self) -> None:
        self.sequence_ok = False
        self.reason = "SEQUENCE_INVALID"

    def mark_sequence_valid(self) -> None:
        self.sequence_ok = True

    def record_event(
        self,
        event_ts_ms: int | None = None,
        receive_monotonic_ns: int | None = None,
    ) -> None:
        self.last_event_ts_ms = event_ts_ms

        self.last_receive_monotonic_ns = (
            receive_monotonic_ns
            if receive_monotonic_ns is not None
            else monotonic_ns()
        )

        self.connection_ok = True

    def age_seconds(
        self,
        now_monotonic_ns: int | None = None,
    ) -> float | None:

        if self.last_receive_monotonic_ns is None:
            return None

        now_ns = (
            now_monotonic_ns
            if now_monotonic_ns is not None
            else monotonic_ns()
        )

        return (
            now_ns - self.last_receive_monotonic_ns
        ) / 1_000_000_000

    def status(
        self,
        now_monotonic_ns: int | None = None,
    ) -> HealthStatus:

        if not self.connection_ok:
            if self.last_receive_monotonic_ns is None:
                return HealthStatus.UNKNOWN

            return HealthStatus.DEGRADED

        if not self.sequence_ok:
            return HealthStatus.DEGRADED

        # Some streams, such as liquidation feeds,
        # may legitimately have no event for a long time.
        if not self.event_required:
            return HealthStatus.HEALTHY

        age = self.age_seconds(now_monotonic_ns)

        if age is None:
            return HealthStatus.UNKNOWN

        if age > self.stale_after_seconds:
            return HealthStatus.STALE

        return HealthStatus.HEALTHY