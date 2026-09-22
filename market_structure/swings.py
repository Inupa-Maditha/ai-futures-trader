from __future__ import annotations

from dataclasses import dataclass

from market_data.candles import Candle


@dataclass(frozen=True, slots=True)
class SwingPoint:
    timeframe: str
    index: int
    confirmed_index: int

    start_ts_ms: int
    confirmed_ts_ms: int

    price: float
    kind: str  # "HIGH" or "LOW"


class SwingDetector:
    def __init__(
        self,
        left_bars: int = 2,
        right_bars: int = 2,
    ):
        if left_bars < 1:
            raise ValueError(
                "left_bars must be at least 1."
            )

        if right_bars < 1:
            raise ValueError(
                "right_bars must be at least 1."
            )

        self.left_bars = left_bars
        self.right_bars = right_bars

    def detect(
        self,
        candles: list[Candle],
    ) -> list[SwingPoint]:

        if any(
            not candle.confirmed
            for candle in candles
        ):
            raise ValueError(
                "Swing detection requires "
                "confirmed candles only."
            )

        minimum = (
            self.left_bars
            + self.right_bars
            + 1
        )

        if len(candles) < minimum:
            return []

        swings: list[SwingPoint] = []

        start_index = self.left_bars

        end_index = (
            len(candles)
            - self.right_bars
        )

        for index in range(
            start_index,
            end_index,
        ):
            current = candles[index]

            current_high = float(
                current.high
            )

            current_low = float(
                current.low
            )

            left = candles[
                index - self.left_bars:
                index
            ]

            right = candles[
                index + 1:
                index + 1 + self.right_bars
            ]

            left_highs = [
                float(candle.high)
                for candle in left
            ]

            right_highs = [
                float(candle.high)
                for candle in right
            ]

            left_lows = [
                float(candle.low)
                for candle in left
            ]

            right_lows = [
                float(candle.low)
                for candle in right
            ]

            is_swing_high = (
                current_high > max(left_highs)
                and current_high > max(right_highs)
            )

            is_swing_low = (
                current_low < min(left_lows)
                and current_low < min(right_lows)
            )

            if is_swing_high:
                confirmation_index = (
                    index + self.right_bars
                )

                swings.append(
                    SwingPoint(
                        timeframe=current.timeframe,
                        index=index,
                        confirmed_index=confirmation_index,
                        start_ts_ms=current.start_ts_ms,
                        confirmed_ts_ms=candles[
                            confirmation_index
                        ].end_ts_ms,
                        price=current_high,
                        kind="HIGH",
                    )
                )

            if is_swing_low:
                confirmation_index = (
                    index + self.right_bars
                )

                swings.append(
                    SwingPoint(
                        timeframe=current.timeframe,
                        index=index,
                        confirmed_index=confirmation_index,
                        start_ts_ms=current.start_ts_ms,
                        confirmed_ts_ms=candles[
                            confirmation_index
                        ].end_ts_ms,
                        price=current_low,
                        kind="LOW",
                    )
                )

        swings.sort(
            key=lambda swing: swing.index
        )

        return swings


def normalize_swings(
    swings: list[SwingPoint],
) -> list[SwingPoint]:

    if not swings:
        return []

    ordered = sorted(
        swings,
        key=lambda swing: swing.index,
    )

    grouped: dict[
        int,
        list[SwingPoint],
    ] = {}

    for swing in ordered:
        grouped.setdefault(
            swing.index,
            [],
        ).append(swing)

    filtered: list[SwingPoint] = []

    for index in sorted(grouped):
        points = grouped[index]

        kinds = {
            point.kind
            for point in points
        }

        # Same candle detected as both
        # HIGH and LOW.
        # OHLC data cannot tell which
        # happened first, so skip it.
        if len(kinds) > 1:
            continue

        filtered.append(
            points[0]
        )

    normalized: list[SwingPoint] = []

    for swing in filtered:

        if not normalized:
            normalized.append(swing)
            continue

        previous = normalized[-1]

        # Alternating HIGH -> LOW
        # or LOW -> HIGH.
        if swing.kind != previous.kind:
            normalized.append(swing)
            continue

        # Consecutive HIGHs:
        # keep the higher one.
        if swing.kind == "HIGH":
            if swing.price > previous.price:
                normalized[-1] = swing

        # Consecutive LOWs:
        # keep the lower one.
        elif swing.kind == "LOW":
            if swing.price < previous.price:
                normalized[-1] = swing

    return normalized