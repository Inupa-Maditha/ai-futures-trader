from __future__ import annotations

import csv

from pathlib import Path

from config.settings import (
    SYMBOL,
)

from evaluation.equity_curve import (
    EquityCurveEngine,
)

from evaluation.journal_evaluator import (
    JournalPerformanceEvaluator,
)

from journal.store import (
    JournalStore,
)


OUTPUT_PATH = Path(
    "data/evaluation/"
    "equity_curve.csv"
)


def main():
    print(
        "=== Equity Curve Export ==="
    )

    store = JournalStore()

    outcomes = (
        JournalPerformanceEvaluator(
            store
        )
        .load_outcomes(
            symbol=SYMBOL
        )
    )

    curve = (
        EquityCurveEngine()
        .build(outcomes)
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            [
                "trade_number",
                "trade_id",
                "closed_at_utc",
                "realized_pnl",
                "cumulative_pnl",
                "peak_cumulative_pnl",
                "drawdown",
            ]
        )

        for point in curve.points:
            writer.writerow(
                [
                    point.trade_number,
                    point.trade_id,

                    point
                    .closed_at_utc
                    .isoformat(),

                    str(
                        point.realized_pnl
                    ),

                    str(
                        point.cumulative_pnl
                    ),

                    str(
                        point
                        .peak_cumulative_pnl
                    ),

                    str(
                        point.drawdown
                    ),
                ]
            )

    print(
        f"\nSymbol: {SYMBOL}"
    )

    print(
        f"Closed Trades: "
        f"{len(curve.points)}"
    )

    print(
        f"Final Cumulative PnL: "
        f"{curve.final_cumulative_pnl}"
    )

    print(
        f"Max Drawdown: "
        f"{curve.max_drawdown}"
    )

    print(
        f"CSV: {OUTPUT_PATH}"
    )

    if not curve.points:
        print(
            "\nNo closed system trades yet."
        )

        print(
            "CSV was created with "
            "headers only."
        )


if __name__ == "__main__":
    main()