from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

import pytest

from evaluation.journal_evaluator import (
    JournalPerformanceEvaluator,
)
from evaluation.outcome_recorder import (
    TradeOutcomeRecorder,
)
from evaluation.schema import (
    TradeExitReason,
    TradeOutcome,
    TradeSide,
)

from journal.schema import (
    JournalEvent,
    JournalEventType,
)
from journal.store import (
    JournalStore,
)
from journal.validator import (
    JournalRunValidator,
)


BASE_TIME = datetime(
    2026,
    9,
    22,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_outcome(
    *,
    trade_id="trade-1",
    source_run_id="source-run-1",
    pnl="100",
    risk="50",
    close_offset=1,
    symbol="BTCUSDT",
):
    return TradeOutcome(
        trade_id=trade_id,

        run_id=source_run_id,

        symbol=symbol,

        side=TradeSide.LONG,

        opened_at_utc=BASE_TIME,

        closed_at_utc=(
            BASE_TIME
            + timedelta(
                hours=close_offset
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
            risk
        ),

        realized_pnl=Decimal(
            pnl
        ),

        exit_reason=(
            TradeExitReason
            .TAKE_PROFIT
        ),
    )


def test_outcome_recorder_creates_valid_run(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    recorder = TradeOutcomeRecorder(
        store
    )

    capture_run_id = (
        recorder.record(
            make_outcome()
        )
    )

    events = store.read_events(
        run_id=capture_run_id
    )

    assert [
        event.event_type
        for event in events
    ] == [
        JournalEventType
        .RUN_STARTED,

        JournalEventType
        .TRADE_OUTCOME,

        JournalEventType
        .RUN_FINISHED,
    ]

    validation = (
        JournalRunValidator()
        .validate(events)
    )

    assert validation.valid is True

    assert (
        validation.status
        == "TRADE_OUTCOME_RECORDED"
    )


def test_outcome_round_trip(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    original = make_outcome(
        trade_id="trade-abc",
        pnl="123.45",
    )

    TradeOutcomeRecorder(
        store
    ).record(
        original
    )

    outcomes = (
        JournalPerformanceEvaluator(
            store
        )
        .load_outcomes()
    )

    assert len(outcomes) == 1

    restored = outcomes[0]

    assert (
        restored.trade_id
        == "trade-abc"
    )

    assert (
        restored.run_id
        == "source-run-1"
    )

    assert (
        restored.realized_pnl
        == Decimal("123.45")
    )


def test_historical_metrics_rebuilt(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    recorder = TradeOutcomeRecorder(
        store
    )

    recorder.record(
        make_outcome(
            trade_id="trade-1",
            pnl="100",
            close_offset=1,
        )
    )

    recorder.record(
        make_outcome(
            trade_id="trade-2",
            pnl="-50",
            close_offset=2,
        )
    )

    recorder.record(
        make_outcome(
            trade_id="trade-3",
            pnl="150",
            close_offset=3,
        )
    )

    metrics = (
        JournalPerformanceEvaluator(
            store
        )
        .calculate(
            symbol="BTCUSDT"
        )
    )

    assert (
        metrics.trade_count
        == 3
    )

    assert (
        metrics.winning_trades
        == 2
    )

    assert (
        metrics.losing_trades
        == 1
    )

    assert (
        metrics.total_realized_pnl
        == Decimal("200")
    )

    assert (
        metrics.profit_factor
        == Decimal("5")
    )


def test_symbol_filter(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    recorder = TradeOutcomeRecorder(
        store
    )

    recorder.record(
        make_outcome(
            trade_id="btc",
            symbol="BTCUSDT",
        )
    )

    recorder.record(
        make_outcome(
            trade_id="eth",
            symbol="ETHUSDT",
        )
    )

    outcomes = (
        JournalPerformanceEvaluator(
            store
        )
        .load_outcomes(
            symbol="BTCUSDT"
        )
    )

    assert len(outcomes) == 1

    assert (
        outcomes[0].symbol
        == "BTCUSDT"
    )


def test_duplicate_trade_id_rejected(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    recorder = TradeOutcomeRecorder(
        store
    )

    recorder.record(
        make_outcome(
            trade_id="same",
            pnl="100",
        )
    )

    recorder.record(
        make_outcome(
            trade_id="same",
            pnl="-50",
            close_offset=2,
        )
    )

    evaluator = (
        JournalPerformanceEvaluator(
            store
        )
    )

    with pytest.raises(
        ValueError,
        match="Duplicate",
    ):
        evaluator.calculate()


def test_invalid_outcome_payload_fails_closed(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    event = JournalEvent.create(
        run_id="capture-run",

        event_type=(
            JournalEventType
            .TRADE_OUTCOME
        ),

        symbol="BTCUSDT",

        payload={
            "outcome": {
                "bad": "data"
            }
        },

        timestamp_utc=BASE_TIME,
    )

    store.append(
        event
    )

    with pytest.raises(
        RuntimeError,
        match="Invalid TradeOutcome",
    ):
        (
            JournalPerformanceEvaluator(
                store
            )
            .load_outcomes()
        )


def test_event_symbol_mismatch_fails_closed(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    outcome = make_outcome(
        symbol="BTCUSDT"
    )

    event = JournalEvent.create(
        run_id="capture-run",

        event_type=(
            JournalEventType
            .TRADE_OUTCOME
        ),

        symbol="ETHUSDT",

        payload={
            "outcome":
            outcome.model_dump(
                mode="json"
            )
        },

        timestamp_utc=BASE_TIME,
    )

    store.append(
        event
    )

    with pytest.raises(
        RuntimeError,
        match="symbol",
    ):
        (
            JournalPerformanceEvaluator(
                store
            )
            .load_outcomes()
        )