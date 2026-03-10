# Active Trades — Mockup Fidelity Changes

**Page:** Active Trades  
**Mockup:** `Active-Trades.png`  
**File:** `frontend-v2/src/pages/Trades.jsx`  
**Date:** March 2026

---

## Visual Differences Found (Before Fixes)

### Top Header Bar
- **Mockup:** NAV $1,250,450.23 (+1.5%), DAILY P&L +$18,750.10, MARGIN AVAIL 85%, BUYING POWER $4,500,000, REGIME BULL TREND (green rectangular badge, white text), WS_LATENCY 35ms
- **Before:** REGIME badge used translucent bg (bg-emerald-400/20); regime+trend displayed

### Positions Table
- **Mockup:** Title "Positions" in white; Side LONG in green, SHRT in red; Actions: Close, Hedge, More ▼; sparkline in each row; headers white, bold
- **Before:** LONG in white; More as icon only; section title slate-300; headers slate-500; empty sparkline when no API data

### Orders Table
- **Mockup:** Title "Orders" in white; Side LONG/SHRT; Actions order: Cancel, Modify ▼, View Logs; status badges FILLED (green), PARTIAL (orange), WORKING (light blue), CANCELLED (grey), REJECTED (red)
- **Before:** Actions order View Logs, Cancel, Modify; Side SHORT vs SHRT; Modify without ▼

### Footer
- **Mockup:** "3 Agents OK" with green circle
- **Before:** Matched

---

## Files Changed

| File | Description |
|------|-------------|
| `frontend-v2/src/pages/Trades.jsx` | Fidelity pass |
| `docs/ACTIVE-TRADES-FIDELITY-CHANGES.md` | Fidelity documentation |

---

## Fidelity Fixes Made

| Section | Changes |
|---------|---------|
| REGIME badge | Solid bg (bg-emerald-500/red-500/amber-500) with white text |
| Positions Side | LONG → text-emerald-400, SHRT → text-red-400 |
| Orders Side | LONG → text-emerald-400, SHRT → text-red-400 (was SHORT) |
| Positions Actions | "More ▼" with ChevronDown instead of MoreHorizontal icon |
| Orders Actions | Order: Cancel, Modify ▼, View Logs (mockup order) |
| Table headers | text-white, font-bold (was slate-500) |
| Section titles | Positions / Orders → text-white (was slate-300) |
| Sparkline | Fallback data when API provides none |

---

## Anything Still Off From Mockup

- **Filter icon:** Mockup describes "three horizontal lines with circles"; SlidersHorizontal may differ slightly.
- **Legs expandable:** Mockup shows Bracket Order with expand arrow; current renders legs inline.
- **Profit Target / Stop Loss format:** Mockup shows "+$15.90 (+1.3%)" / "-$11.95 (-1.5%)" in leg details; current shows limit/stop prices only.

---

## Approval Status

- **Layout, spacing, font sizes, card sizing, section placement:** Aligned with mockup
- **Borders, shadows, colors, icons, alignment:** Aligned with mockup
- **Shared nav/header/sidebar:** Not modified
- **Ready for approval:** Yes, with noted minor differences
