from __future__ import annotations

from dataclasses import (
    asdict,
    is_dataclass,
)
from datetime import (
    date,
    datetime,
)
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from journal.schema import (
    JournalEvent,
    JournalEventType,
)
from journal.store import (
    JournalStore,
)


def to_jsonable(
    value: Any,
):
    """
    Convert trading-domain objects into
    deterministic JSON-compatible values.

    Decimal values become strings so exact
    financial values are preserved.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(
        value,
        Decimal,
    ):
        return str(value)

    if isinstance(
        value,
        Enum,
    ):
        return to_jsonable(
            value.value
        )

    if isinstance(
        value,
        datetime,
    ):
        return value.isoformat()

    if isinstance(
        value,
        date,
    ):
        return value.isoformat()

    if isinstance(
        value,
        BaseModel,
    ):
        return to_jsonable(
            value.model_dump(
                mode="python"
            )
        )

    if is_dataclass(value):
        return to_jsonable(
            asdict(value)
        )

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): to_jsonable(
                item
            )
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            to_jsonable(item)
            for item in value
        ]

    raise TypeError(
        "Unsupported journal value "
        f"type: {type(value).__name__}"
    )


class TradingRunJournal:
    def __init__(
        self,
        *,
        store: JournalStore,
        symbol: str,
        run_id: str | None = None,
    ):
        self.store = store
        self.symbol = symbol

        self.run_id = (
            run_id
            if run_id is not None
            else uuid4().hex
        )

        self._started = False
        self._finished = False

    @property
    def is_started(
        self,
    ) -> bool:
        return self._started

    @property
    def is_finished(
        self,
    ) -> bool:
        return self._finished

    def start(
        self,
        *,
        mode: str,
    ) -> None:

        if self._started:
            raise RuntimeError(
                "Trading run journal "
                "has already started."
            )

        self._started = True

        self._write(
            JournalEventType.RUN_STARTED,
            {
                "mode": mode,
            },
        )

    def record_market_context(
        self,
        context,
    ) -> None:

        self._require_active()

        self._write(
            JournalEventType.MARKET_CONTEXT,
            {
                "context":
                to_jsonable(context),
            },
        )

    def record_decision(
        self,
        decision_result,
    ) -> None:

        self._require_active()

        proposal = getattr(
            decision_result,
            "proposal",
            None,
        )

        self._write(
            JournalEventType.DECISION,
            {
                "accepted": bool(
                    getattr(
                        decision_result,
                        "accepted",
                        False,
                    )
                ),

                "error": to_jsonable(
                    getattr(
                        decision_result,
                        "error",
                        None,
                    )
                ),

                "proposal":
                to_jsonable(proposal),
            },
        )

    def record_risk(
        self,
        bridge_result,
    ) -> None:

        self._require_active()

        self._write(
            JournalEventType.RISK_RESULT,
            {
                "status":
                to_jsonable(
                    getattr(
                        bridge_result,
                        "status",
                        None,
                    )
                ),

                "no_trade_reason":
                to_jsonable(
                    getattr(
                        bridge_result,
                        "no_trade_reason",
                        None,
                    )
                ),

                "risk_result":
                to_jsonable(
                    getattr(
                        bridge_result,
                        "risk_result",
                        None,
                    )
                ),
            },
        )

    def record_manual_approval(
        self,
        *,
        approval_request,
        approval_result,
    ) -> None:

        self._require_active()

        self._write(
            JournalEventType.MANUAL_APPROVAL,
            {
                "request":
                to_jsonable(
                    approval_request
                ),

                "result":
                to_jsonable(
                    approval_result
                ),
            },
        )

    def record_execution(
        self,
        *,
        execution_request,
        execution_result,
    ) -> None:

        self._require_active()

        self._write(
            JournalEventType.EXECUTION_RESULT,
            {
                "request":
                to_jsonable(
                    execution_request
                ),

                "result":
                to_jsonable(
                    execution_result
                ),
            },
        )

    def record_trade_outcome(
        self,
        outcome,
    ) -> None:

        self._require_active()

        self._write(
            JournalEventType.TRADE_OUTCOME,
            {
                "outcome":
                to_jsonable(outcome),
            },
        )

    def record_error(
        self,
        *,
        stage: str,
        error: Exception,
    ) -> None:

        self._require_started()

        if self._finished:
            raise RuntimeError(
                "Cannot record an error "
                "after run completion."
            )

        self._write(
            JournalEventType.ERROR,
            {
                "stage": stage,

                "error_type":
                type(error).__name__,

                "message":
                str(error),
            },
        )

    def finish(
        self,
        *,
        status: str,
    ) -> None:

        self._require_started()

        if self._finished:
            raise RuntimeError(
                "Trading run journal "
                "has already finished."
            )

        self._write(
            JournalEventType.RUN_FINISHED,
            {
                "status": status,
            },
        )

        self._finished = True

    def _write(
        self,
        event_type:
        JournalEventType,
        payload: dict,
    ) -> None:

        event = JournalEvent.create(
            run_id=self.run_id,
            event_type=event_type,
            symbol=self.symbol,
            payload=to_jsonable(
                payload
            ),
        )

        self.store.append(
            event
        )

    def _require_started(
        self,
    ) -> None:

        if not self._started:
            raise RuntimeError(
                "Trading run journal "
                "has not been started."
            )

    def _require_active(
        self,
    ) -> None:

        self._require_started()

        if self._finished:
            raise RuntimeError(
                "Trading run journal "
                "has already finished."
            )