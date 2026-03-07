# Slack -> Embodier Trader Migration Plan

> Date: 2026-03-07
> Status: PLANNING
> Owner: Espen

## Goal

Consolidate ALL signal ingestion, alerting, and channel monitoring into the Embodier Trader app itself. Slack served as an interim hub but the app now has the agent infrastructure to handle everything natively. Each external data channel (Discord, YouTube, X/Twitter, Finviz, Unusual Whales, etc.) gets a dedicated ingestion agent that feeds directly into the council pipeline.

---

## Phase 1: Slack Audit (Current State)

### Active Slack Channels

| Channel | Data Source | Status | Replacement |
|---------|------------|--------|-------------|
| #oc-whale-flow | Unusual Whales via OpenClaw Discord bridge | Active - signals flowing | WhaleFlowAgent (exists: whale_flow.py) |
| #finviz-alerts | Finviz Elite email->Slack | Active - screener alerts | FinvizAgent (exists: finviz_service.py) |
| #oc-signals-raw | Discord bridge raw signals | Empty | DiscordIngestAgent (NEW) |
| #oc-signals-hot | Filtered hot signals | Empty | SignalEngine scoring |
| #oc-trade-desk | Trade execution signals | Empty | ExecutionAgent (exists) |
| #trade-alerts | TradingView + OpenClaw | Empty | TradingViewWebhookAgent (NEW) |
| #oc-regime | Market regime updates | Empty | RegimeAgent (exists) |
| #oc-journal | Trade journal | Empty | OutcomeTracker (exists) |

### Slack Apps to Decommission
- OpenClaw (Discord bridge) -> replace with native discord_swarm_bridge.py
- Cursor -> no longer needed
- Perplexity Bot -> replaced by perplexity_intelligence.py service
- TradingView Alerts -> replace with native webhook endpoint
- Finviz email integration -> replace with direct Finviz API polling

---

## Phase 2: Channel Ingestion Agents (NEW)

Each external channel gets a dedicated agent under `backend/app/services/channels/`

### Agent Architecture

```
services/channels/
  __init__.py
  base_channel_agent.py      # Abstract base with common polling/websocket logic
  discord_agent.py           # Discord server monitoring (multiple servers)
  youtube_agent.py           # YouTube channel/live stream monitoring
  x_agent.py                 # X/Twitter list + keyword monitoring
  finviz_agent.py            # Finviz screener alert polling (direct API)
  tradingview_agent.py       # TradingView webhook receiver
  unusual_whales_agent.py    # UW options flow + dark pool (direct API)
  reddit_agent.py            # Subreddit monitoring (wallstreetbets, options, etc.)
  telegram_agent.py          # Telegram channel monitoring (future)
```

### Agent Details

#### 1. DiscordAgent
- **Replaces:** OpenClaw Slack bridge, Zapier Discord->Slack zap
- **Sources:** Unusual Whales Discord, OpenClaw Trading Signals server, Smart Trading Club
- **Channels to monitor:** #live-options-flow, #dark-pool-alerts, #trading-signals
- **Existing code:** discord_swarm_bridge.py (extend this)
- **Output:** Parsed signals -> MessageBus -> council pipeline
- **Priority:** P0 (already partially built)

#### 2. YouTubeAgent
- **Replaces:** Manual YouTube monitoring
- **Sources:** Trading YouTube channels, live streams, earnings calls
- **Method:** YouTube Data API v3 + transcript extraction
- **Existing code:** youtube_knowledge_agent.py (extend)
- **Output:** Summarized insights -> knowledge_ingest -> council
- **Priority:** P1

#### 3. XAgent (Twitter/X)
- **Replaces:** Nothing (NEW capability)
- **Sources:** FinTwit lists, key accounts (@unusual_whales, @DeItaone, @zaborzhets)
- **Method:** X API v2 filtered stream + keyword rules
- **Output:** Sentiment signals + breaking news -> news_catalyst_agent
- **Priority:** P1

#### 4. FinvizAgent
- **Replaces:** Finviz email->Slack alerts
- **Sources:** Finviz Elite screener (existing alerts: 5-Midday Unusual Volume, 3-Short Mean Reversion)
- **Method:** Direct Finviz API polling every 5 min during market hours
- **Existing code:** finviz_service.py (extend with alert rules)
- **Output:** Screener hits -> signal_engine -> council
- **Priority:** P0

#### 5. TradingViewAgent
- **Replaces:** TradingView Alerts Slack integration
- **Sources:** TradingView webhook alerts
- **Method:** FastAPI webhook endpoint (already have Flask route in OpenClaw)
- **Output:** Alert signals -> signal_engine -> council
- **Priority:** P1

#### 6. UnusualWhalesAgent
- **Replaces:** UW Discord -> Slack bridge
- **Sources:** UW API directly (paid plan endpoints)
- **Method:** REST API polling for options flow, dark pool, Congress trades
- **Existing code:** unusual_whales_service.py (already built)
- **Output:** Structured flow data -> dark_pool_agent, congressional_agent, insider_agent
- **Priority:** P0 (already built, wire to council)

#### 7. RedditAgent
- **Replaces:** Nothing (NEW capability)
- **Sources:** r/wallstreetbets, r/options, r/stocks DD posts
- **Method:** Reddit API + PRAW, sentiment analysis on high-engagement posts
- **Output:** Social sentiment -> social_perception_agent
- **Priority:** P2

---

## Phase 3: Unified Dashboard Integration

All channel agents feed into the existing Embodier Trader UI pages:

| Agent | UI Page | Dashboard Widget |
|-------|---------|------------------|
| DiscordAgent | Data Sources Monitor | Discord feed status + message count |
| YouTubeAgent | Sentiment Intelligence | YouTube sentiment gauge |
| XAgent | Sentiment Intelligence | X/FinTwit sentiment stream |
| FinvizAgent | Signal Intelligence | Finviz screener alert cards |
| TradingViewAgent | Signal Intelligence | TV alert log |
| UnusualWhalesAgent | Signal Intelligence | Options flow table |
| RedditAgent | Sentiment Intelligence | Reddit sentiment gauge |

---

## Phase 4: Slack Decommission Steps

1. **Week 1:** Deploy P0 agents (Discord, Finviz, UW) natively in Embodier Trader
2. **Week 1:** Verify data flowing through council pipeline and visible in UI
3. **Week 2:** Deploy P1 agents (YouTube, X, TradingView)
4. **Week 2:** Run Slack in parallel to validate no data loss
5. **Week 3:** Disable Slack integrations one by one:
   - Remove OpenClaw app from Slack
   - Disable Finviz email forwarding
   - Remove TradingView Alerts integration
   - Remove Cursor app
   - Remove Perplexity Bot
6. **Week 3:** Archive all oc-* channels
7. **Week 4:** Keep Slack workspace for team DMs with Oleh only (optional)

---

## Implementation Order

### Sprint 1 (P0) - This Week
- [ ] Wire unusual_whales_service.py output to council agents (dark_pool, congressional, insider)
- [ ] Extend finviz_service.py with screener alert polling + rules engine
- [ ] Extend discord_swarm_bridge.py to monitor UW Discord channels directly
- [ ] Add /api/v1/channels endpoint for agent status dashboard

### Sprint 2 (P1) - Next Week
- [ ] Build XAgent with X API v2 filtered stream
- [ ] Build TradingViewAgent webhook endpoint in FastAPI
- [ ] Extend youtube_knowledge_agent.py with live stream + channel monitoring
- [ ] Wire all new agents to DataSourcesMonitor UI page

### Sprint 3 (P2) - Week After
- [ ] Build RedditAgent
- [ ] Build TelegramAgent (optional)
- [ ] Full Slack decommission
- [ ] Final validation: all signals flowing natively

---

## Environment Variables Needed

```env
# Channel Agent Config
DISCORD_BOT_TOKEN=           # Already have this
YOUTUBE_API_KEY=             # Google Cloud API key
X_BEARER_TOKEN=              # X/Twitter API v2
X_API_KEY=
X_API_SECRET=
FINVIZ_EMAIL=                # Finviz Elite account
FINVIZ_PASSWORD=
REDDIT_CLIENT_ID=            # Reddit API
REDDIT_CLIENT_SECRET=
TRADINGVIEW_WEBHOOK_SECRET=  # Webhook validation
```

---

## Key Principle

Every external signal that used to flow through Slack now flows through:

```
Channel Agent -> MessageBus -> Council Pipeline -> Signal Engine -> UI Dashboard
                                    |                    |
                              Agent Analysis      Trade Execution
```

The Embodier Trader app becomes the single source of truth for ALL market intelligence, replacing Slack entirely as the signal hub.
