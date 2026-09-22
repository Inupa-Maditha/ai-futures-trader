from __future__ import annotations

import json

from dataclasses import (
    dataclass,
    fields,
    is_dataclass,
)
from datetime import datetime, timezone
from enum import Enum

from config.settings import SYMBOL

from indicators.technical import (
    TechnicalIndicatorEngine,
    TechnicalIndicatorSnapshot,
)

from market_data.candles import (
    CandleService,
)

from market_structure.breaks import (
    BreakType,
    StructureBreakDetector,
    TrendState,
)

from market_structure.structure import (
    StructureClassifier,
)

from market_structure.swings import (
    SwingDetector,
    normalize_swings,
)


class TrendAlignment(str, Enum):
    BULLISH_ALIGNED = "BULLISH_ALIGNED"
    BEARISH_ALIGNED = "BEARISH_ALIGNED"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class TimeframeAnalysisSnapshot:
    timeframe: str

    latest_candle_start_ts_ms: int
    latest_close: float

    indicators: TechnicalIndicatorSnapshot

    trend: TrendState

    latest_structure_label: str | None

    latest_swing_high: float | None
    latest_swing_low: float | None

    latest_break_type: BreakType | None
    latest_break_level: float | None
    latest_break_ts_ms: int | None

    raw_swing_count: int
    normalized_swing_count: int
    structure_break_count: int


@dataclass(frozen=True, slots=True)
class MultiTimeframeAnalysisSnapshot:
    symbol: str
    generated_at_utc: datetime

    timeframe_15m: TimeframeAnalysisSnapshot
    timeframe_1h: TimeframeAnalysisSnapshot
    timeframe_4h: TimeframeAnalysisSnapshot

    trend_alignment: TrendAlignment

    def to_dict(self) -> dict:
        return _serialize_value(self)

    def to_json(
        self,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=False,
        )


class MultiTimeframeAnalyzer:
    def __init__(
        self,
        candle_service: CandleService | None = None,
    ):
        self.candle_service = (
            candle_service
            or CandleService()
        )

        self.indicator_engine = (
            TechnicalIndicatorEngine()
        )

        self.swing_detector = SwingDetector(
            left_bars=2,
            right_bars=2,
        )

        self.structure_classifier = (
            StructureClassifier()
        )

        self.break_detector = (
            StructureBreakDetector()
        )

    def analyze_timeframe(
        self,
        timeframe: str,
    ) -> TimeframeAnalysisSnapshot:

        candles = (
            self.candle_service
            .fetch_closed_candles(
                timeframe=timeframe,
                limit=250,
            )
        )

        indicators = (
            self.indicator_engine.calculate(
                candles
            )
        )

        raw_swings = (
            self.swing_detector.detect(
                candles
            )
        )

        normalized_swings = (
            normalize_swings(
                raw_swings
            )
        )

        classified_swings = (
            self.structure_classifier.classify(
                normalized_swings
            )
        )

        breaks, state = (
            self.break_detector.detect(
                candles,
                raw_swings,
            )
        )

        latest_structure_label = None

        if classified_swings:
            latest_structure_label = (
                classified_swings[-1]
                .classification
            )

        latest_swing_high = None

        if state.latest_swing_high is not None:
            latest_swing_high = (
                state.latest_swing_high.price
            )

        latest_swing_low = None

        if state.latest_swing_low is not None:
            latest_swing_low = (
                state.latest_swing_low.price
            )

        latest_break_type = None
        latest_break_level = None
        latest_break_ts_ms = None

        if state.latest_break is not None:
            latest_break_type = (
                state.latest_break.break_type
            )

            latest_break_level = (
                state.latest_break.broken_level
            )

            latest_break_ts_ms = (
                state.latest_break
                .candle_start_ts_ms
            )

        latest_candle = candles[-1]

        return TimeframeAnalysisSnapshot(
            timeframe=timeframe,

            latest_candle_start_ts_ms=(
                latest_candle.start_ts_ms
            ),

            latest_close=float(
                latest_candle.close
            ),

            indicators=indicators,

            trend=state.trend,

            latest_structure_label=(
                latest_structure_label
            ),

            latest_swing_high=(
                latest_swing_high
            ),

            latest_swing_low=(
                latest_swing_low
            ),

            latest_break_type=(
                latest_break_type
            ),

            latest_break_level=(
                latest_break_level
            ),

            latest_break_ts_ms=(
                latest_break_ts_ms
            ),

            raw_swing_count=len(
                raw_swings
            ),

            normalized_swing_count=len(
                normalized_swings
            ),

            structure_break_count=len(
                breaks
            ),
        )

    def analyze(
        self,
    ) -> MultiTimeframeAnalysisSnapshot:

        tf_15m = self.analyze_timeframe(
            "15m"
        )

        tf_1h = self.analyze_timeframe(
            "1h"
        )

        tf_4h = self.analyze_timeframe(
            "4h"
        )

        alignment = self._get_alignment(
            [
                tf_15m.trend,
                tf_1h.trend,
                tf_4h.trend,
            ]
        )

        return MultiTimeframeAnalysisSnapshot(
            symbol=SYMBOL,

            generated_at_utc=datetime.now(
                timezone.utc
            ),

            timeframe_15m=tf_15m,
            timeframe_1h=tf_1h,
            timeframe_4h=tf_4h,

            trend_alignment=alignment,
        )

    @staticmethod
    def _get_alignment(
        trends: list[TrendState],
    ) -> TrendAlignment:

        if all(
            trend == TrendState.BULLISH
            for trend in trends
        ):
            return (
                TrendAlignment.BULLISH_ALIGNED
            )

        if all(
            trend == TrendState.BEARISH
            for trend in trends
        ):
            return (
                TrendAlignment.BEARISH_ALIGNED
            )

        if all(
            trend == TrendState.NEUTRAL
            for trend in trends
        ):
            return TrendAlignment.NEUTRAL

        return TrendAlignment.MIXED


def _serialize_value(value):
    if is_dataclass(value):
        return {
            field.name: _serialize_value(
                getattr(value, field.name)
            )
            for field in fields(value)
        }

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, list):
        return [
            _serialize_value(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            _serialize_value(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            key: _serialize_value(item)
            for key, item in value.items()
        }

    return value