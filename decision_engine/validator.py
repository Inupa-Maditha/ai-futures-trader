from __future__ import annotations

import re

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)

from config.settings import SYMBOL

from context_engine.market_context import (
    MarketContextSnapshot,
)

from decision_engine.grounding import (
    EvidenceGroundingValidator,
)

from decision_engine.schema import (
    DecisionAction,
    DecisionProposal,
)


@dataclass(
    frozen=True,
    slots=True,
)
class DecisionValidationResult:
    accepted: bool
    reasons: tuple[str, ...]


class DecisionValidator:
    def __init__(
        self,
        max_context_age_seconds: int = 120,
        max_entry_distance_percent: float = 2.0,
    ):
        self.max_context_age_seconds = (
            max_context_age_seconds
        )

        self.max_entry_distance_percent = (
            max_entry_distance_percent
        )

        self.grounding_validator = (
            EvidenceGroundingValidator()
        )

    def validate(
        self,
        proposal: DecisionProposal,
        context: MarketContextSnapshot,
    ) -> DecisionValidationResult:

        reasons: list[str] = []

        # 1. Symbol validation
        if proposal.symbol != SYMBOL:
            reasons.append(
                "Proposal symbol does not "
                "match configured symbol."
            )

        if proposal.symbol != context.symbol:
            reasons.append(
                "Proposal symbol does not "
                "match market context."
            )

        # 2. Health validation
        if not (
            context.health
            .all_required_healthy
        ):
            reasons.append(
                "Required market data "
                "is unhealthy."
            )

        # 3. Context freshness
        age_seconds = (
            datetime.now(timezone.utc)
            - context.generated_at_utc
        ).total_seconds()

        if age_seconds < 0:
            reasons.append(
                "Market context timestamp "
                "is in the future."
            )

        elif (
            age_seconds
            > self.max_context_age_seconds
        ):
            reasons.append(
                "Market context is stale."
            )

        # 4. Grounding validation
        grounding = (
            self.grounding_validator.validate(
                proposal,
                context,
            )
        )

        if not grounding.valid:
            reasons.extend(
                grounding.reasons
            )

        # 5. NO_TRADE requires no
        # additional entry-price checks.
        if (
            proposal.action
            == DecisionAction.NO_TRADE
        ):
            return DecisionValidationResult(
                accepted=(
                    len(reasons) == 0
                ),
                reasons=tuple(reasons),
            )

        # # Trade thesis must not reference
        # # EMA evidence unless an EMA item
        # # was actually selected.
        # thesis_lower = (
        #     proposal.thesis.lower()
        # )

        # selected_paths = {
        #     item.context_path
        #     for item in proposal.evidence
        # }

        # selected_has_ema = any(
        #     ".ema_" in path
        #     for path in selected_paths
        # )

        # if (
        #     "ema" in thesis_lower
        #     and not selected_has_ema
        # ):
        #     reasons.append(
        #         "Thesis references EMA evidence "
        #         "that was not selected."
        #     )

        # 6. Trade invalidation must reference
        # the proposed stop-loss price.
        invalidation = (
            proposal.invalidation_reason
            or ""
        )

        numeric_values = re.findall(
            r"\d[\d,]*(?:\.\d+)?",
            invalidation,
        )

        stop_loss = float(
            proposal.stop_loss
        )

        references_stop_loss = any(
            abs(
                float(
                    value.replace(",", "")
                )
                - stop_loss
            )
            < 1e-8
            for value in numeric_values
        )

        if not references_stop_loss:
            reasons.append(
                "Invalidation reason must reference "
                "the proposed stop loss."
            )

        # 7. Entry sanity check
        mid_price = (
            context.orderbook.mid_price
        )

        if mid_price <= 0:
            reasons.append(
                "Invalid market mid-price."
            )

        elif (
            proposal.entry_price
            is not None
        ):
            entry_distance_percent = (
                abs(
                    proposal.entry_price
                    - mid_price
                )
                / mid_price
                * 100
            )

            if (
                entry_distance_percent
                > self
                .max_entry_distance_percent
            ):
                reasons.append(
                    "Proposed entry is too "
                    "far from current market "
                    "price."
                )

        return DecisionValidationResult(
            accepted=(
                len(reasons) == 0
            ),
            reasons=tuple(reasons),
        )