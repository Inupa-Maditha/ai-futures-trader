# Phase 15 — System Integration Test Plan

## 1. Purpose

Phase 15 verifies that all V1 components operate safely and consistently as one integrated trading system.

This phase evaluates technical reliability.

It does not evaluate strategy profitability.

---

## 2. Scope

- BTCUSDT Perpetual only
- Bybit mainnet public market data
- Bybit Demo authenticated account data
- Bybit Demo execution only
- Python
- 4H / 1H / 15m analysis
- Deterministic feature extraction
- Market structure
- Derivatives context
- Order-flow context
- Bounded LLM reasoning
- Deterministic risk management
- Manual approval
- Persistent JSONL / CSV journal
- Evaluation tooling
- No real-money trading

---

## 3. Full Pipeline

```text
Bybit Mainnet Public Data
        ↓
Historical Candle Bootstrap
        ↓
Live REST / WebSocket Updates
        ↓
Freshness / Health Validation
        ↓
Feature Extraction
        ↓
Market Structure
        ↓
Multi-Timeframe Context
        ↓
LLM Reasoning
        ↓
Schema / Semantic Validation
        ↓
LONG / SHORT / NO_TRADE
        ↓
Fresh Bybit Demo Account State
        ↓
Current Instrument Rules
        ↓
Deterministic Risk Engine
        ↓
Risk Approved / Rejected
        ↓
Execution Safety Switch
        ↓
Manual Approval
        ↓
Execution Request
        ↓
Execution Preflight
        ↓
Idempotent Bybit Demo Execution
        ↓
Persistent Journal
        ↓
Trade Outcome Import
        ↓
Performance Evaluation
```

---

## 4. Safety Invariants

The following invariants must remain true.

### 4.1 Demo-only execution

Authenticated order execution must use Bybit Demo only.

### 4.2 Safe default

```env
ENABLE_DEMO_EXECUTION=false
```

must remain the default configuration.

### 4.3 Deterministic risk authority

The LLM cannot:

- Set final quantity
- Set leverage policy
- Set account risk
- Override deterministic rejection
- Submit an order

### 4.4 Manual approval

No order may be submitted without explicit human approval.

### 4.5 Stale-data protection

Critical stale or unhealthy data must prevent progression.

### 4.6 Existing-position protection

A conflicting BTCUSDT position must block a new entry.

### 4.7 Duplicate protection

A deterministic `orderLinkId` must prevent duplicate submission.

### 4.8 Uncertain execution

If submission status is uncertain:

```text
RECONCILE
```

before any possible retry.

Blind retry is prohibited.

### 4.9 Persistent audit trail

Every pipeline run must terminate with a journaled result.

---

## 5. Test Levels

### Level A — Deterministic / Fake Integration

No external network dependency.

Use injected fake components to verify:

- Pipeline branching
- Journal lifecycle
- NO_TRADE
- Decision rejection
- Risk rejection
- Manual rejection
- Execution-disabled behavior
- Confirmed fake execution
- Execution uncertainty

### Level B — Live Read-Only Integration

Use real public Bybit data but no authenticated execution.

Verify:

- REST bootstrap
- WebSocket data
- Derivatives data
- Health monitoring
- Freshness rules
- Market-context generation

### Level C — Controlled Bybit Demo

Use authenticated Bybit Demo only.

Requires:

- Explicit execution enablement
- Deterministic risk approval
- Manual human approval
- Execution preflight

No automated test shall place a Demo trade without an explicitly supervised session.

### Level D — Multi-Session Stability

Run the complete system repeatedly across different market conditions.

Current Phase 15 plan:

```text
7 days
4 sessions/day
28 sessions
```

---

## 6. Core Integration Scenarios

The system must cover:

- Accepted NO_TRADE
- Rejected LLM decision
- Risk rejection
- Demo execution disabled
- Manual rejection
- Successful fake execution
- Execution uncertainty
- Unexpected pipeline exception

---

## 7. Market-Data Failure Scenarios

Test:

- Public API unavailable
- WebSocket disconnected
- Reconnect
- Stale order book
- Stale public trades
- Stale candles
- Recovery after stale state
- Mixed timestamps
- Unhealthy critical source

Expected behavior:

```text
No unsafe progression
```

---

## 8. Decision-Layer Failure Scenarios

Test:

- Malformed LLM response
- Schema-invalid response
- Semantically invalid response
- Unsupported evidence
- Ungrounded evidence
- Conflicting timeframes
- Valid NO_TRADE

The LLM must never bypass deterministic validation.

---

## 9. Risk-Layer Scenarios

Test:

- Valid safe trade
- Existing position
- Daily loss limit reached
- Remaining daily budget exceeded
- Zero available balance
- Excessive leverage requirement
- Minimum quantity violation
- Minimum notional violation
- Excessively wide stop
- Invalid trade geometry

All rejection behavior must be deterministic.

---

## 10. Execution-Safety Scenarios

Test:

- Existing BTCUSDT position
- Existing active entry order
- Protective reduce-only order
- Duplicate deterministic `orderLinkId`
- Submission exception followed by successful reconciliation
- Submission exception with unresolved state
- No blind retry

---

## 11. Journal Scenarios

Verify:

- RUN_STARTED exists
- MARKET_CONTEXT exists when context is built
- DECISION exists when decision service runs
- RISK_RESULT exists when risk engine runs
- MANUAL_APPROVAL exists when approval is requested
- EXECUTION_RESULT exists after confirmed execution
- ERROR exists for controlled failures where appropriate
- RUN_FINISHED exists exactly once
- Terminal status is valid
- Secret values never appear in journal data

---

## 12. Security Tests

Verify:

- `.env` is ignored by Git
- Demo credentials are never journaled
- Groq key is never journaled
- Authorization headers are not journaled
- Execution is disabled by default

Security audit command:

```powershell
python -m scripts.run_security_audit
```

---

## 13. Freshness and Recovery Tests

Critical event-required streams must behave as:

```text
UNKNOWN
→ HEALTHY
→ STALE / DEGRADED
→ HEALTHY after valid recovery
```

Freshness thresholds must be tested at their boundaries.

A recovered connection alone must not falsely make event-required data fresh if no valid event has been observed.

---

## 14. WebSocket Health Tests

Verify:

- Connected state
- Disconnected state
- Reconnect state
- Health state propagation
- Connection-check failure handling
- No unnecessary repeated health mutation

---

## 15. Production Pipeline Smoke Test

With:

```env
ENABLE_DEMO_EXECUTION=false
```

run:

```powershell
python -m scripts.run_sprint5_demo_execution
```

Expected safe terminal statuses include:

```text
NO_TRADE
RISK_REJECTED
DEMO_EXECUTION_DISABLED
DECISION_REJECTED
```

No order should be submitted when Demo execution is disabled.

---

## 16. Journal Validation

After each real integration session:

```powershell
python -m scripts.validate_latest_journal
```

Expected result:

```text
INTEGRITY
VALID
```

---

## 17. Regression Test

Run:

```powershell
python -m pytest tests -q
```

Phase 15 baseline:

```text
257 passed
```

Any regression must be investigated before the stability window continues.

---

## 18. Stability-Test Baseline

Frozen baseline:

```text
Branch:
feature/system-integration-testing

Commit:
9a18e050f68aa311f4ca4a7628384eee6aec21af

Tag:
phase15-stability-baseline
```

The trading behavior must not be modified during the stability window.

If a critical code fix changes trading behavior, a new baseline must be created and the relevant stability period restarted.

---

## 19. Stability-Test Schedule

Duration:

```text
7 days
```

Sessions:

```text
02:30
08:30
15:30
21:30
```

Total:

```text
28 planned sessions
```

A session does not need to produce a trade.

Valid outcomes include:

- NO_TRADE
- Decision rejection
- Risk rejection
- Demo execution disabled

No trade shall be forced to create test coverage.

---

## 20. Phase 15 Completion Criteria

Phase 15 may be closed only when:

- Automated integration tests pass
- Production pipeline uses the tested orchestration layer
- Security audit passes
- Journal validation passes
- WebSocket disconnect/recovery behavior is tested
- Stale-data degradation/recovery is tested
- Risk safety edge cases are tested
- Duplicate execution protection is tested
- Execution-uncertain behavior is tested
- Multi-session stability testing is complete
- Approximately one week of technical stability has been observed
- No unresolved critical failure remains

After these conditions are satisfied:

```text
Phase 15
    ↓
COMPLETE
    ↓
Phase 16 — Forward Demo Testing
```
