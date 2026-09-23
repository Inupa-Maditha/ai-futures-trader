from __future__ import annotations

from time import sleep

from pybit.unified_trading import HTTP

from account_data.bybit_demo import (
    BybitDemoAccountClient,
)

from account_data.closed_pnl import (
    BybitDemoClosedPnlClient,
)

from approval.console import (
    ConsoleManualApprover,
)

from approval.gate import (
    ManualApprovalGate,
)

from config.settings import (
    BYBIT_DEMO_API_KEY,
    BYBIT_DEMO_API_SECRET,
    ENABLE_DEMO_EXECUTION,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    SYMBOL,
    validate_bybit_demo_settings,
    validate_demo_execution_enabled,
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

from decision_engine.schema import (
    DecisionAction,
)

from decision_engine.validator import (
    DecisionValidator,
)

from execution.bybit_demo import (
    BybitDemoExecutionClient,
)

from execution.coordinator import (
    DemoExecutionCoordinator,
    ExecutionUncertainError,
)

from execution.order_repository import (
    BybitDemoOrderRepository,
)

from execution.preflight import (
    DemoExecutionPreflight,
)

from execution.request_builder import (
    DemoExecutionRequestBuilder,
)

from journal.lifecycle import (
    JournalRunLifecycle,
)

from journal.store import (
    JournalStore,
)

from journal.trading_journal import (
    TradingRunJournal,
)

from market_data.runner import (
    MarketDataRunner,
)

from orchestration.pipeline import (
    PipelineOutcome,
    TradingPipeline,
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


# =========================================================
# Dependency builders
# =========================================================


def build_decision_service():
    provider = GroqProvider(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        base_url=GROQ_BASE_URL,
    )

    decision_pipeline = (
        DecisionPipeline(
            validator=(
                DecisionValidator()
            )
        )
    )

    return LLMDecisionService(
        provider=provider,
        pipeline=decision_pipeline,
    )


def build_demo_risk_state_provider():
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
        account_client=(
            account_client
        ),

        closed_pnl_client=(
            pnl_client
        ),
    )


def build_demo_execution_coordinator():
    """
    Build one authenticated Bybit Demo execution
    stack.

    This function is only called after:
    - valid trade proposal
    - deterministic risk approval
    - execution switch enabled
    - manual human approval
    """

    demo_session = HTTP(
        testnet=False,
        demo=True,

        api_key=(
            BYBIT_DEMO_API_KEY
        ),

        api_secret=(
            BYBIT_DEMO_API_SECRET
        ),
    )

    repository = (
        BybitDemoOrderRepository(
            session=demo_session
        )
    )

    preflight = (
        DemoExecutionPreflight(
            session=demo_session,

            order_repository=(
                repository
            ),
        )
    )

    execution_client = (
        BybitDemoExecutionClient(
            api_key=(
                BYBIT_DEMO_API_KEY
            ),

            api_secret=(
                BYBIT_DEMO_API_SECRET
            ),

            session=demo_session,
        )
    )

    return DemoExecutionCoordinator(
        execution_client=(
            execution_client
        ),

        order_repository=(
            repository
        ),

        preflight=preflight,

        confirmation_attempts=6,

        confirmation_interval_seconds=(
            0.5
        ),
    )


# =========================================================
# Console output helpers
# =========================================================


def print_market_context(
    context,
):
    print(
        "\n=== MARKET CONTEXT ==="
    )

    print(
        f"Symbol: {context.symbol}"
    )

    print(
        "Alignment: "
        f"{context.technical.trend_alignment.value}"
    )

    print(
        "15m: "
        f"{context.technical.timeframe_15m.trend.value}"
    )

    print(
        "1h: "
        f"{context.technical.timeframe_1h.trend.value}"
    )

    print(
        "4h: "
        f"{context.technical.timeframe_4h.trend.value}"
    )


def print_proposal(
    proposal,
):
    print(
        "\n=== LLM PROPOSAL ==="
    )

    print(
        f"Action: "
        f"{proposal.action.value}"
    )

    print(
        f"Quality: "
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

    if (
        proposal.action
        == DecisionAction.NO_TRADE
    ):
        print(
            "No Trade Reason: "
            f"{proposal.no_trade_reason}"
        )

        return

    print(
        f"Entry: "
        f"{proposal.entry_price}"
    )

    print(
        f"Stop Loss: "
        f"{proposal.stop_loss}"
    )

    print(
        f"Take Profit: "
        f"{proposal.take_profit}"
    )


def print_account_state(
    state,
):
    print(
        "\n=== DEMO ACCOUNT ==="
    )

    print(
        "Equity: "
        f"{state.account_equity}"
    )

    print(
        "Available Balance: "
        f"{state.available_balance}"
    )

    print(
        "Open Positions: "
        f"{state.open_position_count}"
    )

    print(
        "Today's Realized PnL: "
        f"{state.daily_realized_pnl}"
    )


def print_risk_result(
    bridge_result,
):
    risk_result = (
        bridge_result.risk_result
    )

    if risk_result is None:
        return

    if risk_result.plan is None:
        print(
            "\n=== DETERMINISTIC "
            "RISK RESULT ==="
        )

        print(
            "RISK_REJECTED"
        )

        for reason in (
            risk_result.reasons
        ):
            print(
                f"- {reason}"
            )

        return

    plan = risk_result.plan

    print(
        "\n=== DETERMINISTIC "
        "RISK PLAN ==="
    )

    print(
        f"Side: {plan.side.value}"
    )

    print(
        f"Entry: {plan.entry_price}"
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
        "Quantity: "
        f"{plan.executable_quantity} BTC"
    )

    print(
        "Risk Budget: "
        f"{plan.risk_amount}"
    )

    print(
        "Actual Risk: "
        f"{plan.actual_risk_amount}"
    )

    print(
        "Reward/Risk: "
        f"{plan.reward_risk_ratio}"
    )

    print(
        "Notional: "
        f"{plan.position_notional}"
    )

    print(
        "Required Margin: "
        f"{plan.required_margin}"
    )

    print(
        f"Leverage: "
        f"{plan.leverage}x"
    )


def print_execution_request(
    request,
):
    print(
        "\n=== EXECUTION REQUEST ==="
    )

    print(
        "OrderLinkId: "
        f"{request.order_link_id}"
    )

    print(
        f"Side: "
        f"{request.side.value}"
    )

    print(
        "Quantity: "
        f"{request.quantity}"
    )

    print(
        "Limit Price: "
        f"{request.entry_price}"
    )

    print(
        "Stop Loss: "
        f"{request.stop_loss}"
    )

    print(
        "Take Profit: "
        f"{request.take_profit}"
    )


def print_final_outcome(
    outcome: PipelineOutcome,
):
    print(
        "\n=== FINAL STATUS ==="
    )

    print(
        outcome.status
    )

    if (
        outcome.status
        == "DECISION_REJECTED"
    ):
        error = getattr(
            outcome.decision_result,
            "error",
            None,
        )

        if error:
            print(
                f"Error: {error}"
            )

        print(
            "\nNo order submitted."
        )

        return

    if (
        outcome.status
        == "NO_TRADE"
    ):
        print(
            "\nNo approval requested."
        )

        print(
            "No order submitted."
        )

        return

    if (
        outcome.status
        == "RISK_REJECTED"
    ):
        print(
            "\nNo approval requested."
        )

        print(
            "No order submitted."
        )

        return

    if (
        outcome.status
        == "DEMO_EXECUTION_DISABLED"
    ):
        print(
            "\nRisk-approved trade found, "
            "but Demo execution is disabled."
        )

        print(
            "No manual approval requested."
        )

        print(
            "No order submitted."
        )

        return

    if (
        outcome.status
        == "MANUALLY_REJECTED"
    ):
        print(
            "\nNo order submitted."
        )

        return

    if (
        outcome.status
        == "EXECUTION_UNCERTAIN"
    ):
        print(
            "\nOrder state is uncertain."
        )

        print(
            "DO NOT manually retry "
            "this approval/orderLinkId."
        )

        return

    if (
        outcome.status
        != "DEMO_ORDER_CONFIRMED"
    ):
        return

    result = (
        outcome.execution_result
    )

    if result is None:
        raise RuntimeError(
            "DEMO_ORDER_CONFIRMED "
            "without execution result."
        )

    observed = (
        result.observed_order
    )

    print(
        "\n=== EXECUTION RESULT ==="
    )

    print(
        "Coordinator Status: "
        f"{result.status.value}"
    )

    print(
        f"Order ID: "
        f"{observed.order_id}"
    )

    print(
        "OrderLinkId: "
        f"{observed.order_link_id}"
    )

    print(
        "Order Status: "
        f"{observed.order_status}"
    )

    print(
        f"Side: "
        f"{observed.side}"
    )

    print(
        "Quantity: "
        f"{observed.quantity}"
    )

    print(
        f"Price: "
        f"{observed.price}"
    )

    if (
        observed.order_status
        == "Filled"
    ):
        print(
            "Entry is filled."
        )

    elif (
        observed.order_status
        == "PartiallyFilled"
    ):
        print(
            "Entry is partially filled."
        )

    elif (
        observed.order_status
        == "New"
    ):
        print(
            "Limit entry is active "
            "and waiting for a fill."
        )

    else:
        print(
            "Final observed status: "
            f"{observed.order_status}"
        )


# =========================================================
# Real production dependency adapters
# =========================================================


def build_trading_pipeline(
    *,
    journal: TradingRunJournal,
    runner: MarketDataRunner,
) -> TradingPipeline:

    decision_service = (
        build_decision_service()
    )

    risk_state_provider = (
        build_demo_risk_state_provider()
    )

    instrument_rules_client = (
        BybitInstrumentRulesClient()
    )

    approval_gate = (
        ManualApprovalGate()
    )

    approver = (
        ConsoleManualApprover(
            gate=approval_gate
        )
    )

    request_builder = (
        DemoExecutionRequestBuilder()
    )

    def market_context_provider():
        context = (
            MarketContextBuilder(
                runner=runner,
                orderbook_depth_levels=10,
            )
            .build(
                require_healthy=True
            )
        )

        print_market_context(
            context
        )

        return context

    def decision_provider(
        context,
    ):
        print(
            f"\nCalling Groq: "
            f"{GROQ_MODEL}"
        )

        result = (
            decision_service
            .decide(context)
        )

        if (
            result.accepted
            and result.proposal
            is not None
        ):
            print_proposal(
                result.proposal
            )

        return result

    def risk_provider(
        proposal,
    ):
        state = (
            risk_state_provider
            .get_state(SYMBOL)
        )

        print_account_state(
            state
        )

        rules = (
            instrument_rules_client
            .get_linear_rules(
                SYMBOL
            )
        )

        risk_engine = (
            DeterministicRiskEngine(
                instrument_rules=rules
            )
        )

        bridge = (
            DecisionRiskBridge(
                risk_engine=(
                    risk_engine
                )
            )
        )

        result = bridge.evaluate(
            proposal=proposal,
            account=state,
        )

        print_risk_result(
            result
        )

        return result

    def execution_enabled_provider():
        if not ENABLE_DEMO_EXECUTION:
            return False

        # Reuse the existing explicit
        # configuration guard.
        validate_demo_execution_enabled()

        return True

    def approval_provider(
        risk_result,
    ):
        approval_request = (
            approval_gate
            .create_request(
                risk_result
            )
        )

        approval_result = (
            approver.ask(
                approval_request
            )
        )

        return (
            approval_request,
            approval_result,
        )

    def execution_request_provider(
        approval_request,
        approval_result,
    ):
        request = (
            request_builder.build(
                approval_request,
                approval_result,
            )
        )

        print_execution_request(
            request
        )

        return request

    def execution_provider(
        request,
    ):
        print(
            "\nSubmitting "
            "Bybit Demo order..."
        )

        coordinator = (
            build_demo_execution_coordinator()
        )

        return coordinator.execute(
            request
        )

    return TradingPipeline(
        journal=journal,

        market_context_provider=(
            market_context_provider
        ),

        decision_provider=(
            decision_provider
        ),

        risk_provider=(
            risk_provider
        ),

        execution_enabled_provider=(
            execution_enabled_provider
        ),

        approval_provider=(
            approval_provider
        ),

        execution_request_provider=(
            execution_request_provider
        ),

        execution_provider=(
            execution_provider
        ),

        execution_uncertain_exceptions=(
            ExecutionUncertainError,
        ),
    )


# =========================================================
# Real journaled pipeline run
# =========================================================


def run_pipeline(
    journal: TradingRunJournal,
) -> PipelineOutcome:

    runner = MarketDataRunner(
        rest_poll_seconds=60
    )

    try:
        runner.start()

        print(
            "\nCollecting live "
            "market data..."
        )

        sleep(5)

        pipeline = (
            build_trading_pipeline(
                journal=journal,
                runner=runner,
            )
        )

        outcome = (
            pipeline.run()
        )

        print_final_outcome(
            outcome
        )

        return outcome

    finally:
        runner.stop()


def main():
    print(
        "=== Phase 15 — "
        "Integrated Journaled "
        "Bybit Demo Pipeline ==="
    )

    print(
        "\nWARNING:"
    )

    print(
        "Demo execution is protected by "
        "ENABLE_DEMO_EXECUTION and "
        "manual approval."
    )

    # Configuration validation happens
    # before RUN_STARTED.
    validate_groq_settings()

    validate_bybit_demo_settings()

    journal = TradingRunJournal(
        store=JournalStore(),
        symbol=SYMBOL,
    )

    journal.start(
        mode="BYBIT_DEMO"
    )

    print(
        "\nJournal Run ID: "
        f"{journal.run_id}"
    )

    lifecycle = (
        JournalRunLifecycle(
            journal
        )
    )

    lifecycle.run(
        lambda: run_pipeline(
            journal
        )
    )


if __name__ == "__main__":
    main()