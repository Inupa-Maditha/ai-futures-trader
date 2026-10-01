# Phase 16 — Forward Demo Test Log

## 1. Purpose

Phase 16 evaluates whether the frozen V1 trading process shows useful performance during forward testing.

This phase uses Bybit Demo only.

---

## 2. Rules

- Use Bybit Demo only.
- Keep the workflow unchanged for every eligible trade.
- Retain manual approval.
- Log every eligible trade.
- Do not cherry-pick trades.
- Do not modify rules after individual losses.
- Keep the strategy version fixed during each test batch.
- Treat NO_TRADE as a valid system outcome.

---

## 3. Evaluation Checkpoints

- 30 trades → early pilot checkpoint
- 100+ trades → minimum serious V1 evaluation target
- 200–300 trades → preferred if practical before stronger conclusions

Results below 100 trades must be labeled preliminary.

---

## 4. Frozen Test-Batch Information

| Field | Value |
|---|---|
| Batch ID | P16-B01 |
| Start Date | 2026-10-01 |
| End Date | OPEN |
| Branch | feature/system-integration-testing |
| Commit | 13d81ba59466c7c4b6e0701b291bbb67715e5be6 |
| Tag / Version | phase16-forward-test-baseline |
| Strategy Version | V1 frozen baseline |
| Feature Version | V1 frozen baseline |
| Prompt Version | 1.0 |
| Risk Configuration Version | V1 frozen baseline |
| LLM Provider / Model | Groq / openai/gpt-oss-20b |
| Symbol | BTCUSDT |
| Exchange | Bybit |
| Execution Environment | Demo |

---

## 5. Trade Log

| # | Date/Time UTC | Run ID | Decision | Direction | Setup Quality | Entry | Stop | TP | Qty | Planned R:R | Risk Result | Manual Approval | Execution Result | Exit | Net PnL | Realized R | Regime | Notes |
|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---:|---:|---:|---|---|
| 1 | | | | | | | | | | | | | | | | | | |

Add one row for every executed forward-demo trade.

---

## 6. Non-Trade / Rejection Summary

Track important non-execution outcomes so the dataset is not limited to winners or executed trades.

| Date/Time UTC | Run ID | Outcome | Reason |
|---|---|---|---|
| | | NO_TRADE / DECISION_REJECTED / RISK_REJECTED / DEMO_EXECUTION_DISABLED / MANUALLY_REJECTED | |

---

## 7. Batch Progress

| Checkpoint | Status | Notes |
|---|---|---|
| 30 trades | Pending | Early pilot only |
| 100 trades | Pending | Serious V1 evaluation target |
| 200 trades | Optional | Stronger evidence |
| 300 trades | Optional | Stronger evidence |

---

## 8. Deviations

Any strategy, prompt, feature, risk, or execution-behavior change must be recorded here.

| Date | Change | Reason | New Version / Commit | New Batch Required? |
|---|---|---|---|---|
| | | | | |

If a material trading-rule change occurs, start a new test batch rather than mixing incompatible versions.

---

## 9. Completion Status

Status:

```text
PENDING
```

Phase 16 is ready for final evaluation when the forward-demo sample is large enough for the intended level of conclusion and the full dataset has been retained without cherry-picking.
