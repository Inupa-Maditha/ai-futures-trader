from __future__ import annotations

from threading import Event, Thread
from time import sleep

from config.settings import SYMBOL

from data_quality.freshness import (
    build_default_health_monitor,
)

from derivatives.bybit_derivatives import (
    BybitDerivativesService,
)

from market_data.candles import CandleService
from market_data.liquidations import LiquidationFlow
from market_data.live_candles import LiveCandleStore
from market_data.orderbook import OrderBook
from market_data.public_ws import BybitPublicWebSocket
from market_data.recorder import JsonlMarketDataRecorder
from market_data.trades import TradeFlow


class MarketDataRunner:
    def __init__(
        self,
        rest_poll_seconds: int = 60,
    ):
        self.rest_poll_seconds = rest_poll_seconds

        self.stop_event = Event()

        self.health_monitor = (
            build_default_health_monitor()
        )

        self.recorder = JsonlMarketDataRecorder()

        self.orderbook = OrderBook(
            symbol=SYMBOL,
            depth=50,
        )

        self.trades = TradeFlow(
            symbol=SYMBOL,
            window_seconds=60,
        )

        self.liquidations = LiquidationFlow(
            symbol=SYMBOL,
            window_seconds=60,
        )

        self.candles = LiveCandleStore(
            symbol=SYMBOL,
        )

        self.ws = BybitPublicWebSocket(
            health_monitor=self.health_monitor,
            recorder=self.recorder,
        )

        self.candle_service = CandleService(
            recorder=self.recorder,
        )

        self.derivatives = BybitDerivativesService(
            health_monitor=self.health_monitor,
            recorder=self.recorder,
        )

        self._rest_thread: Thread | None = None

    def bootstrap_historical_candles(
        self,
    ) -> None:
        print(
            "Bootstrapping historical candles..."
        )

        for timeframe in (
            "15m",
            "1h",
            "4h",
        ):
            candles = (
                self.candle_service
                .fetch_closed_candles(
                    timeframe=timeframe,
                    limit=200,
                )
            )

            print(
                f"  {timeframe}: "
                f"{len(candles)} closed candles"
            )

    def start_websockets(self) -> None:
        print(
            "Starting public WebSocket streams..."
        )

        self.ws.subscribe_orderbook(
            self.orderbook
        )

        self.ws.subscribe_trades(
            self.trades
        )

        self.ws.subscribe_liquidations(
            self.liquidations
        )

        self.ws.subscribe_klines(
            self.candles
        )

    def poll_rest_once(self) -> None:
        oi = self.derivatives.get_open_interest(
            interval="15min"
        )

        funding = self.derivatives.get_funding()

        positioning = (
            self.derivatives.get_positioning(
                period="15min"
            )
        )

        print(
            "[REST] "
            f"OI={oi.current} BTC | "
            f"Funding="
            f"{funding.current_funding_rate} | "
            f"Long="
            f"{positioning.account_holder_long_ratio} | "
            f"Short="
            f"{positioning.account_holder_short_ratio}"
        )

    def _rest_loop(self) -> None:
        while not self.stop_event.wait(
            self.rest_poll_seconds
        ):
            try:
                self.poll_rest_once()

            except Exception as exc:
                print(
                    f"[REST ERROR] {exc}"
                )

                self._mark_rest_sources_disconnected()

    def _mark_rest_sources_disconnected(
        self,
    ) -> None:
        for source_name in (
            "open_interest",
            "funding",
            "account_positioning",
        ):
            self.health_monitor.get(
                source_name
            ).mark_disconnected()

    def start_rest_poller(self) -> None:
        self._rest_thread = Thread(
            target=self._rest_loop,
            name="rest-market-data-poller",
            daemon=True,
        )

        self._rest_thread.start()

    def print_health_summary(self) -> None:
        summary = self.health_monitor.summary()

        print("\n=== Market Data Health ===")

        for name, status in summary.items():
            print(
                f"{name:<22} {status}"
            )

    def market_data_ready(self) -> bool:
        required_sources = [
            "orderbook",
            "public_trades",
            "kline_15m",
            "kline_1h",
            "kline_4h",
            "liquidations",
            "open_interest",
            "funding",
            "account_positioning",
        ]

        return self.health_monitor.critical_ok(
            required_sources
        )

    def start(self) -> None:
        print(
            "=== AI Futures Trader "
            "— Market Data Runner ==="
        )

        self.bootstrap_historical_candles()

        self.start_websockets()

        # Give WebSocket subscriptions
        # a short startup window.
        sleep(3)

        # Fetch REST data immediately before
        # the background polling cycle starts.
        self.poll_rest_once()

        self.start_rest_poller()

        print(
            "\nMarket data pipeline started."
        )

    def stop(self) -> None:
        print(
            "\nStopping market data pipeline..."
        )

        self.stop_event.set()

        if self._rest_thread is not None:
            self._rest_thread.join(
                timeout=5
            )

        try:
            self.ws.close()

        except Exception as exc:
            print(
                f"[WS SHUTDOWN WARNING] {exc}"
            )

        self.recorder.close()

        print(
            "Market data pipeline stopped."
        )