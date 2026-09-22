from datetime import (
    datetime,
    timedelta,
    timezone,
)

from decimal import Decimal

import pytest

from evaluation.bybit_outcome_importer import (
    BybitDemoOutcomeImporter,
)

from evaluation.journal_evaluator import (
    JournalPerformanceEvaluator,
)

from evaluation.outcome_recorder import (
    TradeOutcomeRecorder,
)

from evaluation.schema import (
    TradeExitReason,
    TradeSide,
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


ENTRY_LINK_ID = (
    "aft-v1-entry-test"
)


def ms(
    value: datetime,
) -> str:
    return str(
        int(
            value.timestamp()
            * 1000
        )
    )


def add_execution_run(
    store: JournalStore,
):
    run_id = "source-run-1"

    risk_event = (
        JournalEvent.create(
            run_id=run_id,

            event_type=(
                JournalEventType
                .RISK_RESULT
            ),

            symbol="BTCUSDT",

            payload={
                "status":
                "RISK_APPROVED",

                "no_trade_reason":
                None,

                "risk_result": {
                    "decision":
                    "APPROVE",

                    "reasons": [],

                    "plan": {
                        "actual_risk_amount":
                        "50"
                    },
                },
            },

            timestamp_utc=(
                BASE_TIME
            ),
        )
    )

    execution_event = (
        JournalEvent.create(
            run_id=run_id,

            event_type=(
                JournalEventType
                .EXECUTION_RESULT
            ),

            symbol="BTCUSDT",

            payload={
                "request": {
                    "approval_id":
                    "approval-1",

                    "order_link_id":
                    ENTRY_LINK_ID,

                    "symbol":
                    "BTCUSDT",

                    "side":
                    "Buy",

                    "quantity":
                    "0.050",

                    "entry_price":
                    "85000",

                    "stop_loss":
                    "84000",

                    "take_profit":
                    "87000",

                    "leverage":
                    "1",
                },

                "result": {
                    "status":
                    "SUBMITTED_CONFIRMED"
                },
            },

            timestamp_utc=(
                BASE_TIME
                + timedelta(
                    minutes=1
                )
            ),
        )
    )

    store.append(
        risk_event
    )

    store.append(
        execution_event
    )


class FakeSession:
    def __init__(
        self,
        *,
        stop_order_type="TakeProfit",
        parent_link_id=ENTRY_LINK_ID,
        closed_size="0.050",
        api_error=False,
    ):
        self.stop_order_type = (
            stop_order_type
        )

        self.parent_link_id = (
            parent_link_id
        )

        self.closed_size = (
            closed_size
        )

        self.api_error = (
            api_error
        )

    def get_closed_pnl(
        self,
        **kwargs,
    ):
        if self.api_error:
            return {
                "retCode": 10001,
                "retMsg": "error",
            }

        return {
            "retCode": 0,

            "result": {
                "list": [
                    {
                        "symbol":
                        "BTCUSDT",

                        "orderId":
                        "close-order-1",

                        "side":
                        "Sell",

                        "qty":
                        self.closed_size,

                        "closedSize":
                        self.closed_size,

                        "avgEntryPrice":
                        "85000",

                        "avgExitPrice":
                        "87000",

                        "closedPnl":
                        "100",

                        "execType":
                        "Trade",

                        "createdTime":
                        ms(
                            BASE_TIME
                            + timedelta(
                                hours=2
                            )
                        ),

                        "updatedTime":
                        ms(
                            BASE_TIME
                            + timedelta(
                                hours=2,
                                minutes=1,
                            )
                        ),
                    }
                ],

                "nextPageCursor":
                "",
            },
        }

    def get_order_history(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [
                    {
                        "symbol":
                        "BTCUSDT",

                        "orderId":
                        "close-order-1",

                        "orderLinkId":
                        "",

                        "parentOrderLinkId":
                        self.parent_link_id,

                        "stopOrderType":
                        self.stop_order_type,

                        "createType":
                        "",
                    }
                ],
            },
        }

    def get_executions(
        self,
        **kwargs,
    ):
        return {
            "retCode": 0,

            "result": {
                "list": [
                    {
                        "symbol":
                        "BTCUSDT",

                        "orderLinkId":
                        ENTRY_LINK_ID,

                        "execType":
                        "Trade",

                        "execQty":
                        "0.050",

                        "execTime":
                        ms(
                            BASE_TIME
                            + timedelta(
                                minutes=5
                            )
                        ),
                    }
                ],
            },
        }


def build_importer(
    tmp_path,
    session,
):
    store = JournalStore(
        tmp_path
    )

    add_execution_run(
        store
    )

    recorder = TradeOutcomeRecorder(
        store
    )

    importer = (
        BybitDemoOutcomeImporter(
            session=session,
            store=store,
            recorder=recorder,
        )
    )

    return (
        store,
        importer,
    )


def test_take_profit_outcome_imported(
    tmp_path,
):
    store, importer = build_importer(
        tmp_path,
        FakeSession(),
    )

    result = importer.import_recent(
        symbol="BTCUSDT",
        now_utc=(
            BASE_TIME
            + timedelta(
                days=1
            )
        ),
    )

    assert result.imported == 1

    outcomes = (
        JournalPerformanceEvaluator(
            store
        )
        .load_outcomes()
    )

    assert len(outcomes) == 1

    outcome = outcomes[0]

    assert (
        outcome.trade_id
        == "bybit:close-order-1"
    )

    assert (
        outcome.run_id
        == "source-run-1"
    )

    assert (
        outcome.side
        == TradeSide.LONG
    )

    assert (
        outcome.exit_reason
        == TradeExitReason
        .TAKE_PROFIT
    )

    assert (
        outcome.realized_pnl
        == Decimal("100")
    )

    assert (
        outcome.initial_risk_amount
        == Decimal("50")
    )

    assert (
        outcome.r_multiple
        == Decimal("2")
    )


def test_stop_loss_reason_imported(
    tmp_path,
):
    store, importer = build_importer(
        tmp_path,
        FakeSession(
            stop_order_type=(
                "StopLoss"
            )
        ),
    )

    result = importer.import_recent(
        symbol="BTCUSDT",
        now_utc=(
            BASE_TIME
            + timedelta(
                days=1
            )
        ),
    )

    assert result.imported == 1

    outcome = (
        JournalPerformanceEvaluator(
            store
        )
        .load_outcomes()[0]
    )

    assert (
        outcome.exit_reason
        == TradeExitReason
        .STOP_LOSS
    )


def test_second_import_is_idempotent(
    tmp_path,
):
    store, importer = build_importer(
        tmp_path,
        FakeSession(),
    )

    now = (
        BASE_TIME
        + timedelta(
            days=1
        )
    )

    first = importer.import_recent(
        symbol="BTCUSDT",
        now_utc=now,
    )

    second = importer.import_recent(
        symbol="BTCUSDT",
        now_utc=now,
    )

    assert first.imported == 1

    assert second.imported == 0

    assert (
        second.already_recorded
        == 1
    )

    outcomes = (
        JournalPerformanceEvaluator(
            store
        )
        .load_outcomes()
    )

    assert len(outcomes) == 1


def test_unmatched_parent_is_skipped(
    tmp_path,
):
    store, importer = build_importer(
        tmp_path,
        FakeSession(
            parent_link_id=(
                "unknown-parent"
            )
        ),
    )

    result = importer.import_recent(
        symbol="BTCUSDT",
        now_utc=(
            BASE_TIME
            + timedelta(
                days=1
            )
        ),
    )

    assert result.imported == 0

    assert result.unmatched == 1

    assert (
        JournalPerformanceEvaluator(
            store
        )
        .load_outcomes()
        == ()
    )


def test_partial_close_is_not_guessed(
    tmp_path,
):
    store, importer = build_importer(
        tmp_path,
        FakeSession(
            closed_size="0.025"
        ),
    )

    result = importer.import_recent(
        symbol="BTCUSDT",
        now_utc=(
            BASE_TIME
            + timedelta(
                days=1
            )
        ),
    )

    assert result.imported == 0

    assert (
        result.unsupported
        == 1
    )


def test_closed_pnl_api_error_fails_closed(
    tmp_path,
):
    _, importer = build_importer(
        tmp_path,
        FakeSession(
            api_error=True
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="closed PnL",
    ):
        importer.import_recent(
            symbol="BTCUSDT",
            now_utc=(
                BASE_TIME
                + timedelta(
                    days=1
                )
            ),
        )