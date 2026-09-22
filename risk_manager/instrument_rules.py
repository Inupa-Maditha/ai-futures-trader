from __future__ import annotations

from decimal import (
    Decimal,
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_UP,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from pybit.unified_trading import HTTP


class InstrumentRules(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    symbol: str
    status: str
    contract_type: str

    tick_size: Decimal = Field(gt=0)

    min_price: Decimal = Field(gt=0)
    max_price: Decimal = Field(gt=0)

    qty_step: Decimal = Field(gt=0)

    min_order_qty: Decimal = Field(gt=0)
    max_order_qty: Decimal = Field(gt=0)
    max_market_order_qty: Decimal = Field(gt=0)

    min_notional_value: Decimal = Field(gt=0)

    min_leverage: Decimal = Field(gt=0)
    max_leverage: Decimal = Field(gt=0)
    leverage_step: Decimal = Field(gt=0)


class BybitInstrumentRulesClient:
    def __init__(
        self,
        session=None,
    ):
        # V1 uses mainnet public market data.
        #
        # No API key is required for this
        # public instrument-info endpoint.
        self.session = (
            session
            if session is not None
            else HTTP(testnet=False)
        )

    def get_linear_rules(
        self,
        symbol: str,
    ) -> InstrumentRules:

        response = (
            self.session
            .get_instruments_info(
                category="linear",
                symbol=symbol,
            )
        )

        if response.get("retCode") != 0:
            raise RuntimeError(
                "Bybit instrument-info request "
                f"failed: {response}"
            )

        result = response.get(
            "result",
            {}
        )

        instruments = result.get(
            "list",
            [],
        )

        if len(instruments) != 1:
            raise RuntimeError(
                "Expected exactly one "
                f"instrument for {symbol}, "
                f"got {len(instruments)}."
            )

        instrument = instruments[0]

        if (
            instrument.get("symbol")
            != symbol
        ):
            raise RuntimeError(
                "Bybit returned an unexpected "
                "instrument symbol."
            )

        if (
            instrument.get("status")
            != "Trading"
        ):
            raise RuntimeError(
                f"{symbol} is not currently "
                "in Trading status."
            )

        if (
            instrument.get("contractType")
            != "LinearPerpetual"
        ):
            raise RuntimeError(
                f"{symbol} is not a "
                "LinearPerpetual contract."
            )

        price_filter = instrument[
            "priceFilter"
        ]

        lot_filter = instrument[
            "lotSizeFilter"
        ]

        leverage_filter = instrument[
            "leverageFilter"
        ]

        return InstrumentRules(
            symbol=instrument["symbol"],
            status=instrument["status"],
            contract_type=(
                instrument["contractType"]
            ),

            tick_size=Decimal(
                price_filter["tickSize"]
            ),

            min_price=Decimal(
                price_filter["minPrice"]
            ),

            max_price=Decimal(
                price_filter["maxPrice"]
            ),

            qty_step=Decimal(
                lot_filter["qtyStep"]
            ),

            min_order_qty=Decimal(
                lot_filter["minOrderQty"]
            ),

            max_order_qty=Decimal(
                lot_filter["maxOrderQty"]
            ),

            max_market_order_qty=Decimal(
                lot_filter["maxMktOrderQty"]
            ),

            min_notional_value=Decimal(
                lot_filter[
                    "minNotionalValue"
                ]
            ),

            min_leverage=Decimal(
                leverage_filter[
                    "minLeverage"
                ]
            ),

            max_leverage=Decimal(
                leverage_filter[
                    "maxLeverage"
                ]
            ),

            leverage_step=Decimal(
                leverage_filter[
                    "leverageStep"
                ]
            ),
        )


def floor_to_step(
    value: Decimal,
    step: Decimal,
) -> Decimal:
    _validate_step(
        value=value,
        step=step,
    )

    units = (
        value / step
    ).to_integral_value(
        rounding=ROUND_FLOOR
    )

    return units * step


def ceil_to_step(
    value: Decimal,
    step: Decimal,
) -> Decimal:
    _validate_step(
        value=value,
        step=step,
    )

    units = (
        value / step
    ).to_integral_value(
        rounding=ROUND_CEILING
    )

    return units * step


def nearest_to_step(
    value: Decimal,
    step: Decimal,
) -> Decimal:
    _validate_step(
        value=value,
        step=step,
    )

    units = (
        value / step
    ).to_integral_value(
        rounding=ROUND_HALF_UP
    )

    return units * step


def _validate_step(
    value: Decimal,
    step: Decimal,
) -> None:
    if value < 0:
        raise ValueError(
            "Value must not be negative."
        )

    if step <= 0:
        raise ValueError(
            "Step must be greater "
            "than zero."
        )