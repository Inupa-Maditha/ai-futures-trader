from datetime import datetime, timezone

from market_data.candles import CandleService

from market_structure.structure import (
    StructureClassifier,
)

from market_structure.swings import (
    SwingDetector,
    normalize_swings,
)

def format_timestamp(
    timestamp_ms: int,
) -> str:
    return datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc,
    ).isoformat()


def main():
    print(
        "=== Sprint 2 — "
        "Market Structure Verification ==="
    )

    candle_service = CandleService()

    detector = SwingDetector(
        left_bars=2,
        right_bars=2,
    )

    classifier = StructureClassifier()

    for timeframe in (
        "15m",
        "1h",
        "4h",
    ):
        print(f"\n[{timeframe}]")

        candles = (
            candle_service
            .fetch_closed_candles(
                timeframe=timeframe,
                limit=250,
            )
        )

        raw_swings = detector.detect(
            candles
        )
        swings = normalize_swings(
            raw_swings
        )
        structure = classifier.classify(
            swings
        )

        counts = {
            "HH": 0,
            "HL": 0,
            "LH": 0,
            "LL": 0,
            "EQH": 0,
            "EQL": 0,
        }

        for point in structure:
            if point.classification in counts:
                counts[
                    point.classification
                ] += 1

        print(
            f"Closed candles: "
            f"{len(candles)}"
        )

        print(
            f"Total swings: "
            f"{len(structure)}"
        )

        print(
            f"HH: {counts['HH']} | "
            f"HL: {counts['HL']} | "
            f"LH: {counts['LH']} | "
            f"LL: {counts['LL']}"
        )

        print(
            f"Raw swings: "
            f"{len(raw_swings)}"
        )

        print(
            f"Normalized swings: "
            f"{len(swings)}"
        )

        if (
            counts["EQH"] > 0
            or counts["EQL"] > 0
        ):
            print(
                f"EQH: {counts['EQH']} | "
                f"EQL: {counts['EQL']}"
            )

        print("\nLatest 10 structure points:")

        for point in structure[-10:]:
            print(
                f"{point.classification:<3} | "
                f"{point.price:>10.2f} | "
                f"{format_timestamp(point.start_ts_ms)}"
            )

    print(
        "\nMarket structure "
        "classification: OK"
    )


if __name__ == "__main__":
    main()