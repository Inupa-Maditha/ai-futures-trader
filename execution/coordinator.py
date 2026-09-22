from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import sleep
from typing import Callable

from execution.bybit_demo import (
    BybitDemoExecutionClient,
)

from execution.order_repository import (
    BybitDemoOrderRepository,
    ObservedOrder,
)

from execution.preflight import (
    DemoExecutionPreflight,
)

from execution.schema import (
    DemoExecutionAck,
    DemoExecutionRequest,
)


class CoordinatedExecutionStatus(
    str,
    Enum,
):
    PREEXISTING_ORDER = (
        "PREEXISTING_ORDER"
    )

    SUBMITTED_CONFIRMED = (
        "SUBMITTED_CONFIRMED"
    )

    RECONCILED_AFTER_SUBMIT_ERROR = (
        "RECONCILED_AFTER_SUBMIT_ERROR"
    )


class ExecutionUncertainError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class CoordinatedExecutionResult:
    status: CoordinatedExecutionStatus

    request: DemoExecutionRequest

    observed_order: ObservedOrder

    ack: DemoExecutionAck | None

    submit_error: str | None


class DemoExecutionCoordinator:
    KNOWN_ORDER_STATUSES = {
        "New",
        "PartiallyFilled",
        "Filled",
        "Cancelled",
        "Rejected",
        "Untriggered",
        "Triggered",
        "Deactivated",
    }

    def __init__(
        self,
        execution_client:
        BybitDemoExecutionClient,

        order_repository:
        BybitDemoOrderRepository,

        preflight:
        DemoExecutionPreflight,

        confirmation_attempts: int = 5,

        confirmation_interval_seconds:
        float = 0.5,

        sleeper: Callable[
            [float],
            None,
        ] = sleep,
    ):
        if confirmation_attempts < 1:
            raise ValueError(
                "confirmation_attempts "
                "must be at least 1."
            )

        if (
            confirmation_interval_seconds
            < 0
        ):
            raise ValueError(
                "confirmation interval "
                "must not be negative."
            )

        self.execution_client = (
            execution_client
        )

        self.order_repository = (
            order_repository
        )

        self.preflight = preflight

        self.confirmation_attempts = (
            confirmation_attempts
        )

        self.confirmation_interval_seconds = (
            confirmation_interval_seconds
        )

        self.sleeper = sleeper

    def execute(
        self,
        request:
        DemoExecutionRequest,
    ) -> CoordinatedExecutionResult:

        # -----------------------------------------
        # 1. Idempotency reconciliation BEFORE
        #    doing anything that could create
        #    another order.
        # -----------------------------------------

        existing = (
            self.order_repository
            .find_by_link_id(
                symbol=request.symbol,

                order_link_id=(
                    request.order_link_id
                ),
            )
        )

        if existing is not None:
            self._validate_observed_order(
                request=request,
                observed=existing,
            )

            return (
                CoordinatedExecutionResult(
                    status=(
                        CoordinatedExecutionStatus
                        .PREEXISTING_ORDER
                    ),

                    request=request,

                    observed_order=(
                        existing
                    ),

                    ack=None,

                    submit_error=None,
                )
            )

        # -----------------------------------------
        # 2. Last-moment safety checks.
        # -----------------------------------------

        self.preflight.validate(
            request
        )

        # -----------------------------------------
        # 3. Submit ONCE.
        #
        # Any exception after this point is
        # potentially ambiguous:
        #
        # the request may have reached Bybit
        # even if our client did not receive
        # the response.
        # -----------------------------------------

        try:
            ack = (
                self.execution_client
                .submit(
                    request
                )
            )

        except Exception as exc:
            observed = (
                self._poll_for_order(
                    request
                )
            )

            if observed is not None:
                self._validate_observed_order(
                    request=request,
                    observed=observed,
                )

                return (
                    CoordinatedExecutionResult(
                        status=(
                            CoordinatedExecutionStatus
                            .RECONCILED_AFTER_SUBMIT_ERROR
                        ),

                        request=request,

                        observed_order=(
                            observed
                        ),

                        ack=None,

                        submit_error=str(exc),
                    )
                )

            raise ExecutionUncertainError(
                "Execution state is uncertain "
                "after a submission error. "
                "Do not retry this order "
                "blindly. Reconcile the "
                "orderLinkId before any "
                "further execution action."
            ) from exc

        # -----------------------------------------
        # 4. REST acknowledgement is NOT
        #    final confirmation.
        #
        # Poll by deterministic orderLinkId.
        # -----------------------------------------

        observed = self._poll_for_order(
            request
        )

        if observed is None:
            raise ExecutionUncertainError(
                "Bybit acknowledged the order "
                "submission but the order "
                "could not be confirmed by "
                "orderLinkId. Do not submit "
                "the order again blindly."
            )

        self._validate_observed_order(
            request=request,
            observed=observed,
        )

        # -----------------------------------------
        # 5. Correlate ACK orderId with
        #    reconciled order.
        # -----------------------------------------

        if (
            observed.order_id
            != ack.order_id
        ):
            raise ExecutionUncertainError(
                "Acknowledged orderId does "
                "not match the reconciled "
                "orderId. Execution state "
                "is uncertain."
            )

        if (
            observed.order_link_id
            != ack.order_link_id
        ):
            raise ExecutionUncertainError(
                "Acknowledged orderLinkId "
                "does not match the "
                "reconciled order."
            )

        return CoordinatedExecutionResult(
            status=(
                CoordinatedExecutionStatus
                .SUBMITTED_CONFIRMED
            ),

            request=request,

            observed_order=observed,

            ack=ack,

            submit_error=None,
        )

    def _poll_for_order(
        self,
        request:
        DemoExecutionRequest,
    ) -> ObservedOrder | None:

        last_error: Exception | None = None

        for attempt in range(
            self.confirmation_attempts
        ):
            try:
                observed = (
                    self.order_repository
                    .find_by_link_id(
                        symbol=(
                            request.symbol
                        ),

                        order_link_id=(
                            request
                            .order_link_id
                        ),
                    )
                )

                if observed is not None:
                    return observed

                last_error = None

            except Exception as exc:
                last_error = exc

            if (
                attempt
                < self.confirmation_attempts
                - 1
            ):
                self.sleeper(
                    self
                    .confirmation_interval_seconds
                )

        if last_error is not None:
            raise ExecutionUncertainError(
                "Unable to reconcile "
                "the submitted order due "
                "to repeated order-query "
                "failures. Do not retry "
                "the order blindly."
            ) from last_error

        return None

    def _validate_observed_order(
        self,
        *,
        request:
        DemoExecutionRequest,

        observed:
        ObservedOrder,
    ) -> None:

        if (
            observed.symbol
            != request.symbol
        ):
            raise RuntimeError(
                "Reconciled order symbol "
                "does not match the "
                "execution request."
            )

        if (
            observed.order_link_id
            != request.order_link_id
        ):
            raise RuntimeError(
                "Reconciled orderLinkId "
                "does not match the "
                "execution request."
            )

        if (
            observed.side
            != request.side.value
        ):
            raise RuntimeError(
                "Reconciled order side "
                "does not match the "
                "execution request."
            )

        if (
            observed.quantity
            != request.quantity
        ):
            raise RuntimeError(
                "Reconciled order quantity "
                "does not match the "
                "approved quantity."
            )

        if observed.price is None:
            raise RuntimeError(
                "Reconciled limit order "
                "is missing its price."
            )

        if (
            observed.price
            != request.entry_price
        ):
            raise RuntimeError(
                "Reconciled order price "
                "does not match the "
                "approved entry price."
            )

        if observed.position_idx != 0:
            raise RuntimeError(
                "Reconciled order is not "
                "using One-Way mode."
            )

        if observed.reduce_only:
            raise RuntimeError(
                "Reconciled entry order "
                "unexpectedly has "
                "reduceOnly enabled."
            )

        if (
            observed.order_status
            not in self.KNOWN_ORDER_STATUSES
        ):
            raise RuntimeError(
                "Reconciled order has an "
                "unknown order status: "
                f"{observed.order_status!r}."
            )