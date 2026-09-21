from pybit.unified_trading import HTTP

from config.settings import CATEGORY, SYMBOL


class BybitPublicRestClient:
    def __init__(self):
        self.session = HTTP(
            testnet=False,
            demo=False,
        )

    @staticmethod
    def _validate_response(response: dict, operation: str) -> None:
        if response.get("retCode") != 0:
            raise RuntimeError(
                f"{operation} failed: "
                f"{response.get('retCode')} - {response.get('retMsg')}"
            )

    def get_server_time_ms(self) -> int:
        response = self.session.get_server_time()

        self._validate_response(
            response,
            "Get server time",
        )

        return int(response["result"]["timeSecond"]) * 1000

    def get_klines(
        self,
        interval: str,
        limit: int = 200,
    ) -> dict:
        if not 1 <= limit <= 1000:
            raise ValueError("Kline limit must be between 1 and 1000.")

        response = self.session.get_kline(
            category=CATEGORY,
            symbol=SYMBOL,
            interval=interval,
            limit=limit,
        )

        self._validate_response(
            response,
            f"Get {interval} klines",
        )

        return response
    
    def get_open_interest(
        self,
        interval: str = "15min",
        limit: int = 2,
    ) -> dict:
        response = self.session.get_open_interest(
            category=CATEGORY,
            symbol=SYMBOL,
            intervalTime=interval,
            limit=limit,
        )

        self._validate_response(
            response,
            "Get open interest",
        )

        return response

    def get_funding_rate_history(
        self,
        limit: int = 2,
    ) -> dict:
        response = self.session.get_funding_rate_history(
            category=CATEGORY,
            symbol=SYMBOL,
            limit=limit,
        )

        self._validate_response(
            response,
            "Get funding rate history",
        )

        return response


    def get_long_short_ratio(
        self,
        period: str = "15min",
        limit: int = 2,
    ) -> dict:
        response = self.session.get_long_short_ratio(
            category=CATEGORY,
            symbol=SYMBOL,
            period=period,
            limit=limit,
        )

        self._validate_response(
            response,
            "Get long/short ratio",
        )

        return response


    def get_instrument_info(self) -> dict:
        response = self.session.get_instruments_info(
            category=CATEGORY,
            symbol=SYMBOL,
        )

        self._validate_response(
            response,
            "Get instrument information",
        )

        return response
    
    def get_ticker(self) -> dict:
        response = self.session.get_tickers(
            category=CATEGORY,
            symbol=SYMBOL,
        )

        self._validate_response(
            response,
            "Get ticker",
        )

        return response