from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

import pytest
from pydantic import BaseModel

from journal.schema import (
    JournalEventType,
)

from journal.store import (
    JournalStore,
)

from journal.trading_journal import (
    TradingRunJournal,
    to_jsonable,
)


class SampleSide(str, Enum):
    LONG = "LONG"


class SampleModel(BaseModel):
    price: Decimal
    side: SampleSide


@dataclass
class SampleResult:
    quantity: Decimal
    status: str


class FakeDecision:
    def __init__(
        self,
        *,
        accepted=True,
        proposal=None,
        error=None,
    ):
        self.accepted = accepted
        self.proposal = proposal
        self.error = error


def test_to_jsonable_preserves_decimal():
    result = to_jsonable(
        Decimal("0.00123400")
    )

    assert result == "0.00123400"


def test_to_jsonable_pydantic_model():
    model = SampleModel(
        price=Decimal(
            "85000.10"
        ),
        side=SampleSide.LONG,
    )

    result = to_jsonable(
        model
    )

    assert (
        result["price"]
        == "85000.10"
    )

    assert (
        result["side"]
        == "LONG"
    )


def test_to_jsonable_dataclass():
    value = SampleResult(
        quantity=Decimal(
            "0.050"
        ),
        status="CONFIRMED",
    )

    result = to_jsonable(
        value
    )

    assert (
        result["quantity"]
        == "0.050"
    )

    assert (
        result["status"]
        == "CONFIRMED"
    )


def test_run_start_and_finish(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    journal = TradingRunJournal(
        store=store,
        symbol="BTCUSDT",
        run_id="run-123",
    )

    journal.start(
        mode="DEMO"
    )

    journal.finish(
        status="NO_TRADE"
    )

    events = store.read_events(
        run_id="run-123"
    )

    assert len(events) == 2

    assert (
        events[0].event_type
        == JournalEventType.RUN_STARTED
    )

    assert (
        events[1].event_type
        == JournalEventType.RUN_FINISHED
    )


def test_decision_is_recorded(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    journal = TradingRunJournal(
        store=store,
        symbol="BTCUSDT",
        run_id="run-1",
    )

    journal.start(
        mode="DEMO"
    )

    proposal = SampleModel(
        price=Decimal(
            "85000.10"
        ),
        side=SampleSide.LONG,
    )

    journal.record_decision(
        FakeDecision(
            accepted=True,
            proposal=proposal,
        )
    )

    events = store.read_events(
        event_type=(
            JournalEventType.DECISION
        )
    )

    assert len(events) == 1

    payload = events[0].payload

    assert (
        payload["accepted"]
        is True
    )

    assert (
        payload["proposal"]["price"]
        == "85000.10"
    )


def test_error_is_recorded(
    tmp_path,
):
    store = JournalStore(
        tmp_path
    )

    journal = TradingRunJournal(
        store=store,
        symbol="BTCUSDT",
    )

    journal.start(
        mode="DEMO"
    )

    journal.record_error(
        stage="EXECUTION",
        error=RuntimeError(
            "network timeout"
        ),
    )

    events = store.read_events(
        event_type=(
            JournalEventType.ERROR
        )
    )

    assert len(events) == 1

    assert (
        events[0]
        .payload["error_type"]
        == "RuntimeError"
    )

    assert (
        events[0]
        .payload["message"]
        == "network timeout"
    )


def test_record_after_finish_rejected(
    tmp_path,
):
    journal = TradingRunJournal(
        store=JournalStore(
            tmp_path
        ),
        symbol="BTCUSDT",
    )

    journal.start(
        mode="DEMO"
    )

    journal.finish(
        status="COMPLETE"
    )

    with pytest.raises(
        RuntimeError
    ):
        journal.record_market_context(
            {
                "test": True
            }
        )


def test_double_finish_rejected(
    tmp_path,
):
    journal = TradingRunJournal(
        store=JournalStore(
            tmp_path
        ),
        symbol="BTCUSDT",
    )

    journal.start(
        mode="DEMO"
    )

    journal.finish(
        status="COMPLETE"
    )

    with pytest.raises(
        RuntimeError
    ):
        journal.finish(
            status="COMPLETE"
        )