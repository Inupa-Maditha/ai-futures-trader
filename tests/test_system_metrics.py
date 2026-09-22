from datetime import (
    datetime,
    timedelta,
    timezone,
)

from decimal import Decimal

from evaluation.outcome_recorder import (
    TradeOutcomeRecorder,
)

from evaluation.schema import (
    TradeExitReason,
    TradeOutcome,
    TradeSide,
)

from evaluation.system_metrics import (
    SystemEvaluationEngine,
)

from journal.schema import (
    JournalEvent,
    JournalEventType,
)

from journal.store import (
    JournalStore,
)


BASE_TIME = datetime(
    2026,
    9,
    22,
    12,
    0,
    tzinfo=timezone.utc,
)


def add_event(
    store,
    *,
    run_id,
    event_type,
    seconds,
    payload=None,
):
    store.append(
        JournalEvent.create(
            run_id=run_id,

            event_type=event_type,

            symbol="BTCUSDT",

            payload=(
                payload
                if payload is not None
                else {}
            ),

            timestamp_utc=(
                BASE_TIME
                + timedelta(
                    seconds=seconds
                )
            ),
        )
    )


def add_no_trade_run(
    store,
    *,
    run_id="run-no-trade",
):
    add_event(
        store,
        run_id=run_id,
        event_type=(
            JournalEventType
            .RUN_STARTED
        ),
        seconds=0,
        payload={
            "mode":
            "BYBIT_DEMO"
        },
    )

    add_event(
        store,
        run_id=run_id,
        event_type=(
            JournalEventType
            .MARKET_CONTEXT
        ),
        seconds=1,
    )

    add_event(
        store,
        run_id=run_id,
        event_type=(
            JournalEventType
            .DECISION
        ),
        seconds=2,
        payload={
            "accepted": True,
            "error": None,

            "proposal": {
                "action":
                "NO_TRADE",

                "confidence":
                "0.4",

                "setup_quality":
                "LOW",
            },
        },
    )

    add_event(
        store,
        run_id=run_id,
        event_type=(
            JournalEventType
            .RUN_FINISHED
        ),
        seconds=3,
        payload={
            "status":
            "NO_TRADE"
        },
    )


def add_confirmed_trade_run(
    store,
):
    run_id = "run-trade"

    add_event(
        store,
        run_id=run_id,
        event_type=(
            JournalEventType
            .RUN_STARTED
        ),
        seconds=10,
        payload={
            "mode":
            "BYBIT_DEMO"
        },
    )

    add_event(
        store,
        run_id=run_id,
        event_type=(
            JournalEventType
            .MARKET_CONTEXT
        ),
        seconds=11,
    )

    add_event(
        store,
        run_id=run_id,
        event_type=(
            JournalEventType
            .DECISION
        ),
        seconds=12,
        payload={
            "accepted": True,
            "error": None,

            "proposal": {
                "action":
                "LONG",

                "confidence":
                "0.8",

                "setup_quality":
                "HIGH",
            },
        },
    )

    add_event(
        store,
        run_id=run_id,
        event_type=(
            JournalEventType
            .RISK_RESULT
        ),
        seconds=13,
        payload={
            "status":
            "RISK_APPROVED",

            "risk_result": {
                "decision":
                "APPROVE"
            },

            "no_trade_reason":
            None,
        },
    )

    add_event(
        store,
        run_id=run_id,
        event_type=(
            JournalEventType
            .MANUAL_APPROVAL
        ),
        seconds=14,
        payload={
            "request": {},

            "result": {
                "decision":
                "APPROVE"
            },
        },
    )

    add_event(
        store,
        run_id=run_id,
        event_type=(
            JournalEventType
            .EXECUTION_RESULT
        ),
        seconds=15,
        payload={
            "request": {},
            "result": {},
        },
    )

    add_event(
        store,
        run_id=run_id,
        event_type=(
            JournalEventType
            .RUN_FINISHED
        ),
        seconds=16,
        payload={
            "status":
            "DEMO_ORDER_CONFIRMED"
        },
    )


def test_empty_system_report(
    tmp_path,
):
    report = (
        SystemEvaluationEngine(
            JournalStore(
                tmp_path
            )
        )
        .calculate(
            symbol="BTCUSDT"
        )
    )

    assert (
        report.system.pipeline_runs
        == 0
    )

    assert (
        report.closed_trade_count
        == 0
    )


def test_no_trade_run_metrics(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    add_no_trade_run(
        store
    )

    report = (
        SystemEvaluationEngine(
            store
        )
        .calculate(
            symbol="BTCUSDT"
        )
    )

    assert (
        report.system.pipeline_runs
        == 1
    )

    assert (
        report.system.valid_runs
        == 1
    )

    assert (
        report.system.no_trade_proposals
        == 1
    )

    assert (
        report.system.accepted_decisions
        == 1
    )

    assert (
        report.system
        .average_decision_confidence
        == Decimal("0.4")
    )


def test_trade_pipeline_counts(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    add_confirmed_trade_run(
        store
    )

    report = (
        SystemEvaluationEngine(
            store
        )
        .calculate(
            symbol="BTCUSDT"
        )
    )

    assert (
        report.system.long_proposals
        == 1
    )

    assert (
        report.system.risk_approved
        == 1
    )

    assert (
        report.system.manual_approved
        == 1
    )

    assert (
        report.system.execution_results
        == 1
    )

    assert (
        report.system
        .terminal_status_counts[
            "DEMO_ORDER_CONFIRMED"
        ]
        == 1
    )


def test_average_confidence(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    add_no_trade_run(
        store,
        run_id="run-1",
    )

    add_confirmed_trade_run(
        store
    )

    report = (
        SystemEvaluationEngine(
            store
        )
        .calculate(
            symbol="BTCUSDT"
        )
    )

    assert (
        report.system
        .average_decision_confidence
        == Decimal("0.6")
    )


def test_outcome_capture_run_not_counted_as_pipeline(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    TradeOutcomeRecorder(
        store
    ).record(
        TradeOutcome(
            trade_id="trade-1",

            run_id="source-run",

            symbol="BTCUSDT",

            side=TradeSide.LONG,

            opened_at_utc=(
                BASE_TIME
            ),

            closed_at_utc=(
                BASE_TIME
                + timedelta(
                    hours=1
                )
            ),

            entry_price=Decimal(
                "85000"
            ),

            exit_price=Decimal(
                "86000"
            ),

            quantity=Decimal(
                "0.01"
            ),

            initial_risk_amount=Decimal(
                "50"
            ),

            realized_pnl=Decimal(
                "100"
            ),

            exit_reason=(
                TradeExitReason
                .TAKE_PROFIT
            ),
        )
    )

    report = (
        SystemEvaluationEngine(
            store
        )
        .calculate(
            symbol="BTCUSDT"
        )
    )

    assert (
        report.system.pipeline_runs
        == 0
    )

    assert (
        report.closed_trade_count
        == 1
    )


def test_trade_metrics_included(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    add_confirmed_trade_run(
        store
    )

    TradeOutcomeRecorder(
        store
    ).record(
        TradeOutcome(
            trade_id="trade-1",

            run_id="run-trade",

            symbol="BTCUSDT",

            side=TradeSide.LONG,

            opened_at_utc=(
                BASE_TIME
            ),

            closed_at_utc=(
                BASE_TIME
                + timedelta(
                    hours=1
                )
            ),

            entry_price=Decimal(
                "85000"
            ),

            exit_price=Decimal(
                "87000"
            ),

            quantity=Decimal(
                "0.01"
            ),

            initial_risk_amount=Decimal(
                "50"
            ),

            realized_pnl=Decimal(
                "100"
            ),

            exit_reason=(
                TradeExitReason
                .TAKE_PROFIT
            ),
        )
    )

    report = (
        SystemEvaluationEngine(
            store
        )
        .calculate(
            symbol="BTCUSDT"
        )
    )

    assert (
        report.closed_trade_count
        == 1
    )

    assert (
        report.winning_trades
        == 1
    )

    assert (
        report.total_realized_pnl
        == Decimal("100")
    )

    assert (
        report.average_r_multiple
        == Decimal("2")
    )


def test_invalid_run_counted(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    add_event(
        store,
        run_id="broken",
        event_type=(
            JournalEventType
            .RUN_STARTED
        ),
        seconds=0,
        payload={
            "mode":
            "BYBIT_DEMO"
        },
    )

    add_event(
        store,
        run_id="broken",
        event_type=(
            JournalEventType
            .DECISION
        ),
        seconds=1,
        payload={
            "accepted": True,

            "proposal": {
                "action":
                "NO_TRADE",

                "confidence":
                "0.4",
            },
        },
    )

    report = (
        SystemEvaluationEngine(
            store
        )
        .calculate(
            symbol="BTCUSDT"
        )
    )

    assert (
        report.system.pipeline_runs
        == 1
    )

    assert (
        report.system.invalid_runs
        == 1
    )


def test_terminal_status_counts(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    add_no_trade_run(
        store,
        run_id="run-a",
    )

    add_no_trade_run(
        store,
        run_id="run-b",
    )

    report = (
        SystemEvaluationEngine(
            store
        )
        .calculate(
            symbol="BTCUSDT"
        )
    )

    assert (
        report.system
        .terminal_status_counts[
            "NO_TRADE"
        ]
        == 2
    )