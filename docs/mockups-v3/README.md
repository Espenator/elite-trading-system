# Embodier Trader - V3 UI Mockups

> **Last Updated: March 2, 2026 (9:00 AM EST)**
>
> **Status: 22 mockup images in `images/` folder. 14 sidebar pages, all with mockups except Signals.jsx (deprecated/merged).**
>
> Code files are ALL committed in `frontend-v2/src/pages/`.
> See `frontend-v2/src/V3-ARCHITECTURE.md` for the authoritative page list.

---

## Final 14 Sidebar Pages vs Mockup Status

| # | Section | Page | File | Route | Mockup Image(s) |
|---|---------|------|------|-------|----------------|
| 1 | COMMAND | Dashboard | `Dashboard.jsx` | `/` | `02-intelligence-dashboard.png` |
| 2 | COMMAND | Agent Command Center | `AgentCommandCenter.jsx` | `/agents` | `01-agent-command-center-final.png` + 6 sub-page mockups |
| 3 | INTELLIGENCE | Sentiment Intelligence | `SentimentIntelligence.jsx` | `/sentiment` | `04-sentiment-intelligence.png` |
| 4 | INTELLIGENCE | Data Sources Monitor | `DataSourcesMonitor.jsx` | `/data-sources` | `09-data-sources-manager.png` |
| 5 | INTELLIGENCE | Signal Intelligence | `SignalIntelligenceV3.jsx` | `/signal-intelligence-v3` | `03-signal-intelligence.png` |
| 6 | ML & ANALYSIS | ML Brain & Flywheel | `MLBrainFlywheel.jsx` | `/ml-brain` | `06-ml-brain-flywheel.png` |
| 7 | ML & ANALYSIS | Screener & Patterns | `Patterns.jsx` | `/patterns` | `07-screener-and-patterns.png` |
| 8 | ML & ANALYSIS | Backtesting Lab | `Backtesting.jsx` | `/backtesting` | `08-backtesting-lab.png` |
| 9 | ML & ANALYSIS | Performance Analytics | `PerformanceAnalytics.jsx` | `/performance` | `11-performance-analytics-fullpage.png` |
| 10 | ML & ANALYSIS | Market Regime | `MarketRegime.jsx` | `/market-regime` | `10-market-regime-green.png`, `10-market-regime-red.png` |
| 11 | EXECUTION | Active Trades | `Trades.jsx` | `/trades` | `Active-Trades.png` |
| 12 | EXECUTION | Risk Intelligence | `RiskIntelligence.jsx` | `/risk` | `13-risk-intelligence.png` |
| 13 | EXECUTION | Trade Execution | `TradeExecution.jsx` | `/trade-execution` | `12-trade-execution.png` |
| 14 | SYSTEM | Settings | `Settings.jsx` | `/settings` | `14-settings.png` |

### Non-Sidebar Page Files
| File | Status | Notes |
|------|--------|-------|
| `AlignmentEngine.jsx` | Shared component | Embedded in Settings (Alignment tab) and TradeExecution (governance card). No own route. |
| `Signals.jsx` | DEPRECATED | Merged into SignalIntelligenceV3.jsx. Can be deleted. |

---

## Agent Command Center Sub-Pages (8 tabs — code-verified)

| Tab | Description | Mockup Image | Status |
|-----|-------------|-------------|--------|
| Overview | Main dashboard + all 5 agent components | `01-agent-command-center-final.png` | COMPLETE |
| Agents | Intelligence agent grid with start/stop toggle | `05-agent-command-center.png` | COMPLETE |
| Swarm Control | Spawn agents, team scaling, resource allocation | `05b-agent-command-center-spawn.png`, `agent command center swarm overview.png` | COMPLETE |
| Candidates | Trade candidate symbols with composite scores | `agent command center node control.png` | COMPLETE |
| LLM Flow | Real-time LLM alert stream via WebSocket | No dedicated mockup | COMPLETE |
| Brain Map | DAG neural topology SVG (TODO: dynamic wiring) | `agent command center brain map.png` | PLACEHOLDER |
| Leaderboard | Agent performance ranking table | No dedicated mockup | COMPLETE |
| Blackboard | Real-Time Blackboard Pub/Sub feed | `realtimeblackbard fead.png`, `05d-blackboard-comms.html` | PLACEHOLDER |

## Settings Sub-Tabs (11 tabs — code-verified)

| Tab | Description | Mockup |
|-----|-------------|--------|
| Profile | User profile, display name, email, timezone | `14-settings.png` |
| API Keys | API key management (Alpaca, OpenClaw, providers) | `14-settings.png` |
| Trading | Trading parameters, default order type, sizing | `14-settings.png` |
| Risk | Risk settings, max drawdown, position limits | `14-settings.png` |
| AI / ML | AI/ML model configuration, inference settings | `14-settings.png` |
| Agents | Agent configuration, spawn defaults, teams | `14-settings.png` |
| Data Sources | Data source connections, refresh intervals | `14-settings.png` |
| Notifications | Alert preferences (Discord, Slack, email) | `14-settings.png` |
| Appearance | Theme, font size, density, accent color | `14-settings.png` |
| Audit Log | System audit trail, action history | `14-settings.png` |
| Alignment | Constitutive alignment governance (embeds AlignmentEngine) | `14-settings.png` |

## Pages With NO Sub-Pages (12 single-view pages)

Dashboard, Sentiment Intelligence, Data Sources Monitor, Signal Intelligence, ML Brain & Flywheel, Screener & Patterns, Backtesting Lab, Performance Analytics, Market Regime, Active Trades, Risk Intelligence, Trade Execution

---

## All Mockup Images in `images/` (22 total)

| File | Maps To |
|------|--------|
| `01-agent-command-center-final.png` | Agent Command Center |
| `02-intelligence-dashboard.png` | Dashboard |
| `03-signal-intelligence.png` | Signal Intelligence |
| `04-sentiment-intelligence.png` | Sentiment Intelligence |
| `05-agent-command-center.png` | Agent Command Center (alt) |
| `05b-agent-command-center-spawn.png` | ACC: Swarm Control |
| `05c-agent-registry.png` | ACC: Agents |
| `06-ml-brain-flywheel.png` | ML Brain & Flywheel |
| `07-screener-and-patterns.png` | Screener & Patterns |
| `08-backtesting-lab.png` | Backtesting Lab |
| `09-data-sources-manager.png` | Data Sources Monitor |
| `10-market-regime-green.png` | Market Regime (GREEN) |
| `10-market-regime-red.png` | Market Regime (RED) |
| `11-performance-analytics-fullpage.png` | Performance Analytics |
| `12-trade-execution.png` | Trade Execution |
| `13-risk-intelligence.png` | Risk Intelligence |
| `14-settings.png` | Settings |
| `Active-Trades.png` | Active Trades |
| `agent command center brain map.png` | ACC: Brain Map |
| `agent command center node control.png` | ACC: Candidates |
| `agent command center swarm overview.png` | ACC: Swarm Overview |
| `realtimeblackbard fead.png` | ACC: Blackboard Feed |

---

## Design Reference

See `docs/UI-DESIGN-SYSTEM.md` for the authoritative design system:
- Dark theme (#0a0a0f background, #1a1a2e cards)
- Cyan accent (#00d4ff) for primary actions
- Inter font family
- 24px padding, 12px border-radius
- V3 widescreen layout (no mobile)