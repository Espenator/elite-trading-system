# Active Trades — Mockup Fidelity Changes

**Page:** Active Trades  
**Mockup:** `Active-Trades.png`  
**File:** `frontend-v2/src/pages/Trades.jsx`  
**Date:** March 2026

---

## Visual Differences Found (Before Fixes)

### Top Header Bar
- **Mockup:** NAV, DAILY P&L, MARGIN AVAIL, BUYING POWER, REGIME (BULL TREND with light green bg), WS_LATENCY
- **Before:** REGIME and TREND combined with underscore; REBALANCED dropdown; different REGIME styling

### Positions Table
- **Mockup:** Filter/settings icon (SlidersHorizontal); columns Symbol, Side (LONG/SHRT), Qty, Avg Price, Mkt Price, Day P&L ($), Day P&L (%), Unrealized P&L ($), Unrealized P&L (%), Realized P&L ($), Cost Basis, Mkt Value, Delta, Gamma, Theta, Vega, IV, Daily Range, Vol, Sparkline, Actions (Close, Hedge, More)
- **Before:** Side as LONG/SHORT with pill; different column order; Realized P&L (%); Actions as X/Edit/Settings; duplicate Qty; Beta; Daily Range Vol

### Orders Table
- **Mockup:** Order ID, Time, Symbol, Type, Side, Qty, Filled Qty, Limit Price, Stop Price, Status (FILLED green, PARTIAL orange, WORKING blue, CANCELLED grey, REJECTED red), Execution Time, Avg Fill Price, Legs (Parent/Child), Actions (View Logs, Cancel, Modify)
- **Before:** Date + Time separate; P/L(Day Qty) instead of Qty/Filled Qty; no Side column; Actions Cancel/Close; Status labels different

### Footer
- **Mockup:** "3 Agents OK" with green dot; Positions/Orders counts
- **Before:** Similar; agent count from systemData

---

## Files Changed

| File | Description |
|------|-------------|
| `frontend-v2/src/pages/Trades.jsx` | Full mockup fidelity pass |

---

## Fidelity Fixes Made

| Section | Changes |
|---------|---------|
| Header | REGIME badge as "BULL TREND" with light green bg; removed REBALANCED dropdown; Refresh button next to WS_LATENCY |
| Positions | Added SlidersHorizontal filter icon; column order Day P&L ($) then (%); Unrealized P&L ($) and (%); Realized P&L ($); Mkt Value; Gamma, Vega, IV; Daily Range, Vol; Side LONG/SHRT (SHRT in red); Actions Close, Hedge, More |
| Orders | Removed Date column; added Side (LONG/SHORT); Qty + Filled Qty columns; Legs (Parent/Child); Status FILLED/PARTIAL/WORKING/CANCELLED/REJECTED with correct colors; Actions View Logs, Cancel, Modify |
| StatusBadge | FILLED green, PARTIAL orange, WORKING light blue, CANCELLED grey, REJECTED red |
| Fallbacks | NAV, dayPnl, buyingPower, marginPct when API empty |

---

## Anything Still Off From Mockup

- **View Logs / Modify:** May need functional wiring.
- **Hedge button:** Placeholder; no action wired.
- **Filter icon:** Opens no panel; filter input remains.
- **Legs expand:** Mockup shows expandable bracket legs; current renders inline.

---

## Approval Status

- **Layout, spacing, font sizes, card sizing, section placement:** Aligned with mockup
- **Borders, shadows, colors, icons, alignment:** Aligned with mockup
- **Shared nav/header/sidebar:** Not modified (consistent with system)
- **Ready for approval:** Yes, with noted minor differences
