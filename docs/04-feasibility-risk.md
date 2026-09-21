# Feasibility and Risk Assessment

## 1. Purpose

This document evaluates whether the proposed V1 AI-Assisted Crypto Futures Trading System is technically practical and identifies the major engineering risks that must be controlled before development and testing.

---

# 2. Feasibility Summary

## Overall Result

**V1 is technically feasible.**

The required architecture can be implemented using:

* Python
* Bybit V5 public REST/WebSocket APIs
* Bybit Demo Trading REST API
* Bybit Demo private WebSocket
* Local deterministic analysis
* LLM-assisted reasoning
* Deterministic risk management
* CSV / JSON storage

No major technical limitation currently blocks V1 development.

---

# 3. Market Data Feasibility

Bybit provides the primary data required for V1:

* 15m candles
* 1H candles
* 4H candles
* Order book
* Public trades
* Open Interest
* Funding
* Long/Short account-holder ratio
* Liquidations

Therefore, an external paid market-data provider is not required for V1.

However, historical microstructure data is more limited than live data.

For that reason, V1 should record selected live data locally from the beginning.

Important streams to preserve include:

* Public trades
* Liquidations
* Order-book information

---

# 4. Execution Feasibility

Bybit Demo Trading supports the core functionality required for V1, including:

* Order creation
* Order amendment
* Order cancellation
* Order history
* Execution history
* Position information
* Stop Loss / Take Profit handling
* Private WebSocket updates

V1 shall use:

```text
Mainnet Public Market Data
        ↓
Analysis
        ↓
Decision
        ↓
Risk Validation
        ↓
Manual Approval
        ↓
Bybit Demo REST Execution
        ↓
Demo Private WebSocket Monitoring
```

WebSocket order entry is not required for V1.

REST shall be used for order submission.

---

# 5. AI Feasibility

A pure LLM trading controller is not appropriate.

The selected hybrid architecture is technically practical:

```text
Raw Market Data
        ↓
Deterministic Processing
        ↓
Structured Market Context
        ↓
LLM Proposal
        ↓
Schema Validation
        ↓
Semantic Validation
        ↓
Deterministic Risk Engine
        ↓
Manual Approval
```

The LLM remains a bounded analysis component.

It does not control:

* Final position size
* Risk limits
* Order execution
* Environment selection
* Risk rejection

---

# 6. Local Execution Feasibility

The V1 system can run locally without:

* Docker
* Kubernetes
* Cloud deployment
* PostgreSQL
* Distributed services
* Web dashboard

A single local Python application is sufficient for the planned V1 scope.

---

# 7. Technical Feasibility Assessment

| Area                             | Feasibility | Notes                                          |
| -------------------------------- | ----------- | ---------------------------------------------- |
| BTCUSDT data                     | High        | Directly available from Bybit                  |
| Multi-timeframe candles          | High        | 15m, 1H and 4H supported                       |
| Indicators                       | High        | Calculated locally                             |
| Market structure                 | High        | Deterministic implementation                   |
| Derivatives analysis             | High        | OI, funding and ratios available               |
| Basic order flow                 | Medium–High | Suitable for V1 with limitations               |
| Liquidation monitoring           | High        | Live stream available                          |
| LLM reasoning                    | High        | Must use structured bounded inputs             |
| Risk engine                      | High        | Fully deterministic                            |
| Manual approval                  | High        | Simple CLI workflow                            |
| Demo execution                   | High        | Bybit Demo supports required operations        |
| Historical microstructure replay | Medium      | Requires self-recording or later external data |
| Exact live-fill simulation       | Medium      | Demo may differ from production fills          |

---

# 8. Risk Management Principle

The system shall use the following fail-safe rule:

```text
If a critical prerequisite is uncertain
                ↓
             NO TRADE
```

Missed opportunities are acceptable.

Uncertain execution or uncontrolled risk is not acceptable.

---

# 9. Risk Register

## R1 — Bybit REST/API Unavailable

**Impact:** High
**Likelihood:** Medium

### Risk

The system may temporarily lose access to market or account endpoints.

### Mitigation

* Disable new entries
* Retry using bounded exponential backoff
* Preserve existing exchange-side protection
* Log outage state
* Resume only after health checks pass

---

## R2 — Public WebSocket Disconnect

**Impact:** High
**Likelihood:** Medium

### Risk

Real-time order-book, trade or liquidation data may stop unexpectedly.

### Mitigation

```text
Connection Lost
      ↓
Mark Feed UNHEALTHY
      ↓
Disable Trade Generation
      ↓
Reconnect
      ↓
Rebuild State
      ↓
Verify Freshness
      ↓
Resume
```

New entries shall not be allowed while required streams are unhealthy.

---

## R3 — Stale Market Data

**Impact:** High
**Likelihood:** Medium

### Risk

A trade could be generated using outdated market information.

### Mitigation

* Maintain per-source freshness thresholds
* Store exchange and local timestamps
* Validate freshness before analysis
* Re-check freshness before execution
* Reject stale data with:

```text
NO_TRADE
```

---

## R4 — Incorrect Timestamp Handling

**Impact:** High
**Likelihood:** Medium

### Risk

Different Bybit streams use different timestamp semantics.

Incorrect timestamp handling could misalign:

* Order book
* Trades
* Liquidations
* OI
* Candles
* Account state

### Mitigation

Preserve separately:

```text
exchange_event_timestamp
matching_engine_timestamp
local_receive_timestamp
sequence
update_id
```

Use UTC internally.

---

## R5 — Machine Clock Drift

**Impact:** High
**Likelihood:** Low–Medium

### Risk

Incorrect local system time may affect authenticated API requests and timing measurements.

### Mitigation

* Maintain NTP synchronization
* Monitor clock offset
* Disable authenticated execution if clock health is uncertain

---

## R6 — Order-Book State Corruption

**Impact:** High
**Likelihood:** Medium

### Risk

Missing or misapplied WebSocket updates may create an incorrect local order book.

### Mitigation

* Start from a valid snapshot
* Apply documented delta rules
* Preserve update/sequence information
* Replace state when a fresh snapshot arrives
* Mark book invalid when continuity is uncertain
* Rebuild before trading

Never guess missing order-book state.

---

## R7 — Order-Book Noise / Spoofing

**Impact:** Medium
**Likelihood:** High

### Risk

Displayed liquidity may disappear quickly and may not represent genuine future support or resistance.

### Mitigation

Do not use individual large orders as deterministic signals.

Prefer measurable features such as:

* Persistent imbalance
* Depth inside fixed basis-point ranges
* Spread
* Signed trade imbalance
* Liquidity concentration persistence

Order-book signals shall remain contextual.

---

## R8 — Incomplete Market Visibility

**Impact:** Medium
**Likelihood:** High

### Risk

The system sees Bybit activity only.

It does not observe the complete global cryptocurrency market.

### Mitigation

* Treat order flow as Bybit-specific
* Do not interpret venue-specific signals as total-market truth
* Avoid unsupported claims such as institutional intent

Cross-exchange aggregation is deferred to V2.

---

## R9 — LLM Hallucination

**Impact:** High
**Likelihood:** Medium

### Risk

The LLM may generate reasoning or trade information unsupported by the supplied market context.

### Mitigation

* Give the LLM only structured market context
* Require supporting and contradicting evidence
* Use strict output schema
* Run deterministic semantic validation
* Risk engine always has override authority
* Invalid proposals become NO_TRADE

---

## R10 — Malformed LLM Output

**Impact:** Medium–High
**Likelihood:** Medium initially

### Risk

The LLM may return invalid JSON or missing fields.

### Mitigation

```text
LLM Response
      ↓
JSON Validation
      ↓
Schema Validation
      ↓
One Bounded Retry
      ↓
Still Invalid?
      ↓
NO_TRADE
```

Never invent missing financial values.

---

## R11 — Semantically Invalid LLM Trade

**Impact:** High
**Likelihood:** Medium

### Risk

The response may be valid JSON but contain impossible trade geometry.

Example:

```text
LONG
Entry = 100
SL = 110
TP = 90
```

### Mitigation

Deterministic validation.

LONG:

```text
SL < Entry < TP
```

SHORT:

```text
TP < Entry < SL
```

Also validate:

* Price increments
* Quantity increments
* Current market distance
* NaN / Infinity
* Freshness

---

## R12 — Duplicate Order Execution

**Impact:** Critical
**Likelihood:** Low–Medium

### Risk

A network timeout may occur after Bybit accepted an order but before the application receives confirmation.

Blind retry could create a second order.

### Mitigation

Use:

* Unique `intent_id`
* Unique `orderLinkId`
* Persistent local execution state

On timeout:

```text
Do Not Retry Immediately
        ↓
Query / Reconcile
        ↓
Confirm Existing Order
        ↓
Retry Only If Conclusively Absent
```

---

## R13 — Incorrect Order State

**Impact:** High
**Likelihood:** Medium

### Risk

REST acknowledgement may be mistaken for final order status.

### Mitigation

Use an explicit execution state machine.

Final state shall be established using:

* Demo private WebSocket
* REST reconciliation

---

## R14 — Unexpected Existing Position

**Impact:** Critical
**Likelihood:** Low–Medium

### Risk

The application may restart while a Demo position already exists.

Local memory could incorrectly assume no active position.

### Mitigation

At startup:

```text
Fetch Positions
      ↓
Fetch Open Orders
      ↓
Fetch Protection State
      ↓
Reconstruct Local State
      ↓
Allow New Trades
```

No new entry before reconciliation completes.

---

## R15 — Missing Stop Loss Protection

**Impact:** Critical
**Likelihood:** Low–Medium

### Risk

An entry may execute while protective orders fail to attach.

### Mitigation

A trade is not considered operationally complete until exchange-side protection is verified.

If protection cannot be verified:

* Enter execution-risk state
* Disable new entries
* Reconcile immediately
* Preserve or restore protection according to predefined rules

---

## R16 — Approval Becomes Stale

**Impact:** High
**Likelihood:** Medium

### Risk

The user may approve a trade, but market conditions may change before the order is submitted.

### Mitigation

Manual approval shall have a TTL.

Immediately before execution:

* Re-check data
* Re-check account
* Re-check prices
* Re-check risk
* Validate approval age

If invalid:

```text
Approval Expired
      ↓
NO TRADE
```

---

## R17 — Demo / Live Execution Mismatch

**Impact:** Medium–High
**Likelihood:** High

### Risk

Demo fill behavior may not exactly reproduce:

* Production queue position
* Slippage
* Liquidity
* Market impact

### Mitigation

Use Demo primarily for:

* Integration validation
* Workflow validation
* Forward observation
* Execution-state testing

Do not claim Demo fills prove equivalent real-world execution.

---

## R18 — Overfitting

**Impact:** High
**Likelihood:** Medium–High

### Risk

Repeatedly modifying rules based on previous losses may produce a system fitted to historical noise.

### Mitigation

Freeze:

```text
strategy_version
feature_version
prompt_version
model_version
risk_config_version
```

during each evaluation batch.

Any meaningful logic change begins a new test cohort.

---

## R19 — Too Many Confirmation Filters

**Impact:** Medium
**Likelihood:** Medium

### Risk

Combining every indicator, derivative metric and order-flow metric as mandatory conditions may create an overly restrictive strategy.

### Mitigation

Separate:

```text
CONTEXT
SETUP
CONFIRMATION
```

Do not automatically make every feature a hard requirement.

---

## R20 — Risk Engine Failure

**Impact:** Critical
**Likelihood:** Low

### Risk

A software error inside the risk manager could allow unsafe execution.

### Mitigation

* Independent module
* Strong unit testing
* Defensive exception handling
* No execution if risk result is unavailable
* Default failure behavior:

```text
NO TRADE
```

---

## R21 — Disk / Journal Write Failure

**Impact:** Medium–High
**Likelihood:** Low

### Risk

Trade history or execution state may not be saved correctly.

### Mitigation

* Detect write failures
* Log critical errors
* Prevent new execution if required persistent state cannot be safely recorded
* Periodically verify log integrity

---

## R22 — API Credentials Exposed

**Impact:** High
**Likelihood:** Low

### Risk

API keys may accidentally enter Git or logs.

### Mitigation

* `.env`
* `.gitignore`
* No secrets in logs
* Minimum Demo permissions
* Secret rotation
* Git secret scanning where available

No production credentials shall exist in V1.

---

# 10. Important Unknowns

The following should be confirmed during integration testing:

1. Exact Demo fill behavior for market orders.
2. Stop-Loss / Take-Profit behavior after partial fills.
3. Best V1 protection workflow.
4. Order-book freshness thresholds.
5. Public-trade freshness thresholds.
6. OI / long-short acceptable delay thresholds.
7. Optimal order-book depth between L50 and later alternatives.
8. Practical reconnect timing.
9. Approval TTL.
10. Acceptable entry-price movement tolerance.

These should be measured rather than guessed.

---

# 11. Feasibility Decision

Based on current research:

```text
TECHNICAL FEASIBILITY: PASS
```

The V1 architecture can proceed to detailed system design.

No identified risk currently requires cancelling the project.

However, several risks require architectural controls from the beginning rather than being added later.

The highest-priority risks are:

* Stale or invalid market data
* Duplicate order execution
* Incorrect execution state
* Missing exchange-side protection
* Unexpected existing positions
* Invalid LLM output
* Risk-engine failure
* Demo/live execution mismatch

---

# 12. Phase Conclusion

The project should proceed to system architecture design with the following principles fixed:

1. Fail closed.
2. LLM is not execution authority.
3. Risk engine is independent.
4. Public market data and Demo execution are separated.
5. Execution uses explicit state tracking.
6. Exchange state must be reconciled after restart.
7. Order submission must be idempotent.
8. Every trade must have verified exchange-side protection.
9. Critical stale data means NO_TRADE.
10. Testing must include failure scenarios, not only successful trades.
