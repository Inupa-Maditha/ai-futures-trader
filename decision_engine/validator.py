from __future__ import annotations

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

        # 6. Entry sanity check
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