from __future__ import annotations

from config.settings import (
    SYMBOL,
)

from evaluation.system_metrics import (
    SystemEvaluationEngine,
)

from journal.store import (
    JournalStore,
)


def value_or_na(
    value,
):
    if value is None:
        return "N/A"

    return str(value)


def main():
    report = (
        SystemEvaluationEngine(
            JournalStore()
        )
        .calculate(
            symbol=SYMBOL
        )
    )

    system = report.system

    print(
        "=== AI Futures Trader "
        "System Evaluation ==="
    )

    print(
        f"\nSymbol: {SYMBOL}"
    )

    print(
        "\n=== PIPELINE RUNS ==="
    )

    print(
        f"Total Runs: "
        f"{system.pipeline_runs}"
    )

    print(
        f"Valid Runs: "
        f"{system.valid_runs}"
    )

    print(
        f"Invalid Runs: "
        f"{system.invalid_runs}"
    )

    print(
        f"Error Events: "
        f"{system.error_events}"
    )

    print(
        "\n=== DECISIONS ==="
    )

    print(
        f"Accepted Decisions: "
        f"{system.accepted_decisions}"
    )

    print(
        f"Rejected Decisions: "
        f"{system.rejected_decisions}"
    )

    print(
        f"LONG Proposals: "
        f"{system.long_proposals}"
    )

    print(
        f"SHORT Proposals: "
        f"{system.short_proposals}"
    )

    print(
        f"NO_TRADE Proposals: "
        f"{system.no_trade_proposals}"
    )

    print(
        f"Average Confidence: "
        f"{value_or_na(
            system.average_decision_confidence
        )}"
    )

    print(
        "\n=== RISK / APPROVAL / EXECUTION ==="
    )

    print(
        f"Risk Approved: "
        f"{system.risk_approved}"
    )

    print(
        f"Risk Rejected: "
        f"{system.risk_rejected}"
    )

    print(
        f"Manual Approved: "
        f"{system.manual_approved}"
    )

    print(
        f"Manual Rejected: "
        f"{system.manual_rejected}"
    )

    print(
        f"Execution Results: "
        f"{system.execution_results}"
    )

    print(
        "\n=== TERMINAL STATUS COUNTS ==="
    )

    if (
        system.terminal_status_counts
    ):
        for status in sorted(
            system.terminal_status_counts
        ):
            count = (
                system
                .terminal_status_counts[
                    status
                ]
            )

            print(
                f"{status}: {count}"
            )

    else:
        print(
            "No terminal runs."
        )

    print(
        "\n=== CLOSED-TRADE PERFORMANCE ==="
    )

    print(
        f"Closed Trades: "
        f"{report.closed_trade_count}"
    )

    print(
        f"Wins: "
        f"{report.winning_trades}"
    )

    print(
        f"Losses: "
        f"{report.losing_trades}"
    )

    print(
        f"Breakeven: "
        f"{report.breakeven_trades}"
    )

    print(
        f"Win Rate: "
        f"{report.win_rate * 100}%"
    )

    print(
        f"Total Realized PnL: "
        f"{report.total_realized_pnl}"
    )

    print(
        f"Profit Factor: "
        f"{value_or_na(
            report.profit_factor
        )}"
    )

    print(
        f"Expectancy / Trade: "
        f"{value_or_na(
            report.expectancy_per_trade
        )}"
    )

    print(
        f"Average R: "
        f"{value_or_na(
            report.average_r_multiple
        )}"
    )

    print(
        f"Max Drawdown: "
        f"{report.max_drawdown}"
    )

    print(
        f"Max Consecutive Losses: "
        f"{report.max_consecutive_losses}"
    )


if __name__ == "__main__":
    main()