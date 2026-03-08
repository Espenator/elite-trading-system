# API Key Inventory & Two-PC Setup Guide

> Version: v3.5.0
> Last updated: March 8, 2026
> Repo: elite-trading-system
> PC1 (ESPENMAIN): 192.168.1.105 - Primary trading + fast inference
> PC2 (ProfitTrader): 192.168.1.116 - Heavy compute + ML + Brain Service (Ollama gRPC 50051)

## Overview

Both PCs share the SAME repo and SAME `.env` keys for API services.
The only differences are cluster/network settings (which PC is master vs worker).

**IMPORTANT:** Never commit real keys to the repo. Only edit `backend/.env` locally on each PC.

---

## Master API Key Status

### TIER 1: CRITICAL (Required for Trading)

| Service | Env Var | Code File | Status | Get Key At | PC1 | PC2 |
|---------|---------|-----------|--------|------------|-----|-----|
| Alpaca Markets | `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | alpaca_service.py | NEEDS KEY | https://app.alpaca.markets | YES | YES |
| Alpaca (APCA compat) | `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` | config.py (property) | Auto-mapped from above | Same key | YES | YES |

### TIER 2: P0 AGENTS (Replace Slack - This Week)

| Service | Env Var | Code File | Status | Get Key At | PC1 | PC2 |
|---------|---------|-----------|--------|------------|-----|-----|
| Unusual Whales | `UNUSUAL_WHALES_API_KEY` | unusual_whales_service.py | NEEDS KEY | https://unusualwhales.com/pricing | YES | YES |
| Finviz Elite | `FINVIZ_API_KEY` | finviz_service.py | NEEDS KEY | https://elite.finviz.com/ | YES | YES |
| Discord Bot | `DISCORD_BOT_TOKEN` | discord_swarm_bridge.py | NEEDS KEY | https://discord.com/developers/applications | YES | NO |
| Discord Channels | `DISCORD_CHANNEL_IDS` | discord_swarm_bridge.py | NEEDS CONFIG | Get from Discord channel settings | YES | NO |

### TIER 3: INTELLIGENCE LAYER (LLMs)

| Service | Env Var | Code File | Status | Get Key At | PC1 | PC2 |
|---------|---------|-----------|--------|------------|-----|-----|
| Perplexity AI | `PERPLEXITY_API_KEY` | perplexity_intelligence.py | NEEDS KEY | https://docs.perplexity.ai/ | YES | YES |
| Anthropic/Claude | `ANTHROPIC_API_KEY` | claude_reasoning.py | NEEDS KEY | https://console.anthropic.com/ | YES | YES |
| Ollama (Local) | `OLLAMA_BASE_URL` | ollama_node_pool.py | AUTO (localhost) | Install: https://ollama.ai | YES | YES |

### TIER 4: DATA ENRICHMENT

| Service | Env Var | Code File | Status | Get Key At | PC1 | PC2 |
|---------|---------|-----------|--------|------------|-----|-----|
| FRED | `FRED_API_KEY` | fred_service.py | NEEDS KEY | https://fred.stlouisfed.org/docs/api/api_key.html | YES | YES |
| SEC EDGAR | `SEC_EDGAR_USER_AGENT` | sec_edgar_service.py | NEEDS CONFIG | Free - just set name + email | YES | YES |
| News API | `NEWS_API_KEY` | news_aggregator.py | NEEDS KEY | https://newsapi.org/ | YES | YES |
| StockGeist | `STOCKGEIST_API_KEY` | social_perception_agent.py | NEEDS KEY | https://stockgeist.ai/ | YES | NO |

### TIER 5: P1 AGENTS (Next Week)

| Service | Env Var | Code File | Status | Get Key At | PC1 | PC2 |
|---------|---------|-----------|--------|------------|-----|-----|
| YouTube Data API | `YOUTUBE_API_KEY` | youtube_knowledge_agent.py | NEEDS KEY | https://console.cloud.google.com/apis | YES | NO |
| X/Twitter API v2 | `X_BEARER_TOKEN` | social_perception_agent.py | NEEDS KEY | https://developer.x.com/ | YES | NO |
| X (Full) | `X_API_KEY` / `X_API_KEY_SECRET` | config.py | NEEDS KEY | Same as above | YES | NO |

### TIER 6: ALERTS & NOTIFICATIONS

| Service | Env Var | Code File | Status | Get Key At | PC1 | PC2 |
|---------|---------|-----------|--------|------------|-----|-----|
| Resend (email) | `RESEND_API_KEY` | config.py | OPTIONAL | https://resend.com/ | YES | NO |
| Telegram | `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | config.py | OPTIONAL | https://core.telegram.org/bots | YES | NO |

### TIER 7: CLUSTER / MULTI-PC

| Setting | Env Var | Code File | PC1 Value | PC2 Value |
|---------|---------|-----------|-----------|----------|
| Cluster PC2 Host | `CLUSTER_PC2_HOST` | node_discovery.py | `192.168.1.116` | (empty) |
| Redis URL | `REDIS_URL` | message_bus.py | `redis://192.168.1.105:6379/0` | `redis://192.168.1.105:6379/0` |
| Brain Host | `BRAIN_HOST` | brain_client.py | `192.168.1.116` | `localhost` |
| Brain Port | `BRAIN_PORT` | brain_client.py | `50051` | `50051` |
| Brain Enabled | `BRAIN_ENABLED` | brain_client.py | `true` | `false` |
| Ollama PC2 URL | `OLLAMA_PC2_URL` | ollama_node_pool.py | `http://192.168.1.116:11434` | `http://localhost:11434` |
| Scanner Ollama URLs | `SCANNER_OLLAMA_URLS` | turbo_scanner.py | `http://localhost:11434,http://192.168.1.116:11434` | `http://localhost:11434` |

---

## Setup Checklist

### Step 1: Get API Keys (Do Once)

Open each URL below and create/get your API key:

- [ ] **Alpaca**: https://app.alpaca.markets -> Paper Trading -> API Keys
- [ ] **Unusual Whales**: https://unusualwhales.com/pricing -> Get paid plan -> API tab
- [ ] **Finviz Elite**: https://elite.finviz.com/ -> Already subscribed? -> API key in account settings
- [ ] **Discord Bot**: https://discord.com/developers/applications -> New Application -> Bot -> Token
- [ ] **Perplexity**: https://docs.perplexity.ai/ -> API Keys
- [ ] **Anthropic**: https://console.anthropic.com/ -> API Keys
- [ ] **FRED**: https://fred.stlouisfed.org/docs/api/api_key.html -> Request Key (free, instant)
- [ ] **SEC EDGAR**: Free - just set `SEC_EDGAR_USER_AGENT=YourName your@email.com`
- [ ] **News API**: https://newsapi.org/ -> Get API Key (free tier available)
- [ ] **YouTube**: https://console.cloud.google.com -> Enable YouTube Data API v3 -> Create Credential
- [ ] **X/Twitter**: https://developer.x.com/ -> Developer Portal -> Create Project -> Bearer Token

### Step 2: Configure PC1 (ESPENMAIN)

```powershell
cd C:\Users\Espen\elite-trading-system\backend
copy .env.example .env
# Edit .env with your keys - use notepad, VS Code, etc.
notepad .env
```

PC1 `.env` overrides (add at bottom):
```env
# --- PC1 CLUSTER CONFIG ---
CLUSTER_PC2_HOST=192.168.1.116
REDIS_URL=redis://192.168.1.105:6379/0
BRAIN_HOST=192.168.1.116
OLLAMA_PC2_URL=http://192.168.1.116:11434
SCANNER_OLLAMA_URLS=http://localhost:11434,http://192.168.1.116:11434
```

### Step 3: Configure PC2 (ProfitTrader)

```powershell
cd C:\Users\ProfitTrader\elite-trading-system\backend
copy .env.example .env
notepad .env
```

PC2 `.env` overrides (add at bottom):
```env
# --- PC2 CLUSTER CONFIG ---
CLUSTER_PC2_HOST=
REDIS_URL=redis://192.168.1.105:6379/0
BRAIN_HOST=localhost
OLLAMA_PC2_URL=http://localhost:11434
SCANNER_OLLAMA_URLS=http://localhost:11434
# PC2 doesn't need Discord bot, YouTube, X keys
# PC2 DOES need: Alpaca, UW, Finviz, Perplexity, Anthropic, FRED, News
```

### Step 4: Install Redis on PC1 (For Cross-PC MessageBus)

```powershell
# On ESPENMAIN (PC1):
winget install Redis.Redis
# Or use Docker:
docker run -d --name redis -p 6379:6379 redis:alpine
```

Then open Redis port in Windows Firewall (already have script):
```powershell
.\scripts\setup-redis-firewall.ps1
```

### Step 5: Verify

Run on each PC:
```powershell
cd backend
python -c "from app.core.config import settings; print('Alpaca:', bool(settings.ALPACA_API_KEY)); print('UW:', bool(settings.UNUSUAL_WHALES_API_KEY)); print('Finviz:', bool(settings.FINVIZ_API_KEY)); print('Discord:', bool(settings.DISCORD_BOT_TOKEN)); print('Perplexity:', bool(settings.PERPLEXITY_API_KEY))"
```

---

## Which Keys Go Where?

```
                    PC1 (ESPENMAIN)     PC2 (ProfitTrader)
Alpaca              YES                 YES
Unusual Whales      YES                 YES
Finviz              YES                 YES
Discord Bot         YES                 NO (PC1 runs the bot)
Perplexity          YES                 YES
Anthropic           YES                 YES
Ollama              YES (local)         YES (local + gRPC 50051)
Brain Service       CLIENT (port 50051) SERVER (runs server.py)
FRED                YES                 YES
SEC EDGAR           YES                 YES
News API            YES                 YES
StockGeist          YES                 NO
YouTube             YES                 NO
X/Twitter           YES                 NO
Resend              YES                 NO
Telegram            YES                 NO
Redis               HOST (6379)         CLIENT (connect to PC1)
```

**Rule of thumb:** Data-fetching API keys go on BOTH PCs. Channel-monitoring agents (Discord, YouTube, X) run ONLY on PC1 to avoid duplicate ingestion. The brain_service (Ollama gRPC server) runs ONLY on PC2; PC1 connects to it as a client via `BRAIN_HOST=192.168.1.116` and `BRAIN_PORT=50051`.
