from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(
    frozen=True,
    slots=True,
)
class RiskPolicy:
    # 0.5% of account equity per trade.
    risk_per_trade_fraction: Decimal = Decimal(
        "0.005"
    )

    # Reject extremely tiny stops.
    min_stop_distance_fraction: Decimal = Decimal(
        "0.001"
    )

    # Reject very wide stops.
    max_stop_distance_fraction: Decimal = Decimal(
        "0.03"
    )

    # Minimum reward:risk ratio.
    minimum_reward_risk: Decimal = Decimal(
        "1.5"
    )

    # Hard V1 leverage ceiling.
    max_leverage: Decimal = Decimal(
        "3"
    )

    # Stop new trades after losing
    # 2% of starting/evaluated equity
    # during the trading day.
    max_daily_loss_fraction: Decimal = Decimal(
        "0.02"
    )

    # V1 allows only one BTCUSDT
    # directional position at a time.
    max_open_positions: int = 1

    def __post_init__(self):
        if not (
            Decimal("0")
            < self.risk_per_trade_fraction
            < Decimal("1")
        ):
            raise ValueError(
                "risk_per_trade_fraction "
                "must be between 0 and 1."
            )

        if not (
            Decimal("0")
            < self.min_stop_distance_fraction
        ):
            raise ValueError(
                "min_stop_distance_fraction "
                "must be greater than zero."
            )

        if (
            self.max_stop_distance_fraction
            <= self.min_stop_distance_fraction
        ):
            raise ValueError(
                "max_stop_distance_fraction "
                "must be greater than "
                "min_stop_distance_fraction."
            )

        if self.minimum_reward_risk <= 0:
            raise ValueError(
                "minimum_reward_risk "
                "must be greater than zero."
            )

        if self.max_leverage < 1:
            raise ValueError(
                "max_leverage must be "
                "at least 1."
            )

        if not (
            Decimal("0")
            < self.max_daily_loss_fraction
            < Decimal("1")
        ):
            raise ValueError(
                "max_daily_loss_fraction "
                "must be between 0 and 1."
            )

        if self.max_open_positions < 1:
            raise ValueError(
                "max_open_positions "
                "must be at least 1."
            )