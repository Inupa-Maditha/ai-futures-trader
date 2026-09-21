INITIAL_HEALTH_POLICIES = {
    "orderbook": {
        "stale_after_seconds": 5,
        "event_required": True,
    },

    "public_trades": {
        "stale_after_seconds": 5,
        "event_required": True,
    },

    "kline_15m": {
        "stale_after_seconds": 75,
        "event_required": True,
    },

    "kline_1h": {
        "stale_after_seconds": 75,
        "event_required": True,
    },

    "kline_4h": {
        "stale_after_seconds": 75,
        "event_required": True,
    },

    # No liquidation event occurring is normal.
    # Connection health matters more than event age.
    "liquidations": {
        "stale_after_seconds": 0,
        "event_required": False,
    },

    "open_interest": {
        "stale_after_seconds": 20 * 60,
        "event_required": True,
    },

    "funding": {
        "stale_after_seconds": 5 * 60,
        "event_required": True,
    },

    "account_positioning": {
        "stale_after_seconds": 20 * 60,
        "event_required": True,
    },
}