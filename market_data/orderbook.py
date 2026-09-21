from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock


class OrderBook:
    def __init__(self, symbol: str, depth: int = 50):
        self.symbol = symbol
        self.depth = depth

        self._bids: dict[Decimal, Decimal] = {}
        self._asks: dict[Decimal, Decimal] = {}

        self.update_id: int | None = None
        self.sequence: int | None = None

        self.exchange_ts_ms: int | None = None
        self.matching_engine_ts_ms: int | None = None

        self.local_receive_ts_utc: datetime | None = None

        self.has_snapshot = False
        self.message_count = 0

        self._lock = Lock()

    @staticmethod
    def _apply_levels(
        book: dict[Decimal, Decimal],
        levels: list[list[str]],
    ) -> None:
        for price_raw, size_raw in levels:
            price = Decimal(price_raw)
            size = Decimal(size_raw)

            if size == 0:
                book.pop(price, None)
            else:
                book[price] = size

    def process_message(self, message: dict) -> None:
        message_type = message.get("type")
        data = message.get("data", {})

        if data.get("s") != self.symbol:
            return

        with self._lock:
            self.local_receive_ts_utc = datetime.now(timezone.utc)

            self.exchange_ts_ms = message.get("ts")
            self.matching_engine_ts_ms = message.get("cts")

            self.update_id = data.get("u")
            self.sequence = data.get("seq")

            bids = data.get("b", [])
            asks = data.get("a", [])

            is_snapshot = (
                message_type == "snapshot"
                or self.update_id == 1
            )

            if is_snapshot:
                self._bids.clear()
                self._asks.clear()

                self._apply_levels(self._bids, bids)
                self._apply_levels(self._asks, asks)

                self.has_snapshot = True

            elif message_type == "delta":
                if not self.has_snapshot:
                    return

                self._apply_levels(self._bids, bids)
                self._apply_levels(self._asks, asks)

            self.message_count += 1

    def get_bids(self) -> list[tuple[Decimal, Decimal]]:
        with self._lock:
            return sorted(
                self._bids.items(),
                key=lambda x: x[0],
                reverse=True,
            )[: self.depth]

    def get_asks(self) -> list[tuple[Decimal, Decimal]]:
        with self._lock:
            return sorted(
                self._asks.items(),
                key=lambda x: x[0],
            )[: self.depth]

    def best_bid(self) -> tuple[Decimal, Decimal] | None:
        bids = self.get_bids()
        return bids[0] if bids else None

    def best_ask(self) -> tuple[Decimal, Decimal] | None:
        asks = self.get_asks()
        return asks[0] if asks else None

    def spread(self) -> Decimal | None:
        bid = self.best_bid()
        ask = self.best_ask()

        if bid is None or ask is None:
            return None

        return ask[0] - bid[0]

    def is_ready(self) -> bool:
        return (
            self.has_snapshot
            and self.best_bid() is not None
            and self.best_ask() is not None
        )