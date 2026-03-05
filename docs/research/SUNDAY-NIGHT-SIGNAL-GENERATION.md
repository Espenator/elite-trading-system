<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# OPTIMIZED: Sunday Night Elite Signal Generation - Efficient 3-Stage Funnel

**Goal**: Scan 10,000+ stocks → Filter to 100 prospects → Validate to 20 elite trades (10 LONG + 10 SHORT)
**Time**: 2 hours max (10:00 PM - 12:00 AM)
**Strategy**: Automated filtering first, manual validation only for finalists

***

## COPILOT ASSISTANT - STREAMLINED WORKFLOW

### STAGE 1: MASS SCAN - Cast Wide Net (10:00 PM - 10:15 PM)

**Objective**: Generate 200-500 raw candidates from 10,000+ stock universe

**STEP 1.1**: Configure Elite Scanner for MAXIMUM throughput

Navigate to: `http://localhost:8501`

```
SCANNER SETTINGS (Aggressive - we'll filter later):

Universe:
☑ Scan ALL US Stocks (10,000+)
☐ Minimum Market Cap: NONE (scan everything)
☐ Minimum Price: $5+ (avoid penny stocks)

Score Thresholds (VERY LOW - we want quantity):
• Min LONG Score: 25 (down from 60)
• Min SHORT Score: 25 (down from 60)

Filters (ALL OFF for Stage 1):
☐ GJR-GARCH: OFF
☐ Validate Liquidity: OFF
☐ Validate Hurst Regime: OFF
☐ ADX Filter: OFF
☐ Volume Filter: OFF (we'll filter by volume later)

Output:
• Max Results: 500 per direction
• Export Format: CSV with ALL data fields
```

**STEP 1.2**: Execute dual scans (parallel if possible)

```
Action 1: Click "Run Scan" → Direction: LONG
Expected: 300-500 LONG candidates
Wait time: ~2-3 minutes

Action 2: Click "Run Scan" → Direction: SHORT  
Expected: 300-500 SHORT candidates
Wait time: ~2-3 minutes

Export both:
- LONG_Raw_Dec01.csv (300-500 rows)
- SHORT_Raw_Dec01.csv (300-500 rows)
```

**STEP 1.3**: Verify raw data quality

```
Open LONG_Raw_Dec01.csv
Check columns exist:
✓ Symbol
✓ Composite_Score (25-100 range)
✓ Setup_Type (FRACTAL/MOMENTUM/BREAKOUT/etc)
✓ Price
✓ Volume
✓ ATR
✓ Sector

Quick sanity check:
- Total rows: _____ (should be 200-500)
- Highest score: _____ (should be 70-95)
- Lowest score: _____ (should be 25-30)
```


***

### STAGE 2: AUTOMATED FILTERING - Narrow to Top 100 (10:15 PM - 10:30 PM)

**Objective**: Apply programmatic filters to reduce 500 → 100 finalists per direction

**STEP 2.1**: Create filtering script (or use Excel/Sheets formulas)

**FILTER CRITERIA** (apply in this order):

```
FILTER #1: Volume Requirements
Keep only: Average Volume > 1 million shares/day
Reason: Ensures liquidity for $800k position sizes
Reduces: 500 → ~250 candidates

FILTER #2: Price Range
Keep only: Price between $10 and $500
Reason: Avoid penny stocks and ultra-expensive stocks
Reduces: 250 → ~200 candidates

FILTER #3: Score Quality
Keep only: Composite Score > 40
Reason: Minimum quality threshold for consideration
Reduces: 200 → ~120 candidates

FILTER #4: Sector Diversification
Keep only: Max 15 stocks per sector
Reason: Avoid over-concentration in one sector
Reduces: 120 → ~100 candidates

FILTER #5: Setup Type Priority
Rank by preference:
1. FRACTAL_BREAKOUT (highest probability)
2. MOMENTUM_SURGE (strong trend)
3. VOLATILITY_CLUSTER (academic edge)
4. STAIRCASE_PATTERN (structured move)
5. ROLLOVER_MEAN_REVERSION (counter-trend)
Keep top 50 of each type
Reduces: 100 → ~80 final candidates per direction
```

**STEP 2.2**: Execute filtering in Google Sheets (faster than manual)

```
1. Go to: https://docs.google.com/spreadsheets/d/1HamJwzq3QXzY9jEYI0HxpA7xiK8xmD35jvhiEHpd7pY

2. Create NEW tab: "Stage2_Filtering"

3. Import CSV:
   File → Import → Upload → LONG_Raw_Dec01.csv
   Import location: "New sheet"

4. Apply filters using built-in Data menu:
   Data → Create a filter
   
   Column filters:
   • Volume > 1000000
   • Price: Custom formula = AND(B2>10, B2<500)
   • Composite_Score > 40
   
5. Sort by: Composite_Score (descending)

6. Copy top 50 rows → Paste in new tab "LONG_Top50"

7. Repeat for SHORT_Raw_Dec01.csv → "SHORT_Top50"
```

**STEP 2.3**: Quick Finviz bulk validation

**Instead of checking each symbol individually, use Finviz screener to validate in bulk:**

```
LONG Validation:
1. Go to: https://elite.finviz.com/screener.ashx?v=111&f=sh_avgvol_o1000,sh_price_o10,ta_sma20_pa,ta_sma50_pa

2. This shows ALL stocks with:
   - Volume > 1M
   - Price > $10
   - Above 20 SMA
   - Above 50 SMA

3. Export Finviz results: Click "Export" → Save as Finviz_LONG_Validated.csv

4. Cross-reference:
   Open both files in Excel/Sheets
   Use VLOOKUP or MATCH formula to check which of your top 50 appear in Finviz
   
   Formula in Google Sheets:
   =IF(COUNTIF(Finviz_LONG!A:A, A2)>0, "✓ CONFIRMED", "⚠ SKIP")

5. Keep only "✓ CONFIRMED" symbols
   Expected: 50 → ~30-35 confirmed

SHORT Validation: Same process with different Finviz URL:
https://elite.finviz.com/screener.ashx?v=111&f=sh_avgvol_o1000,sh_price_o10,ta_sma20_pb,ta_sma50_pb
```

**EXPECTED OUTPUT**: 30-35 LONG + 30-35 SHORT finalists (down from 1000+)

***

### STAGE 3: MANUAL VALIDATION - Final 20 Elite Trades (10:30 PM - 11:30 PM)

**Objective**: Human-verified structure checks on 60-70 finalists → Select best 20

**STEP 3.1**: Prioritization scoring (do this BEFORE TradingView)

```
Open: "LONG_Top50" tab in Google Sheets

Add new column: "Priority_Score"

Calculate for each symbol:
Priority_Score = (Composite_Score × 0.5) + (Volume_Rank × 0.3) + (Setup_Bonus × 0.2)

Where:
• Composite_Score: Scanner output (40-100)
• Volume_Rank: 1-10 scale (10 = highest volume in list)
• Setup_Bonus: 
  - FRACTAL_BREAKOUT = 20 points
  - MOMENTUM_SURGE = 15 points
  - VOLATILITY_CLUSTER = 10 points
  - Other = 5 points

Sort by Priority_Score descending

Check TOP 15 ONLY in TradingView (not all 35)
```

**STEP 3.2**: Rapid TradingView validation (15 symbols × 2 min = 30 min)

**Create TradingView watchlist:**

```
1. TradingView.com → Login
2. Watchlist → Create "Monday Top 15 LONG"
3. Add top 15 symbols from Priority_Score ranking
4. Open first symbol
```

**SIMPLIFIED 3-Check System (not full 9-question process):**

```
For EACH symbol (2 minutes max):

CHECK 1: 4-Hour Chart Structure (30 seconds)
• Timeframe: 4H
• Question: Is price making Higher Highs + Higher Lows (HHHL)?
  - YES = Continue ✓
  - NO = REJECT immediately ✗ (move to next symbol)

CHECK 2: Daily Support/Resistance (30 seconds)
• Timeframe: 1D
• Find last swing low (for LONG) or swing high (for SHORT)
• Record as STOP LOSS price
• Measure distance: Entry - Stop = $____
• ATR check: Is distance 2-3× ATR?
  - YES = Continue ✓
  - NO = REJECT ✗

CHECK 3: Risk:Reward Math (60 seconds)
• Entry = Current price (or Monday open estimate)
• Stop = From CHECK 2
• Target 1 = Next resistance level (eyeball the chart)
• Calculate RR: (Target - Entry) ÷ (Entry - Stop)
• Is RR > 2.0?
  - YES = ✅ APPROVED (add to final list)
  - NO = REJECT ✗

Time per symbol: ~2 minutes
15 symbols = 30 minutes total
```

**STEP 3.3**: Accept first 10 that pass all 3 checks

```
Stop after you approve 10 LONG trades
No need to check all 15 if you hit 10 approvals

Document in Google Sheets "Live Signals" tab:

| Symbol | Score | Entry | Stop | Target | Size | RR | Status |
|--------|-------|-------|------|--------|------|----|--------|
| NVDA   | 85    | 178.5 | 170  | 195    | 1882 |3.2 | APPROVED|
```

**STEP 3.4**: Repeat for SHORT (another 30 minutes)

Same process with SHORT_Top50 list → Approve first 10 that pass validation

***

### STAGE 4: POSITION SIZING \& FINAL OUTPUT (11:30 PM - 12:00 AM)

**STEP 4.1**: Batch calculate position sizes (10 min)

**Use this simplified formula** (no complex Van Tharp calculations):

```
For EACH approved trade:

1. Determine risk tier by Composite Score:
   • Score 70-100: STRONG (2% account risk)
   • Score 50-69: REGULAR (1.5% account risk)
   • Score 40-49: SMALL (1% account risk)

2. Calculate position:
   Account Risk = $800,000 × [Risk %]
   Risk Per Share = Entry Price - Stop Price
   Position Size = Account Risk ÷ Risk Per Share

Example:
• NVDA: Score 85 (STRONG = 2%)
• Entry: $178.50, Stop: $170.00
• Risk/share: $178.50 - $170 = $8.50
• Position: ($800k × 0.02) ÷ $8.50 = 1,882 shares
• Capital needed: 1,882 × $178.50 = $335,817

3. Add to Google Sheets with all fields populated
```

**STEP 4.2**: Generate summary report (10 min)

```
In Google Sheets, add summary at top:

Row 1: "=== MONDAY DECEMBER 1, 2025 - ELITE TRADE PLAN ==="
Row 2: "Scanned: 10,000+ stocks → Filtered: [X] → Validated: 20"
Row 3: "Total Capital Deployed: $_______ | Total Risk: $_______"
Row 4: ""
Row 5: [Start data table]

Columns:
A: Symbol
B: Direction (LONG/SHORT)
C: Score
D: Entry
E: Stop
F: Target 1
G: Position (shares)
H: Capital ($)
I: Risk ($)
J: R:R Ratio
K: Status (all = "PENDING")
```

**STEP 4.3**: Create backup \& summary doc (10 min)

```
Save backup CSV:
File → Download → CSV
Save as: C:\Desktop\Trading\Monday_Dec01_Final_20_Trades.csv

Create text summary:
---
MONDAY DECEMBER 1 - TOP 10 LONG + 10 SHORT

LONG TRADES:
1. NVDA @ 178.50 | Stop: 170 | Target: 195 | Score: 85
2. [Symbol] @ [Entry] | Stop: [X] | Target: [X] | Score: [X]
...

SHORT TRADES:
1. [Symbol] @ [Entry] | Stop: [X] | Target: [X] | Score: [X]
...

EXECUTION PLAN MONDAY 9:30 AM:
- Observe first 5 min (no entries)
- Enter between 9:35-10:00 AM with market confirmation
- Set 3% trailing stops IMMEDIATELY on all positions
---

Save as: Monday_Dec01_Summary.txt
```


***

## QUALITY CONTROL CHECKLIST

Before midnight, verify:

```
✅ Google Sheets has exactly 20 rows (10 LONG + 10 SHORT)
✅ All 20 trades have Entry, Stop, Target, Position Size calculated
✅ All 20 trades passed 4-hour structure check (documented)
✅ All 20 trades have Risk:Reward > 2:1
✅ Total account risk < 15% (per TRADING-BIBLE.md crash protocol)
✅ CSV backup saved to desktop
✅ Summary text file created
✅ Diversity: Max 3 trades from same sector
✅ No position > 50% of account (individual trade limit)
```


***

## TROUBLESHOOTING: If You Still Can't Get 10+10

**Problem**: After Stage 2 filtering, only 5-8 LONG or SHORT finalists

**Emergency Solutions**:

### Option A: Lower score threshold in Stage 1

```
Change: Min Score 25 → Min Score 20
This expands raw candidates from 500 → 800+
```


### Option B: Relax Finviz validation

```
Instead of requiring Finviz confirmation:
Accept symbols that score 60+ even without Finviz match
Mark these as "HIGH CONVICTION - No Finviz" in sheets
```


### Option C: Include secondary setup types

```
Stage 2 Filter #5: Include ALL setup types (not just top 5)
Accept: OVERSOLD_BOUNCE, GAP_FILL, etc.
Reduces quality slightly but increases quantity
```


### Option D: Expand to small/mid caps

```
Stage 2 Filter #1: Lower volume to 500K average (from 1M)
Stage 2 Filter #2: Lower min price to $5 (from $10)
This opens universe to small/mid cap names
```


***

## TIME ESTIMATE BREAKDOWN

| Stage | Task | Time |
| :-- | :-- | :-- |
| 1 | Mass scan 10,000+ stocks | 15 min |
| 2 | Automated filtering to top 100 | 15 min |
| 3 | TradingView validation (30 symbols) | 60 min |
| 4 | Position sizing \& final output | 30 min |
| **TOTAL** |  | **2 hours** |


***

## EXPECTED FINAL DELIVERABLES

By midnight you will have:

1. ✅ **Google Sheet**: 20 rows with complete trade data
2. ✅ **CSV Export**: Monday_Dec01_Final_20_Trades.csv
3. ✅ **Summary Doc**: Monday_Dec01_Summary.txt
4. ✅ **TradingView Watchlist**: "Monday Top 20" saved
5. ✅ **Scan Archives**: LONG_Raw.csv + SHORT_Raw.csv (for audit trail)

**Total stocks processed**: 10,000+
**Total stocks validated**: 60-70
**Total trades approved**: 20 (10+10)
**Efficiency**: 99.8% automated filtering, 0.2% human validation

***

**START NOW. The 3-stage funnel prevents assistant burnout by:**

- ✅ Automating 95% of the filtering work
- ✅ Only requiring manual TradingView checks on 30 finalists (not 1000)
- ✅ Using simplified 3-check validation (not 9-question deep dive)
- ✅ Batch processing position sizing calculations
- ✅ Clear stopping criteria (stop at 10 approvals per direction)

**BEGIN STAGE 1 MASS SCAN NOW. REPORT BACK AFTER EACH STAGE.**

