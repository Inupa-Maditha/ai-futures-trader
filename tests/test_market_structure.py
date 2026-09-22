from datetime import datetime, timezone
from decimal import Decimal

import pytest

from market_data.candles import Candle

from market_structure.breaks import (
    BreakType,
    StructureBreakDetector,
    TrendState,
)

from market_structure.swings import (
    SwingPoint,
    normalize_swings,
)


def make_candle(
    index: int,
    close: float,
    high: float | None = None,
    low: float | None = None,
    confirmed: bool = True,
) -> Candle:

    if high is None:
        high = close + 1

    if low is None:
        low = close - 1

    return Candle(
        symbol="BTCUSDT",
        timeframe="15m",
        start_ts_ms=index * 900_000,
        end_ts_ms=(index + 1) * 900_000,
        open=Decimal(str(close)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal("10"),
        turnover=Decimal("1000"),
        confirmed=confirmed,
        exchange_response_ts_ms=1_000_000,
        local_receive_ts_utc=datetime.now(
            timezone.utc
        ),
    )


def make_swing(
    index: int,
    confirmed_index: int,
    price: float,
    kind: str,
) -> SwingPoint:

    return SwingPoint(
        timeframe="15m",
        index=index,
        confirmed_index=confirmed_index,
        start_ts_ms=index * 900_000,
        confirmed_ts_ms=(
            (confirmed_index + 1)
            * 900_000
        ),
        price=price,
        kind=kind,
    )


def test_normalize_keeps_more_extreme_high():
    swings = [
        make_swing(
            index=1,
            confirmed_index=3,
            price=105,
            kind="HIGH",
        ),
        make_swing(
            index=3,
            confirmed_index=5,
            price=110,
            kind="HIGH",
        ),
        make_swing(
            index=5,
            confirmed_index=7,
            price=95,
            kind="LOW",
        ),
    ]

    result = normalize_swings(swings)

    assert len(result) == 2

    assert result[0].kind == "HIGH"
    assert result[0].price == 110

    assert result[1].kind == "LOW"
    assert result[1].price == 95


def test_normalize_keeps_more_extreme_low():
    swings = [
        make_swing(
            index=1,
            confirmed_index=3,
            price=95,
            kind="LOW",
        ),
        make_swing(
            index=3,
            confirmed_index=5,
            price=90,
            kind="LOW",
        ),
        make_swing(
            index=5,
            confirmed_index=7,
            price=110,
            kind="HIGH",
        ),
    ]

    result = normalize_swings(swings)

    assert len(result) == 2

    assert result[0].kind == "LOW"
    assert result[0].price == 90


def test_same_candle_high_and_low_is_removed():
    swings = [
        make_swing(
            index=2,
            confirmed_index=4,
            price=110,
            kind="HIGH",
        ),
        make_swing(
            index=2,
            confirmed_index=4,
            price=90,
            kind="LOW",
        ),
    ]

    result = normalize_swings(swings)

    assert result == []


def test_wick_does_not_trigger_bullish_break():
    candles = [
        make_candle(
            index=0,
            close=100,
        ),
        make_candle(
            index=1,
            close=104,
            high=110,
            low=99,
        ),
        make_candle(
            index=2,
            close=106,
            high=107,
            low=103,
        ),
    ]

    swing = make_swing(
        index=0,
        confirmed_index=1,
        price=105,
        kind="HIGH",
    )

    detector = StructureBreakDetector()

    breaks, state = detector.detect(
        candles,
        [swing],
    )

    assert len(breaks) == 1

    # Candle 1 wicked above 105,
    # but closed at 104.
    # Break must happen on candle 2.
    assert breaks[0].candle_index == 2

    assert (
        breaks[0].break_type
        == BreakType.BOS_BULLISH
    )

    assert state.trend == TrendState.BULLISH


def test_swing_cannot_break_before_confirmation():
    candles = [
        make_candle(
            index=0,
            close=100,
        ),
        make_candle(
            index=1,
            close=102,
        ),

        # Price already closes above 105,
        # but the swing is not confirmed yet.
        make_candle(
            index=2,
            close=110,
        ),

        # Swing becomes confirmed here,
        # but close is below the level.
        make_candle(
            index=3,
            close=104,
        ),

        # First valid break after confirmation.
        make_candle(
            index=4,
            close=106,
        ),
    ]

    swing = make_swing(
        index=1,
        confirmed_index=3,
        price=105,
        kind="HIGH",
    )

    detector = StructureBreakDetector()

    breaks, _ = detector.detect(
        candles,
        [swing],
    )

    assert len(breaks) == 1

    assert breaks[0].candle_index == 4


def test_bearish_bos_then_bullish_choch():
    candles = [
        make_candle(
            index=0,
            close=100,
        ),
        make_candle(
            index=1,
            close=100,
        ),
        make_candle(
            index=2,
            close=100,
        ),

        # Break below confirmed swing low.
        make_candle(
            index=3,
            close=94,
        ),

        # Reverse and break confirmed swing high.
        make_candle(
            index=4,
            close=106,
        ),
    ]

    swing_high = make_swing(
        index=0,
        confirmed_index=1,
        price=105,
        kind="HIGH",
    )

    swing_low = make_swing(
        index=1,
        confirmed_index=2,
        price=95,
        kind="LOW",
    )

    detector = StructureBreakDetector()

    breaks, state = detector.detect(
        candles,
        [
            swing_high,
            swing_low,
        ],
    )

    assert len(breaks) == 2

    assert (
        breaks[0].break_type
        == BreakType.BOS_BEARISH
    )

    assert (
        breaks[0].trend_before
        == TrendState.NEUTRAL
    )

    assert (
        breaks[0].trend_after
        == TrendState.BEARISH
    )

    assert (
        breaks[1].break_type
        == BreakType.CHOCH_BULLISH
    )

    assert (
        breaks[1].trend_before
        == TrendState.BEARISH
    )

    assert (
        breaks[1].trend_after
        == TrendState.BULLISH
    )

    assert (
        state.trend
        == TrendState.BULLISH
    )


def test_break_detector_rejects_unconfirmed_candle():
    candles = [
        make_candle(
            index=0,
            close=100,
        ),
        make_candle(
            index=1,
            close=106,
            confirmed=False,
        ),
    ]

    detector = StructureBreakDetector()

    with pytest.raises(
        ValueError,
        match="confirmed candles",
    ):
        detector.detect(
            candles,
            [],
        )