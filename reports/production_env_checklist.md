# Production Environment Checklist — Embodier Trader

**Version**: 1.0  
**Last updated**: March 12, 2026  
**Template**: `backend/.env.example`  
**Loader**: `backend/app/core/config.py` (pydantic-settings, env_file=`backend/.env`)  
**No secrets in this document** — only variable names and recommended initial values.

---

## Required for ALL deployments (including paper)

| Variable | Required | Recommended value | Notes |
|----------|----------|-------------------|--------|
| `TRADING_MODE` | Yes | `paper` (until Week 3) | `paper` \| `live` \| `shadow` |
| `ALPACA_API_KEY` | Yes (for trading) | — | Alpaca API key (paper or live) |
| `ALPACA_SECRET_KEY` | Yes (for trading) | — | Alpaca secret |
| `API_AUTH_TOKEN` | Yes (for protected endpoints) | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` | Bearer token for API and emergency-flatten |

**Evidence**: `config.py` 436–449 — when `TRADING_MODE=live`, startup fails if any of `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `API_AUTH_TOKEN` are missing.

---

## Required for LIVE only

When `TRADING_MODE=live`, the same three variables above are required. No additional env vars are enforced at startup for live, but the following are **strongly recommended**:

| Variable | Recommended initial live value | Notes |
|----------|--------------------------------|--------|
| `KELLY_MAX_ALLOCATION` | `0.15` | config default 0.25; 0.15 for initial live |
| `MAX_DAILY_TRADES` | `10` | config default 10 |
| `MAX_PORTFOLIO_HEAT` | `0.30` | config default 0.06; 0.30 for initial live (audit recommendation) |

---

## Slack (monitoring)

| Variable | Required for alerts | Recommended | Notes |
|----------|---------------------|-------------|--------|
| `SLACK_BOT_TOKEN` | Yes (for MessageBus→Slack bridges) | — | Refresh every 12h at api.slack.com/apps |
| `SLACK_APP_TOKEN` | Optional | — | If using Socket Mode |
| `SLACK_SIGNING_SECRET` | Optional | — | For Slack events |
| `SLACK_WEBHOOK_URL` | No (for SlackAlerter) | — | Alternative to Bot token for webhook alerts |
| `SLACK_ALERT_CHANNEL` | No | — | Override for SlackAlerter |

**Channels** (hardcoded in code; must exist in workspace): `#trade-alerts`, `#oc-trade-desk`, `#embodier-trader`.  
**Evidence**: `backend/app/services/slack_notification_service.py` lines 34–36.

---

## Alpaca and server

| Variable | Required | Default / recommendation |
|----------|----------|---------------------------|
| `ALPACA_BASE_URL` | No | `https://api.alpaca.markets` (live) or paper URL |
| `ALPACA_DATA_URL` | No | `https://data.alpaca.markets` |
| `ALPACA_FEED` | No | `sip` for production real-time; `iex` free |
| `HOST` | No | `0.0.0.0` |
| `PORT` | No | `8000` |
| `ENVIRONMENT` | No | `production` |

---

## Risk and execution (recommended initial live)

| Variable | config.py default | Recommended initial live |
|----------|-------------------|---------------------------|
| `KELLY_MAX_ALLOCATION` | 0.25 | 0.15 |
| `MAX_PORTFOLIO_HEAT` | 0.06 | 0.30 |
| `MAX_DAILY_TRADES` | 10 | 10 |
| `MAX_DAILY_LOSS_PCT` | 2.0 | 2.0 |
| `MAX_DAILY_DRAWDOWN_PCT` | 5.0 | 5.0 |
| `AUTO_EXECUTE_TRADES` | False | Set True when ready for auto-execution |
| `AUTO_EXECUTE_ENABLED` | True | True |

---

## Optional (degrade gracefully if missing)

- **Data / LLM**: `FRED_API_KEY`, `NEWS_API_KEY`, `UNUSUAL_WHALES_API_KEY`, `FINVIZ_API_KEY`, `PERPLEXITY_API_KEY`, `ANTHROPIC_API_KEY`, `SEC_EDGAR_USER_AGENT`, `BENZINGA_*`, `YOUTUBE_API_KEY`, `BRAIN_SERVICE_URL`, `OLLAMA_BASE_URL`, etc.  
- **Other**: `RESEND_API_KEY`, `RESEND_ALERT_TO_EMAIL`, `TELEGRAM_*`, `REDIS_URL`, `FERNET_KEY`, `OPENCLAW_*`, Discord/X keys, etc.

Full list: see `backend/.env.example` and `backend/app/core/config.py`.

---

## Which values are missing (operator checklist)

Before first run, confirm:

- [ ] `TRADING_MODE` set (e.g. `paper`).  
- [ ] `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` set for the target account (paper or live).  
- [ ] `API_AUTH_TOKEN` set and stored securely; used in Bearer header for API and emergency-flatten.  
- [ ] For live: `KELLY_MAX_ALLOCATION`, `MAX_DAILY_TRADES`, `MAX_PORTFOLIO_HEAT` set to recommended values.  
- [ ] For Slack: `SLACK_BOT_TOKEN` set; channels `#trade-alerts`, `#oc-trade-desk`, `#embodier-trader` exist and bot is a member.  
- [ ] No secrets committed to repo; `.env` is gitignored.

---

## Creating production .env

1. Copy: `cp backend/.env.example backend/.env` (or on Windows: `Copy-Item backend\.env.example backend\.env`).  
2. Fill every variable marked required above.  
3. Set recommended initial live values for risk/execution when going live.  
4. Do not commit `backend/.env`.

---

## Evidence references

- Config loader: `backend/app/core/config.py` (lines 15–25, 32, 36, 201, 205, 356, 436–449).  
- .env template: `backend/.env.example`.  
- Slack channels: `backend/app/services/slack_notification_service.py` (34–36).
