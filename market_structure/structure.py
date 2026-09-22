from __future__ import annotations

from dataclasses import dataclass

from market_structure.swings import SwingPoint


@dataclass(frozen=True, slots=True)
class ClassifiedSwing:
    timeframe: str
    index: int
    start_ts_ms: int
    price: float

    kind: str
    classification: str


class StructureClassifier:
    def classify(
        self,
        swings: list[SwingPoint],
    ) -> list[ClassifiedSwing]:

        if not swings:
            return []

        timeframes = {
            swing.timeframe
            for swing in swings
        }

        if len(timeframes) != 1:
            raise ValueError(
                "Structure classification requires "
                "swings from one timeframe only."
            )

        ordered_swings = sorted(
            swings,
            key=lambda swing: swing.index,
        )

        previous_high: float | None = None
        previous_low: float | None = None

        result: list[ClassifiedSwing] = []

        for swing in ordered_swings:

            classification: str

            if swing.kind == "HIGH":

                if previous_high is None:
                    classification = "H"

                elif swing.price > previous_high:
                    classification = "HH"

                elif swing.price < previous_high:
                    classification = "LH"

                else:
                    classification = "EQH"

                previous_high = swing.price

            elif swing.kind == "LOW":

                if previous_low is None:
                    classification = "L"

                elif swing.price > previous_low:
                    classification = "HL"

                elif swing.price < previous_low:
                    classification = "LL"

                else:
                    classification = "EQL"

                previous_low = swing.price

            else:
                raise ValueError(
                    f"Unsupported swing kind: "
                    f"{swing.kind}"
                )

            result.append(
                ClassifiedSwing(
                    timeframe=swing.timeframe,
                    index=swing.index,
                    start_ts_ms=swing.start_ts_ms,
                    price=swing.price,
                    kind=swing.kind,
                    classification=classification,
                )
            )

        return result