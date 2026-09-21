# V1 Development Sprint Plan

## 1. Purpose

This document defines the implementation order for V1 of the AI-Assisted Crypto Futures Trading System.

Development will be divided into six major sprints.

Each sprint must be testable independently before moving to the next one.

---

# Sprint 1 — Market Data Pipeline

## Goal

Build a reliable BTCUSDT market-data layer using Bybit mainnet public APIs.

## Build

### REST

* Historical 15m candles
* Historical 1H candles
* Historical 4H candles
* Open Interest
* Funding rate
* Account-holder long/short ratio
* Instrument information

### WebSocket

* Live klines
* L50 order book
* Public trades
* Liquidations

### Data handling

* Normalized event structures
* UTC timestamps
* Exchange timestamps
* Local receive timestamps
* Sequence/update IDs
* Closed-candle validation

### Reliability

Implement:

* Connection health
* Freshness checks
* WebSocket heartbeat
* Reconnect logic
* Order-book rebuild
* Duplicate-event handling
* Stale-data detection

### Recording

Store selected live data:

* Public trades
* Liquidations
* Order-book data

using JSONL or other suitable local format.

## Tests

* REST response tests
* Candle parsing
* Closed-candle validation
* Timestamp conversion
* Order-book snapshot handling
* Order-book delta handling
* Reconnect simulation
* Stale-data detection
* Duplicate-event handling

## Definition of Done

Sprint 1 is complete when:

* 15m / 1H / 4H candles load correctly
* Only confirmed candles are accepted for analysis
* L50 order book is maintained locally
* Public trades stream reliably
* Liquidations stream reliably
* OI / funding / positioning are available
* Data-health states work
* Reconnect restores valid state
* Invalid/stale data cannot be consumed as healthy data
* Raw/normalized microstructure recording works

---

# Sprint 2 — Technical Analysis and Market Structure

## Goal

Convert validated market data into deterministic analytical features.

## Build

### Indicators

* EMA
* RSI
* ATR
* Volume metrics
* Basic volatility metrics

### Market structure

* Swing highs
* Swing lows
* Higher High
* Higher Low
* Lower High
* Lower Low
* Basic trend state
* Support zones
* Resistance zones
* Basic regime classification

## Multi-Timeframe Roles

### 4H

Primary higher-timeframe context.

### 1H

Market structure.

### 15m

Entry/setup timeframe.

## Tests

* Indicator fixtures
* Indicator comparison against reference calculations
* Insufficient warm-up data
* Missing candles
* Duplicate candles
* Flat prices
* Extreme candles
* Swing detection
* Structure transitions
* Support/resistance generation

## Definition of Done

Sprint 2 is complete when:

* Indicators calculate consistently
* Calculations use closed candles only
* Indicator values are independently verified
* Structure engine identifies deterministic swing states
* 4H / 1H / 15m analysis objects can be produced
* Invalid source data produces invalid analysis state

---

# Sprint 3 — Context and Hybrid Decision Engine

## Goal

Build the structured market-context pipeline and bounded LLM analyst.

## Build

### Context Engine

Organize analysis into:

```text
CONTEXT
├── Market regime
├── 4H trend
├── 1H structure
└── Key levels

SETUP
├── 15m setup
├── Volatility
└── Potential reward/risk

CONFIRMATION
├── Open Interest
├── Funding
├── Account positioning
├── Liquidations
├── Trade flow
└── Order-book context
```

### Market Snapshot

Create immutable structured snapshots containing:

* Snapshot ID
* Data-health state
* Multi-timeframe context
* Derivatives context
* Order-flow features
* Feature version
* Strategy version

### LLM Interface

LLM receives structured snapshot only.

Expected proposal:

* LONG
* SHORT
* NO_TRADE
* Setup quality
* Supporting evidence
* Contradicting evidence
* Proposed entry
* Proposed Stop Loss
* Proposed Take Profit
* Reasoning
* Invalidation

### Validation

Implement:

```text
JSON parsing
      ↓
Schema validation
      ↓
Semantic validation
```

### Failure handling

Invalid LLM response:

```text
One bounded retry
      ↓
Still invalid
      ↓
NO_TRADE
```

## Tests

At least:

* Clear bullish scenario
* Clear bearish scenario
* Range
* Conflicting timeframes
* Stale data
* Missing feature
* Malformed JSON
* Valid JSON with invalid LONG geometry
* Valid JSON with invalid SHORT geometry
* NO_TRADE scenario

## Definition of Done

Sprint 3 is complete when:

* Structured market snapshots are reproducible
* LLM receives no raw uncontrolled feed
* Output schema is enforced
* Semantic validation works
* Invalid LLM output cannot reach risk engine
* All decisions are traceable to snapshot IDs
* NO_TRADE works as a normal output

---

# Sprint 4 — Deterministic Risk Engine

## Goal

Build an independent risk authority.

## Build

### Risk Rules

* Mandatory Stop Loss
* Position sizing
* Configurable risk per trade
* Configurable minimum reward/risk
* Daily maximum-loss guard
* Maximum one BTCUSDT position
* Maximum one active entry intent
* Existing-position check
* Existing-order check
* Stale-data rejection
* Invalid account-state rejection
* Price geometry validation
* Quantity-step validation

### Forbidden V1 Behaviors

* Martingale
* Averaging down
* Automatic pyramiding
* LLM-defined position size
* LLM-defined account risk

### Output

Example:

```json
{
  "approved": false,
  "reason_codes": [
    "RR_BELOW_MINIMUM"
  ]
}
```

## Tests

* Valid LONG
* Valid SHORT
* Bad Stop Loss
* Bad Take Profit
* Poor reward/risk
* Existing position
* Existing entry order
* Daily-loss limit
* Stale data
* Unknown account state
* Quantity rounding
* Extremely tight stop
* Extremely wide stop

## Definition of Done

Sprint 4 is complete when:

* Risk engine functions without LLM
* Every rejection has deterministic reason codes
* Position sizing is deterministic
* No rule violation can proceed to approval
* Risk-engine failure defaults to rejection

---

# Sprint 5 — Manual Approval and Demo Execution

## Goal

Safely execute risk-approved proposals through Bybit Demo.

## Build

### Approval CLI

Display:

* Symbol
* Direction
* Setup quality
* Entry
* Stop Loss
* Take Profit
* Position size
* Risk amount
* Reward/risk
* Supporting evidence
* Contradicting evidence
* Risk verdict

Prompt:

```text
Approve trade? [Y/N]
```

### Approval Controls

* Approval TTL
* Market-movement invalidation
* Rejection handling

### Final Preflight

Check:

* Demo environment
* BTCUSDT
* Fresh market data
* Current account state
* Existing position
* Existing orders
* Price tolerance
* Risk rules
* Approval validity

### Execution

Use:

```text
Bybit Demo REST
```

for:

* Order creation
* Amendment
* Cancellation
* Protection management

### Idempotency

Create:

```text
decision_id
intent_id
orderLinkId
```

before submitting an order.

### State Machine

Implement:

```text
IDLE
↓
CANDIDATE
↓
LLM_PROPOSED
↓
RISK_APPROVED
↓
AWAITING_HUMAN
↓
HUMAN_APPROVED
↓
FINAL_PREFLIGHT
↓
SUBMITTING
↓
WORKING / RECONCILING
↓
POSITION_OPEN
↓
PROTECTION_VERIFIED
↓
EXITING
↓
CLOSED
```

### Execution Monitoring

Use:

* Demo private WebSocket
* REST reconciliation

### Protection

Verify exchange-side Stop Loss.

No position is considered safely established until protection is confirmed.

## Tests

* User approves
* User rejects
* Approval expires
* Market moves after approval
* Market order
* Limit order
* Cancel
* Amend
* REST timeout
* Reconciliation
* Duplicate-submit prevention
* WebSocket disconnect
* Program restart with existing position
* Protection verification failure

## Definition of Done

Sprint 5 is complete when:

* User approval is mandatory
* Rejected trades never execute
* Expired approvals cannot execute
* Duplicate submission is prevented
* Orders appear in Bybit Demo
* Execution state is reconciled
* Existing positions survive application restart correctly
* Exchange-side protection is verified

---

# Sprint 6 — Journaling and Evaluation

## Goal

Make every decision and execution auditable and measurable.

## Build

### Decision Journal

Log:

* Snapshot ID
* Decision ID
* LLM proposal
* Validation result
* Risk result
* Human decision
* Execution status

Including:

```text
NO_TRADE
```

decisions.

### Execution Journal

Store:

* Intent ID
* orderLinkId
* Bybit order ID
* REST acknowledgement
* WebSocket updates
* Fills
* Fees
* Protection
* Exit

### Trade Journal

Store:

* Entry
* Exit
* Direction
* Quantity
* Stop
* Take Profit
* Gross PnL
* Fees
* Net PnL
* Planned R/R
* Realized R
* Regime
* Setup type
* Versions

### Trading Metrics

Calculate:

* Win rate
* Profit factor
* Average win
* Average loss
* Expectancy
* Expectancy in R
* Maximum drawdown
* Consecutive losses
* Total PnL
* Long vs short
* Setup performance
* Regime performance

### Technical Metrics

Calculate:

* LLM schema failures
* LLM semantic failures
* Risk rejections
* Stale-data rejections
* WebSocket reconnects
* Duplicate submissions prevented
* Fill rate
* Slippage
* Execution latency
* Protection failures

## Tests

* Journal completeness
* CSV correctness
* JSON/JSONL correctness
* Metric calculations using known fixtures
* Recovery from malformed log entry
* Missing-field validation

## Definition of Done

Sprint 6 is complete when:

* Every decision can be reconstructed
* Every executed trade can be reconstructed
* NO_TRADE decisions are retained
* Evaluation metrics calculate correctly
* Technical reliability metrics are available
* No secrets appear in logs

---

# Development Order

The implementation sequence is fixed as:

```text
Sprint 1
Market Data Pipeline
        ↓
Sprint 2
Indicators + Structure
        ↓
Sprint 3
Context + LLM Decision
        ↓
Sprint 4
Risk Engine
        ↓
Sprint 5
Approval + Demo Execution
        ↓
Sprint 6
Journal + Evaluation
```

Do not implement Demo trade execution before deterministic risk validation exists.

---

# Git Branch Strategy

Stable:

```text
main
```

Integration:

```text
dev
```

Feature branches:

```text
feature/data-pipeline
feature/technical-analysis
feature/market-structure
feature/decision-engine
feature/risk-engine
feature/demo-execution
feature/journal
```

Workflow:

```text
feature branch
      ↓
dev
      ↓
tested milestone
      ↓
main
```

---

# V1 Milestones

## M1 — Data Pipeline

Sprint 1 complete.

## M2 — Analysis Engine

Sprint 2 complete.

## M3 — Decision Engine

Sprint 3 complete.

## M4 — Risk Engine

Sprint 4 complete.

## M5 — Demo Execution

Sprint 5 complete.

## M6 — Evaluation

Sprint 6 complete.

---

# Final Development Rule

The system shall be built from the bottom upward:

```text
Reliable Data
      ↓
Reliable Calculations
      ↓
Reliable Context
      ↓
Bounded AI Reasoning
      ↓
Deterministic Risk
      ↓
Controlled Execution
      ↓
Evaluation
```

A later layer shall not compensate for an unreliable earlier layer.
