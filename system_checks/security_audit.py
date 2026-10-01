from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from journal.schema import (
    JournalEvent,
)


FORBIDDEN_KEY_NAMES = {
    "api_key",
    "apikey",
    "api_secret",
    "apisecret",
    "secret_key",
    "secret",
    "password",
    "authorization",
    "access_token",
    "refresh_token",
    "bearer_token",
}


@dataclass(
    frozen=True,
    slots=True,
)
class SecurityAuditIssue:
    location: str
    reason: str


@dataclass(
    frozen=True,
    slots=True,
)
class SecurityAuditResult:
    safe: bool

    event_count: int

    issues: tuple[
        SecurityAuditIssue,
        ...,
    ]


class JournalSecurityAuditor:
    def audit(
        self,
        events: (
            tuple[JournalEvent, ...]
            | list[JournalEvent]
        ),
        *,
        secret_values: (
            tuple[str, ...]
            | list[str]
        ) = (),
    ) -> SecurityAuditResult:

        event_list = tuple(
            events
        )

        issues: list[
            SecurityAuditIssue
        ] = []

        normalized_secrets = tuple(
            value
            for value in secret_values
            if self._is_real_secret(
                value
            )
        )

        for index, event in enumerate(
            event_list
        ):
            base_path = (
                f"event[{index}]"
                f".{event.event_type.value}"
                ".payload"
            )

            self._scan_value(
                event.payload,
                path=base_path,
                secret_values=(
                    normalized_secrets
                ),
                issues=issues,
            )

        return SecurityAuditResult(
            safe=not issues,

            event_count=len(
                event_list
            ),

            issues=tuple(
                issues
            ),
        )

    def _scan_value(
        self,
        value: Any,
        *,
        path: str,
        secret_values:
        tuple[str, ...],
        issues:
        list[SecurityAuditIssue],
    ) -> None:

        if isinstance(
            value,
            dict,
        ):
            for key, item in (
                value.items()
            ):
                key_string = str(
                    key
                )

                normalized_key = (
                    self._normalize_key(
                        key_string
                    )
                )

                child_path = (
                    f"{path}.{key_string}"
                )

                if (
                    normalized_key
                    in FORBIDDEN_KEY_NAMES
                ):
                    issues.append(
                        SecurityAuditIssue(
                            location=(
                                child_path
                            ),

                            reason=(
                                "Forbidden "
                                "credential-related "
                                "field name found."
                            ),
                        )
                    )

                self._scan_value(
                    item,
                    path=child_path,
                    secret_values=(
                        secret_values
                    ),
                    issues=issues,
                )

            return

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            for index, item in (
                enumerate(value)
            ):
                self._scan_value(
                    item,

                    path=(
                        f"{path}[{index}]"
                    ),

                    secret_values=(
                        secret_values
                    ),

                    issues=issues,
                )

            return

        if isinstance(
            value,
            str,
        ):
            for secret in (
                secret_values
            ):
                if secret in value:
                    issues.append(
                        SecurityAuditIssue(
                            location=path,

                            reason=(
                                "Known secret value "
                                "found in journal "
                                "content."
                            ),
                        )
                    )

                    break

    @staticmethod
    def _normalize_key(
        value: str,
    ) -> str:

        return (
            value
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

    @staticmethod
    def _is_real_secret(
        value: str,
    ) -> bool:

        if not isinstance(
            value,
            str,
        ):
            return False

        cleaned = value.strip()

        if len(cleaned) < 6:
            return False

        placeholders = {
            "changeme",
            "your_api_key",
            "your_api_secret",
            "your_secret",
            "none",
            "null",
        }

        return (
            cleaned.lower()
            not in placeholders
        )