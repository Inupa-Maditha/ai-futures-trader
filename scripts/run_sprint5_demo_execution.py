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
from approval.schema import (
    ManualApprovalDecision,
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

from risk_manager.account_state_provider import (
    DemoRiskStateProvider,
)
from risk_manager.bridge import (
    DecisionRiskBridge,
    RiskBridgeStatus,
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

    pipeline = DecisionPipeline(
        validator=DecisionValidator()
    )

    return LLMDecisionService(
        provider=provider,
        pipeline=pipeline,
    )


def build_demo_risk_state_provider():
    account_client = BybitDemoAccountClient(
        api_key=BYBIT_DEMO_API_KEY,
        api_secret=BYBIT_DEMO_API_SECRET,
    )

    pnl_client = BybitDemoClosedPnlClient(
        api_key=BYBIT_DEMO_API_KEY,
        api_secret=BYBIT_DEMO_API_SECRET,
    )

    return DemoRiskStateProvider(
        account_client=account_client,
        closed_pnl_client=pnl_client,
    )


def print_proposal(proposal):
    print(
        "\n=== LLM PROPOSAL ==="
    )

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

    if (
        proposal.action
        == DecisionAction.NO_TRADE
    ):
        print(
            f"No Trade Reason: "
            f"{proposal.no_trade_reason}"
        )

        return

    print(
        f"Entry: {proposal.entry_price}"
    )

    print(
        f"Stop Loss: {proposal.stop_loss}"
    )

    print(
        f"Take Profit: {proposal.take_profit}"
    )


def print_risk_plan(plan):
    print(
        "\n=== DETERMINISTIC RISK PLAN ==="
    )

    print(
        f"Side: {plan.side.value}"
    )

    print(
        f"Entry: {plan.entry_price}"
    )

    print(
        f"Stop Loss: {plan.stop_loss}"
    )

    print(
        f"Take Profit: {plan.take_profit}"
    )

    print(
        f"Quantity: "
        f"{plan.executable_quantity} BTC"
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
        f"Reward/Risk: "
        f"{plan.reward_risk_ratio}"
    )

    print(
        f"Notional: "
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


def run_pipeline(
    journal: TradingRunJournal,
):
    runner = MarketDataRunner(
        rest_poll_seconds=60
    )

    try:
        # -------------------------------------------------
        # 1. Public market data
        # -------------------------------------------------

        runner.start()

        print(
            "\nCollecting live market data..."
        )

        sleep(5)

        # -------------------------------------------------
        # 2. Build market context
        # -------------------------------------------------

        context = MarketContextBuilder(
            runner=runner,
            orderbook_depth_levels=10,
        ).build(
            require_healthy=True
        )

        journal.record_market_context(
            context
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

        # -------------------------------------------------
        # 3. Groq decision
        # -------------------------------------------------

        print(
            f"\nCalling Groq: {GROQ_MODEL}"
        )

        decision_result = (
            build_decision_service()
            .decide(context)
        )

        journal.record_decision(
            decision_result
        )

        if (
            not decision_result.accepted
            or decision_result.proposal is None
        ):
            print(
                "\n=== FINAL STATUS ==="
            )

            print(
                "DECISION_REJECTED"
            )

            print(
                f"Error: "
                f"{decision_result.error}"
            )

            journal.finish(
                status="DECISION_REJECTED"
            )

            print(
                "\nNo order submitted."
            )

            return

        proposal = (
            decision_result.proposal
        )

        print_proposal(
            proposal
        )

        # -------------------------------------------------
        # 4. NO_TRADE
        # -------------------------------------------------

        if (
            proposal.action
            == DecisionAction.NO_TRADE
        ):
            journal.finish(
                status="NO_TRADE"
            )

            print(
                "\n=== FINAL STATUS ==="
            )

            print(
                "NO_TRADE"
            )

            print(
                "\nNo approval requested."
            )

            print(
                "No order submitted."
            )

            return

        # -------------------------------------------------
        # 5. Fresh Demo account state
        # -------------------------------------------------

        risk_state = (
            build_demo_risk_state_provider()
            .get_state(SYMBOL)
        )

        print(
            "\n=== DEMO ACCOUNT ==="
        )

        print(
            f"Equity: "
            f"{risk_state.account_equity}"
        )

        print(
            f"Available Balance: "
            f"{risk_state.available_balance}"
        )

        print(
            f"Open Positions: "
            f"{risk_state.open_position_count}"
        )

        print(
            f"Today's Realized PnL: "
            f"{risk_state.daily_realized_pnl}"
        )

        # -------------------------------------------------
        # 6. Current exchange rules
        # -------------------------------------------------

        rules = (
            BybitInstrumentRulesClient()
            .get_linear_rules(SYMBOL)
        )

        # -------------------------------------------------
        # 7. Deterministic risk evaluation
        # -------------------------------------------------

        risk_engine = (
            DeterministicRiskEngine(
                instrument_rules=rules
            )
        )

        bridge = DecisionRiskBridge(
            risk_engine=risk_engine
        )

        bridge_result = bridge.evaluate(
            proposal=proposal,
            account=risk_state,
        )

        journal.record_risk(
            bridge_result
        )

        if (
            bridge_result.status
            != RiskBridgeStatus.RISK_APPROVED
        ):
            print(
                "\n=== FINAL STATUS ==="
            )

            print(
                "RISK_REJECTED"
            )

            if (
                bridge_result.risk_result
                is not None
            ):
                for reason in (
                    bridge_result
                    .risk_result
                    .reasons
                ):
                    print(
                        f"- {reason}"
                    )

            journal.finish(
                status="RISK_REJECTED"
            )

            print(
                "\nNo order submitted."
            )

            return

        if (
            bridge_result.risk_result
            is None
        ):
            raise RuntimeError(
                "RISK_APPROVED result is "
                "missing risk_result."
            )

        plan = (
            bridge_result
            .risk_result
            .plan
        )

        if plan is None:
            raise RuntimeError(
                "Risk approval did not "
                "contain a risk plan."
            )

        print_risk_plan(
            plan
        )

        # -------------------------------------------------
        # 8. Execution safety switch
        # -------------------------------------------------

        if not ENABLE_DEMO_EXECUTION:
            print(
                "\n=== FINAL STATUS ==="
            )

            print(
                "DEMO_EXECUTION_DISABLED"
            )

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

            journal.finish(
                status="DEMO_EXECUTION_DISABLED"
            )

            return

        validate_demo_execution_enabled()

        # -------------------------------------------------
        # 9. Manual approval
        # -------------------------------------------------

        gate = ManualApprovalGate()

        approval_request = (
            gate.create_request(
                bridge_result
            )
        )

        approver = (
            ConsoleManualApprover(
                gate=gate
            )
        )

        approval_result = (
            approver.ask(
                approval_request
            )
        )

        journal.record_manual_approval(
            approval_request=approval_request,
            approval_result=approval_result,
        )

        if (
            approval_result.decision
            != ManualApprovalDecision.APPROVE
        ):
            journal.finish(
                status="MANUALLY_REJECTED"
            )

            print(
                "\n=== FINAL STATUS ==="
            )

            print(
                "MANUALLY_REJECTED"
            )

            print(
                "\nNo order submitted."
            )

            return

        # -------------------------------------------------
        # 10. Build immutable execution request
        # -------------------------------------------------

        execution_request = (
            DemoExecutionRequestBuilder()
            .build(
                approval_request,
                approval_result,
            )
        )

        print(
            "\n=== EXECUTION REQUEST ==="
        )

        print(
            f"OrderLinkId: "
            f"{execution_request.order_link_id}"
        )

        print(
            f"Side: "
            f"{execution_request.side.value}"
        )

        print(
            f"Quantity: "
            f"{execution_request.quantity}"
        )

        print(
            f"Limit Price: "
            f"{execution_request.entry_price}"
        )

        print(
            f"Stop Loss: "
            f"{execution_request.stop_loss}"
        )

        print(
            f"Take Profit: "
            f"{execution_request.take_profit}"
        )

        # -------------------------------------------------
        # 11. Authenticated Demo session
        # -------------------------------------------------

        demo_session = HTTP(
            testnet=False,
            demo=True,
            api_key=BYBIT_DEMO_API_KEY,
            api_secret=BYBIT_DEMO_API_SECRET,
        )

        repository = (
            BybitDemoOrderRepository(
                session=demo_session
            )
        )

        preflight = (
            DemoExecutionPreflight(
                session=demo_session,
                order_repository=repository,
            )
        )

        execution_client = (
            BybitDemoExecutionClient(
                api_key=BYBIT_DEMO_API_KEY,
                api_secret=BYBIT_DEMO_API_SECRET,
                session=demo_session,
            )
        )

        coordinator = (
            DemoExecutionCoordinator(
                execution_client=execution_client,
                order_repository=repository,
                preflight=preflight,
                confirmation_attempts=6,
                confirmation_interval_seconds=0.5,
            )
        )

        # -------------------------------------------------
        # 12. Controlled Demo execution
        # -------------------------------------------------

        print(
            "\nSubmitting Bybit Demo order..."
        )

        try:
            execution_result = (
                coordinator.execute(
                    execution_request
                )
            )

        except ExecutionUncertainError as exc:
            journal.record_error(
                stage="EXECUTION",
                error=exc,
            )

            journal.finish(
                status="EXECUTION_UNCERTAIN"
            )

            print(
                "\n=== FINAL STATUS ==="
            )

            print(
                "EXECUTION_UNCERTAIN"
            )

            print(
                str(exc)
            )

            print(
                "\nDO NOT manually retry "
                "this approval/orderLinkId."
            )

            return

        # -------------------------------------------------
        # 13. Record confirmed execution
        # -------------------------------------------------

        journal.record_execution(
            execution_request=execution_request,
            execution_result=execution_result,
        )

        observed = (
            execution_result
            .observed_order
        )

        print(
            "\n=== EXECUTION RESULT ==="
        )

        print(
            f"Coordinator Status: "
            f"{execution_result.status.value}"
        )

        print(
            f"Order ID: "
            f"{observed.order_id}"
        )

        print(
            f"OrderLinkId: "
            f"{observed.order_link_id}"
        )

        print(
            f"Order Status: "
            f"{observed.order_status}"
        )

        print(
            f"Side: "
            f"{observed.side}"
        )

        print(
            f"Quantity: "
            f"{observed.quantity}"
        )

        print(
            f"Price: "
            f"{observed.price}"
        )

        journal.finish(
            status="DEMO_ORDER_CONFIRMED"
        )

        print(
            "\n=== FINAL STATUS ==="
        )

        print(
            "DEMO_ORDER_CONFIRMED"
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

    finally:
        runner.stop()


def main():
    print(
        "=== Sprint 6 — "
        "Journaled Bybit Demo Pipeline ==="
    )

    print(
        "\nWARNING:"
    )

    print(
        "Demo execution is protected by "
        "ENABLE_DEMO_EXECUTION and "
        "manual approval."
    )

    # -------------------------------------------------
    # Configuration checks happen before journal start.
    # Invalid configuration is not considered a
    # trading-run event.
    # -------------------------------------------------

    validate_groq_settings()
    validate_bybit_demo_settings()

    # -------------------------------------------------
    # Start persistent run journal
    # -------------------------------------------------

    journal = TradingRunJournal(
        store=JournalStore(),
        symbol=SYMBOL,
    )

    journal.start(
        mode="BYBIT_DEMO"
    )

    print(
        f"\nJournal Run ID: "
        f"{journal.run_id}"
    )

    # -------------------------------------------------
    # Fail-safe lifecycle
    #
    # Any unexpected exception after RUN_STARTED:
    #
    # ERROR
    # ↓
    # RUN_FINISHED
    # ↓
    # UNHANDLED_ERROR
    # -------------------------------------------------

    lifecycle = JournalRunLifecycle(
        journal
    )

    lifecycle.run(
        lambda: run_pipeline(
            journal
        )
    )


if __name__ == "__main__":
    main()