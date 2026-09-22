from __future__ import annotations

from typing import (
    Callable,
    TypeVar,
)

from journal.trading_journal import (
    TradingRunJournal,
)


T = TypeVar("T")


class JournalRunLifecycle:
    """
    Fail-safe wrapper around one trading run.

    Expected pipeline paths should finish the
    journal themselves.

    Unexpected exceptions are automatically
    recorded and the run is closed.
    """

    def __init__(
        self,
        journal:
        TradingRunJournal,
    ):
        self.journal = journal

    def run(
        self,
        operation:
        Callable[[], T],
    ) -> T:

        if not self.journal.is_started:
            raise RuntimeError(
                "Journal must be started "
                "before entering the "
                "fail-safe lifecycle."
            )

        if self.journal.is_finished:
            raise RuntimeError(
                "Journal is already "
                "finished."
            )

        try:
            result = operation()

        except Exception as exc:

            # If the pipeline already closed
            # itself, preserve its terminal
            # journal state.
            if self.journal.is_finished:
                raise

            self.journal.record_error(
                stage="UNHANDLED_PIPELINE",
                error=exc,
            )

            self.journal.finish(
                status="UNHANDLED_ERROR"
            )

            raise

        # A normal function return without
        # RUN_FINISHED is also a lifecycle bug.
        if not self.journal.is_finished:
            error = RuntimeError(
                "Pipeline returned without "
                "writing a terminal journal "
                "status."
            )

            self.journal.record_error(
                stage="LIFECYCLE",
                error=error,
            )

            self.journal.finish(
                status="PIPELINE_INCOMPLETE"
            )

            raise error

        return result