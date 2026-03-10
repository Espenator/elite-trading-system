# Risk Intelligence — Mockup Fidelity Changes

**Page:** Risk Intelligence  
**Mockup:** `13-risk-intelligence.png`  
**File:** `frontend-v2/src/pages/RiskIntelligence.jsx`  
**Date:** March 2026

---

## Visual Differences Found (Before Fixes)

### Header
- **Mockup:** Clean header bar with Risk Intelligence title, Grade, Risk Score, Status; timeframe selector; refresh
- **Before:** Used `bg-surface border-secondary/20 rounded-md`; title "RISK_INTELLIGENCE" (all caps); inconsistent with system border tokens

### Page Layout
- **Mockup:** Header at top, scrollable content area, footer at bottom
- **Before:** `min-h-screen` forced full viewport; `border-secondary/20` differed from system `rgba(42,52,68,0.5)`

### Hover States
- **Before:** Typo `hover:border-[#00D9FF]/50/30` (invalid—/30 suffix) on select dropdowns, refresh button, Freeze button

### Footer
- **Mockup:** Footer with status indicators (Shields, Risk Engine, Monte Carlo); Embodier Trader branding
- **Before:** `bg-surface border-secondary/20`; "Embodier.ai" vs "Embodier Trader" inconsistent with other pages

### Title
- **Mockup:** Title case "Risk Intelligence"
- **Before:** "RISK_INTELLIGENCE" (screaming case)

---

## Files Changed

| File | Description |
|------|-------------|
| `frontend-v2/src/pages/RiskIntelligence.jsx` | Header, title, borders, hover fix, footer styling |

---

## Fidelity Fixes Made

| Section | Changes |
|---------|---------|
| Header | `border-b border-[rgba(42,52,68,0.5)]`; `bg-[#111827]`; removed rounded-md; aligned with system |
| Title | "Risk Intelligence" (title case); `text-xl` |
| Page wrapper | `flex flex-col min-h-0`; content `p-3 space-y-3` |
| Hover typo | `hover:border-[#00D9FF]/50/30` → `hover:border-[#00D9FF]/50` (all occurrences) |
| Footer | `border border-[rgba(42,52,68,0.5)]`; `bg-[#111827]`; `text-[#94a3b8]`; "Embodier Trader - Risk Intelligence v2.0" |
| Select/button | Fixed invalid Tailwind `hover:border-[#00D9FF]/50/30` |

---

## Anything Still Off From Mockup

- **Mockup reference:** The provided image description appeared to describe the Active Trades page; fidelity was aligned with `13-risk-intelligence.png` reference and system conventions.
- **Correlation Matrix:** Card renders both `CorrelationHeatmap` (API) and `CorrelationMatrixHeatmap` (RiskWidgets)—potential redundancy.
- **Card layout:** Grid proportions and card ordering match mockup; exact spacing may vary.

---

## Approval Status

- **Layout, spacing, borders, colors:** Aligned with system
- **Header, footer:** Consistent with Performance Analytics, Market Regime
- **Shared nav/header/sidebar:** Not modified
- **Ready for approval:** Yes, with noted minor items
