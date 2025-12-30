# Trade Service Documentation

## Overview

The Trade Service (`trade.service.js`) provides functionality to fetch and transform stock data from the Finviz API into live trading signals for the Dashboard.

## Features

- **Fetch Stock List**: Gets filtered stock data from Finviz screener API
- **Fetch Quote Data**: Gets historical price data for specific tickers
- **Transform to Signals**: Converts raw stock data into trading signals with:
  - Entry, target, and stop prices
  - Risk/reward ratios
  - Confidence scores
  - Trading tiers (A-, B+, B, C+, C, D)
  - Buy/Sell recommendations

## API Endpoints Used

### Stock List
```
GET /api/v1/stocks/list
```

### Quote Data
```
GET /api/v1/quotes/{ticker}?p={timeframe}&r={duration}
```

## Signal Generation Logic

### Score Calculation
- Base score: 50
- Volume bonus: +10 (if > 1M), +10 (if > 5M)
- Price change bonus: +15 (if > 2%), +10 (if > 5%)
- P/E bonus: +10 (if 0 < P/E < 30)
- Score range: 0-100

### Tier Assignment
- **A-**: Score ≥ 90
- **B+**: Score ≥ 85
- **B**: Score ≥ 80
- **C+**: Score ≥ 75
- **C**: Score ≥ 70
- **D**: Score < 70

### Price Calculations
- **Entry**: Current stock price
- **Target**: Price × (1 ± volatility × 2) based on direction
- **Stop**: Price × (1 ∓ volatility × 1.5) based on direction
- **Risk/Reward**: (Target - Entry) / (Entry - Stop)

### Action Determination
- **BUY**: Positive price change
- **SELL**: Negative price change

## Usage in Dashboard

The Dashboard component uses the trade service to:
1. Fetch live signals every 30 seconds
2. Display signals in a table
3. Show loading state during updates
4. Display last update timestamp

### Example Usage

```javascript
import tradeService from '../services/trade.service';

// Fetch live signals
const signals = await tradeService.getLiveSignals();

// Or fetch with custom filters
const signals = await tradeService.getLiveSignals('cap_midover,sh_avgvol_o500');
```

## Configuration

The API base URL can be configured via environment variable:
```env
VITE_API_BASE_URL=http://localhost:8001/api/v1
```

Default: `http://localhost:8001/api/v1`

## Error Handling

- Returns empty array on error to prevent UI breakage
- Logs errors to console for debugging
- Maintains previous signals if fetch fails

