from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

from journal.schema import (
    JournalEvent,
    JournalEventType,
)

from system_checks.security_audit import (
    JournalSecurityAuditor,
)


NOW = datetime(
    2026,
    9,
    23,
    4,
    0,
    tzinfo=timezone.utc,
)


def make_event(
    payload,
):
    return JournalEvent.create(
        run_id="security-test-run",

        event_type=(
            JournalEventType
            .DECISION
        ),

        symbol="BTCUSDT",

        payload=payload,

        timestamp_utc=NOW,
    )


def test_normal_journal_payload_is_safe():
    events = (
        make_event(
            {
                "accepted": True,

                "proposal": {
                    "action":
                    "NO_TRADE",

                    "confidence":
                    0.4,
                },
            }
        ),
    )

    result = (
        JournalSecurityAuditor()
        .audit(events)
    )

    assert result.safe is True

    assert result.issues == ()


def test_api_key_field_is_detected():
    events = (
        make_event(
            {
                "api_key":
                "should-not-be-here"
            }
        ),
    )

    result = (
        JournalSecurityAuditor()
        .audit(events)
    )

    assert result.safe is False

    assert len(
        result.issues
    ) == 1

    assert (
        "credential"
        in result
        .issues[0]
        .reason
    )


def test_nested_secret_field_is_detected():
    events = (
        make_event(
            {
                "provider": {
                    "credentials": {
                        "api-secret":
                        "bad-value"
                    }
                }
            }
        ),
    )

    result = (
        JournalSecurityAuditor()
        .audit(events)
    )

    assert result.safe is False

    assert any(
        "api-secret"
        in issue.location
        for issue in result.issues
    )


def test_known_secret_value_is_detected():
    real_secret = (
        "super-secret-value-123"
    )

    events = (
        make_event(
            {
                "error": (
                    "Provider failed using "
                    f"{real_secret}"
                )
            }
        ),
    )

    result = (
        JournalSecurityAuditor()
        .audit(
            events,

            secret_values=(
                real_secret,
            ),
        )
    )

    assert result.safe is False

    assert any(
        "Known secret value"
        in issue.reason
        for issue in result.issues
    )


def test_secret_substring_is_detected():
    secret = (
        "abc123-secret-value"
    )

    events = (
        make_event(
            {
                "message": (
                    "Authorization failure: "
                    f"credential={secret}"
                )
            }
        ),
    )

    result = (
        JournalSecurityAuditor()
        .audit(
            events,

            secret_values=(
                secret,
            ),
        )
    )

    assert result.safe is False


def test_blank_secret_is_ignored():
    events = (
        make_event(
            {
                "message":
                "normal journal message"
            }
        ),
    )

    result = (
        JournalSecurityAuditor()
        .audit(
            events,

            secret_values=(
                "",
                "   ",
            ),
        )
    )

    assert result.safe is True


def test_common_non_secret_fields_are_allowed():
    events = (
        make_event(
            {
                "model":
                "openai/gpt-oss-20b",

                "max_tokens":
                2000,

                "order_link_id":
                "aft-v1-test",

                "approval_id":
                "approval-123",

                "decision_id":
                "decision-123",
            }
        ),
    )

    result = (
        JournalSecurityAuditor()
        .audit(events)
    )

    assert result.safe is True