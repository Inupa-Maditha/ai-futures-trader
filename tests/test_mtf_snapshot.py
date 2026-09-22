from datetime import datetime, timezone

from context_engine.technical_snapshot import (
    MultiTimeframeAnalysisSnapshot,
    MultiTimeframeAnalyzer,
    TimeframeAnalysisSnapshot,
    TrendAlignment,
)

from indicators.technical import (
    TechnicalIndicatorSnapshot,
)

from market_structure.breaks import (
    BreakType,
    TrendState,
)


def make_indicators(
    timeframe: str,
) -> TechnicalIndicatorSnapshot:

    return TechnicalIndicatorSnapshot(
        timeframe=timeframe,
        candle_start_ts_ms=1000,
        close=100.0,
        ema_20=99.0,
        ema_50=98.0,
        ema_200=90.0,
        rsi_14=55.0,
        atr_14=2.0,
        atr_percent=2.0,
    )


def make_timeframe_snapshot(
    timeframe: str,
    trend: TrendState,
) -> TimeframeAnalysisSnapshot:

    return TimeframeAnalysisSnapshot(
        timeframe=timeframe,
        latest_candle_start_ts_ms=1000,
        latest_close=100.0,
        indicators=make_indicators(
            timeframe
        ),
        trend=trend,
        latest_structure_label="HH",
        latest_swing_high=105.0,
        latest_swing_low=95.0,
        latest_break_type=(
            BreakType.BOS_BULLISH
        ),
        latest_break_level=105.0,
        latest_break_ts_ms=1000,
        raw_swing_count=10,
        normalized_swing_count=8,
        structure_break_count=3,
    )


def test_bullish_alignment():
    result = (
        MultiTimeframeAnalyzer
        ._get_alignment(
            [
                TrendState.BULLISH,
                TrendState.BULLISH,
                TrendState.BULLISH,
            ]
        )
    )

    assert (
        result
        == TrendAlignment.BULLISH_ALIGNED
    )


def test_bearish_alignment():
    result = (
        MultiTimeframeAnalyzer
        ._get_alignment(
            [
                TrendState.BEARISH,
                TrendState.BEARISH,
                TrendState.BEARISH,
            ]
        )
    )

    assert (
        result
        == TrendAlignment.BEARISH_ALIGNED
    )


def test_neutral_alignment():
    result = (
        MultiTimeframeAnalyzer
        ._get_alignment(
            [
                TrendState.NEUTRAL,
                TrendState.NEUTRAL,
                TrendState.NEUTRAL,
            ]
        )
    )

    assert (
        result
        == TrendAlignment.NEUTRAL
    )


def test_mixed_alignment():
    result = (
        MultiTimeframeAnalyzer
        ._get_alignment(
            [
                TrendState.BEARISH,
                TrendState.BULLISH,
                TrendState.BULLISH,
            ]
        )
    )

    assert (
        result
        == TrendAlignment.MIXED
    )


def test_snapshot_serialization():
    snapshot = MultiTimeframeAnalysisSnapshot(
        symbol="BTCUSDT",
        generated_at_utc=datetime(
            2026,
            9,
            22,
            tzinfo=timezone.utc,
        ),
        timeframe_15m=(
            make_timeframe_snapshot(
                "15m",
                TrendState.BEARISH,
            )
        ),
        timeframe_1h=(
            make_timeframe_snapshot(
                "1h",
                TrendState.BULLISH,
            )
        ),
        timeframe_4h=(
            make_timeframe_snapshot(
                "4h",
                TrendState.BULLISH,
            )
        ),
        trend_alignment=(
            TrendAlignment.MIXED
        ),
    )

    data = snapshot.to_dict()

    assert data["symbol"] == "BTCUSDT"

    assert (
        data["trend_alignment"]
        == "MIXED"
    )

    assert (
        data["timeframe_15m"]["trend"]
        == "BEARISH"
    )

    assert (
        data["timeframe_1h"]
        ["latest_break_type"]
        == "BOS_BULLISH"
    )

    assert (
        data["generated_at_utc"]
        == "2026-09-22T00:00:00+00:00"
    )

    json_output = snapshot.to_json()

    assert '"BTCUSDT"' in json_output
    assert '"MIXED"' in json_output
    assert '"BEARISH"' in json_output