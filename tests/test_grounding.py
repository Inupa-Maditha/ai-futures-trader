from datetime import (
    datetime,
    timezone,
)
from types import SimpleNamespace

from decision_engine.grounding import (
    EvidenceGroundingValidator,
)

from decision_engine.schema import (
    DecisionAction,
    DecisionProposal,
    EvidenceDirection,
    EvidenceItem,
    SetupQuality,
)


def enum_value(value: str):
    return SimpleNamespace(
        value=value
    )


def make_timeframe(
    trend: str,
    close: float,
):
    return SimpleNamespace(
        latest_close=close,
        trend=enum_value(trend),
        latest_structure_label="HH",
        latest_swing_high=86000.0,
        latest_swing_low=84000.0,
        latest_break_type=enum_value(
            "BOS_BULLISH"
        ),
        latest_break_level=85500.0,

        indicators=SimpleNamespace(
            ema_20=84900.0,
            ema_50=84700.0,
            ema_200=82000.0,
            rsi_14=55.0,
            atr_14=500.0,
            atr_percent=0.7,
        ),
    )


def make_context():
    return SimpleNamespace(
        symbol="BTCUSDT",

        generated_at_utc=datetime.now(
            timezone.utc
        ),

        technical=SimpleNamespace(
            trend_alignment=enum_value(
                "MIXED"
            ),

            timeframe_15m=make_timeframe(
                "BEARISH",
                84950.0,
            ),

            timeframe_1h=make_timeframe(
                "BULLISH",
                85000.0,
            ),

            timeframe_4h=make_timeframe(
                "BULLISH",
                85100.0,
            ),
        ),

        derivatives=SimpleNamespace(
            open_interest=59622.088,
            oi_change_percent=-0.2781,
            current_funding_rate=0.0001,
            long_account_ratio=0.5106,
            short_account_ratio=0.4894,
            long_short_account_ratio=1.0433,
        ),

        trade_flow=SimpleNamespace(
            aggressive_buy_volume=10.0,
            aggressive_sell_volume=9.0,
            signed_volume_imbalance=0.0526,
            trade_count=100,
        ),

        orderbook=SimpleNamespace(
            mid_price=85000.0,
            spread=0.1,
            spread_bps=0.02,
            depth_levels=10,
            depth_imbalance=0.10,
        ),

        liquidations=SimpleNamespace(
            event_count=0,
            long_liquidation_volume=0.0,
            short_liquidation_volume=0.0,
        ),

        health=SimpleNamespace(
            all_required_healthy=True,
        ),
    )


def make_proposal(
    evidence: list[EvidenceItem],
):
    return DecisionProposal(
        symbol="BTCUSDT",
        action=DecisionAction.NO_TRADE,
        setup_quality=SetupQuality.LOW,
        confidence=0.5,
        thesis="Mixed context.",
        evidence=evidence,
        no_trade_reason="No clear setup.",
    )


def test_exact_grounded_value_passes():
    proposal = make_proposal(
        [
            EvidenceItem(
                context_path=(
                    "technical.15m.trend"
                ),
                value="BEARISH",
                direction=(
                    EvidenceDirection.BEARISH
                ),
                interpretation=(
                    "The 15m trend is bearish."
                ),
            )
        ]
    )

    result = (
        EvidenceGroundingValidator()
        .validate(
            proposal,
            make_context(),
        )
    )

    assert result.valid is True
    assert result.reasons == ()


def test_exact_numeric_value_passes():
    proposal = make_proposal(
        [
            EvidenceItem(
                context_path=(
                    "derivatives."
                    "oi_change_percent"
                ),
                value="-0.2781",
                direction=(
                    EvidenceDirection.NEUTRAL
                ),
                interpretation=(
                    "Open interest changed "
                    "slightly."
                ),
            )
        ]
    )

    result = (
        EvidenceGroundingValidator()
        .validate(
            proposal,
            make_context(),
        )
    )

    assert result.valid is True


def test_wrong_value_is_rejected():
    proposal = make_proposal(
        [
            EvidenceItem(
                context_path=(
                    "technical.4h.trend"
                ),

                # Actual value is BULLISH.
                value="BEARISH",

                direction=(
                    EvidenceDirection.BEARISH
                ),

                interpretation=(
                    "The 4h trend is bearish."
                ),
            )
        ]
    )

    result = (
        EvidenceGroundingValidator()
        .validate(
            proposal,
            make_context(),
        )
    )

    assert result.valid is False

    assert any(
        "value mismatch"
        in reason
        for reason in result.reasons
    )


def test_unsupported_context_path_is_rejected():
    proposal = make_proposal(
        [
            EvidenceItem(
                context_path=(
                    "derivatives."
                    "open_interest_ratio"
                ),
                value="0.5",
                direction=(
                    EvidenceDirection.NEUTRAL
                ),
                interpretation=(
                    "Invented metric."
                ),
            )
        ]
    )

    result = (
        EvidenceGroundingValidator()
        .validate(
            proposal,
            make_context(),
        )
    )

    assert result.valid is False

    assert any(
        "unsupported context path"
        in reason
        for reason in result.reasons
    )


def test_numeric_value_outside_tolerance_rejected():
    proposal = make_proposal(
        [
            EvidenceItem(
                context_path=(
                    "derivatives."
                    "oi_change_percent"
                ),

                # Actual is -0.2781.
                value="-0.5",

                direction=(
                    EvidenceDirection.BEARISH
                ),

                interpretation=(
                    "Open interest decreased."
                ),
            )
        ]
    )

    result = (
        EvidenceGroundingValidator()
        .validate(
            proposal,
            make_context(),
        )
    )

    assert result.valid is False

    assert any(
        "value mismatch"
        in reason
        for reason in result.reasons
    )