from __future__ import annotations

from decimal import Decimal

from config.settings import SYMBOL

from risk_manager.instrument_rules import (
    InstrumentRules,
    ceil_to_step,
    floor_to_step,
    nearest_to_step,
)

from risk_manager.policy import (
    RiskPolicy,
)

from risk_manager.schema import (
    ApprovedRiskPlan,
    RiskDecision,
    RiskEvaluationInput,
    RiskEvaluationResult,
    RiskSide,
)


ZERO = Decimal("0")
ONE = Decimal("1")


class DeterministicRiskEngine:
    def __init__(
        self,
        instrument_rules: InstrumentRules,
        policy: RiskPolicy | None = None,
    ):
        self.rules = instrument_rules

        self.policy = (
            policy
            if policy is not None
            else RiskPolicy()
        )

    def evaluate(
        self,
        data: RiskEvaluationInput,
    ) -> RiskEvaluationResult:

        reasons: list[str] = []

        # -------------------------------------------------
        # 1. Symbol guards
        # -------------------------------------------------

        if data.symbol != SYMBOL:
            reasons.append(
                "Symbol does not match "
                "the configured trading symbol."
            )

        if data.symbol != self.rules.symbol:
            reasons.append(
                "Symbol does not match "
                "the loaded instrument rules."
            )

        # -------------------------------------------------
        # 2. Existing-position guard
        # -------------------------------------------------

        if (
            data.open_position_count
            >= self.policy.max_open_positions
        ):
            reasons.append(
                "Maximum open-position "
                "limit reached."
            )

        # -------------------------------------------------
        # 3. Exchange-align prices
        # -------------------------------------------------

        entry_price = nearest_to_step(
            data.entry_price,
            self.rules.tick_size,
        )

        if data.side == RiskSide.LONG:
            stop_loss = floor_to_step(
                data.stop_loss,
                self.rules.tick_size,
            )

            take_profit = floor_to_step(
                data.take_profit,
                self.rules.tick_size,
            )

        else:
            stop_loss = ceil_to_step(
                data.stop_loss,
                self.rules.tick_size,
            )

            take_profit = ceil_to_step(
                data.take_profit,
                self.rules.tick_size,
            )

        # -------------------------------------------------
        # 4. Exchange price boundaries
        # -------------------------------------------------

        for name, price in (
            ("entry_price", entry_price),
            ("stop_loss", stop_loss),
            ("take_profit", take_profit),
        ):
            if (
                price < self.rules.min_price
                or price > self.rules.max_price
            ):
                reasons.append(
                    f"{name} is outside "
                    "Bybit instrument price limits."
                )

        # -------------------------------------------------
        # 5. Re-check structure after rounding
        # -------------------------------------------------

        if data.side == RiskSide.LONG:
            if not (
                stop_loss
                < entry_price
                < take_profit
            ):
                reasons.append(
                    "Exchange price rounding "
                    "invalidated LONG price "
                    "structure."
                )

        else:
            if not (
                take_profit
                < entry_price
                < stop_loss
            ):
                reasons.append(
                    "Exchange price rounding "
                    "invalidated SHORT price "
                    "structure."
                )

        if reasons:
            return self._reject(
                reasons
            )

        # -------------------------------------------------
        # 6. Distances
        # -------------------------------------------------

        stop_distance = abs(
            entry_price - stop_loss
        )

        reward_distance = abs(
            take_profit - entry_price
        )

        if stop_distance <= ZERO:
            return self._reject(
                [
                    "Stop distance must be "
                    "greater than zero."
                ]
            )

        stop_distance_fraction = (
            stop_distance
            / entry_price
        )

        reward_risk_ratio = (
            reward_distance
            / stop_distance
        )

        # -------------------------------------------------
        # 7. Stop policy
        # -------------------------------------------------

        if (
            stop_distance_fraction
            < self.policy
            .min_stop_distance_fraction
        ):
            reasons.append(
                "Stop distance is below "
                "the minimum allowed distance."
            )

        if (
            stop_distance_fraction
            > self.policy
            .max_stop_distance_fraction
        ):
            reasons.append(
                "Stop distance exceeds "
                "the maximum allowed distance."
            )

        # -------------------------------------------------
        # 8. Reward:risk
        # -------------------------------------------------

        if (
            reward_risk_ratio
            < self.policy.minimum_reward_risk
        ):
            reasons.append(
                "Reward-risk ratio is below "
                "the minimum requirement."
            )

        # -------------------------------------------------
        # 9. Maximum risk budget
        # -------------------------------------------------

        risk_amount = (
            data.account_equity
            * self.policy
            .risk_per_trade_fraction
        )

        raw_quantity = (
            risk_amount
            / stop_distance
        )

        executable_quantity = floor_to_step(
            raw_quantity,
            self.rules.qty_step,
        )

        if executable_quantity <= ZERO:
            reasons.append(
                "Risk-sized quantity rounds "
                "to zero."
            )

        # -------------------------------------------------
        # 10. Exchange quantity constraints
        # -------------------------------------------------

        if (
            executable_quantity
            < self.rules.min_order_qty
        ):
            reasons.append(
                "Executable quantity is below "
                "Bybit minimum order quantity."
            )

        max_executable_quantity = min(
            self.rules.max_order_qty,
            self.rules.max_market_order_qty,
        )

        if (
            executable_quantity
            > max_executable_quantity
        ):
            reasons.append(
                "Executable quantity exceeds "
                "the conservative Bybit "
                "maximum order quantity."
            )

        # -------------------------------------------------
        # 11. Actual risk after rounding
        # -------------------------------------------------

        actual_risk_amount = (
            executable_quantity
            * stop_distance
        )

        if (
            actual_risk_amount
            > risk_amount
        ):
            reasons.append(
                "Exchange-rounded quantity "
                "exceeds the configured "
                "risk budget."
            )

        # -------------------------------------------------
        # 12. Notional
        # -------------------------------------------------

        position_notional = (
            executable_quantity
            * entry_price
        )

        if (
            position_notional
            < self.rules.min_notional_value
        ):
            reasons.append(
                "Position notional is below "
                "Bybit minimum notional value."
            )

        # -------------------------------------------------
        # 13. Daily-loss protection
        # -------------------------------------------------

        daily_loss_limit = (
            data.account_equity
            * self.policy
            .max_daily_loss_fraction
        )

        current_daily_loss = max(
            -data.daily_realized_pnl,
            ZERO,
        )

        if (
            current_daily_loss
            >= daily_loss_limit
        ):
            reasons.append(
                "Daily loss limit has "
                "already been reached."
            )

        else:
            remaining_daily_risk_budget = (
                daily_loss_limit
                - current_daily_loss
            )

            if (
                actual_risk_amount
                > remaining_daily_risk_budget
            ):
                reasons.append(
                    "Proposed trade risk exceeds "
                    "the remaining daily "
                    "risk budget."
                )

        # -------------------------------------------------
        # 14. Available balance
        # -------------------------------------------------

        if data.available_balance <= ZERO:
            reasons.append(
                "Available balance is zero."
            )

            return self._reject(
                reasons
            )

        # -------------------------------------------------
        # 15. Required leverage
        # -------------------------------------------------

        minimum_required_leverage = (
            position_notional
            / data.available_balance
        )

        leverage = max(
            minimum_required_leverage,
            ONE,
            self.rules.min_leverage,
        )

        leverage = ceil_to_step(
            leverage,
            self.rules.leverage_step,
        )

        # -------------------------------------------------
        # 16. Policy leverage ceiling
        # -------------------------------------------------

        if (
            leverage
            > self.policy.max_leverage
        ):
            reasons.append(
                "Required leverage exceeds "
                "the maximum allowed "
                "risk-policy leverage."
            )

        # -------------------------------------------------
        # 17. Exchange leverage ceiling
        # -------------------------------------------------

        if (
            leverage
            > self.rules.max_leverage
        ):
            reasons.append(
                "Required leverage exceeds "
                "Bybit maximum leverage."
            )

        required_margin = (
            position_notional
            / leverage
        )

        if (
            required_margin
            > data.available_balance
        ):
            reasons.append(
                "Required margin exceeds "
                "available balance."
            )

        # -------------------------------------------------
        # 18. Final decision
        # -------------------------------------------------

        if reasons:
            return self._reject(
                reasons
            )

        plan = ApprovedRiskPlan(
            symbol=data.symbol,
            side=data.side,

            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,

            risk_amount=risk_amount,

            stop_distance=stop_distance,
            stop_distance_fraction=(
                stop_distance_fraction
            ),

            reward_distance=reward_distance,
            reward_risk_ratio=(
                reward_risk_ratio
            ),

            raw_quantity=raw_quantity,

            executable_quantity=(
                executable_quantity
            ),

            actual_risk_amount=(
                actual_risk_amount
            ),

            position_notional=(
                position_notional
            ),

            required_margin=(
                required_margin
            ),

            leverage=leverage,
        )

        return RiskEvaluationResult(
            decision=RiskDecision.APPROVE,
            reasons=(),
            plan=plan,
        )

    @staticmethod
    def _reject(
        reasons: list[str],
    ) -> RiskEvaluationResult:
        return RiskEvaluationResult(
            decision=RiskDecision.REJECT,
            reasons=tuple(reasons),
            plan=None,
        )