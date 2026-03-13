# Cursor Agent Prompt — Trading Assistant Implementation

> Copy everything below the line into Cursor as a single prompt.

---

Read these files first (in order): `CLAUDE.md`, `project_state.md`, `docs/TRADING-ASSISTANT-PLAN.md`, `docs/TRADING-ASSISTANT-RESEARCH.md`

## Context

Embodier Trader v5.0.0 is a FastAPI backend + React 18/Vite frontend trading platform with 35-agent council DAG, 981+ tests, CI GREEN. We need to build the **Trading Assistant Module** — a morning briefing service, TradingView webhook bridge, trade journal, and position monitoring system. This is 4 new backend files, 2 new API route files, 1 new frontend page, and tests.

Reference the existing codebase patterns throughout. All existing services, schemas, and patterns must be reused — never duplicate logic.

## What to Build

### FILE 1: `backend/app/services/briefing_service.py` (NEW — Core Service)

Create the `BriefingService` class — the orchestrator for all trading assistant features.

```python
# Dependencies to import from existing codebase:
# - from app.council.schemas import AgentVote, DecisionPacket
# - from app.services.signal_engine import EventDrivenSignalEngine (or however signals are accessed)
# - from app.services.kelly_position_sizer import calculate position sizing
# - from app.council.regime.bayesian_regime import get_regime_state
# - from app.data.storage import get_conn (DuckDB)
# - from app.services.slack_notification_service import SlackNotificationService
# - from app.core.message_bus import MessageBus
```

**Methods required:**

`async generate_morning_briefing() -> dict`:
- Query DuckDB for active signals via existing signal engine queries
- Get current regime from bayesian_regime service
- Get open positions from Alpaca service (existing `alpaca_service.py`)
- Get portfolio heat from existing risk calculations
- Filter signals: score ≥ regime-adaptive threshold (GREEN=55, YELLOW=65, RED/CRISIS=75), confidence ≥ 0.4
- Exclude symbols with open positions
- Rank by Kelly edge × confidence × regime suitability
- Take top 5
- For each signal, compute TradingView levels (see `format_tradingview_levels`)
- Publish `briefing.generated` event on MessageBus
- Return structured JSON (see schema below)

`async get_position_review() -> dict`:
- Get all open positions from Alpaca
- For each position: compute unrealized P&L, R-multiple progress, days in trade, distance to stop
- Flag positions needing attention: within 0.5R of stop, >18 days held, regime changed since entry
- Return list of enriched position objects

`format_tradingview_levels(signal: dict, atr: float) -> dict`:
- Compute entry_zone: [current_price * 0.998, current_price * 1.002] (0.2% band around signal price)
- Compute stop_loss: entry_price - (2.0 × ATR) for longs, entry_price + (2.0 × ATR) for shorts
- Compute target_1: entry_price + (2 × risk) where risk = abs(entry - stop)
- Compute target_2: entry_price + (3 × risk)
- Compute position_size_pct using existing Kelly sizer
- Return dict with all levels + metadata

`async generate_weekly_review(start_date, end_date) -> dict`:
- Query DuckDB `council_decisions` table for all decisions in date range
- Query DuckDB `trade_outcomes` table for all closed trades
- Compute: total P&L, win rate, avg R-multiple, max drawdown, Sharpe approximation
- Get agent Brier scores from weight_learner
- Identify best/worst trades by R-multiple
- Summarize regime transitions during the week
- Return structured review object

`format_slack_briefing(briefing: dict) -> str`:
- Format the morning briefing as Slack-compatible markdown
- Use emoji regime indicators: 🟢 GREEN, 🟡 YELLOW, 🔴 RED, ⚫ CRISIS
- Format each trade idea as a compact block with entry/stop/target
- Include portfolio summary header
- Include calendar events if any

`format_slack_weekly(review: dict) -> str`:
- Format weekly review as Slack markdown
- Include performance table, best/worst trades, agent calibration, regime summary

**Morning Briefing Return Schema:**
```python
{
    "timestamp": "2026-03-12T09:00:00-04:00",
    "regime": {
        "state": "bull",       # bull/bear/sideways/crisis
        "vix": 14.5,
        "confidence": 0.82,
        "signal_threshold": 55  # regime-adaptive
    },
    "portfolio": {
        "total_value": 100000.00,
        "heat_pct": 4.2,
        "open_positions": 3,
        "daily_pnl": 250.00,
        "drawdown_pct": 1.5
    },
    "positions": [
        {
            "symbol": "AAPL",
            "direction": "long",
            "entry_price": 178.50,
            "current_price": 181.20,
            "unrealized_pnl": 270.00,
            "r_multiple": 0.73,
            "days_held": 5,
            "stop_loss": 174.80,
            "needs_attention": false,
            "attention_reason": null
        }
    ],
    "trade_ideas": [
        {
            "symbol": "MSFT",
            "direction": "buy",
            "score": 82,
            "confidence": 0.87,
            "kelly_fraction": 0.012,
            "entry_zone": [415.50, 416.30],
            "stop_loss": 409.80,
            "target_1": 425.90,
            "target_2": 431.50,
            "position_size_pct": 1.2,
            "risk_per_share": 6.10,
            "reward_risk_ratio": 2.0,
            "regime": "bull",
            "council_decision_id": "uuid-here",
            "top_agents": ["regime(1.2)", "momentum(0.82)", "flow(0.79)"],
            "risk_notes": "Portfolio heat at 4.2%, sector OK, no earnings this week"
        }
    ],
    "calendar_events": [
        {
            "type": "earnings",
            "symbol": "ORCL",
            "date": "2026-03-12",
            "timing": "AMC",
            "impact": "medium"
        }
    ],
    "webhook_sent": true,
    "slack_sent": true
}
```

### FILE 2: `backend/app/services/tradingview_bridge.py` (NEW — Webhook Bridge)

Create `TradingViewBridge` class for outbound signal delivery.

```python
import httpx
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TradingViewBridge:
    """Pushes Embodier Trader signals to external webhooks.

    Supports two destinations (both fire if configured):
    - TRADINGVIEW_WEBHOOK_URL: webhook.site for testing / monitoring
    - TRADERSPOST_WEBHOOK_URL: TradersPost for actual Alpaca execution

    TradersPost webhook: https://webhooks.traderspost.io/trading/webhook/40bbd93b-9ee2-4aff-a56d-237465d849fb/a07f5ad16fbcb7925246eebf611c4770
    """

    def __init__(self):
        self.webhook_url = os.getenv("TRADINGVIEW_WEBHOOK_URL", "")
        self.traderspost_url = os.getenv("TRADERSPOST_WEBHOOK_URL", "")
        self.enabled = bool(self.webhook_url) or bool(self.traderspost_url)
        self.timeout = 10.0  # seconds

    async def push_signals(self, trade_ideas: list[dict], execute: bool = False) -> dict:
        """Send trade ideas to configured webhook URLs.

        Args:
            trade_ideas: List of signal dicts from briefing service
            execute: If True, ALSO send to TradersPost for real Alpaca execution.
                     If False, only send to monitoring webhook (webhook.site).
                     This is a safety gate — never auto-execute without explicit flag.

        Returns delivery status.
        """
        if not self.enabled:
            logger.info("No webhook URLs configured")
            return {"sent": False, "reason": "no_webhook_urls_configured"}

        monitor_results = []
        execution_results = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for idea in trade_ideas:
                # Always send to monitoring webhook (webhook.site)
                if self.webhook_url:
                    payload = self._format_payload(idea)
                    try:
                        resp = await client.post(self.webhook_url, json=payload)
                        monitor_results.append({
                            "symbol": idea["symbol"],
                            "status": resp.status_code,
                            "success": 200 <= resp.status_code < 300
                        })
                    except httpx.RequestError as e:
                        logger.error(f"Monitor webhook failed for {idea['symbol']}: {e}")
                        monitor_results.append({"symbol": idea["symbol"], "success": False, "error": str(e)})

                # Only send to TradersPost if execute=True (safety gate)
                if execute and self.traderspost_url:
                    tp_payload = self._format_traderspost_payload(idea)
                    try:
                        resp = await client.post(self.traderspost_url, json=tp_payload)
                        execution_results.append({
                            "symbol": idea["symbol"],
                            "status": resp.status_code,
                            "success": 200 <= resp.status_code < 300
                        })
                    except httpx.RequestError as e:
                        logger.error(f"TradersPost execution failed for {idea['symbol']}: {e}")
                        execution_results.append({"symbol": idea["symbol"], "success": False, "error": str(e)})

        return {
            "sent": True,
            "monitor_results": monitor_results,
            "execution_results": execution_results,
            "executed": execute,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _format_payload(self, idea: dict) -> dict:
        """Format for monitoring webhook (webhook.site) — full detail."""
        return {
            "ticker": idea["symbol"],
            "action": idea["direction"],
            "price": idea["entry_zone"][0] if idea.get("entry_zone") else 0,
            "stop_loss": idea.get("stop_loss", 0),
            "take_profit": idea.get("target_1", 0),
            "take_profit_2": idea.get("target_2", 0),
            "position_size_pct": idea.get("position_size_pct", 0),
            "order_type": "limit",
            "confidence": idea.get("confidence", 0),
            "score": idea.get("score", 0),
            "regime": idea.get("regime", "unknown"),
            "council_decision_id": idea.get("council_decision_id", ""),
            "source": "embodier_trader",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": f"Embodier: {idea['direction'].upper()} {idea['symbol']} | Score {idea.get('score', 0)} | Conf {idea.get('confidence', 0):.0%}"
        }

    def _format_traderspost_payload(self, idea: dict) -> dict:
        """Format for TradersPost — matches their expected webhook schema.
        See: https://docs.traderspost.io/webhooks
        TradersPost expects: ticker, action, price (minimum).
        Optional: sentiment, quantity, time, interval.
        """
        return {
            "ticker": idea["symbol"],
            "action": idea["direction"],  # "buy" or "sell"
            "sentiment": "bullish" if idea["direction"] == "buy" else "bearish",
            "price": idea["entry_zone"][0] if idea.get("entry_zone") else 0,
            "time": datetime.now(timezone.utc).isoformat()
        }
```

**Env vars to add to `.env.example` and `.env`:**
```
# TradingView / TradersPost webhook bridge (outbound signals)
TRADINGVIEW_WEBHOOK_URL=https://webhook.site/6dbab002-7eca-43b8-8d92-8dd8c73495b7
TRADERSPOST_WEBHOOK_URL=https://webhooks.traderspost.io/trading/webhook/40bbd93b-9ee2-4aff-a56d-237465d849fb/a07f5ad16fbcb7925246eebf611c4770
```

### FILE 3: `backend/app/api/v1/briefing.py` (NEW — API Routes)

```python
from fastapi import APIRouter, Depends, Query
from datetime import date, timedelta
from app.core.security import require_auth
# Import your BriefingService

router = APIRouter(prefix="/api/v1/briefing", tags=["briefing"])
```

**Endpoints:**

`GET /api/v1/briefing/morning` (auth required)
- Calls `BriefingService.generate_morning_briefing()`
- Optionally sends to Slack (query param `?notify=true`)
- Optionally pushes to TradingView webhook (query param `?webhook=true`)
- Returns the full briefing JSON

`GET /api/v1/briefing/positions` (auth required)
- Calls `BriefingService.get_position_review()`
- Returns enriched position list with attention flags

`GET /api/v1/briefing/weekly` (auth required)
- Query params: `start_date`, `end_date` (defaults to last 7 days)
- Calls `BriefingService.generate_weekly_review(start, end)`
- Returns weekly review JSON

`POST /api/v1/briefing/webhook/test` (auth required)
- Sends a test payload to the configured TRADINGVIEW_WEBHOOK_URL
- Returns delivery status
- Use this to verify webhook.site integration

`GET /api/v1/briefing/status` (auth required)
- Returns briefing service configuration: webhook URL configured?, Slack configured?, last briefing time, regime state

### FILE 4: `backend/app/api/v1/tradingview.py` (NEW — TradingView-specific routes)

```python
router = APIRouter(prefix="/api/v1/tradingview", tags=["tradingview"])
```

**Endpoints:**

`POST /api/v1/tradingview/push-signals` (auth required)
- Accepts list of signal objects (or uses latest from briefing service)
- Query param `?execute=true` to ALSO send to TradersPost for real Alpaca execution
- Default: execute=false (monitoring only — webhook.site)
- Calls `TradingViewBridge.push_signals(trade_ideas, execute=execute)`
- Returns delivery results for both monitoring and execution webhooks
- SAFETY: The execute flag is an explicit opt-in. Never auto-execute.

`GET /api/v1/tradingview/config` (auth required)
- Returns: webhook_url configured (bool), last push timestamp, delivery stats

`GET /api/v1/tradingview/pine-script` (no auth — public)
- Returns the Pine Script indicator code as plain text
- This is the Embodier Signal Overlay indicator for TradingView
- Content-Type: text/plain

The Pine Script indicator to serve:
```pine
//@version=5
indicator("Embodier Signals", overlay=true, max_labels_count=10)

// === INPUTS ===
direction  = input.string("none", "Direction", options=["long", "short", "none"], group="Signal")
entryPrice = input.float(0.0, "Entry Price", group="Signal")
stopLoss   = input.float(0.0, "Stop Loss", group="Signal")
target1    = input.float(0.0, "Target 1 (2R)", group="Signal")
target2    = input.float(0.0, "Target 2 (3R)", group="Signal")
showLabels = input.bool(true, "Show Labels", group="Display")

// === COLORS ===
entryColor = color.new(color.blue, 20)
stopColor  = color.new(color.red, 20)
t1Color    = color.new(color.green, 20)
t2Color    = color.new(color.lime, 30)

// === PLOT LEVELS ===
isActive = direction != "none" and entryPrice > 0

plot(isActive ? entryPrice : na, "Entry", color=entryColor, linewidth=2, style=plot.style_linebr)
plot(isActive ? stopLoss : na, "Stop", color=stopColor, linewidth=2, style=plot.style_linebr)
plot(isActive ? target1 : na, "T1 (2R)", color=t1Color, linewidth=1, style=plot.style_linebr)
plot(isActive ? target2 : na, "T2 (3R)", color=t2Color, linewidth=1, style=plot.style_linebr)

// === FILL ZONES ===
entryLine = plot(isActive ? entryPrice : na, display=display.none)
stopLine  = plot(isActive ? stopLoss : na, display=display.none)
t1Line    = plot(isActive ? target1 : na, display=display.none)

fill(entryLine, stopLine, color=color.new(color.red, 90), title="Risk Zone")
fill(entryLine, t1Line, color=color.new(color.green, 90), title="Reward Zone")

// === LABELS ===
if isActive and showLabels and barstate.islast
    riskPerShare = math.abs(entryPrice - stopLoss)
    rewardRatio = riskPerShare > 0 ? math.abs(target1 - entryPrice) / riskPerShare : 0

    label.new(bar_index + 2, entryPrice, "ENTRY " + str.tostring(entryPrice, "#.##"),
              color=entryColor, textcolor=color.white, size=size.small)
    label.new(bar_index + 2, stopLoss, "STOP " + str.tostring(stopLoss, "#.##"),
              color=stopColor, textcolor=color.white, size=size.small)
    label.new(bar_index + 2, target1, "T1 " + str.tostring(target1, "#.##") + " (" + str.tostring(rewardRatio, "#.#") + "R)",
              color=t1Color, textcolor=color.white, size=size.small)
    label.new(bar_index + 2, target2, "T2 " + str.tostring(target2, "#.##"),
              color=t2Color, textcolor=color.white, size=size.small)

// === ALERTS ===
longEntryZone  = direction == "long" and close <= entryPrice * 1.003 and close >= entryPrice * 0.997
shortEntryZone = direction == "short" and close >= entryPrice * 0.997 and close <= entryPrice * 1.003
stopHit        = (direction == "long" and low <= stopLoss) or (direction == "short" and high >= stopLoss)
t1Hit          = (direction == "long" and high >= target1) or (direction == "short" and low <= target1)

alertcondition(longEntryZone, "Long Entry Zone", "EMBODIER: Price in LONG entry zone for {{ticker}}")
alertcondition(shortEntryZone, "Short Entry Zone", "EMBODIER: Price in SHORT entry zone for {{ticker}}")
alertcondition(stopHit, "Stop Loss Hit", "EMBODIER: STOP HIT on {{ticker}}")
alertcondition(t1Hit, "Target 1 Hit", "EMBODIER: TARGET 1 HIT on {{ticker}} — consider trailing stop")
```

### FILE 5: `frontend-v2/src/pages/TradingViewBridge.jsx` (NEW — Frontend Page)

Create a page at route `/tradingview` that displays:

1. **Morning Briefing Panel** — Today's trade ideas with copy-pasteable TradingView levels
2. **Position Monitor** — Open positions with R-multiple progress bars
3. **Webhook Status** — Whether outbound webhook is configured and last delivery status
4. **Pine Script** — Downloadable Pine Script indicator code

Use existing patterns:
```javascript
import { useApi } from '../hooks/useApi';
// Fetch data:
const briefing = useApi('morningBriefing');  // GET /api/v1/briefing/morning
const positions = useApi('briefingPositions'); // GET /api/v1/briefing/positions
const tvConfig = useApi('tradingviewConfig');  // GET /api/v1/tradingview/config
```

**Layout**: Inside `<Layout />` wrapper (mandatory). Use the ultrawide command strip pattern from Trade Execution page. TailwindCSS dark theme.

**Key UI elements:**
- Regime badge (colored: green/yellow/red/black) at top
- Portfolio heat meter (progress bar, warning at >6%)
- Trade idea cards: each card shows symbol, direction, entry/stop/target with one-click copy
- "Copy All Levels" button that copies all TradingView inputs as formatted text
- "Push to Webhook" button that calls POST /api/v1/tradingview/push-signals
- "Download Pine Script" button

### FILE 6: Register Everything

**`backend/app/main.py`** — Add to router registration section (around line 44):
```python
from app.api.v1 import briefing, tradingview
app.include_router(briefing.router)
app.include_router(tradingview.router)
```

**`frontend-v2/src/config/api.js`** — Add endpoint definitions:
```javascript
morningBriefing: { method: 'GET', path: '/api/v1/briefing/morning' },
briefingPositions: { method: 'GET', path: '/api/v1/briefing/positions' },
weeklyReview: { method: 'GET', path: '/api/v1/briefing/weekly' },
briefingWebhookTest: { method: 'POST', path: '/api/v1/briefing/webhook/test' },
briefingStatus: { method: 'GET', path: '/api/v1/briefing/status' },
tradingviewPushSignals: { method: 'POST', path: '/api/v1/tradingview/push-signals' },
tradingviewConfig: { method: 'GET', path: '/api/v1/tradingview/config' },
tradingviewPineScript: { method: 'GET', path: '/api/v1/tradingview/pine-script' },
```

**`frontend-v2/src/App.jsx`** — Add route inside `<Layout />`:
```jsx
<Route path="/tradingview" element={<TradingViewBridge />} />
```

**`frontend-v2/src/components/layout/Sidebar.jsx`** — Add nav item under Tools section:
```jsx
{ path: '/tradingview', label: 'TradingView Bridge', icon: <TvMinimal size={18} /> }
```

**`backend/.env.example`** — Add:
```
# TradingView / TradersPost webhook bridge (outbound signals)
# TRADINGVIEW_WEBHOOK_URL = monitoring/testing (webhook.site or similar)
# TRADERSPOST_WEBHOOK_URL = execution (TradersPost → Alpaca orders)
TRADINGVIEW_WEBHOOK_URL=
TRADERSPOST_WEBHOOK_URL=
```

### FILE 7: `backend/tests/test_briefing.py` (NEW — Tests)

Write tests for:

1. `test_briefing_service_init` — Service instantiates without error
2. `test_format_tradingview_levels_long` — Long trade levels calculated correctly (entry zone, stop = entry - 2×ATR, target1 = entry + 2×risk, target2 = entry + 3×risk)
3. `test_format_tradingview_levels_short` — Short trade levels calculated correctly (flipped)
4. `test_tradingview_bridge_format_payload` — Payload format matches expected schema
5. `test_tradingview_bridge_disabled` — Returns gracefully when TRADINGVIEW_WEBHOOK_URL is empty
6. `test_briefing_morning_endpoint` — GET /api/v1/briefing/morning returns 200 with auth
7. `test_briefing_morning_no_auth` — GET /api/v1/briefing/morning returns 401 without auth
8. `test_briefing_positions_endpoint` — GET /api/v1/briefing/positions returns 200
9. `test_briefing_weekly_endpoint` — GET /api/v1/briefing/weekly returns 200
10. `test_webhook_test_endpoint` — POST /api/v1/briefing/webhook/test returns result
11. `test_briefing_status_endpoint` — GET /api/v1/briefing/status returns config
12. `test_pine_script_endpoint` — GET /api/v1/tradingview/pine-script returns text/plain
13. `test_regime_adaptive_threshold` — Signals filtered correctly per regime (GREEN=55, YELLOW=65, RED=75)
14. `test_position_attention_flags` — Positions near stop, old, or regime-changed are flagged
15. `test_slack_briefing_format` — Slack message contains required sections (regime, positions, ideas)

Use existing test patterns from `conftest.py` (monkey-patched DuckDB, in-memory DB). Mock Alpaca and external APIs.

## Rules (CRITICAL)

1. **Read CLAUDE.md section 16 coding rules** — follow every single one
2. **Never use yfinance** — use Alpaca/Finviz/UW for market data
3. **Never add mock data** — all data via real API endpoints and services
4. **4-space Python indentation** — never tabs
5. **All frontend data via `useApi()` hook** — never raw fetch
6. **DuckDB via `get_conn()` only** — never raw connections
7. **Bearer token auth** on all endpoints except pine-script (public)
8. **MessageBus for events** — publish `briefing.generated` and `briefing.weekly` events
9. **Existing services only** — reuse signal_engine, kelly_position_sizer, bayesian_regime, alpaca_service, slack_notification_service. Don't recreate their logic.
10. **Dashboard route inside `<Layout />`** in App.jsx
11. **Run tests before and after**: `cd backend && python -m pytest --tb=short -q`

## Verification

After implementation, confirm:
- [ ] `python -m pytest --tb=short -q` passes (existing 981+ tests + new tests)
- [ ] `GET /api/v1/briefing/morning` returns valid JSON with regime, positions, trade_ideas
- [ ] `GET /api/v1/briefing/positions` returns enriched position list
- [ ] `POST /api/v1/briefing/webhook/test` sends payload to webhook URL
- [ ] `GET /api/v1/tradingview/pine-script` returns Pine Script as text/plain
- [ ] Frontend `/tradingview` page renders with trade ideas and copy functionality
- [ ] Slack format includes emoji regime indicators
- [ ] No mock data anywhere — all endpoints return real or gracefully-degraded data
