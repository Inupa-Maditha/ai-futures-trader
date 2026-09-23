# AI-Assisted Crypto Futures Trading System

A V1 AI-assisted cryptocurrency futures trading system for **BTCUSDT Perpetual on Bybit**.

The system combines deterministic market analysis, multi-timeframe technical analysis, derivatives data, order-flow features, bounded LLM reasoning, deterministic risk management, manual approval, Bybit Demo execution, persistent journaling, and performance evaluation.

> V1 is strictly a Demo Trading system.
> It does not support authenticated real-money execution.

---

## Project Status

**V1 — System Integration / Stability Testing**

Current implementation status:

- Market-data pipeline: complete
- Technical analysis: complete
- Market structure: complete
- Structured market context: complete
- LLM decision layer: complete
- Deterministic risk engine: complete
- Manual approval: complete
- Bybit Demo execution: complete
- Persistent journal: complete
- Evaluation tooling: complete
- System integration tests: complete
- Stability testing: in progress
- Forward Demo testing: pending

Current automated test baseline:

```text
257 passed
```

Current Phase 15 stability baseline:

```text
Branch:
feature/system-integration-testing

Commit:
9a18e050f68aa311f4ca4a7628384eee6aec21af

Tag:
phase15-stability-baseline
```

---

## V1 Scope

V1 focuses on:

- BTCUSDT Perpetual only
- Bybit mainnet public market data
- Bybit Demo Trading for authenticated execution
- Python
- 4H / 1H / 15m multi-timeframe analysis
- EMA / RSI / ATR
- Deterministic market structure
- Open Interest
- Funding rate
- Account-holder long/short positioning
- Liquidation data
- L50 order book
- Recent trades / order-flow analysis
- Structured market context
- Groq-hosted LLM reasoning
- LONG / SHORT / NO_TRADE proposals
- Independent deterministic risk validation
- Manual approval before every trade
- Demo execution only
- JSONL / CSV journaling
- Trade-outcome import
- Performance evaluation

---

## Core Architecture

```text
Bybit Mainnet Public Market Data
        ↓
Historical Bootstrap
        ↓
Live REST / WebSocket Data
        ↓
Data Health / Freshness Validation
        ↓
Deterministic Feature Extraction
        ↓
Market Structure Analysis
        ↓
Multi-Timeframe Market Context
        ↓
Bounded LLM Reasoning
        ↓
Schema / Semantic Validation
        ↓
LONG / SHORT / NO_TRADE
        ↓
Fresh Bybit Demo Account State
        ↓
Current Instrument Rules
        ↓
Independent Deterministic Risk Engine
        ↓
Execution Safety Switch
        ↓
Manual Human Approval
        ↓
Execution Preflight
        ↓
Idempotent Bybit Demo Execution
        ↓
Persistent Journal
        ↓
Trade Outcome / Evaluation
```

---

## Decision Authority

The system deliberately separates responsibilities.

```text
LLM
    → may propose a trade

Deterministic Risk Engine
    → may approve or reject the proposal

Human
    → may approve a risk-approved trade

Execution Layer
    → may execute only after all required checks pass
```

The LLM cannot:

- Determine final position size
- Choose account risk
- Override risk rejection
- Access the authenticated exchange client
- Submit an order directly

---

## Safety Principles

V1 follows a fail-closed design.

- No real-money trading
- No fully autonomous execution
- Manual approval is mandatory
- Stop Loss is mandatory
- Risk validation is deterministic
- Maximum one BTCUSDT position
- Existing-position checks are enforced
- Duplicate execution is prevented using deterministic order IDs
- Uncertain order submission is reconciled before any retry
- Stale or unhealthy critical data blocks progression
- NO_TRADE is a valid outcome
- API credentials must never be committed to Git
- Demo execution is disabled by default

Default safety configuration:

```env
ENABLE_DEMO_EXECUTION=false
```

---

## Technology

- Python 3.12+
- Bybit V5 API
- Bybit mainnet public REST
- Bybit mainnet public WebSocket
- Bybit Demo Trading REST
- `pybit`
- `pandas`
- `numpy`
- `pydantic`
- `python-dotenv`
- OpenAI-compatible Python SDK
- GroqCloud
- `openai/gpt-oss-20b`
- `pytest`
- Git / GitHub

---

## Installation

Clone the repository:

```powershell
git clone https://github.com/Inupa-Maditha/ai-futures-trader.git
cd ai-futures-trader
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

---

## Environment Configuration

Copy:

```text
.env.example
```

to:

```text
.env
```

Required configuration:

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

Never commit `.env`.

---

## Running Tests

Run the full automated test suite:

```powershell
python -m pytest tests -q
```

Current Phase 15 baseline:

```text
257 passed
```

---

## Security Audit

Run:

```powershell
python -m scripts.run_security_audit
```

The audit checks:

- Journal content for credential leakage
- Git protection for `.env`
- Demo execution safety state

---

## Running the Integrated Pipeline

Run:

```powershell
python -m scripts.run_sprint5_demo_execution
```

The production pipeline performs:

```text
Market Data
→ Market Context
→ Groq Decision
→ Risk Validation
→ Execution Safety Check
→ Manual Approval
→ Demo Execution
→ Journal
```

With:

```env
ENABLE_DEMO_EXECUTION=false
```

the system may analyze a valid trade but cannot submit a Demo order.

---

## Journal Validation

Validate the latest run:

```powershell
python -m scripts.validate_latest_journal
```

A valid run must contain a consistent event sequence and a valid terminal status.

Example:

```text
RUN_STARTED
MARKET_CONTEXT
DECISION
RUN_FINISHED
```

A NO_TRADE run is a normal successful pipeline outcome.

---

## System Evaluation Report

Run:

```powershell
python -m scripts.show_system_report
```

The report summarizes:

- Pipeline runs
- Valid / invalid runs
- Error events
- Decision distribution
- Average confidence
- Risk outcomes
- Manual approvals
- Executions
- Terminal statuses
- Closed-trade performance
- Profit factor
- Expectancy
- Drawdown
- Consecutive losses

---

## Phase 15 Stability Testing

Phase 15 verifies technical stability rather than strategy profitability.

Current test plan:

```text
7 days
×
4 scheduled sessions per day
=
28 planned stability sessions
```

Scheduled sessions:

```text
02:30
08:30
15:30
21:30
```

Strategy and execution behavior remain frozen during this test window.

---

## Forward Demo Testing

After Phase 15 completes successfully, Phase 16 begins.

Forward testing will:

- Keep the tested strategy version fixed
- Use Bybit Demo only
- Retain manual approval
- Log every eligible trade
- Avoid cherry-picking
- Avoid modifying rules after individual losses

Evaluation checkpoints:

```text
30 trades   → early pilot
100+ trades → serious V1 evaluation target
200–300     → stronger evidence if practical
```

---

## Documentation

Project documentation is stored in:

```text
docs/
```

Main documents:

```text
01-problem-statement.md
02-research-notes.md
03-requirements.md
04-feasibility-risk.md
05-system-design.md
06-data-design.md
07-sprint-plan.md
15-test-plan.md
15-stability-log.md
16-forward-test-log.md
17-evaluation-report.md
19-deployment-notes.md
21-future-roadmap.md
```

Some later-phase documents are created as the project reaches those phases.

---

## V1 Out of Scope

V1 intentionally does not require:

- Real-money live trading
- Fully autonomous execution
- Multiple trading pairs
- Web dashboard
- PostgreSQL
- Docker
- Kubernetes
- Cloud deployment
- CI/CD infrastructure

These may be considered for later versions.

---

## Disclaimer

This project is intended for software engineering, research, and Bybit Demo Trading experimentation.

V1 does not execute authenticated real-money trades.

Demo Trading results must not be treated as proof of future live-trading profitability.
