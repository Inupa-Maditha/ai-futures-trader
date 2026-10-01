from __future__ import annotations

from decimal import Decimal

from risk_manager.bridge import (
    AccountRiskState,
    DecisionRiskBridge,
)

from risk_manager.engine import (
    DeterministicRiskEngine,
)

from risk_manager.instrument_rules import (
    BybitInstrumentRulesClient,
)

from dataclasses import replace
from time import sleep

from config.settings import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
)

from context_engine.market_context import (
    MarketContextBuilder,
)

from decision_engine.pipeline import (
    DecisionPipeline,
)

from decision_engine.prompt_builder import (
    DecisionPromptBuilder,
)

from decision_engine.providers.groq_provider import (
    GroqProvider,
)

from decision_engine.validator import (
    DecisionValidator,
)

from market_data.runner import (
    MarketDataRunner,
)

from scripts.test_llm_reachability import (
    make_synthetic_context,
)


V11_SYSTEM_PROMPT = """
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


def run_scenario(
    name,
    context,
):
    builder = DecisionPromptBuilder()

    package = builder.build(
        context
    )

    package = replace(
        package,
        prompt_version="1.1-test",
        system_prompt=V11_SYSTEM_PROMPT,
    )

    provider = GroqProvider(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        base_url=GROQ_BASE_URL,
    )

    raw = provider.generate(
        package
    )

    print("\n=== RAW MODEL OUTPUT ===")
    print(raw)

    result = DecisionPipeline(
        validator=DecisionValidator()
    ).process(
        raw_response=raw,
        context=context,
    )

    print(
        "\n========================================"
    )
    print(
        f"SCENARIO: {name}"
    )
    print(
        "========================================"
    )

    print(
        f"Accepted: {result.accepted}"
    )

    if result.error:
        print(
            f"Error: {result.error}"
        )

    if result.validation:
        print(
            f"Validation: "
            f"{result.validation.reasons}"
        )

    proposal = result.proposal

    if proposal is None:
        return

    print(
        f"Action: {proposal.action.value}"
    )
    print(
        f"Quality: {proposal.setup_quality.value}"
    )
    print(
        f"Confidence: {proposal.confidence}"
    )
    print(
        f"Thesis: {proposal.thesis}"
    )

    print(
        f"Entry: {proposal.entry_price}"
    )
    print(
        f"Stop Loss: {proposal.stop_loss}"
    )
    print(
        f"Take Profit: {proposal.take_profit}"
    )
    print(
        f"Invalidation: "
        f"{proposal.invalidation_reason}"
    )
    print(
        f"No Trade Reason: "
        f"{proposal.no_trade_reason}"
    )

    if proposal.action.value == "NO_TRADE":
        print("\n=== RISK ENGINE ===")
        print("Skipped: NO_TRADE")
        return

    rules = (
        BybitInstrumentRulesClient()
        .get_linear_rules("BTCUSDT")
    )

    risk_engine = DeterministicRiskEngine(
        instrument_rules=rules,
    )

    bridge = DecisionRiskBridge(
        risk_engine=risk_engine,
    )

    synthetic_account = AccountRiskState(
        account_equity=Decimal("10000"),
        available_balance=Decimal("10000"),
        open_position_count=0,
        daily_realized_pnl=Decimal("0"),
    )

    risk_result = bridge.evaluate(
        proposal=proposal,
        account=synthetic_account,
    )

    print("\n=== RISK ENGINE ===")
    print(f"Status: {risk_result.status.value}")

    if risk_result.risk_result is not None:
        print(
            "Reasons:",
            risk_result.risk_result.reasons,
        )

        plan = risk_result.risk_result.plan

        if plan is not None:
            print(
                "Reward/Risk:",
                plan.reward_risk_ratio,
            )
            print(
                "Stop Distance %:",
                (
                    plan.stop_distance_fraction
                    * Decimal("100")
                ),
            )
            print(
                "Quantity:",
                plan.executable_quantity,
            )
            print(
                "Leverage:",
                plan.leverage,
            )


def main():
    print(
        "=== EXPERIMENTAL PROMPT V1.1 "
        "REACHABILITY TEST ==="
    )

    print(
        "No orders can be executed by this script."
    )

    runner = MarketDataRunner(
        rest_poll_seconds=60,
    )

    try:
        runner.start()

        sleep(5)

        base_context = (
            MarketContextBuilder(
                runner=runner,
                orderbook_depth_levels=10,
            )
            .build(
                require_healthy=True
            )
        )

        bullish = make_synthetic_context(
            base_context,
            bullish=True,
        )

        bearish = make_synthetic_context(
            base_context,
            bullish=False,
        )

        mid = base_context.orderbook.mid_price

        mixed_15m = replace(
            bullish.technical.timeframe_15m,
            trend=type(
                bullish.technical.timeframe_15m.trend
            )("BULLISH"),
            latest_structure_label=None,
            latest_break_type=None,
            latest_break_level=None,
            indicators=replace(
                bullish.technical.timeframe_15m.indicators,
                ema_20=mid,
                ema_50=mid,
                ema_200=mid,
                rsi_14=50.0,
            ),
        )

        mixed_1h = replace(
            bearish.technical.timeframe_1h,
            trend=type(
                bearish.technical.timeframe_1h.trend
            )("BEARISH"),
            latest_structure_label=None,
            latest_break_type=None,
            latest_break_level=None,
            indicators=replace(
                bearish.technical.timeframe_1h.indicators,
                ema_20=mid,
                ema_50=mid,
                ema_200=mid,
                rsi_14=50.0,
            ),
        )

        mixed_4h = replace(
            bullish.technical.timeframe_4h,
            trend=type(
                bullish.technical.timeframe_4h.trend
            )("NEUTRAL"),
            latest_structure_label=None,
            latest_break_type=None,
            latest_break_level=None,
            indicators=replace(
                bullish.technical.timeframe_4h.indicators,
                ema_20=mid,
                ema_50=mid,
                ema_200=mid,
                rsi_14=50.0,
            ),
        )

        mixed = replace(
            bullish,

            technical=replace(
                bullish.technical,
                trend_alignment=type(
                    bullish.technical.trend_alignment
                )("MIXED"),
                timeframe_15m=mixed_15m,
                timeframe_1h=mixed_1h,
                timeframe_4h=mixed_4h,
            ),

            trade_flow=replace(
                bullish.trade_flow,
                aggressive_buy_volume=50.0,
                aggressive_sell_volume=50.0,
                signed_volume_imbalance=0.0,
            ),

            orderbook=replace(
                bullish.orderbook,
                depth_imbalance=0.0,
            ),

            derivatives=replace(
                bullish.derivatives,
                oi_change_percent=0.0,
                current_funding_rate=0.0,
                long_account_ratio=0.5,
                short_account_ratio=0.5,
                long_short_account_ratio=1.0,
            ),

            liquidations=replace(
                bullish.liquidations,
                event_count=0,
                long_liquidation_volume=0.0,
                short_liquidation_volume=0.0,
                total_liquidation_volume=0.0,
            ),
        )

        run_scenario(
            "CLEAR BULLISH",
            bullish,
        )

        run_scenario(
            "CLEAR BEARISH",
            bearish,
        )

        run_scenario(
            "CLEAR MIXED",
            mixed,
        )

    finally:
        runner.stop()


if __name__ == "__main__":
    main()