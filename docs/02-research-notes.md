# Engineering Validation Report for a V1 AI-Assisted Bybit BTCUSDT Perpetual Trading System


> **Citation note:** This repository copy replaces ChatGPT-internal citation tokens with portable source labels such as `[S1]`, `[S2]`. The corresponding source names are retained in the source list near the end of this document.
## Executive Summary and Bybit API Findings

**Executive Summary**

**Engineering recommendation:** The proposed V1 is technically feasible with Bybit as the only required exchange/data source. The cleanest architecture is:

**Bybit mainnet public REST/WebSocket market data → deterministic normalization/features → compact structured market-context snapshot → LLM analyst → strict schema/semantic validator → independent deterministic risk engine → manual approval → Bybit Demo REST execution → Demo private WebSocket confirmation/reconciliation → CSV/JSON journal.**

The most important architectural conclusion is that **Bybit Demo Trading is not the same environment as Testnet**. Bybit's current Demo documentation says Demo Trading is an isolated service with its own UID; authenticated Demo REST uses `api-demo.bybit.com`, Demo private WebSocket uses `stream-demo.bybit.com`, Demo does not support WebSocket order-entry, and public market data should come from the ordinary mainnet public stream because that public data is identical to mainnet. Bybit specifically warns against creating a Demo API key from Testnet. [S20]

For the requested live inputs, Bybit V5 exposes 15-minute, 1-hour and 4-hour klines; order-book snapshots and deltas; public trades with taker side; open interest; funding history; account long/short ratios; and a real-time all-liquidation stream. Therefore, **no paid external data vendor is required for V1 live forward testing**. [S3][S5][S9][S12][S15][S13][S14]

The principal Bybit data limitation is historical microstructure rather than live availability. REST order book is a current snapshot, while the WebSocket supplies live deltas. Liquidations are exposed as a live WebSocket stream. Recent public trades are available through REST and Bybit points users to downloadable archives for older public trades. Consequently, a V1 that may later need historical order-flow replay should **record its own normalized order-book, trade and liquidation streams from day one**. [S5][S9][S6][S15]

The LLM should not be the trading system's controller. Empirical research has documented hallucination problems in financial LLM tasks, while a 2026 review of LLM trading-agent literature found serious weaknesses in reproducibility, transaction-cost modeling and evaluation protocol consistency. [S40][S41] The strongest V1 design therefore makes the LLM a **bounded analyst/proposal generator**, not an executor or risk authority.

The recommended chain is:

```text
LIVE BYBIT MAINNET PUBLIC DATA
            │
            ▼
  Normalization + Health Checks
            │
            ▼
 Deterministic Feature Engine
            │
            ▼
 Structured Market Context
            │
     ┌──────┴──────┐
     │             │
Preconditions      LLM Analyst
     │             │
     └──────┬──────┘
            ▼
   Schema + Semantic Validation
            │
            ▼
  INDEPENDENT RISK ENGINE
            │
         PASS?
       No │ │ Yes
          ▼ ▼
    NO TRADE     Manual Approval
                       │
                       ▼
              Final Freshness/
              Account Preflight
                       │
                       ▼
                BYBIT DEMO REST
                       │
              ┌────────┴─────────┐
              ▼                  ▼
      Demo Private WS       REST Reconcile
              │                  │
              └────────┬─────────┘
                       ▼
                 CSV / JSON Log
```

The strongest fail-safe rule for this architecture is:

> **Any uncertainty in a critical prerequisite causes NO TRADE, not best-effort execution.**

That includes stale data, uncertain order-book state, lost private connectivity, malformed LLM output, invalid risk geometry, an unexpected existing position, ambiguous order status after a timeout, an expired human approval, or a mismatch between the approved proposal and the state immediately before submission.

For terminology throughout this report:

**Verified fact** means explicitly supported by primary documentation or research.
**Engineering recommendation** means my architecture judgment.
**Inference** means a conclusion derived from multiple documented facts.
**Uncertainty** means the documentation reviewed does not establish the behavior strongly enough to rely upon it.

**Bybit API Findings**

### Market and timeframe feasibility

**Verified fact:** Bybit V5's Kline endpoint covers USDT contracts and accepts intervals including `15`, `60`, and `240`, directly matching your 15m, 1H and 4H hierarchy. REST Kline requests support up to 1,000 candles per request. [S3]

Bybit's Kline WebSocket similarly supports those intervals. Importantly, its payload contains a `confirm` field: `true` means the candle is closed, while `false` identifies a still-forming candle. Bybit states Kline updates are pushed at frequencies between one and 60 seconds. [S4]

**Engineering recommendation:** Indicator and structural calculations that affect entry eligibility should use **confirmed closed bars only**. An incomplete bar may be exposed separately as informational context but should not silently replace a closed bar. This mirrors a failure mode that Freqtrade explicitly guards against: it removes incomplete candles by default because indicators evaluated on incomplete bars can create misleading signals. [S31]

### Order book

**Verified fact:** `/v5/market/orderbook` provides a snapshot; linear/inverse contracts can request as many as 1,000 levels. Bybit supplies several useful clocks/sequence fields: `ts` is a system timestamp, `u` is the update identifier, `seq` is a cross sequence, and `cts` is the matching-engine timestamp. Bybit specifically says `cts` can be correlated with the public-trade `T` timestamp. RPI orders are excluded from the API-visible order book. [S5]

The public order-book WebSocket is substantially more useful for order-flow work. For linear/inverse contracts, documented depths/frequencies include approximately:

| Depth | Documented push frequency |
|---:|---:|
| 1 | 10 ms |
| 50 | 20 ms |
| 200 | 100 ms |
| 1000 | 200 ms |

Bybit sends an initial snapshot followed by deltas whenever the book changes. A new snapshot must replace the local book. Delta entries with size zero delete a price level; a missing level should be inserted; an existing level should be updated. Level 1 is snapshot-only, and Bybit may resend an unchanged L1 snapshot after three seconds. Bybit also documents that an update ID of `1` can occur after a service restart and should cause the local book to be overwritten. [S6][S7][S8]

**Engineering recommendation:** Use **L50** initially. It gives much more useful near-book context than L1 while avoiding the storage and computational noise of maintaining 1,000 levels at 200 ms cadence. Make depth configurable so L200 can be evaluated later without redesigning the adapter.

### Public trades

**Verified fact:** REST `/v5/market/recent-trade` supplies price, size, taker side, execution identifier, execution time and sequence information; linear/inverse requests can return up to 1,000 entries. Bybit also points users to downloadable archived historical trade data. [S9]

The public-trades WebSocket is real time. For futures/spot, one WebSocket message can contain up to 1,024 trades, and more than one message can share a sequence number. Each trade includes matched time `T`, taker side, size, price and trade ID, while records in the payload are ordered by matched time. [S10][S11]

That is sufficient to calculate exchange-local aggressive buy volume versus aggressive sell volume without inferring aggressor direction yourself.

### Open interest

**Verified fact:** `/v5/market/open-interest` supports USDT contracts and sampling intervals of `5min`, `15min`, `30min`, `1h`, `4h`, and `1d`. The maximum page is 200 rows, cursor pagination is available, and the upper historical boundary can extend to the symbol's launch time. Bybit cautions that extreme volatility can introduce increased latency or temporary data delays. For linear BTCUSDT, Bybit documents open interest in BTC units. [S12]

**Engineering recommendation:** Do not pretend OI is tick-level order flow. Align OI observations with their documented sampling timestamps and treat OI change as a slower derivatives-state feature.

### Funding

**Verified fact:** `/v5/market/funding/history` exposes perpetual funding history, with up to 200 records per call. The funding interval is instrument-specific; Bybit directs clients to instrument information rather than assuming a universal interval. A request containing a `startTime` without an `endTime` is invalid, while an `endTime` alone can retrieve the preceding records. [S13]

**Engineering recommendation:** Query the instrument's funding interval at startup and store it in symbol metadata. Do not hard-code an eight-hour assumption.

### Long/short ratio

**Verified fact:** `/v5/market/account-ratio` defines `buyRatio` as the proportion of position holders who are net long and `sellRatio` as the proportion who are net short. It supports `5min`, `15min`, `30min`, `1h`, `4h`, and `1d`, has a maximum page size of 500, and the documented earliest start time is July 20, 2020. This endpoint carries the same extreme-volatility delay warning. [S14]

**Engineering recommendation:** Name this feature something like `account_holder_long_ratio`, not generic `long_short_ratio`, because it is specifically a ratio of position holders. Naming it precisely reduces the chance that either deterministic code or the LLM mistakes it for long/short notional volume.

### Liquidations

**Verified fact:** Bybit's `allLiquidation.{symbol}` WebSocket covers linear contracts and pushes all liquidations on the exchange every 500 ms. Events include updated timestamp, side, quantity and bankruptcy price. [S15]

**Inference:** The reviewed V5 material gives you strong **live** liquidation coverage but not an equivalent historical liquidation REST time series suitable for arbitrary replay. Therefore, historical liquidation-based backtests require either data that you record yourself or a historical market-data archive.

### Time and sequencing model

A useful V1 canonical timestamp model is:

| Source | Exchange time fields to preserve | Recommended canonical use |
|---|---|---|
| Kline | candle start/end, message timestamp | Candle/event alignment |
| Order book | `ts`, `cts`, `u`, `seq` | `cts` for engine timing; sequence for reconstruction |
| Public trade | `T`, trade ID, `seq` | Trade-event time |
| Liquidation | message `ts`, event `T` | Liquidation-event time |
| OI | observation timestamp | Slow derivatives series |
| Long/short | observation timestamp | Slow derivatives series |
| Funding | funding-rate timestamp | Scheduled derivatives state |
| Local client | UTC receipt time + monotonic clock | Latency/freshness measurement |

Bybit authentication has an explicit timestamp window condition and recommends NTP synchronization of the client's local clock. The default receive window is 5,000 ms. [S18]

**Engineering recommendation:** Every logged event should keep both:

```text
exchange_event_ts_ms
local_receive_ts_utc
```

and, where applicable:

```text
matching_engine_ts_ms
sequence
update_id
```

Never destroy the original exchange timestamps by overwriting them with a converted local datetime.

### REST and WebSocket limits

**Verified fact:** Bybit documents a default HTTP IP limit of 600 requests per five seconds per IP; crossing it can produce HTTP 403, after which the documentation instructs users to terminate sessions and wait at least ten minutes. Endpoint-level API limits are also applied per UID on a rolling one-second basis, and response headers report the applicable limit and remaining allowance. [S19]

For linear trading, documented limits include 10 requests/sec for order create, amend and cancel, while several order/history/execution/position queries are allowed at higher rates such as 50/sec. [S19]

Bybit WebSocket guidance states:

- up to 500 connection establishments per five minutes per WebSocket domain;
- a market-data connection cap at the IP/category level;
- clients should avoid frequent connection/disconnection;
- connections can disconnect at any time because of network complexity and should reconnect promptly;
- [S1] [S2] sending a ping approximately every 20 seconds is recommended.

**Engineering recommendation:** A BTCUSDT-only application should be nowhere near these limits. If V1 routinely approaches them, the architecture is polling too aggressively.

The preferred acquisition model should therefore be:

```text
REST:
    bootstrap snapshots
    slow data
    periodic reconciliation
    recovery

WebSocket:
    order book
    public trades
    liquidations
    live kline state
    private execution/order/position state
```

This is both fresher and operationally simpler than trying to poll everything.

## Demo Trading Findings and Data Availability Matrix

**Demo Trading Findings**

### Environment selection

The environment decision should be unambiguous.

| Function | Recommended environment | Why |
|---|---|---|
| Public REST market data | **Mainnet public** | Canonical live market |
| Public WebSocket market data | **Mainnet public** | Explicitly prescribed for Demo |
| Authenticated order placement | **Demo Trading REST** | No real-money execution |
| Order amend/cancel | **Demo Trading REST** | Supported |
| Account/position/order queries | **Demo Trading REST** | Supported |
| Private order/execution/position updates | **Demo private WebSocket** | Supported |
| WebSocket order entry | **Do not use** | Demo does not support it |
| Testnet | **Do not use for V1** | Unnecessary second environment |

**Verified fact:** Bybit says Demo Trading is isolated, has its own UID, uses `https://api-demo.bybit.com` for REST and `wss://stream-demo.bybit.com` for its supported private streams. The same documentation says public market data is identical to mainnet and instructs Demo users to connect to `wss://stream.bybit.com` for public data. WebSocket Trade/order-entry is not supported in Demo. [S20]

**Verified fact:** Bybit also explicitly says creating a Demo API key from Testnet Demo is meaningless; the normal process is to switch a mainnet account into Demo Trading and create a Demo API key there. [S20]

That gives you an important safety property: the application can have **unauthenticated mainnet public clients** and **authenticated Demo-only execution clients**, with no authenticated mainnet trading client anywhere in V1.

### Order capabilities

Bybit's Demo-supported endpoint list includes create, amend and cancel order; cancel-all/open-order/order-history/trade-history operations; position endpoints including position list and Trading Stop; and Demo private WebSocket topics including order, execution, position and wallet. [S20]

The general V5 order endpoint supports both market and limit orders. Bybit's market-order implementation converts a futures market request into an IOC limit order with a slippage-protection mechanism; if liquidity inside the acceptable range is unavailable, the order can fail rather than behave like an unlimited market sweep. [S21]

The same endpoint supports conditional orders, take profit, stop loss and `reduceOnly`. `orderLinkId` is a client-supplied identifier up to 36 characters and must be unique, making it particularly useful as a client-side idempotency key. [S21]

A significant Bybit-specific constraint is that an order marked `reduceOnly=true` cannot simultaneously specify TP/SL parameters. [S21]

`/v5/position/trading-stop` can create internal conditional TP/SL orders attached to a position. Bybit says these are automatically adjusted with the open position size and canceled when the position closes. Full-position and partial-position modes have different capabilities, and modifying only one side of a paired TP/SL can break the original pairing relationship. [S22]

Amend and cancel acknowledgements are asynchronous; Bybit recommends confirming final order status through WebSocket rather than treating the REST acknowledgement itself as proof of the final state. [S23][S24] This matches the create-order API, which also tells the client to use WebSocket for confirmation. [S21]

### Safe V1 order lifecycle

**Engineering recommendation:** Model execution explicitly as a state machine rather than "call API and assume success."

```text
IDLE
  ↓
CANDIDATE
  ↓
LLM_PROPOSED
  ↓
RISK_APPROVED
  ↓
AWAITING_HUMAN
  ↓
HUMAN_APPROVED
  ↓
FINAL_PREFLIGHT
  ↓
SUBMITTING
  ├─ uncertain ──> RECONCILING
  │                  │
  │                  ├─ found ──> WORKING / FILLED
  │                  └─ absent ─> controlled resubmit
  ↓
WORKING
  ├─ partial fill
  ├─ amended
  ├─ cancelled
  ↓
POSITION_OPEN
  ↓
PROTECTION_VERIFIED
  ↓
EXITING
  ↓
CLOSED
```

Do not automatically retry a timed-out `POST /v5/order/create`. First query/reconcile using its unique `orderLinkId`. Bybit itself has an "invalid duplicate request" error class, and client-generated order IDs give you an explicit mechanism for determining whether an apparently failed request actually reached the server. [S26][S21]

### Protection policy

**Engineering recommendation:** An approved entry is not considered operationally complete until exchange-side protective state has been verified.

A safe implementation can test two patterns in Demo:

1. submit compatible TP/SL fields together with the original entry request and verify them after fill; or
2. confirm the fill, immediately call the position `trading-stop` endpoint, and verify the resulting stop/TP state.

The exact pattern should be chosen after integration tests for market fills, limit partial fills, stop attachment and reconnect scenarios. V1 should not silently leave an unprotected position because a secondary API call failed.

### Retention

**Verified fact:** Bybit says Demo Trading orders are retained for **seven days**. Demo's standard rate limit is not upgradeable. [S20]

**Engineering recommendation:** Your CSV/JSON journal is therefore not merely convenient. It is your durable V1 research record. Store request, acknowledgement, WS lifecycle events and reconciled terminal state locally before Bybit's Demo history expires.

### Demo versus live behavior

**Verified fact:** Bybit describes Demo as following the basic trading rules of real trading, but also says not every API is available and explicitly documents Demo-specific differences such as seven-day order retention and lack of WebSocket order-entry. [S20]

**Uncertainty:** The reviewed official documentation does **not** establish that Demo queue position, fill probability, market impact or slippage reproduce production trading perfectly.

Therefore:

**Engineering recommendation:** Treat Demo as an **execution-integration and forward-observation environment**, not as proof that future live fills would equal Demo fills.

### Data Availability Matrix

| V1 requirement | Direct Bybit source | Live? | Useful history | Key limitation | V1 judgment |
|---|---|---:|---:|---|---|
| BTCUSDT perpetual | V5 linear instruments/market APIs | Yes | N/A | Instrument rules can change | **Required: Bybit** [S16][S17] |
| 15m candles | REST + Kline WS | Yes | REST pagination | 1,000/request | **Fully adequate** [S3][S4] |
| 1H candles | REST + Kline WS | Yes | REST pagination | Same | **Fully adequate** [S3] |
| 4H candles | REST + Kline WS | Yes | REST pagination | Same | **Fully adequate** [S3] |
| Order book | REST snapshot + WS | Yes | Not equivalent full historical V5 book | RPI excluded | **Adequate live; self-record** [S5][S6] |
| Public trades | REST + WS | Yes | Archive available | Venue-specific | **Fully adequate** [S9][S10] |
| Open interest | REST | Periodic | To symbol launch, subject to API pagination | Can lag in volatility | **Adequate** [S12] |
| Funding | REST | Scheduled | Yes | Interval instrument-specific | **Adequate** [S13] |
| Long/short ratio | REST | Periodic | From July 20, 2020 | Holder ratio, not notional positioning | **Adequate** [S14] |
| Liquidations | WS | Yes, 500 ms feed | Not equivalent REST archive found | Live-centric | **Adequate live; self-record** [S15] |
| Aggressive buy/sell | Public-trade taker side | Yes | Trades can be archived | Only Bybit activity | **Derivable** [S9][S10] |
| Bid/ask imbalance | L2 book | Yes | Must self-record for faithful replay | Spoof/cancel noise; RPI omission | **Derivable with caveats** [S6] |
| Demo positions/orders | Demo REST + private WS | Yes | Seven days on Demo | Demo-specific | **Fully adequate** [S20] |
| Demo executions | Demo REST + private WS | Yes | Seven days on Demo | One order may have multiple executions | **Fully adequate** [S25][S20] |

### External-data decision

**Required:** None for the stated V1.

**Useful but optional later:** a specialist historical market-data archive becomes useful if you decide that pre-launch backtesting must faithfully reproduce historical L2-book deltas, liquidations or other microstructure data that you were not already recording.

**Not justified for V1:** a paid cross-exchange derivatives service, an aggregated order-flow vendor, a secondary execution platform or a third-party trading SaaS. Those add vendor semantics, synchronization problems and another failure surface without solving a current V1 requirement.

**Inference:** Since Bybit provides the live variables you specified, the highest-value "external data" investment right now is not another vendor; it is **high-quality local recording of Bybit's own event streams**.

## Existing-System Comparison and AI Architecture Comparison

**Existing-System Comparison**

The point of reviewing mature systems is not to inherit their full stacks. It is to copy the parts that encode lessons from real trading-system engineering.

| System | Ideas worth copying | Ideas not needed in V1 |
|---|---|---|
| Freqtrade | Dry-run mindset; explicit historical backtesting; on-exchange stops; protections; dropping incomplete bars; lookahead-bias testing; exchange integration tests | Multi-pair management, web UI, Telegram, SQLite persistence, optimization ecosystem, broad CCXT abstraction |
| Hummingbot | Explicit connector layer; order lifecycle/state tracking; REST+WS reconciliation; order tracking before API submit; market-data/strategy/execution separation; kill-switch thinking | Multi-exchange/HFT breadth, DEX Gateway, market-making infrastructure, broad orchestration |
| 3Commas | Separation of trade intent/conditions from exchange operations; managed conditional-order workflow | SaaS dependency, cloud intermediary, proprietary layer, automated bot management |
| NautilusTrader | Typed configuration and reusable separation of strategy logic from venues | Rust core, broad multi-asset platform, production-scale framework complexity |

### Freqtrade lessons

Freqtrade officially supports futures exchanges including Bybit and provides dry-run and historical backtesting modes. Its persistence/UI/multi-exchange footprint is considerably larger than your V1 requires. [S27]

Several design decisions are directly useful:

Freqtrade's protection system includes StoplossGuard, MaxDrawdown and CooldownPeriod concepts. [S30] For your system, these translate well into a daily-loss lock, maximum-consecutive-loss observation and post-failure cooldown.

Freqtrade supports exchange-side stops for Bybit futures, reflecting the broader design principle that protective exits should not depend solely on the client remaining online. [S29]

Its development guide explicitly calls for unit tests, online exchange compatibility tests, extended historical-data checks for holes, market-order/limit-order/cancel testing, complete entry-to-exit tests and fee/result reconciliation. It also specifically discusses dropping incomplete candles. [S31]

Freqtrade additionally provides a lookahead-analysis facility that deliberately runs altered backtests to detect lookahead bias. [S32]

**Engineering recommendation:** Copy those testing disciplines, not the application.

### Hummingbot lessons

Hummingbot's connector architecture places order-book tracking and user-stream tracking behind exchange connector objects. [S33] More importantly, its documented order lifecycle starts tracking an order **before** sending the exchange API request, then continues tracking until completion, cancellation, expiry or failure. [S34]

That pattern is exactly right for this project:

```text
create local intent
→ persist intent
→ begin state tracking
→ submit exchange request
→ merge REST acknowledgement and WS events
→ reconcile until terminal state
```

It prevents the common mistake of treating a synchronous HTTP response as the lifecycle.

Hummingbot Strategy V2 also explicitly separates market-data access, controllers and self-contained execution-related components. [S35]

**Engineering recommendation:** Borrow the modular boundaries while keeping your implementation vastly smaller.

### 3Commas lessons

3Commas' current developer documentation exposes REST-based strategy/trading APIs, including Simple Trading and SmartTrade-style workflows that create, manage and close trades under predefined conditions. [S37][S38] It also offers backtesting-oriented tooling.

The useful conceptual lesson is **separation of trade intent from execution management**.

The actual platform is a poor V1 fit because your specification explicitly favors local Python and minimal infrastructure. Adding 3Commas would insert another authenticated intermediary and another set of state semantics between your risk engine and Bybit.

### NautilusTrader lessons

NautilusTrader emphasizes reusable strategy logic across instruments/venues and typed configuration while exposing Python on top of a performance-oriented core. [S39]

For V1, the lesson is simply: define strict typed interfaces between market state, strategy analysis, risk and execution. Do not adopt its full technology stack.

**AI Architecture Comparison**

| Dimension | Pure rule-based | Pure LLM | Hybrid deterministic + LLM |
|---|---|---|---|
| Determinism | High | Low/medium | High around critical boundaries |
| Reproducibility | High | Weakest | Good if context/model/prompt logged |
| Explainability | Explicit rules | Natural-language rationale but can be unreliable | Rules + bounded rationale |
| Unit testing | Excellent | Difficult | Excellent for deterministic layers |
| Context synthesis | Limited unless hand-coded | Strong | Strong |
| Hallucination exposure | None from LLM | Maximum | Contained |
| Latency | Low | Highest | Moderate |
| Risk isolation | Strong | Poor if LLM controls execution | Strong |
| Structured output | Native | Must constrain/validate | Constrain + validate |
| Failure behavior | Predictable | Can fail semantically despite valid syntax | Can fail closed |
| Suitability here | Viable but less flexible | **Reject** | **Recommended** |

### Pure deterministic rules

A pure rule engine is the easiest architecture to unit-test and reproduce. Every condition can be traced to an input value.

Its weakness for your intended experiment is that it forces all qualitative context synthesis—market regime, conflicting timeframes, derivative context, structure quality—into increasingly complicated handcrafted rule trees.

For a non-LLM baseline, however, it is extremely valuable.

**Engineering recommendation:** Maintain a deterministic baseline signal path even if it only outputs `ELIGIBLE_CONTEXT` / `NOT_ELIGIBLE`. The hybrid system should be measured against something simpler.

### Pure LLM

A pure LLM trading controller would accept market information, choose direction/size/entry/SL/TP and send the order.

That architecture is inappropriate here.

Empirical work specifically examining LLMs on financial tasks reports serious hallucination behavior. [S40] A 2026 review of agentic financial trading literature also found substantial weaknesses in reproducible protocols, explicit transaction-cost modeling and execution-semantics reporting. [S41]

An output may also be perfectly valid JSON and still be economically or operationally nonsensical.

### Hybrid system

The hybrid pattern preserves LLM strengths—contextual synthesis, weighing conflicting evidence, concise rationale—while moving irreversible and objectively checkable decisions to deterministic software.

The LLM may answer:

```json
{
  "decision": "LONG",
  "setup_quality": 72,
  "rationale": "...",
  "entry": 123.45,
  "stop_loss": 120.00,
  "take_profit": 130.00
}
```

But this is a **proposal**, not an order.

The risk engine subsequently decides whether those numbers are valid.

### Raw data versus preprocessed context

**Engineering recommendation:** Give the LLM **preprocessed structured market context**, not raw WebSocket feeds.

A suitable input might resemble:

```json
{
  "snapshot_id": "btc-20260921T...",
  "symbol": "BTCUSDT",
  "decision_time_utc": "...",
  "data_quality": {
    "critical_ok": true,
    "orderbook_age_ms": 83,
    "trade_stream_age_ms": 14,
    "private_stream_ok": true
  },
  "timeframes": {
    "4h": {
      "last_closed_bar": "...",
      "trend_state": "...",
      "volatility": "...",
      "key_levels": []
    },
    "1h": {
      "structure_state": "...",
      "swing_highs": [],
      "swing_lows": []
    },
    "15m": {
      "setup_features": {},
      "last_closed_candles_summary": {}
    }
  },
  "derivatives": {
    "open_interest": {},
    "funding": {},
    "account_long_short": {},
    "liquidations": {}
  },
  "order_flow": {
    "spread_bps": 0,
    "depth_imbalance_5": 0,
    "depth_imbalance_25": 0,
    "aggressive_buy_volume_60s": 0,
    "aggressive_sell_volume_60s": 0
  }
}
```

This has five advantages: input units are known, timestamps are explicit, feature computation is reproducible, token usage stays bounded, and the model cannot silently perform a different indicator calculation from one invocation to the next.

You can include a **small supporting raw slice**—for example top-of-book levels or recent aggregated candle values—but the LLM should not be expected to reconstruct an L2 order book or calculate RSI from thousands of raw messages.

## Recommended Hybrid Architecture and Risk-Engine Recommendations

**Recommended Hybrid Architecture**

### Responsibility boundary

The cleanest division of authority is:

| Capability | Deterministic software | LLM | Human |
|---|---:|---:|---:|
| Fetch market data | Yes | No | No |
| Normalize timestamps | Yes | No | No |
| Indicators | Yes | No | No |
| Market-structure primitives | Yes | No | No |
| Order-flow aggregation | Yes | No | No |
| Data freshness | Yes | No | No |
| Summarize conflicting evidence | No | Yes | Optional |
| LONG/SHORT/NO TRADE proposal | No | Yes | Reviews |
| Setup-quality assessment | No | Yes | Reviews |
| Proposed entry/SL/TP | No | Yes | Reviews |
| Position size | **Yes** | No | Reviews |
| Enforce max loss | **Yes** | No | No override |
| Validate stops | **Yes** | No | No override |
| Override risk rejection | **Never** | Never | Never in V1 |
| Approve submission | No | No | **Yes** |
| Construct Bybit request | **Yes** | No | No |
| Send order | **Yes after approval** | No | No |
| Cancel/modify protection | **Yes under predefined rules** | No | No |

The key architectural invariant should be:

> **The LLM has no reference to the authenticated exchange client.**

That makes direct LLM execution impossible by construction rather than merely prohibited by a prompt.

### LLM output contract

Use a strict schema resembling:

```text
decision:
    enum {LONG, SHORT, NO_TRADE}

setup_quality:
    bounded integer

rationale:
    concise evidence-based explanation

supporting_evidence:
    array of feature IDs / observations

contradicting_evidence:
    array

entry:
    nullable decimal

stop_loss:
    nullable decimal

take_profit:
    nullable decimal

invalidation:
    concise text

assumptions:
    array
```

Do not request free-form fields for leverage, account risk percentage or position quantity.

Pydantic supports direct JSON parsing/validation through `model_validate_json()` and strict model specifications, making it a suitable Python boundary for this output. [S42][S43]

### Validation stages

A response must pass four separate checks:

```text
LLM TEXT
   │
   ▼
JSON parsing
   │
   ▼
Schema validation
   │
   ▼
Semantic validation
   │
   ▼
Risk validation
```

Schema-valid is not risk-valid.

For example, this may be valid JSON:

```json
{
  "decision": "LONG",
  "entry": 100,
  "stop_loss": 110,
  "take_profit": 90
}
```

but deterministic semantics must reject it.

For a simple V1 long:

```text
stop_loss < entry < take_profit
```

For a simple V1 short:

```text
take_profit < entry < stop_loss
```

Additional validators should reject NaN/infinity, out-of-range prices, impossible tick increments, stale proposals and proposal prices too far from the current market according to a configured tolerance.

### Malformed output

**Engineering recommendation:** Use one bounded retry containing the validation error and requesting a complete replacement object. If it still fails:

```text
decision = NO_TRADE
failure_reason = LLM_SCHEMA_FAILURE
```

Never guess missing stop prices. Never silently coerce a SHORT to LONG. Never "repair" economically meaningful numbers behind the user's back.

### Reproducibility record

Every model invocation should log:

```text
model/provider identifier
prompt version
schema version
market snapshot ID
market snapshot hash
feature-engine version
response
parsed response
validation errors
retry count
final accepted/rejected status
```

This does not make the LLM deterministic, but it makes the experiment auditable.

**Risk-Engine Recommendations**

### Risk engine must be independent

The risk engine should consume only:

```text
validated trade proposal
current normalized market state
current Demo account state
static/versioned risk configuration
```

It should not consume LLM prose as an instruction.

Its result should be something like:

```json
{
  "approved": false,
  "reason_codes": [
    "RR_BELOW_MINIMUM",
    "MARKET_DATA_STALE"
  ]
}
```

### Position sizing

For BTCUSDT linear perpetual, an engineering-level risk calculation can be expressed approximately as:

\[
RiskBudget = Equity \times ConfiguredRiskFraction
\]

and, before fees/slippage adjustments,

\[
Quantity_{BTC}
\approx
\frac{RiskBudget_{USDT}}
{|Entry-Stop|}
\]

because linear BTCUSDT PnL is fundamentally related to BTC quantity multiplied by the price move.

Then:

```text
raw quantity
→ subtract/allow for fee and slippage assumptions
→ floor to valid quantity step
→ enforce exchange minimum/maximum
→ enforce notional/margin/leverage caps
```

Current tick-size, quantity-step and other symbol specifications should be pulled from Bybit's instrument-information endpoint rather than hard-coded permanently. Bybit describes this endpoint as providing instrument specifications for online pairs. [S16]

**Engineering recommendation:** Make `risk_per_trade` a configuration input, not an LLM field. There is no engineering justification for claiming a particular percentage is profitable.

For Demo V1, a small fixed risk budget or small configurable percentage is preferable because the purpose is system validation, not return maximization.

### Minimum risk/reward

Use a deterministic configurable field such as:

```text
min_reward_to_risk
```

with:

\[
RR =
\frac{|TakeProfit-Entry|}
{|Entry-Stop|}
\]

The threshold itself is a strategy/test parameter, not a universally correct number.

### Daily loss guard

Track both realized session loss and outstanding worst-case risk.

A useful engineering representation is R-units:

```text
1R = configured intended loss on a normal trade
```

Then the daily lock can be configured as a maximum number of R, or as an account-equity percentage.

Once exceeded:

```text
new entries = disabled
existing protection = left active
manual reset = prohibited until configured reset condition
```

This is a safety circuit breaker, not a profitability mechanism.

### Maximum positions

Because V1 trades one instrument, the cleanest rule is:

```text
maximum BTCUSDT directional positions = 1
maximum concurrent entry intents = 1
```

**Engineering recommendation:** Do not pyramid, hedge long against short, scale into losing positions, or run multiple competing BTCUSDT strategies in V1. Every one of those adds state-machine ambiguity.

### Existing-position guard

Immediately before execution:

```text
if open BTCUSDT position != expected:
    reject

if open BTCUSDT entry order exists:
    reject

if protective/conditional order state unexpected:
    reject
```

### Duplicate-order prevention

Use three levels:

```text
unique intent_id
        ↓
unique Bybit orderLinkId
        ↓
local persistent state-machine lock
```

On timeout:

```text
DO NOT blindly POST again
        ↓
query/reconcile orderLinkId
        ↓
resubmit only if conclusively absent
```

Bybit supports custom unique `orderLinkId` values, while its error catalog explicitly includes duplicate-request handling. [S21][S26]

### Stale-data guard

Risk should reject independently of what the LLM thinks.

Suggested configurable categories:

| Data | Example V1 policy |
|---|---|
| Order book | Very short age threshold; require healthy WS |
| Public trades | Short threshold plus public-stream health |
| 15m bar | Most recent required closed bar present |
| 1H/4H bars | Most recent expected closed bar present |
| OI | No older than expected source cadence + grace |
| L/S ratio | Same principle |
| Funding | Current/latest expected observation |
| Private account | Fresh REST/WS state immediately before entry |
| Human approval | Must not exceed approval TTL |

The exact millisecond thresholds should come from measured behavior during forward testing, rather than being treated as universal constants.

### Account-state validation

Preflight should verify:

```text
authenticated endpoint = Demo
symbol = BTCUSDT
account state readable
balance valid
position mode expected
margin/leverage configuration expected
no conflicting position
no conflicting active entry
private state channel healthy or REST reconciliation successful
risk limits loaded successfully
```

If any one is unknown, the appropriate default is NO TRADE.

### Multi-timeframe hierarchy assessment

Your proposed hierarchy is technically coherent:

```text
Market regime
    ↓
4H higher-timeframe trend
    ↓
1H structure
    ↓
Key levels
    ↓
15m setup
    ↓
Derivatives context
    ↓
Order-flow context
    ↓
Volatility
    ↓
Risk/reward
    ↓
LONG / SHORT / NO TRADE
```

Its primary strength is **coarse-to-fine information flow**: slow context is established before fast execution evidence is considered.

The main weaknesses are redundancy and potential over-conditioning.

"Market regime", "4H trend", "1H structure", support/resistance and volatility may be correlated representations of some of the same price behavior. If each becomes an independent hard gate, the resulting strategy can become a brittle collection of filters with few observations and large data-mining risk.

Derivatives and order-flow evidence likewise should not automatically become a growing list of mandatory confirmations merely because the data exists.

**Engineering recommendation:** Separate three concepts:

```text
CONTEXT:
    regime
    4H
    1H
    levels

SETUP:
    15m
    volatility
    attainable R/R

CONFIRMATION:
    OI
    funding
    long/short
    liquidations
    trade imbalance
    book imbalance
```

Then define exactly which fields are eligibility requirements and which are descriptive evidence.

Do not let the LLM invent new hierarchy rules during testing.

At every 15m evaluation, use the most recently **confirmed** 4H/1H/15m bars. Bybit explicitly provides candle confirmation status for this purpose. [S4]

### Order-flow feature set

A reasonable V1 can derive the following without pretending to reconstruct the entire market:

\[
BookImbalance_N =
\frac{\sum BidQty_N-\sum AskQty_N}
{\sum BidQty_N+\sum AskQty_N}
\]

Calculate it for a small set such as top 5, 10, 25 or 50 levels.

Also useful:

```text
best-bid / best-ask spread
spread in basis points
depth inside ±X bps
distance-weighted bid/ask depth
aggressive buy volume over fixed window
aggressive sell volume over fixed window
signed trade-volume imbalance
largest nearby liquidity concentrations
short-window liquidation buy/sell volume
imbalance persistence rather than one snapshot
```

Bybit exposes taker side directly in public trades, so signed/aggressive-volume measures do not require a heuristic aggressor classifier. [S9][S10]

The order book should be interpreted cautiously. Bybit excludes RPI orders from the API-visible book, so even the Bybit book is not literally every executable intention on the venue. [S5][S6]

More fundamentally:

**Inference:** visible limit orders are intentions, not commitments. Orders can be canceled quickly, large displayed liquidity can disappear, and one exchange provides only one exchange's microstructure.

Therefore V1 should avoid claims such as:

```text
"large bid = institutional support"
```

A more defensible feature is:

```text
"bid depth within 10 bps was X% greater than ask depth
for Y% of observations over the last Z seconds"
```

That is measurable and testable.

Postpone:

```text
spoofing classifiers
queue-position estimation
deep order-book neural networks
microsecond event prediction
cross-exchange consolidated books
historical L2 footprint reconstruction
```

Those require substantially more data and validation than V1 needs.

## Data Quality / Reliability Design and Testing Methodology

**Data Quality / Reliability Design**

### Normalize by event semantics, not just timestamps

A robust event wrapper should look conceptually like:

```python
NormalizedEvent(
    source="bybit",
    environment="mainnet_public",
    symbol="BTCUSDT",
    event_type="orderbook_delta",
    exchange_ts_ms=...,
    matching_engine_ts_ms=...,
    local_receive_ts=...,
    monotonic_receive_ns=...,
    sequence=...,
    update_id=...,
    payload=...
)
```

Bybit exposes materially different timestamps for different purposes. Order-book `cts` represents matching-engine timing and can be correlated with trade `T`; `ts` is the system-generated timestamp. [S5][S8]

Do not reduce all of those to a single `timestamp`.

### Clock synchronization

Bybit's authentication rules constrain the client's timestamp relative to server time and explicitly recommend NTP synchronization. [S18]

**Engineering recommendation:**

```text
NTP healthy?
  No → execution disabled
  Yes → continue
```

Monitor clock offset and log it periodically.

### Order-book recovery

The reconstruction algorithm should follow Bybit semantics:

```text
connect
→ receive snapshot
→ replace local book
→ process deltas
→ if Bybit emits a new snapshot:
       replace local book
→ if u == 1 / restart signal:
       replace local state from snapshot
→ if continuity becomes uncertain:
       mark book INVALID
       reacquire snapshot/state
       do not trade until healthy
```

Bybit explicitly says a newly pushed snapshot replaces the local book and documents update ID `1` as a possible service-restart condition. [S6][S7]

Do not assume that every integer sequence must increment exactly by one unless the specific stream contract guarantees that semantics. Use documented ordering plus your own continuity/health checks.

### Duplicate handling

Recommended keys:

```text
public trade:
    trade ID primarily

liquidation:
    event timestamp + side + price + size,
    with sequence/message metadata where available

order lifecycle:
    orderId + state/update identity

execution:
    execId primarily

local intent:
    intent_id / orderLinkId
```

Bybit notes that one order may generate multiple executions and warns that execution-history records sharing the same `execTime` can have sorting ambiguity; it recommends additional fields such as execution/order identifiers and leaves quantity for ordering. [S25]

### Reconnect policy

Bybit says WebSocket disconnection can occur because of network complexity and tells clients to reconnect promptly. It also recommends periodic ping messages and imposes connection-establishment limits. [S1][S2]

Use:

```text
connection lost
→ data-health state = UNHEALTHY immediately
→ trading proposals disabled
→ reconnect with bounded exponential backoff + jitter
→ rebuild snapshots
→ refill short rolling feature windows
→ verify timestamps/sequences
→ only then mark HEALTHY
```

Avoid tight reconnect loops because Bybit limits connection establishments. [S2]

### Freshness should be feature-specific

A 500 ms liquidation feed and a 4H candle obviously require different freshness semantics.

Recommended health-state representation:

```text
HEALTHY
DEGRADED
STALE
UNKNOWN
```

and:

```text
critical component != HEALTHY
    => no new trade
```

The threshold values should be configurable and empirically observed.

### Extreme volatility

Bybit explicitly warns that open-interest, long/short and instrument-information interfaces can experience increased latency or temporary data delays during extreme volatility. [S12][S14][S16]

That matters because high-volatility periods are precisely when a trading engine may be most tempted to act.

**Engineering recommendation:** Volatility should tighten, not relax, data-quality discipline.

Examples:

```text
spread beyond configured sanity bound → NO TRADE
book state recovering → NO TRADE
derivatives endpoint unexpectedly stale → NO TRADE
price moves outside approved entry tolerance → approval expires
```

### Fail-safe policy

A strong V1 policy is:

```text
IF uncertain before a new entry:
    NO TRADE

IF order submission status is uncertain:
    RECONCILE before retry

IF already in position and analysis data fails:
    DO NOT remove existing protection

IF protection state becomes uncertain:
    escalate execution-risk state immediately

IF risk configuration cannot load:
    execution disabled

IF environment identity cannot be proven Demo:
    execution disabled
```

This is intentionally asymmetric: missed trades are acceptable; accidental duplicated or unbounded-risk trades are not.

**Testing Methodology**

### Unit tests

Unit-test all deterministic logic without network access:

```text
indicator formulas
bar aggregation
closed-bar selection
market-structure state
support/resistance calculations
order-flow aggregation
timestamp conversion
sequence handling
freshness states
schema validation
long/short price geometry
R/R calculation
position sizing
quantity rounding
daily-loss guard
duplicate-intent guard
approval expiry
state-machine transitions
```

Each risk rejection should have a test that proves it rejects and a neighboring test that proves a valid case passes.

### Indicator verification

For important indicators, compare at least two of:

```text
hand-calculated fixture
trusted reference library
independent implementation
known historical examples
```

Edge cases matter more than the happy path:

```text
insufficient warmup bars
zero volume
flat prices
missing candle
duplicated candle
very large candle
NaN
timezone boundary
```

### Historical scenario tests

These are not necessarily strategy backtests.

Use deterministic saved scenarios such as:

```text
steady trend
range
sharp breakout
gap-like move
high volatility
liquidation burst
WS disconnect
stale OI
large spread
partial entry fill
```

Replay them and verify that the **system state** is correct.

Historical simulations are especially vulnerable to data-mining and selection effects. Research on backtest overfitting shows that choosing the best result among many tested configurations can produce deceptively strong in-sample performance that fails out of sample. [S44]

### Integration tests

Against actual Bybit public endpoints and Demo:

```text
REST bootstrap
WS subscribe
WS reconnect
order-book rebuild
market entry
limit entry
limit amend
cancel
partial fill if reproducible
TP
SL
reduce-only exit
position query
order-history query
execution-history query
private WS event receipt
REST/WS reconciliation
```

Freqtrade's own developer guidance similarly calls for exchange-specific public tests plus real order creation, cancellation, completed-trade checks and fee/result reconciliation. [S31]

### Failure-injection tests

These are more important than hundreds of uncomplicated Demo trades.

Simulate:

```text
HTTP timeout immediately after order POST
duplicate local submit request
WS dies after fill
private WS dies before fill
mainnet public WS disconnect
out-of-order synthetic messages
malformed LLM JSON
valid JSON / invalid economics
risk engine exception
disk write failure
stale approval
unexpected position exists
Bybit rate-limit response
machine clock offset
process restart with an open Demo position
```

The last case is especially valuable: restart the Python program while a Demo position/order exists and prove that it reconstructs exchange state **before** allowing another trade.

### Forward Demo testing

Technical-system validation and strategy validation should be deliberately separated.

**Technical validation** asks:

```text
Did every event arrive?
Did the right order get placed?
Did duplicate prevention work?
Were stops present?
Was the local state reconciled?
Did logs reconstruct exactly what happened?
```

A practical engineering milestone might be **25–50 supervised Demo executions covering all execution paths**, but that number has no statistical significance. Coverage matters more than trade count.

**Strategy-performance validation** asks:

```text
Does a frozen decision process exhibit positive expectancy
after realistic costs across sufficiently varied regimes?
```

Do not draw strong conclusions from 20 or 50 trades.

For statistical intuition, assuming independent Bernoulli trades and a true win probability near 50%, the familiar 95% approximation requires roughly:

\[
n \approx \frac{1.96^2(0.5)(0.5)}{e^2}
\]

which gives approximately:

```text
±10 percentage points → ~96 observations
±5 percentage points  → ~384 observations
```

Real trades violate the independence and stationarity assumptions, so these figures are **lower-bound intuition, not proof thresholds**.

**Engineering recommendation:**

```text
<100 trades:
    preliminary only

~100 trades:
    enough to identify very large problems,
    not enough to establish a durable edge

several hundred trades across distinct regimes:
    materially stronger evidence,
    still not proof of future profitability
```

A system with 400 trades all generated in one homogeneous market regime may be less informative than a smaller but carefully segmented, pre-specified test spanning distinct conditions.

### Freeze the experiment

Once forward strategy testing begins, use:

```text
strategy_version
feature_version
prompt_version
model identifier
risk_config_version
```

If any decision rule changes, start a new experimental cohort.

Changing filters after every loss is a form of adaptive data mining, precisely the problem backtest-overfitting research warns about. [S44]

### Evaluation metrics

The user's proposed metrics are appropriate, but their importance is not equal.

\[
ProfitFactor =
\frac{GrossProfit}{|GrossLoss|}
\]

\[
Expectancy =
P(win)\times AvgWin -
P(loss)\times AvgLoss
\]

A more comparable form is expectancy in R:

\[
Expectancy_R
=
P(win)\times AvgWin_R
-
P(loss)\times AvgLoss_R
\]

Recommended priority:

| Metric | Importance | Why |
|---|---|---|
| Expectancy in R | **Very high** | Integrates win frequency and payoff size |
| Maximum drawdown | **Very high** | Captures path/risk severity |
| Profit factor | High | Gross payoff efficiency |
| Average win / average loss | High | Explains expectancy mechanics |
| Consecutive losses | High | Important operational/psychological tail behavior |
| Realized R distribution | High | Normalizes across sizing changes |
| Total PnL | Medium | Depends heavily on account size/position sizing |
| Win rate | Medium/low alone | High win rate can coexist with negative expectancy |
| Mean advertised R/R | Medium | Proposed R/R is not the same as realized R |
| Setup-type performance | Diagnostic | Useful only with enough observations |
| Regime performance | Diagnostic | Useful for stability/fragility analysis |

For this particular research system, add technical metrics:

```text
order submission success rate
order rejection rate
fill rate
partial-fill rate
slippage versus approved price
approval-to-submit latency
submit-to-ack latency
ack-to-fill latency
number of reconnects
data-staleness NO-TRADE count
LLM schema-failure rate
LLM semantic-rejection rate
risk-engine rejection reasons
duplicate-submit attempts prevented
protective-order verification failures
```

Those determine whether the software works even before discussing strategy performance.

## Security Recommendations and Risk Register

**Security Recommendations**

### V1 should make real-money trading structurally impossible

The best security decision is not secret management; it is **not having production trading credentials**.

Use separate classes/configuration:

```text
PublicMainnetClient
    no API key
    base URL fixed to mainnet public endpoints

DemoExecutionClient
    Demo key only
    authenticated host fixed to api-demo.bybit.com
```

No configuration option such as:

```text
environment = "live"
```

should exist in V1.

A production authenticated endpoint should require a future source-code change plus review, not a one-character environment setting.

### Secrets

GitHub's current guidance explicitly says never to hard-code secrets, recommends environment variables or a secret-management facility, and recommends rotation/expiration where possible. [S48]

For this local V1:

```text
BYBIT_DEMO_API_KEY
BYBIT_DEMO_API_SECRET
LLM_API_KEY
```

may be injected through environment variables or a local `.env` file that is excluded from Git.

Never commit:

```text
.env
API keys
API secrets
bearer tokens
authentication signatures
private keys
cookies/session credentials
passwords
secret-containing notebooks
debug dumps containing authentication headers
production credentials of any kind
```

Also avoid committing account-specific identifiers or raw authenticated API captures unless intentionally sanitized.

### Logging redaction

Never write authentication headers such as an API key or signature into CSV/JSON debug logs.

Log:

```text
request_id
endpoint
HTTP status
response code
latency
safe parameters
```

rather than the entire signed request.

### Git defenses

GitHub secret scanning checks repository history for hardcoded credentials, including API keys, passwords and tokens. Its push-protection feature can prevent recognized credentials from being pushed in the first place. [S46][S47]

Enable those features where available.

If a secret is accidentally committed, removing the line from the latest commit is not sufficient. GitHub recommends rotating compromised credentials; historical Git copies can persist even after content is removed from the visible branch. [S46]

### API permissions

Use the minimum Demo permissions required to create/manage orders and query account/position state. Bybit's error catalog explicitly distinguishes permission failures and also supports IP-binding-related rejection. [S26]

For V1 there is no reason to possess withdrawal-capable real-account credentials.

### Local file hygiene

CSV/JSON logs may reveal strategy logic, account balances, model outputs and exact execution history even when they contain no API secret.

Recommended:

```text
restrict filesystem permissions
back up deliberately, not automatically to public sync locations
redact secrets before diagnostic sharing
keep config and secrets separate
rotate Demo credentials periodically
```

**Risk Register**

Likelihood below is a **qualitative engineering assessment**, not a measured Bybit failure-rate statistic.

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Bybit REST/API outage | High | Medium | Fail closed; no new entries; retry with backoff; maintain exchange-side protection |
| Public WS disconnect | High | Medium | Immediate unhealthy state, reconnect, rebuild snapshots, warm features before re-enable. Bybit explicitly says disconnects may occur. [S1] |
| Stale market data | High | Medium | Per-source freshness thresholds; `STALE → NO_TRADE` |
| Incorrect local clock | High for auth/data alignment | Low–Medium | NTP; monitor offset; Bybit recommends synchronized time. [S18] |
| Timestamp semantic confusion | Medium–High | Medium | Preserve `ts`, `cts`, `T`, receipt time separately |
| Missing order-book messages/state | High | Medium | Snapshot/delta health state; invalidate/rebuild rather than guess. [S6][S7] |
| Duplicate event processing | Medium | Medium | Trade/execution IDs, idempotent state transitions |
| Malformed LLM output | Medium | Medium initially | Strict schema, one bounded retry, otherwise NO TRADE |
| Semantically invalid LLM output | High | Medium | Deterministic price/risk validation after schema validation |
| LLM hallucination | High | Medium | Structured factual context; no execution/risk authority; evidence fields; independent validation; empirical finance research documents hallucination risk. [S40] |
| Duplicate order execution | High | Low–Medium | Unique intent/orderLinkId; reconcile uncertain POST before retry |
| HTTP response lost after order accepted | High | Low–Medium | Treat status as UNKNOWN; query by orderLinkId; never blind retry |
| Demo/private WS loss during order | High | Medium | REST reconciliation; execution state machine |
| Demo/live behavior mismatch | High for future deployment conclusions | Medium | Never extrapolate Demo fills/slippage directly to production; separate future live validation |
| Extreme volatility | High | Medium | Wider safety checks; reject stale derivatives/order-book data; Bybit warns some data endpoints may delay during volatility. [S12][S14] |
| Market order not filled as expected | Medium–High | Low–Medium | Handle Bybit's market-as-IOC semantics; inspect terminal order status. [S21] |
| Stop/TP not attached correctly | Very high | Low–Medium | Protective-state verification; automated alert/controlled emergency logic |
| Order-book spoof/noise | Medium | High | Use persistence/aggregation, not single-level signals; cap weight in decision |
| Incomplete market visibility | Medium | Certain | Explicitly label Bybit-only; RPI exclusion documented. [S5] |
| Overfitting | Very high | High | Freeze definitions; limited hypothesis changes; out-of-sample/forward tests; track experiment count. [S44] |
| Strategy changes during test | High | High unless governed | Versioning; reset experimental cohort after material change |
| Human approval mistake | High | Medium | Display exact entry/SL/TP/qty/risk and expiry; require single explicit confirmation |
| Approval becomes stale | High | Medium | Short approval TTL and final market-price/freshness recheck |
| Unexpected existing position | High | Low–Medium | Hard preflight rejection; REST account reconciliation |
| Rate-limit breach | Medium | Low | WS-first design; client-side throttler; monitor headers. [S19] |
| Local application crash | High with open position | Medium | Exchange-native protection; restart reconciliation before new trading |
| Disk/log write failure | Medium | Low–Medium | Health check and fail new entries when audit persistence unavailable |
| Secret committed to Git | High | Low–Medium | `.gitignore`, push protection, secret scanning, immediate rotation. [S46][S47] |

## Recommended V1 Architecture and V2 / Deferred Features

**Recommended V1 Architecture**

### Application shape

A **single local Python application** with clearly separated modules is preferable to microservices.

There is no engineering benefit in V1 from Docker, Kubernetes, Kafka, Redis, PostgreSQL or a service mesh.

Use `asyncio` or an equivalent asynchronous networking structure for the live streams, but preserve synchronous deterministic interfaces inside the feature/risk layers where practical.

A reasonable package shape:

```text
trading_system/
│
├── config/
│   ├── settings.py
│   ├── risk.py
│   └── schemas.py
│
├── bybit/
│   ├── public_rest.py
│   ├── public_ws.py
│   ├── demo_rest.py
│   ├── demo_private_ws.py
│   └── models.py
│
├── data/
│   ├── normalizer.py
│   ├── orderbook.py
│   ├── rolling_store.py
│   ├── freshness.py
│   └── recorder.py
│
├── features/
│   ├── indicators.py
│   ├── structure.py
│   ├── derivatives.py
│   ├── orderflow.py
│   └── context_builder.py
│
├── decision/
│   ├── eligibility.py
│   ├── llm_client.py
│   ├── llm_schema.py
│   └── semantic_validator.py
│
├── risk/
│   ├── engine.py
│   ├── sizing.py
│   └── guards.py
│
├── execution/
│   ├── intent.py
│   ├── state_machine.py
│   ├── approval.py
│   ├── executor.py
│   └── reconciler.py
│
├── journal/
│   ├── events.py
│   ├── csv_writer.py
│   └── json_writer.py
│
└── tests/
```

### Public data collector

At application startup:

```text
1. Fetch symbol specification.
2. Fetch historical bars sufficient for indicator warmup.
3. Fetch initial slow derivatives values.
4. Connect public WebSocket.
5. Build L2 order-book snapshot/state.
6. Start trades.
7. Start liquidations.
8. Start relevant kline streams.
9. Wait until all critical components healthy.
10. Enable analysis.
```

Bybit's instrument-information endpoint is the appropriate source for current instrument specifications, while the dedicated market endpoints provide the relevant time series. [S16][S3][S12][S13]

### Rolling local store

You do not need a database for V1.

Maintain:

```text
4H candle deque
1H candle deque
15m candle deque
OI observations
funding observations
long/short observations
recent liquidation buckets
L2 order book
recent trade windows
calculated feature snapshots
```

in memory.

Append raw/normalized research events or aggregated snapshots to JSON/CSV as appropriate.

For high-frequency order-book deltas, raw CSV can become inefficient. Since the user specifically wants CSV/JSON and no database, a reasonable compromise is:

```text
human-analysis logs → CSV
structured decisions/trades → JSONL
raw high-frequency stream recording → optional JSONL / compressed files
```

Compression does not add architectural complexity.

### Deterministic feature engine

Every feature should return not just a value but metadata:

```json
{
  "value": 0.23,
  "as_of": "...",
  "valid": true,
  "source": "bybit_public_ws",
  "version": "orderflow_v1"
}
```

That allows stale features to be rejected before they reach the LLM.

### Decision cadence

Do not call the LLM on every public trade or book delta.

**Engineering recommendation:** Start evaluation primarily around 15-minute setup events or explicitly defined candidate changes.

For example:

```text
new confirmed 15m candle
    ↓
deterministic eligibility computation
    ↓
only if market context is potentially actionable:
       create frozen context snapshot
       call LLM
```

This reduces noise, cost and accidental prompt-dependent high-frequency behavior without inventing a specific trading strategy.

### Manual approval interface

A CLI is enough.

Display:

```text
BTCUSDT
Direction
Decision price
Proposed entry
Stop
Target
Calculated quantity
Risk budget
Proposed R/R
4H context
1H structure
15m setup summary
Derivatives summary
Order-flow summary
LLM rationale
Risk-engine PASS
Snapshot age
Approval expires at
```

Then require an explicit typed action.

The approval should contain:

```text
intent_id
snapshot_hash
approved_parameters_hash
approval_timestamp
expiry_timestamp
```

If entry/SL/TP/quantity changes afterward, the approval becomes invalid.

### Final preflight

Human approval is **not** the final API step.

Immediately before `create-order`:

```text
refresh best price
check price deviation
check public-data health
check private/account health
fetch/reconcile open positions
fetch/reconcile open orders
re-run risk checks
confirm approval TTL
confirm Demo host
```

Only then submit.

### Execution/reconciliation

Bybit order acknowledgements are asynchronous, so private WebSocket should be the primary lifecycle feed with REST reconciliation as the recovery mechanism. [S21][S23][S24]

Private Demo topics include order, execution and position, making this architecture directly supported. [S20]

### Event journal

A decision record should be able to answer, months later:

```text
What did the system know?
What were all source timestamps?
What features were calculated?
What did the LLM say?
What did deterministic validation reject/accept?
What risk did the engine calculate?
What did the human approve?
What exact API request was submitted?
What was acknowledged?
What actually filled?
What stops/TP were active?
What eventually closed the position?
What was realized PnL and R?
```

That is far more valuable for V1 than a dashboard.

**V2 / Deferred Features**

### Required now

Keep these:

| Component | V1 status |
|---|---|
| Mainnet public REST adapter | Required |
| Mainnet public WS adapter | Required |
| Demo REST authenticated adapter | Required |
| Demo private WS adapter | Required |
| Time synchronization/health | Required |
| Order-book reconstruction | Required |
| Rolling candle/derivatives state | Required |
| Technical indicators | Required |
| Explicit market-structure features | Required |
| Basic order-flow features | Required |
| Data-quality gate | Required |
| Structured market-context builder | Required |
| LLM proposal layer | Required for experiment |
| Pydantic/schema validator | Required |
| Independent risk engine | Required |
| Manual approval CLI | Required |
| Order state machine | Required |
| REST reconciliation | Required |
| CSV/JSON/JSONL journal | Required |
| Unit/integration/failure tests | Required |

### Optional but useful in V1

```text
compressed raw WS recording
simple offline trade-report script
local matplotlib charts for post-trade analysis
replay harness for recorded events
second independent indicator implementation for verification
```

None needs a persistent server or dashboard.

### Postpone to V2

```text
real-money credentials
automatic order approval
multi-symbol trading
multi-exchange trading
cross-exchange order-flow aggregation
paid historical L2/liquidation feeds
machine-learning strategy optimization
reinforcement learning
LLM self-modification
LLM-generated risk limits
LLM tool access to exchange execution
multiple simultaneous strategies
position pyramiding
hedge-mode complexity
distributed services
message broker
PostgreSQL
cloud deployment
Docker/Kubernetes
web dashboard
mobile controls
vector database / RAG infrastructure
complex news/sentiment feeds
deep-learning order-book models
spoofing classification
queue-position simulation
```

In particular, **RAG is not required merely because an LLM is present**. The important information for a decision is the current structured market snapshot and fixed strategy/risk instructions, both of which you already control.

## Open Questions and Source List

**Open Questions**

The core architecture is sufficiently validated to begin development, but several items should be intentionally resolved before freezing the forward-test protocol.

**Definition of market regime.** "Regime" must become deterministic, testable inputs rather than discretionary labels. Decide whether the regime classifier uses volatility, trend/range state, or another finite feature set, then version it.

**Definition of market structure.** Swing-high/low rules, break-of-structure logic and support/resistance construction need algorithmic definitions. Otherwise the LLM will inherit ambiguity from upstream data.

**Confirmation versus gate.** Decide whether OI, funding, holder long/short ratio, liquidations and order flow are mandatory gates or contextual evidence. Making all of them hard gates risks creating a highly filtered, data-mined strategy.

**Decision timing.** Specify whether evaluation happens only on a confirmed 15m close, on additional structure events, or both. Do not let this cadence drift during testing.

**Slow-data freshness.** Collect real observations for OI and account-ratio API delays and choose freshness thresholds based on actual cadence rather than arbitrary seconds.

**Order-book depth.** L50 is the recommended starting point, but compare L50/L200 feature stability during data collection before fixing the production feature definition.

**Protective-order pattern.** Demo integration tests should determine whether attached entry TP/SL or immediate post-fill `trading-stop` provides the cleanest state semantics for your chosen order types.

**Position/margin configuration.** Freeze one-way/hedge mode, margin mode and leverage configuration before execution testing. Avoid varying leverage as a strategy output.

**LLM provider/model.** Model choice should not change the authority boundary. Whichever model is used, record exact model ID, prompt version, response and validation results.

**LLM setup-quality scale.** Decide whether it has operational meaning. If "72/100" does not deterministically alter anything, it is merely an analysis field and should not be falsely interpreted as a calibrated probability.

**Demo fill interpretation.** Bybit documents Demo capabilities but the reviewed material does not establish perfect production fill/queue/market-impact equivalence. This remains a deliberate uncertainty rather than something the system should assume away. [S20]

**Performance study design.** Predefine which metrics and subgroup analyses will be examined before accumulating enough trades. Looking at dozens of setup/regime subgroups after the fact increases multiple-testing and overfitting risk. [S44][S45]

### Overall verdict

**Verified fact:** The Bybit V5 API presently supplies the public live data and Demo execution primitives required by the proposed V1. [S3][S5][S9][S12][S15][S13][S14][S20]

**Engineering recommendation:** Proceed without an external market-data provider, database, cloud platform or trading framework.

**Engineering recommendation:** Use mainnet for live public data and Bybit Demo for authenticated execution.

**Engineering recommendation:** Make the LLM an analyst that produces a constrained proposal from structured, deterministic market context.

**Engineering recommendation:** Make risk, sizing, account validation, duplicate prevention and execution permission fully deterministic.

**Engineering recommendation:** Keep manual approval as a final human authorization step, but re-run machine preflight checks after approval so a human cannot accidentally authorize a stale proposal.

**Engineering recommendation:** Record live microstructure from the first day because order-book/liquidation history is the largest gap between what you can see live and what is conveniently reproducible later.

**Engineering recommendation:** Treat any critical uncertainty as `NO_TRADE`.

The resulting V1 is intentionally conservative:

```text
LLM proposes.
Risk engine decides eligibility.
Human authorizes.
Deterministic code executes.
Bybit confirms.
The journal preserves the evidence.
```

That architecture is substantially more testable and safer than either an autonomous LLM agent or a heavily distributed quantitative platform, while retaining enough richness to research whether structured multi-timeframe, derivatives and order-flow context adds analytical value.

**Source List**

Primary Bybit documentation formed the basis of all exchange feasibility conclusions:

- [S3] Bybit V5 Get Kline — supported contract categories, intervals and request limits.
- [S4] Bybit V5 WebSocket Kline — update cadence and closed-candle `confirm` semantics.
- [S5] Bybit V5 REST Orderbook — snapshot depth, timestamp/sequence fields and RPI exclusion.
- [S6] [S7] [S8] Bybit V5 WebSocket Orderbook — depths, update frequencies, snapshot/delta reconstruction and reset behavior.
- [S9] Bybit V5 Recent Public Trades — taker side, IDs, timestamps, limits and archive reference.
- [S10] [S11] Bybit V5 Public Trade WebSocket — real-time stream semantics and message sequencing.
- [S12] Bybit V5 Open Interest — intervals, pagination, historical extent and volatility-delay warning.
- [S13] Bybit V5 Funding Rate History — pagination and instrument-specific funding interval.
- [S14] Bybit V5 Long Short Ratio — holder-ratio definition, intervals and historical lower bound.
- [S15] Bybit V5 All Liquidation WebSocket — 500 ms all-liquidation stream.
- [S16] [S17] Bybit V5 Instruments Info — current instrument specification interface and latency warning.
- [S18] Bybit V5 Integration Guidance — endpoint environments, timestamp window and NTP recommendation.
- Bybit V5 WebSocket Connect guidance — mainnet/testnet endpoints, heartbeat and reconnect behavior. [S1][S2]
- [S19] Bybit V5 Rate Limit Rules — REST/WS connection and endpoint limits.
- [S20] Bybit Demo Trading Service — Demo REST/private-WS environments, mainnet public stream use, supported endpoints, seven-day retention and unsupported WS order entry.
- [S21] Bybit V5 Place Order — market/limit behavior, IOC conversion, `orderLinkId`, TP/SL and reduce-only rules.
- [S22] Bybit V5 Set Trading Stop — position TP/SL semantics and automatic size adjustment.
- [S23] [S24] Bybit V5 Amend/Cancel Order — asynchronous acknowledgement and WS confirmation model.
- [S25] Bybit V5 Get Trade History — execution identifiers, multiple executions per order and ordering caveats.
- [S26] Bybit V5 Error Codes — permission, environment, duplicate-request, IP and trading errors.

Relevant trading-system engineering sources:

- [S27] Freqtrade official repository — dry-run, backtesting, futures support and platform scope.
- [S28] Freqtrade Backtesting documentation.
- [S29] Freqtrade Stoploss documentation — exchange-side stops including Bybit futures.
- [S30] Freqtrade Protections — StoplossGuard, MaxDrawdown and cooldown concepts.
- [S31] Freqtrade developer documentation — unit/integration testing, exchange tests and incomplete-candle handling.
- [S32] Freqtrade Lookahead Analysis — explicit lookahead-bias detection tooling.
- [S33] Hummingbot Connector Architecture — order-book/user-stream separation.
- [S34] Hummingbot Order Lifecycle — start tracking before exchange submission and maintain lifecycle state.
- [S35] Hummingbot Strategy V2 architecture — market-data/controller/executor modularity.
- [S36] Hummingbot Paper Trade documentation.
- [S37] [S38] 3Commas Simple Trading and SmartTrade developer documentation.
- [S39] NautilusTrader official platform material — reusable typed strategy/configuration approach.

LLM, validation, testing and security sources:

- [S40] Kang & Liu, *Deficiency of Large Language Models in Finance: An Empirical Examination of Hallucination* — empirical financial-domain hallucination study.
- [S41] Xia et al., *Agentic Trading: When LLM Agents Meet Financial Markets* — 2026 audit/review highlighting reproducibility and evaluation limitations in LLM trading research.
- [S42] [S43] Pydantic JSON validation documentation — strict structured JSON parsing/validation.
- [S44] Bailey, Borwein, López de Prado & Zhu, *The Probability of Backtest Overfitting* — formal treatment of selection/backtest overfitting.
- [S45] Bailey & López de Prado, *The Deflated Sharpe Ratio* — selection-bias/backtest-overfitting adjustment research.
- [S46] GitHub Secret Scanning documentation — repository-history credential detection and rotation guidance.
- [S47] GitHub Push Protection documentation — preventing recognized secrets from entering repositories.
- [S48] GitHub secret-storage guidance — no hard-coding, environment/secret storage and regular rotation.
