from __future__ import annotations

import subprocess
from pathlib import Path

from config.settings import (
    BYBIT_DEMO_API_KEY,
    BYBIT_DEMO_API_SECRET,
    ENABLE_DEMO_EXECUTION,
    GROQ_API_KEY,
)

from journal.store import (
    JournalStore,
)

from system_checks.security_audit import (
    JournalSecurityAuditor,
)


ENV_FILE = Path(
    ".env"
)


def check_env_gitignored():
    result = subprocess.run(
        [
            "git",
            "check-ignore",
            ".env",
        ],

        capture_output=True,
        text=True,
        check=False,
    )

    return (
        result.returncode
        == 0
    )


def main():
    print(
        "=== V1 Security Audit ==="
    )

    failures: list[str] = []

    # -----------------------------------------
    # Journal secret audit
    # -----------------------------------------

    store = JournalStore()

    events = store.read_events()

    journal_result = (
        JournalSecurityAuditor()
        .audit(
            events,

            secret_values=(
                BYBIT_DEMO_API_KEY,
                BYBIT_DEMO_API_SECRET,
                GROQ_API_KEY,
            ),
        )
    )

    print(
        "\n=== JOURNAL ==="
    )

    print(
        f"Events scanned: "
        f"{journal_result.event_count}"
    )

    if journal_result.safe:
        print(
            "Secret Leak Check: PASS"
        )

    else:
        print(
            "Secret Leak Check: FAIL"
        )

        for issue in (
            journal_result.issues
        ):
            print(
                f"- {issue.location}: "
                f"{issue.reason}"
            )

        failures.append(
            "Journal contains possible "
            "credential material."
        )

    # -----------------------------------------
    # .env Git protection
    # -----------------------------------------

    print(
        "\n=== GIT SECRET PROTECTION ==="
    )

    env_ignored = (
        check_env_gitignored()
    )

    print(
        f".env exists: "
        f"{ENV_FILE.exists()}"
    )

    print(
        f".env ignored by Git: "
        f"{env_ignored}"
    )

    if not env_ignored:
        failures.append(
            ".env is not ignored by Git."
        )

    # -----------------------------------------
    # Demo execution switch
    # -----------------------------------------

    print(
        "\n=== EXECUTION SAFETY ==="
    )

    print(
        "ENABLE_DEMO_EXECUTION: "
        f"{ENABLE_DEMO_EXECUTION}"
    )

    if ENABLE_DEMO_EXECUTION:
        print(
            "Status: WARNING — Demo order "
            "execution is currently enabled."
        )

    else:
        print(
            "Status: SAFE DEFAULT — "
            "Demo execution is disabled."
        )

    # -----------------------------------------
    # Final result
    # -----------------------------------------

    print(
        "\n=== AUDIT RESULT ==="
    )

    if failures:
        print(
            "FAIL"
        )

        for failure in failures:
            print(
                f"- {failure}"
            )

        raise SystemExit(1)

    print(
        "PASS"
    )

    print(
        "No journal credential leaks "
        "were detected."
    )


if __name__ == "__main__":
    main()