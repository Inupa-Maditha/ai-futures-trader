from __future__ import annotations

from decimal import Decimal

import pytest

from execution.coordinator import (
    DemoExecutionCoordinator,
    ExecutionUncertainError,
)

from execution.order_repository import (
    ObservedOrder,
)

from execution.preflight import (
    DemoExecutionPreflight,
)

from execution.schema import (
    DemoExecutionAck,
    DemoExecutionRequest,
    ExecutionSide,
    ExecutionStatus,
)


# =========================================================
# Shared request / order builders
# =========================================================


def make_request(
    *,
    order_link_id="aft-v1-integration-001",
):
    return DemoExecutionRequest(
        approval_id="approval-001",

        order_link_id=order_link_id,

        symbol="BTCUSDT",

        side=ExecutionSide.BUY,

        quantity=Decimal(
            "0.001"
        ),

        entry_price=Decimal(
            "85000"
        ),

        stop_loss=Decimal(
            "84000"
        ),

        take_profit=Decimal(
            "87000"
        ),

        leverage=Decimal(
            "1"
        ),
    )


def make_observed_order(
    *,
    order_link_id="aft-v1-integration-001",
    order_id="order-001",
    order_status="New",
    reduce_only=False,
):
    return ObservedOrder(
        symbol="BTCUSDT",

        order_id=order_id,

        order_link_id=order_link_id,

        side="Buy",

        order_status=order_status,

        quantity=Decimal(
            "0.001"
        ),

        price=Decimal(
            "85000"
        ),

        position_idx=0,

        reduce_only=reduce_only,
    )


def make_ack(
    *,
    order_link_id="aft-v1-integration-001",
    order_id="order-001",
):
    return DemoExecutionAck(
        status=(
            ExecutionStatus
            .ACKNOWLEDGED
        ),

        approval_id="approval-001",

        order_id=order_id,

        order_link_id=(
            order_link_id
        ),

        symbol="BTCUSDT",

        side=ExecutionSide.BUY,

        quantity=Decimal(
            "0.001"
        ),

        leverage=Decimal(
            "1"
        ),

        leverage_changed=False,
    )


# =========================================================
# Fake Bybit session for real preflight tests
# =========================================================


class FakePositionSession:
    def __init__(
        self,
        *,
        size="0",
        side="",
        position_idx=0,
        ret_code=0,
    ):
        self.size = size
        self.side = side
        self.position_idx = (
            position_idx
        )
        self.ret_code = ret_code
        self.calls = 0

    def get_positions(
        self,
        **kwargs,
    ):
        self.calls += 1

        if self.ret_code != 0:
            return {
                "retCode":
                self.ret_code,

                "retMsg":
                "simulated error",
            }

        return {
            "retCode": 0,

            "result": {
                "list": [
                    {
                        "symbol":
                        "BTCUSDT",

                        "positionIdx":
                        self.position_idx,

                        "side":
                        self.side,

                        "size":
                        self.size,
                    }
                ]
            },
        }


class FakeActiveOrderRepository:
    def __init__(
        self,
        orders=None,
    ):
        self.orders = list(
            orders or []
        )

        self.calls = 0

    def list_active_orders(
        self,
        symbol,
    ):
        self.calls += 1

        assert symbol == "BTCUSDT"

        return tuple(
            self.orders
        )


# =========================================================
# Fake coordinator dependencies
# =========================================================


class PassingPreflight:
    def __init__(
        self,
    ):
        self.calls = 0

    def validate(
        self,
        request,
    ):
        self.calls += 1

        assert (
            request.symbol
            == "BTCUSDT"
        )


class FakeExecutionClient:
    def __init__(
        self,
        *,
        ack=None,
        error=None,
    ):
        self.ack = ack
        self.error = error
        self.submit_calls = 0

    def submit(
        self,
        request,
    ):
        self.submit_calls += 1

        if self.error is not None:
            raise self.error

        if self.ack is None:
            raise AssertionError(
                "FakeExecutionClient "
                "has no ACK configured."
            )

        return self.ack


class SequencedOrderRepository:
    """
    Returns predefined results from
    find_by_link_id().

    When sequence is exhausted,
    returns the final value again.
    """

    def __init__(
        self,
        sequence,
    ):
        self.sequence = list(
            sequence
        )

        self.calls = 0

    def find_by_link_id(
        self,
        symbol,
        order_link_id,
    ):
        self.calls += 1

        assert (
            symbol
            == "BTCUSDT"
        )

        assert (
            order_link_id
            == "aft-v1-integration-001"
        )

        if not self.sequence:
            return None

        if self.calls <= len(
            self.sequence
        ):
            return self.sequence[
                self.calls - 1
            ]

        return self.sequence[
            -1
        ]


# =========================================================
# IT-501
# Existing BTC position must block execution
# =========================================================


def test_existing_open_position_is_blocked():
    request = make_request()

    session = FakePositionSession(
        size="0.015",
        side="Buy",
        position_idx=0,
    )

    repository = (
        FakeActiveOrderRepository()
    )

    preflight = (
        DemoExecutionPreflight(
            session=session,

            order_repository=(
                repository
            ),
        )
    )

    with pytest.raises(
        RuntimeError
    ):
        preflight.validate(
            request
        )

    assert session.calls == 1


# =========================================================
# IT-502
# Existing active entry order must block execution
# =========================================================


def test_conflicting_active_entry_order_is_blocked():
    request = make_request()

    session = FakePositionSession(
        size="0",
        side="",
        position_idx=0,
    )

    conflicting_order = (
        ObservedOrder(
            symbol="BTCUSDT",

            order_id=(
                "existing-entry"
            ),

            order_link_id=(
                "different-entry-link"
            ),

            side="Buy",

            order_status="New",

            quantity=Decimal(
                "0.002"
            ),

            price=Decimal(
                "84000"
            ),

            position_idx=0,

            reduce_only=False,
        )
    )

    repository = (
        FakeActiveOrderRepository(
            [
                conflicting_order
            ]
        )
    )

    preflight = (
        DemoExecutionPreflight(
            session=session,

            order_repository=(
                repository
            ),
        )
    )

    with pytest.raises(
        RuntimeError
    ):
        preflight.validate(
            request
        )

    assert (
        repository.calls
        == 1
    )


# =========================================================
# IT-503
# Protective reduce-only order must not block
# =========================================================


def test_reduce_only_order_does_not_block():
    request = make_request()

    session = FakePositionSession(
        size="0",
        side="",
        position_idx=0,
    )

    protective_order = (
        ObservedOrder(
            symbol="BTCUSDT",

            order_id=(
                "protective-order"
            ),

            order_link_id=(
                "protective-link"
            ),

            side="Sell",

            order_status="New",

            quantity=Decimal(
                "0.001"
            ),

            price=Decimal(
                "84000"
            ),

            position_idx=0,

            reduce_only=True,
        )
    )

    repository = (
        FakeActiveOrderRepository(
            [
                protective_order
            ]
        )
    )

    preflight = (
        DemoExecutionPreflight(
            session=session,

            order_repository=(
                repository
            ),
        )
    )

    # Must not raise.
    preflight.validate(
        request
    )

    assert (
        session.calls
        == 1
    )

    assert (
        repository.calls
        == 1
    )


# =========================================================
# IT-504
# Existing exact orderLinkId must NEVER resubmit
# =========================================================


def test_duplicate_order_link_id_is_not_resubmitted():
    request = make_request()

    existing = (
        make_observed_order()
    )

    repository = (
        SequencedOrderRepository(
            [
                existing
            ]
        )
    )

    preflight = PassingPreflight()

    execution_client = (
        FakeExecutionClient(
            ack=make_ack()
        )
    )

    coordinator = (
        DemoExecutionCoordinator(
            execution_client=(
                execution_client
            ),

            order_repository=(
                repository
            ),

            preflight=(
                preflight
            ),

            confirmation_attempts=3,

            confirmation_interval_seconds=0,

            sleeper=lambda seconds:
            None,
        )
    )

    result = coordinator.execute(
        request
    )

    assert (
        result.status.value
        == "PREEXISTING_ORDER"
    )

    assert (
        result
        .observed_order
        .order_id
        == "order-001"
    )

    # Critical safety assertion:
    # no second submission.
    assert (
        execution_client
        .submit_calls
        == 0
    )

    # Existing exact link is handled
    # before execution preflight.
    assert (
        preflight.calls
        == 0
    )


# =========================================================
# IT-505
# Submit throws but order exists:
# reconcile, never submit twice
# =========================================================


def test_submit_error_reconciles_existing_order():
    request = make_request()

    reconciled_order = (
        make_observed_order(
            order_id=(
                "order-after-error"
            )
        )
    )

    repository = (
        SequencedOrderRepository(
            [
                # Initial idempotency check
                None,

                # First reconciliation
                # after submit exception
                reconciled_order,
            ]
        )
    )

    preflight = PassingPreflight()

    execution_client = (
        FakeExecutionClient(
            error=RuntimeError(
                "Simulated network "
                "timeout after submit"
            )
        )
    )

    coordinator = (
        DemoExecutionCoordinator(
            execution_client=(
                execution_client
            ),

            order_repository=(
                repository
            ),

            preflight=(
                preflight
            ),

            confirmation_attempts=3,

            confirmation_interval_seconds=0,

            sleeper=lambda seconds:
            None,
        )
    )

    result = coordinator.execute(
        request
    )

    assert (
        result.status.value
        == (
            "RECONCILED_AFTER_SUBMIT_ERROR"
        )
    )

    assert (
        result
        .observed_order
        .order_id
        == "order-after-error"
    )

    assert (
        preflight.calls
        == 1
    )

    # Most important assertion:
    # submit happened exactly once.
    assert (
        execution_client
        .submit_calls
        == 1
    )


# =========================================================
# IT-506
# Submit throws and no order can be reconciled:
# state uncertain, no blind retry
# =========================================================


def test_submit_error_without_reconciliation_never_retries():
    request = make_request()

    repository = (
        SequencedOrderRepository(
            [
                None,
                None,
                None,
                None,
                None,
            ]
        )
    )

    preflight = PassingPreflight()

    execution_client = (
        FakeExecutionClient(
            error=RuntimeError(
                "Simulated timeout"
            )
        )
    )

    coordinator = (
        DemoExecutionCoordinator(
            execution_client=(
                execution_client
            ),

            order_repository=(
                repository
            ),

            preflight=(
                preflight
            ),

            confirmation_attempts=3,

            confirmation_interval_seconds=0,

            sleeper=lambda seconds:
            None,
        )
    )

    with pytest.raises(
        ExecutionUncertainError,
        match="Do not retry",
    ):
        coordinator.execute(
            request
        )

    assert (
        preflight.calls
        == 1
    )

    # Critical safety invariant.
    assert (
        execution_client
        .submit_calls
        == 1
    )

    # The coordinator may query/reconcile
    # repeatedly, but it must never issue
    # a second submit.
    assert (
        repository.calls
        >= 2
    )