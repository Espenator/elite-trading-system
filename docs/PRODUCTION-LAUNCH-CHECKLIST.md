# Embodier Trader v5.0.0 — Final Production Launch Checklist

**Repository**: github.com/Espenator/elite-trading-system
**Date**: March 12, 2026 | **Version**: v5.0.0 | **Status**: All Phases A-E Complete
**Prepared by**: Perplexity Deep Research + Manual Audit

## Current Verdict: NO-GO

Three hard blockers need resolution first:

1. **PR #157** has 3 CI failures (Backend Py3.11, Py3.12, Frontend) and merge conflicts. Fix: rebase onto main, add pytest-xdist, fix package-lock.json.
2. **API_AUTH_TOKEN** is empty in .env.example — must be generated before live trading.
3. **All 8 safety gates** exist in code but have NOT been hands-on tested in paper mode.

---

## PHASE 1: Pre-Launch Verification

### 1.1 CI/CD Integrity

| Item | Status | Evidence |
|------|--------|----------|
| Main branch CI | PASS | 3-job pipeline running |
| PR #157 merge status | FAIL | Mergeable state is dirty — branch diverged |
| PR #157 CI: Backend (Py3.11) | FAIL | pytest-xdist missing |
| PR #157 CI: Frontend | FAIL | package-lock.json stale (esbuild mismatch) |
| CodeQL security scan | PASS | All 3 analyzers passed |

**Remediation:**
1. Rebase verify/learning-loop-e2e onto main (commit fc835f9)
2. Add pytest-xdist>=3.0.0 to backend/requirements.txt
3. Regenerate frontend-v2/package-lock.json via npm install
4. Confirm all 3 CI jobs pass before merging

### 1.2 Safety Gate Verification

| Safety Gate | Code Present | Needs Testing |
|-------------|-------------|---------------|
| Circuit breakers (10) | Phase A4 — Gate 2c in OrderExecutor | Must trigger each in paper mode |
| Emergency flatten | Phase E — POST /orders/emergency-stop | Test end-to-end |
| Paper/live safety | Phase A6 — forces SHADOW on mismatch | Test: live mode + paper keys |
| Max daily loss kill switch | MAX_DAILY_LOSS_PCT=2.0 | Verify it HALTS trading |
| Regime RED/CRISIS block | Phase A3 — Gate 2b | Test: RED regime + BUY signal |
| VETO enforcement | VETO_AGENTS = risk, execution | Test: risk veto -> HOLD |
| Stale verdict rejection | Phase E — 30s timeout | Test: old verdict -> rejected |
| Auth fail-closed | Bearer token required | Test: no token -> 401 |

### 1.3 Data Source Health

| Source | Status |
|--------|--------|
| Alpaca Markets | CONFIGURED (core) |
| Unusual Whales | CONFIGURED |
| Finviz Elite | Needs key |
| FRED | CONFIGURED |
| SEC EDGAR | CONFIGURED |
| NewsAPI | CONFIGURED |
| Benzinga (scraper) | CONFIGURED |
| SqueezeMetrics (scraper) | CONFIGURED |
| Capitol Trades | CONFIGURED |
| StockGeist | Not configured |
| YouTube | Not configured |

### 1.4 Frontend Wiring Status

| Page | Status | Notes |
|------|--------|-------|
| Dashboard | GOOD | WS verification needed |
| Signal Intelligence | GOOD | Polish only |
| ML Brain & Flywheel | GOOD | Polish only |
| Patterns | GOOD | Polish only |
| Data Sources | DONE | Verified |
| Market Regime | DONE | Verified |
| Active Trades | DONE | Verified |
| Settings | GOOD | Polish only |
| Backtesting | GOOD | Polish only |
| ACC Swarm Overview | MAJOR GAP | 8-12h rewrite |
| Performance Analytics | PARTIAL | 3-4h fixes |
| Trade Execution | PARTIAL | 2-3h fixes |
| Risk Intelligence | PARTIAL | 2-3h fixes |
| Sentiment | PARTIAL | 2-3h fixes |

### 1.5 Secrets & Security

| Check | Status |
|-------|--------|
| .env in .gitignore | PASS |
| .env.example completeness | NEEDS ATTENTION — APP_VERSION stale |
| CORS configuration | NEEDS ATTENTION — verify for dual-PC LAN |
| API_AUTH_TOKEN | BLOCKING — empty, must generate |
| AUTO_EXECUTE_TRADES | PASS — defaults to false |
| Slack token freshness | NEEDS ATTENTION — expire every 12h |

---

## PHASE 2: Paper Trading Burn-In (1-5 Trading Days)

### Paper Mode Config
```
TRADING_MODE=paper
ALPACA_BASE_URL=https://paper-api.alpaca.markets
AUTO_EXECUTE_TRADES=false
KELLY_MAX_ALLOCATION=0.10
MAX_DAILY_TRADES=10
MAX_PORTFOLIO_HEAT=0.06
```

### Hourly Monitoring
- GET /signals/ — entries with score >= 65
- GET /council/latest — recent verdicts
- GET /alpaca/orders — paper orders appearing
- GET /system/event-bus/status — 25 channels active
- GET /logs — zero DuckDB errors
- Slack #trade-alerts — verdicts posting
- GET /council/weights — weights changing
- GET /agents — no scout errors

### Burn-In Success Criteria (ALL Must Pass)
- [ ] 3+ full trading days without crash
- [ ] 10+ paper trades end-to-end
- [ ] Emergency stop tested
- [ ] No unhandled exceptions
- [ ] Circuit breaker triggered and blocked
- [ ] Weight learner processed 5+ outcomes
- [ ] Slack received all notification types
- [ ] Council latency sub-2s

---

## PHASE 3: Live Trading Cutover

### Conservative Parameters
| Parameter | Value | Key |
|-----------|-------|-----|
| Kelly max | 0.15 | KELLY_MAX_ALLOCATION |
| Max daily trades | 10 | MAX_DAILY_TRADES |
| Max portfolio heat | 0.30 | MAX_PORTFOLIO_HEAT |
| Max single position | 2% | MAX_SINGLE_POSITION |
| Max daily drawdown | 5% | MAX_DAILY_DRAWDOWN_PCT |

### Cutover Steps
1. Stop all services
2. Update .env: TRADING_MODE=live, live Alpaca keys
3. Generate fresh API_AUTH_TOKEN
4. Refresh Slack tokens
5. Start backend — verify GET /alpaca/account returns live info
6. Start frontend — verify Dashboard shows live equity
7. Place ONE small test order ($50-100) manually
8. Verify in Alpaca dashboard
9. Enable AUTO_EXECUTE_TRADES=true
10. Monitor first 30 minutes manually

### Graduated Position Sizing
| Week | Max Per Trade | Heat | Monitoring |
|------|--------------|------|------------|
| 1-2 | Paper only | N/A | Hourly |
| 3 | $100 | 0.10 | Hourly |
| 4 | $500 | 0.20 | Every 2h |
| 5-6 | $1,000 | 0.30 | 3x daily |
| 7+ | Gradual increase | Per risk profile | Standard |

---

## PHASE 4: Blockers Summary

| # | Blocker | Status | Fix |
|---|---------|--------|-----|
| 1 | PR #157 CI failures | BLOCKING | Rebase, add pytest-xdist, fix conflicts |
| 2 | API_AUTH_TOKEN empty | BLOCKING | Generate with secrets.token_urlsafe(32) |
| 3 | Safety gates untested | BLOCKING | Test all 8 gates in paper mode |
| 4 | Slack tokens expired | HIGH | Refresh at api.slack.com/apps |
| 5 | docker-compose.yml missing | MEDIUM | Referenced but doesn't exist |
| 6 | Finviz API key missing | MEDIUM | 1 of 10 sources without key |
| 7 | APP_VERSION stale | LOW | Says 4.1.0, should be 5.0.0 |

---

## GO/NO-GO Checklist

- [ ] PR #157 merged, CI GREEN
- [ ] Paper traded 2+ weeks, no crashes
- [ ] Emergency flatten tested
- [ ] All 10 circuit breakers tested
- [ ] Kill switch tested
- [ ] Slack alerts firing
- [ ] DuckDB backup tested
- [ ] Alpaca dashboard fallback tested
- [ ] Positive/break-even paper P&L
- [ ] No ERROR-level logs
- [ ] Kelly sizing reasonable
- [ ] CORS reviewed for LAN
- [ ] API_AUTH_TOKEN generated
- [ ] API keys rotated

**Current Verdict: NO-GO until blockers 1-3 resolved and paper burn-in passes.**
