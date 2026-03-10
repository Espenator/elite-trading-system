# Home / Landing Page (Dashboard) — Menu & Fidelity Restore Report

**Date:** March 2, 2026  
**Scope:** Home/landing page only (Intelligence Dashboard at `/dashboard`).  
**Reference:** `docs/mockups-v3/FULL-MOCKUP-SPEC.md`, `frontend-v2/src/V3-ARCHITECTURE.md`, `docs/mockups-v3/images/02-intelligence-dashboard.png`, `docs/UI-DESIGN-SYSTEM.md`.

---

## 1. What Was Wrong With the Menu

### Main app sidebar (Layout Sidebar)
- **Incorrect comment:** Sidebar.jsx stated "16 sidebar pages" instead of the authoritative **14 sidebar pages** (V3-ARCHITECTURE).
- **No structural errors:** The main sidebar already matched the intended product structure (COMMAND → INTELLIGENCE → ML & ANALYSIS → EXECUTION → SYSTEM) with correct labels and routes. No random or invented menu items were present.

### Dashboard page internal mini sidebar (6-icon nav)
- **Wrong routes:** The 6-icon mini sidebar (Dash, Signals, Port, Risk, Agents, ML) used incorrect paths:
  - **Dash** used `path: "/"` instead of `path: "/dashboard"` (dashboard route is `/dashboard`).
  - **Signals** used `path: "/signals"` which does not exist; the correct route is `/signal-intelligence-v3`.
- **Full-page reloads:** Mini-nav used `<button>` + `window.location.href`, causing full page reloads instead of SPA navigation.
- **Hardcoded active state:** The first item used `active: true` instead of deriving active state from the current route.

---

## 2. What Was Restored

### Main app sidebar
- Comment updated to **"14 sidebar pages"** to match V3-ARCHITECTURE.md.
- Confirmed all 14 items and 5 sections match the spec: labels, order, and routes unchanged (already correct).

### Dashboard mini sidebar
- **Dash** now links to `/dashboard`.
- **Signals** now links to `/signal-intelligence-v3`.
- **Port, Risk, Agents, ML** already pointed to `/trades`, `/risk`, `/agents`, `/ml-brain` — left as-is.
- Replaced `<button>` + `window.location.href` with **`<NavLink>`** from `react-router-dom` for SPA navigation and correct active state (cyan highlight when on that route).

### Dashboard page fidelity (design system)
- **Right column:** Section background set to `#0B0E14` (--bg-primary) with `p-2 gap-2` so cards sit on page background.
- **Cards:** SWARM CONSENSUS, Signal Strength Bar Chart, and Regime/Top Trades row use **rounded-md** (6px) and **border** per UI-DESIGN-SYSTEM card spec.
- **Card headers:** Existing `text-xs font-bold uppercase tracking-wider text-slate-400 font-mono` retained (matches design system).

---

## 3. Files Changed

| File | Changes |
|------|--------|
| `frontend-v2/src/pages/Dashboard.jsx` | Added `NavLink` import; replaced mini sidebar buttons with `NavLink`; fixed paths (`/dashboard`, `/signal-intelligence-v3`); applied card styling (rounded-md, border, bg) to right-panel sections; right column container given `p-2 gap-2` and `bg-[#0B0E14]`. |
| `frontend-v2/src/components/layout/Sidebar.jsx` | Comment only: "16 sidebar pages" → "14 sidebar pages". |

**Not changed:** `App.jsx` (routes already correct); no new or removed routes.

---

## 4. Remaining Differences From the Mockup

- **Mini sidebar:** Mockup shows 6 icons (Dash, Signals, Port, Risk, Agents, ML). Implemented and routes fixed. Icon set is Unicode symbols; mockup may use different icons — acceptable per design system.
- **Score bar widths in signals table:** MOCKUP-FIDELITY-AUDIT notes "Score bar widths in table may not match mockup proportions" — minor; no change in this pass.
- **Ticker strip animation:** Scroll speed may differ from mockup; tune via CSS if needed.
- **Cognitive Dashboard link:** "View Full →" in the Cognitive Intelligence card still links to `/cognitive-dashboard` (page has no mockup and is not in the 14-page sidebar). Left as-is; can be removed or redirected in a follow-up.
- **Footer bar:** Global status footer (WebSocket, API, agents, etc.) is provided by Layout/StatusFooter; Dashboard does not duplicate it. Matches intent.

---

## 5. Screenshot-Ready Status

**Status: Yes — screenshot-ready for the home/landing page.**

- **Menu/navigation:** Main sidebar shows the correct 14-page structure and labels. Dashboard mini sidebar shows 6 items with correct routes and active state.
- **Layout:** Dashboard uses the approved structure: top header (EMBODIER TRADER, regime, KPIs), ticker strip, left mini sidebar, center signals table, right intelligence panel with cards.
- **Design system:** Right-panel cards use 6px radius, borders, and consistent spacing; typography and hierarchy align with UI-DESIGN-SYSTEM.md.
- **No redesign:** Only fixes to match the intended page and design system; no new patterns or layout changes.

To capture: open `/dashboard`, ensure backend is up so data loads, then screenshot the full page (including main sidebar and status footer).
