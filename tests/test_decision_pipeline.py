from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace

from decision_engine.pipeline import (
    DecisionPipeline,
)


def enum_value(value: str):
    return SimpleNamespace(
        value=value
    )


def make_timeframe(
    trend: str,
    close: float,
):
    return SimpleNamespace(
        latest_close=close,
        trend=enum_value(trend),
        latest_structure_label="HH",
        latest_swing_high=86000.0,
        latest_swing_low=84000.0,
        latest_break_type=enum_value(
            "BOS_BULLISH"
        ),
        latest_break_level=85500.0,

        indicators=SimpleNamespace(
          ema_20=84900.0,
          ema_50=84700.0,
          ema_200=82000.0,
          rsi_14=55.0,
          atr_14=500.0,
          atr_percent=0.7,
      ),
    )


def make_context(
    *,
    symbol: str = "BTCUSDT",
    healthy: bool = True,
    age_seconds: int = 0,
    mid_price: float = 85000.0,
):
    return SimpleNamespace(
        symbol=symbol,

        generated_at_utc=(
            datetime.now(timezone.utc)
            - timedelta(
                seconds=age_seconds
            )
        ),

        technical=SimpleNamespace(
            trend_alignment=enum_value(
                "MIXED"
            ),

            timeframe_15m=make_timeframe(
                "BEARISH",
                84950.0,
            ),

            timeframe_1h=make_timeframe(
                "BULLISH",
                85000.0,
            ),

            timeframe_4h=make_timeframe(
                "BULLISH",
                85100.0,
            ),
        ),

        derivatives=SimpleNamespace(
            open_interest=60000.0,
            oi_change_percent=-0.25,
            current_funding_rate=0.0001,
            long_account_ratio=0.51,
            short_account_ratio=0.49,
            long_short_account_ratio=1.0408,
        ),

        trade_flow=SimpleNamespace(
            aggressive_buy_volume=10.0,
            aggressive_sell_volume=9.0,
            signed_volume_imbalance=0.0526,
            trade_count=100,
        ),

        orderbook=SimpleNamespace(
            mid_price=mid_price,
            spread=0.1,
            spread_bps=0.02,
            depth_levels=10,
            depth_imbalance=0.10,
        ),

        liquidations=SimpleNamespace(
            event_count=0,
            long_liquidation_volume=0.0,
            short_liquidation_volume=0.0,
        ),

        health=SimpleNamespace(
            all_required_healthy=healthy,
        ),
    )


def test_valid_long_is_accepted():
    raw = """
    {
      "schema_version": "1.0",
      "symbol": "BTCUSDT",
      "action": "LONG",
      "setup_quality": "MEDIUM",
      "confidence": 0.72,
      "thesis": "Bullish setup.",
      "evidence": [
        {
          "context_path": "technical.1h.trend",
          "value": "BULLISH",
          "direction": "BULLISH",
          "interpretation": "The 1h trend is bullish."
        }
      ],
      "entry_price": 85000,
      "stop_loss": 84500,
      "take_profit": 86000,
      "invalidation_reason": "Bullish structure fails.",
      "no_trade_reason": null
    }
    """

    result = DecisionPipeline().process(
        raw,
        make_context(),
    )

    assert result.accepted is True
    assert result.proposal is not None
    assert result.error is None


def test_valid_no_trade_is_accepted():
    raw = """
    {
      "schema_version": "1.0",
      "symbol": "BTCUSDT",
      "action": "NO_TRADE",
      "setup_quality": "LOW",
      "confidence": 0.82,
      "thesis": "Timeframes conflict.",
      "evidence": [
        {
          "context_path": "technical.trend_alignment",
          "value": "MIXED",
          "direction": "NEUTRAL",
          "interpretation": "The timeframes are not aligned."
        }
      ],
      "entry_price": null,
      "stop_loss": null,
      "take_profit": null,
      "invalidation_reason": null,
      "no_trade_reason": "Directional evidence is mixed."
    }
    """

    result = DecisionPipeline().process(
        raw,
        make_context(),
    )

    assert result.accepted is True

    assert (
        result.proposal.action.value
        == "NO_TRADE"
    )


def test_malformed_json_is_rejected():
    raw = """
    {
      "symbol": "BTCUSDT",
      "action": "LONG",
    """

    result = DecisionPipeline().process(
        raw,
        make_context(),
    )

    assert result.accepted is False
    assert result.proposal is None
    assert result.error is not None


def test_invalid_trade_schema_is_rejected():
    raw = """
    {
      "schema_version": "1.0",
      "symbol": "BTCUSDT",
      "action": "LONG",
      "setup_quality": "HIGH",
      "confidence": 0.9,
      "thesis": "Long setup.",
      "evidence": [
        {
          "context_path": "technical.1h.trend",
          "value": "BULLISH",
          "direction": "BULLISH",
          "interpretation": "The 1h trend is bullish."
        }
      ],
      "entry_price": 85000,
      "stop_loss": 85500,
      "take_profit": 86000,
      "invalidation_reason": "Fails.",
      "no_trade_reason": null
    }
    """

    result = DecisionPipeline().process(
        raw,
        make_context(),
    )

    assert result.accepted is False
    assert result.proposal is None


def test_wrong_symbol_is_rejected():
    raw = """
    {
      "schema_version": "1.0",
      "symbol": "ETHUSDT",
      "action": "NO_TRADE",
      "setup_quality": "LOW",
      "confidence": 0.8,
      "thesis": "No trade.",
      "evidence": [
        {
          "context_path": "technical.trend_alignment",
          "value": "MIXED",
          "direction": "NEUTRAL",
          "interpretation": "Trend alignment is mixed."
        }
      ],
      "entry_price": null,
      "stop_loss": null,
      "take_profit": null,
      "invalidation_reason": null,
      "no_trade_reason": "No setup."
    }
    """

    result = DecisionPipeline().process(
        raw,
        make_context(),
    )

    assert result.accepted is False
    assert result.validation is not None

    assert len(
        result.validation.reasons
    ) > 0


def test_stale_context_is_rejected():
    raw = """
    {
      "schema_version": "1.0",
      "symbol": "BTCUSDT",
      "action": "NO_TRADE",
      "setup_quality": "LOW",
      "confidence": 0.8,
      "thesis": "Wait.",
      "evidence": [
        {
          "context_path": "technical.trend_alignment",
          "value": "MIXED",
          "direction": "NEUTRAL",
          "interpretation": "Trend alignment is mixed."
        }
      ],
      "entry_price": null,
      "stop_loss": null,
      "take_profit": null,
      "invalidation_reason": null,
      "no_trade_reason": "No clear setup."
    }
    """

    result = DecisionPipeline().process(
        raw,
        make_context(
            age_seconds=300
        ),
    )

    assert result.accepted is False

    assert (
        "Market context is stale."
        in result.validation.reasons
    )


def test_far_entry_is_rejected():
    raw = """
    {
      "schema_version": "1.0",
      "symbol": "BTCUSDT",
      "action": "LONG",
      "setup_quality": "HIGH",
      "confidence": 0.8,
      "thesis": "Bullish.",
      "evidence": [
        {
          "context_path": "technical.1h.trend",
          "value": "BULLISH",
          "direction": "BULLISH",
          "interpretation": "The 1h trend is bullish."
        }
      ],
      "entry_price": 90000,
      "stop_loss": 89000,
      "take_profit": 92000,
      "invalidation_reason": "Structure fails.",
      "no_trade_reason": null
    }
    """

    result = DecisionPipeline().process(
        raw,
        make_context(
            mid_price=85000
        ),
    )

    assert result.accepted is False

    assert (
        "Proposed entry is too far "
        "from current market price."
        in result.validation.reasons
    )


def test_unhealthy_context_is_rejected():
    raw = """
    {
      "schema_version": "1.0",
      "symbol": "BTCUSDT",
      "action": "NO_TRADE",
      "setup_quality": "LOW",
      "confidence": 1.0,
      "thesis": "Market data is unhealthy.",
      "evidence": [
        {
          "context_path": "health.all_required_healthy",
          "value": false,
          "direction": "NEUTRAL",
          "interpretation": "Required market data is unhealthy."
        }
      ],
      "entry_price": null,
      "stop_loss": null,
      "take_profit": null,
      "invalidation_reason": null,
      "no_trade_reason": "Data health failure."
    }
    """

    result = DecisionPipeline().process(
        raw,
        make_context(
            healthy=False
        ),
    )

    assert result.accepted is False

    assert (
        "Required market data is unhealthy."
        in result.validation.reasons
    )