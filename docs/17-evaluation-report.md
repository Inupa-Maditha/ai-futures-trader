# Phase 17 — V1 Evaluation Report

## 1. Status

```text
PENDING FORWARD-DEMO SAMPLE
```

This report will be finalized after Phase 16 forward-demo testing provides enough observations.

---

## 2. Evaluation Principle

The system is evaluated by expectancy, drawdown, consistency, and technical reliability.

A small winning streak is not sufficient evidence of success.

---

## 3. Test Batch

| Field | Value |
|---|---|
| Batch ID | |
| Number of Forward-Demo Trades | |
| Start Date | |
| End Date | |
| Strategy Version | |
| Feature Version | |
| Prompt Version | |
| Risk Version | |
| LLM Provider / Model | |
| Symbol | BTCUSDT |
| Environment | Bybit Demo |

---

## 4. Core Performance Metrics

| Metric | Result |
|---|---:|
| Closed Trades | |
| Wins | |
| Losses | |
| Breakeven | |
| Win Rate | |
| Total Realized PnL | |
| Average Win | |
| Average Loss | |
| Profit Factor | |
| Expectancy / Trade | |
| Average R | |
| Best R | |
| Worst R | |
| Maximum Drawdown | |
| Maximum Consecutive Losses | |

---

## 5. Equity Curve

Equity-curve file / chart:

```text
Pending
```

Observations:

- Pending

---

## 6. Long vs Short Performance

| Direction | Trades | Win Rate | Total PnL | Average R |
|---|---:|---:|---:|---:|
| LONG | | | | |
| SHORT | | | | |

---

## 7. Setup-Type Performance

| Setup Type | Trades | Win Rate | Total PnL | Average R |
|---|---:|---:|---:|---:|
| | | | | |

---

## 8. Market-Regime Performance

| Regime | Trades | Win Rate | Total PnL | Average R |
|---|---:|---:|---:|---:|
| | | | | |

---

## 9. Time-of-Day Performance

Use this section only if the sample is large enough to make the comparison useful.

| Time Window | Trades | Win Rate | Average R |
|---|---:|---:|---:|
| | | | |

---

## 10. NO_TRADE Analysis

Review whether NO_TRADE filtering appears to remove low-quality or conflicting setups.

Questions:

- How often does the system return NO_TRADE?
- Which conditions most often cause NO_TRADE?
- Are avoided setups later seen as poor trades?
- Is the system excessively selective?

Findings:

- Pending

---

## 11. Risk-Engine Rejection Analysis

Review:

- Most common rejection reasons
- Whether rejections are technically correct
- Whether risk rules reject valid-looking but unsafe setups
- Whether any rejection rule appears unnecessarily restrictive

Findings:

- Pending

---

## 12. LLM Reasoning Analysis

Evaluate:

- Whether accepted decisions are grounded in supplied evidence
- Whether the LLM adds useful synthesis beyond deterministic context
- Schema / semantic failure rate
- Rejected or unsupported evidence patterns
- Whether the LLM introduces unstable behavior

Findings:

- Pending

---

## 13. Order-Flow / Derivatives Value

Evaluate whether these inputs appear useful:

- Open Interest
- Funding
- Account-holder long/short ratios
- Liquidations
- Public-trade imbalance
- Order-book imbalance

Also inspect whether some features are redundant.

Findings:

- Pending

---

## 14. False-Signal Patterns

Document recurring losing patterns.

Examples:

- Failed breakout
- Trend exhaustion
- Conflicting timeframe structure
- High-volatility entries
- Weak order-flow confirmation

Findings:

- Pending

---

## 15. Technical Reliability

| Metric | Result |
|---|---:|
| Valid Pipeline Runs | |
| Invalid Pipeline Runs | |
| Error Events | |
| LLM Schema Failures | |
| LLM Semantic Rejections | |
| Risk Rejections | |
| Stale-Data Rejections | |
| WebSocket Recovery Events | |
| Duplicate Submissions Prevented | |
| Execution-Uncertain Events | |
| Protection Failures | |

---

## 16. Known Limitations

- Bybit Demo execution does not prove future live fill quality.
- The system trades BTCUSDT only.
- The sample may not cover every market regime.
- Results from fewer than 100 forward-demo trades are preliminary.
- LLM behavior is not perfectly deterministic.
- One exchange's order flow does not represent the entire crypto market.

Add observed limitations here:

- Pending

---

## 17. Final Assessment

### Evidence Summary

Pending.

### Positive Expectancy

```text
NOT YET DETERMINED
```

### V1 Evaluation Status

```text
PENDING
```

---

## 18. Completion Checklist

- [ ] Forward-demo dataset reviewed
- [ ] Equity curve created
- [ ] Drawdown analyzed
- [ ] Expectancy calculated
- [ ] Long vs short reviewed
- [ ] Setup performance reviewed
- [ ] Regime performance reviewed
- [ ] NO_TRADE filtering reviewed
- [ ] Risk-engine rejection quality reviewed
- [ ] LLM value reviewed
- [ ] Order-flow value reviewed
- [ ] Weaknesses documented
- [ ] Limitations documented
- [ ] No exaggerated profitability claims
