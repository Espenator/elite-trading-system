# Launch Schedule — Staged Rollout with Measurable Gates

**Version**: 1.0  
**Last updated**: March 12, 2026  
**Purpose**: Define week-by-week stages and go/no-go criteria for moving from paper to live trading.

---

## Overview

| Week | Mode | Position size cap | Primary goal |
|------|------|-------------------|--------------|
| 1 | Paper | N/A | Full monitoring; fix any issues |
| 2 | Paper | N/A | Reduced intervention; validate stability |
| 3 | Live | $100 max per trade | Live with MIN size |
| 4 | Live | $500 max per trade | SMALL size |
| 5+ | Live | Gradual | Increase based on performance metrics |

---

## Week 1: Paper trading with full monitoring

**Objective**: Run full pipeline in paper mode; confirm monitoring and alerts; fix issues.

**Config**:
- `TRADING_MODE=paper`
- Alpaca paper account
- All Slack bridges and alerts enabled (`SLACK_BOT_TOKEN` set)

**Gates (must pass before Week 2)**:
- [ ] Backend starts without error; no missing env vars for paper mode.
- [ ] At least one signal → council → verdict flow observed (log or Slack #trade-alerts).
- [ ] At least one order.submitted / order.filled (or equivalent) visible in Slack #oc-trade-desk.
- [ ] Alert bridge: trigger one of alert.health / agent_failure / data_starvation / council_degraded / websocket_circuit_open and confirm message in #embodier-trader.
- [ ] Emergency flatten tested in paper: call `POST /api/v1/orders/flatten-all` or risk-shield kill_switch; confirm positions close and Slack shows flatten message.
- [ ] No unhandled exceptions in backend logs for 24h continuous run (or document known non-blocking issues).

**Metrics to capture**:
- Number of signals per day
- Council verdict distribution (BUY/SELL/HOLD)
- Orders submitted vs filled
- Slack message count per channel (sanity check)

**Exit**: All Week 1 gates checked; decision to proceed to Week 2.

---

## Week 2: Paper trading with reduced intervention

**Objective**: Validate stability; minimal manual overrides; confirm automation holds.

**Config**: Same as Week 1 (`TRADING_MODE=paper`).

**Gates (must pass before Week 3)**:
- [ ] 5 consecutive trading days without backend crash or restart (or planned restarts documented).
- [ ] No emergency flatten required due to system bug (only if intentionally tested).
- [ ] Weight learner / outcome resolution: at least one outcome.resolved or daily_outcome_update run successfully (check scheduler or logs).
- [ ] Data backfill: daily_backfill and overnight_refresh run at least once without fatal error (scheduler logs).
- [ ] DuckDB and SQLite: no corruption; backup run at least once and restore tested (even if to a copy).

**Metrics to capture**:
- Uptime (hours per day)
- Number of council runs per day
- Paper P&L (for reference only)

**Exit**: All Week 2 gates checked; decision to enable live with MIN size.

---

## Week 3: Live trading — MIN position sizes ($100 max per trade)

**Objective**: Live capital at minimal risk; validate execution and risk controls.

**Config**:
- `TRADING_MODE=live`
- `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` for **live** account
- `API_AUTH_TOKEN` set and Bearer enforced
- Position size cap: **$100 max per trade** (enforced via config or order sizing logic; confirm in risk/execution code)
- `KELLY_MAX_ALLOCATION`: recommend 0.15
- `MAX_DAILY_TRADES`: 10
- `MAX_PORTFOLIO_HEAT`: 0.30 (or per production_env_checklist)

**Gates (must pass before Week 4)**:
- [ ] No unintended orders (only orders that match council verdict and risk gates).
- [ ] All live orders appear in Alpaca dashboard and in Slack #oc-trade-desk.
- [ ] At least one full cycle: signal → council → order → fill → outcome (if applicable).
- [ ] No 403/401 on emergency endpoints when using `API_AUTH_TOKEN` (including emergency-flatten after fix).
- [ ] Manual close tested once on live: close one position from Alpaca dashboard to confirm fallback.

**Metrics to capture**:
- Live P&L (realized and unrealized)
- Slippage vs expected (if available)
- Number of trades per day (vs MAX_DAILY_TRADES)

**Exit**: All Week 3 gates checked; decision to increase to $500 max per trade.

---

## Week 4: Live trading — SMALL position sizes ($500 max per trade)

**Objective**: Increase size gradually; confirm risk limits hold.

**Config**:
- Same as Week 3 except position size cap: **$500 max per trade**.

**Gates (must pass before Week 5+)**:
- [ ] No breach of MAX_DAILY_TRADES or MAX_PORTFOLIO_HEAT (or breaches logged and explained).
- [ ] Circuit breaker / kill switch tested once in live (e.g. freeze entries or flatten) and behavior as expected.
- [ ] Daily backup running and at least one restore verified.

**Metrics to capture**:
- P&L, drawdown, win rate
- Max portfolio heat observed vs limit
- Daily trade count vs limit

**Exit**: All Week 4 gates checked; decision to gradually increase size (Week 5+).

---

## Week 5+: Gradual size increase

**Objective**: Scale position sizes based on performance and risk metrics.

**Process**:
- Review weekly: P&L, drawdown, win rate, slippage, number of trades.
- Increase per-trade cap in steps (e.g. $500 → $1,000 → $2,500) only if:
  - No serious incidents (e.g. runaway orders, repeated circuit breaker).
  - Win rate and risk metrics within acceptable bounds.
  - Backup and recovery procedures in place and tested.

**Staged launch criteria (summary)**:
- Week 1–2: Paper only; monitoring and stability.
- Week 3: Live MIN ($100/trade); auth and execution verified.
- Week 4: Live SMALL ($500/trade); limits and backup verified.
- Week 5+: Gradual increase with weekly review.

---

## Document control

- **Owner**: Operator / product.  
- **Review**: After each week and before moving to next stage.  
- **Location**: `reports/launch_schedule.md`.
