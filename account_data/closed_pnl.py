from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from pybit.unified_trading import HTTP


class DailyClosedPnlSnapshot(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    symbol: str

    start_utc: datetime
    end_utc: datetime

    record_count: int = Field(
        ge=0
    )

    realized_pnl: Decimal


class BybitDemoClosedPnlClient:
    PAGE_LIMIT = 100
    MAX_PAGES = 100

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        session=None,
    ):
        if not api_key:
            raise ValueError(
                "api_key is required."
            )

        if not api_secret:
            raise ValueError(
                "api_secret is required."
            )

        self.session = (
            session
            if session is not None
            else HTTP(
                testnet=False,
                demo=True,
                api_key=api_key,
                api_secret=api_secret,
            )
        )

    def get_today_realized_pnl(
        self,
        symbol: str,
        now_utc: datetime | None = None,
    ) -> DailyClosedPnlSnapshot:

        now = (
            now_utc
            if now_utc is not None
            else datetime.now(
                timezone.utc
            )
        )

        if (
            now.tzinfo is None
            or now.utcoffset() is None
        ):
            raise ValueError(
                "now_utc must be "
                "timezone-aware."
            )

        now = now.astimezone(
            timezone.utc
        )

        start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        start_ms = int(
            start.timestamp() * 1000
        )

        end_ms = int(
            now.timestamp() * 1000
        )

        total_pnl = Decimal("0")
        record_count = 0

        cursor: str | None = None

        seen_cursors: set[str] = set()

        for _ in range(
            self.MAX_PAGES
        ):
            params = {
                "category": "linear",
                "symbol": symbol,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": self.PAGE_LIMIT,
            }

            if cursor:
                params["cursor"] = cursor

            response = (
                self.session
                .get_closed_pnl(
                    **params
                )
            )

            self._validate_response(
                response
            )

            result = response.get(
                "result",
                {},
            )

            records = result.get(
                "list",
                [],
            )

            for record in records:
                record_symbol = (
                    record.get("symbol")
                )

                if (
                    record_symbol
                    != symbol
                ):
                    raise RuntimeError(
                        "Bybit returned "
                        "closed PnL for an "
                        "unexpected symbol."
                    )

                updated_time = (
                    self._integer(
                        record.get(
                            "updatedTime"
                        ),
                        field_name=(
                            "updatedTime"
                        ),
                    )
                )

                if not (
                    start_ms
                    <= updated_time
                    <= end_ms
                ):
                    raise RuntimeError(
                        "Bybit returned a "
                        "closed PnL record "
                        "outside the requested "
                        "UTC day range."
                    )

                closed_pnl = (
                    self._decimal(
                        record.get(
                            "closedPnl"
                        ),
                        field_name=(
                            "closedPnl"
                        ),
                    )
                )

                total_pnl += closed_pnl
                record_count += 1

            next_cursor = (
                result.get(
                    "nextPageCursor"
                )
                or ""
            )

            if not next_cursor:
                break

            if (
                next_cursor
                in seen_cursors
            ):
                raise RuntimeError(
                    "Bybit closed PnL "
                    "pagination cursor "
                    "repeated unexpectedly."
                )

            seen_cursors.add(
                next_cursor
            )

            cursor = next_cursor

        else:
            raise RuntimeError(
                "Bybit closed PnL "
                "pagination exceeded "
                "the safety page limit."
            )

        return DailyClosedPnlSnapshot(
            symbol=symbol,
            start_utc=start,
            end_utc=now,
            record_count=(
                record_count
            ),
            realized_pnl=total_pnl,
        )

    @staticmethod
    def _validate_response(
        response: dict,
    ) -> None:
        if response.get("retCode") != 0:
            raise RuntimeError(
                "Bybit closed PnL "
                "request failed: "
                f"{response}"
            )

    @staticmethod
    def _decimal(
        value,
        *,
        field_name: str,
    ) -> Decimal:
        if value in (
            None,
            "",
        ):
            raise RuntimeError(
                f"Bybit field "
                f"'{field_name}' "
                "is missing or empty."
            )

        try:
            return Decimal(
                str(value)
            )

        except Exception as exc:
            raise RuntimeError(
                f"Invalid decimal "
                f"'{field_name}': "
                f"{value!r}"
            ) from exc

    @staticmethod
    def _integer(
        value,
        *,
        field_name: str,
    ) -> int:
        if value in (
            None,
            "",
        ):
            raise RuntimeError(
                f"Bybit field "
                f"'{field_name}' "
                "is missing or empty."
            )

        try:
            return int(value)

        except Exception as exc:
            raise RuntimeError(
                f"Invalid integer "
                f"'{field_name}': "
                f"{value!r}"
            ) from exc