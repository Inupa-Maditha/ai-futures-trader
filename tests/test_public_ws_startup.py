from __future__ import annotations

from unittest.mock import Mock

import pytest

import market_data.public_ws as public_ws_module

from market_data.public_ws import (
    BybitPublicWebSocket,
)


def test_ws_connects_on_first_attempt(
    monkeypatch,
):
    websocket = Mock()

    websocket_factory = Mock(
        return_value=websocket
    )

    monkeypatch.setattr(
        public_ws_module,
        "WebSocket",
        websocket_factory,
    )

    monkeypatch.setattr(
        public_ws_module,
        "sleep",
        Mock(),
    )

    client = BybitPublicWebSocket()

    assert client.ws is websocket

    assert websocket_factory.call_count == 1


def test_ws_retries_with_backoff_then_connects(
    monkeypatch,
):
    websocket = Mock()

    websocket_factory = Mock(
        side_effect=[
            RuntimeError("attempt 1"),
            RuntimeError("attempt 2"),
            websocket,
        ]
    )

    sleep_mock = Mock()

    monkeypatch.setattr(
        public_ws_module,
        "WebSocket",
        websocket_factory,
    )

    monkeypatch.setattr(
        public_ws_module,
        "sleep",
        sleep_mock,
    )

    client = BybitPublicWebSocket()

    assert client.ws is websocket

    assert websocket_factory.call_count == 3

    assert (
        sleep_mock.call_args_list[0].args[0]
        == 5
    )

    assert (
        sleep_mock.call_args_list[1].args[0]
        == 15
    )


def test_ws_fails_closed_after_bounded_attempts(
    monkeypatch,
):
    websocket_factory = Mock(
        side_effect=RuntimeError(
            "connection failed"
        )
    )

    sleep_mock = Mock()

    monkeypatch.setattr(
        public_ws_module,
        "WebSocket",
        websocket_factory,
    )

    monkeypatch.setattr(
        public_ws_module,
        "sleep",
        sleep_mock,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Unable to establish Bybit "
            "public WebSocket"
        ),
    ):
        BybitPublicWebSocket()

    assert websocket_factory.call_count == 4

    assert [
        call.args[0]
        for call in sleep_mock.call_args_list
    ] == [
        5,
        15,
        30,
    ]