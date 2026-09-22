from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
)


class JournalEventType(str, Enum):
    RUN_STARTED = "RUN_STARTED"

    MARKET_CONTEXT = "MARKET_CONTEXT"

    DECISION = "DECISION"

    RISK_RESULT = "RISK_RESULT"

    MANUAL_APPROVAL = "MANUAL_APPROVAL"

    EXECUTION_RESULT = "EXECUTION_RESULT"

    TRADE_OUTCOME = "TRADE_OUTCOME"

    ERROR = "ERROR"

    RUN_FINISHED = "RUN_FINISHED"


class JournalEvent(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    schema_version: str = "1.0"

    event_id: str = Field(
        min_length=1
    )

    run_id: str = Field(
        min_length=1
    )

    timestamp_utc: datetime

    event_type: JournalEventType

    symbol: str = Field(
        min_length=1
    )

    payload: dict[str, JsonValue]

    @field_validator(
        "timestamp_utc"
    )
    @classmethod
    def validate_timestamp(
        cls,
        value: datetime,
    ) -> datetime:

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "timestamp_utc must be "
                "timezone-aware."
            )

        return value.astimezone(
            timezone.utc
        )

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        event_type: JournalEventType,
        symbol: str,
        payload: dict[str, JsonValue],
        timestamp_utc: datetime | None = None,
    ) -> "JournalEvent":

        timestamp = (
            timestamp_utc
            if timestamp_utc is not None
            else datetime.now(
                timezone.utc
            )
        )

        return cls(
            event_id=uuid4().hex,
            run_id=run_id,
            timestamp_utc=timestamp,
            event_type=event_type,
            symbol=symbol,
            payload=payload,
        )