from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock


@dataclass(frozen=True, slots=True)
class PublicTrade:
    symbol: str
    trade_id: str
    side: str

    price: Decimal
    quantity: Decimal

    exchange_event_ts_ms: int
    system_ts_ms: int
    sequence: int

    local_receive_ts_utc: datetime


class TradeFlow:
    def __init__(
        self,
        symbol: str,
        window_seconds: int = 60,
    ):
        self.symbol = symbol
        self.window_seconds = window_seconds

        self._trades: deque[PublicTrade] = deque()
        self._trade_ids: set[str] = set()

        self.message_count = 0
        self.total_trade_count = 0
        self.duplicate_count = 0

        self._latest_event_ts_ms: int | None = None
        self._lock = Lock()

    def process_message(self, message: dict) -> None:
        data = message.get("data", [])

        if not isinstance(data, list):
            return

        system_ts_ms = int(message.get("ts", 0))
        local_receive_ts = datetime.now(timezone.utc)

        with self._lock:
            self.message_count += 1

            for item in data:
                if item.get("s") != self.symbol:
                    continue

                trade_id = item.get("i")

                if not trade_id:
                    continue

                # Trade ID is the primary duplicate key.
                if trade_id in self._trade_ids:
                    self.duplicate_count += 1
                    continue

                trade = PublicTrade(
                    symbol=self.symbol,
                    trade_id=trade_id,
                    side=item["S"],
                    price=Decimal(item["p"]),
                    quantity=Decimal(item["v"]),
                    exchange_event_ts_ms=int(item["T"]),
                    system_ts_ms=system_ts_ms,
                    sequence=int(item["seq"]),
                    local_receive_ts_utc=local_receive_ts,
                )

                self._trades.append(trade)
                self._trade_ids.add(trade_id)

                self.total_trade_count += 1

                if (
                    self._latest_event_ts_ms is None
                    or trade.exchange_event_ts_ms
                    > self._latest_event_ts_ms
                ):
                    self._latest_event_ts_ms = (
                        trade.exchange_event_ts_ms
                    )

            self._remove_expired_trades()

    def _remove_expired_trades(self) -> None:
        if self._latest_event_ts_ms is None:
            return

        cutoff_ms = (
            self._latest_event_ts_ms
            - self.window_seconds * 1000
        )

        while (
            self._trades
            and self._trades[0].exchange_event_ts_ms < cutoff_ms
        ):
            expired = self._trades.popleft()
            self._trade_ids.discard(expired.trade_id)

    def get_recent_trades(self) -> list[PublicTrade]:
        with self._lock:
            return list(self._trades)

    def latest_trade(self) -> PublicTrade | None:
        with self._lock:
            if not self._trades:
                return None

            return self._trades[-1]

    def aggressive_buy_volume(self) -> Decimal:
        with self._lock:
            return sum(
                (
                    trade.quantity
                    for trade in self._trades
                    if trade.side == "Buy"
                ),
                Decimal("0"),
            )

    def aggressive_sell_volume(self) -> Decimal:
        with self._lock:
            return sum(
                (
                    trade.quantity
                    for trade in self._trades
                    if trade.side == "Sell"
                ),
                Decimal("0"),
            )

    def signed_volume_imbalance(self) -> Decimal:
        buy_volume = self.aggressive_buy_volume()
        sell_volume = self.aggressive_sell_volume()

        total = buy_volume + sell_volume

        if total == 0:
            return Decimal("0")

        return (
            buy_volume - sell_volume
        ) / total

    def recent_trade_count(self) -> int:
        with self._lock:
            return len(self._trades)

    def is_ready(self) -> bool:
        with self._lock:
            return len(self._trades) > 0