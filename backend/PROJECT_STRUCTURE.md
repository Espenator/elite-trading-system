# Project Structure

## 📁 Directory Layout

```
backend/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── api/                      # API routes
│   │   ├── __init__.py
│   │   └── v1/                   # API version 1
│   │       ├── __init__.py
│   │       ├── stocks.py         # Stock screener endpoints
│   │       ├── quotes.py         # Quote/chart data endpoints
│   │       ├── orders.py         # Order execution endpoints
│   │       └── system.py         # System status (glass-box: trading mode + modules)
│   ├── core/                     # Core configuration
│   │   ├── __init__.py
│   │   └── config.py             # Settings and configuration (TRADING_MODE=paper|live)
│   ├── modules/                  # Modular components (see MODULAR_ARCHITECTURE.md at repo root)
│   │   ├── symbol_universe/      # Stock/symbol database and watchlists
│   │   ├── social_news_engine/   # Real-time social/news search and compute
│   │   ├── chart_patterns/       # Pattern library and detection pipeline
│   │   ├── ml_engine/            # ML and algorithms (signal fusion, learning)
│   │   └── execution_engine/    # Paper/live execution (Alpaca)
│   └── services/                 # Business logic services
│       ├── __init__.py
│       ├── alpaca_service.py     # Alpaca API (paper by default)
│       ├── database.py          # SQLite orders DB
│       └── finviz_service.py     # Finviz API integration
├── tools/                        # Testing and utility tools
│   ├── __init__.py
│   ├── test_api.py              # Backend API test tool
│   └── test_finviz_direct.py    # Direct Finviz API test
├── tests/                        # Unit tests (for future)
├── .env                          # Environment variables (create this)
├── .env.example                  # Example environment file
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── start_server.py                # Server startup script
├── start.bat                     # Windows startup script
├── README.md                     # Full documentation
├── QUICKSTART.md                 # Quick start guide
└── PROJECT_STRUCTURE.md          # This file
```

## 🔑 Key Files

### Configuration
- **`app/core/config.py`**: Loads settings from `.env` file
- **`.env`**: Your API keys and configuration (create from `.env.example`)

### API Endpoints
- **`app/api/v1/stocks.py`**: `/api/v1/stocks/list` - Get stock screener data
- **`app/api/v1/quotes.py`**: `/api/v1/quotes/{ticker}` - Get quote/chart data

### Services
- **`app/services/finviz_service.py`**: Handles all Finviz API calls

### Testing
- **`tools/test_api.py`**: Test the backend API endpoints
- **`tools/test_finviz_direct.py`**: Test Finviz API directly

## 🚀 API Endpoints

### 0. System Status (glass-box)
```
GET /api/v1/system/status
```
Returns `trading_mode` (paper | live) and status of each module (symbol_universe, social_news_engine, chart_patterns, ml_engine, execution_engine) for the UI.

### 1. Stock List
```
GET /api/v1/stocks/list
```

**Query Parameters:**
- `filters` (optional): Custom filter string
- `version` (optional): Screener version
- `filter_type` (optional): Filter type
- `columns` (optional): Specific columns to export

### 2. Quote Data
```
GET /api/v1/quotes/{ticker}
```

**Path Parameters:**
- `ticker`: Stock symbol (e.g., MSFT, AAPL)

**Query Parameters:**
- `p` (optional): Timeframe/unit - i1, i3, i5, i15, i30, h, d, w, m
- `r` (optional): Duration/range - d1, d5, m1, m3, m6, ytd, y1, y2, y5, max

## 🔧 Environment Variables

All configuration is in `.env`:

```env
FINVIZ_API_KEY=your_key_here
FINVIZ_SCREENER_FILTERS=cap_midover,sh_avgvol_o500,sh_price_o10
FINVIZ_SCREENER_VERSION=111
FINVIZ_SCREENER_FILTER_TYPE=4
FINVIZ_QUOTE_TIMEFRAME=d

# Alpaca — paper by default; set TRADING_MODE=live for real execution
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2
TRADING_MODE=paper
```

## 📝 Next Steps

1. Create `.env` file with your API key
2. Install dependencies: `pip install -r requirements.txt`
3. Start server: `python start_server.py`
4. Test API: `python tools/test_api.py`
5. Visit docs: http://localhost:8000/docs

