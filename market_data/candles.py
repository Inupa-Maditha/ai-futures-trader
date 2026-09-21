from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from config.settings import SYMBOL
from market_data.rest_client import BybitPublicRestClient
from market_data.recorder import JsonlMarketDataRecorder


TIMEFRAMES = {
    "15m": {
        "interval": "15",
        "minutes": 15,
    },
    "1h": {
        "interval": "60",
        "minutes": 60,
    },
    "4h": {
        "interval": "240",
        "minutes": 240,
    },
}


class Candle(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    timeframe: str

    start_ts_ms: int
    end_ts_ms: int

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    volume: Decimal
    turnover: Decimal

    confirmed: bool

    exchange_response_ts_ms: int
    local_receive_ts_utc: datetime


class CandleService:
    def __init__(
        self,
        client: BybitPublicRestClient | None = None,
        recorder: JsonlMarketDataRecorder | None = None,
    ):
        self.client = client or BybitPublicRestClient()
        self.recorder = recorder

    def fetch_closed_candles(
        self,
        timeframe: str,
        limit: int = 200,
    ) -> list[Candle]:

        if timeframe not in TIMEFRAMES:
            raise ValueError(
                f"Unsupported timeframe: {timeframe}. "
                f"Supported: {list(TIMEFRAMES.keys())}"
            )

        config = TIMEFRAMES[timeframe]

        response = self.client.get_klines(
            interval=config["interval"],
            limit=limit,
        )

        if self.recorder is not None:
            self.recorder.record(
                f"historical_kline_{timeframe}",
                response,
            )

        server_time_ms = self.client.get_server_time_ms()

        interval_ms = (
            config["minutes"]
            * 60
            * 1000
        )

        exchange_response_ts_ms = int(
            response["time"]
        )

        local_receive_ts = datetime.now(
            timezone.utc
        )

        raw_candles = response[
            "result"
        ]["list"]

        candles: list[Candle] = []

        for item in raw_candles:
            start_ts_ms = int(item[0])

            end_ts_ms = (
                start_ts_ms
                + interval_ms
            )

            confirmed = (
                server_time_ms
                >= end_ts_ms
            )

            if not confirmed:
                continue

            candle = Candle(
                symbol=SYMBOL,
                timeframe=timeframe,
                start_ts_ms=start_ts_ms,
                end_ts_ms=end_ts_ms,
                open=Decimal(item[1]),
                high=Decimal(item[2]),
                low=Decimal(item[3]),
                close=Decimal(item[4]),
                volume=Decimal(item[5]),
                turnover=Decimal(item[6]),
                confirmed=True,
                exchange_response_ts_ms=(
                    exchange_response_ts_ms
                ),
                local_receive_ts_utc=(
                    local_receive_ts
                ),
            )

            candles.append(candle)

        # Bybit returns newest -> oldest.
        # Internally we want oldest -> newest.
        candles.sort(
            key=lambda candle: candle.start_ts_ms
        )

        return candles