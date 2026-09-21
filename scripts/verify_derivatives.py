from datetime import datetime, timezone

from derivatives.bybit_derivatives import (
    BybitDerivativesService,
)


def format_timestamp(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc,
    ).isoformat()


def main():
    print(
        "=== Sprint 1 — Derivatives Verification ==="
    )

    service = BybitDerivativesService()

    print("\n[1] Open Interest")

    oi = service.get_open_interest(
        interval="15min"
    )

    print(f"Symbol: {oi.symbol}")
    print(f"Interval: {oi.interval}")
    print(f"Current OI: {oi.current} BTC")
    print(f"Previous OI: {oi.previous} BTC")
    print(
        f"Absolute Change: "
        f"{oi.change_absolute} BTC"
    )
    print(
        f"Percentage Change: "
        f"{oi.change_percent}%"
    )
    print(
        "Observation Time:",
        format_timestamp(
            oi.observation_ts_ms
        ),
    )

    print("\n[2] Funding")

    funding = service.get_funding()

    print(
        f"Current Funding Rate: "
        f"{funding.current_funding_rate}"
    )

    print(
        f"Funding Interval: "
        f"{funding.funding_interval_minutes} minutes"
    )

    print(
        "Next Funding Time:",
        format_timestamp(
            funding.next_funding_ts_ms
        ),
    )

    print("\n[3] Account Positioning")

    positioning = service.get_positioning(
        period="15min"
    )

    print(
        f"Long Account Ratio: "
        f"{positioning.account_holder_long_ratio}"
    )

    print(
        f"Short Account Ratio: "
        f"{positioning.account_holder_short_ratio}"
    )

    print(
        f"Long/Short Account Ratio: "
        f"{positioning.long_short_account_ratio}"
    )

    print(
        "Observation Time:",
        format_timestamp(
            positioning.observation_ts_ms
        ),
    )

    print(
        "\nDerivatives verification: OK"
    )


if __name__ == "__main__":
    main()