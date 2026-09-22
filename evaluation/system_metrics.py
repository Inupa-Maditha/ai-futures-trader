from __future__ import annotations

from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from evaluation.journal_evaluator import (
    JournalPerformanceEvaluator,
)

from journal.query import (
    JournalQuery,
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


ZERO = Decimal("0")


class SystemEvaluationMetrics(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    pipeline_runs: int = Field(
        ge=0
    )

    valid_runs: int = Field(
        ge=0
    )

    invalid_runs: int = Field(
        ge=0
    )

    accepted_decisions: int = Field(
        ge=0
    )

    rejected_decisions: int = Field(
        ge=0
    )

    long_proposals: int = Field(
        ge=0
    )

    short_proposals: int = Field(
        ge=0
    )

    no_trade_proposals: int = Field(
        ge=0
    )

    average_decision_confidence: Decimal | None

    risk_approved: int = Field(
        ge=0
    )

    risk_rejected: int = Field(
        ge=0
    )

    manual_approved: int = Field(
        ge=0
    )

    manual_rejected: int = Field(
        ge=0
    )

    execution_results: int = Field(
        ge=0
    )

    error_events: int = Field(
        ge=0
    )

    terminal_status_counts: dict[str, int]


class SystemEvaluationReport(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    system: SystemEvaluationMetrics

    closed_trade_count: int = Field(
        ge=0
    )

    winning_trades: int = Field(
        ge=0
    )

    losing_trades: int = Field(
        ge=0
    )

    breakeven_trades: int = Field(
        ge=0
    )

    win_rate: Decimal

    total_realized_pnl: Decimal

    profit_factor: Decimal | None

    expectancy_per_trade: Decimal | None

    average_r_multiple: Decimal | None

    max_drawdown: Decimal

    max_consecutive_losses: int = Field(
        ge=0
    )


class SystemEvaluationEngine:
    PIPELINE_EVENT_TYPES = {
        JournalEventType
        .MARKET_CONTEXT,

        JournalEventType
        .DECISION,

        JournalEventType
        .RISK_RESULT,

        JournalEventType
        .MANUAL_APPROVAL,

        JournalEventType
        .EXECUTION_RESULT,
    }

    def __init__(
        self,
        store: JournalStore,
    ):
        self.store = store

    def calculate(
        self,
        *,
        symbol: str | None = None,
    ) -> SystemEvaluationReport:

        runs = JournalQuery(
            self.store
        ).get_all_runs()

        pipeline_runs: list[
            tuple[
                JournalEvent,
                ...,
            ]
        ] = []

        for events in runs.values():
            if (
                symbol is not None
                and events
                and events[0].symbol
                != symbol
            ):
                continue

            if self._is_pipeline_run(
                events
            ):
                pipeline_runs.append(
                    events
                )

        valid_runs = 0
        invalid_runs = 0

        accepted_decisions = 0
        rejected_decisions = 0

        long_proposals = 0
        short_proposals = 0
        no_trade_proposals = 0

        confidences: list[
            Decimal
        ] = []

        risk_approved = 0
        risk_rejected = 0

        manual_approved = 0
        manual_rejected = 0

        execution_results = 0
        error_events = 0

        terminal_status_counts: dict[
            str,
            int,
        ] = {}

        validator = (
            JournalRunValidator()
        )

        for events in pipeline_runs:
            validation = (
                validator.validate(
                    events
                )
            )

            if validation.valid:
                valid_runs += 1

            else:
                invalid_runs += 1

            if validation.status:
                terminal_status_counts[
                    validation.status
                ] = (
                    terminal_status_counts.get(
                        validation.status,
                        0,
                    )
                    + 1
                )

            for event in events:
                if (
                    event.event_type
                    == JournalEventType.DECISION
                ):
                    accepted = (
                        event.payload.get(
                            "accepted"
                        )
                    )

                    if accepted is True:
                        accepted_decisions += 1

                    elif accepted is False:
                        rejected_decisions += 1

                    proposal = (
                        event.payload.get(
                            "proposal"
                        )
                    )

                    if isinstance(
                        proposal,
                        dict,
                    ):
                        action = (
                            proposal.get(
                                "action"
                            )
                        )

                        if action == "LONG":
                            long_proposals += 1

                        elif action == "SHORT":
                            short_proposals += 1

                        elif (
                            action
                            == "NO_TRADE"
                        ):
                            no_trade_proposals += 1

                        confidence = (
                            proposal.get(
                                "confidence"
                            )
                        )

                        if confidence is not None:
                            try:
                                confidence_decimal = (
                                    Decimal(
                                        str(
                                            confidence
                                        )
                                    )
                                )

                            except Exception as exc:
                                raise RuntimeError(
                                    "Invalid decision "
                                    "confidence in "
                                    "journal."
                                ) from exc

                            if not (
                                ZERO
                                <= confidence_decimal
                                <= Decimal("1")
                            ):
                                raise RuntimeError(
                                    "Decision confidence "
                                    "outside valid range."
                                )

                            confidences.append(
                                confidence_decimal
                            )

                elif (
                    event.event_type
                    == JournalEventType
                    .RISK_RESULT
                ):
                    status = (
                        event.payload.get(
                            "status"
                        )
                    )

                    if (
                        status
                        == "RISK_APPROVED"
                    ):
                        risk_approved += 1

                    elif (
                        status
                        == "RISK_REJECTED"
                    ):
                        risk_rejected += 1

                elif (
                    event.event_type
                    == JournalEventType
                    .MANUAL_APPROVAL
                ):
                    result = (
                        event.payload.get(
                            "result"
                        )
                    )

                    if isinstance(
                        result,
                        dict,
                    ):
                        decision = (
                            result.get(
                                "decision"
                            )
                        )

                        if (
                            decision
                            == "APPROVE"
                        ):
                            manual_approved += 1

                        elif (
                            decision
                            == "REJECT"
                        ):
                            manual_rejected += 1

                elif (
                    event.event_type
                    == JournalEventType
                    .EXECUTION_RESULT
                ):
                    execution_results += 1

                elif (
                    event.event_type
                    == JournalEventType.ERROR
                ):
                    error_events += 1

        average_confidence = None

        if confidences:
            average_confidence = (
                sum(
                    confidences,
                    ZERO,
                )
                / Decimal(
                    len(confidences)
                )
            )

        system_metrics = (
            SystemEvaluationMetrics(
                pipeline_runs=(
                    len(
                        pipeline_runs
                    )
                ),

                valid_runs=valid_runs,

                invalid_runs=invalid_runs,

                accepted_decisions=(
                    accepted_decisions
                ),

                rejected_decisions=(
                    rejected_decisions
                ),

                long_proposals=(
                    long_proposals
                ),

                short_proposals=(
                    short_proposals
                ),

                no_trade_proposals=(
                    no_trade_proposals
                ),

                average_decision_confidence=(
                    average_confidence
                ),

                risk_approved=(
                    risk_approved
                ),

                risk_rejected=(
                    risk_rejected
                ),

                manual_approved=(
                    manual_approved
                ),

                manual_rejected=(
                    manual_rejected
                ),

                execution_results=(
                    execution_results
                ),

                error_events=(
                    error_events
                ),

                terminal_status_counts=(
                    terminal_status_counts
                ),
            )
        )

        trade_metrics = (
            JournalPerformanceEvaluator(
                self.store
            )
            .calculate(
                symbol=symbol
            )
        )

        return SystemEvaluationReport(
            system=system_metrics,

            closed_trade_count=(
                trade_metrics
                .trade_count
            ),

            winning_trades=(
                trade_metrics
                .winning_trades
            ),

            losing_trades=(
                trade_metrics
                .losing_trades
            ),

            breakeven_trades=(
                trade_metrics
                .breakeven_trades
            ),

            win_rate=(
                trade_metrics
                .win_rate
            ),

            total_realized_pnl=(
                trade_metrics
                .total_realized_pnl
            ),

            profit_factor=(
                trade_metrics
                .profit_factor
            ),

            expectancy_per_trade=(
                trade_metrics
                .expectancy_per_trade
            ),

            average_r_multiple=(
                trade_metrics
                .average_r_multiple
            ),

            max_drawdown=(
                trade_metrics
                .max_drawdown
            ),

            max_consecutive_losses=(
                trade_metrics
                .max_consecutive_losses
            ),
        )

    def _is_pipeline_run(
        self,
        events:
        tuple[
            JournalEvent,
            ...,
        ],
    ) -> bool:

        if not events:
            return False

        for event in events:
            if (
                event.event_type
                in self.PIPELINE_EVENT_TYPES
            ):
                return True

        # A run may fail immediately after
        # RUN_STARTED before market context
        # is successfully produced.
        for event in events:
            if (
                event.event_type
                == JournalEventType
                .RUN_STARTED
            ):
                mode = (
                    event.payload.get(
                        "mode"
                    )
                )

                if mode == "BYBIT_DEMO":
                    return True

        return False
