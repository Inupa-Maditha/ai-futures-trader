from __future__ import annotations

from journal.query import (
    JournalQuery,
)

from journal.schema import (
    JournalEventType,
)

from journal.store import (
    JournalStore,
)

from journal.validator import (
    JournalRunValidator,
)


def main():
    print(
        "=== Trading Journal "
        "Integrity Check ==="
    )

    store = JournalStore()

    query = JournalQuery(
        store
    )

    events = query.get_latest_run()

    if not events:
        print(
            "\nNo journal runs found."
        )

        return

    validator = (
        JournalRunValidator()
    )

    result = validator.validate(
        events
    )

    first = events[0]
    last = events[-1]

    print(
        f"\nRun ID: "
        f"{result.run_id}"
    )

    print(
        f"Symbol: "
        f"{first.symbol}"
    )

    print(
        f"Started: "
        f"{first.timestamp_utc.isoformat()}"
    )

    print(
        f"Last Event: "
        f"{last.timestamp_utc.isoformat()}"
    )

    print(
        f"Terminal Status: "
        f"{result.status}"
    )

    print(
        f"Event Count: "
        f"{result.event_count}"
    )

    print(
        "\n=== EVENT SEQUENCE ==="
    )

    for index, event in enumerate(
        events,
        start=1,
    ):
        print(
            f"{index:02d}. "
            f"{event.event_type.value}"
        )

    print(
        "\n=== INTEGRITY ==="
    )

    if result.valid:
        print(
            "VALID"
        )

    else:
        print(
            "INVALID"
        )

        print(
            "\nErrors:"
        )

        for error in result.errors:
            print(
                f"- {error}"
            )

    # -----------------------------------------
    # Useful summary checks
    # -----------------------------------------

    decision_events = [
        event
        for event in events
        if (
            event.event_type
            == JournalEventType
            .DECISION
        )
    ]

    if decision_events:
        payload = (
            decision_events[0]
            .payload
        )

        proposal = payload.get(
            "proposal"
        )

        print(
            "\n=== DECISION SUMMARY ==="
        )

        print(
            f"Accepted: "
            f"{payload.get('accepted')}"
        )

        if isinstance(
            proposal,
            dict,
        ):
            print(
                f"Action: "
                f"{proposal.get('action')}"
            )

            print(
                f"Confidence: "
                f"{proposal.get('confidence')}"
            )

            print(
                f"Setup Quality: "
                f"{proposal.get('setup_quality')}"
            )

    if not result.valid:
        raise RuntimeError(
            "Latest journal run failed "
            "integrity validation."
        )


if __name__ == "__main__":
    main()