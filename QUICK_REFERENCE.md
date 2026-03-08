# Elite Trading System — Quick Reference

**Last Updated:** March 8, 2026

---

## 🏁 First-Time Setup

```bash
# 1. Clone repository
git clone https://github.com/Espenator/elite-trading-system.git
cd elite-trading-system

# 2. Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env (see LIVE_TRADING_SETUP.md)

# 3. Verify setup
python scripts/verify_live_trading_setup.py

# 4. Start backend
python start_server.py

# 5. Frontend setup (new terminal)
cd ../frontend-v2
npm install
npm run dev

# 6. Open browser
# http://localhost:3000
```

---

## 🔑 Required API Keys (Minimum)

| Service | Required? | Cost | Get Keys |
|---------|-----------|------|----------|
| **Alpaca Markets** | ✅ YES | FREE (paper) | https://alpaca.markets/ |
| **Ollama (local LLM)** | ✅ YES | FREE | https://ollama.ai/ |
| **FRED** | ⭐ Recommended | FREE | https://fred.stlouisfed.org/docs/api/api_key.html |

**Optional but valuable:**
- Finviz Elite ($40/mo) — Screener + fundamentals
- Unusual Whales (paid) — Options flow, dark pool
- NewsAPI (free tier) — Breaking news

---

## 🚀 Common Commands

### Backend

```bash
# Start server (development)
cd backend
python start_server.py

# Run tests
python -m pytest tests/ -q

# Verify live trading setup
python scripts/verify_live_trading_setup.py

# Backfill historical data
python -m app.jobs.backfill_bars --symbol SPY --days 365

# Check database
sqlite3 data/elite_trading.db ".tables"
duckdb data/analytics.duckdb "SELECT COUNT(*) FROM daily_ohlcv;"

# Generate security keys
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Frontend

```bash
# Start dev server
cd frontend-v2
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Ollama (LLM)

```bash
# Install (Linux/macOS)
curl https://ollama.ai/install.sh | sh

# Start service
ollama serve

# Download models
ollama pull llama3.2      # Fast (1.3 GB)
ollama pull qwen3:14b     # Better reasoning (8.3 GB)

# Test inference
curl http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"Test","stream":false}'

# List installed models
ollama list
```

---

## 📊 Health Checks

### Backend Health

```bash
# Health endpoint
curl http://localhost:8000/api/v1/status/health | jq

# API documentation
# http://localhost:8000/docs
```

### Service Status

Check startup logs for:
- ✅ `CouncilGate started (13-agent council controls trading)` — Council enabled
- ✅ `AlpacaStreamManager launched for 10 symbols` — Market data streaming
- ✅ `OrderExecutor started (SHADOW mode)` — Order execution ready
- ✅ `Scheduler started (6 adapters)` — Data ingestion active

### Common Issues

| Issue | Fix |
|-------|-----|
| DNS errors for Alpaca | Check network, verify API keys |
| "CouncilGate DISABLED" | Set `LLM_ENABLED=true`, start Ollama |
| "Scheduler disabled" | Set `SCHEDULER_ENABLED=true` |
| Empty DuckDB | Backfill data (see commands above) |
| High memory usage | Use smaller LLM model (llama3.2) |

---

## ⚙️ Configuration (.env)

### Test Mode (Development)

```bash
TRADING_MODE=paper
AUTO_EXECUTE_TRADES=false    # SHADOW mode (no real orders)
LLM_ENABLED=false            # Can test without LLM
SCHEDULER_ENABLED=false      # Can test without data sources
STREAMING_ENABLED=false      # Can test without Alpaca stream
```

### Paper Trading (Validation)

```bash
TRADING_MODE=paper
AUTO_EXECUTE_TRADES=true     # Auto-execute on paper account
LLM_ENABLED=true             # Full council evaluation
SCHEDULER_ENABLED=true       # Enable data ingestion
STREAMING_ENABLED=true       # Real-time market data

# Required API keys:
ALPACA_API_KEY=PKxxxx
ALPACA_SECRET_KEY=xxxx
FRED_API_KEY=xxxx            # At least 1 data source
```

### Live Trading (Production)

```bash
TRADING_MODE=live            # ⚠️ REAL MONEY
AUTO_EXECUTE_TRADES=true     # Auto-execute
LLM_ENABLED=true
SCHEDULER_ENABLED=true
STREAMING_ENABLED=true

# Use live Alpaca credentials
ALPACA_BASE_URL=https://api.alpaca.markets
ALPACA_API_KEY=<live-key>
ALPACA_SECRET_KEY=<live-secret>

# Conservative risk limits
MAX_PORTFOLIO_HEAT=0.04      # 4% max heat
MAX_SINGLE_POSITION=0.015    # 1.5% per position
MAX_DAILY_TRADES=5           # Max 5 trades/day
```

---

## 🛡️ Safety Checklist

**Before enabling live trading:**
- [ ] Paper trading profitable for 30+ days
- [ ] All risk limits tested (drawdown, position size)
- [ ] Circuit breaker verified
- [ ] Emergency stop procedure documented
- [ ] Account funded (minimum $2000)
- [ ] Conservative risk limits set (see .env.production)
- [ ] Daily monitoring schedule established

**Trading modes:**
1. **SHADOW** (`AUTO_EXECUTE_TRADES=false`) — Signals logged to DuckDB only
2. **PAPER** (`TRADING_MODE=paper`, `AUTO_EXECUTE_TRADES=true`) — Trade on paper account
3. **LIVE** (`TRADING_MODE=live`, `AUTO_EXECUTE_TRADES=true`) — Real money ⚠️

**Always:** Start with SHADOW → Paper → Live (30+ days each stage)

---

## 📚 Documentation

| Guide | Purpose |
|-------|---------|
| [`README.md`](README.md) | Project overview, architecture |
| [`LIVE_TRADING_SETUP.md`](LIVE_TRADING_SETUP.md) | **Complete setup guide for live trading** |
| [`STARTUP_DEBUG_AUDIT.md`](STARTUP_DEBUG_AUDIT.md) | Detailed startup flow audit |
| [`backend/.env.production`](backend/.env.production) | Production-ready .env template |
| `http://localhost:8000/docs` | API documentation (Swagger) |

---

## 🔍 Monitoring

### Real-Time WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => {
  // Subscribe to channels
  ws.send(JSON.stringify({ type: 'subscribe', channel: 'signals' }));
  ws.send(JSON.stringify({ type: 'subscribe', channel: 'orders' }));
  ws.send(JSON.stringify({ type: 'subscribe', channel: 'alerts' }));
};
ws.onmessage = (evt) => console.log('Event:', JSON.parse(evt.data));
```

### Key Channels
- `signals` — Trade signals generated
- `council` — Council verdicts
- `orders` — Order submissions/fills
- `alerts` — Risk alerts, circuit breaker
- `market` — Market data updates

### Dashboard Pages

1. **Dashboard** (`/`) — Overview, P&L, positions
2. **Signal Intelligence** (`/signal-intelligence-v3`) — Real-time signals
3. **Risk Intelligence** (`/risk`) — Risk metrics, circuit breaker
4. **Trades** (`/trades`) — Trade history, attribution
5. **Performance** (`/performance`) — Win rate, Sharpe, drawdown
6. **Agent Command** (`/agents`) — Council agent status

---

## 🆘 Emergency Stop

```bash
# 1. Stop backend immediately
Ctrl+C  # or pkill -f start_server.py

# 2. Disable auto-execution (without restart)
# Edit backend/.env:
AUTO_EXECUTE_TRADES=false

# 3. Cancel all open orders
# Alpaca Dashboard:
# Paper: https://app.alpaca.markets/paper/dashboard
# Live: https://app.alpaca.markets/brokerage/dashboard

# 4. Restart in SHADOW mode
python start_server.py
```

---

## 📞 Support

- **Issues:** https://github.com/Espenator/elite-trading-system/issues
- **Logs:** `backend/logs/` (if configured)
- **Database:** `backend/data/elite_trading.db` (SQLite), `backend/data/analytics.duckdb` (DuckDB)

---

**Version:** 3.5.0 | **Last Updated:** March 8, 2026
