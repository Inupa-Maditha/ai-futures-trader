from __future__ import annotations

from approval.gate import (
    ManualApprovalGate,
)

from approval.schema import (
    ManualApprovalDecision,
    ManualApprovalRequest,
    ManualApprovalResult,
)


class ConsoleManualApprover:
    def __init__(
        self,
        gate: ManualApprovalGate,
    ):
        self.gate = gate

    def ask(
        self,
        request:
        ManualApprovalRequest,
    ) -> ManualApprovalResult:

        plan = request.risk_plan

        print(
            "\n"
            "===================================="
        )

        print(
            "MANUAL TRADE APPROVAL REQUIRED"
        )

        print(
            "===================================="
        )

        print(
            f"Approval ID: "
            f"{request.approval_id}"
        )

        print(
            f"Symbol: {plan.symbol}"
        )

        print(
            f"Side: {plan.side.value}"
        )

        print(
            f"Entry: {plan.entry_price}"
        )

        print(
            f"Stop Loss: {plan.stop_loss}"
        )

        print(
            f"Take Profit: "
            f"{plan.take_profit}"
        )

        print(
            f"Quantity: "
            f"{plan.executable_quantity} BTC"
        )

        print(
            f"Risk Budget: "
            f"{plan.risk_amount}"
        )

        print(
            f"Actual Risk: "
            f"{plan.actual_risk_amount}"
        )

        print(
            f"Reward/Risk: "
            f"{plan.reward_risk_ratio}"
        )

        print(
            f"Leverage: "
            f"{plan.leverage}x"
        )

        print(
            "===================================="
        )

        print(
            "Type APPROVE to continue."
        )

        print(
            "Anything else = REJECT."
        )

        user_input = input(
            "> "
        ).strip().upper()

        if user_input == "APPROVE":
            decision = (
                ManualApprovalDecision
                .APPROVE
            )

        else:
            decision = (
                ManualApprovalDecision
                .REJECT
            )

        return self.gate.record_decision(
            request=request,
            decision=decision,
        )