# Data Sources Manager — Mockup Fidelity Changes

**Page:** Data Sources Manager  
**Mockup:** `09-data-sources-manager.png`  
**File:** `frontend-v2/src/pages/DataSourcesMonitor.jsx`  
**Date:** March 2026

---

## File Changed

| File | Description |
|------|-------------|
| `frontend-v2/src/pages/DataSourcesMonitor.jsx` | Full mockup fidelity pass |

---

## Issues Fixed

### Header & Metrics

| Issue | Before | After |
|-------|--------|-------|
| Title alignment | Left-aligned with icon | Centered `DATA_SOURCES_MANAGER` |
| Metrics layout | Single row, wrong structure | Row 1: Connected, System Health, Ingestion (left); WS Connected, API Healthy, Refresh (right) |
| Metrics icons | Wrong or missing | Green checkmark (Connected), circular arrow (System Health), grey arrow (Ingestion) |
| OpenClaw / WS | Same row as main metrics | Separate row below: "OpenClaw Bridge: CONNECTED", "WS: CONNECTED" |

### AI-Powered Add Source

| Issue | Before | After |
|-------|--------|-------|
| Section title | "AI-POWERED ADD SOURCE" | "AI-POWERED ADD SOURCE INPUT" |
| Placeholder | "Search for data source to add..." | "Type a service name, URL, or paste API docs link..." |
| Input icon | None | Magnifying glass icon |
| Browse button | "Shop API store" | "Or browse..." |
| Drag-drop area | Missing | Cloud icon + "Drop API docs or config file" |
| Suggested pills | 5 services, wrong set | Polygon.io, Benzinga, Alpha Vantage, Quandl, IEX Cloud, CoinGecko |

### Filter Chips & Search

| Issue | Before | After |
|-------|--------|-------|
| Filter chips | [ALL], [Brokerage], [Alpha Vantage], [Quant], [RX Cloud], [ConfStack] | [ALL], [Screener], [Options], [Market], [Macro], [Filings], [Sentiment], [News], [Social], [Knowledge] |
| Search input | Missing | Search input with magnifying glass |

### Source List

| Issue | Before | After |
|-------|--------|-------|
| Section title | Missing | "SOURCE LIST" |
| SEC EDGAR type | Sentiment | Filings |
| Stockgrid | Stockgrid | Stockgeist |
| DEGRADED badge | Red | Amber/yellow |
| Row actions | None | [Show][Copy][Rotate] (Finviz); LIVE PING (Alpaca) |
| FRED dataSize | Empty | "Syncs 08:00 EST" |
| SEC EDGAR latency | 5.6K | 890ms |
| News API dataRate | 78K | 18K |

### Supplementary Section

| Issue | Before | After |
|-------|--------|-------|
| Section title | "Supply Chain Overview" | "SUPPLEMENTARY" |
| Layout | Checkboxes | Source rows (icon, name, type, status, latency, uptime) |
| Sources | Reddit, Benzinga, OpenClaw Bridge, TradingView, GitHub Gist | yFinance, Reddit, Benzinga, RSS, TradingView, OpenClaw Bridge, GitHub Gist |

### Credential Editor Panel

| Issue | Before | After |
|-------|--------|-------|
| Panel title | "Credential / Config Panel" | "CREDENTIAL EDITOR PANEL" |
| Alpaca display | "Alpaca" | "Alpaca Markets" + green checkmark |
| API Key buttons | Show, Copy, Rotate (redundant) | Copy, Rotate |
| API Secret | Show/Eye, no Rotate | Show eye, Rotate |
| Field label | "Trading Type" | "Account Type" |
| Bottom buttons | Connect, Reset to Default | Test Connection, Save Changes, Cancel, Reset to Default |
| Connection log | Missing | Connection Log section with sample entries |

### Footer

| Issue | Before | After |
|-------|--------|-------|
| Right side | "System telemetry: 10:33", "Idle: 4/11", dynamic time | "System telemetry: 1039 WSI: 93rb APII 0.00" |

### Code Cleanup

| Issue | Change |
|-------|--------|
| Unused imports | Removed `Database`, `StopCircle`, `ShoppingBag`, `ChevronDown` |
| New imports | Added `Cloud`, `ArrowRight` |
| Unused component | Removed `MetricPill` |
| Filter logic | Added `filteredSources` for chip + search filtering |
| Supplementary selection | Added `SUPPLY_CHAIN_SOURCES` with full row structure; selectable like main sources |

---

## Remaining Differences (Acceptable)

- **Source icons:** Text badges (FV, UW, AL) vs. custom icons (llama, chart) in mockup
- **Footer telemetry:** Placeholder "1039 WSI: 93rb APII 0.00" — real values from API when available
