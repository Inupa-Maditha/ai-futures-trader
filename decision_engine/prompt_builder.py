from __future__ import annotations

import json

from dataclasses import dataclass

from context_engine.market_context import (
    MarketContextSnapshot,
)

from decision_engine.evidence_catalog import (
    build_evidence_catalog,
)


PROMPT_VERSION = "1.1"


SYSTEM_PROMPT = """
You are the decision-analysis component of a BTCUSDT
perpetual futures demo-trading system.

Return exactly one decision:

LONG
SHORT
NO_TRADE

Use only the supplied market context.

You cannot execute orders, choose position size, choose leverage,
choose account risk, or override the deterministic risk engine.

DECISION FRAMEWORK

First evaluate technical direction.

A LONG setup may be selected when the supplied evidence shows
clear bullish directional agreement.

Strong LONG evidence includes:
- BULLISH_ALIGNED trend alignment
- bullish 4h trend
- bullish 1h trend
- bullish 15m trend
- HH or HL market structure
- BOS_BULLISH
- price above relevant EMAs
- positive recent order-flow imbalance
- positive order-book depth imbalance

A SHORT setup may be selected when the supplied evidence shows
clear bearish directional agreement.

Strong SHORT evidence includes:
- BEARISH_ALIGNED trend alignment
- bearish 4h trend
- bearish 1h trend
- bearish 15m trend
- LL or LH market structure
- BOS_BEARISH
- price below relevant EMAs
- negative recent order-flow imbalance
- negative order-book depth imbalance

Derivatives, liquidations, funding and positioning are confirmation
features. They do not all need to point in the same direction.

Do not require every available metric to agree.

Use NO_TRADE when:
- higher timeframes materially conflict
- technical direction is unclear
- directional evidence is approximately balanced
- required market data is unhealthy
- a valid entry, stop loss and take profit cannot be constructed

When technical evidence is strongly aligned, do not choose
NO_TRADE merely because some secondary confirmation metrics
are neutral.

DIRECTIONAL SYMMETRY RULE

Evaluate LONG and SHORT independently.

A bearish setup does not require any bullish confirmation.

If the market context is clearly bearish and valid SHORT geometry
can be constructed, choose SHORT.

Do not choose NO_TRADE merely because there is no bullish entry,
bullish reversal, or bullish confirmation.

Likewise, a bullish setup does not require bearish confirmation.

If the market context is clearly bullish and valid LONG geometry
can be constructed, choose LONG.

NO_TRADE means neither LONG nor SHORT has a sufficiently valid
setup. It must not mean that only one direction is unavailable.

TRADE GEOMETRY

For LONG:
- entry_price must be close to orderbook.mid_price
- entry_price must be within 2% of orderbook.mid_price
- stop_loss must be below entry_price
- stop distance must be between 0.1% and 3% of entry_price
- prefer a supplied recent swing low as structural invalidation
- take_profit must be above entry_price
- target reward-to-risk should be at least 1.6

For SHORT:
- entry_price must be close to orderbook.mid_price
- entry_price must be within 2% of orderbook.mid_price
- stop_loss must be above entry_price
- stop distance must be between 0.1% and 3% of entry_price
- prefer a supplied recent swing high as structural invalidation
- take_profit must be below entry_price
- target reward-to-risk should be at least 1.6

Before returning LONG or SHORT, calculate:

risk_distance = abs(entry_price - stop_loss)
reward_distance = abs(take_profit - entry_price)
reward_to_risk = reward_distance / risk_distance

If reward_to_risk is below 1.6, choose NO_TRADE instead.

Use 1.6 as the proposal minimum to provide a small safety
margin above the deterministic risk engine minimum of 1.5
after exchange price rounding.

For LONG or SHORT, invalidation_reason must describe the actual
market condition or supplied structural level that invalidates
the trade.

Never return "None", "N/A", "Unknown", or similar placeholder
text as invalidation_reason.

If a valid stop, target, or invalidation cannot be constructed,
choose NO_TRADE.

GROUNDING RULES

Every evidence item must reference exactly one context_path from
evidence_catalog.

Every evidence.value must be copied exactly from evidence_catalog.

Evidence values must remain JSON strings.

Never invent a context path or value.

Select EXACTLY 4 evidence items.
Never return more than 4 evidence items.

For LONG or SHORT:
- no_trade_reason must be null
- invalidation_reason must be non-empty

For NO_TRADE:
- entry_price must be null
- stop_loss must be null
- take_profit must be null
- invalidation_reason must be null
- no_trade_reason must be non-empty

Return JSON only.
Do not include markdown or text outside the JSON object.

THESIS AND INVALIDATION RULES

Thesis must discuss only facts represented by the selected
evidence items.

Do not mention BOS, EMA, RSI, funding, order flow, structure,
or any other metric unless that exact metric is included in
the selected evidence.

For LONG:
- invalidation_reason must state that the trade becomes invalid
  if price reaches or falls below the proposed stop_loss.
- include the exact stop_loss value.

For SHORT:
- invalidation_reason must state that the trade becomes invalid
  if price reaches or rises above the proposed stop_loss.
- include the exact stop_loss value.

Do not use supporting evidence as the invalidation condition.
""".strip()


@dataclass(
    frozen=True,
    slots=True,
)
class LLMPromptPackage:
    prompt_version: str
    system_prompt: str
    user_payload: dict

    def user_json(self) -> str:
        return json.dumps(
            self.user_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )


class DecisionPromptBuilder:
    def build(
        self,
        context: MarketContextSnapshot,
    ) -> LLMPromptPackage:

        payload = {
            "prompt_version": PROMPT_VERSION,

            "evidence_catalog": (
                build_evidence_catalog(
                    context
                )
            ),

            "market_context": {
                "schema_version": (
                    context.schema_version
                ),

                "symbol": context.symbol,

                "generated_at_utc": (
                    context.generated_at_utc
                    .isoformat()
                ),

                "health": {
                    "all_required_healthy": (
                        context.health
                        .all_required_healthy
                    ),
                    "statuses": (
                        context.health.statuses
                    ),
                },

                "technical": {
                    "trend_alignment": (
                        context.technical
                        .trend_alignment.value
                    ),

                    "15m": self._timeframe_context(
                        context.technical
                        .timeframe_15m
                    ),

                    "1h": self._timeframe_context(
                        context.technical
                        .timeframe_1h
                    ),

                    "4h": self._timeframe_context(
                        context.technical
                        .timeframe_4h
                    ),
                },

                "derivatives": {
                    "open_interest": self._round(
                        context.derivatives
                        .open_interest,
                        3,
                    ),

                    "oi_change_percent": (
                        self._round_optional(
                            context.derivatives
                            .oi_change_percent,
                            4,
                        )
                    ),

                    "funding_rate": self._round(
                        context.derivatives
                        .current_funding_rate,
                        8,
                    ),

                    "long_account_ratio": (
                        self._round(
                            context.derivatives
                            .long_account_ratio,
                            4,
                        )
                    ),

                    "short_account_ratio": (
                        self._round(
                            context.derivatives
                            .short_account_ratio,
                            4,
                        )
                    ),

                    "long_short_account_ratio": (
                        self._round_optional(
                            context.derivatives
                            .long_short_account_ratio,
                            4,
                        )
                    ),
                },

                "order_flow": {
                    "window_seconds": (
                        context.trade_flow
                        .window_seconds
                    ),

                    "aggressive_buy_volume": (
                        self._round(
                            context.trade_flow
                            .aggressive_buy_volume,
                            3,
                        )
                    ),

                    "aggressive_sell_volume": (
                        self._round(
                            context.trade_flow
                            .aggressive_sell_volume,
                            3,
                        )
                    ),

                    "signed_volume_imbalance": (
                        self._round(
                            context.trade_flow
                            .signed_volume_imbalance,
                            4,
                        )
                    ),

                    "trade_count": (
                        context.trade_flow
                        .trade_count
                    ),
                },

                "orderbook": {
                    "mid_price": self._round(
                        context.orderbook
                        .mid_price,
                        2,
                    ),

                    "spread": self._round(
                        context.orderbook
                        .spread,
                        4,
                    ),

                    "spread_bps": self._round(
                        context.orderbook
                        .spread_bps,
                        4,
                    ),

                    "depth_levels": (
                        context.orderbook
                        .depth_levels
                    ),

                    "depth_imbalance": (
                        self._round(
                            context.orderbook
                            .depth_imbalance,
                            4,
                        )
                    ),
                },

                "liquidations": {
                    "window_seconds": (
                        context.liquidations
                        .window_seconds
                    ),

                    "event_count": (
                        context.liquidations
                        .event_count
                    ),

                    "long_liquidation_volume": (
                        self._round(
                            context.liquidations
                            .long_liquidation_volume,
                            3,
                        )
                    ),

                    "short_liquidation_volume": (
                        self._round(
                            context.liquidations
                            .short_liquidation_volume,
                            3,
                        )
                    ),
                },
            },

            "interpretation_notes": [
                (
                    "Order-book depth imbalance describes "
                    "visible liquidity only and is not proof "
                    "of support or resistance."
                ),
                (
                    "Long/short ratios describe account-holder "
                    "positioning, not notional position size."
                ),
                (
                    "Aggressive trade-flow imbalance describes "
                    "recent taker-side activity only."
                ),
                (
                    "Absence of liquidation events is normal "
                    "and must not be treated as missing data."
                ),
                (
                    "Trend alignment may be mixed across "
                    "timeframes."
                ),
                (
                    "open_interest and oi_change_percent are separate "
                    "from account-holder long/short positioning ratios."
                ),
                (
                    "Do not infer a trend from a single snapshot unless "
                    "an explicit change value is supplied."
                ),
            ],
        }

        return LLMPromptPackage(
            prompt_version=PROMPT_VERSION,
            system_prompt=SYSTEM_PROMPT,
            user_payload=payload,
        )

    @staticmethod
    def _timeframe_context(
        snapshot,
    ) -> dict:

        indicators = snapshot.indicators

        return {
            "close": round(
                snapshot.latest_close,
                2,
            ),

            "trend": snapshot.trend.value,

            "structure": (
                snapshot.latest_structure_label
            ),

            "ema_20": round(
                indicators.ema_20,
                2,
            ),

            "ema_50": round(
                indicators.ema_50,
                2,
            ),

            "ema_200": round(
                indicators.ema_200,
                2,
            ),

            "rsi_14": round(
                indicators.rsi_14,
                2,
            ),

            "atr_14": round(
                indicators.atr_14,
                2,
            ),

            "atr_percent": round(
                indicators.atr_percent,
                4,
            ),

            "latest_swing_high": (
                round(
                    snapshot.latest_swing_high,
                    2,
                )
                if snapshot.latest_swing_high
                is not None
                else None
            ),

            "latest_swing_low": (
                round(
                    snapshot.latest_swing_low,
                    2,
                )
                if snapshot.latest_swing_low
                is not None
                else None
            ),

            "latest_break": (
                snapshot.latest_break_type.value
                if snapshot.latest_break_type
                is not None
                else None
            ),

            "latest_break_level": (
                round(
                    snapshot.latest_break_level,
                    2,
                )
                if snapshot.latest_break_level
                is not None
                else None
            ),
        }

    @staticmethod
    def _round(
        value: float,
        digits: int,
    ) -> float:
        return round(
            value,
            digits,
        )

    @staticmethod
    def _round_optional(
        value: float | None,
        digits: int,
    ) -> float | None:

        if value is None:
            return None

        return round(
            value,
            digits,
        )