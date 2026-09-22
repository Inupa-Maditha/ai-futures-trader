from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from typing import Any

from evaluation.outcome_recorder import (
    TradeOutcomeRecorder,
)
from evaluation.schema import (
    TradeExitReason,
    TradeOutcome,
    TradeSide,
)

from journal.schema import (
    JournalEventType,
)
from journal.store import (
    JournalStore,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ExecutionCandidate:
    run_id: str
    symbol: str
    order_link_id: str
    side: str
    quantity: Decimal
    initial_risk_amount: Decimal


@dataclass(
    frozen=True,
    slots=True,
)
class OutcomeImportResult:
    scanned_closed_records: int
    imported: int
    already_recorded: int
    unmatched: int
    unsupported: int


class BybitDemoOutcomeImporter:
    PAGE_LIMIT = 100
    MAX_PAGES = 20

    def __init__(
        self,
        *,
        session,
        store: JournalStore,
        recorder: TradeOutcomeRecorder,
    ):
        self.session = session
        self.store = store
        self.recorder = recorder

    def import_recent(
        self,
        *,
        symbol: str,
        now_utc: datetime | None = None,
        lookback_days: int = 7,
    ) -> OutcomeImportResult:

        if not 1 <= lookback_days <= 7:
            raise ValueError(
                "lookback_days must be "
                "between 1 and 7."
            )

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

        start = (
            now
            - timedelta(
                days=lookback_days
            )
        )

        candidates = (
            self._load_execution_candidates(
                symbol=symbol
            )
        )

        already_recorded = (
            self._load_recorded_trade_ids()
        )

        closed_records = (
            self._load_closed_pnl(
                symbol=symbol,
                start_utc=start,
                end_utc=now,
            )
        )

        imported = 0
        duplicate_count = 0
        unmatched = 0
        unsupported = 0

        for record in closed_records:
            close_order_id = self._required_string(
                record,
                "orderId",
            )

            trade_id = (
                f"bybit:{close_order_id}"
            )

            if trade_id in already_recorded:
                duplicate_count += 1
                continue

            if (
                record.get("execType")
                != "Trade"
            ):
                unsupported += 1
                continue

            close_order = (
                self._get_close_order(
                    symbol=symbol,
                    order_id=close_order_id,
                )
            )

            parent_order_link_id = (
                close_order.get(
                    "parentOrderLinkId"
                )
                or ""
            )

            if not parent_order_link_id:
                # Do not guess which system
                # execution this close belongs to.
                unmatched += 1
                continue

            candidate = candidates.get(
                parent_order_link_id
            )

            if candidate is None:
                unmatched += 1
                continue

            closed_size = self._decimal(
                record.get(
                    "closedSize"
                ),
                field_name="closedSize",
            )

            # V1 metrics support only one complete
            # system position per trade.
            #
            # Partial closes require proportional
            # risk allocation and are intentionally
            # not guessed here.
            if (
                closed_size
                != candidate.quantity
            ):
                unsupported += 1
                continue

            avg_entry_price = self._decimal(
                record.get(
                    "avgEntryPrice"
                ),
                field_name="avgEntryPrice",
            )

            avg_exit_price = self._decimal(
                record.get(
                    "avgExitPrice"
                ),
                field_name="avgExitPrice",
            )

            realized_pnl = self._decimal(
                record.get(
                    "closedPnl"
                ),
                field_name="closedPnl",
            )

            if (
                avg_entry_price <= 0
                or avg_exit_price <= 0
                or closed_size <= 0
            ):
                raise RuntimeError(
                    "Closed PnL record contains "
                    "invalid trade values."
                )

            opened_at = (
                self._get_entry_open_time(
                    order_link_id=(
                        parent_order_link_id
                    ),
                    symbol=symbol,
                )
            )

            closed_at = self._millis_to_datetime(
                self._integer(
                    record.get(
                        "updatedTime"
                    ),
                    field_name="updatedTime",
                )
            )

            if opened_at >= closed_at:
                raise RuntimeError(
                    "Entry execution time is not "
                    "earlier than close time."
                )

            outcome = TradeOutcome(
                trade_id=trade_id,

                run_id=(
                    candidate.run_id
                ),

                symbol=symbol,

                side=(
                    TradeSide.LONG
                    if candidate.side
                    == "Buy"
                    else TradeSide.SHORT
                ),

                opened_at_utc=opened_at,

                closed_at_utc=closed_at,

                entry_price=(
                    avg_entry_price
                ),

                exit_price=(
                    avg_exit_price
                ),

                quantity=(
                    closed_size
                ),

                initial_risk_amount=(
                    candidate
                    .initial_risk_amount
                ),

                realized_pnl=(
                    realized_pnl
                ),

                exit_reason=(
                    self._map_exit_reason(
                        close_order
                    )
                ),
            )

            self.recorder.record(
                outcome
            )

            already_recorded.add(
                trade_id
            )

            imported += 1

        return OutcomeImportResult(
            scanned_closed_records=(
                len(closed_records)
            ),

            imported=imported,

            already_recorded=(
                duplicate_count
            ),

            unmatched=unmatched,

            unsupported=unsupported,
        )

    def _load_execution_candidates(
        self,
        *,
        symbol: str,
    ) -> dict[
        str,
        ExecutionCandidate,
    ]:

        execution_events = (
            self.store.read_events(
                event_type=(
                    JournalEventType
                    .EXECUTION_RESULT
                )
            )
        )

        candidates: dict[
            str,
            ExecutionCandidate,
        ] = {}

        for execution_event in execution_events:
            if (
                execution_event.symbol
                != symbol
            ):
                continue

            request = (
                execution_event.payload.get(
                    "request"
                )
            )

            if not isinstance(
                request,
                dict,
            ):
                raise RuntimeError(
                    "EXECUTION_RESULT event "
                    "is missing request payload."
                )

            order_link_id = (
                request.get(
                    "order_link_id"
                )
            )

            side = request.get(
                "side"
            )

            quantity = request.get(
                "quantity"
            )

            if (
                not isinstance(
                    order_link_id,
                    str,
                )
                or not order_link_id
            ):
                raise RuntimeError(
                    "Execution journal is missing "
                    "order_link_id."
                )

            if side not in (
                "Buy",
                "Sell",
            ):
                raise RuntimeError(
                    "Execution journal contains "
                    "invalid side."
                )

            quantity_decimal = (
                self._decimal(
                    quantity,
                    field_name=(
                        "execution quantity"
                    ),
                )
            )

            risk_events = (
                self.store.read_events(
                    run_id=(
                        execution_event.run_id
                    ),
                    event_type=(
                        JournalEventType
                        .RISK_RESULT
                    ),
                )
            )

            if len(risk_events) != 1:
                raise RuntimeError(
                    "Expected exactly one "
                    "RISK_RESULT for an "
                    "executed journal run."
                )

            risk_result = (
                risk_events[0]
                .payload.get(
                    "risk_result"
                )
            )

            if not isinstance(
                risk_result,
                dict,
            ):
                raise RuntimeError(
                    "RISK_RESULT payload is "
                    "missing risk_result."
                )

            plan = risk_result.get(
                "plan"
            )

            if not isinstance(
                plan,
                dict,
            ):
                raise RuntimeError(
                    "RISK_RESULT payload is "
                    "missing approved plan."
                )

            actual_risk = self._decimal(
                plan.get(
                    "actual_risk_amount"
                ),
                field_name=(
                    "actual_risk_amount"
                ),
            )

            if actual_risk <= 0:
                raise RuntimeError(
                    "Recorded actual risk "
                    "must be positive."
                )

            if order_link_id in candidates:
                raise RuntimeError(
                    "Duplicate execution "
                    "orderLinkId found in "
                    "journal."
                )

            candidates[
                order_link_id
            ] = ExecutionCandidate(
                run_id=(
                    execution_event.run_id
                ),

                symbol=symbol,

                order_link_id=(
                    order_link_id
                ),

                side=side,

                quantity=(
                    quantity_decimal
                ),

                initial_risk_amount=(
                    actual_risk
                ),
            )

        return candidates

    def _load_recorded_trade_ids(
        self,
    ) -> set[str]:

        events = self.store.read_events(
            event_type=(
                JournalEventType
                .TRADE_OUTCOME
            )
        )

        trade_ids: set[str] = set()

        for event in events:
            outcome = event.payload.get(
                "outcome"
            )

            if not isinstance(
                outcome,
                dict,
            ):
                raise RuntimeError(
                    "Invalid TRADE_OUTCOME "
                    "journal payload."
                )

            trade_id = outcome.get(
                "trade_id"
            )

            if (
                not isinstance(
                    trade_id,
                    str,
                )
                or not trade_id
            ):
                raise RuntimeError(
                    "TRADE_OUTCOME is missing "
                    "trade_id."
                )

            if trade_id in trade_ids:
                raise RuntimeError(
                    "Duplicate recorded "
                    "trade_id found."
                )

            trade_ids.add(
                trade_id
            )

        return trade_ids

    def _load_closed_pnl(
        self,
        *,
        symbol: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> tuple[dict, ...]:

        start_ms = int(
            start_utc.timestamp()
            * 1000
        )

        end_ms = int(
            end_utc.timestamp()
            * 1000
        )

        records: list[dict] = []

        cursor: str | None = None
        seen_cursors: set[str] = set()

        for _ in range(
            self.MAX_PAGES
        ):
            params: dict[
                str,
                Any,
            ] = {
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
                response,
                operation="closed PnL",
            )

            result = response.get(
                "result",
                {},
            )

            page_records = result.get(
                "list",
                [],
            )

            for record in page_records:
                if (
                    record.get("symbol")
                    != symbol
                ):
                    raise RuntimeError(
                        "Closed PnL query "
                        "returned unexpected "
                        "symbol."
                    )

                records.append(
                    record
                )

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
                    "Closed PnL pagination "
                    "cursor repeated."
                )

            seen_cursors.add(
                next_cursor
            )

            cursor = next_cursor

        else:
            raise RuntimeError(
                "Closed PnL pagination "
                "exceeded safety limit."
            )

        return tuple(records)

    def _get_close_order(
        self,
        *,
        symbol: str,
        order_id: str,
    ) -> dict:

        response = (
            self.session
            .get_order_history(
                category="linear",
                symbol=symbol,
                orderId=order_id,
                limit=1,
            )
        )

        self._validate_response(
            response,
            operation=(
                "closing order history"
            ),
        )

        records = (
            response
            .get("result", {})
            .get("list", [])
        )

        if len(records) != 1:
            raise RuntimeError(
                "Expected exactly one "
                "closing order history "
                "record."
            )

        record = records[0]

        if (
            record.get("orderId")
            != order_id
        ):
            raise RuntimeError(
                "Closing order history "
                "returned wrong orderId."
            )

        if (
            record.get("symbol")
            != symbol
        ):
            raise RuntimeError(
                "Closing order history "
                "returned wrong symbol."
            )

        return record

    def _get_entry_open_time(
        self,
        *,
        order_link_id: str,
        symbol: str,
    ) -> datetime:

        response = (
            self.session
            .get_executions(
                category="linear",
                symbol=symbol,
                orderLinkId=(
                    order_link_id
                ),
                limit=100,
            )
        )

        self._validate_response(
            response,
            operation=(
                "entry execution history"
            ),
        )

        records = (
            response
            .get("result", {})
            .get("list", [])
        )

        execution_times: list[int] = []

        for record in records:
            if (
                record.get(
                    "orderLinkId"
                )
                != order_link_id
            ):
                raise RuntimeError(
                    "Entry execution query "
                    "returned unexpected "
                    "orderLinkId."
                )

            if (
                record.get("symbol")
                != symbol
            ):
                raise RuntimeError(
                    "Entry execution query "
                    "returned unexpected "
                    "symbol."
                )

            if (
                record.get("execType")
                != "Trade"
            ):
                continue

            exec_qty = self._decimal(
                record.get(
                    "execQty"
                ),
                field_name="execQty",
            )

            if exec_qty <= 0:
                continue

            execution_times.append(
                self._integer(
                    record.get(
                        "execTime"
                    ),
                    field_name="execTime",
                )
            )

        if not execution_times:
            raise RuntimeError(
                "No entry trade execution "
                "was found for the system "
                "orderLinkId."
            )

        return self._millis_to_datetime(
            min(
                execution_times
            )
        )

    @staticmethod
    def _map_exit_reason(
        closing_order: dict,
    ) -> TradeExitReason:

        stop_type = (
            closing_order.get(
                "stopOrderType"
            )
            or ""
        )

        create_type = (
            closing_order.get(
                "createType"
            )
            or ""
        )

        if stop_type in (
            "TakeProfit",
            "PartialTakeProfit",
        ):
            return (
                TradeExitReason
                .TAKE_PROFIT
            )

        if stop_type in (
            "StopLoss",
            "PartialStopLoss",
        ):
            return (
                TradeExitReason
                .STOP_LOSS
            )

        if create_type in (
            "CreateByTakeProfit",
            "CreateByPartialTakeProfit",
        ):
            return (
                TradeExitReason
                .TAKE_PROFIT
            )

        if create_type in (
            "CreateByStopLoss",
            "CreateByPartialStopLoss",
        ):
            return (
                TradeExitReason
                .STOP_LOSS
            )

        return TradeExitReason.OTHER

    @staticmethod
    def _required_string(
        record: dict,
        field_name: str,
    ) -> str:

        value = record.get(
            field_name
        )

        if (
            not isinstance(
                value,
                str,
            )
            or not value
        ):
            raise RuntimeError(
                f"Missing or invalid "
                f"{field_name}."
            )

        return value

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
                f"Missing {field_name}."
            )

        try:
            return Decimal(
                str(value)
            )

        except Exception as exc:
            raise RuntimeError(
                f"Invalid {field_name}."
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
                f"Missing {field_name}."
            )

        try:
            return int(
                value
            )

        except Exception as exc:
            raise RuntimeError(
                f"Invalid {field_name}."
            ) from exc

    @staticmethod
    def _millis_to_datetime(
        value: int,
    ) -> datetime:

        return datetime.fromtimestamp(
            value / 1000,
            tz=timezone.utc,
        )

    @staticmethod
    def _validate_response(
        response: dict,
        *,
        operation: str,
    ) -> None:

        if (
            response.get(
                "retCode"
            )
            != 0
        ):
            raise RuntimeError(
                f"Bybit {operation} "
                f"request failed: "
                f"{response}"
            )