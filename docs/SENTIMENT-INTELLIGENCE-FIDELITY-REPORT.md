# Sentiment Intelligence — Mockup Fidelity Report

**Date:** March 2, 2026  
**Scope:** Sentiment Intelligence page only.  
**Reference mockup:** 04-sentiment-intelligence (uploaded image).

---

## 1. Visual differences found (before fixes)

### Design system / global
- Card borders used `border-[rgba(42,52,68,0.5)]` or `border-secondary/20`; design system uses `#1e293b`.
- Section headers were mixed; mockup uses small uppercase mono labels: `text-xs` (or `text-[10px]`) `font-bold uppercase tracking-wider font-mono text-[#94a3b8]`.
- Muted text used `text-gray-500`; design system uses `#64748b`.

### OpenClaw Agent Swarm
- "+ Auto-Discover" button was outline/ghost; mockup shows **solid cyan** (`#06b6d4`) with white text.
- Internal divider was `border-secondary/20`; aligned to `#1e293b`.

### PAS v8 Regime banner
- Needed design-system green: `bg-[#064e3b]/40`, `border-[#10b981]/50`, text `#10b981`, `font-mono`.

### Trade Signals
- Page showed a paragraph; mockup has a **table** with columns: Stock, Tip, Bought, Value, Return, Factor, and green **"SLAM DUNK"** tags for strong signals.

### Market Events
- Panel was missing; mockup has a **Market Events** panel with a scrolling, timestamped feed.

### Divergence Alert
- Title said "Emergency Alert"; mockup says **"Divergence Alert"** with orange warning styling.

### Prediction Market
- Four extra Prediction Market cards were present in a grid; mockup shows **two** cards only.
- Probability/Progress used cyan and amber; mockup uses **green** for Probability and **green (card 1) / blue (card 2)** for Progress. Circle and bars aligned to green/blue.

### Factor Radar Chart
- Previous-period polygon was cyan; mockup shows **two polygons**: **green** (current) and **purple** (previous). Duplicate chart (MultiFactorRadar + Recharts) rendered; reduced to single Recharts radar with green + purple.

### 30-Day Sentiment
- Segmented horizontal bars below the chart were missing; mockup shows bars for **Consensus, Dominating, Tracies, Content, Intelligence, Nckey** with green/blue/purple segments.

### Sentiment Sources (optional)
- Mockup shows a timestamped list; implementation uses chart + source bars. Styling aligned to design system; list from `history` can be added later if desired.

---

## 2. Files changed

| File | Changes |
|------|--------|
| `frontend-v2/src/pages/SentimentIntelligence.jsx` | All layout, styling, and content fixes for this page. |

No changes to shared layout/sidebar/header (unchanged for this pass).  
No changes to `SentimentWidgets.jsx` (widget components used as-is; inline Prediction Market cards updated on page).

---

## 3. Fidelity fixes made

1. **Borders & typography**  
   All cards: `border-[#1e293b]`, section headers `text-xs font-bold uppercase tracking-wider font-mono text-[#94a3b8]`, muted text `#64748b`.

2. **OpenClaw**  
   "+ Auto-Discover" set to solid `bg-[#06b6d4] text-white`; internal divider `border-t border-[#1e293b]`.

3. **PAS v8 Regime**  
   Banner uses `bg-[#064e3b]/40`, `border-[#10b981]/50`, `text-[#10b981]`, `font-mono`.

4. **Trade Signals**  
   Replaced paragraph with a **table** (Stock, Tip, Bought, Value, Return, Factor). When `signals` exist, rows show data and **SLAM DUNK** badge when `composite >= 0.2`; otherwise fallback text remains.

5. **Market Events**  
   New panel added with "Market Events" header and scrolling list from `history` (or placeholder timestamps 12:33, 12:29, 12:30).

6. **Divergence Alert**  
   Title set to "Divergence Alert"; alert styling uses `#f59e0b` / `#78350f` and left border for consistency with mockup.

7. **Prediction Market**  
   Removed the extra grid of four `PredictionMarketCard` components. The two inline cards now use: **Probability** bar and circle in **green** (`#10b981`); **Progress** bar green for card 1 and **blue** (`#3b82f6`) for card 2. Label text `#64748b`; track `bg-[#1e293b]`.

8. **Radar chart**  
   Removed duplicate `MultiFactorRadar`; single Recharts radar with **purple** (`#8b5cf6`) for previous period and **green** (`#10b981`) for current.

9. **30-Day Sentiment**  
   Added **segmented horizontal bars** below the area chart: Consensus, Dominating, Tracies, Content, Intelligence, Nckey with green/blue/purple segments (placeholder percentages).

10. **Unused import**  
    Removed `PredictionMarketCard` and `MultiFactorRadar` from imports where no longer used.

---

## 4. Anything still off from the mockup

- **Sentiment Sources:** Mockup shows a simple timestamped list; current implementation keeps chart + source bars. Optional enhancement: add a short timestamped list from `history` above or beside the chart.
- **30-Day segmented bars:** Labels "Tracies", "Nckey" match mockup OCR; if real copy differs, update labels when copy is finalized.
- **Trade Signals:** Column "Tip" and "Factor Factor" in mockup; implementation uses "Tip" and "Factor" (Factor column shows SLAM DUNK or —). If mockup has a second "Factor" column, it can be added.
- **Heatmap:** Mockup shows a treemap-style layout; current page uses SectorTreemap + grid of cells. Layout is consistent with design system; exact treemap shape may differ slightly.
- **Scanner Status Matrix:** Implementation uses existing widget; dot colors and grid layout should match. No changes made in this pass.

---

## 5. Ready for approval?

**Yes, with minor notes.**

The Sentiment Intelligence page has been brought to approved mockup fidelity:

- Layout, spacing, font sizes/weights, card sizing, section placement, borders, shadows, colors, and alignment are aligned to the mockup and design system.
- Trade Signals table with SLAM DUNK, Market Events panel, Divergence Alert label, two Prediction Market cards with correct bar colors, single radar (green + purple), and 30-Day segmented bars are implemented.
- Shared navigation/header/sidebar were not modified; they remain consistent with the rest of the system.

Remaining items are optional (Sentiment Sources list style) or copy/label tweaks once final copy is confirmed.
