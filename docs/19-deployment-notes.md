# Phase 19 — Minimal V1 Deployment Notes

## 1. Purpose

V1 is a local Python application.

It does not require:

- Docker
- Cloud deployment
- Kubernetes
- CI/CD
- PostgreSQL
- Web dashboard

---

## 2. Prerequisites

- Windows 11 or compatible desktop OS
- Python 3.12+
- Git
- Internet access
- Bybit Demo API credentials
- Groq API key

---

## 3. Clone the Repository

```powershell
git clone https://github.com/Inupa-Maditha/ai-futures-trader.git
cd ai-futures-trader
```

---

## 4. Create the Virtual Environment

```powershell
python -m venv .venv
```

Activate:

```powershell
.venv\Scripts\Activate.ps1
```

---

## 5. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

---

## 6. Configure Local Secrets

Copy:

```text
.env.example
```

to:

```text
.env
```

Set:

```env
BYBIT_DEMO_API_KEY=
BYBIT_DEMO_API_SECRET=

SYMBOL=BTCUSDT
CATEGORY=linear

GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1

ENABLE_DEMO_EXECUTION=false
```

Do not commit `.env`.

---

## 7. Verify Security Before Running

```powershell
python -m scripts.run_security_audit
```

Expected:

```text
PASS
```

The default execution setting should remain:

```text
ENABLE_DEMO_EXECUTION=False
```

---

## 8. Run the Automated Test Suite

```powershell
python -m pytest tests -q
```

Current Phase 15 baseline:

```text
257 passed
```

---

## 9. Run the Integrated Pipeline

```powershell
python -m scripts.run_sprint5_demo_execution
```

With Demo execution disabled, the system may analyze and risk-check but must not submit an order.

---

## 10. Validate the Latest Journal

```powershell
python -m scripts.validate_latest_journal
```

Expected:

```text
INTEGRITY
VALID
```

---

## 11. Show the System Report

```powershell
python -m scripts.show_system_report
```

Use this to review:

- Pipeline runs
- Invalid runs
- Error events
- Decision counts
- Risk outcomes
- Execution outcomes
- Closed-trade metrics

---

## 12. Local Data

Runtime data and journals are stored locally under the project's data directory.

Do not publish raw logs if they contain sensitive account or strategy information.

---

## 13. Startup Safety Procedure

Before every supervised session:

1. Activate `.venv`.
2. Confirm `.env` exists locally.
3. Confirm Demo credentials are being used.
4. Confirm `ENABLE_DEMO_EXECUTION=false` unless a specifically planned supervised Demo execution is being performed.
5. Run the security audit.
6. Start the integrated pipeline.
7. Validate the journal after the run.

---

## 14. Recovery After Restart

After an unexpected machine or process restart:

1. Do not assume the previous order or position state.
2. Restart the application normally.
3. Re-read Bybit Demo account / position state before any new execution.
4. Check for existing BTCUSDT positions.
5. Check for active entry orders.
6. Check the latest journal.
7. Confirm execution safety state before continuing.
8. If order submission state is uncertain, reconcile it by deterministic order identity before any retry.

Never blindly resubmit an uncertain order.

---

## 15. Troubleshooting

### Tests fail

Run:

```powershell
python -m pytest tests -q
```

Investigate the first failing test before continuing stability or forward testing.

### Journal invalid

Run:

```powershell
python -m scripts.validate_latest_journal
```

Do not treat an invalid run as valid evidence.

### Security audit fails

Do not continue execution until the cause is fixed.

### WebSocket / API failure

The system should fail closed and should not create a new trade from unhealthy critical data.

---

## 16. Clean-Environment Verification

Before Phase 19 is marked complete, repeat the setup on a clean local environment using only:

- Repository
- Python
- `requirements.txt`
- `.env.example`
- Local secret values

Checklist:

- [ ] Clone succeeds
- [ ] Virtual environment creates successfully
- [ ] Dependencies install successfully
- [ ] `.env` configuration is clear
- [ ] Security audit passes
- [ ] Test suite passes
- [ ] Integrated pipeline starts
- [ ] Journal validation works
- [ ] Restart / recovery instructions are understandable

---

## 17. Phase 19 Status

```text
DOCUMENTATION PREPARED
CLEAN-ENVIRONMENT VERIFICATION PENDING
```
