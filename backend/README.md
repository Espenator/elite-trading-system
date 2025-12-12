# Elite Trading System - Backend

A high-performance FastAPI backend providing real-time trading signals, market data analysis, and stock screening capabilities. Features live WebSocket streaming of trading signals with multi-factor scoring algorithms.

## 🚀 Features

- **Real-Time Signal Feed**: WebSocket-based live trading signal streaming
- **Multi-Factor Signal Engine**: Analyzes momentum, volume, RSI, VWAP, and gap patterns
- **Tiered Signal Classification**: T1/T2/T3 signals based on confidence scores (0-100)
- **Stock Screener**: Scrapes and stores stock data from Finviz.com
- **Live Market Data**: Integrated with yfinance for real-time price and volume data
- **Chart Data API**: Historical price data for charting applications
- **SQLite Database**: Persistent storage for stock screener results
- **Auto-Reconnecting WebSockets**: Robust connection handling with heartbeat
- **RESTful API**: Full CRUD operations for stock data management

## 🛠️ Tech Stack

- **Framework**: FastAPI 0.104+
- **ASGI Server**: Uvicorn with WebSocket support
- **Database**: SQLAlchemy 2.0 + SQLite (aiosqlite)
- **Market Data**: yfinance, pandas, numpy
- **Web Scraping**: httpx, BeautifulSoup4, lxml
- **Data Validation**: Pydantic 2.0+
- **Configuration**: pydantic-settings, python-dotenv

## 📋 Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## 🔧 Installation

### 1. Clone the Repository

```bash
cd backend
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration (Optional)

Create a `.env` file in the backend directory:

```env
# Application Settings
APP_NAME="Elite Trading System API"
DEBUG=False

# Database
DATABASE_URL="sqlite:///./finviz_stocks.db"

# Finviz Settings
FINVIZ_USE_ELITE=False
DEFAULT_FILTERS="cap_midover,sh_avgvol_o500,sh_price_o10"
```

## 🚀 Running the Server

### Development Mode (with auto-reload)

```bash
python start_server.py
```

### Production Mode

```bash
python start_server.py --prod
```

### Custom Host and Port

```bash
python start_server.py --host 0.0.0.0 --port 8080
```

### Using Uvicorn Directly

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start on `http://localhost:8000`

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/ws

## 📡 API Endpoints

### Root & Health

- `GET /` - API information and available endpoints
- `GET /health` - Server health check with WebSocket status

### Stock Data

- `GET /api/v1/stocks` - List stocks (paginated)
  - Query params: `page`, `per_page`, `ticker`, `sector`, `country`
- `GET /api/v1/stocks/ticker/{ticker}` - Get single stock by ticker
- `GET /api/v1/stocks/sectors` - List unique sectors
- `GET /api/v1/stocks/countries` - List unique countries
- `POST /api/v1/stocks/scrape` - Scrape stocks from Finviz
  - Body: `{"filters": "cap_midover,sh_avgvol_o500"}`
  - Query params: `max_pages` (optional)
- `DELETE /api/v1/stocks` - Delete all stocks

### Chart Data

- `GET /api/chart/data/{symbol}` - Get historical chart data
  - Query params: `period` (1d, 5d, 1mo, 3mo, 6mo, 1y, 5y)
  - Query params: `interval` (1m, 5m, 15m, 1h, 1d)

### WebSocket

- `WS /ws` - Live trading signal feed
- `WS /api/v1/ws` - Alternative WebSocket endpoint

#### WebSocket Message Format

**Signals Update:**
```json
{
  "type": "signals_update",
  "signals": [
    {
      "symbol": "AAPL",
      "signal_type": "momentum",
      "tier": "T1",
      "score": 85.5,
      "price": 178.50,
      "change_pct": 2.5,
      "volume_ratio": 2.3,
      "catalyst": "Strong momentum +2.5% with 2.3x vol",
      "rsi": 65.2,
      "momentum": 3.1,
      "vwap": 177.80,
      "timestamp": "2024-12-12T10:30:00"
    }
  ],
  "timestamp": "2024-12-12T10:30:00"
}
```

**Connection Status:**
```json
{
  "type": "connection_status",
  "status": "connected",
  "message": "Connected to live signal feed"
}
```

## 🎯 Signal Engine

### Signal Types

1. **MOMENTUM** - Strong price momentum with volume
2. **VOLUME_SPIKE** - Unusual volume activity (2x+ average)
3. **RSI_OVERSOLD** - RSI below 30 (potential reversal)
4. **RSI_OVERBOUGHT** - RSI above 70 (potential reversal)
5. **BREAKOUT** - Price breakout patterns
6. **VWAP_CROSS** - Price crossing VWAP indicator
7. **GAP_UP** - Significant gap up from previous close
8. **GAP_DOWN** - Significant gap down from previous close

### Signal Tiers

- **T1 (High Confidence)**: Score ≥ 80 - Strongest signals with multiple confirming factors
- **T2 (Medium Confidence)**: Score ≥ 60 - Good signals with decent setup
- **T3 (Lower Confidence)**: Score < 60 - Weaker signals, lower probability

### Scoring Components

The signal engine uses a weighted multi-factor scoring system:

- **Volume (25%)**: Volume ratio vs average volume
- **Momentum (30%)**: Price change and momentum indicators
- **RSI (20%)**: Relative Strength Index positioning
- **Gap (15%)**: Gap from previous close
- **VWAP (10%)**: Price relationship to VWAP

**Composite Score**: 0-100 weighted average of all factors

### Configuration Thresholds

```python
{
    'volume_spike_threshold': 2.0,    # 2x average volume
    'high_volume_threshold': 3.0,     # 3x for stronger signal
    'rsi_oversold': 30,
    'rsi_overbought': 70,
    'momentum_threshold': 2.0,         # 2% move
    'strong_momentum': 5.0,            # 5% move
    'gap_threshold': 2.0,              # 2% gap
    'min_signal_score': 40,            # Minimum score to generate
}
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── chart.py             # Chart data endpoints
│   │       ├── items.py             # Sample CRUD endpoints
│   │       ├── stocks.py            # Stock data endpoints
│   │       └── websocket.py         # WebSocket endpoint & manager
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py                # Application configuration
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py                # SQLAlchemy models
│   │   └── session.py               # Database session management
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── item.py                  # Item schemas
│   │   └── stock.py                 # Stock schemas
│   └── services/
│       ├── __init__.py
│       ├── finviz_scraper.py        # Finviz web scraper
│       ├── live_data_service.py     # Real-time market data service
│       ├── signal_engine.py         # Trading signal generation
│       ├── stock_service.py         # Stock CRUD operations
│       └── item_service.py          # Item CRUD operations
├── tests/
│   ├── __init__.py
│   └── test_items.py                # Test suite
├── start_server.py                  # Server startup script
├── requirements.txt                 # Python dependencies
├── finviz_stocks.db                 # SQLite database (auto-created)
└── README.md                        # This file
```

## 🔍 Key Components

### LiveDataService

Manages real-time market data streaming:
- Fetches live data from yfinance
- Calculates technical indicators (RSI, VWAP, momentum)
- Updates every 5 seconds (configurable)
- Handles watchlist of symbols
- Thread-safe background processing

### SignalEngine

Multi-factor signal analysis:
- Analyzes market data using 5 scoring components
- Generates signals with 0-100 confidence scores
- Implements signal cooldown (60s per symbol)
- Configurable thresholds for all indicators
- Batch processing for multiple symbols

### WebSocketManager

Real-time communication:
- Manages multiple concurrent WebSocket connections
- Broadcasting signals to all connected clients
- Heartbeat mechanism (every 30s)
- Automatic scanner start/stop based on connections
- Connection state tracking

### FinvizScraper

Web scraping for stock data:
- Scrapes Finviz screener with custom filters
- Multi-page scraping support
- Parses market cap, P/E, price, volume, etc.
- Handles both free and Elite Finviz accounts
- Built-in rate limiting and error handling

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## 🔐 Security Considerations

**For Production Deployment:**

1. **CORS Configuration**: Update allowed origins in `app/main.py`
   ```python
   allow_origins=["https://yourdomain.com"]  # Replace "*"
   ```

2. **Environment Variables**: Use production-grade secrets management
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **Authentication**: Add JWT or OAuth2 authentication
5. **HTTPS**: Use reverse proxy (nginx) with SSL certificates
6. **Database**: Consider PostgreSQL for production use
7. **Monitoring**: Add logging aggregation and error tracking

## 🐛 Troubleshooting

### Database Issues

```bash
# Reset database
rm finviz_stocks.db

# Restart server (will auto-create tables)
python start_server.py
```

### WebSocket Connection Failed

- Ensure server is running on correct host/port
- Check firewall settings
- Verify CORS configuration for frontend origin
- Check browser console for connection errors

### Scraping Fails

- Finviz may have changed HTML structure
- Check if Finviz is accessible from your network
- Try with different filters
- Consider using Elite Finviz account

### No Signals Generated

- Ensure stocks are in database (run scraper first)
- Check if market is open (signals based on live data)
- Lower `min_signal_score` threshold in signal engine config
- Monitor logs for errors

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [yfinance Documentation](https://pypi.org/project/yfinance/)
- [Finviz Screener](https://finviz.com/screener.ashx)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [WebSocket Protocol](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)

## 📝 Development Notes

### Adding New Signal Types

1. Add enum value to `SignalType` in `signal_engine.py`
2. Implement scoring logic in `SignalEngine._score_*` method
3. Update `_determine_signal_type` to handle new type
4. Adjust weights in `analyze` method if needed

### Adding New API Endpoints

1. Create router in `app/api/v1/`
2. Define schemas in `app/schemas/`
3. Implement business logic in `app/services/`
4. Include router in `app/main.py`

### Database Migrations

For schema changes:

```bash
# Install Alembic
pip install alembic

# Initialize migrations
alembic init alembic

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## 🤝 Contributing

1. Follow PEP 8 style guidelines
2. Add docstrings to all functions/classes
3. Write tests for new features
4. Update README for significant changes

## 📄 License

This project is part of the Elite Trading System suite.

## 💬 Support

For issues, questions, or contributions, please refer to the main project repository.

---

**Built with FastAPI** ⚡ | **Powered by yfinance** 📈 | **Elite Trading System** 🎯

