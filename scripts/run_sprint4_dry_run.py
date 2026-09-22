from __future__ import annotations

from time import sleep

from account_data.bybit_demo import (
    BybitDemoAccountClient,
)

from account_data.closed_pnl import (
    BybitDemoClosedPnlClient,
)

from config.settings import (
    BYBIT_DEMO_API_KEY,
    BYBIT_DEMO_API_SECRET,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    SYMBOL,
    validate_bybit_demo_settings,
    validate_groq_settings,
)

from context_engine.market_context import (
    MarketContextBuilder,
)

from decision_engine.llm_service import (
    LLMDecisionService,
)

from decision_engine.pipeline import (
    DecisionPipeline,
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

from orchestration.dry_run import (
    DryRunStatus,
    TradingDryRun,
)

from risk_manager.account_state_provider import (
    DemoRiskStateProvider,
)

from risk_manager.bridge import (
    DecisionRiskBridge,
)

from risk_manager.engine import (
    DeterministicRiskEngine,
)

from risk_manager.instrument_rules import (
    BybitInstrumentRulesClient,
)


def build_decision_service():
    provider = GroqProvider(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        base_url=GROQ_BASE_URL,
    )

    validator = DecisionValidator()

    pipeline = DecisionPipeline(
        validator=validator
    )

    return LLMDecisionService(
        provider=provider,
        pipeline=pipeline,
    )


def build_account_state_provider():
    account_client = (
        BybitDemoAccountClient(
            api_key=(
                BYBIT_DEMO_API_KEY
            ),

            api_secret=(
                BYBIT_DEMO_API_SECRET
            ),
        )
    )

    pnl_client = (
        BybitDemoClosedPnlClient(
            api_key=(
                BYBIT_DEMO_API_KEY
            ),

            api_secret=(
                BYBIT_DEMO_API_SECRET
            ),
        )
    )

    return DemoRiskStateProvider(
        account_client=account_client,

        closed_pnl_client=(
            pnl_client
        ),
    )


def print_decision(result):
    decision_result = (
        result.decision_result
    )

    proposal = (
        decision_result.proposal
    )

    print(
        "\n=== LLM DECISION ==="
    )

    print(
        f"Accepted: "
        f"{decision_result.accepted}"
    )

    if proposal is None:
        print(
            f"Error: "
            f"{decision_result.error}"
        )

        return

    print(
        f"Action: "
        f"{proposal.action.value}"
    )

    print(
        f"Setup Quality: "
        f"{proposal.setup_quality.value}"
    )

    print(
        f"Confidence: "
        f"{proposal.confidence}"
    )

    print(
        f"Thesis: "
        f"{proposal.thesis}"
    )

    if proposal.entry_price is not None:
        print(
            f"Proposed Entry: "
            f"{proposal.entry_price}"
        )

        print(
            f"Proposed Stop: "
            f"{proposal.stop_loss}"
        )

        print(
            f"Proposed Target: "
            f"{proposal.take_profit}"
        )

    if proposal.no_trade_reason:
        print(
            f"No Trade Reason: "
            f"{proposal.no_trade_reason}"
        )


def print_risk(result):
    bridge = (
        result.risk_bridge_result
    )

    if bridge is None:
        return

    print(
        "\n=== RISK LAYER ==="
    )

    print(
        f"Bridge Status: "
        f"{bridge.status.value}"
    )

    if bridge.no_trade_reason:
        print(
            f"Reason: "
            f"{bridge.no_trade_reason}"
        )

    risk_result = bridge.risk_result

    if risk_result is None:
        return

    print(
        f"Risk Decision: "
        f"{risk_result.decision.value}"
    )

    if risk_result.reasons:
        print(
            "Risk Reasons:"
        )

        for reason in (
            risk_result.reasons
        ):
            print(
                f"- {reason}"
            )

    plan = risk_result.plan

    if plan is None:
        return

    print(
        "\n=== APPROVED RISK PLAN ==="
    )

    print(
        f"Symbol: "
        f"{plan.symbol}"
    )

    print(
        f"Side: "
        f"{plan.side.value}"
    )

    print(
        f"Entry: "
        f"{plan.entry_price}"
    )

    print(
        f"Stop Loss: "
        f"{plan.stop_loss}"
    )

    print(
        f"Take Profit: "
        f"{plan.take_profit}"
    )

    print(
        f"Risk Budget: "
        f"{plan.risk_amount}"
    )

    print(
        f"Actual Risk: "
        f"{plan.actual_risk_amount}"
    )

    print(
        f"Quantity: "
        f"{plan.executable_quantity}"
        f" BTC"
    )

    print(
        f"Reward/Risk: "
        f"{plan.reward_risk_ratio}"
    )

    print(
        f"Position Notional: "
        f"{plan.position_notional}"
    )

    print(
        f"Required Margin: "
        f"{plan.required_margin}"
    )

    print(
        f"Leverage: "
        f"{plan.leverage}x"
    )


def main():
    print(
        "=== Sprint 4 — "
        "End-to-End Dry Run ==="
    )

    print(
        "\nDRY RUN ONLY — "
        "NO ORDERS WILL BE PLACED."
    )

    validate_groq_settings()
    validate_bybit_demo_settings()

    # ---------------------------------------------
    # Public market-data runner
    # ---------------------------------------------

    runner = MarketDataRunner(
        rest_poll_seconds=60
    )

    try:
        runner.start()

        print(
            "\nCollecting market data..."
        )

        sleep(5)

        context = (
            MarketContextBuilder(
                runner=runner,

                orderbook_depth_levels=10,
            )
            .build(
                require_healthy=True
            )
        )

        print(
            "\n=== MARKET CONTEXT ==="
        )

        print(
            f"Symbol: {context.symbol}"
        )

        print(
            f"Alignment: "
            f"{context.technical.trend_alignment.value}"
        )

        print(
            f"15m: "
            f"{context.technical.timeframe_15m.trend.value}"
        )

        print(
            f"1h: "
            f"{context.technical.timeframe_1h.trend.value}"
        )

        print(
            f"4h: "
            f"{context.technical.timeframe_4h.trend.value}"
        )

        # -----------------------------------------
        # Live instrument rules
        # -----------------------------------------

        rules = (
            BybitInstrumentRulesClient()
            .get_linear_rules(
                SYMBOL
            )
        )

        risk_engine = (
            DeterministicRiskEngine(
                instrument_rules=rules
            )
        )

        risk_bridge = (
            DecisionRiskBridge(
                risk_engine=risk_engine
            )
        )

        dry_run = TradingDryRun(
            decision_service=(
                build_decision_service()
            ),

            account_state_provider=(
                build_account_state_provider()
            ),

            risk_bridge=risk_bridge,
        )

        print(
            f"\nCalling Groq model: "
            f"{GROQ_MODEL}"
        )

        result = dry_run.run(
            context
        )

        print_decision(
            result
        )

        print_risk(
            result
        )

        print(
            "\n=== FINAL DRY-RUN STATUS ==="
        )

        print(
            result.status.value
        )

        if result.error:
            print(
                f"Error: "
                f"{result.error}"
            )

        print(
            "\nNO ORDER WAS PLACED."
        )

        if (
            result.status
            == DryRunStatus.RISK_APPROVED
        ):
            print(
                "Risk approval means only "
                "that the proposal passed "
                "deterministic checks."
            )

            print(
                "Execution still requires "
                "the future manual-approval "
                "and execution layers."
            )

    finally:
        runner.stop()


if __name__ == "__main__":
    main()