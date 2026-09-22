from datetime import (
    datetime,
    timezone,
)
from types import SimpleNamespace

from decision_engine.llm_service import (
    LLMDecisionService,
)

from decision_engine.prompt_builder import (
    LLMPromptPackage,
)


VALID_NO_TRADE = """
{
  "schema_version": "1.0",
  "symbol": "BTCUSDT",
  "action": "NO_TRADE",
  "setup_quality": "LOW",
  "confidence": 0.8,
  "thesis": "Evidence is mixed.",
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
  "no_trade_reason": "No clear setup."
}
"""


def enum_value(value: str):
    return SimpleNamespace(
        value=value
    )


def make_timeframe(
    trend: str,
):
    return SimpleNamespace(
        latest_close=85000.0,
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


class FakePromptBuilder:
    def build(self, context):
        return LLMPromptPackage(
            prompt_version="1.0",
            system_prompt="test",
            user_payload={
                "test": True
            },
        )


class FakeProvider:
    def __init__(
        self,
        response: str,
    ):
        self.response = response

    def generate(
        self,
        package,
    ) -> str:
        return self.response


class FailingProvider:
    def generate(
        self,
        package,
    ) -> str:
        raise RuntimeError(
            "simulated API failure"
        )


def make_context(
    healthy: bool = True,
):
    return SimpleNamespace(
        symbol="BTCUSDT",

        generated_at_utc=datetime.now(
            timezone.utc
        ),

        technical=SimpleNamespace(
            trend_alignment=enum_value(
                "MIXED"
            ),

            timeframe_15m=make_timeframe(
                "BEARISH"
            ),

            timeframe_1h=make_timeframe(
                "BULLISH"
            ),

            timeframe_4h=make_timeframe(
                "BULLISH"
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
            mid_price=85000.0,
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


def test_valid_provider_output_is_accepted():
    service = LLMDecisionService(
        provider=FakeProvider(
            VALID_NO_TRADE
        ),
        prompt_builder=FakePromptBuilder(),
    )

    result = service.decide(
        make_context()
    )

    assert result.accepted is True

    assert (
        result.proposal.action.value
        == "NO_TRADE"
    )


def test_provider_failure_fails_closed():
    service = LLMDecisionService(
        provider=FailingProvider(),
        prompt_builder=FakePromptBuilder(),
    )

    result = service.decide(
        make_context()
    )

    assert result.accepted is False
    assert result.proposal is None

    assert (
        "LLM provider failure"
        in result.error
    )


def test_invalid_llm_output_fails_closed():
    service = LLMDecisionService(
        provider=FakeProvider(
            "this is not json"
        ),
        prompt_builder=FakePromptBuilder(),
    )

    result = service.decide(
        make_context()
    )

    assert result.accepted is False
    assert result.proposal is None


def test_unhealthy_context_blocks_llm():
    service = LLMDecisionService(
        provider=FakeProvider(
            VALID_NO_TRADE
        ),
        prompt_builder=FakePromptBuilder(),
    )

    result = service.decide(
        make_context(
            healthy=False
        )
    )

    assert result.accepted is False

    assert (
        "market data is unhealthy"
        in result.error
    )