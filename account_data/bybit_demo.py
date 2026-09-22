from __future__ import annotations

from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from pybit.unified_trading import HTTP


class DemoPositionSnapshot(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    symbol: str

    side: str | None

    size: Decimal = Field(
        ge=0
    )

    avg_price: Decimal | None

    leverage: Decimal | None

    unrealised_pnl: Decimal

    current_realised_pnl: Decimal


class DemoAccountSnapshot(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    account_equity: Decimal = Field(
        gt=0
    )

    available_balance: Decimal = Field(
        ge=0
    )

    open_position_count: int = Field(
        ge=0
    )

    positions: tuple[
        DemoPositionSnapshot,
        ...
    ]


class BybitDemoAccountClient:
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

    def get_snapshot(
        self,
        symbol: str,
    ) -> DemoAccountSnapshot:

        wallet = self._get_wallet()

        positions = self._get_positions(
            symbol=symbol
        )

        account_equity = self._decimal(
            wallet.get("totalEquity"),
            field_name="totalEquity",
        )

        available_balance = self._decimal(
            wallet.get(
                "totalAvailableBalance"
            ),
            field_name=(
                "totalAvailableBalance"
            ),
        )

        if account_equity <= 0:
            raise RuntimeError(
                "Demo account totalEquity "
                "must be greater than zero."
            )

        if available_balance < 0:
            raise RuntimeError(
                "Demo account "
                "totalAvailableBalance "
                "must not be negative."
            )

        parsed_positions = tuple(
            self._parse_position(
                item=item,
                expected_symbol=symbol,
            )
            for item in positions
        )

        open_position_count = sum(
            1
            for position
            in parsed_positions
            if position.size > 0
        )

        return DemoAccountSnapshot(
            account_equity=(
                account_equity
            ),

            available_balance=(
                available_balance
            ),

            open_position_count=(
                open_position_count
            ),

            positions=parsed_positions,
        )

    def _get_wallet(
        self,
    ) -> dict:

        response = (
            self.session
            .get_wallet_balance(
                accountType="UNIFIED"
            )
        )

        self._validate_response(
            response,
            name="wallet balance",
        )

        items = (
            response
            .get("result", {})
            .get("list", [])
        )

        if len(items) != 1:
            raise RuntimeError(
                "Expected exactly one "
                "UNIFIED account wallet "
                f"record, got {len(items)}."
            )

        wallet = items[0]

        if (
            wallet.get("accountType")
            != "UNIFIED"
        ):
            raise RuntimeError(
                "Unexpected Bybit "
                "account type."
            )

        return wallet

    def _get_positions(
        self,
        symbol: str,
    ) -> list[dict]:

        response = (
            self.session
            .get_positions(
                category="linear",
                symbol=symbol,
            )
        )

        self._validate_response(
            response,
            name="position info",
        )

        return (
            response
            .get("result", {})
            .get("list", [])
        )

    def _parse_position(
        self,
        item: dict,
        expected_symbol: str,
    ) -> DemoPositionSnapshot:

        symbol = item.get("symbol")

        if symbol != expected_symbol:
            raise RuntimeError(
                "Bybit returned an "
                "unexpected position symbol."
            )

        size = self._decimal(
            item.get("size", "0"),
            field_name="position.size",
        )

        raw_side = item.get(
            "side",
            "",
        )

        if size > 0:
            if raw_side not in (
                "Buy",
                "Sell",
            ):
                raise RuntimeError(
                    "Open position has an "
                    "invalid side."
                )

            side: str | None = raw_side

        else:
            side = None

        avg_price = self._optional_decimal(
            item.get("avgPrice")
        )

        leverage = self._optional_decimal(
            item.get("leverage")
        )

        # Empty / flat positions returned by
        # Bybit may contain empty PnL fields.
        #
        # For a zero-size position these are
        # safely normalised to zero.
        #
        # For a real open position, missing
        # PnL remains a fail-closed condition.

        if size == 0:
            unrealised_pnl = (
                self._decimal_or_zero(
                    item.get(
                        "unrealisedPnl"
                    )
                )
            )

            current_realised_pnl = (
                self._decimal_or_zero(
                    item.get(
                        "curRealisedPnl"
                    )
                )
            )

        else:
            unrealised_pnl = self._decimal(
                item.get(
                    "unrealisedPnl"
                ),
                field_name=(
                    "position.unrealisedPnl"
                ),
            )

            current_realised_pnl = (
                self._decimal(
                    item.get(
                        "curRealisedPnl"
                    ),
                    field_name=(
                        "position."
                        "curRealisedPnl"
                    ),
                )
            )

        return DemoPositionSnapshot(
            symbol=symbol,
            side=side,
            size=size,
            avg_price=avg_price,
            leverage=leverage,
            unrealised_pnl=(
                unrealised_pnl
            ),
            current_realised_pnl=(
                current_realised_pnl
            ),
        )

    @staticmethod
    def _validate_response(
        response: dict,
        name: str,
    ) -> None:
        if response.get("retCode") != 0:
            raise RuntimeError(
                f"Bybit {name} request "
                f"failed: {response}"
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
                f"Invalid decimal value "
                f"for '{field_name}': "
                f"{value!r}"
            ) from exc
        
    @staticmethod
    def _decimal_or_zero(
        value,
    ) -> Decimal:
        if value in (
            None,
            "",
        ):
            return Decimal("0")

        try:
            return Decimal(
                str(value)
            )

        except Exception as exc:
            raise RuntimeError(
                "Invalid decimal value: "
                f"{value!r}"
            ) from exc

    @staticmethod
    def _optional_decimal(
        value,
    ) -> Decimal | None:
        if value in (
            None,
            "",
        ):
            return None

        try:
            return Decimal(
                str(value)
            )

        except Exception as exc:
            raise RuntimeError(
                "Invalid optional "
                "decimal value: "
                f"{value!r}"
            ) from exc