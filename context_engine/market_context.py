from __future__ import annotations

import json

from dataclasses import (
    asdict,
    dataclass,
)
from datetime import datetime, timezone

from config.settings import SYMBOL

from context_engine.technical_snapshot import (
    MultiTimeframeAnalysisSnapshot,
    MultiTimeframeAnalyzer,
)

from market_data.runner import (
    MarketDataRunner,
)


@dataclass(frozen=True, slots=True)
class OrderBookContext:
    best_bid: float
    best_ask: float

    mid_price: float
    spread: float
    spread_bps: float

    depth_levels: int

    bid_volume: float
    ask_volume: float

    depth_imbalance: float

    update_id: int | None
    sequence: int | None

    exchange_ts_ms: int | None
    matching_engine_ts_ms: int | None


@dataclass(frozen=True, slots=True)
class TradeFlowContext:
    window_seconds: int

    aggressive_buy_volume: float
    aggressive_sell_volume: float

    signed_volume_imbalance: float

    trade_count: int

    latest_trade_price: float | None
    latest_trade_side: str | None
    latest_trade_ts_ms: int | None


@dataclass(frozen=True, slots=True)
class LiquidationContext:
    window_seconds: int

    long_liquidation_volume: float
    short_liquidation_volume: float
    total_liquidation_volume: float

    event_count: int

    latest_event_side: str | None
    latest_event_price: float | None
    latest_event_ts_ms: int | None


@dataclass(frozen=True, slots=True)
class DerivativesContext:
    open_interest: float
    previous_open_interest: float | None

    oi_change_absolute: float | None
    oi_change_percent: float | None

    oi_observation_ts_ms: int

    current_funding_rate: float
    next_funding_ts_ms: int
    funding_interval_minutes: int

    long_account_ratio: float
    short_account_ratio: float

    long_short_account_ratio: float | None

    positioning_observation_ts_ms: int


@dataclass(frozen=True, slots=True)
class DataHealthContext:
    all_required_healthy: bool
    statuses: dict[str, str]


@dataclass(frozen=True, slots=True)
class MarketContextSnapshot:
    schema_version: str

    symbol: str
    generated_at_utc: datetime

    technical: MultiTimeframeAnalysisSnapshot

    orderbook: OrderBookContext
    trade_flow: TradeFlowContext
    liquidations: LiquidationContext
    derivatives: DerivativesContext
    health: DataHealthContext

    def to_dict(self) -> dict:
        return {
            "schema_version": (
                self.schema_version
            ),
            "symbol": self.symbol,
            "generated_at_utc": (
                self.generated_at_utc.isoformat()
            ),
            "technical": (
                self.technical.to_dict()
            ),
            "orderbook": asdict(
                self.orderbook
            ),
            "trade_flow": asdict(
                self.trade_flow
            ),
            "liquidations": asdict(
                self.liquidations
            ),
            "derivatives": asdict(
                self.derivatives
            ),
            "health": asdict(
                self.health
            ),
        }

    def to_json(
        self,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=False,
        )


class MarketContextBuilder:
    def __init__(
        self,
        runner: MarketDataRunner,
        orderbook_depth_levels: int = 10,
    ):
        if orderbook_depth_levels < 1:
            raise ValueError(
                "orderbook_depth_levels "
                "must be at least 1."
            )

        self.runner = runner

        self.orderbook_depth_levels = (
            orderbook_depth_levels
        )

        self.technical_analyzer = (
            MultiTimeframeAnalyzer(
                candle_service=(
                    runner.candle_service
                )
            )
        )

    def build(
        self,
        require_healthy: bool = True,
    ) -> MarketContextSnapshot:

        if (
            require_healthy
            and not self.runner.market_data_ready()
        ):
            raise RuntimeError(
                "Market context build rejected: "
                "required market data is unhealthy."
            )

        technical = (
            self.technical_analyzer.analyze()
        )

        orderbook = (
            self._build_orderbook_context()
        )

        trade_flow = (
            self._build_trade_flow_context()
        )

        liquidations = (
            self._build_liquidation_context()
        )

        derivatives = (
            self._build_derivatives_context()
        )

        health = self._build_health_context()

        # Fail closed if health changed while
        # context construction was in progress.
        if (
            require_healthy
            and not health.all_required_healthy
        ):
            raise RuntimeError(
                "Market context build rejected: "
                "market data became unhealthy."
            )

        return MarketContextSnapshot(
            schema_version="1.0",
            symbol=SYMBOL,
            generated_at_utc=datetime.now(
                timezone.utc
            ),
            technical=technical,
            orderbook=orderbook,
            trade_flow=trade_flow,
            liquidations=liquidations,
            derivatives=derivatives,
            health=health,
        )

    def _build_orderbook_context(
        self,
    ) -> OrderBookContext:

        best_bid = (
            self.runner.orderbook.best_bid()
        )

        best_ask = (
            self.runner.orderbook.best_ask()
        )

        if (
            best_bid is None
            or best_ask is None
        ):
            raise RuntimeError(
                "Order book is not ready."
            )

        bids = (
            self.runner.orderbook
            .get_bids()[
                :self.orderbook_depth_levels
            ]
        )

        asks = (
            self.runner.orderbook
            .get_asks()[
                :self.orderbook_depth_levels
            ]
        )

        bid_decimal = best_bid[0]
        ask_decimal = best_ask[0]

        spread_decimal = (
            ask_decimal - bid_decimal
        )

        mid_decimal = (
            bid_decimal + ask_decimal
        ) / 2

        bid_price = float(
            bid_decimal
        )

        ask_price = float(
            ask_decimal
        )

        spread = float(
            spread_decimal
        )

        mid_price = float(
            mid_decimal
        )

        if mid_price == 0:
            spread_bps = 0.0
        else:
            spread_bps = (
                spread
                / mid_price
                * 10_000
            )

        bid_volume = sum(
            float(quantity)
            for _, quantity in bids
        )

        ask_volume = sum(
            float(quantity)
            for _, quantity in asks
        )

        total_volume = (
            bid_volume + ask_volume
        )

        if total_volume == 0:
            depth_imbalance = 0.0
        else:
            depth_imbalance = (
                bid_volume - ask_volume
            ) / total_volume

        return OrderBookContext(
            best_bid=bid_price,
            best_ask=ask_price,
            mid_price=mid_price,
            spread=spread,
            spread_bps=spread_bps,
            depth_levels=(
                self.orderbook_depth_levels
            ),
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            depth_imbalance=(
                depth_imbalance
            ),
            update_id=(
                self.runner.orderbook.update_id
            ),
            sequence=(
                self.runner.orderbook.sequence
            ),
            exchange_ts_ms=(
                self.runner.orderbook
                .exchange_ts_ms
            ),
            matching_engine_ts_ms=(
                self.runner.orderbook
                .matching_engine_ts_ms
            ),
        )

    def _build_trade_flow_context(
        self,
    ) -> TradeFlowContext:

        latest = (
            self.runner.trades.latest_trade()
        )

        return TradeFlowContext(
            window_seconds=(
                self.runner.trades
                .window_seconds
            ),
            aggressive_buy_volume=float(
                self.runner.trades
                .aggressive_buy_volume()
            ),
            aggressive_sell_volume=float(
                self.runner.trades
                .aggressive_sell_volume()
            ),
            signed_volume_imbalance=float(
                self.runner.trades
                .signed_volume_imbalance()
            ),
            trade_count=(
                self.runner.trades
                .recent_trade_count()
            ),
            latest_trade_price=(
                float(latest.price)
                if latest is not None
                else None
            ),
            latest_trade_side=(
                latest.side
                if latest is not None
                else None
            ),
            latest_trade_ts_ms=(
                latest.exchange_event_ts_ms
                if latest is not None
                else None
            ),
        )

    def _build_liquidation_context(
        self,
    ) -> LiquidationContext:

        latest = (
            self.runner.liquidations
            .latest_event()
        )

        long_volume = float(
            self.runner.liquidations
            .long_liquidation_volume()
        )

        short_volume = float(
            self.runner.liquidations
            .short_liquidation_volume()
        )

        return LiquidationContext(
            window_seconds=(
                self.runner.liquidations
                .window_seconds
            ),
            long_liquidation_volume=(
                long_volume
            ),
            short_liquidation_volume=(
                short_volume
            ),
            total_liquidation_volume=(
                long_volume
                + short_volume
            ),
            event_count=(
                self.runner.liquidations
                .recent_event_count()
            ),
            latest_event_side=(
                latest.position_side
                if latest is not None
                else None
            ),
            latest_event_price=(
                float(
                    latest.bankruptcy_price
                )
                if latest is not None
                else None
            ),
            latest_event_ts_ms=(
                latest.exchange_event_ts_ms
                if latest is not None
                else None
            ),
        )

    def _build_derivatives_context(
        self,
    ) -> DerivativesContext:

        (
            oi,
            funding,
            positioning,
        ) = (
            self.runner
            .get_latest_derivatives()
        )

        return DerivativesContext(
            open_interest=float(
                oi.current
            ),
            previous_open_interest=(
                float(oi.previous)
                if oi.previous is not None
                else None
            ),
            oi_change_absolute=(
                float(
                    oi.change_absolute
                )
                if oi.change_absolute
                is not None
                else None
            ),
            oi_change_percent=(
                float(
                    oi.change_percent
                )
                if oi.change_percent
                is not None
                else None
            ),
            oi_observation_ts_ms=(
                oi.observation_ts_ms
            ),
            current_funding_rate=float(
                funding.current_funding_rate
            ),
            next_funding_ts_ms=(
                funding.next_funding_ts_ms
            ),
            funding_interval_minutes=(
                funding
                .funding_interval_minutes
            ),
            long_account_ratio=float(
                positioning
                .account_holder_long_ratio
            ),
            short_account_ratio=float(
                positioning
                .account_holder_short_ratio
            ),
            long_short_account_ratio=(
                float(
                    positioning
                    .long_short_account_ratio
                )
                if positioning
                .long_short_account_ratio
                is not None
                else None
            ),
            positioning_observation_ts_ms=(
                positioning
                .observation_ts_ms
            ),
        )

    def _build_health_context(
        self,
    ) -> DataHealthContext:

        return DataHealthContext(
            all_required_healthy=(
                self.runner.market_data_ready()
            ),
            statuses=(
                self.runner
                .health_monitor
                .summary()
            ),
        )