# API Complete List — Elite Trading System (March 2026)

**Version**: v3.5.0
**Last Updated**: March 8, 2026

---

## Section A: Backend API Route Files (`backend/app/api/v1/`)

As of v3.5.0, there are **34 route files** in `backend/app/api/v1/` (excluding `__init__.py`):

| # | File | Prefix / Purpose |
|---|------|-----------------|
| 1 | `agents.py` | `/agents` — council agent status, control |
| 2 | `alerts.py` | `/alerts` — price/signal alerts |
| 3 | `alignment.py` | `/alignment` — AI alignment checks |
| 4 | `alpaca.py` | `/alpaca` — Alpaca broker integration |
| 5 | `backtest_routes.py` | `/backtest` — backtesting runs |
| 6 | `cluster.py` | `/cluster` — multi-PC cluster status |
| 7 | `cns.py` | `/cns` — central nervous system / system health |
| 8 | `cognitive.py` | `/cognitive` — cognitive telemetry dashboard |
| 9 | `council.py` | `/council` — council run/status endpoints |
| 10 | `data_sources.py` | `/data-sources` — data source monitor |
| 11 | `features.py` | `/features` — ML feature pipeline |
| 12 | `flywheel.py` | `/flywheel` — ML flywheel / training loop |
| 13 | `llm_health.py` | `/llm-health` — LLM router health status |
| 14 | `logs.py` | `/logs` — system log streaming |
| 15 | `market.py` | `/market` — market data endpoints |
| 16 | `ml_brain.py` | `/ml-brain` — ML model management |
| 17 | `openclaw.py` | `/openclaw` — OpenClaw scanner integration |
| 18 | `orders.py` | `/orders` — order management |
| 19 | `patterns.py` | `/patterns` — pattern library |
| 20 | `performance.py` | `/performance` — P&L, performance analytics |
| 21 | `portfolio.py` | `/portfolio` — portfolio positions |
| 22 | `quotes.py` | `/quotes` — real-time quotes |
| 23 | `risk.py` | `/risk` — risk metrics + Kelly sizing |
| 24 | `risk_shield_api.py` | `/risk-shield` — risk circuit breakers |
| 25 | `sentiment.py` | `/sentiment` — NLP sentiment scores |
| 26 | `settings_routes.py` | `/settings` — system settings |
| 27 | `signals.py` | `/signals` — generated trading signals |
| 28 | `status.py` | `/status` — system status / health |
| 29 | `stocks.py` | `/stocks` — stock screener results |
| 30 | `strategy.py` | `/strategy` — strategy management |
| 31 | `swarm.py` | `/swarm` — agent swarm control |
| 32 | `system.py` | `/system` — system info / diagnostics |
| 33 | `training.py` | `/training` — ML training management |
| 34 | `youtube_knowledge.py` | `/youtube-knowledge` — YouTube intelligence |

> **Note**: The original issue references 29 route files. The actual codebase has 34 as of v3.5.0.
> The 5 additional routes added since that count are: `cluster`, `cns`, `cognitive`, `llm_health`, `swarm`.

---

## Section B: External API Keys & Services

**Perplexity API:** `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`

---

## 1. Finviz Elite
- **Env var:** `FINVIZ_API_KEY` — `4475cd42-70ea-4fa7-9630-0d9cd30d9620`
- **Base URL:** `https://elite.finviz.com/export.ashx` (openclaw) / `https://elite.finviz.com` (elite-trading-system)
- **Auth method:** `&auth=API_KEY` query param on export URL
- **Get key from:** https://elite.finviz.com/
- **Repos:** `openclaw` (config.py, finviz_scanner.py), `elite-trading-system` (backend/app/services/finviz_service.py, backend/.env.example)
- **GitHub Secret:** `FINVIZ_API_KEY` — configured
- **Python lib:** `requests` (direct HTTP)
- **Extra config (elite-trading-system):** `FINVIZ_SCREENER_FILTERS`, `FINVIZ_SCREENER_VERSION`, `FINVIZ_SCREENER_FILTER_TYPE`, `FINVIZ_QUOTE_TIMEFRAME`

### Finviz Export Steps
1. Configure Screener — Set up your filters in the main Screener interface
2. Replace URL Path — Change `screener.ashx` to `export.ashx` in your URL
3. Customize Columns (Optional) — Specify columns using `&c=column1,column2` parameters
4. Add Authentication — Append your API token to the URL

**Example Export URL:**
```
https://elite.finviz.com/export.ashx?v=111&f=fa_div_pos,sec_technology&auth=4475cd42-70ea-4fa7-9630-0d9cd30d9620
```

**Google Sheets:**
```
=IMPORTDATA("https://elite.finviz.com/export.ashx?[allYourFilters]&auth=4475cd42-70ea-4fa7-9630-0d9cd30d9620")
```

---

## 2. Unusual Whales
- **Env var:** `UNUSUALWHALES_API_KEY`
- **Base URL:** `https://api.unusualwhales.com/api`
- **Auth method:** Bearer token in `Authorization` header
- **Endpoint used:** `/option-trades/flow-alerts`
- **Repos:** `openclaw` (config.py, whale_flow.py), `elite-trading-system` (frontend Settings.jsx)
- **GitHub Secret:** `UNUSUALWHALES_API_KEY` — configured
- **Python lib:** `requests`

---

## 3. FRED (Federal Reserve Economic Data)
- **Env var:** `FRED_API_KEY`
- **Get key from:** https://fred.stlouisfed.org/docs/api/api_key.html
- **Repos:** `openclaw` (config.py, macro_context.py, regime.py)
- **Python lib:** `fredapi>=0.5.0`
- **Series used:** VIX (`VIXCLS`), HY spread (`BAMLH0A0HYM2`), Fed Funds Rate (`FEDFUNDS`), Yield curve 10Y-2Y (`T10Y2Y`), SPY breadth via FRED proxies
- **GitHub Secret:** `FRED_API_KEY` — configured

---

## 4. Discord
- **Env var:** `DISCORD_USER_TOKEN` (user token, not bot token)
- **API Base:** `https://discord.com/api/v10`
- **Auth method:** User token in `Authorization` header
- **How to get token:** Browser DevTools > Network tab > find API request > copy Authorization header value
- **Monitored channel IDs:**
  - UW Free Options Flow: `1186354600622694400`
  - UW Live Options Flow: `1187484002844680354`
  - FOM Trade Ideas: `850211054549860352`
  - FOM Daily Expected Moves: `1097299537758003201`
  - FOM Zones: `998705356882595840`
  - FOM Daily IVOL Alerts: `1430213250645102602`
  - Maverick Live Market Trading: `1051968098506379265`
- **Repos:** `openclaw` (discord_listener.py, fom_expected_moves.py)
- **GitHub Secret:** `DISCORD_USER_TOKEN` — configured
- **Python lib:** `aiohttp>=3.9.0`
- **Token:** `MTE1Mzc1ODM2OTg1NzkzMzM4Mg.Gtkvds.ZO4Wfy3SnZSWpeDmVnMWr42O0YlyUmmecevy7E`

---

## 5. News API
- **Env var:** `NEWS_API_KEY`
- **Get key from:** https://newsapi.org
- **Repos:** `openclaw` (config.py, .env.example)
- **GitHub Secret:** `NEWS_API_KEY` — configured
- **Python lib:** `newsapi-python>=0.2.7`

---

## 6. StockGeist
- **Env var:** `STOCKGEIST_API_URL`, `STOCKGEIST_AUTH`
- **Base URL:** `https://api.stockgeist.ai`
- **Auth method:** username:password format (or token)
- **Repos:** `openclaw` (config.py, .env.example)
- **GitHub Secret:** **NOT configured** (missing from Actions secrets)
- **Python lib:** `beautifulsoup4>=4.12.0` (web scraping fallback), `lxml>=4.9.0`
- **Login:** `Espen@embodier.ai` / `Eastsound1!#`

---

## 7. YouTube Data API v3
- **Env var:** `YOUTUBE_API_KEY`
- **Get key from:** https://console.cloud.google.com
- **Repos:** `openclaw` (config.py, .env.example)
- **GitHub Secret:** **NOT configured** (missing from Actions secrets)
- **Python lib:** `google-api-python-client>=2.100.0`
- **Key:** `AIzaSyCn1B6rIYvhyoXsomXl4ZcyQIV7VbTbEkk`

---

## 8. X / Twitter
- **Env var:** `X_BEARER_TOKEN`
- **Get key from:** https://developer.twitter.com/en/portal/dashboard
- **Repos:** `openclaw` (config.py, .env.example)
- **GitHub Secret:** **NOT configured** (missing from Actions secrets)
- **Python lib:** `tweepy>=4.14.0`
- **API Key:** `xqJifauJmwyqJGmC1EV2fx3fF`
- **Key Secret:** `kGuRa9RvBS98bT1AReIh0r8poq81XPLfID3Thi98ssYSFyngAT`
- **OAuth Secret:** `8W6omW9jlhwHwipTO5f1FicHec_aWH--wwYXvQZcrVaK9-eByS`
- **OAuth 2.0 Client ID:** `X3hzWHh1YkVocGZ1YUMzTVBzcnM6MTpjaQ`

---

## 9. SEC EDGAR
- **Status:** Implemented in `backend/app/services/sec_edgar_service.py`
- **Base URL:** `https://data.sec.gov`
- **Auth:** No API key required — only needs a `User-Agent` header
- **Env Var:** `SEC_EDGAR_USER_AGENT`
- **User-Agent:** `Embodier.ai espen@embodier.ai`

### Key Endpoints
- **Submissions (filings history):** `https://data.sec.gov/submissions/CIK##########.json`
- **Company Concept (XBRL):** `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/us-gaap/{concept}.json`
- **Company Facts (all XBRL data):** `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`
- **Frames (cross-company comparisons):** `https://data.sec.gov/api/xbrl/frames/us-gaap/{concept}/USD/CY2019Q1I.json`

> The CIK is a company's 10-digit central index key (with leading zeros). No env var or secret needed.

---

## 10. Slack
- **Webhook URL:** `https://hooks.slack.com/services/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`

---

## API Status Summary

| API | Env Var | GH Secret Set? | Implementation |
|---|---|---|---|
| Finviz | `FINVIZ_API_KEY` | ✅ Yes | Full (both repos) |
| Unusual Whales | `UNUSUALWHALES_API_KEY` | ✅ Yes | Full |
| FRED | `FRED_API_KEY` | ✅ Yes | Full |
| Discord | `DISCORD_USER_TOKEN` | ✅ Yes | Full |
| News API | `NEWS_API_KEY` | ✅ Yes | Config only |
| StockGeist | `STOCKGEIST_AUTH` | ❌ No | Config only |
| YouTube | `YOUTUBE_API_KEY` | ❌ No | Config only |
| X / Twitter | `X_BEARER_TOKEN` | ❌ No | Config only |
| SEC EDGAR | `SEC_EDGAR_USER_AGENT` | ❌ No (no secret needed) | ✅ Implemented (sec_edgar_service.py) |
| Slack | `SLACK_WEBHOOK_URL` | ❌ No | Webhook only |
| Perplexity | `PERPLEXITY_API_KEY` | ❌ No | ✅ Implemented (perplexity_intelligence.py) |
| Anthropic/Claude | `ANTHROPIC_API_KEY` | ❌ No | ✅ Implemented (claude_reasoning.py) |
| Ollama (local) | `OLLAMA_BASE_URL` | N/A (local) | ✅ Implemented (brain_service gRPC 50051) |
