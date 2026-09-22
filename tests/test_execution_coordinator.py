from decimal import Decimal

import pytest

from execution.coordinator import (
    CoordinatedExecutionStatus,
    DemoExecutionCoordinator,
    ExecutionUncertainError,
)

from execution.order_repository import (
    ObservedOrder,
)

from execution.schema import (
    DemoExecutionAck,
    DemoExecutionRequest,
    ExecutionSide,
    ExecutionStatus,
)


def make_request():
    return DemoExecutionRequest(
        approval_id="approval-1",

        order_link_id=(
            "aft-v1-test"
        ),

        symbol="BTCUSDT",

        side=ExecutionSide.BUY,

        quantity=Decimal(
            "0.050"
        ),

        entry_price=Decimal(
            "86000.10"
        ),

        stop_loss=Decimal(
            "85000.00"
        ),

        take_profit=Decimal(
            "88000.00"
        ),

        leverage=Decimal(
            "1"
        ),
    )


def make_observed(
    *,
    order_id="order-123",
    link_id="aft-v1-test",
    side="Buy",
    quantity="0.050",
    price="86000.10",
    status="New",
    position_idx=0,
    reduce_only=False,
):
    return ObservedOrder(
        symbol="BTCUSDT",

        order_id=order_id,

        order_link_id=link_id,

        side=side,

        order_status=status,

        quantity=Decimal(
            quantity
        ),

        price=Decimal(
            price
        ),

        position_idx=(
            position_idx
        ),

        reduce_only=(
            reduce_only
        ),
    )


def make_ack():
    return DemoExecutionAck(
        status=(
            ExecutionStatus
            .ACKNOWLEDGED
        ),

        approval_id="approval-1",

        order_id="order-123",

        order_link_id=(
            "aft-v1-test"
        ),

        symbol="BTCUSDT",

        side=ExecutionSide.BUY,

        quantity=Decimal(
            "0.050"
        ),

        leverage=Decimal(
            "1"
        ),

        leverage_changed=False,
    )


class FakeRepository:
    def __init__(
        self,
        responses,
    ):
        self.responses = list(
            responses
        )

        self.calls = 0

    def find_by_link_id(
        self,
        **kwargs,
    ):
        self.calls += 1

        if not self.responses:
            return None

        result = self.responses.pop(
            0
        )

        if isinstance(
            result,
            Exception,
        ):
            raise result

        return result


class FakePreflight:
    def __init__(self):
        self.calls = 0

    def validate(
        self,
        request,
    ):
        self.calls += 1


class FakeExecutionClient:
    def __init__(
        self,
        *,
        ack=None,
        error=None,
    ):
        self.ack = (
            ack
            if ack is not None
            else make_ack()
        )

        self.error = error

        self.calls = 0

    def submit(
        self,
        request,
    ):
        self.calls += 1

        if self.error is not None:
            raise self.error

        return self.ack


def make_coordinator(
    *,
    repository,
    client=None,
    preflight=None,
    attempts=3,
):
    return DemoExecutionCoordinator(
        execution_client=(
            client
            if client is not None
            else FakeExecutionClient()
        ),

        order_repository=(
            repository
        ),

        preflight=(
            preflight
            if preflight is not None
            else FakePreflight()
        ),

        confirmation_attempts=(
            attempts
        ),

        confirmation_interval_seconds=0,

        sleeper=lambda _: None,
    )


def test_existing_order_is_never_resubmitted():
    repository = FakeRepository(
        [
            make_observed()
        ]
    )

    client = FakeExecutionClient()

    preflight = FakePreflight()

    coordinator = make_coordinator(
        repository=repository,
        client=client,
        preflight=preflight,
    )

    result = coordinator.execute(
        make_request()
    )

    assert (
        result.status
        == CoordinatedExecutionStatus
        .PREEXISTING_ORDER
    )

    assert client.calls == 0

    assert preflight.calls == 0


def test_new_order_runs_preflight_and_confirms():
    repository = FakeRepository(
        [
            None,
            None,
            make_observed(),
        ]
    )

    client = FakeExecutionClient()

    preflight = FakePreflight()

    coordinator = make_coordinator(
        repository=repository,
        client=client,
        preflight=preflight,
    )

    result = coordinator.execute(
        make_request()
    )

    assert (
        result.status
        == CoordinatedExecutionStatus
        .SUBMITTED_CONFIRMED
    )

    assert preflight.calls == 1

    assert client.calls == 1

    assert result.ack is not None

    assert (
        result.observed_order.order_status
        == "New"
    )


def test_preexisting_mismatched_order_fails_closed():
    repository = FakeRepository(
        [
            make_observed(
                side="Sell"
            )
        ]
    )

    coordinator = make_coordinator(
        repository=repository
    )

    with pytest.raises(
        RuntimeError,
        match="side",
    ):
        coordinator.execute(
            make_request()
        )


def test_submit_error_can_be_reconciled():
    repository = FakeRepository(
        [
            None,
            make_observed(),
        ]
    )

    client = FakeExecutionClient(
        error=RuntimeError(
            "network timeout"
        )
    )

    coordinator = make_coordinator(
        repository=repository,
        client=client,
    )

    result = coordinator.execute(
        make_request()
    )

    assert (
        result.status
        == CoordinatedExecutionStatus
        .RECONCILED_AFTER_SUBMIT_ERROR
    )

    assert client.calls == 1

    assert (
        result.submit_error
        == "network timeout"
    )


def test_submit_error_without_order_is_uncertain():
    repository = FakeRepository(
        [
            None,
            None,
            None,
        ]
    )

    client = FakeExecutionClient(
        error=RuntimeError(
            "network timeout"
        )
    )

    coordinator = make_coordinator(
        repository=repository,
        client=client,
        attempts=2,
    )

    with pytest.raises(
        ExecutionUncertainError,
        match="Do not retry",
    ):
        coordinator.execute(
            make_request()
        )

    assert client.calls == 1


def test_ack_without_confirmation_is_uncertain():
    repository = FakeRepository(
        [
            None,
            None,
            None,
            None,
        ]
    )

    client = FakeExecutionClient()

    coordinator = make_coordinator(
        repository=repository,
        client=client,
        attempts=3,
    )

    with pytest.raises(
        ExecutionUncertainError,
        match="Do not submit",
    ):
        coordinator.execute(
            make_request()
        )

    assert client.calls == 1


def test_ack_order_id_mismatch_is_uncertain():
    repository = FakeRepository(
        [
            None,
            make_observed(
                order_id=(
                    "different-order"
                )
            ),
        ]
    )

    coordinator = make_coordinator(
        repository=repository
    )

    with pytest.raises(
        ExecutionUncertainError,
        match="orderId",
    ):
        coordinator.execute(
            make_request()
        )


def test_rejected_existing_order_is_not_resubmitted():
    repository = FakeRepository(
        [
            make_observed(
                status="Rejected"
            )
        ]
    )

    client = FakeExecutionClient()

    coordinator = make_coordinator(
        repository=repository,
        client=client,
    )

    result = coordinator.execute(
        make_request()
    )

    assert (
        result.status
        == CoordinatedExecutionStatus
        .PREEXISTING_ORDER
    )

    assert (
        result.observed_order
        .order_status
        == "Rejected"
    )

    # Critical idempotency rule:
    assert client.calls == 0