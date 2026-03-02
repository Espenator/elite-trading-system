# V3 Architecture - Embodier.ai Trading Intelligence System

## Overview

Consolidated to **14 sidebar pages** (+ 1 hidden debug route) for cleaner UX and maintainability.
All pages use V3 widescreen layout with dark theme. Charting uses a mix of **lightweight-charts** (LW Charts) and **Recharts** -- migration to 100% LW Charts is in progress.

> **Current Status (Mar 2, 2026 - Comet AI Session):**
> - Signals.jsx merged into SignalIntelligenceV3.jsx (now "Signal Intelligence" in sidebar)
> - AlignmentEngine.jsx embedded into Settings.jsx (Alignment tab) and TradeExecution.jsx (governance card)
> - AlignmentEngine.jsx no longer has its own route; it is a shared component used by Settings and TradeExecution
> - Final sidebar count: 14 pages across 5 sections

> **IMPORTANT**: This is the AUTHORITATIVE architecture doc. Sidebar.jsx defines the 14 visible pages.
> App.jsx defines all 14 sidebar routes + 1 hidden debug route = 15 total routes.

---

## Final 14-Page Sidebar Architecture (matches App.jsx + Sidebar.jsx)

### COMMAND (2 pages)

| # | Page | File | Route | Mockup | Notes |
|---|------|------|-------|--------|-------|
| 1 | Dashboard | `Dashboard.jsx` | `/` | `02-intelligence-dashboard.png` | Main overview with market cards, agent status, portfolio summary |
| 2 | Agent Command Center | `AgentCommandCenter.jsx` | `/agents` | `01-agent-command-center-final.png` | 6 internal tabs, 5 decomposed agent components, swarm visualization |

#### Agent Command Center Sub-Pages (6 tabs — verified from code lines 721-730)
| Tab ID | Tab Label | Description | Component Files | Mockup Image | Status |
|--------|-----------|-------------|----------------|-------------|--------|
| `overview` | Overview | Main dashboard: RegimeGauge, Swarm Status, Active Teams, Wave State + all 5 decomposed agent components | `SwarmTopology.jsx`, `ConferencePipeline.jsx`, `SystemAlerts.jsx`, `DriftMonitor.jsx`, `AgentResourceMonitor.jsx` | `01-agent-command-center-final.png` | COMPLETE |
| `agents` | Agents | Intelligence Agents grid with AgentCard toggle (start/stop) | Inline AgentCard component | `05-agent-command-center.png` | COMPLETE |
| `swarm` | Swarm Control | Spawn new agents form, team scaling, resource allocation | Inline (spawn form, scaling controls) | `05b-agent-command-center-spawn.png`, `agent command center swarm overview.png` | COMPLETE |
| `candidates` | Candidates | Trade candidate symbols with composite scores, click-to-execute | Inline (symbol grid with heatmap scoring) | `agent command center node control.png` | COMPLETE |
| `brain-map` | Brain Map | DAG neural topology SVG — agent inter-dependencies visualization | Inline SVG (TODO: wire nodes dynamically) | `agent command center brain map.png` | PLACEHOLDER — needs dynamic wiring |
| `blackboard` | Blackboard | Real-Time Blackboard Pub/Sub feed for inter-agent memory bus + HITL Ring Buffer | Inline (marked MISSING V3 in code) | `realtimeblackbard fead.png`, `05d-blackboard-comms.html` | COMPLETE - real-time mock via setInterval, WebSocket-ready |

**Agent Component Usage:** All 5 decomposed agent components (`SwarmTopology`, `ConferencePipeline`, `DriftMonitor`, `SystemAlerts`, `AgentResourceMonitor`) render inside the **Overview** tab, not as separate tabs.

**Mockup Coverage:** 7 mockup images cover ACC. Brain Map tab is the only remaining placeholder. Blackboard is COMPLETE with real-time mock data. Leaderboard table is now embedded in the Overview tab.

### INTELLIGENCE (3 pages)

| # | Page | File | Route | Mockup | Notes |
|---|------|------|-------|--------|-------|
| 3 | Sentiment Intelligence | `SentimentIntelligence.jsx` | `/sentiment` | `04-sentiment-intelligence.png` | Multi-panel sentiment analysis |
| 4 | Data Sources Monitor | `DataSourcesMonitor.jsx` | `/data-sources` | `09-data-sources-manager.png` | Data pipeline monitoring, 636 lines |
| 5 | Signal Intelligence | `SignalIntelligenceV3.jsx` | `/signal-intelligence-v3` | `03-signal-intelligence.png` | 4-column panoramic grid + Live Signal Feed table (merged from Signals.jsx) |

### ML & ANALYSIS (5 pages)

| # | Page | File | Route | Mockup | Notes |
|---|------|------|-------|--------|-------|
| 6 | ML Brain & Flywheel | `MLBrainFlywheel.jsx` | `/ml-brain` | `06-ml-brain-flywheel.png` | ML model management and flywheel visualization |
| 7 | Screener & Patterns | `Patterns.jsx` | `/patterns` | `07-screener-and-patterns.png` | Bloomberg-grade 3-column layout |
| 8 | Backtesting Lab | `Backtesting.jsx` | `/backtesting` | `08-backtesting-lab.png` | Strategy backtesting engine |
| 9 | Performance Analytics | `PerformanceAnalytics.jsx` | `/performance` | `11-performance-analytics-fullpage.png` | Portfolio performance analysis |
| 10 | Market Regime | `MarketRegime.jsx` | `/market-regime` | `10-market-regime-green.png`, `10-market-regime-red.png` | Regime detection with green/red states |

### EXECUTION (3 pages)

| # | Page | File | Route | Mockup | Notes |
|---|------|------|-------|--------|-------|
| 11 | Active Trades | `Trades.jsx` | `/trades` | `Active-Trades.png` | Active trade management |
| 12 | Risk Intelligence | `RiskIntelligence.jsx` | `/risk` | `13-risk-intelligence.png` | Risk monitoring and analysis |
| 13 | Trade Execution | `TradeExecution.jsx` | `/trade-execution` | `12-trade-execution.png` | Order execution + Alignment Preflight + Alignment Engine governance card |

### SYSTEM (1 page)

| # | Page | File | Route | Mockup | Notes |
|---|------|------|-------|--------|-------|
| 14 | Settings | `Settings.jsx` | `/settings` | `14-settings.png` | 11 tabs: Profile, API Keys, Trading, Risk, AI/ML, Agents, Data Sources, Notifications, Appearance, Audit Log, Alignment (embeds AlignmentEngine component) |

#### Settings Sub-Tabs (11 tabs — verified from code lines 641-653)
| # | Tab Key | Tab Label | Description | Mockup |
|---|---------|-----------|-------------|--------|
| 1 | `profile` | Profile | User profile, display name, email, timezone | Part of `14-settings.png` |
| 2 | `apiKeys` | API Keys | API key management (Alpaca, OpenClaw, data providers) | Part of `14-settings.png` |
| 3 | `trading` | Trading | Trading parameters, default order type, position sizing | Part of `14-settings.png` |
| 4 | `risk` | Risk | Risk management settings, max drawdown, position limits | Part of `14-settings.png` |
| 5 | `aiml` | AI / ML | AI/ML model configuration, inference settings | Part of `14-settings.png` |
| 6 | `agents` | Agents | Agent configuration, spawn defaults, team settings | Part of `14-settings.png` |
| 7 | `dataSources` | Data Sources | Data source connection settings, refresh intervals | Part of `14-settings.png` |
| 8 | `notifications` | Notifications | Alert preferences, channels (Discord, Slack, email) | Part of `14-settings.png` |
| 9 | `appearance` | Appearance | Theme, font size, density, accent color | Part of `14-settings.png` |
| 10 | `auditLog` | Audit Log | System audit trail, action history | Part of `14-settings.png` |
| 11 | `alignment` | Alignment | Constitutive alignment governance (embeds AlignmentEngine.jsx) | Part of `14-settings.png` |

### NON-SIDEBAR FILES (shared components, no dedicated routes)

| File | Purpose | Used By |
|------|---------|--------|
| `AlignmentEngine.jsx` | Constitutive alignment governance dashboard | Settings.jsx (Alignment tab), TradeExecution.jsx (governance card) |
| `Signals.jsx` | **DEPRECATED** - Merged into SignalIntelligenceV3.jsx | None (can be deleted) |

---

## Component Architecture

### agents/ (5 components)
- `AgentResourceMonitor.jsx` - Individual agent monitoring
- `ConferencePipeline.jsx` - Multi-agent conference coordination
- `DriftMonitor.jsx` - Agent behavior drift detection
- `SwarmTopology.jsx` - Swarm network visualization
- `SystemAlerts.jsx` - Agent system alert management

### charts/ (8 components)
- `DataSourceSparkLC.jsx` - Data source sparkline (LW Charts)
- `EquityCurveChart.jsx` - Equity curve visualization
- `MiniChart.jsx` - Compact inline charts
- `MonteCarloLC.jsx` - Monte Carlo simulation (LW Charts)
- `PatternFrequencyLC.jsx` - Pattern frequency (LW Charts)
- `RiskEquityLC.jsx` - Risk equity overlay (LW Charts)
- `RiskHistoryChart.jsx` - Risk history timeline
- `SentimentTimelineLC.jsx` - Sentiment timeline (LW Charts)

### dashboard/ (6 components)
- `ActivePositions.jsx` - Active position cards
- `LiveSignalFeed.jsx` - Real-time signal feed
- `MLStatusCard.jsx` - ML model status
- `MarketRegimeCard.jsx` - Regime indicator
- `PerformanceCard.jsx` - Performance metrics
- `QuickStats.jsx` - Quick statistics overview

### layout/ (3 components)
- `Header.jsx` - Top header bar
- `Layout.jsx` - Page layout wrapper
- `Sidebar.jsx` - 14-page navigation sidebar

### ui/ (12 components)
- `AlignmentPreflight.jsx` - Pre-trade alignment check widget
- `Badge.jsx`, `Button.jsx`, `Card.jsx`, `Checkbox.jsx`
- `DataTable.jsx`, `PageHeader.jsx`, `Select.jsx`
- `Slider.jsx`, `SymbolIcon.jsx`, `TextField.jsx`, `Toggle.jsx`

### Root components
- `ErrorBoundary.jsx` - Error boundary wrapper
- `RegimeBanner.jsx` - Market regime banner

---

## Services (4 files)
- `dataSourcesApi.js` - Data sources API client
- `openclawService.js` - OpenClaw trading service
- `tradeExecutionService.js` - Trade execution API
- `websocket.js` - WebSocket connection manager

## Hooks (4 files)
- `useApi.js` - Generic API hook with polling
- `useSentiment.js` - Sentiment data hook
- `useSettings.js` - Settings state management
- `useTradeExecution.js` - Trade execution logic

## Config (1 file)
- `api.js` - API base URL configuration

## Lib (3 entries)
- `types/` - TypeScript type definitions
- `dataSourceIcons.js` - Data source icon mapping
- `symbolIcons.js` - Ticker symbol icon mapping

---

## Design System
- Dark theme: `#0a0a0f` background, `#1a1a2e` cards
- Cyan accent: `#00d4ff` for primary actions
- Inter font family
- 24px padding, 12px border-radius
- V3 widescreen layout (no mobile)
- See `docs/UI-DESIGN-SYSTEM.md` for full spec