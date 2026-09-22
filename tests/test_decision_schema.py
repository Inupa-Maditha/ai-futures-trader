import pytest

from pydantic import ValidationError

from decision_engine.schema import (
    DecisionAction,
    DecisionProposal,
    EvidenceDirection,
    EvidenceItem,
    SetupQuality,
)


def evidence():
    return [
        EvidenceItem(
            context_path="technical.1h.trend",
            value="BULLISH",
            direction=EvidenceDirection.BULLISH,
            interpretation=(
                "The 1h trend is bullish."
            ),
        )
    ]


def test_valid_long():
    proposal = DecisionProposal(
        symbol="BTCUSDT",
        action=DecisionAction.LONG,
        setup_quality=SetupQuality.MEDIUM,
        confidence=0.72,
        thesis="Bullish setup.",
        evidence=evidence(),
        entry_price=85000,
        stop_loss=84500,
        take_profit=86000,
        invalidation_reason=(
            "Bullish structure fails."
        ),
    )

    assert proposal.action == DecisionAction.LONG


def test_valid_short():
    proposal = DecisionProposal(
        symbol="BTCUSDT",
        action=DecisionAction.SHORT,
        setup_quality=SetupQuality.MEDIUM,
        confidence=0.65,
        thesis="Bearish setup.",
        evidence=evidence(),
        entry_price=85000,
        stop_loss=85500,
        take_profit=84000,
        invalidation_reason=(
            "Bearish structure fails."
        ),
    )

    assert proposal.action == DecisionAction.SHORT


def test_valid_no_trade():
    proposal = DecisionProposal(
        symbol="BTCUSDT",
        action=DecisionAction.NO_TRADE,
        setup_quality=SetupQuality.LOW,
        confidence=0.85,
        thesis="Timeframes conflict.",
        evidence=evidence(),
        no_trade_reason=(
            "No clear directional setup."
        ),
    )

    assert (
        proposal.action
        == DecisionAction.NO_TRADE
    )


def test_no_trade_rejects_prices():
    with pytest.raises(ValidationError):
        DecisionProposal(
            symbol="BTCUSDT",
            action=DecisionAction.NO_TRADE,
            setup_quality=SetupQuality.LOW,
            confidence=0.8,
            thesis="No trade.",
            evidence=evidence(),
            entry_price=85000,
            no_trade_reason=(
                "Conflicting context."
            ),
        )


def test_long_rejects_invalid_price_order():
    with pytest.raises(ValidationError):
        DecisionProposal(
            symbol="BTCUSDT",
            action=DecisionAction.LONG,
            setup_quality=SetupQuality.HIGH,
            confidence=0.8,
            thesis="Long.",
            evidence=evidence(),
            entry_price=85000,
            stop_loss=85500,
            take_profit=86000,
            invalidation_reason=(
                "Invalidated."
            ),
        )


def test_short_rejects_invalid_price_order():
    with pytest.raises(ValidationError):
        DecisionProposal(
            symbol="BTCUSDT",
            action=DecisionAction.SHORT,
            setup_quality=SetupQuality.HIGH,
            confidence=0.8,
            thesis="Short.",
            evidence=evidence(),
            entry_price=85000,
            stop_loss=84500,
            take_profit=84000,
            invalidation_reason=(
                "Invalidated."
            ),
        )


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        DecisionProposal(
            symbol="BTCUSDT",
            action=DecisionAction.NO_TRADE,
            setup_quality=SetupQuality.LOW,
            confidence=0.5,
            thesis="No trade.",
            evidence=evidence(),
            no_trade_reason="Wait.",
            leverage=100,
        )