from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock

from market_data.candles import Candle, TIMEFRAMES


class LiveCandleStore:
    def __init__(self, symbol: str, max_closed: int = 500):
        self.symbol = symbol
        self.max_closed = max_closed

        self._closed: dict[str, deque[Candle]] = {
            "15m": deque(maxlen=max_closed),
            "1h": deque(maxlen=max_closed),
            "4h": deque(maxlen=max_closed),
        }

        self._forming: dict[str, Candle | None] = {
            "15m": None,
            "1h": None,
            "4h": None,
        }

        self.message_count = 0
        self.closed_count = 0

        self._lock = Lock()

    def process_message(self, message: dict) -> None:
        data = message.get("data", [])

        if not isinstance(data, list):
            return

        response_ts_ms = int(message.get("ts", 0))
        local_receive_ts = datetime.now(timezone.utc)

        with self._lock:
            self.message_count += 1

            for item in data:
                interval = str(item["interval"])

                timeframe = self._interval_to_timeframe(interval)

                if timeframe is None:
                    continue

                candle = Candle(
                    symbol=self.symbol,
                    timeframe=timeframe,
                    start_ts_ms=int(item["start"]),
                    end_ts_ms=int(item["end"]) + 1,
                    open=Decimal(item["open"]),
                    high=Decimal(item["high"]),
                    low=Decimal(item["low"]),
                    close=Decimal(item["close"]),
                    volume=Decimal(item["volume"]),
                    turnover=Decimal(item["turnover"]),
                    confirmed=bool(item["confirm"]),
                    exchange_response_ts_ms=response_ts_ms,
                    local_receive_ts_utc=local_receive_ts,
                )

                if candle.confirmed:
                    self._add_closed_candle(
                        timeframe,
                        candle,
                    )

                    self._forming[timeframe] = None

                else:
                    self._forming[timeframe] = candle

    @staticmethod
    def _interval_to_timeframe(
        interval: str,
    ) -> str | None:
        for timeframe, config in TIMEFRAMES.items():
            if config["interval"] == interval:
                return timeframe

        return None

    def _add_closed_candle(
        self,
        timeframe: str,
        candle: Candle,
    ) -> None:
        candles = self._closed[timeframe]

        # Prevent duplicate closed candle insertion.
        if (
            candles
            and candles[-1].start_ts_ms
            == candle.start_ts_ms
        ):
            candles[-1] = candle
            return

        candles.append(candle)
        self.closed_count += 1

    def get_closed_candles(
        self,
        timeframe: str,
    ) -> list[Candle]:
        with self._lock:
            return list(self._closed[timeframe])

    def latest_closed(
        self,
        timeframe: str,
    ) -> Candle | None:
        with self._lock:
            candles = self._closed[timeframe]

            if not candles:
                return None

            return candles[-1]

    def current_forming(
        self,
        timeframe: str,
    ) -> Candle | None:
        with self._lock:
            return self._forming[timeframe]

    def closed_count_for(
        self,
        timeframe: str,
    ) -> int:
        with self._lock:
            return len(self._closed[timeframe])