from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from config.settings import SYMBOL
from market_data.rest_client import BybitPublicRestClient
from data_quality.freshness import DataHealthMonitor
from market_data.recorder import JsonlMarketDataRecorder


@dataclass(frozen=True, slots=True)
class OpenInterestSnapshot:
    symbol: str
    interval: str

    current: Decimal
    previous: Decimal | None

    change_absolute: Decimal | None
    change_percent: Decimal | None

    observation_ts_ms: int
    response_ts_ms: int

    local_receive_ts_utc: datetime


@dataclass(frozen=True, slots=True)
class FundingSnapshot:
    symbol: str

    current_funding_rate: Decimal
    next_funding_ts_ms: int
    funding_interval_minutes: int

    response_ts_ms: int
    local_receive_ts_utc: datetime


@dataclass(frozen=True, slots=True)
class PositioningSnapshot:
    symbol: str
    period: str

    account_holder_long_ratio: Decimal
    account_holder_short_ratio: Decimal
    long_short_account_ratio: Decimal | None

    observation_ts_ms: int
    response_ts_ms: int

    local_receive_ts_utc: datetime


class BybitDerivativesService:
    def __init__(
        self,
        client: BybitPublicRestClient | None = None,
        health_monitor: DataHealthMonitor | None = None,
        recorder: JsonlMarketDataRecorder | None = None,
    ):
        self.client = client or BybitPublicRestClient()
        self.health_monitor = health_monitor
        self.recorder = recorder

    def _record_raw(
        self,
        source_name: str,
        response: dict,
    ) -> None:
        if self.recorder is None:
            return

        self.recorder.record(
            source_name,
            response,
        )

    def _record_health(
        self,
        source_name: str,
        event_ts_ms: int,
    ) -> None:
        if self.health_monitor is None:
            return

        health = self.health_monitor.get(
            source_name
        )

        health.record_event(
            event_ts_ms=event_ts_ms
        )

    def get_open_interest(
        self,
        interval: str = "15min",
    ) -> OpenInterestSnapshot:

        response = self.client.get_open_interest(
            interval=interval,
            limit=2,
        )

        self._record_raw(
            "open_interest",
            response,
        )

        records = response["result"]["list"]

        if not records:
            raise RuntimeError(
                "Open Interest response contained no data."
            )

        records = sorted(
            records,
            key=lambda item: int(item["timestamp"]),
        )

        latest = records[-1]

        current = Decimal(latest["openInterest"])

        previous = None
        change_absolute = None
        change_percent = None

        if len(records) >= 2:
            previous = Decimal(
                records[-2]["openInterest"]
            )

            change_absolute = current - previous

            if previous != 0:
                change_percent = (
                    change_absolute / previous
                ) * Decimal("100")

        snapshot = OpenInterestSnapshot(
            symbol=SYMBOL,
            interval=interval,
            current=current,
            previous=previous,
            change_absolute=change_absolute,
            change_percent=change_percent,
            observation_ts_ms=int(
                latest["timestamp"]
            ),
            response_ts_ms=int(response["time"]),
            local_receive_ts_utc=datetime.now(
                timezone.utc
            ),
        )

        self._record_health(
            "open_interest",
            snapshot.observation_ts_ms,
        )

        return snapshot

    def get_funding(self) -> FundingSnapshot:

        ticker_response = self.client.get_ticker()

        instrument_response = (
            self.client.get_instrument_info()
        )

        self._record_raw(
            "funding_ticker",
            ticker_response,
        )

        self._record_raw(
            "instrument_info",
            instrument_response,
        )

        tickers = ticker_response["result"]["list"]

        if not tickers:
            raise RuntimeError(
                "Ticker response contained no data."
            )

        instruments = (
            instrument_response["result"]["list"]
        )

        if not instruments:
            raise RuntimeError(
                "Instrument information not found."
            )

        ticker = tickers[0]
        instrument = instruments[0]

        snapshot = FundingSnapshot(
            symbol=SYMBOL,
            current_funding_rate=Decimal(
                ticker["fundingRate"]
            ),
            next_funding_ts_ms=int(
                ticker["nextFundingTime"]
            ),
            funding_interval_minutes=int(
                instrument["fundingInterval"]
            ),
            response_ts_ms=int(
                ticker_response["time"]
            ),
            local_receive_ts_utc=datetime.now(
                timezone.utc
            ),
        )

        self._record_health(
            "funding",
            snapshot.response_ts_ms,
        )

        return snapshot

    def get_positioning(
        self,
        period: str = "15min",
    ) -> PositioningSnapshot:

        response = self.client.get_long_short_ratio(
            period=period,
            limit=2,
        )

        self._record_raw(
            "account_positioning",
            response,
        )
        records = response["result"]["list"]

        if not records:
            raise RuntimeError(
                "Long/short ratio response "
                "contained no data."
            )

        records = sorted(
            records,
            key=lambda item: int(
                item["timestamp"]
            ),
        )

        latest = records[-1]

        long_ratio = Decimal(
            latest["buyRatio"]
        )

        short_ratio = Decimal(
            latest["sellRatio"]
        )

        account_ratio = None

        if short_ratio != 0:
            account_ratio = (
                long_ratio / short_ratio
            )

        snapshot = PositioningSnapshot(
            symbol=SYMBOL,
            period=period,
            account_holder_long_ratio=long_ratio,
            account_holder_short_ratio=short_ratio,
            long_short_account_ratio=account_ratio,
            observation_ts_ms=int(
                latest["timestamp"]
            ),
            response_ts_ms=int(
                response["time"]
            ),
            local_receive_ts_utc=datetime.now(
                timezone.utc
            ),
        )

        self._record_health(
            "account_positioning",
            snapshot.observation_ts_ms,
        )

        return snapshot