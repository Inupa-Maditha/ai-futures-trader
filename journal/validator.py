from __future__ import annotations

from dataclasses import dataclass

from journal.schema import (
    JournalEvent,
    JournalEventType,
)


@dataclass(
    frozen=True,
    slots=True,
)
class JournalValidationResult:
    valid: bool

    run_id: str

    status: str | None

    event_count: int

    errors: tuple[str, ...]


class JournalRunValidator:
    TERMINAL_REQUIREMENTS = {
        "NO_TRADE": {
            JournalEventType.RUN_STARTED,
            JournalEventType.MARKET_CONTEXT,
            JournalEventType.DECISION,
            JournalEventType.RUN_FINISHED,
        },

        "DECISION_REJECTED": {
            JournalEventType.RUN_STARTED,
            JournalEventType.MARKET_CONTEXT,
            JournalEventType.DECISION,
            JournalEventType.RUN_FINISHED,
        },

        "RISK_REJECTED": {
            JournalEventType.RUN_STARTED,
            JournalEventType.MARKET_CONTEXT,
            JournalEventType.DECISION,
            JournalEventType.RISK_RESULT,
            JournalEventType.RUN_FINISHED,
        },

        "DEMO_EXECUTION_DISABLED": {
            JournalEventType.RUN_STARTED,
            JournalEventType.MARKET_CONTEXT,
            JournalEventType.DECISION,
            JournalEventType.RISK_RESULT,
            JournalEventType.RUN_FINISHED,
        },

        "MANUALLY_REJECTED": {
            JournalEventType.RUN_STARTED,
            JournalEventType.MARKET_CONTEXT,
            JournalEventType.DECISION,
            JournalEventType.RISK_RESULT,
            JournalEventType.MANUAL_APPROVAL,
            JournalEventType.RUN_FINISHED,
        },

        "EXECUTION_UNCERTAIN": {
            JournalEventType.RUN_STARTED,
            JournalEventType.MARKET_CONTEXT,
            JournalEventType.DECISION,
            JournalEventType.RISK_RESULT,
            JournalEventType.MANUAL_APPROVAL,
            JournalEventType.ERROR,
            JournalEventType.RUN_FINISHED,
        },

        "DEMO_ORDER_CONFIRMED": {
            JournalEventType.RUN_STARTED,
            JournalEventType.MARKET_CONTEXT,
            JournalEventType.DECISION,
            JournalEventType.RISK_RESULT,
            JournalEventType.MANUAL_APPROVAL,
            JournalEventType.EXECUTION_RESULT,
            JournalEventType.RUN_FINISHED,
        },
        
        "UNHANDLED_ERROR": {
            JournalEventType.RUN_STARTED,
            JournalEventType.ERROR,
            JournalEventType.RUN_FINISHED,
        },

        "PIPELINE_INCOMPLETE": {
            JournalEventType.RUN_STARTED,
            JournalEventType.ERROR,
            JournalEventType.RUN_FINISHED,
        },
        
        "TRADE_OUTCOME_RECORDED": {
            JournalEventType.RUN_STARTED,
            JournalEventType.TRADE_OUTCOME,
            JournalEventType.RUN_FINISHED,
        },
    }

    SINGLETON_TYPES = {
        JournalEventType.RUN_STARTED,
        JournalEventType.MARKET_CONTEXT,
        JournalEventType.DECISION,
        JournalEventType.RISK_RESULT,
        JournalEventType.MANUAL_APPROVAL,
        JournalEventType.EXECUTION_RESULT,
        JournalEventType.RUN_FINISHED,
    }

    def validate(
        self,
        events: tuple[
            JournalEvent,
            ...,
        ],
    ) -> JournalValidationResult:

        errors: list[str] = []

        if not events:
            return JournalValidationResult(
                valid=False,
                run_id="UNKNOWN",
                status=None,
                event_count=0,
                errors=(
                    "Run contains no events.",
                ),
            )

        run_id = events[0].run_id

        # -----------------------------------------
        # 1. All events must belong to one run
        # -----------------------------------------

        for event in events:
            if event.run_id != run_id:
                errors.append(
                    "Events from multiple "
                    "run IDs were supplied."
                )

                break

        # -----------------------------------------
        # 2. Symbol must stay constant
        # -----------------------------------------

        symbol = events[0].symbol

        for event in events:
            if event.symbol != symbol:
                errors.append(
                    "Symbol changed within "
                    "the same journal run."
                )

                break

        # -----------------------------------------
        # 3. Timestamps must be monotonic
        # -----------------------------------------

        previous_timestamp = None

        for event in events:
            if (
                previous_timestamp
                is not None
                and event.timestamp_utc
                < previous_timestamp
            ):
                errors.append(
                    "Journal timestamps are "
                    "not in chronological order."
                )

                break

            previous_timestamp = (
                event.timestamp_utc
            )

        # -----------------------------------------
        # 4. First/last event rules
        # -----------------------------------------

        if (
            events[0].event_type
            != JournalEventType.RUN_STARTED
        ):
            errors.append(
                "First event must be "
                "RUN_STARTED."
            )

        if (
            events[-1].event_type
            != JournalEventType.RUN_FINISHED
        ):
            errors.append(
                "Last event must be "
                "RUN_FINISHED."
            )

        # -----------------------------------------
        # 5. Singleton event counts
        # -----------------------------------------

        counts: dict[
            JournalEventType,
            int,
        ] = {}

        for event in events:
            counts[event.event_type] = (
                counts.get(
                    event.event_type,
                    0,
                )
                + 1
            )

        for event_type in (
            self.SINGLETON_TYPES
        ):
            count = counts.get(
                event_type,
                0,
            )

            if count > 1:
                errors.append(
                    f"{event_type.value} "
                    "appears more than once."
                )

        # -----------------------------------------
        # 6. Read terminal status
        # -----------------------------------------

        status: str | None = None

        finished_events = [
            event
            for event in events
            if (
                event.event_type
                == JournalEventType.RUN_FINISHED
            )
        ]

        if len(finished_events) == 1:
            raw_status = (
                finished_events[0]
                .payload
                .get("status")
            )

            if not isinstance(
                raw_status,
                str,
            ):
                errors.append(
                    "RUN_FINISHED payload "
                    "must contain string "
                    "'status'."
                )

            elif not raw_status:
                errors.append(
                    "RUN_FINISHED status "
                    "must not be empty."
                )

            else:
                status = raw_status

        # -----------------------------------------
        # 7. Required events for final status
        # -----------------------------------------

        if status is not None:
            requirements = (
                self.TERMINAL_REQUIREMENTS
                .get(status)
            )

            if requirements is None:
                errors.append(
                    "Unknown terminal status: "
                    f"{status}."
                )

            else:
                present = set(
                    counts.keys()
                )

                missing = (
                    requirements
                    - present
                )

                for event_type in sorted(
                    missing,
                    key=lambda item:
                    item.value,
                ):
                    errors.append(
                        "Terminal status "
                        f"{status} requires "
                        f"{event_type.value}."
                    )

        # -----------------------------------------
        # 8. Stage ordering
        # -----------------------------------------

        positions = {
            event.event_type: index
            for index, event in enumerate(
                events
            )
        }

        expected_order = (
            JournalEventType.RUN_STARTED,
            JournalEventType.MARKET_CONTEXT,
            JournalEventType.DECISION,
            JournalEventType.RISK_RESULT,
            JournalEventType.MANUAL_APPROVAL,
            JournalEventType.EXECUTION_RESULT,
            JournalEventType.RUN_FINISHED,
        )

        previous_index = -1

        for event_type in expected_order:
            if event_type not in positions:
                continue

            current_index = positions[
                event_type
            ]

            if (
                current_index
                < previous_index
            ):
                errors.append(
                    "Journal stage ordering "
                    "is invalid near "
                    f"{event_type.value}."
                )

                break

            previous_index = (
                current_index
            )

        # -----------------------------------------
        # 9. Terminal-specific forbidden events
        # -----------------------------------------

        if status in (
            "NO_TRADE",
            "DECISION_REJECTED",
        ):
            forbidden = {
                JournalEventType
                .RISK_RESULT,

                JournalEventType
                .MANUAL_APPROVAL,

                JournalEventType
                .EXECUTION_RESULT,
            }

            self._check_forbidden(
                counts=counts,
                forbidden=forbidden,
                status=status,
                errors=errors,
            )

        elif status in (
            "RISK_REJECTED",
            "DEMO_EXECUTION_DISABLED",
        ):
            forbidden = {
                JournalEventType
                .MANUAL_APPROVAL,

                JournalEventType
                .EXECUTION_RESULT,
            }

            self._check_forbidden(
                counts=counts,
                forbidden=forbidden,
                status=status,
                errors=errors,
            )

        elif status == (
            "MANUALLY_REJECTED"
        ):
            forbidden = {
                JournalEventType
                .EXECUTION_RESULT,
            }

            self._check_forbidden(
                counts=counts,
                forbidden=forbidden,
                status=status,
                errors=errors,
            )

        return JournalValidationResult(
            valid=not errors,
            run_id=run_id,
            status=status,
            event_count=len(events),
            errors=tuple(errors),
        )

    @staticmethod
    def _check_forbidden(
        *,
        counts:
        dict[JournalEventType, int],

        forbidden:
        set[JournalEventType],

        status: str,

        errors: list[str],
    ) -> None:

        for event_type in forbidden:
            if (
                counts.get(
                    event_type,
                    0,
                )
                > 0
            ):
                errors.append(
                    f"{event_type.value} "
                    "must not exist for "
                    f"terminal status "
                    f"{status}."
                )