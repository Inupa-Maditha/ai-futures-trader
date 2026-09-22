from __future__ import annotations

from datetime import datetime

from account_data.bybit_demo import (
    BybitDemoAccountClient,
)

from account_data.closed_pnl import (
    BybitDemoClosedPnlClient,
)

from risk_manager.bridge import (
    AccountRiskState,
)


class DemoRiskStateProvider:
    def __init__(
        self,
        account_client:
        BybitDemoAccountClient,

        closed_pnl_client:
        BybitDemoClosedPnlClient,
    ):
        self.account_client = (
            account_client
        )

        self.closed_pnl_client = (
            closed_pnl_client
        )

    def get_state(
        self,
        symbol: str,
        now_utc: datetime | None = None,
    ) -> AccountRiskState:

        account = (
            self.account_client
            .get_snapshot(
                symbol
            )
        )

        daily_pnl = (
            self.closed_pnl_client
            .get_today_realized_pnl(
                symbol=symbol,
                now_utc=now_utc,
            )
        )

        if daily_pnl.symbol != symbol:
            raise RuntimeError(
                "Daily PnL symbol does "
                "not match requested symbol."
            )

        return AccountRiskState(
            account_equity=(
                account.account_equity
            ),

            available_balance=(
                account.available_balance
            ),

            open_position_count=(
                account
                .open_position_count
            ),

            daily_realized_pnl=(
                daily_pnl.realized_pnl
            ),
        )