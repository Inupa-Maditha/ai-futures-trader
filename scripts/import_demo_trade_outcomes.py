from __future__ import annotations

from pybit.unified_trading import HTTP

from config.settings import (
    BYBIT_DEMO_API_KEY,
    BYBIT_DEMO_API_SECRET,
    SYMBOL,
    validate_bybit_demo_settings,
)

from evaluation.bybit_outcome_importer import (
    BybitDemoOutcomeImporter,
)

from evaluation.outcome_recorder import (
    TradeOutcomeRecorder,
)

from evaluation.journal_evaluator import (
    JournalPerformanceEvaluator,
)

from journal.store import (
    JournalStore,
)


def main():
    print(
        "=== Bybit Demo "
        "Trade Outcome Importer ==="
    )

    print(
        "\nREAD-ONLY EXCHANGE QUERY."
    )

    print(
        "NO ORDER WILL BE PLACED."
    )

    validate_bybit_demo_settings()

    store = JournalStore()

    session = HTTP(
        testnet=False,
        demo=True,
        api_key=BYBIT_DEMO_API_KEY,
        api_secret=BYBIT_DEMO_API_SECRET,
    )

    importer = (
        BybitDemoOutcomeImporter(
            session=session,

            store=store,

            recorder=(
                TradeOutcomeRecorder(
                    store
                )
            ),
        )
    )

    result = importer.import_recent(
        symbol=SYMBOL,
        lookback_days=7,
    )

    print(
        "\n=== IMPORT RESULT ==="
    )

    print(
        f"Closed records scanned: "
        f"{result.scanned_closed_records}"
    )

    print(
        f"Imported: "
        f"{result.imported}"
    )

    print(
        f"Already recorded: "
        f"{result.already_recorded}"
    )

    print(
        f"Unmatched: "
        f"{result.unmatched}"
    )

    print(
        f"Unsupported: "
        f"{result.unsupported}"
    )

    metrics = (
        JournalPerformanceEvaluator(
            store
        )
        .calculate(
            symbol=SYMBOL
        )
    )

    print(
        "\n=== CURRENT METRICS ==="
    )

    print(
        f"Closed Trades: "
        f"{metrics.trade_count}"
    )

    print(
        f"Total Realized PnL: "
        f"{metrics.total_realized_pnl}"
    )

    print(
        f"Win Rate: "
        f"{metrics.win_rate * 100}%"
    )

    print(
        f"Profit Factor: "
        f"{metrics.profit_factor}"
    )


if __name__ == "__main__":
    main()