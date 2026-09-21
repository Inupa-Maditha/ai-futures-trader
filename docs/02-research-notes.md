# Research Notes — AI-Assisted Crypto Futures Trading System

## 1. Research Objective

The purpose of this research is to verify whether the required data, exchange functionality, and technical architecture for V1 are practical.

V1 focuses on:

* BTCUSDT Perpetual
* Bybit
* Live public market data
* Bybit Demo Trading
* Hybrid rule-based + LLM decision making
* Independent deterministic risk management

---

# 2. Bybit Data Availability

## 2.1 OHLCV / Candlestick Data

Bybit V5 provides historical and real-time candlestick data.

Required V1 timeframes are supported:

* 15 minutes
* 1 hour
* 4 hours

Required candle fields include:

* Open
* High
* Low
* Close
* Volume
* Timestamp

This means the system can directly obtain the 4H, 1H, and 15m data required for multi-timeframe analysis.

---

## 2.2 Order Book

Bybit provides both REST order-book snapshots and real-time WebSocket order-book updates.

For linear contracts such as BTCUSDT, multiple depth levels are available.

The WebSocket stream uses:

* Initial snapshot
* Incremental delta updates
* Sequence information
* Matching-engine timestamps

This data can be used to calculate basic order-flow features such as:

* Bid/ask imbalance
* Liquidity concentration
* Large bid/ask areas
* Short-term order-book pressure

---

## 2.3 Recent Public Trades

Bybit provides public recent-trade information.

Useful fields include:

* Trade price
* Trade size
* Taker side
* Trade timestamp

The real-time WebSocket public trade stream can therefore be used to estimate:

* Aggressive buying
* Aggressive selling
* Short-term trade-flow imbalance

---

## 2.4 Open Interest

Bybit directly provides Open Interest data for perpetual contracts.

Supported intervals include:

* 5m
* 15m
* 30m
* 1h
* 4h
* 1d

The system can calculate changes in Open Interest over time and combine them with price movement.

Bybit notes that this endpoint may experience additional latency during extreme market volatility, so freshness checking remains important.

---

## 2.5 Funding Rate

Historical funding-rate data is available directly from the Bybit V5 API.

Funding information can therefore be included in the derivatives-analysis engine without an external provider.

---

## 2.6 Long / Short Ratio

Bybit provides the percentage of position holders holding long and short positions.

Supported intervals include:

* 5m
* 15m
* 30m
* 1h
* 4h
* 1d

This information can be used as market-positioning context rather than as a standalone trading signal.

---

## 2.7 Liquidation Data

Bybit provides an All Liquidation WebSocket stream for perpetual contracts.

The stream includes:

* Symbol
* Liquidated position side
* Executed size
* Bankruptcy price
* Timestamp

The stream currently pushes liquidation information at approximately 500 ms intervals.

---

# 3. Data Source Decision

For V1, all required primary market and derivatives data can come directly from Bybit.

External paid data providers are therefore not required for the first version.

Primary source:

```text
Bybit V5 API
```

Data:

```text
OHLCV
Order Book
Public Trades
Open Interest
Funding
Long/Short Ratio
Liquidations
```

Technical indicators such as EMA, RSI, ATR, and derived volume metrics will be calculated locally in Python.

---

# 4. Demo Trading Research

Bybit V5 supports Demo Trading through a dedicated demo account.

Demo REST endpoint:

```text
https://api-demo.bybit.com
```

Demo private WebSocket:

```text
wss://stream-demo.bybit.com
```

However, the Demo WebSocket endpoint supports private streams only.

Public market data should use the normal Bybit public WebSocket stream because public market data is the same as mainnet market data.

Therefore V1 architecture will use:

```text
MAINNET PUBLIC MARKET DATA
        ↓
Analysis System
        ↓
Trading Decision
        ↓
Risk Engine
        ↓
Manual Approval
        ↓
BYBIT DEMO ACCOUNT
```

Demo Trading supports core order-management APIs including order creation, amendment, cancellation, order history, execution history, and position information.

Demo orders are retained for seven days.

WebSocket order-entry is not supported by the Demo Trading service, so V1 should use REST for order submission and private WebSocket streams for execution/order-state monitoring.

---

# 5. Order Execution and Protection

Bybit V5 allows Take Profit and Stop Loss parameters to be attached when creating supported futures/perpetual orders.

Position-level TP/SL management is also available.

Therefore V1 can implement exchange-side protection rather than relying only on the Python application remaining online.

Order creation is asynchronous, so successful API acknowledgement does not necessarily mean the final order state has already been completed.

The system should confirm execution status using private WebSocket/order-state information.

---

# 6. Rate-Limit Assessment

Bybit applies both IP-level and UID/API endpoint rate limits.

For example, the default HTTP IP limit is substantially higher than what a single-symbol V1 system should normally require.

V1 should still:

* Prefer WebSocket streams for high-frequency market updates
* Avoid unnecessary REST polling
* Monitor rate-limit response headers
* Implement retry/backoff behavior
* Avoid reconnect loops

The project should never operate close to the exchange rate limits.

---

# 7. Existing Solution Research

## 7.1 Freqtrade

Freqtrade is an open-source Python crypto trading bot.

Important ideas relevant to this project include:

* Python-based strategies
* Historical data
* Backtesting
* Dry-run / forward testing
* Trade management
* Strategy evaluation

Freqtrade documentation also recommends forward testing because historical backtesting can differ from real-world execution.

Useful concepts for this project:

* Separate strategy logic from execution
* Test before live trading
* Store trading results
* Evaluate strategies using repeatable data
* Treat backtesting results carefully

---

## 7.2 3Commas

3Commas provides tools for manual and automated crypto trading.

Its SmartTrade functionality demonstrates useful trade-management concepts such as:

* Long and short trading
* Market and limit orders
* Conditional orders
* Multiple take-profit targets
* Stop-loss management
* Trade-history tracking

Useful idea for this project:

The user should receive clear structured trade information before execution rather than seeing only a simple BUY or SELL signal.

---

# 8. AI Architecture Research

Three possible approaches were considered.

## Approach A — Pure Rule-Based System

Advantages:

* Deterministic
* Easy to test
* Reproducible
* Easy to audit

Limitations:

* Complex market context can require many rules
* Rule interactions can become difficult to maintain
* Difficult to express nuanced reasoning

---

## Approach B — Pure LLM Trading System

Example:

```text
Raw market data
      ↓
LLM
      ↓
BUY / SELL
```

This approach is not suitable for V1.

Problems include:

* Non-deterministic reasoning
* Difficult validation
* Potential malformed output
* Poor risk isolation
* LLM reasoning should not directly control account risk

---

## Approach C — Hybrid System

Selected architecture:

```text
Raw Market Data
        ↓
Deterministic Processing
        ↓
Indicators
Market Structure
Derivatives Context
Order Flow
        ↓
Rule-Based Market Context
        ↓
Structured Input
        ↓
LLM Reasoning
        ↓
Structured Trade Proposal
        ↓
Independent Deterministic Risk Engine
        ↓
Manual Approval
```

This approach keeps deterministic calculations and risk-management rules separate from LLM reasoning.

---

# 9. Responsibility of the LLM

The LLM may:

* Interpret structured market context
* Identify agreement or conflict between signals
* Explain the market setup
* Produce LONG / SHORT / NO TRADE proposals
* Explain why a setup should be rejected

The LLM must not:

* Directly submit orders
* Override the risk engine
* Change account-risk limits
* Ignore stale-data warnings
* Treat its own confidence as a real probability of winning

---

# 10. Responsibility of the Deterministic System

Python modules will calculate or validate:

* Indicators
* Swing highs and lows
* Market structure
* Support and resistance
* Open Interest changes
* Funding context
* Long/short positioning
* Order-book imbalance
* Trade aggression
* Volatility
* Data freshness
* Position size
* Stop Loss
* Risk/Reward
* Daily-loss limits
* Existing-position state

The deterministic risk engine has final authority over whether a proposed trade is allowed to reach manual approval.

---

# 11. Data Reliability Decision

Every source must contain or be associated with a timestamp.

Before a decision is generated, the system must verify:

```text
Current Time
     ↓
Source Timestamp
     ↓
Fresh enough?
```

If required data is stale:

```text
NO TRADE
```

This is especially important because different feeds may update at different frequencies and some derivatives endpoints may experience delays during extreme volatility.

---

# 12. Final V1 Architecture Decision

The V1 architecture is confirmed as:

```text
Bybit Mainnet Public Market Data
                ↓
Data Ingestion
                ↓
Freshness / Timestamp Validation
                ↓
Feature Calculation
                ↓
Market Structure
                ↓
Derivatives Analysis
                ↓
Order-Flow Analysis
                ↓
Hierarchical Rule Engine
                ↓
LLM Reasoning
                ↓
Trade Proposal
                ↓
Independent Risk Engine
                ↓
Manual Approval
                ↓
Bybit Demo REST Execution
                ↓
Private Demo WebSocket Monitoring
                ↓
Trade Journal
```

---

# 13. Research Conclusions

1. Bybit provides the primary market data required for V1.
2. No external paid market-data provider is required for V1.
3. BTCUSDT 4H, 1H, and 15m analysis is technically supported.
4. Order-book and recent-trade data can support a basic order-flow engine.
5. Open Interest, funding, long/short ratio, and liquidation data are available.
6. Demo Trading supports the core order-execution workflow required by V1.
7. Public real-time data and private demo execution must use different WebSocket environments.
8. Exchange-side TP/SL protection is technically possible.
9. The hybrid decision architecture remains appropriate.
10. Deterministic risk control must remain separate from LLM reasoning.
11. Data freshness and reconnection handling are mandatory.
12. No major API limitation currently blocks the proposed V1.
