from __future__ import annotations

from dataclasses import dataclass

from market_data.candles import Candle


@dataclass(frozen=True, slots=True)
class TechnicalIndicatorSnapshot:
    timeframe: str
    candle_start_ts_ms: int
    close: float

    ema_20: float
    ema_50: float
    ema_200: float

    rsi_14: float
    atr_14: float
    atr_percent: float


def ema(
    values: list[float],
    period: int,
) -> list[float | None]:
    if period <= 0:
        raise ValueError(
            "EMA period must be greater than zero."
        )

    result: list[float | None] = [
        None
    ] * len(values)

    if len(values) < period:
        return result

    # Seed EMA with SMA.
    seed = sum(
        values[:period]
    ) / period

    result[period - 1] = seed

    multiplier = 2 / (period + 1)

    previous_ema = seed

    for index in range(
        period,
        len(values),
    ):
        current_ema = (
            values[index] - previous_ema
        ) * multiplier + previous_ema

        result[index] = current_ema
        previous_ema = current_ema

    return result


def rsi(
    values: list[float],
    period: int = 14,
) -> list[float | None]:
    if period <= 0:
        raise ValueError(
            "RSI period must be greater than zero."
        )

    result: list[float | None] = [
        None
    ] * len(values)

    if len(values) <= period:
        return result

    gains: list[float] = []
    losses: list[float] = []

    for index in range(
        1,
        period + 1,
    ):
        change = (
            values[index]
            - values[index - 1]
        )

        gains.append(
            max(change, 0.0)
        )

        losses.append(
            max(-change, 0.0)
        )

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    result[period] = _rsi_from_averages(
        average_gain,
        average_loss,
    )

    for index in range(
        period + 1,
        len(values),
    ):
        change = (
            values[index]
            - values[index - 1]
        )

        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        average_gain = (
            (
                average_gain
                * (period - 1)
            )
            + gain
        ) / period

        average_loss = (
            (
                average_loss
                * (period - 1)
            )
            + loss
        ) / period

        result[index] = _rsi_from_averages(
            average_gain,
            average_loss,
        )

    return result


def _rsi_from_averages(
    average_gain: float,
    average_loss: float,
) -> float:
    if average_loss == 0:
        if average_gain == 0:
            return 50.0

        return 100.0

    relative_strength = (
        average_gain / average_loss
    )

    return (
        100
        - (
            100
            / (1 + relative_strength)
        )
    )


def atr(
    candles: list[Candle],
    period: int = 14,
) -> list[float | None]:
    if period <= 0:
        raise ValueError(
            "ATR period must be greater than zero."
        )

    result: list[float | None] = [
        None
    ] * len(candles)

    if len(candles) < period:
        return result

    true_ranges: list[float] = []

    for index, candle in enumerate(
        candles
    ):
        high = float(candle.high)
        low = float(candle.low)

        if index == 0:
            true_range = high - low

        else:
            previous_close = float(
                candles[index - 1].close
            )

            true_range = max(
                high - low,
                abs(
                    high - previous_close
                ),
                abs(
                    low - previous_close
                ),
            )

        true_ranges.append(true_range)

    initial_atr = (
        sum(true_ranges[:period])
        / period
    )

    result[period - 1] = initial_atr

    previous_atr = initial_atr

    for index in range(
        period,
        len(candles),
    ):
        current_atr = (
            (
                previous_atr
                * (period - 1)
            )
            + true_ranges[index]
        ) / period

        result[index] = current_atr
        previous_atr = current_atr

    return result


class TechnicalIndicatorEngine:
    MINIMUM_CANDLES = 200

    def calculate(
        self,
        candles: list[Candle],
    ) -> TechnicalIndicatorSnapshot:

        if len(candles) < self.MINIMUM_CANDLES:
            raise ValueError(
                "At least 200 closed candles "
                "are required."
            )

        # Safety rule:
        # never calculate strategy indicators
        # from an unconfirmed candle.
        if any(
            not candle.confirmed
            for candle in candles
        ):
            raise ValueError(
                "Indicator input contains "
                "an unconfirmed candle."
            )

        closes = [
            float(candle.close)
            for candle in candles
        ]

        ema_20_values = ema(
            closes,
            period=20,
        )

        ema_50_values = ema(
            closes,
            period=50,
        )

        ema_200_values = ema(
            closes,
            period=200,
        )

        rsi_14_values = rsi(
            closes,
            period=14,
        )

        atr_14_values = atr(
            candles,
            period=14,
        )

        latest = candles[-1]

        ema_20_latest = ema_20_values[-1]
        ema_50_latest = ema_50_values[-1]
        ema_200_latest = ema_200_values[-1]
        rsi_14_latest = rsi_14_values[-1]
        atr_14_latest = atr_14_values[-1]

        if any(
            value is None
            for value in (
                ema_20_latest,
                ema_50_latest,
                ema_200_latest,
                rsi_14_latest,
                atr_14_latest,
            )
        ):
            raise RuntimeError(
                "Indicator warm-up incomplete."
            )

        close = float(latest.close)

        atr_percent = (
            atr_14_latest
            / close
            * 100
        )

        return TechnicalIndicatorSnapshot(
            timeframe=latest.timeframe,
            candle_start_ts_ms=(
                latest.start_ts_ms
            ),
            close=close,
            ema_20=ema_20_latest,
            ema_50=ema_50_latest,
            ema_200=ema_200_latest,
            rsi_14=rsi_14_latest,
            atr_14=atr_14_latest,
            atr_percent=atr_percent,
        )