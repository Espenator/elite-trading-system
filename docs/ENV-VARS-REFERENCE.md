# Environment Variables Reference

**Elite Trading System v3.5.0**
**Last Updated:** March 9, 2026

This document provides a comprehensive reference for all environment variables used across the Elite Trading System. Variables are organized by category and include type, default values, and usage notes.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Trading & Execution](#trading--execution)
- [External Data APIs](#external-data-apis)
- [LLM & Intelligence](#llm--intelligence)
- [Multi-PC Cluster](#multi-pc-cluster)
- [Risk Management](#risk-management)
- [Application Config](#application-config)
- [Security & Authentication](#security--authentication)
- [Database & Storage](#database--storage)
- [Feature Flags](#feature-flags)

---

## Quick Start

**Minimum required variables to run the system:**

```bash
# Backend (backend/.env)
ALPACA_API_KEY=your-alpaca-api-key
ALPACA_SECRET_KEY=your-alpaca-secret-key
TRADING_MODE=paper
```

All other variables have sensible defaults or graceful degradation.

---

## Trading & Execution

### Alpaca Markets (Live Trading)

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `ALPACA_API_KEY` | string | **Yes** | - | Alpaca API key (get from alpaca.markets) |
| `ALPACA_SECRET_KEY` | string | **Yes** | - | Alpaca secret key (keep secure) |
| `ALPACA_BASE_URL` | string | No | `https://api.alpaca.markets` | API endpoint (paper: `https://paper-api.alpaca.markets`) |
| `ALPACA_DATA_URL` | string | No | `https://data.alpaca.markets` | Market data endpoint |
| `ALPACA_FEED` | string | No | `sip` | Data feed: `sip` (consolidated) or `iex` (free) |
| `APCA_API_KEY_ID` | string | No | - | Duplicate of ALPACA_API_KEY (for alpaca-py SDK) |
| `APCA_API_SECRET_KEY` | string | No | - | Duplicate of ALPACA_SECRET_KEY (for alpaca-py SDK) |
| `APCA_API_BASE_URL` | string | No | - | Duplicate of ALPACA_BASE_URL (for alpaca-py SDK) |

**Multi-Key Setup (Optional):**

For advanced users running multiple Alpaca accounts (one WebSocket connection per account):

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `ALPACA_KEY_1` | string | No | - | Trading account key |
| `ALPACA_SECRET_1` | string | No | - | Trading account secret |
| `ALPACA_KEY_2` | string | No | - | Discovery A account key |
| `ALPACA_SECRET_2` | string | No | - | Discovery A account secret |
| `ALPACA_KEY_3` | string | No | - | Discovery B account key |
| `ALPACA_SECRET_3` | string | No | - | Discovery B account secret |

### Trading Control

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `TRADING_MODE` | string | **Yes** | `paper` | `paper` or `live` |
| `AUTO_EXECUTE_TRADES` | bool | No | `false` | Auto-execute council decisions (dangerous in live) |
| `AUTO_EXECUTE_ENABLED` | bool | No | `true` | Enable auto-execution feature |
| `MAX_DAILY_TRADES` | int | No | `10` | Maximum trades per day |
| `SLIPPAGE_BPS` | float | No | `5.0` | Expected slippage in basis points |
| `PARTIAL_FILL_ENABLED` | bool | No | `true` | Allow partial order fills |

---

## External Data APIs

### Finviz Elite

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `FINVIZ_API_KEY` | string | No | - | Finviz Elite API key (elite.finviz.com) |
| `FINVIZ_BASE_URL` | string | No | `https://elite.finviz.com` | API endpoint |
| `FINVIZ_SCREENER_FILTERS` | string | No | `sh_avgvol_o500,sh_price_u500` | Default screener filters |
| `FINVIZ_SCREENER_FILTER_TYPE` | int | No | `4` | Filter type code |
| `FINVIZ_SCREENER_VERSION` | int | No | `111` | Screener version |
| `FINVIZ_QUOTE_TIMEFRAME` | string | No | `d` | Quote timeframe (d/w/m) |

### FRED (Federal Reserve Economic Data)

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `FRED_API_KEY` | string | No | - | FRED API key (fred.stlouisfed.org) |

### Unusual Whales (Options Flow)

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `UNUSUAL_WHALES_API_KEY` | string | No | - | Unusual Whales API key |
| `UNUSUALWHALES_API_KEY` | string | No | - | Duplicate for OpenClaw compatibility |
| `UNUSUAL_WHALES_BASE_URL` | string | No | `https://api.unusualwhales.com/api` | API endpoint |

### SEC EDGAR

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `SEC_EDGAR_USER_AGENT` | string | No | - | User agent for SEC API (format: "YourName your@email.com") |

### News API

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `NEWS_API_KEY` | string | No | - | NewsAPI.org API key |

### StockGeist (Social Sentiment)

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `STOCKGEIST_API_KEY` | string | No | - | StockGeist API key |
| `STOCKGEIST_BASE_URL` | string | No | `https://api.stockgeist.ai` | API endpoint |

### YouTube

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `YOUTUBE_API_KEY` | string | No | - | YouTube Data API key (Google Cloud Console) |
| `YOUTUBE_SEARCH_QUERY` | string | No | `stock trading signals analysis` | Default search query |

### X / Twitter

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `X_API_KEY` | string | No | - | X API key |
| `X_API_KEY_SECRET` | string | No | - | X API key secret |
| `X_OAUTH2_CLIENT_ID` | string | No | - | X OAuth2 client ID |
| `X_OAUTH2_CLIENT_SECRET` | string | No | - | X OAuth2 client secret |
| `X_BEARER_TOKEN` | string | No | - | X API v2 bearer token (read-only) |

### Discord

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `DISCORD_BOT_TOKEN` | string | No | - | Discord bot token |
| `DISCORD_CHANNEL_IDS` | string | No | - | Comma-separated channel IDs |
| `DISCORD_UW_CHANNEL_ID` | string | No | - | Unusual Whales channel ID |
| `DISCORD_FOM_CHANNEL_ID` | string | No | - | Flow of Money channel ID |
| `DISCORD_EXPECTED_MOVES_CHANNEL_ID` | string | No | - | Expected Moves channel ID |
| `DISCORD_MAVERICK_CHANNEL_ID` | string | No | - | Maverick channel ID |

### Alert Services

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `RESEND_API_KEY` | string | No | - | Resend email API key (resend.com) |
| `RESEND_FROM_EMAIL` | string | No | - | Email sender address |
| `RESEND_ALERT_TO_EMAIL` | string | No | - | Alert recipient email |
| `TELEGRAM_BOT_TOKEN` | string | No | - | Telegram bot token |
| `TELEGRAM_CHAT_ID` | string | No | - | Telegram chat ID |

---

## LLM & Intelligence

### Cloud LLM Services

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `PERPLEXITY_API_KEY` | string | No | - | Perplexity AI API key |
| `PERPLEXITY_MODEL` | string | No | `sonar-pro` | Model to use |
| `PERPLEXITY_ENABLED` | bool | No | `true` | Enable Perplexity integration |
| `ANTHROPIC_API_KEY` | string | No | - | Anthropic Claude API key |
| `ANTHROPIC_MODEL` | string | No | `claude-sonnet-4-20250514` | Claude model to use |

### Local LLM (Ollama)

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `OLLAMA_BASE_URL` | string | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | string | No | `llama3.2` | Default Ollama model |
| `LOCAL_LLM_MODEL` | string | No | `qwen3:14b` | Local LLM model name |
| `LLM_ENABLED` | bool | No | `true` | Enable LLM features |
| `LLM_PREFER_LOCAL` | bool | No | `true` | Prefer local over cloud LLMs |
| `LLM_ROUTER_ENABLED` | bool | No | `true` | Enable intelligent LLM routing |
| `SCANNER_OLLAMA_URLS` | string | No | - | Comma-separated Ollama node URLs |

### Brain Service (gRPC + Ollama)

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `BRAIN_ENABLED` | bool | No | `true` | Enable brain service integration |
| `BRAIN_HOST` | string | No | `localhost` | Brain service host (PC2 IP for dual-PC) |
| `BRAIN_PORT` | int | No | `50051` | Brain service gRPC port |

### LLM Dispatcher

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `LLM_DISPATCHER_ENABLED` | bool | No | `true` | Enable LLM dispatcher |
| `LLM_DISPATCHER_HEARTBEAT_TIMEOUT` | int | No | `3` | Heartbeat timeout (seconds) |
| `LLM_DISPATCHER_FALLBACK_MODEL` | string | No | `llama3.2` | Fallback model if primary fails |
| `LLM_DISPATCHER_GPU_UTIL_THRESHOLD` | float | No | `85.0` | GPU utilization threshold (%) |

---

## Multi-PC Cluster

### Network Configuration

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `PC1_HOSTNAME` | string | No | `ESPENMAIN` | Primary PC hostname |
| `PC1_IP` | string | No | `192.168.1.105` | Primary PC IP address |
| `PC1_MAC` | string | No | - | Primary PC MAC address |
| `PC1_ROLE` | string | No | `primary` | Primary PC role |
| `PC2_HOSTNAME` | string | No | `ProfitTrader` | Secondary PC hostname |
| `PC2_IP` | string | No | `192.168.1.116` | Secondary PC IP address |
| `PC2_MAC` | string | No | - | Secondary PC MAC address |
| `PC2_ROLE` | string | No | `secondary` | Secondary PC role |

### Cross-PC API Access

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `PC1_API_URL` | string | No | `http://192.168.1.105:8000` | PC1 backend URL (from PC2) |
| `PC1_WS_URL` | string | No | `ws://192.168.1.105:8000/ws` | PC1 WebSocket URL (from PC2) |
| `PC2_API_URL` | string | No | `http://192.168.1.116:8000` | PC2 backend URL (from PC1) |
| `PC2_WS_URL` | string | No | `ws://192.168.1.116:8000/ws` | PC2 WebSocket URL (from PC1) |

### Cluster Services

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `CLUSTER_PC2_HOST` | string | No | - | PC2 IP for dual-PC mode (leave empty for single-PC) |
| `CLUSTER_HEALTH_INTERVAL` | int | No | `60` | Health check interval (seconds) |
| `REDIS_URL` | string | No | - | Redis URL for cross-PC MessageBus bridge |

### GPU & Model Routing

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `GPU_TELEMETRY_ENABLED` | bool | No | `true` | Enable GPU monitoring |
| `GPU_TELEMETRY_INTERVAL` | float | No | `3.0` | GPU telemetry interval (seconds) |
| `GPU_VRAM_HEADROOM_MB` | int | No | `512` | VRAM headroom (MB) |
| `MODEL_PIN_PC1` | string | No | `llama3.2,mistral:7b` | Models pinned to PC1 |
| `MODEL_PIN_PC2` | string | No | `deepseek-r1:14b,mixtral:8x7b` | Models pinned to PC2 |
| `MODEL_PIN_TASK_AFFINITY` | string | No | - | Task-to-node affinity mapping |

---

## Risk Management

### Kelly Criterion & Position Sizing

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `KELLY_MAX_ALLOCATION` | float | No | `0.10` | Maximum Kelly allocation (10%) |
| `KELLY_DEFAULT_WIN_RATE` | float | No | `0.55` | Default win rate for Kelly |
| `KELLY_DEFAULT_AVG_WIN` | float | No | `0.035` | Default average win (3.5%) |
| `KELLY_DEFAULT_AVG_LOSS` | float | No | `0.015` | Default average loss (1.5%) |
| `KELLY_USE_HALF` | bool | No | `true` | Use half-Kelly (safer) |

### Risk Limits

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `MAX_PORTFOLIO_HEAT` | float | No | `0.06` | Maximum portfolio risk (6%) |
| `MAX_SINGLE_POSITION` | float | No | `0.02` | Maximum single position size (2%) |
| `MAX_SECTOR_CONCENTRATION` | float | No | `0.30` | Maximum sector exposure (30%) |
| `MAX_DAILY_LOSS_PCT` | float | No | `2.0` | Maximum daily loss (2%) |
| `DEFAULT_RISK_PCT` | float | No | `1.5` | Default risk per trade (1.5%) |
| `MIN_RISK_SCORE` | float | No | `3.0` | Minimum risk score to trade |
| `VOLATILITY_BASELINE` | float | No | `0.15` | Baseline volatility (15%) |
| `CIRCUIT_BREAKER_THRESHOLD` | float | No | `-0.03` | Circuit breaker trigger (-3%) |
| `MAX_DAILY_DRAWDOWN_PCT` | float | No | `5.0` | Maximum daily drawdown (5%) |
| `AUTO_PAUSE_TRADING` | bool | No | `true` | Auto-pause on circuit breaker |

### Stop Loss & Position Management

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `ATR_STOP_MULTIPLIER` | float | No | `2.0` | ATR multiplier for stops |
| `TRAILING_STOP_PCT` | float | No | `0.03` | Trailing stop percentage (3%) |
| `MAX_POSITION_PCT` | float | No | `0.10` | Maximum position size (10%) |

---

## Application Config

### Server Settings

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `APP_NAME` | string | No | `Embodier Trader API` | Application name |
| `APP_VERSION` | string | No | `4.0.0` | Application version |
| `HOST` | string | No | `0.0.0.0` | Server bind address |
| `PORT` | int | No | `8000` | Server port |
| `ENVIRONMENT` | string | No | `production` | Environment (production/development) |
| `DEBUG` | bool | No | `false` | Enable debug mode |
| `LOG_LEVEL` | string | No | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

### CORS

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `CORS_ORIGINS` | string | No | `http://localhost:5173,http://localhost:3000,...` | Allowed CORS origins |

### WebSocket

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `WS_HEARTBEAT_INTERVAL` | int | No | `30` | WebSocket heartbeat interval (seconds) |
| `WS_MAX_CONNECTIONS` | int | No | `100` | Maximum WebSocket connections |

### Scheduler

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `SCHEDULER_ENABLED` | bool | No | `true` | Enable APScheduler |
| `SCAN_INTERVAL_MINUTES` | int | No | `5` | Default scan interval |

### Streaming

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `STREAMING_ENABLED` | bool | No | `true` | Enable market data streaming |
| `STREAMING_BAR_TIMEFRAME` | string | No | `1Min` | Bar timeframe (1Min/5Min/15Min/1H/1D) |
| `SCORE_TRIGGER_THRESHOLD` | int | No | `75` | Score threshold to trigger signals |

---

## Security & Authentication

### API Authentication

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `API_AUTH_TOKEN` | string | **Live** | - | API authentication token (generate with `secrets.token_urlsafe(32)`) |
| `VITE_API_AUTH_TOKEN` | string | **Live** | - | Frontend API token (must match backend) |

**Generate token:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Encryption

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `FERNET_KEY` | string | No | - | Encryption key for credentials (generate with Fernet.generate_key()) |

**Generate encryption key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### OpenClaw Bridge

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `OPENCLAW_ENABLED` | bool | No | `true` | Enable OpenClaw integration |
| `OPENCLAW_BRIDGE_TOKEN` | string | No | - | Shared secret for OpenClaw bridge |
| `GIST_TOKEN` | string | No | - | GitHub PAT with gist scope |
| `BRIDGE_GIST_ID` | string | No | - | GitHub gist ID for bridge |

---

## Database & Storage

### DuckDB

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `DATABASE_URL` | string | No | `duckdb:///data/elite_trading.duckdb` | DuckDB database path |

### ML Model Storage

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `ML_MODEL_DIR` | string | No | `data/models` | ML model directory |
| `MODEL_ARTIFACTS_PATH` | string | No | `models/artifacts` | Model artifacts directory |

---

## Feature Flags

### Core Features

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `COUNCIL_ENABLED` | bool | No | `true` | Enable 31-agent council |
| `ML_ENSEMBLE_ENABLED` | bool | No | `true` | Enable ML ensemble |

### Signal Thresholds

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `SIGNAL_BUY_THRESHOLD` | float | No | `0.60` | Buy signal threshold (60%) |
| `SIGNAL_STRONG_BUY_THRESHOLD` | float | No | `0.75` | Strong buy threshold (75%) |
| `SIGNAL_MIN_EDGE` | float | No | `0.05` | Minimum edge required (5%) |
| `SIGNAL_MIN_VOLUME_SCORE` | float | No | `0.5` | Minimum volume score (0-1) |

### ML Engine

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `ML_RETRAIN_INTERVAL_HOURS` | int | No | `168` | Model retraining interval (1 week) |

### GPU / PyTorch

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `GPU_DEVICE` | string | No | `auto` | GPU device (auto/cuda/cpu) |
| `TORCH_MIXED_PRECISION` | bool | No | `true` | Enable mixed precision training |

---

## Frontend (Vite)

### API Connection

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `VITE_API_URL` | string | No | - | Backend API URL (leave empty for dev proxy) |
| `VITE_WS_URL` | string | No | - | Backend WebSocket URL (leave empty for dev) |

### External APIs

| Variable | Type | Required | Default | Notes |
|----------|------|----------|---------|-------|
| `VITE_FMP_API_KEY` | string | No | - | Financial Modeling Prep API key |

---

## Environment File Locations

1. **Root `.env`**: Docker Compose and root-level scripts
2. **`backend/.env`**: Backend application (80+ variables)
3. **`frontend-v2/.env`**: Frontend application (4 variables)

---

## Production Deployment Checklist

### Required Variables

- [ ] `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- [ ] `TRADING_MODE` set to `paper` or `live`
- [ ] `API_AUTH_TOKEN` generated and set (backend + frontend)
- [ ] `FERNET_KEY` generated for credential encryption

### Recommended Variables

- [ ] External API keys for data sources (Finviz, FRED, Unusual Whales, etc.)
- [ ] Alert services configured (Resend email, Telegram)
- [ ] Risk limits reviewed and configured
- [ ] Multi-PC cluster configured (if using dual-PC setup)

### Security Checklist

- [ ] All API keys stored in `.env` (not in code)
- [ ] `.env` files added to `.gitignore`
- [ ] `API_AUTH_TOKEN` generated with sufficient entropy
- [ ] `TRADING_MODE` explicitly set (don't rely on defaults in production)
- [ ] `AUTO_EXECUTE_TRADES` explicitly set to `false` for paper trading

---

## Troubleshooting

### Common Issues

**Issue**: "python-dotenv not found"
- **Solution**: Run `pip install -r requirements.txt`

**Issue**: "Alpaca connection failed"
- **Solution**: Verify `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` are correct
- **Solution**: Check `ALPACA_BASE_URL` matches your account type (paper vs live)

**Issue**: "Council not running"
- **Solution**: Ensure `COUNCIL_ENABLED=true`
- **Solution**: Check `LLM_ENABLED=true` if using LLM agents

**Issue**: "Brain service not connecting"
- **Solution**: Verify `BRAIN_HOST` points to correct PC2 IP
- **Solution**: Ensure brain service is running on PC2 at port 50051

---

## Related Documentation

- [README.md](../README.md) - Main project documentation
- [SETUP.md](../SETUP.md) - Setup and installation guide
- [REPOSITORY_AUDIT_REPORT.md](../REPOSITORY_AUDIT_REPORT.md) - Latest audit report
- [AGENT-SWARM-ARCHITECTURE-v2.md](AGENT-SWARM-ARCHITECTURE-v2.md) - Council architecture

---

**Last Updated:** March 9, 2026
**Total Variables Documented:** 116+
