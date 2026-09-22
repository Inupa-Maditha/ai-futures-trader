from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from market_data.candles import Candle
from market_structure.swings import SwingPoint


class TrendState(str, Enum):
    NEUTRAL = "NEUTRAL"
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class BreakType(str, Enum):
    BOS_BULLISH = "BOS_BULLISH"
    BOS_BEARISH = "BOS_BEARISH"
    CHOCH_BULLISH = "CHOCH_BULLISH"
    CHOCH_BEARISH = "CHOCH_BEARISH"


@dataclass(frozen=True, slots=True)
class StructureBreak:
    timeframe: str

    break_type: BreakType

    candle_index: int
    candle_start_ts_ms: int
    close_price: float

    broken_swing_index: int
    broken_level: float

    trend_before: TrendState
    trend_after: TrendState


@dataclass(frozen=True, slots=True)
class StructureState:
    timeframe: str
    trend: TrendState

    latest_swing_high: SwingPoint | None
    latest_swing_low: SwingPoint | None

    latest_break: StructureBreak | None


class StructureBreakDetector:
    def detect(
        self,
        candles: list[Candle],
        swings: list[SwingPoint],
    ) -> tuple[
        list[StructureBreak],
        StructureState,
    ]:

        if not candles:
            raise ValueError(
                "Candles cannot be empty."
            )

        if any(
            not candle.confirmed
            for candle in candles
        ):
            raise ValueError(
                "Structure break detection requires "
                "confirmed candles only."
            )

        timeframe = candles[-1].timeframe

        if any(
            candle.timeframe != timeframe
            for candle in candles
        ):
            raise ValueError(
                "Candles must belong to one timeframe."
            )

        if any(
            swing.timeframe != timeframe
            for swing in swings
        ):
            raise ValueError(
                "Swings must belong to the same "
                "timeframe as candles."
            )

        # Remove ambiguous pivots where the same
        # candle is detected as both HIGH and LOW.
        swings_by_index: dict[
            int,
            list[SwingPoint],
        ] = {}

        for swing in swings:
            swings_by_index.setdefault(
                swing.index,
                [],
            ).append(swing)

        valid_swings: list[SwingPoint] = []

        for points in swings_by_index.values():
            kinds = {
                point.kind
                for point in points
            }

            # OHLC data cannot tell whether
            # HIGH or LOW happened first.
            if len(kinds) > 1:
                continue

            valid_swings.extend(points)

        # A swing becomes usable only after its
        # right-side confirmation candles close.
        swings_by_confirmation: dict[
            int,
            list[SwingPoint],
        ] = {}

        for swing in valid_swings:
            swings_by_confirmation.setdefault(
                swing.confirmed_index,
                [],
            ).append(swing)

        latest_high: SwingPoint | None = None
        latest_low: SwingPoint | None = None

        trend = TrendState.NEUTRAL

        breaks: list[StructureBreak] = []

        broken_swing_keys: set[
            tuple[str, int]
        ] = set()

        for candle_index, candle in enumerate(
            candles
        ):
            # Only expose confirmed swings.
            for swing in swings_by_confirmation.get(
                candle_index,
                [],
            ):
                if swing.kind == "HIGH":
                    latest_high = swing

                elif swing.kind == "LOW":
                    latest_low = swing

            close = float(candle.close)

            # Bullish structure break.
            if latest_high is not None:
                high_key = (
                    "HIGH",
                    latest_high.index,
                )

                if (
                    high_key not in broken_swing_keys
                    and close > latest_high.price
                ):
                    trend_before = trend

                    if trend == TrendState.BEARISH:
                        break_type = (
                            BreakType.CHOCH_BULLISH
                        )
                    else:
                        break_type = (
                            BreakType.BOS_BULLISH
                        )

                    trend = TrendState.BULLISH

                    event = StructureBreak(
                        timeframe=timeframe,
                        break_type=break_type,
                        candle_index=candle_index,
                        candle_start_ts_ms=(
                            candle.start_ts_ms
                        ),
                        close_price=close,
                        broken_swing_index=(
                            latest_high.index
                        ),
                        broken_level=(
                            latest_high.price
                        ),
                        trend_before=trend_before,
                        trend_after=trend,
                    )

                    breaks.append(event)

                    broken_swing_keys.add(
                        high_key
                    )

            # Bearish structure break.
            if latest_low is not None:
                low_key = (
                    "LOW",
                    latest_low.index,
                )

                if (
                    low_key not in broken_swing_keys
                    and close < latest_low.price
                ):
                    trend_before = trend

                    if trend == TrendState.BULLISH:
                        break_type = (
                            BreakType.CHOCH_BEARISH
                        )
                    else:
                        break_type = (
                            BreakType.BOS_BEARISH
                        )

                    trend = TrendState.BEARISH

                    event = StructureBreak(
                        timeframe=timeframe,
                        break_type=break_type,
                        candle_index=candle_index,
                        candle_start_ts_ms=(
                            candle.start_ts_ms
                        ),
                        close_price=close,
                        broken_swing_index=(
                            latest_low.index
                        ),
                        broken_level=(
                            latest_low.price
                        ),
                        trend_before=trend_before,
                        trend_after=trend,
                    )

                    breaks.append(event)

                    broken_swing_keys.add(
                        low_key
                    )

        state = StructureState(
            timeframe=timeframe,
            trend=trend,
            latest_swing_high=latest_high,
            latest_swing_low=latest_low,
            latest_break=(
                breaks[-1]
                if breaks
                else None
            ),
        )

        return breaks, state