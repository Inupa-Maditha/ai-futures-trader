from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from risk_manager.schema import (
    ApprovedRiskPlan,
)


class ManualApprovalDecision(
    str,
    Enum,
):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ManualApprovalRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    approval_id: str = Field(
        min_length=1
    )

    created_at_utc: datetime

    risk_plan: ApprovedRiskPlan

    @model_validator(
        mode="after"
    )
    def validate_timezone(self):
        value = self.created_at_utc

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "created_at_utc must be "
                "timezone-aware."
            )

        return self


class ManualApprovalResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    approval_id: str = Field(
        min_length=1
    )

    decision: ManualApprovalDecision

    decided_at_utc: datetime

    note: str | None = None

    @model_validator(
        mode="after"
    )
    def validate_timezone(self):
        value = self.decided_at_utc

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "decided_at_utc must be "
                "timezone-aware."
            )

        return self