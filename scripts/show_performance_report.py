from __future__ import annotations

from config.settings import (
    SYMBOL,
)

from evaluation.journal_evaluator import (
    JournalPerformanceEvaluator,
)

from journal.store import (
    JournalStore,
)


def display_decimal(
    value,
):
    if value is None:
        return "N/A"

    return str(value)


def main():
    print(
        "=== AI Futures Trader "
        "Performance Report ==="
    )

    evaluator = (
        JournalPerformanceEvaluator(
            JournalStore()
        )
    )

    metrics = evaluator.calculate(
        symbol=SYMBOL
    )

    print(
        f"\nSymbol: {SYMBOL}"
    )

    print(
        f"Closed Trades: "
        f"{metrics.trade_count}"
    )

    print(
        f"Wins: "
        f"{metrics.winning_trades}"
    )

    print(
        f"Losses: "
        f"{metrics.losing_trades}"
    )

    print(
        f"Breakeven: "
        f"{metrics.breakeven_trades}"
    )

    win_rate_percent = (
        metrics.win_rate
        * 100
    )

    print(
        f"Win Rate: "
        f"{win_rate_percent}%"
    )

    print(
        f"Total Realized PnL: "
        f"{metrics.total_realized_pnl}"
    )

    print(
        f"Gross Profit: "
        f"{metrics.gross_profit}"
    )

    print(
        f"Gross Loss: "
        f"{metrics.gross_loss}"
    )

    print(
        f"Average Win: "
        f"{display_decimal(metrics.average_win)}"
    )

    print(
        f"Average Loss: "
        f"{display_decimal(metrics.average_loss)}"
    )

    print(
        f"Profit Factor: "
        f"{display_decimal(metrics.profit_factor)}"
    )

    print(
        f"Expectancy / Trade: "
        f"{display_decimal(metrics.expectancy_per_trade)}"
    )

    print(
        f"Average R: "
        f"{display_decimal(metrics.average_r_multiple)}"
    )

    print(
        f"Best Trade: "
        f"{display_decimal(metrics.best_trade_pnl)}"
    )

    print(
        f"Worst Trade: "
        f"{display_decimal(metrics.worst_trade_pnl)}"
    )

    print(
        f"Max Drawdown: "
        f"{metrics.max_drawdown}"
    )

    print(
        f"Max Consecutive Losses: "
        f"{metrics.max_consecutive_losses}"
    )

    if metrics.trade_count == 0:
        print(
            "\nNo closed trade outcomes "
            "have been recorded yet."
        )


if __name__ == "__main__":
    main()