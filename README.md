# AI-Assisted Crypto Futures Trading System

An AI-assisted cryptocurrency futures trading system focused on BTCUSDT Perpetual trading using Bybit Demo Trading.

The system combines deterministic market analysis, multi-timeframe technical analysis, derivatives data, order-flow information, LLM-assisted reasoning, and an independent risk-management layer.

## Project Status

🚧 Under Development — V1

## V1 Objectives

The system will:

* Analyze BTCUSDT Perpetual
* Use 4H, 1H, and 15m timeframes
* Analyze technical indicators and market structure
* Use derivatives data such as Open Interest and Funding Rate
* Analyze order-book and recent-trade information
* Generate:

  * LONG
  * SHORT
  * NO TRADE
* Calculate Entry, Stop Loss, and Take Profit
* Validate every trade using deterministic risk rules
* Require manual user approval
* Execute approved trades through Bybit Demo Trading
* Log trades and evaluate system performance

## Core Architecture

```text
Bybit Market Data
        ↓
Data Validation
        ↓
Feature Extraction
        ↓
Market Analysis
        ↓
Rule-Based Context
        ↓
LLM Reasoning
        ↓
Trade Proposal
        ↓
Deterministic Risk Engine
        ↓
Manual Approval
        ↓
Bybit Demo Execution
        ↓
Trade Journal
```

## Safety Principles

* No real-money trading in V1
* No fully autonomous execution
* Stop Loss is mandatory
* Risk validation is independent from AI output
* Stale or invalid market data results in NO TRADE
* API keys and secrets must never be committed to Git

## Technology

Planned stack:

* Python
* Bybit V5 API
* REST API
* WebSocket
* pandas
* NumPy
* CSV / JSON
* LLM API or local LLM integration
* Git / GitHub

## Documentation

Project documentation is stored inside:

```text
/docs
```

Current documents:

```text
01-problem-statement.md
```

## Disclaimer

This project is intended for software development, research, and demo trading purposes.

V1 uses Bybit Demo Trading and does not execute real-money trades.
