from __future__ import annotations

from typing import Callable


WS_HEALTH_SOURCES = (
    "orderbook",
    "public_trades",
    "liquidations",
    "kline_15m",
    "kline_1h",
    "kline_4h",
)


class WebSocketHealthSupervisor:
    """
    Bridges the physical WebSocket connection state
    into the application's market-data health model.

    pybit is responsible for reconnecting and
    resubscribing.

    This supervisor is responsible for making sure
    our own health monitor immediately knows whether
    the transport is connected or disconnected.
    """

    def __init__(
        self,
        *,
        health_monitor,
        connection_checker:
        Callable[[], bool],
    ):
        self.health_monitor = (
            health_monitor
        )

        self.connection_checker = (
            connection_checker
        )

        self._last_connected:bool | None = None

    @property
    def last_connected(
        self,
    ) -> bool | None:
        return self._last_connected

    def check_once(
        self,
    ) -> bool:
        """
        Check WebSocket transport state once.

        Any exception while checking connection state
        is treated as disconnected.

        Health state is only updated when the
        connection state changes.
        """

        try:
            connected = bool(
                self.connection_checker()
            )

        except Exception:
            connected = False

        if (
            connected
            == self._last_connected
        ):
            return connected

        for source_name in (
            WS_HEALTH_SOURCES
        ):
            source = (
                self.health_monitor
                .get(source_name)
            )

            if connected:
                source.mark_connected()

            else:
                source.mark_disconnected()

        self._last_connected = (
            connected
        )

        return connected