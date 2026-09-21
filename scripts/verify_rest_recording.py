from config.settings import SYMBOL

from derivatives.bybit_derivatives import (
    BybitDerivativesService,
)

from market_data.candles import CandleService
from market_data.recorder import (
    JsonlMarketDataRecorder,
)


def count_lines(path) -> int:
    if not path.exists():
        return 0

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return sum(1 for _ in file)


def main():
    print(
        "=== Sprint 1 — REST Raw Recording Verification ==="
    )

    recorder = JsonlMarketDataRecorder()

    candle_service = CandleService(
        recorder=recorder,
    )

    derivatives = BybitDerivativesService(
        recorder=recorder,
    )

    print("\n[1] Recording historical candles...")

    for timeframe in (
        "15m",
        "1h",
        "4h",
    ):
        candles = (
            candle_service.fetch_closed_candles(
                timeframe=timeframe,
                limit=10,
            )
        )

        print(
            f"{timeframe}: "
            f"{len(candles)} closed candles"
        )

    print("\n[2] Recording derivatives...")

    oi = derivatives.get_open_interest(
        interval="15min"
    )

    funding = derivatives.get_funding()

    positioning = derivatives.get_positioning(
        period="15min"
    )

    print(
        f"Open Interest: {oi.current} BTC"
    )

    print(
        f"Funding Rate: "
        f"{funding.current_funding_rate}"
    )

    print(
        f"Long Ratio: "
        f"{positioning.account_holder_long_ratio}"
    )

    recorder.close()

    print("\n[3] Recorded files")

    required_sources = [
        "historical_kline_15m",
        "historical_kline_1h",
        "historical_kline_4h",
        "open_interest",
        "funding_ticker",
        "instrument_info",
        "account_positioning",
    ]

    for source in required_sources:
        path = recorder.get_file_path(
            source
        )

        lines = count_lines(path)

        print(
            f"{source:<25} "
            f"{lines:>4} lines"
        )

        if path.exists():
            print(
                f"  -> {path}"
            )

        if lines == 0:
            raise RuntimeError(
                f"No raw data recorded "
                f"for {source}."
            )

    print(
        "\nREST raw-data recording: OK"
    )


if __name__ == "__main__":
    main()