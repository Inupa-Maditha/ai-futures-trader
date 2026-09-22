from __future__ import annotations

from journal.lifecycle import (
    JournalRunLifecycle,
)
from journal.store import (
    JournalStore,
)
from journal.trading_journal import (
    TradingRunJournal,
)

from evaluation.schema import (
    TradeOutcome,
)


class TradeOutcomeRecorder:
    def __init__(
        self,
        store: JournalStore,
    ):
        self.store = store

    def record(
        self,
        outcome: TradeOutcome,
    ) -> str:
        """
        Store one closed-trade outcome in its own
        append-only journal run.

        Returns the journal run ID used for the
        outcome-capture operation.

        outcome.run_id still points to the original
        trading/execution run.
        """

        journal = TradingRunJournal(
            store=self.store,
            symbol=outcome.symbol,
        )

        journal.start(
            mode="TRADE_OUTCOME_CAPTURE"
        )

        lifecycle = JournalRunLifecycle(
            journal
        )

        def operation():
            journal.record_trade_outcome(
                outcome
            )

            journal.finish(
                status="TRADE_OUTCOME_RECORDED"
            )

        lifecycle.run(
            operation
        )

        return journal.run_id