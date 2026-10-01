from __future__ import annotations

from pybit.unified_trading import (
    WebSocket,
)

from config.settings import (
    SYMBOL,
)

from data_quality.freshness import (
    DataHealthMonitor,
)

from market_data.liquidations import (
    LiquidationFlow,
)

from market_data.live_candles import (
    LiveCandleStore,
)

from market_data.orderbook import (
    OrderBook,
)

from market_data.recorder import (
    JsonlMarketDataRecorder,
)

from market_data.trades import (
    TradeFlow,
)

from time import sleep

WS_START_ATTEMPTS = 4

WS_START_BACKOFF_SECONDS = (
    5,
    15,
    30,
)

PYBIT_RETRIES_PER_ATTEMPT = 3

INTERVAL_TO_HEALTH_SOURCE = {
    "15": "kline_15m",
    "60": "kline_1h",
    "240": "kline_4h",
}


class BybitPublicWebSocket:
    def __init__(
        self,
        health_monitor:
        DataHealthMonitor | None = None,
        recorder:
        JsonlMarketDataRecorder | None = None,
    ):
        self.health_monitor = (
            health_monitor
        )

        self.recorder = (
            recorder
        )

        # pybit handles transport-level reconnect
        # and resubscription.
        #
        # Keep these values explicit so the V1
        # reconnect policy is visible in our code.
        self.ws = (
            self._connect_with_backoff()
        )

    def _connect_with_backoff(
        self,
    ):
        last_error = None

        for attempt in range(
            1,
            WS_START_ATTEMPTS + 1,
        ):
            try:
                print(
                    "[WS START] "
                    f"Connection attempt "
                    f"{attempt}/"
                    f"{WS_START_ATTEMPTS}"
                )

                websocket = WebSocket(
                    testnet=False,
                    channel_type="linear",
                    restart_on_error=True,
                    retries=(
                        PYBIT_RETRIES_PER_ATTEMPT
                    ),
                )

                print(
                    "[WS START] Connected."
                )

                return websocket

            except Exception as exc:
                last_error = exc

                if (
                    attempt
                    >= WS_START_ATTEMPTS
                ):
                    break

                delay = (
                    WS_START_BACKOFF_SECONDS[
                        attempt - 1
                    ]
                )

                print(
                    "[WS START WARNING] "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                print(
                    "[WS START] "
                    f"Retrying in {delay}s..."
                )

                sleep(delay)

        raise RuntimeError(
            "Unable to establish Bybit "
            "public WebSocket after "
            f"{WS_START_ATTEMPTS} "
            "bounded startup attempts."
        ) from last_error

    def is_connected(
        self,
    ) -> bool:
        """
        Return current pybit WebSocket transport state.

        Any unexpected checker failure is treated
        as disconnected so trading fails closed.
        """

        try:
            return bool(
                self.ws.is_connected()
            )

        except Exception:
            return False

    def _get_health(
        self,
        name: str,
    ):
        if (
            self.health_monitor
            is None
        ):
            return None

        return (
            self.health_monitor
            .get(name)
        )

    def subscribe_orderbook(
        self,
        orderbook: OrderBook,
    ) -> None:

        health = self._get_health(
            "orderbook"
        )

        def callback(
            message: dict,
        ) -> None:

            if (
                self.recorder
                is not None
            ):
                self.recorder.record(
                    "orderbook",
                    message,
                )

            orderbook.process_message(
                message
            )

            if health is not None:
                event_ts = (
                    message.get("cts")
                    or message.get("ts")
                )

                health.record_event(
                    event_ts_ms=(
                        event_ts
                    )
                )

        self.ws.orderbook_stream(
            depth=orderbook.depth,
            symbol=SYMBOL,
            callback=callback,
        )

        if health is not None:
            health.mark_connected()

    def subscribe_trades(
        self,
        trade_flow: TradeFlow,
    ) -> None:

        health = self._get_health(
            "public_trades"
        )

        def callback(
            message: dict,
        ) -> None:

            if (
                self.recorder
                is not None
            ):
                self.recorder.record(
                    "public_trades",
                    message,
                )

            trade_flow.process_message(
                message
            )

            if health is None:
                return

            data = message.get(
                "data",
                [],
            )

            event_ts = (
                message.get("ts")
            )

            if data:
                timestamps = [
                    int(
                        item["T"]
                    )

                    for item in data

                    if "T" in item
                ]

                if timestamps:
                    event_ts = max(
                        timestamps
                    )

            health.record_event(
                event_ts_ms=(
                    event_ts
                )
            )

        self.ws.trade_stream(
            symbol=SYMBOL,
            callback=callback,
        )

        if health is not None:
            health.mark_connected()

    def subscribe_liquidations(
        self,
        liquidation_flow:
        LiquidationFlow,
    ) -> None:

        health = self._get_health(
            "liquidations"
        )

        def callback(
            message: dict,
        ) -> None:

            if (
                self.recorder
                is not None
            ):
                self.recorder.record(
                    "liquidations",
                    message,
                )

            liquidation_flow.process_message(
                message
            )

            if health is None:
                return

            data = message.get(
                "data",
                [],
            )

            event_ts = (
                message.get("ts")
            )

            if data:
                timestamps = [
                    int(
                        item["T"]
                    )

                    for item in data

                    if "T" in item
                ]

                if timestamps:
                    event_ts = max(
                        timestamps
                    )

            health.record_event(
                event_ts_ms=(
                    event_ts
                )
            )

        self.ws.all_liquidation_stream(
            symbol=SYMBOL,
            callback=callback,
        )

        # Liquidation source does not require
        # actual liquidation events to remain
        # healthy, but its WebSocket transport
        # must remain connected.
        if health is not None:
            health.mark_connected()

    def subscribe_klines(
        self,
        candle_store:
        LiveCandleStore,
    ) -> None:

        def callback(
            message: dict,
        ) -> None:

            data = message.get(
                "data",
                [],
            )

            if (
                data
                and self.recorder
                is not None
            ):
                interval = str(
                    data[0].get(
                        "interval"
                    )
                )

                source_name = (
                    INTERVAL_TO_HEALTH_SOURCE
                    .get(interval)
                )

                if (
                    source_name
                    is not None
                ):
                    self.recorder.record(
                        source_name,
                        message,
                    )

            candle_store.process_message(
                message
            )

            if (
                self.health_monitor
                is None
            ):
                return

            for item in data:
                interval = str(
                    item.get(
                        "interval"
                    )
                )

                source_name = (
                    INTERVAL_TO_HEALTH_SOURCE
                    .get(interval)
                )

                if (
                    source_name
                    is None
                ):
                    continue

                health = self._get_health(
                    source_name
                )

                event_ts = (
                    item.get(
                        "timestamp"
                    )
                    or message.get(
                        "ts"
                    )
                )

                if event_ts is None:
                    continue

                health.record_event(
                    event_ts_ms=int(
                        event_ts
                    )
                )

        for interval in (
            15,
            60,
            240,
        ):
            self.ws.kline_stream(
                interval=interval,
                symbol=SYMBOL,
                callback=callback,
            )

            source_name = (
                INTERVAL_TO_HEALTH_SOURCE[
                    str(interval)
                ]
            )

            health = self._get_health(
                source_name
            )

            if health is not None:
                health.mark_connected()

    def close(
        self,
    ) -> None:

        self.ws.exit()