from __future__ import annotations

from evaluation.metrics import (
    PerformanceMetrics,
    PerformanceMetricsEngine,
)
from evaluation.schema import (
    TradeOutcome,
)

from journal.schema import (
    JournalEventType,
)
from journal.store import (
    JournalStore,
)


class JournalPerformanceEvaluator:
    def __init__(
        self,
        store: JournalStore,
    ):
        self.store = store

    def load_outcomes(
        self,
        *,
        symbol: str | None = None,
    ) -> tuple[TradeOutcome, ...]:

        events = self.store.read_events(
            event_type=(
                JournalEventType
                .TRADE_OUTCOME
            )
        )

        outcomes: list[
            TradeOutcome
        ] = []

        for event in events:
            raw_outcome = (
                event.payload.get(
                    "outcome"
                )
            )

            if not isinstance(
                raw_outcome,
                dict,
            ):
                raise RuntimeError(
                    "TRADE_OUTCOME event "
                    "is missing a valid "
                    "'outcome' object."
                )

            try:
                outcome = (
                    TradeOutcome
                    .model_validate(
                        raw_outcome
                    )
                )

            except Exception as exc:
                raise RuntimeError(
                    "Invalid TradeOutcome "
                    "journal payload."
                ) from exc

            if (
                event.symbol
                != outcome.symbol
            ):
                raise RuntimeError(
                    "TRADE_OUTCOME event symbol "
                    "does not match the "
                    "stored TradeOutcome."
                )

            if (
                symbol is not None
                and outcome.symbol
                != symbol
            ):
                continue

            outcomes.append(
                outcome
            )

        return tuple(
            sorted(
                outcomes,
                key=lambda trade:
                trade.closed_at_utc,
            )
        )

    def calculate(
        self,
        *,
        symbol: str | None = None,
    ) -> PerformanceMetrics:

        outcomes = (
            self.load_outcomes(
                symbol=symbol
            )
        )

        return (
            PerformanceMetricsEngine()
            .calculate(
                outcomes
            )
        )