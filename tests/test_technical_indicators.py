from datetime import datetime, timezone
from decimal import Decimal

import pytest

from indicators.technical import (
    TechnicalIndicatorEngine,
    atr,
    ema,
    rsi,
)
from market_data.candles import Candle


def make_candle(
    index: int,
    confirmed: bool = True,
) -> Candle:
    close = Decimal(100 + index)

    return Candle(
        symbol="BTCUSDT",
        timeframe="15m",
        start_ts_ms=index * 900_000,
        end_ts_ms=(index + 1) * 900_000,
        open=close - Decimal("0.5"),
        high=close + Decimal("1"),
        low=close - Decimal("1"),
        close=close,
        volume=Decimal("10"),
        turnover=Decimal("1000"),
        confirmed=confirmed,
        exchange_response_ts_ms=1_000_000,
        local_receive_ts_utc=datetime.now(
            timezone.utc
        ),
    )


def test_ema_known_values():
    values = [
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
    ]

    result = ema(
        values,
        period=3,
    )

    assert result[0] is None
    assert result[1] is None

    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(3.0)
    assert result[4] == pytest.approx(4.0)


def test_rsi_strictly_increasing_is_100():
    values = [
        float(value)
        for value in range(1, 30)
    ]

    result = rsi(
        values,
        period=14,
    )

    assert result[-1] == pytest.approx(
        100.0
    )


def test_rsi_flat_market_is_50():
    values = [100.0] * 30

    result = rsi(
        values,
        period=14,
    )

    assert result[-1] == pytest.approx(
        50.0
    )


def test_atr_constant_true_range():
    candles = [
        make_candle(index)
        for index in range(30)
    ]

    result = atr(
        candles,
        period=14,
    )

    assert result[-1] == pytest.approx(
        2.0
    )


def test_engine_requires_200_candles():
    candles = [
        make_candle(index)
        for index in range(199)
    ]

    engine = TechnicalIndicatorEngine()

    with pytest.raises(
        ValueError,
        match="At least 200 closed candles",
    ):
        engine.calculate(candles)


def test_engine_rejects_unconfirmed_candle():
    candles = [
        make_candle(index)
        for index in range(199)
    ]

    candles.append(
        make_candle(
            index=199,
            confirmed=False,
        )
    )

    engine = TechnicalIndicatorEngine()

    with pytest.raises(
        ValueError,
        match="unconfirmed candle",
    ):
        engine.calculate(candles)


def test_indicator_engine_snapshot():
    candles = [
        make_candle(index)
        for index in range(220)
    ]

    engine = TechnicalIndicatorEngine()

    snapshot = engine.calculate(
        candles
    )

    assert snapshot.timeframe == "15m"

    assert snapshot.close == pytest.approx(
        319.0
    )

    assert (
        snapshot.ema_20
        > snapshot.ema_50
        > snapshot.ema_200
    )

    assert (
        snapshot.close
        > snapshot.ema_20
    )

    assert snapshot.rsi_14 == pytest.approx(
        100.0
    )

    assert snapshot.atr_14 == pytest.approx(
        2.0
    )

    assert snapshot.atr_percent > 0