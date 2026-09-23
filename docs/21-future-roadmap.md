# Phase 21 — V2 Future Roadmap

## 1. Purpose

This document records improvements intentionally deferred beyond V1.

V1 should remain minimal, local, Demo-only, and focused on BTCUSDT until its current design is properly evaluated.

---

## 2. Infrastructure Improvements

Potential V2 additions:

- Docker
- Cloud deployment
- PostgreSQL
- CI/CD
- Web dashboard
- Automated notifications
- Improved operational monitoring

---

## 3. Market Expansion

Potential additions:

- ETHUSDT
- Additional liquid perpetual pairs
- Multi-symbol portfolio controls
- Cross-symbol exposure limits

Any multi-asset expansion requires new risk and concurrency rules.

---

## 4. Strategy / Analysis Improvements

Potential research:

- Better regime classification
- More advanced order-flow analysis
- Walk-forward backtesting
- Historical microstructure replay
- Better feature selection
- Indicator redundancy analysis
- Model comparison
- Strategy versioning
- Explicit baseline strategy comparison

---

## 5. LLM Improvements

Potential additions:

- Compare multiple LLM providers / models
- Prompt-version experiments
- Structured reasoning-quality scoring
- LLM vs deterministic baseline analysis
- Cost / latency optimization
- Fallback model strategy

The LLM must remain outside final risk authority.

---

## 6. Execution Improvements

Potential additions:

- More detailed private WebSocket lifecycle handling
- More execution-path coverage
- Improved partial-fill management
- More detailed slippage analysis
- Better restart recovery
- Notification / alerting for execution-risk states

---

## 7. Evaluation Improvements

Potential additions:

- Larger forward-test samples
- Market-regime stratification
- Walk-forward evaluation
- Transaction-cost stress testing
- Demo-vs-live behavior study
- Statistical confidence reporting
- Parameter stability analysis

---

## 8. Live-Trading Transition — Future Only

Real-money execution is not part of V1.

Any future live-trading transition must be treated as a separate engineering phase and require additional safeguards.

At minimum, review:

- Production credential isolation
- Separate live configuration
- Smaller exposure limits
- Kill switch
- Monitoring / alerts
- Position recovery
- Exchange outage procedures
- Protection verification
- Live slippage behavior
- Operational runbook
- Additional supervised testing

V1 must not be converted to live trading by a simple configuration toggle.

---

## 9. Suggested V2 Backlog

| Area | Improvement | Status |
|---|---|---|
| UI | Web dashboard | Backlog |
| Storage | PostgreSQL | Backlog |
| Packaging | Docker | Backlog |
| Deployment | Cloud | Backlog |
| Automation | CI/CD | Backlog |
| Alerts | Notifications | Backlog |
| Markets | ETH / other pairs | Backlog |
| Analysis | Advanced order flow | Backlog |
| Evaluation | Walk-forward backtesting | Backlog |
| Analysis | Better regime classification | Backlog |
| AI | Model comparison | Backlog |
| Engineering | Strategy versioning | Backlog |
| Safety | Live-trading transition plan | Backlog |

---

## 10. GitHub

Create GitHub issues with the label:

```text
enhancement
```

for future work that is accepted into V2.

Do not add V2 features to V1 solely because they are interesting.

---

## 11. V2 Status

```text
BACKLOG ONLY
```
