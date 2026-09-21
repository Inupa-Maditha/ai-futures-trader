from __future__ import annotations

from data_quality.health import (
    HealthStatus,
    SourceHealth,
)
from data_quality.policies import INITIAL_HEALTH_POLICIES


class DataHealthMonitor:
    def __init__(self):
        self.sources: dict[str, SourceHealth] = {}

    def register(
        self,
        name: str,
        stale_after_seconds: float,
        event_required: bool = True,
    ) -> SourceHealth:

        source = SourceHealth(
            name=name,
            stale_after_seconds=stale_after_seconds,
            event_required=event_required,
        )

        self.sources[name] = source

        return source

    def get(self, name: str) -> SourceHealth:
        if name not in self.sources:
            raise KeyError(
                f"Unknown health source: {name}"
            )

        return self.sources[name]

    def status(
        self,
        name: str,
    ) -> HealthStatus:
        return self.get(name).status()

    def critical_ok(
        self,
        critical_sources: list[str],
    ) -> bool:

        return all(
            self.status(name)
            == HealthStatus.HEALTHY
            for name in critical_sources
        )

    def summary(self) -> dict[str, str]:
        return {
            name: source.status().value
            for name, source in self.sources.items()
        }


def build_default_health_monitor() -> DataHealthMonitor:
    monitor = DataHealthMonitor()

    for name, policy in INITIAL_HEALTH_POLICIES.items():
        monitor.register(
            name=name,
            stale_after_seconds=policy[
                "stale_after_seconds"
            ],
            event_required=policy[
                "event_required"
            ],
        )

    return monitor