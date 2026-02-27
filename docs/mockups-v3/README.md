# Embodier Trader - V3 UI Mockups

> **Last Updated: February 27, 2026 (3:00 PM EST)**
>
> **Status: 6 approved mockup images committed. 11 pages still need mockups.**
>
> Code files are ALL committed in `frontend-v2/src/pages/`.
> See `frontend-v2/src/V3-ARCHITECTURE.md` for the authoritative page list.

---

## Current 15 Pages vs Mockup Status

The codebase has evolved since initial mockup generation. Below maps the current code routes to mockup availability.

| # | Current Page | File | Route | Mockup Status |
|---|-------------|------|-------|---------------|
| 1 | Dashboard | `Dashboard.jsx` | `/` | Needs mockup |
| 2 | Portfolio Manager | `Portfolio.jsx` | `/portfolio` | Needs mockup |
| 3 | Market Scanner | `Scanner.jsx` | `/scanner` | Needs mockup |
| 4 | Order Management | `Orders.jsx` | `/orders` | Needs mockup |
| 5 | Risk Management | `Risk.jsx` | `/risk` | Needs mockup |
| 6 | Agent Command Center | `AgentCommandCenter.jsx` | `/agents` | HAS MOCKUP (approved) |
| 7 | Trading Journal | `Journal.jsx` | `/journal` | Needs mockup |
| 8 | Backtesting Engine | `Backtesting.jsx` | `/backtesting` | Needs mockup |
| 9 | Settings | `Settings.jsx` | `/settings` | HAS MOCKUP (approved) |
| 10 | Alerts & Notifications | `Alerts.jsx` | `/alerts` | Needs mockup |
| 11 | Research & Analysis | `Research.jsx` | `/research` | Needs mockup |
| 12 | ML Model Hub | `MLModels.jsx` | `/ml-models` | Needs mockup |
| 13 | News & Sentiment | `News.jsx` | `/news` | Needs mockup |
| 14 | Social & Community | `Social.jsx` | `/social` | Needs mockup |
| 15 | Debug Panel (hidden) | `Debug.jsx` | `/debug` | No mockup needed |

**Total: 6 approved mockup images in `images/` folder, 11 pages still need mockups.**

---

## Approved Mockup Images (in `images/`)

These 6 mockups are the source of truth for visual design:

1. **Agent Command Center** - Full 8-tab layout with swarm visualization
2. **Settings** - Configuration panels
3. **Patterns & Screener** - Bloomberg-grade 3-column layout (committed as PNG)
4. **Sentiment Intelligence** - Multi-panel sentiment analysis view
5. **Data Sources Monitor** - Data pipeline monitoring
6. Additional approved mockup

> **Note:** Some mockups were generated under older page names (Signal Intelligence, Sentiment Intelligence, Data Sources Monitor, etc.). These pages have been renamed/reorganized in the current codebase. The visual designs remain valid references for the current pages.

---

## Legacy Page Name Mapping

Some mockups reference older page names. Here is the mapping:

| Old Mockup Name | Current Code Page | Current Route |
|----------------|-------------------|---------------|
| Intelligence Dashboard | Dashboard | `/` |
| Signal Intelligence | Market Scanner | `/scanner` |
| Sentiment Intelligence | News & Sentiment | `/news` |
| Data Sources Monitor | Research & Analysis | `/research` |
| ML Brain & Flywheel | ML Model Hub | `/ml-models` |
| Screener & Patterns | Market Scanner | `/scanner` |
| Backtesting Lab | Backtesting Engine | `/backtesting` |
| Performance Analytics | Portfolio Manager | `/portfolio` |
| Market Regime | Dashboard (regime panel) | `/` |
| Active Trades | Order Management | `/orders` |
| Risk Intelligence | Risk Management | `/risk` |
| Trade Execution | Order Management | `/orders` |

---

## Mockup Generation Process

Mockups are generated using Perplexity MAX model council (3 versions each):
1. User submits page specification
2. 3 AI models generate competing mockup versions
3. Best version selected and approved
4. Approved mockup committed to `images/` as PNG
5. Code aligned to match approved mockup design

---

## Design Reference

See `docs/UI-DESIGN-SYSTEM.md` for the authoritative design system:
- Dark theme (#0a0a0f background, #1a1a2e cards)
- Cyan accent (#00d4ff) for primary actions
- Inter font family
- 24px padding, 12px border-radius
- V3 widescreen layout (no mobile)

---

## Full Specification

See `FULL-MOCKUP-SPEC.md` in this directory for complete mockup specifications for all 14 sidebar pages.
