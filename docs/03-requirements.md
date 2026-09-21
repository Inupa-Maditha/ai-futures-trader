# System Requirements — AI-Assisted Crypto Futures Trading System

## 1. Purpose

This document defines the functional and non-functional requirements for V1 of the AI-Assisted Crypto Futures Trading System.

V1 focuses on:

* BTCUSDT Perpetual only
* Bybit mainnet public market data
* Bybit Demo Trading for execution
* 4H / 1H / 15m analysis
* Hybrid deterministic + LLM decision making
* Independent deterministic risk control
* Manual approval before execution
* Demo-only trading

---

# 2. Functional Requirements

## FR1 — Market Data Acquisition

The system shall obtain BTCUSDT market data from Bybit.

Required data:

* 4H klines
* 1H klines
* 15m klines
* Order book
* Public trades
* Open Interest
* Funding rate
* Account-holder long/short ratio
* Liquidation data

---

## FR2 — Closed Candle Validation

The system shall distinguish between:

* Closed candles
* Currently forming candles

Indicators, market structure, and trade-eligibility logic shall use confirmed closed candles only.

An incomplete candle may be displayed or logged as context but shall not replace the most recent confirmed candle.

---

## FR3 — Historical Bootstrap

At startup, the system shall fetch enough historical candle data to calculate all configured indicators correctly.

The system shall reject analysis if insufficient warm-up data exists.

---

## FR4 — Technical Indicator Calculation

The system shall calculate deterministic technical indicators including:

* EMA
* RSI
* ATR
* Volume-based metrics

Indicator calculations shall be performed locally in Python.

---

## FR5 — Market Structure Analysis

The system shall identify:

* Swing highs
* Swing lows
* Higher Highs
* Higher Lows
* Lower Highs
* Lower Lows
* Trend state
* Support zones
* Resistance zones
* Basic market regime

---

## FR6 — Multi-Timeframe Analysis

The system shall analyze the market using the following hierarchy:

```text
Market Regime
      ↓
4H Higher-Timeframe Context
      ↓
1H Market Structure
      ↓
Key Support / Resistance
      ↓
15m Setup
      ↓
Derivatives Context
      ↓
Order-Flow Context
      ↓
Volatility
      ↓
Risk / Reward
```

The system shall use the most recent valid closed candle for each required timeframe.

---

## FR7 — Derivatives Analysis

The system shall collect and process:

* Open Interest
* Open Interest change
* Funding rate
* Account-holder long ratio
* Account-holder short ratio
* Liquidation activity

These values shall be used as contextual or confirmation features rather than automatically acting as trade signals.

---

## FR8 — Order Book Processing

The system shall maintain a local BTCUSDT order book using:

* Initial snapshot
* WebSocket updates
* Update identifiers
* Sequence information

V1 shall initially use approximately L50 depth.

Order-book depth shall remain configurable for later testing.

If order-book continuity becomes uncertain, the local order-book state shall be marked invalid and rebuilt before trading resumes.

---

## FR9 — Order-Flow Features

The system shall derive basic measurable order-flow features including:

* Bid/ask spread
* Spread in basis points
* Bid/ask depth imbalance
* Aggressive buy volume
* Aggressive sell volume
* Signed trade-volume imbalance
* Nearby liquidity concentration
* Short-window liquidation activity
* Imbalance persistence

The system shall not assume that visible order-book liquidity represents guaranteed future liquidity.

---

## FR10 — Market Data Recording

The system shall locally record selected live microstructure data required for future analysis.

At minimum:

* Public trade events
* Liquidation events
* Normalized order-book state or selected order-book updates

This is required because complete historical microstructure data may not be available later from Bybit.

---

## FR11 — Timestamp Normalization

Every normalized market event shall preserve relevant timestamps.

Where available:

```text
exchange_event_timestamp
matching_engine_timestamp
local_receive_timestamp
sequence
update_id
```

The original exchange timestamp shall never be replaced by the local timestamp.

---

## FR12 — Data Health Monitoring

Each critical data source shall have a health state such as:

```text
HEALTHY
DEGRADED
STALE
UNKNOWN
```

The system shall monitor:

* Stream connection status
* Last update time
* Data age
* Sequence/state validity

If a required critical source is not healthy, the system shall not generate an executable trade proposal.

---

## FR13 — Market Context Generation

The deterministic analysis layer shall generate a structured market-context object containing:

* Data-quality status
* Multi-timeframe state
* Indicators
* Market structure
* Support/resistance
* Derivatives context
* Order-flow features
* Volatility state

The LLM shall receive this structured context instead of uncontrolled raw WebSocket data.

---

## FR14 — LLM Decision Generation

The LLM layer shall be able to propose:

```text
LONG
SHORT
NO_TRADE
```

A proposal may contain:

* Setup-quality assessment
* Reasoning
* Supporting evidence
* Contradicting evidence
* Proposed entry
* Proposed Stop Loss
* Proposed Take Profit
* Invalidation reasoning

The LLM proposal shall not directly cause order execution.

---

## FR15 — Structured LLM Output

LLM responses shall use a predefined structured schema.

The system shall process LLM output through:

```text
LLM Output
     ↓
JSON Parsing
     ↓
Schema Validation
     ↓
Semantic Validation
     ↓
Risk Validation
```

Malformed output shall never be interpreted manually by execution code.

---

## FR16 — LLM Failure Handling

If the LLM returns malformed or schema-invalid output:

1. The system may perform one bounded retry.
2. The replacement output must pass full validation.
3. If validation still fails:

```text
NO_TRADE
```

The system shall not invent missing prices or silently repair economically meaningful values.

---

## FR17 — Trade Geometry Validation

The deterministic validator shall verify price relationships.

For LONG:

```text
stop_loss < entry < take_profit
```

For SHORT:

```text
take_profit < entry < stop_loss
```

The system shall also reject:

* NaN values
* Infinite values
* Invalid tick increments
* Invalid quantities
* Prices outside configured tolerance
* Stale proposals

---

## FR18 — Independent Risk Engine

The risk engine shall operate independently from the LLM.

It shall consume only:

* Validated trade proposal
* Current normalized market state
* Current Demo account state
* Versioned risk configuration

The LLM shall not be able to bypass risk validation.

---

## FR19 — Position Sizing

Position size shall be calculated deterministically.

The system shall use:

* Account equity or configured test balance
* Configured risk budget
* Entry price
* Stop-loss distance
* Instrument quantity step
* Minimum/maximum quantity constraints
* Relevant fee/slippage assumptions

The LLM shall not determine final trade quantity.

---

## FR20 — Risk Controls

The system shall support deterministic controls including:

* Mandatory Stop Loss
* Configurable risk per trade
* Configurable minimum reward-to-risk
* Daily maximum-loss guard
* Maximum one BTCUSDT position
* Maximum one active BTCUSDT entry intent
* Existing-position guard
* Existing-order guard
* No martingale
* No averaging down
* No automatic pyramiding in V1

---

## FR21 — Risk Rejection Output

The risk engine shall return deterministic rejection information.

Example:

```json
{
  "approved": false,
  "reason_codes": [
    "MARKET_DATA_STALE",
    "RR_BELOW_MINIMUM"
  ]
}
```

A risk rejection shall result in:

```text
NO TRADE
```

---

## FR22 — Manual Approval

Every risk-approved trade shall require explicit manual approval.

The CLI shall display at minimum:

* Direction
* Setup quality
* Entry
* Stop Loss
* Take Profit
* Risk
* Reward-to-risk
* Key reasoning
* Contradicting evidence
* Risk-engine verdict

The user shall explicitly choose:

```text
Approve? [Y/N]
```

No trade shall execute without approval.

---

## FR23 — Approval Expiry

Manual approval shall have a configurable validity period.

If the market moves materially, required data becomes stale, account state changes, or the approval expires, the previously approved trade shall not execute.

A new analysis and approval shall be required.

---

## FR24 — Final Pre-Execution Check

Immediately before order submission the system shall verify:

* Environment is Bybit Demo
* Symbol is BTCUSDT
* Market data is healthy
* Account state is readable
* Balance/state is valid
* No unexpected BTCUSDT position exists
* No conflicting order exists
* Proposed prices remain within tolerance
* Risk rules still pass
* Approval is still valid

If any check fails, execution shall be rejected.

---

## FR25 — Demo-Only Execution

Authenticated execution shall use Bybit Demo Trading only.

V1 shall not contain authenticated production trading credentials.

The execution client shall be explicitly tied to the Demo environment.

---

## FR26 — Order Submission

Approved orders shall be submitted using Bybit Demo REST.

The system shall support V1-required order operations such as:

* Create
* Amend
* Cancel
* Query
* Position retrieval
* Execution retrieval
* Stop-loss / take-profit management

---

## FR27 — Idempotent Order Submission

Every local trade intent shall have a unique identifier.

The system shall use a unique Bybit `orderLinkId` or equivalent identifier for order reconciliation.

On submission timeout:

```text
DO NOT immediately retry
        ↓
Reconcile order state
        ↓
Retry only if conclusively absent
```

This requirement exists to reduce duplicate execution risk.

---

## FR28 — Execution State Machine

Order execution shall be represented as explicit states.

Example:

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

Unexpected state transitions shall not be silently ignored.

---

## FR29 — Execution Confirmation

REST acknowledgement shall not be treated as final order confirmation.

The system shall use:

* Demo private WebSocket
* REST reconciliation where required

to determine actual order and execution state.

---

## FR30 — Exchange-Side Protection

Every executed trade shall have exchange-side Stop Loss protection.

The system shall verify that protective state actually exists.

If protection cannot be verified after entry, the system shall enter an execution-risk state and prevent new entries.

---

## FR31 — WebSocket Recovery

If a WebSocket connection is lost:

1. Mark relevant data unhealthy.
2. Prevent new trade execution.
3. Reconnect using bounded retry/backoff.
4. Rebuild required state.
5. Restore rolling feature windows.
6. Verify freshness/sequence health.
7. Resume trading only after state is healthy.

---

## FR32 — Startup Recovery

When the program starts, it shall first retrieve and reconcile:

* Existing Demo positions
* Existing open orders
* Protective orders where relevant
* Account state

The system shall not assume that no position exists merely because local memory is empty.

---

## FR33 — Trade Journal

Every decision shall be recorded.

Minimum fields:

* Decision ID
* Timestamp
* Direction
* Entry
* Stop Loss
* Take Profit
* Risk
* Reward-to-risk
* Market conditions
* LLM reasoning
* LLM output
* Risk verdict
* Approval status
* Execution result
* Order ID
* Strategy version
* Feature version
* Prompt version
* Data-health status

---

## FR34 — Execution Event Logging

The system shall log enough execution information to reconstruct the order lifecycle.

Examples:

* Intent created
* Request submitted
* REST acknowledgement
* WebSocket order updates
* Execution events
* Amend/cancel events
* Protection state
* Final closure

Secrets shall not be logged.

---

## FR35 — Evaluation Metrics

The system shall calculate trading metrics including:

* Win rate
* Profit factor
* Average win
* Average loss
* Expectancy
* Expectancy in R
* Maximum drawdown
* Consecutive losses
* Total PnL
* Realized R distribution
* Long vs short performance
* Setup-type performance
* Market-regime performance

---

## FR36 — Technical Reliability Metrics

The system shall also record software-quality metrics such as:

* Order submission success rate
* Order rejection rate
* Fill rate
* Partial-fill rate
* Slippage
* Approval-to-submit latency
* Submit-to-ack latency
* Ack-to-fill latency
* WebSocket reconnect count
* Stale-data NO_TRADE count
* LLM schema-failure count
* LLM semantic-rejection count
* Risk-engine rejection reasons
* Duplicate-submit attempts prevented
* Protection-verification failures

---

# 3. Non-Functional Requirements

## NFR1 — Fail-Safe Operation

When a critical prerequisite is uncertain:

```text
NO TRADE
```

Missed trades are acceptable.

Uncertain or uncontrolled execution is not acceptable.

---

## NFR2 — Traceability

Every trade decision shall be traceable from:

```text
Raw / normalized data
        ↓
Features
        ↓
Market context
        ↓
LLM proposal
        ↓
Validation
        ↓
Risk decision
        ↓
Human approval
        ↓
Execution
```

---

## NFR3 — Reproducibility

Every decision shall record version identifiers where applicable:

* Strategy version
* Feature-engine version
* Prompt version
* LLM model/provider identifier
* Schema version
* Risk configuration version

---

## NFR4 — Deterministic Risk Control

Risk-management behavior shall remain deterministic and independent of LLM output.

The LLM shall never have permission to override risk limits.

---

## NFR5 — Data Freshness

Every critical feed shall have configurable freshness rules.

The system shall reject decisions based on stale or uncertain data.

---

## NFR6 — Time Synchronization

The execution machine shall maintain synchronized system time.

Clock-health failure shall disable authenticated execution until resolved.

---

## NFR7 — Data Integrity

The system shall preserve:

* Original exchange timestamps
* Event identifiers
* Sequence information
* Update identifiers where available

Duplicate or uncertain events shall not silently corrupt state.

---

## NFR8 — Connection Resilience

Temporary API or WebSocket failures shall not produce:

* Duplicate trades
* Invalid order-book state
* Incorrect account state
* New trades during uncertain recovery

---

## NFR9 — Security

Secrets shall never be committed to Git.

The following shall remain outside version control:

```text
.env
API keys
API secrets
LLM API keys
authentication signatures
tokens
passwords
```

Logs shall redact authentication information.

---

## NFR10 — Demo Isolation

V1 shall not provide a simple runtime switch from Demo Trading to live authenticated trading.

Moving to production trading shall require a future design and code change.

---

## NFR11 — Maintainability

Major responsibilities shall be separated into modules.

Examples:

* Market data
* Indicators
* Market structure
* Derivatives
* Order flow
* Decision engine
* LLM interface
* Validation
* Risk manager
* Execution
* Journal

---

## NFR12 — Testability

Deterministic modules shall be testable without network access.

Critical logic shall support unit tests using saved fixtures.

---

## NFR13 — Observability

Failures and state transitions shall produce understandable logs.

Examples:

```text
MARKET_DATA_STALE
ORDERBOOK_INVALID
LLM_SCHEMA_FAILURE
RISK_REJECTED
APPROVAL_EXPIRED
ORDER_STATE_UNCERTAIN
PROTECTION_NOT_VERIFIED
```

---

## NFR14 — Performance

The V1 system shall process BTCUSDT data fast enough that analysis is based on current data under normal operating conditions.

V1 is not intended to be a high-frequency trading system.

---

## NFR15 — Minimal Infrastructure

V1 shall run locally and shall not require:

* Cloud deployment
* Kubernetes
* PostgreSQL
* Distributed services
* Web dashboard

Infrastructure complexity shall not be added unless it solves a demonstrated V1 requirement.

---

# 4. Global Safety Invariant

The most important system rule is:

```text
Any uncertainty in a critical prerequisite
                ↓
             NO TRADE
```

Examples include:

* Stale data
* Broken order-book state
* WebSocket recovery in progress
* Invalid LLM output
* Invalid trade geometry
* Risk-rule failure
* Unknown Demo account state
* Unexpected open position
* Duplicate-order uncertainty
* Expired human approval
* Unverified exchange-side protection

---

# 5. V1 Authority Model

```text
MARKET DATA
      ↓
DETERMINISTIC ANALYSIS
      ↓
LLM PROPOSAL
      ↓
SCHEMA / SEMANTIC VALIDATION
      ↓
DETERMINISTIC RISK ENGINE
      ↓
MANUAL APPROVAL
      ↓
FINAL PREFLIGHT
      ↓
BYBIT DEMO EXECUTION
```

Authority:

```text
LLM
    → may propose

Risk Engine
    → may reject

Human
    → may approve a risk-approved proposal

Execution Layer
    → may execute only after all required checks pass
```

Neither the LLM nor the human approval step may override a deterministic risk rejection.
