# Phase 15 — System Integration Test Plan

## Project

AI-Assisted Crypto Futures Trading System

## Scope

- BTCUSDT Perpetual only
- Bybit
- Mainnet public market data
- Bybit Demo Trading for authenticated execution
- Python
- 4H / 1H / 15m multi-timeframe analysis
- Hybrid deterministic + LLM decision engine
- Independent deterministic risk engine
- Manual approval before every trade
- Demo execution only
- Persistent JSONL / CSV journal
- Trade-outcome evaluation
- No real-money trading

---

# 1. Purpose

The purpose of Phase 15 is to verify that all previously developed
components work correctly together as one complete V1 trading system.

The system must fail safely when market data, AI services, exchange APIs,
risk validation, approval, execution, or journal components fail.

The goal is not to evaluate strategy profitability in this phase.

Strategy performance will be evaluated later during forward demo testing.

---

# 2. Full V1 Pipeline

```text
Bybit Public Market Data
        ↓
Historical Candle Bootstrap
        ↓
Live WebSocket / REST Updates
        ↓
Freshness Validation
        ↓
Indicator Engine
        ↓
Market Structure Engine
        ↓
Multi-Timeframe Market Context
        ↓
Groq LLM Decision
        ↓
Decision Schema Validation
        ↓
Evidence Grounding Validation
        ↓
LONG / SHORT / NO_TRADE
        ↓
Fresh Bybit Demo Account State
        ↓
Instrument Rules
        ↓
Deterministic Risk Engine
        ↓
Risk Approved / Rejected
        ↓
Manual Human Approval
        ↓
Execution Preflight
        ↓
Idempotent Bybit Demo Execution
        ↓
Exchange-Side SL / TP
        ↓
Persistent Journal
        ↓
Trade Outcome Import
        ↓
Performance Evaluation