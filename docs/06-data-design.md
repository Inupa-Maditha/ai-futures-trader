# Data Design — AI-Assisted Crypto Futures Trading System

## 1. Purpose

This document defines the main V1 data structures used by:

* Market-data ingestion
* Data-quality validation
* Technical analysis
* Market-structure analysis
* Derivatives analysis
* Order-flow analysis
* LLM reasoning
* Risk validation
* Manual approval
* Demo execution
* Trade journaling
* Performance evaluation

The goal is to make every decision and execution event traceable and reproducible.

---

# 2. General Data Rules

All V1 data shall follow these rules.

### Symbol

V1 supports:

```text
BTCUSDT
```

### Internal Time Standard

All internal timestamps shall use:

```text
UTC
```

### Numeric Precision

Prices and quantities shall not rely on binary floating-point values where execution precision matters.

Execution-facing values should use decimal-safe handling.

### Original Exchange Data

Original exchange timestamps and identifiers shall be preserved whenever available.

They shall not be overwritten by locally generated timestamps.

---

# 3. Core Identifiers

The system shall use separate identifiers for different stages.

```text
snapshot_id
decision_id
intent_id
orderLinkId
order_id
execution_id
trade_id
```

Relationship:

```text
Market Snapshot
      ↓
snapshot_id
      ↓
Decision
      ↓
decision_id
      ↓
Execution Intent
      ↓
intent_id
      ↓
Bybit Client Order ID
      ↓
orderLinkId
      ↓
Bybit Order
      ↓
order_id
      ↓
Executions
      ↓
execution_id
```

---

# 4. Normalized Event

All real-time event adapters should convert exchange data into a normalized internal event structure.

```json
{
  "source": "bybit",
  "environment": "mainnet_public",
  "symbol": "BTCUSDT",
  "event_type": "public_trade",

  "exchange_event_ts_ms": 0,
  "matching_engine_ts_ms": null,
  "local_receive_ts_utc": "",
  "local_receive_monotonic_ns": 0,

  "sequence": null,
  "update_id": null,

  "payload": {}
}
```

Possible `event_type` values:

```text
kline
orderbook_snapshot
orderbook_delta
public_trade
liquidation
open_interest
funding
account_ratio
private_order
private_execution
private_position
```

---

# 5. Candle Schema

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "15m",

  "start_ts_ms": 0,
  "end_ts_ms": 0,

  "open": 0,
  "high": 0,
  "low": 0,
  "close": 0,
  "volume": 0,
  "turnover": 0,

  "confirmed": true,

  "exchange_message_ts_ms": 0,
  "local_receive_ts_utc": ""
}
```

Supported V1 timeframes:

```text
15m
1h
4h
```

Only:

```text
confirmed = true
```

candles may be used for entry-related deterministic analysis.

---

# 6. Technical Indicator Schema

Technical indicators shall be grouped by timeframe.

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "15m",
  "calculated_at_ts_utc": "",

  "source_candle_close_ts_ms": 0,

  "ema": {
    "ema_50": 0,
    "ema_200": 0
  },

  "rsi": {
    "period": 14,
    "value": 0
  },

  "atr": {
    "period": 14,
    "value": 0
  },

  "volume": {
    "current": 0,
    "average": 0,
    "relative_volume": 0
  },

  "valid": true
}
```

The exact indicator parameters shall come from configuration rather than being permanently hard-coded into analysis logic.

---

# 7. Swing Point Schema

```json
{
  "type": "SWING_HIGH",
  "price": 0,
  "timestamp_ms": 0,
  "timeframe": "1h",
  "confirmed": true
}
```

Allowed types:

```text
SWING_HIGH
SWING_LOW
```

---

# 8. Market Structure Schema

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",

  "trend": "BULLISH",
  "regime": "TRENDING",

  "last_structure_event": "HIGHER_HIGH",

  "swing_highs": [],
  "swing_lows": [],

  "nearest_support": {
    "low": 0,
    "high": 0
  },

  "nearest_resistance": {
    "low": 0,
    "high": 0
  },

  "source_candle_close_ts_ms": 0,
  "calculated_at_ts_utc": "",

  "valid": true
}
```

Suggested structure labels:

```text
HIGHER_HIGH
HIGHER_LOW
LOWER_HIGH
LOWER_LOW
NONE
```

Suggested trend labels:

```text
BULLISH
BEARISH
NEUTRAL
UNKNOWN
```

Suggested regime labels:

```text
TRENDING
RANGING
HIGH_VOLATILITY
LOW_VOLATILITY
UNCERTAIN
```

---

# 9. Open Interest Schema

```json
{
  "symbol": "BTCUSDT",

  "value": 0,
  "change_absolute": 0,
  "change_percent": 0,

  "observation_ts_ms": 0,
  "local_receive_ts_utc": "",

  "health": "HEALTHY"
}
```

---

# 10. Funding Schema

```json
{
  "symbol": "BTCUSDT",

  "funding_rate": 0,
  "funding_ts_ms": 0,

  "funding_interval_minutes": 0,

  "local_receive_ts_utc": "",
  "health": "HEALTHY"
}
```

Funding interval shall come from exchange metadata rather than a permanently assumed value.

---

# 11. Account Positioning Schema

The Bybit long/short ratio shall be named precisely to avoid confusing it with long/short notional volume.

```json
{
  "symbol": "BTCUSDT",

  "account_holder_long_ratio": 0,
  "account_holder_short_ratio": 0,

  "observation_ts_ms": 0,
  "period": "15min",

  "local_receive_ts_utc": "",
  "health": "HEALTHY"
}
```

---

# 12. Liquidation Event Schema

```json
{
  "symbol": "BTCUSDT",

  "side": "SELL",
  "quantity": 0,
  "bankruptcy_price": 0,

  "exchange_event_ts_ms": 0,
  "local_receive_ts_utc": ""
}
```

---

# 13. Liquidation Summary Schema

Individual liquidation events may be aggregated into rolling windows.

```json
{
  "symbol": "BTCUSDT",

  "window_seconds": 60,

  "long_liquidation_volume": 0,
  "short_liquidation_volume": 0,
  "total_liquidation_volume": 0,

  "event_count": 0,

  "window_start_ts_utc": "",
  "window_end_ts_utc": "",

  "health": "HEALTHY"
}
```

---

# 14. Order Book Level Schema

```json
{
  "price": 0,
  "quantity": 0
}
```

---

# 15. Order Book State Schema

```json
{
  "symbol": "BTCUSDT",

  "depth": 50,

  "bids": [],
  "asks": [],

  "exchange_ts_ms": 0,
  "matching_engine_ts_ms": 0,

  "update_id": 0,
  "sequence": 0,

  "local_receive_ts_utc": "",

  "health": "HEALTHY"
}
```

The book shall not be considered usable unless:

```text
health = HEALTHY
```

---

# 16. Public Trade Schema

```json
{
  "symbol": "BTCUSDT",

  "trade_id": "",
  "side": "Buy",

  "price": 0,
  "quantity": 0,

  "exchange_event_ts_ms": 0,
  "sequence": 0,

  "local_receive_ts_utc": ""
}
```

The exchange-provided taker side shall be preserved.

---

# 17. Order Flow Feature Schema

```json
{
  "symbol": "BTCUSDT",

  "calculated_at_ts_utc": "",

  "spread": 0,
  "spread_bps": 0,

  "book_imbalance": {
    "top_5": 0,
    "top_10": 0,
    "top_25": 0,
    "top_50": 0
  },

  "trade_flow": {
    "window_seconds": 60,
    "aggressive_buy_volume": 0,
    "aggressive_sell_volume": 0,
    "signed_volume_imbalance": 0
  },

  "liquidity": {
    "bid_depth": 0,
    "ask_depth": 0,
    "imbalance_persistence": 0
  },

  "health": "HEALTHY"
}
```

---

# 18. Data Health Schema

Each critical source shall expose a common health object.

```json
{
  "source_name": "orderbook",

  "status": "HEALTHY",

  "last_exchange_event_ts_ms": 0,
  "last_local_receive_ts_utc": "",

  "age_ms": 0,

  "connection_ok": true,
  "sequence_ok": true,

  "reason": null
}
```

Allowed states:

```text
HEALTHY
DEGRADED
STALE
UNKNOWN
```

---

# 19. Multi-Timeframe Context Schema

```json
{
  "4h": {
    "indicators": {},
    "structure": {}
  },

  "1h": {
    "indicators": {},
    "structure": {}
  },

  "15m": {
    "indicators": {},
    "structure": {},
    "setup": {}
  }
}
```

---

# 20. Structured Market Snapshot

This is the main object passed to the LLM.

```json
{
  "snapshot_id": "",
  "symbol": "BTCUSDT",

  "created_at_ts_utc": "",

  "data_quality": {
    "critical_ok": true,
    "sources": {}
  },

  "market_context": {
    "regime": "",
    "higher_timeframe_trend": "",
    "key_levels": []
  },

  "timeframes": {
    "4h": {},
    "1h": {},
    "15m": {}
  },

  "derivatives": {
    "open_interest": {},
    "funding": {},
    "account_positioning": {},
    "liquidations": {}
  },

  "order_flow": {},

  "volatility": {},

  "feature_version": "",
  "strategy_version": ""
}
```

A snapshot is immutable after creation.

If market state changes materially, a new snapshot shall be created rather than modifying an existing decision snapshot.

---

# 21. LLM Request Metadata

Every LLM call shall be associated with:

```json
{
  "snapshot_id": "",

  "provider": "",
  "model": "",

  "prompt_version": "",
  "schema_version": "",

  "request_ts_utc": "",

  "snapshot_hash": ""
}
```

---

# 22. LLM Proposal Schema

```json
{
  "decision": "NO_TRADE",

  "setup_quality": 0,

  "supporting_evidence": [],
  "contradicting_evidence": [],

  "entry": null,
  "stop_loss": null,
  "take_profit": null,

  "reasoning": "",
  "invalidation": "",

  "assumptions": []
}
```

Allowed decisions:

```text
LONG
SHORT
NO_TRADE
```

Suggested setup-quality range:

```text
0–100
```

This value is not a win probability.

---

# 23. LLM Validation Result

```json
{
  "json_parse_ok": true,
  "schema_valid": true,
  "semantic_valid": true,

  "errors": [],

  "retry_count": 0,

  "final_status": "ACCEPTED"
}
```

Possible final status:

```text
ACCEPTED
REJECTED
```

---

# 24. Validated Trade Proposal

Only schema-valid and semantically-valid proposals become this object.

```json
{
  "decision_id": "",
  "snapshot_id": "",

  "symbol": "BTCUSDT",
  "direction": "LONG",

  "entry": 0,
  "stop_loss": 0,
  "take_profit": 0,

  "setup_quality": 0,

  "created_at_ts_utc": "",
  "expires_at_ts_utc": ""
}
```

---

# 25. Risk Configuration Schema

```json
{
  "risk_config_version": "",

  "max_positions": 1,
  "max_active_entry_intents": 1,

  "risk_per_trade": 0,
  "minimum_reward_to_risk": 0,

  "daily_max_loss": 0,

  "allow_martingale": false,
  "allow_averaging_down": false,
  "allow_pyramiding": false,

  "require_stop_loss": true
}
```

Risk values shall be configuration values, not LLM outputs.

---

# 26. Risk Evaluation Result

```json
{
  "decision_id": "",

  "approved": false,

  "reason_codes": [],

  "calculated_position_size": 0,

  "risk_amount": 0,
  "risk_fraction": 0,

  "reward_to_risk": 0,

  "evaluated_at_ts_utc": "",

  "risk_config_version": ""
}
```

Example rejection codes:

```text
MARKET_DATA_STALE
ORDERBOOK_INVALID
STOP_LOSS_MISSING
INVALID_PRICE_GEOMETRY
RR_BELOW_MINIMUM
DAILY_LOSS_LIMIT
EXISTING_POSITION
EXISTING_ENTRY_ORDER
INVALID_QUANTITY
ACCOUNT_STATE_UNKNOWN
```

---

# 27. Approval Record

```json
{
  "decision_id": "",
  "intent_id": "",

  "approved": true,

  "approval_ts_utc": "",
  "expires_at_ts_utc": "",

  "approval_status": "VALID"
}
```

Possible status:

```text
VALID
REJECTED
EXPIRED
INVALIDATED
```

---

# 28. Execution Intent

The execution intent must be persisted before sending an order.

```json
{
  "intent_id": "",
  "decision_id": "",

  "symbol": "BTCUSDT",
  "direction": "LONG",

  "entry": 0,
  "stop_loss": 0,
  "take_profit": 0,
  "quantity": 0,

  "order_link_id": "",

  "created_at_ts_utc": "",

  "state": "HUMAN_APPROVED"
}
```

---

# 29. Execution State Schema

```json
{
  "intent_id": "",

  "current_state": "SUBMITTING",
  "previous_state": "FINAL_PREFLIGHT",

  "state_changed_at_ts_utc": "",

  "reason": null,

  "order_link_id": "",
  "order_id": null
}
```

Allowed major states:

```text
IDLE
CANDIDATE
LLM_PROPOSED
RISK_APPROVED
AWAITING_HUMAN
HUMAN_APPROVED
FINAL_PREFLIGHT
SUBMITTING
RECONCILING
WORKING
POSITION_OPEN
PROTECTION_VERIFIED
EXITING
CLOSED

NO_TRADE
USER_REJECTED
APPROVAL_EXPIRED
EXECUTION_BLOCKED
EXECUTION_RISK
CANCELLED
```

---

# 30. Order Record

```json
{
  "intent_id": "",

  "order_link_id": "",
  "order_id": "",

  "symbol": "BTCUSDT",

  "side": "Buy",
  "order_type": "Market",

  "requested_quantity": 0,
  "filled_quantity": 0,

  "average_fill_price": null,

  "order_status": "",

  "submitted_at_ts_utc": "",
  "last_update_ts_utc": ""
}
```

---

# 31. Execution Event

One order may generate multiple execution events.

```json
{
  "execution_id": "",
  "order_id": "",
  "order_link_id": "",

  "price": 0,
  "quantity": 0,

  "fee": 0,

  "execution_ts_ms": 0,
  "local_receive_ts_utc": ""
}
```

---

# 32. Position State

```json
{
  "symbol": "BTCUSDT",

  "side": "LONG",

  "quantity": 0,
  "average_entry_price": 0,

  "unrealized_pnl": 0,
  "realized_pnl": 0,

  "stop_loss": null,
  "take_profit": null,

  "protection_verified": false,

  "updated_at_ts_utc": ""
}
```

---

# 33. Trade Journal Record

A completed trade shall produce a durable summary record.

```json
{
  "trade_id": "",

  "decision_id": "",
  "snapshot_id": "",
  "intent_id": "",

  "order_link_id": "",
  "order_id": "",

  "symbol": "BTCUSDT",
  "direction": "LONG",

  "entry_price": 0,
  "stop_loss": 0,
  "take_profit": 0,

  "quantity": 0,

  "exit_price": 0,

  "gross_pnl": 0,
  "fees": 0,
  "net_pnl": 0,

  "risk_amount": 0,
  "planned_reward_to_risk": 0,
  "realized_r": 0,

  "outcome": "WIN",

  "opened_at_ts_utc": "",
  "closed_at_ts_utc": "",

  "market_regime": "",
  "setup_type": "",

  "strategy_version": "",
  "feature_version": "",
  "prompt_version": "",
  "risk_config_version": ""
}
```

Outcome values may include:

```text
WIN
LOSS
BREAKEVEN
```

---

# 34. Decision Journal Record

Every decision shall be logged, including NO_TRADE decisions.

```json
{
  "decision_id": "",
  "snapshot_id": "",

  "timestamp_utc": "",

  "llm_decision": "NO_TRADE",
  "setup_quality": 0,

  "schema_valid": true,
  "semantic_valid": true,

  "risk_approved": false,
  "risk_reasons": [],

  "human_approval": null,

  "executed": false,

  "final_result": "NO_TRADE",

  "strategy_version": "",
  "feature_version": "",
  "prompt_version": "",
  "model_identifier": "",
  "risk_config_version": ""
}
```

Logging NO_TRADE decisions is important because otherwise evaluation would contain only selected executed trades.

---

# 35. Data Storage Strategy

V1 shall use:

```text
CSV
JSON
JSONL
```

Use CSV primarily for:

```text
Completed trade journal
Performance tables
Metrics
Simple historical series
```

Use JSON/JSONL primarily for:

```text
Structured market snapshots
LLM input/output
Risk evaluations
Execution events
System events
Nested market context
```

---

# 36. Recommended Data Directory

```text
data/
│
├── market/
│   ├── candles/
│   ├── trades/
│   ├── orderbook/
│   ├── liquidations/
│   └── derivatives/
│
├── snapshots/
│
├── decisions/
│
├── executions/
│
└── journal/
```

Runtime diagnostic logs:

```text
logs/
├── system/
├── errors/
└── execution/
```

---

# 37. Suggested File Naming

Examples:

```text
candles_BTCUSDT_15m_2026-09.csv

public_trades_BTCUSDT_2026-09-21.jsonl

liquidations_BTCUSDT_2026-09-21.jsonl

market_snapshots_2026-09-21.jsonl

decisions_2026-09-21.jsonl

execution_events_2026-09-21.jsonl

trades.csv
```

---

# 38. Versioning Fields

The following versions shall be stored where relevant:

```text
strategy_version
feature_version
prompt_version
schema_version
risk_config_version
```

Changing trading logic during a test cohort shall require a version change.

---

# 39. Snapshot Immutability

Once a decision is generated from a market snapshot:

```text
snapshot_id = X
```

that snapshot shall not later be modified to represent newer market conditions.

A new market condition creates:

```text
snapshot_id = Y
```

This is required for auditability.

---

# 40. Data Retention

Local trading research records shall not depend on Bybit's Demo history retention.

The project shall retain locally:

```text
Decisions
Execution intents
Orders
Executions
Market snapshots
Trade outcomes
```

for the duration of the V1 research period.

---

# 41. Secret Exclusion

No stored schema may intentionally include:

```text
API secret
API key
LLM API key
Authentication signature
Password
Bearer token
```

Authentication data shall never be written into market, decision, execution, or journal files.

---

# 42. Evaluation Support

The data design must allow calculation of:

```text
Win rate
Profit factor
Average win
Average loss
Expectancy
Expectancy in R
Maximum drawdown
Consecutive losses
Total PnL
Realized R
Long vs short performance
Setup performance
Market-regime performance
```

It must also allow technical evaluation of:

```text
LLM schema failures
Semantic validation failures
Risk rejections
Stale-data rejections
Reconnect events
Duplicate execution prevention
Slippage
Execution latency
Protection failures
```

---

# 43. Traceability Chain

Every executed trade should be traceable through:

```text
trade_id
   ↓
order_id
   ↓
orderLinkId
   ↓
intent_id
   ↓
decision_id
   ↓
snapshot_id
```

This allows the system to answer:

```text
What market data caused this decision?

What did the LLM propose?

What did validation accept or reject?

What did the risk engine calculate?

What did the human approve?

What exactly was submitted?

What happened on the exchange?

What was the final outcome?
```

---

# 44. Data Design Invariants

The following rules shall always hold:

```text
Every decision has a decision_id.

Every LLM decision references a snapshot_id.

Every execution references a validated decision.

Every order attempt has a persistent intent_id.

Every Bybit submission has a unique orderLinkId.

Every executed trade is journaled.

NO_TRADE decisions are also logged.

Original exchange timestamps are preserved.

Secrets are never stored in research data.

Historical records are not silently rewritten.
```

---

# 45. Final Data Flow

```text
RAW BYBIT EVENTS
       ↓
NORMALIZED EVENTS
       ↓
HEALTH VALIDATION
       ↓
FEATURE OBJECTS
       ↓
MARKET STRUCTURE
DERIVATIVES
ORDER FLOW
       ↓
MARKET SNAPSHOT
       ↓
LLM PROPOSAL
       ↓
VALIDATION RESULT
       ↓
RISK RESULT
       ↓
APPROVAL RECORD
       ↓
EXECUTION INTENT
       ↓
ORDER / EXECUTION EVENTS
       ↓
POSITION STATE
       ↓
TRADE JOURNAL
       ↓
PERFORMANCE METRICS
```

This schema design is the V1 contract between system modules.

---

# 39. Phase 15 Persistence / Evaluation Implementation Note

The implemented V1 journal uses:

```text
JSONL = source of truth
CSV   = human-readable mirror
```

Journal lifecycle event types include:

```text
RUN_STARTED
MARKET_CONTEXT
DECISION
RISK_RESULT
MANUAL_APPROVAL
EXECUTION_RESULT
TRADE_OUTCOME
ERROR
RUN_FINISHED
```

Common terminal statuses include:

```text
NO_TRADE
DECISION_REJECTED
RISK_REJECTED
DEMO_EXECUTION_DISABLED
MANUALLY_REJECTED
EXECUTION_UNCERTAIN
DEMO_ORDER_CONFIRMED
UNHANDLED_ERROR
PIPELINE_INCOMPLETE
TRADE_OUTCOME_RECORDED
```

The evaluation layer supports:

- Closed-trade PnL metrics
- Win / loss / breakeven counts
- Win rate
- Profit factor
- Expectancy
- Average R
- Best / worst R
- Maximum drawdown
- Maximum consecutive losses
- System / pipeline metrics
- Equity-curve export

The journal is the durable local research record and must not contain API credentials or authentication secrets.
