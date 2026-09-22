from __future__ import annotations

import json

from dataclasses import dataclass

from context_engine.market_context import (
    MarketContextSnapshot,
)

from decision_engine.evidence_catalog import (
    build_evidence_catalog,
)


PROMPT_VERSION = "1.0"


SYSTEM_PROMPT = """
You are the decision-analysis component of a BTCUSDT
perpetual futures demo-trading system.

Your job is to analyze the supplied verified market context
and return exactly one structured proposal:

LONG
SHORT
NO_TRADE

Important constraints:

1. This is analysis only.
2. You cannot execute orders.
3. You cannot choose position size.
4. You cannot choose leverage.
5. You cannot choose account risk.
6. You cannot override the deterministic risk engine.
7. You must use only the supplied market context.
8. Do not invent unavailable market data.
9. Mixed or insufficient evidence is a valid reason for NO_TRADE.
10. Data-health uncertainty must result in NO_TRADE.

GROUNDING RULES:

11. Use metric names exactly as supplied in the market context.
12. Never combine two different metrics into a new metric.
13. open_interest and oi_change_percent describe aggregate open interest.
14. long_account_ratio and short_account_ratio describe account-holder positioning.
15. Do not call account-holder ratios "open interest ratios".
16. A single snapshot does not prove a trend.
17. Do not say a metric is rising, falling, trending, increasing,
    or decreasing unless an explicit change metric or historical comparison
    is supplied.
18. oi_change_percent may be described as open-interest change,
    not as long/short positioning change.
19. Evidence values and interpretations must be directly supported
    by values present in the supplied context.
20. If evidence is ambiguous, use NEUTRAL or choose NO_TRADE.
21. Every evidence item must reference one exact context_path.
22. The evidence value must exactly match the supplied context value.
23. Never invent a context_path.
24. Do not combine multiple metrics into one evidence item.
25. Use one evidence item per factual claim.
26. evidence_catalog contains canonical string values.
27. Every evidence.value MUST be copied exactly from evidence_catalog.
28. Every evidence.value MUST be a JSON string, even when it represents a number, boolean, or null.
29. Never reformat, round, scale, convert, or reinterpret an evidence_catalog value.
30. For NO_TRADE, no_trade_reason MUST be a non-empty string.
31. For NO_TRADE, invalidation_reason MUST be null.
32. For LONG or SHORT, invalidation_reason MUST be a non-empty string.
33. For LONG or SHORT, no_trade_reason MUST be null.
34. context_path MUST be selected exactly from evidence_catalog.
35. Copy the corresponding evidence_catalog value exactly.
36. Never construct or guess a context_path yourself.
37. Select only the 3 to 6 most relevant evidence items.
38. Do not list every available metric.
39. Thesis and interpretations must discuss only the selected evidence items.
40. Never mention EMA crossover, ATR, structure, funding, order flow, or any other metric unless that metric is present in the selected evidence.
41. Prefer NO_TRADE when the selected evidence does not support a sufficiently clear directional setup.

For LONG:
- entry_price, stop_loss and take_profit MUST be numbers.
- stop_loss < entry_price < take_profit.
- invalidation_reason MUST be a non-empty string.
- no_trade_reason MUST be null.

For SHORT:
- entry_price, stop_loss and take_profit MUST be numbers.
- take_profit < entry_price < stop_loss.
- invalidation_reason MUST be a non-empty string.
- no_trade_reason MUST be null.

For NO_TRADE:
- entry_price MUST be null.
- stop_loss MUST be null.
- take_profit MUST be null.
- invalidation_reason MUST be null.
- no_trade_reason MUST be a non-empty string.

IMPORTANT:
A response that violates any of these rules is invalid.

Return JSON only.
Do not include markdown.
Do not include text outside the JSON object.

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