from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from journal.trading_journal import (
    TradingRunJournal,
)


def enum_value(
    value: Any,
) -> Any:
    """
    Return Enum.value when value is an Enum-like
    object. Otherwise return the value unchanged.
    """

    return getattr(
        value,
        "value",
        value,
    )


@dataclass(
    frozen=True,
    slots=True,
)
class PipelineOutcome:
    status: str

    decision_result: Any = None

    risk_result: Any = None

    approval_request: Any = None

    approval_result: Any = None

    execution_request: Any = None

    execution_result: Any = None


class TradingPipeline:
    """
    Test-friendly orchestration layer.

    External systems are supplied through dependency
    injection.

    This class owns pipeline branching only.

    It does not know how:
    - market data is fetched
    - Groq is called
    - account state is fetched
    - risk is calculated internally
    - console approval works
    - Bybit execution works

    Those operations are injected.
    """

    def __init__(
        self,
        *,
        journal: TradingRunJournal,
        market_context_provider:
        Callable[[], Any],
        decision_provider:
        Callable[[Any], Any],
        risk_provider:
        Callable[[Any], Any],
        execution_enabled_provider:
        Callable[[], bool],
        approval_provider:
        Callable[[Any], tuple[Any, Any]]
        | None = None,
        execution_request_provider:
        Callable[[Any, Any], Any]
        | None = None,
        execution_provider:
        Callable[[Any], Any]
        | None = None,
        execution_uncertain_exceptions:
        tuple[type[Exception], ...] = (),
    ):
        self.journal = journal

        self.market_context_provider = (
            market_context_provider
        )

        self.decision_provider = (
            decision_provider
        )

        self.risk_provider = (
            risk_provider
        )

        self.execution_enabled_provider = (
            execution_enabled_provider
        )

        self.approval_provider = (
            approval_provider
        )

        self.execution_request_provider = (
            execution_request_provider
        )

        self.execution_provider = (
            execution_provider
        )

        self.execution_uncertain_exceptions = (
            execution_uncertain_exceptions
        )

    def run(
        self,
    ) -> PipelineOutcome:

        # -----------------------------------------
        # 1. Market context
        # -----------------------------------------

        context = (
            self.market_context_provider()
        )

        self.journal.record_market_context(
            context
        )

        # -----------------------------------------
        # 2. Decision
        # -----------------------------------------

        decision_result = (
            self.decision_provider(
                context
            )
        )

        self.journal.record_decision(
            decision_result
        )

        accepted = bool(
            getattr(
                decision_result,
                "accepted",
                False,
            )
        )

        proposal = getattr(
            decision_result,
            "proposal",
            None,
        )

        if (
            not accepted
            or proposal is None
        ):
            self.journal.finish(
                status="DECISION_REJECTED"
            )

            return PipelineOutcome(
                status=(
                    "DECISION_REJECTED"
                ),
                decision_result=(
                    decision_result
                ),
            )

        action = enum_value(
            getattr(
                proposal,
                "action",
                None,
            )
        )

        # -----------------------------------------
        # 3. NO_TRADE short circuit
        # -----------------------------------------

        if action == "NO_TRADE":
            self.journal.finish(
                status="NO_TRADE"
            )

            return PipelineOutcome(
                status="NO_TRADE",
                decision_result=(
                    decision_result
                ),
            )

        if action not in (
            "LONG",
            "SHORT",
        ):
            raise RuntimeError(
                "Validated trade proposal "
                "contains unsupported action: "
                f"{action}"
            )

        # -----------------------------------------
        # 4. Deterministic risk
        # -----------------------------------------

        risk_result = (
            self.risk_provider(
                proposal
            )
        )

        self.journal.record_risk(
            risk_result
        )

        risk_status = enum_value(
            getattr(
                risk_result,
                "status",
                None,
            )
        )

        if (
            risk_status
            != "RISK_APPROVED"
        ):
            self.journal.finish(
                status="RISK_REJECTED"
            )

            return PipelineOutcome(
                status="RISK_REJECTED",

                decision_result=(
                    decision_result
                ),

                risk_result=(
                    risk_result
                ),
            )

        # -----------------------------------------
        # 5. Demo execution safety switch
        # -----------------------------------------

        if not (
            self.execution_enabled_provider()
        ):
            self.journal.finish(
                status=(
                    "DEMO_EXECUTION_DISABLED"
                )
            )

            return PipelineOutcome(
                status=(
                    "DEMO_EXECUTION_DISABLED"
                ),

                decision_result=(
                    decision_result
                ),

                risk_result=(
                    risk_result
                ),
            )

        # -----------------------------------------
        # 6. Approval dependencies
        # -----------------------------------------

        if self.approval_provider is None:
            raise RuntimeError(
                "approval_provider is required "
                "when Demo execution is enabled."
            )

        (
            approval_request,
            approval_result,
        ) = self.approval_provider(
            risk_result
        )

        self.journal.record_manual_approval(
            approval_request=(
                approval_request
            ),

            approval_result=(
                approval_result
            ),
        )

        approval_decision = enum_value(
            getattr(
                approval_result,
                "decision",
                None,
            )
        )

        if (
            approval_decision
            != "APPROVE"
        ):
            self.journal.finish(
                status=(
                    "MANUALLY_REJECTED"
                )
            )

            return PipelineOutcome(
                status=(
                    "MANUALLY_REJECTED"
                ),

                decision_result=(
                    decision_result
                ),

                risk_result=(
                    risk_result
                ),

                approval_request=(
                    approval_request
                ),

                approval_result=(
                    approval_result
                ),
            )

        # -----------------------------------------
        # 7. Execution request
        # -----------------------------------------

        if (
            self.execution_request_provider
            is None
        ):
            raise RuntimeError(
                "execution_request_provider "
                "is required after approval."
            )

        execution_request = (
            self.execution_request_provider(
                approval_request,
                approval_result,
            )
        )

        # -----------------------------------------
        # 8. Execution
        # -----------------------------------------

        if self.execution_provider is None:
            raise RuntimeError(
                "execution_provider is required "
                "after approval."
            )

        try:
            execution_result = (
                self.execution_provider(
                    execution_request
                )
            )

        except (
            self.execution_uncertain_exceptions
        ) as exc:
            self.journal.record_error(
                stage="EXECUTION",
                error=exc,
            )

            self.journal.finish(
                status="EXECUTION_UNCERTAIN"
            )

            return PipelineOutcome(
                status=(
                    "EXECUTION_UNCERTAIN"
                ),

                decision_result=(
                    decision_result
                ),

                risk_result=(
                    risk_result
                ),

                approval_request=(
                    approval_request
                ),

                approval_result=(
                    approval_result
                ),

                execution_request=(
                    execution_request
                ),
            )

        # -----------------------------------------
        # 9. Successful execution
        # -----------------------------------------

        self.journal.record_execution(
            execution_request=(
                execution_request
            ),

            execution_result=(
                execution_result
            ),
        )

        self.journal.finish(
            status="DEMO_ORDER_CONFIRMED"
        )

        return PipelineOutcome(
            status=(
                "DEMO_ORDER_CONFIRMED"
            ),

            decision_result=(
                decision_result
            ),

            risk_result=(
                risk_result
            ),

            approval_request=(
                approval_request
            ),

            approval_result=(
                approval_result
            ),

            execution_request=(
                execution_request
            ),

            execution_result=(
                execution_result
            ),
        )