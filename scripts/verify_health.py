from time import monotonic_ns

from data_quality.freshness import DataHealthMonitor
from data_quality.health import HealthStatus
from data_quality.policies import INITIAL_HEALTH_POLICIES


def build_monitor() -> DataHealthMonitor:
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


def main():
    print(
        "=== Sprint 1 — Data Health Verification ==="
    )

    monitor = build_monitor()

    orderbook = monitor.get("orderbook")

    print("\n[1] Initial state")

    assert (
        orderbook.status()
        == HealthStatus.UNKNOWN
    )

    print(
        "Order book:",
        orderbook.status().value,
    )

    print("\n[2] Fresh event")

    now_ns = monotonic_ns()

    orderbook.mark_connected()
    orderbook.record_event(
        event_ts_ms=123456789,
        receive_monotonic_ns=now_ns,
    )

    assert (
        orderbook.status(now_ns)
        == HealthStatus.HEALTHY
    )

    print(
        "Order book:",
        orderbook.status(now_ns).value,
    )

    print("\n[3] Simulated stale state")

    future_ns = (
        now_ns
        + 6 * 1_000_000_000
    )

    assert (
        orderbook.status(future_ns)
        == HealthStatus.STALE
    )

    print(
        "Order book:",
        orderbook.status(future_ns).value,
    )

    print("\n[4] Sequence failure")

    orderbook.record_event(
        event_ts_ms=123456790,
        receive_monotonic_ns=now_ns,
    )

    orderbook.mark_sequence_invalid()

    assert (
        orderbook.status(now_ns)
        == HealthStatus.DEGRADED
    )

    print(
        "Order book:",
        orderbook.status(now_ns).value,
    )

    print("\n[5] Disconnection")

    orderbook.mark_sequence_valid()
    orderbook.mark_disconnected()

    assert (
        orderbook.status(now_ns)
        == HealthStatus.DEGRADED
    )

    print(
        "Order book:",
        orderbook.status(now_ns).value,
    )

    print("\n[6] Liquidation stream")

    liquidations = monitor.get(
        "liquidations"
    )

    liquidations.mark_connected()

    assert (
        liquidations.status()
        == HealthStatus.HEALTHY
    )

    print(
        "Liquidations:",
        liquidations.status().value,
    )

    print(
        "\nData health verification: OK"
    )


if __name__ == "__main__":
    main()