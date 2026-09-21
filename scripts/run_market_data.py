from time import sleep

from market_data.runner import MarketDataRunner


def main():
    runner = MarketDataRunner(
        rest_poll_seconds=60,
    )

    try:
        runner.start()

        print(
            "\nRunning continuously."
        )

        print(
            "Press Ctrl+C to stop safely."
        )

        while True:
            sleep(30)

            runner.print_health_summary()

            print(
                "\nMarket data ready:",
                runner.market_data_ready(),
            )

            print(
                f"Order-book messages: "
                f"{runner.orderbook.message_count}"
            )

            print(
                f"Public trades: "
                f"{runner.trades.total_trade_count}"
            )

            print(
                f"Kline messages: "
                f"{runner.candles.message_count}"
            )

            print(
                f"Liquidation events: "
                f"{runner.liquidations.total_event_count}"
            )

    except KeyboardInterrupt:
        print(
            "\nKeyboard interrupt received."
        )

    finally:
        runner.stop()


if __name__ == "__main__":
    main()