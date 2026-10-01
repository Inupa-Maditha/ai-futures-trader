from __future__ import annotations

from market_data.public_ws import (
    BybitPublicWebSocket,
)

from market_data.ws_health import (
    WS_HEALTH_SOURCES,
    WebSocketHealthSupervisor,
)


class FakeHealthSource:
    def __init__(
        self,
    ):
        self.connected = None

        self.connected_calls = 0
        self.disconnected_calls = 0

    def mark_connected(
        self,
    ):
        self.connected = True

        self.connected_calls += 1

    def mark_disconnected(
        self,
    ):
        self.connected = False

        self.disconnected_calls += 1


class FakeHealthMonitor:
    def __init__(
        self,
    ):
        self.sources = {
            name: FakeHealthSource()

            for name in (
                WS_HEALTH_SOURCES
            )
        }

    def get(
        self,
        name,
    ):
        return self.sources[
            name
        ]


class MutableConnection:
    def __init__(
        self,
        connected,
    ):
        self.connected = connected

    def __call__(
        self,
    ):
        return self.connected


def test_connected_socket_marks_all_sources_connected():
    monitor = FakeHealthMonitor()

    connection = MutableConnection(
        True
    )

    supervisor = (
        WebSocketHealthSupervisor(
            health_monitor=monitor,

            connection_checker=(
                connection
            ),
        )
    )

    result = (
        supervisor.check_once()
    )

    assert result is True

    assert (
        supervisor.last_connected
        is True
    )

    for source in (
        monitor.sources.values()
    ):
        assert (
            source.connected
            is True
        )

        assert (
            source.connected_calls
            == 1
        )

        assert (
            source.disconnected_calls
            == 0
        )


def test_disconnect_marks_all_sources_disconnected():
    monitor = FakeHealthMonitor()

    connection = MutableConnection(
        False
    )

    supervisor = (
        WebSocketHealthSupervisor(
            health_monitor=monitor,

            connection_checker=(
                connection
            ),
        )
    )

    result = (
        supervisor.check_once()
    )

    assert result is False

    assert (
        supervisor.last_connected
        is False
    )

    for source in (
        monitor.sources.values()
    ):
        assert (
            source.connected
            is False
        )

        assert (
            source.disconnected_calls
            == 1
        )


def test_disconnect_then_reconnect_restores_transport_health():
    monitor = FakeHealthMonitor()

    connection = MutableConnection(
        True
    )

    supervisor = (
        WebSocketHealthSupervisor(
            health_monitor=monitor,

            connection_checker=(
                connection
            ),
        )
    )

    assert (
        supervisor.check_once()
        is True
    )

    connection.connected = False

    assert (
        supervisor.check_once()
        is False
    )

    for source in (
        monitor.sources.values()
    ):
        assert (
            source.connected
            is False
        )

    # Represents pybit successfully
    # reconnecting its underlying socket.
    connection.connected = True

    assert (
        supervisor.check_once()
        is True
    )

    for source in (
        monitor.sources.values()
    ):
        assert (
            source.connected
            is True
        )

        assert (
            source.connected_calls
            == 2
        )

        assert (
            source.disconnected_calls
            == 1
        )


def test_connection_check_exception_fails_closed():
    monitor = FakeHealthMonitor()

    def broken_checker():
        raise RuntimeError(
            "socket state unavailable"
        )

    supervisor = (
        WebSocketHealthSupervisor(
            health_monitor=monitor,

            connection_checker=(
                broken_checker
            ),
        )
    )

    result = (
        supervisor.check_once()
    )

    assert result is False

    for source in (
        monitor.sources.values()
    ):
        assert (
            source.connected
            is False
        )


def test_same_state_does_not_repeatedly_mutate_health():
    monitor = FakeHealthMonitor()

    connection = MutableConnection(
        True
    )

    supervisor = (
        WebSocketHealthSupervisor(
            health_monitor=monitor,

            connection_checker=(
                connection
            ),
        )
    )

    supervisor.check_once()
    supervisor.check_once()
    supervisor.check_once()

    for source in (
        monitor.sources.values()
    ):
        assert (
            source.connected_calls
            == 1
        )

        assert (
            source.disconnected_calls
            == 0
        )


def test_public_ws_connection_check_delegates_safely():
    class FakePybitSocket:
        def is_connected(
            self,
        ):
            return True

    wrapper = (
        BybitPublicWebSocket
        .__new__(
            BybitPublicWebSocket
        )
    )

    wrapper.ws = FakePybitSocket()

    assert (
        wrapper.is_connected()
        is True
    )