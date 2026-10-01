from __future__ import annotations

from time import monotonic_ns

from data_quality.freshness import (
    build_default_health_monitor,
)

from data_quality.health import (
    HealthStatus,
)

from data_quality.policies import (
    INITIAL_HEALTH_POLICIES,
)

from market_data.runner import (
    MarketDataRunner,
)


NANOSECONDS_PER_SECOND = (
    1_000_000_000
)


def ns_after(
    base_ns: int,
    seconds: float,
) -> int:
    return (
        base_ns
        + int(
            seconds
            * NANOSECONDS_PER_SECOND
        )
    )


def mark_source_fresh(
    monitor,
    source_name: str,
    *,
    receive_ns: int,
) -> None:

    source = monitor.get(
        source_name
    )

    if source.event_required:
        source.record_event(
            event_ts_ms=1,
            receive_monotonic_ns=(
                receive_ns
            ),
        )

    else:
        source.mark_connected()


def mark_all_runner_sources_fresh(
    monitor,
    *,
    receive_ns: int,
) -> None:

    for source_name in (
        "orderbook",
        "public_trades",
        "kline_15m",
        "kline_1h",
        "kline_4h",
        "liquidations",
        "open_interest",
        "funding",
        "account_positioning",
    ):
        mark_source_fresh(
            monitor,
            source_name,
            receive_ns=receive_ns,
        )


# =========================================================
# Initial state
# =========================================================


def test_event_required_source_starts_unknown():
    monitor = (
        build_default_health_monitor()
    )

    source = monitor.get(
        "orderbook"
    )

    assert (
        source.status()
        == HealthStatus.UNKNOWN
    )


# =========================================================
# Connected but no data yet
# =========================================================


def test_connected_event_required_source_is_unknown_until_event():
    monitor = (
        build_default_health_monitor()
    )

    source = monitor.get(
        "orderbook"
    )

    source.mark_connected()

    assert source.connection_ok is True

    assert (
        source.status()
        == HealthStatus.UNKNOWN
    )


# =========================================================
# Fresh event -> HEALTHY
# =========================================================


def test_fresh_event_makes_source_healthy():
    monitor = (
        build_default_health_monitor()
    )

    source = monitor.get(
        "orderbook"
    )

    base_ns = monotonic_ns()

    source.record_event(
        event_ts_ms=1_000,
        receive_monotonic_ns=(
            base_ns
        ),
    )

    assert (
        source.status(
            now_monotonic_ns=(
                ns_after(
                    base_ns,
                    1,
                )
            )
        )
        == HealthStatus.HEALTHY
    )


# =========================================================
# Fresh -> STALE
# =========================================================


def test_orderbook_becomes_stale_after_threshold():
    monitor = (
        build_default_health_monitor()
    )

    source = monitor.get(
        "orderbook"
    )

    base_ns = 1_000_000_000

    source.record_event(
        event_ts_ms=1_000,
        receive_monotonic_ns=(
            base_ns
        ),
    )

    assert (
        source.status(
            now_monotonic_ns=(
                ns_after(
                    base_ns,
                    5,
                )
            )
        )
        == HealthStatus.HEALTHY
    )

    assert (
        source.status(
            now_monotonic_ns=(
                ns_after(
                    base_ns,
                    5.001,
                )
            )
        )
        == HealthStatus.STALE
    )


# =========================================================
# STALE -> fresh event -> HEALTHY
# =========================================================


def test_stale_source_recovers_after_fresh_event():
    monitor = (
        build_default_health_monitor()
    )

    source = monitor.get(
        "public_trades"
    )

    first_event_ns = (
        1_000_000_000
    )

    source.record_event(
        event_ts_ms=1_000,
        receive_monotonic_ns=(
            first_event_ns
        ),
    )

    stale_check_ns = ns_after(
        first_event_ns,
        6,
    )

    assert (
        source.status(
            now_monotonic_ns=(
                stale_check_ns
            )
        )
        == HealthStatus.STALE
    )

    recovery_event_ns = (
        stale_check_ns
    )

    source.record_event(
        event_ts_ms=2_000,
        receive_monotonic_ns=(
            recovery_event_ns
        ),
    )

    assert (
        source.status(
            now_monotonic_ns=(
                ns_after(
                    recovery_event_ns,
                    1,
                )
            )
        )
        == HealthStatus.HEALTHY
    )


# =========================================================
# HEALTHY -> disconnected -> DEGRADED
# =========================================================


def test_disconnect_after_event_becomes_degraded():
    monitor = (
        build_default_health_monitor()
    )

    source = monitor.get(
        "orderbook"
    )

    source.record_event(
        event_ts_ms=1_000,
        receive_monotonic_ns=(
            monotonic_ns()
        ),
    )

    assert (
        source.status()
        == HealthStatus.HEALTHY
    )

    source.mark_disconnected()

    assert (
        source.status()
        == HealthStatus.DEGRADED
    )

    assert (
        source.reason
        == "CONNECTION_LOST"
    )


# =========================================================
# Liquidations do not require events
# =========================================================


def test_liquidation_source_is_healthy_without_event():
    monitor = (
        build_default_health_monitor()
    )

    source = monitor.get(
        "liquidations"
    )

    assert (
        source.event_required
        is False
    )

    source.mark_connected()

    assert (
        source.status()
        == HealthStatus.HEALTHY
    )

    assert (
        source.last_receive_monotonic_ns
        is None
    )


# =========================================================
# Default policy thresholds
# =========================================================


def test_default_freshness_policies_match_v1():
    assert (
        INITIAL_HEALTH_POLICIES[
            "orderbook"
        ]["stale_after_seconds"]
        == 5
    )

    assert (
        INITIAL_HEALTH_POLICIES[
            "public_trades"
        ]["stale_after_seconds"]
        == 5
    )

    assert (
        INITIAL_HEALTH_POLICIES[
            "kline_15m"
        ]["stale_after_seconds"]
        == 75
    )

    assert (
        INITIAL_HEALTH_POLICIES[
            "kline_1h"
        ]["stale_after_seconds"]
        == 75
    )

    assert (
        INITIAL_HEALTH_POLICIES[
            "kline_4h"
        ]["stale_after_seconds"]
        == 75
    )

    assert (
        INITIAL_HEALTH_POLICIES[
            "open_interest"
        ]["stale_after_seconds"]
        == 20 * 60
    )

    assert (
        INITIAL_HEALTH_POLICIES[
            "funding"
        ]["stale_after_seconds"]
        == 5 * 60
    )

    assert (
        INITIAL_HEALTH_POLICIES[
            "account_positioning"
        ]["stale_after_seconds"]
        == 20 * 60
    )


# =========================================================
# Runner readiness fail-closed + recovery
# =========================================================


def test_runner_readiness_fails_when_source_stale_and_recovers():
    monitor = (
        build_default_health_monitor()
    )

    now_ns = monotonic_ns()

    mark_all_runner_sources_fresh(
        monitor,
        receive_ns=now_ns,
    )

    # Avoid MarketDataRunner.__init__()
    # because it creates live API/WebSocket
    # dependencies. We only need to test
    # the existing market_data_ready()
    # integration with DataHealthMonitor.
    runner = (
        MarketDataRunner.__new__(
            MarketDataRunner
        )
    )

    runner.health_monitor = monitor

    assert (
        runner.market_data_ready()
        is True
    )

    # Make orderbook older than its
    # five-second freshness limit.
    orderbook = monitor.get(
        "orderbook"
    )

    orderbook.last_receive_monotonic_ns = (
        monotonic_ns()
        - 10
        * NANOSECONDS_PER_SECOND
    )

    assert (
        orderbook.status()
        == HealthStatus.STALE
    )

    # One stale critical source must
    # fail the whole readiness gate.
    assert (
        runner.market_data_ready()
        is False
    )

    # New orderbook event arrives.
    orderbook.record_event(
        event_ts_ms=2_000,
        receive_monotonic_ns=(
            monotonic_ns()
        ),
    )

    assert (
        orderbook.status()
        == HealthStatus.HEALTHY
    )

    # Critical readiness recovers.
    assert (
        runner.market_data_ready()
        is True
    )