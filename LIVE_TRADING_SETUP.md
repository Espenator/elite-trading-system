# Live Trading Setup Guide
**Elite Trading System — Production Deployment Checklist**

This guide walks you through enabling all external dependencies required for live trading.

---

## Prerequisites Checklist

Before enabling live trading, ensure you have:

- [ ] Valid Alpaca Markets account (paper or live)
- [ ] Network access to external APIs (no DNS restrictions)
- [ ] Ollama installed for LLM inference (or cloud LLM API keys)
- [ ] At least one external data source API key (Finviz, FRED, or Unusual Whales)
- [ ] 8GB+ RAM for full intelligence stack
- [ ] GPU recommended for faster LLM inference (optional)

---

## Step 1: Network Connectivity Verification

### Test Alpaca API Access

```bash
# Test DNS resolution
nslookup paper-api.alpaca.markets

# Test HTTPS connectivity
curl -I https://paper-api.alpaca.markets/v2/clock

# Expected: HTTP 401 Unauthorized (authentication required, but connection works)
```

### Test Other API Endpoints

```bash
# Finviz (if you have elite access)
curl -I https://elite.finviz.com

# FRED
curl -I https://api.stlouisfed.org/fred/series

# Unusual Whales
curl -I https://api.unusualwhales.com/api
```

**Troubleshooting:**
- If DNS fails: Check `/etc/resolv.conf` or contact network admin
- If firewall blocks: Whitelist domains in your firewall/proxy
- If running in Docker: Ensure `--network host` or bridge networking configured

---

## Step 2: API Keys Configuration

### 2.1 Obtain API Keys

**Required (minimum for trading):**
1. **Alpaca Markets** (https://alpaca.markets/)
   - Sign up for paper trading account (free)
   - Or use live trading account (funded, approved)
   - Get: API Key + Secret Key

**Recommended (for intelligence features):**
2. **FRED** (https://fred.stlouisfed.org/docs/api/api_key.html) — FREE
   - Federal Reserve economic data
   - Used for macro regime detection

3. **Finviz Elite** (https://elite.finviz.com/) — PAID ($40/month)
   - Screener + fundamentals
   - Used for TurboScanner + initial universe

4. **Unusual Whales** (https://unusualwhales.com/) — PAID
   - Options flow, dark pool data
   - Used for GEX, insider trading signals

**Optional (enhances intelligence):**
5. **NewsAPI** (https://newsapi.org/) — FREE tier available
6. **YouTube API** (https://console.cloud.google.com/) — FREE quota
7. **Perplexity AI** (https://docs.perplexity.ai/) — PAID (cloud LLM fallback)
8. **Anthropic Claude** (https://docs.anthropic.com/) — PAID (cloud LLM fallback)

### 2.2 Create `.env` File

```bash
cd backend
cp .env.example .env
```

### 2.3 Edit `.env` — Critical Settings

Open `backend/.env` and configure:

```bash
# ===== CRITICAL: Trading Mode =====
TRADING_MODE=paper              # paper | live (START WITH PAPER!)
AUTO_EXECUTE_TRADES=false       # false = SHADOW mode, true = AUTO trading
DEBUG=False                     # False for production
ENVIRONMENT=production

# ===== CRITICAL: Alpaca (REQUIRED) =====
ALPACA_API_KEY=PKxxxxxxxxxxxxxx
ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxx
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # paper trading
ALPACA_DATA_URL=https://data.alpaca.markets
ALPACA_FEED=iex                 # iex (free) | sip (paid real-time)

# Duplicate names for alpaca-py SDK compatibility
APCA_API_KEY_ID=PKxxxxxxxxxxxxxx
APCA_API_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxx

# ===== CRITICAL: LLM for Council =====
LLM_ENABLED=true                # MUST be true for council
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2           # or qwen3:14b, mixtral:8x7b
LOCAL_LLM_MODEL=qwen3:14b
LLM_PREFER_LOCAL=true
COUNCIL_ENABLED=true

# ===== CRITICAL: Security =====
# Generate FERNET_KEY:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY=your-generated-key-here

# Generate API_AUTH_TOKEN (for frontend authentication):
# python -c "import secrets; print(secrets.token_urlsafe(32))"
API_AUTH_TOKEN=your-generated-token-here

# ===== Data Sources (at least 1 recommended) =====
FRED_API_KEY=your-fred-api-key              # FREE — get from fred.stlouisfed.org
FINVIZ_API_KEY=your-finviz-api-key          # PAID — elite.finviz.com
UNUSUAL_WHALES_API_KEY=your-uw-api-key      # PAID — unusualwhales.com
UNUSUALWHALES_API_KEY=your-uw-api-key       # Duplicate for OpenClaw compat
NEWS_API_KEY=your-newsapi-key               # FREE tier — newsapi.org

# ===== Enable Services =====
SCHEDULER_ENABLED=true          # Enable ingestion adapters
STREAMING_ENABLED=true          # Enable real-time Alpaca data stream
```

**⚠️ CRITICAL SAFETY:**
- **ALWAYS start with `TRADING_MODE=paper`**
- **ALWAYS start with `AUTO_EXECUTE_TRADES=false`** (SHADOW mode)
- Only enable auto-execution after extensive paper trading validation
- Live trading requires `TRADING_MODE=live` + funded Alpaca account

### 2.4 Frontend `.env` (Optional)

If deploying frontend separately:

```bash
cd frontend-v2
cp .env.example .env
```

Edit `frontend-v2/.env`:

```bash
# Only needed for production deployment (dev mode uses Vite proxy)
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_API_AUTH_TOKEN=<same-as-backend-API_AUTH_TOKEN>
```

---

## Step 3: LLM Setup (Ollama)

The 31-agent council **requires** an LLM service. Recommended: local Ollama.

### 3.1 Install Ollama

**Linux / macOS:**
```bash
curl https://ollama.ai/install.sh | sh
```

**Windows:**
Download from https://ollama.ai/download/windows

**Docker:**
```bash
docker run -d --name ollama -p 11434:11434 ollama/ollama
```

### 3.2 Start Ollama Service

```bash
# Start service (runs on localhost:11434)
ollama serve

# Verify running
curl http://localhost:11434/api/tags
```

### 3.3 Download Models

```bash
# Recommended: Fast tactical model (1.3 GB)
ollama pull llama3.2

# Alternative: Larger reasoning model (8.3 GB)
ollama pull qwen3:14b

# Optional: Advanced multi-agent reasoning (47 GB)
ollama pull mixtral:8x7b
```

**Model Selection Guide:**
- **llama3.2** (1.3 GB): Fast, good for real-time signals (6-8 GB RAM)
- **qwen3:14b** (8.3 GB): Better reasoning for strategy/postmortem (16 GB RAM)
- **mixtral:8x7b** (47 GB): Best quality, slower (32+ GB RAM, GPU recommended)

### 3.4 Verify LLM Connectivity

```bash
# Test inference
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "What is the capital of France?",
  "stream": false
}'

# Expected: JSON response with "Paris"
```

**Troubleshooting:**
- `Connection refused`: Ollama not running → run `ollama serve`
- `Model not found`: Download model → run `ollama pull llama3.2`
- Slow inference: Use smaller model or add GPU acceleration

### 3.5 Cloud LLM Fallback (Optional)

If you can't run Ollama locally, use cloud APIs:

```bash
# backend/.env
LLM_ENABLED=true
LLM_PREFER_LOCAL=false
PERPLEXITY_API_KEY=your-perplexity-key
PERPLEXITY_MODEL=sonar-pro
ANTHROPIC_API_KEY=your-anthropic-key
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

**Note:** Cloud LLMs cost per API call. Budget accordingly.

---

## Step 4: Database Initialization

### 4.1 Verify Database Creation

Databases auto-create on first startup, but verify:

```bash
cd backend

# Check SQLite
ls -lh data/elite_trading.db

# Check DuckDB
ls -lh data/analytics.duckdb
```

### 4.2 Backfill Historical Data (Recommended)

Empty DuckDB blocks backtesting and ML training. Backfill at least 1 year:

```bash
# From backend/
python -m app.jobs.backfill_bars --symbol SPY --days 365
python -m app.jobs.backfill_bars --symbol QQQ --days 365
python -m app.jobs.backfill_bars --symbol AAPL --days 365
```

**Expected:** Populates `daily_ohlcv` table with historical bars.

**Verification:**
```bash
# Using DuckDB CLI
duckdb data/analytics.duckdb

# Query row count
SELECT COUNT(*) FROM daily_ohlcv;
-- Expected: >250 rows per symbol (1 year of trading days)

# Query symbols
SELECT DISTINCT symbol FROM daily_ohlcv;
-- Expected: SPY, QQQ, AAPL, ...
```

---

## Step 5: Start Backend

### 5.1 Install Dependencies

```bash
cd backend
pip install -r requirements.txt

# Optional: PyTorch for LSTM models (large download)
# pip install torch>=2.0.0
```

### 5.2 Start Server

```bash
python start_server.py
```

### 5.3 Verify Startup Logs

**✅ SUCCESS indicators:**
```
✅ CouncilGate started (13-agent council controls trading)
✅ AlpacaStreamManager launched for 10 symbols
✅ EventDrivenSignalEngine started
✅ OrderExecutor started (SHADOW mode, council-controlled)
✅ Scheduler started (6 adapters)
```

**❌ FAILURE indicators:**
```
ERROR Alpaca connection error: [Errno -5] No address associated with hostname
→ Fix: Check network, verify API keys

⚠️ CouncilGate DISABLED -- routing signals directly to OrderExecutor
→ Fix: Set LLM_ENABLED=true, start Ollama

⚠️ Scheduler disabled (SCHEDULER_ENABLED=false in config)
→ Fix: Set SCHEDULER_ENABLED=true in .env
```

### 5.4 Check Health Endpoint

```bash
curl http://localhost:8000/api/v1/status/health | jq

# Expected output:
{
  "status": "ok",
  "timestamp": "2026-03-08T...",
  "version": "4.0.0",
  "services": {
    "message_bus": "online",
    "signal_engine": "online",
    "council_gate": "online",
    "order_executor": "shadow",
    "alpaca_stream": "connected"
  }
}
```

---

## Step 6: Start Frontend

```bash
cd frontend-v2
npm install
npm run dev

# Dev server starts on http://localhost:3000
```

**Open browser:** http://localhost:3000

**Verify:**
- Dashboard loads without errors
- WebSocket connection established (check DevTools → Network → WS)
- Market data updates (if streaming enabled)

---

## Step 7: Enable Live Trading (Advanced)

**⚠️ WARNING: Only proceed after extensive paper trading validation!**

### 7.1 Paper Trading Validation Period

Run in SHADOW mode for **minimum 30 days**:

```bash
# backend/.env
TRADING_MODE=paper
AUTO_EXECUTE_TRADES=false  # SHADOW = DuckDB only, no real orders
```

**Validation checklist:**
- [ ] Signal engine generates reasonable signals (score >= 65)
- [ ] Council evaluations align with market conditions
- [ ] No false positives during high volatility
- [ ] Risk limits respected (max heat, position size)
- [ ] Circuit breaker triggers on drawdown
- [ ] WebSocket updates arrive in <1s

### 7.2 Enable Paper Auto-Execution

After validation, enable auto-execution in **paper mode**:

```bash
# backend/.env
TRADING_MODE=paper
AUTO_EXECUTE_TRADES=true   # Auto-execute on paper account
```

**Monitor for 7+ days:**
- [ ] Orders execute without errors
- [ ] Fills reported correctly
- [ ] P&L tracking accurate
- [ ] Trailing stops work
- [ ] Position manager exits stale positions

### 7.3 Enable Live Trading (Real Money)

**Prerequisites:**
- [ ] Alpaca account approved for live trading
- [ ] Account funded (minimum $2000 recommended)
- [ ] Paper trading profitable over 30+ days
- [ ] Risk management tested (drawdown limits)
- [ ] Emergency stop procedures documented

**Configuration:**

```bash
# backend/.env
TRADING_MODE=live                              # ⚠️ REAL MONEY
AUTO_EXECUTE_TRADES=true                       # Auto-execute
ALPACA_BASE_URL=https://api.alpaca.markets     # Live API (not paper)

# Update credentials to LIVE keys
ALPACA_API_KEY=<your-live-api-key>
ALPACA_SECRET_KEY=<your-live-secret-key>

# Conservative risk limits for live trading
MAX_PORTFOLIO_HEAT=0.04           # 4% max heat (vs 6% in paper)
MAX_SINGLE_POSITION=0.015         # 1.5% per position (vs 2% in paper)
MAX_DAILY_LOSS_PCT=1.5            # 1.5% daily loss limit (vs 2% in paper)
MAX_DAILY_TRADES=5                # 5 trades/day max (vs 10 in paper)
CIRCUIT_BREAKER_THRESHOLD=-0.02   # -2% triggers pause (vs -3% in paper)
```

**Start backend:**
```bash
python start_server.py
```

**Monitor logs for:**
```
🚨 LIVE TRADING ENABLED — Real money at risk
Mode: LIVE | Auto-Execute: TRUE | Account: $XXXXX
```

---

## Step 8: Monitoring & Safety

### 8.1 Real-Time Monitoring

**WebSocket channels to monitor:**
1. `signals` — Trade signals generated
2. `council` — Council verdicts
3. `orders` — Order submissions/fills
4. `alerts` — Risk alerts, circuit breaker triggers

**Browser DevTools:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'subscribe', channel: 'orders' }));
  ws.send(JSON.stringify({ type: 'subscribe', channel: 'alerts' }));
};
ws.onmessage = (evt) => console.log('Event:', JSON.parse(evt.data));
```

### 8.2 Emergency Stop

**Immediate shutdown:**
```bash
# Stop backend
Ctrl+C

# Or kill process
pkill -f start_server.py

# Cancel all open orders via Alpaca dashboard
# https://app.alpaca.markets/paper/dashboard (paper)
# https://app.alpaca.markets/brokerage/dashboard (live)
```

**Disable auto-execution without restart:**
```bash
# Edit .env while server running
AUTO_EXECUTE_TRADES=false

# Restart server
python start_server.py
```

### 8.3 Daily Monitoring Checklist

- [ ] Check P&L dashboard
- [ ] Review executed trades vs signals
- [ ] Verify no stuck positions (> 5 days old)
- [ ] Check circuit breaker status
- [ ] Review risk gauges (heat, drawdown)
- [ ] Check external API health (scheduler logs)
- [ ] Verify LLM inference not timing out

---

## Troubleshooting Common Issues

### Issue: "Alpaca connection error: [Errno -5]"

**Cause:** DNS resolution failure or network blocking

**Fix:**
1. Test DNS: `nslookup paper-api.alpaca.markets`
2. Test HTTPS: `curl -I https://paper-api.alpaca.markets/v2/clock`
3. Check firewall/proxy settings
4. Verify API keys not expired

### Issue: "CouncilGate DISABLED"

**Cause:** LLM_ENABLED=false or Ollama not running

**Fix:**
1. Set `LLM_ENABLED=true` in `.env`
2. Start Ollama: `ollama serve`
3. Verify: `curl http://localhost:11434/api/tags`
4. Restart backend

### Issue: "MarketWideSweep: universe=0 symbols"

**Cause:** Empty DuckDB + Alpaca API failure

**Fix:**
1. Backfill data: `python -m app.jobs.backfill_bars --symbol SPY --days 365`
2. Or fix Alpaca connectivity (see above)
3. Restart backend

### Issue: "Scheduler disabled"

**Cause:** SCHEDULER_ENABLED=false

**Fix:**
1. Set `SCHEDULER_ENABLED=true` in `.env`
2. Add at least 1 API key (FRED recommended, it's free)
3. Restart backend

### Issue: WebSocket not connecting from browser

**Cause:** CORS or proxy misconfiguration

**Fix:**
1. Check `CORS_ORIGINS` includes frontend URL
2. Verify proxy in `vite.config.js`:
   ```javascript
   proxy: {
     "/ws": { target: "ws://localhost:8000", ws: true }
   }
   ```
3. Clear browser cache, hard reload

### Issue: High memory usage (>4 GB)

**Cause:** Large LLM model + many concurrent swarms

**Fix:**
1. Use smaller model: `llama3.2` instead of `mixtral:8x7b`
2. Reduce concurrent swarms: `COUNCIL_MAX_CONCURRENT=1` in `.env`
3. Disable heavy services: `UNIFIED_PROFIT_ENGINE=false`

---

## Verification Script

Run this script to check all dependencies:

```bash
cd backend
python scripts/verify_live_trading_setup.py

# Expected: ✅ All checks pass
```

(See `scripts/verify_live_trading_setup.py` for implementation)

---

## Production Deployment Checklist

- [ ] Valid Alpaca API keys (paper or live)
- [ ] Network connectivity verified
- [ ] Ollama running with model downloaded
- [ ] At least 1 data source API key configured
- [ ] FERNET_KEY generated and set
- [ ] API_AUTH_TOKEN generated and set
- [ ] Historical data backfilled (1+ year)
- [ ] Backend starts without errors
- [ ] Frontend connects to backend
- [ ] WebSocket channels active
- [ ] Council evaluations running (logs show agent votes)
- [ ] Paper trading validated (30+ days)
- [ ] Emergency stop procedure documented
- [ ] Daily monitoring schedule established

---

## Support & Documentation

- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **Health Check:** http://localhost:8000/api/v1/status/health
- **Logs:** `backend/logs/` (if configured)
- **Database:** `backend/data/elite_trading.db` (SQLite), `backend/data/analytics.duckdb` (DuckDB)

**Recommended reading:**
- `STARTUP_DEBUG_AUDIT.md` — Detailed startup flow audit
- `README.md` — Project overview
- `backend/.env.example` — Full configuration reference
- `docs/audits/brain_consciousness_audit_2026-03-08.pdf` — Council intelligence architecture

---

**Status after this guide:** ✅ **LIVE TRADING READY**

🎯 **Next Steps:**
1. Run verification script
2. Start 30-day paper trading validation
3. Monitor daily, iterate on strategy
4. Graduate to live trading when consistently profitable
