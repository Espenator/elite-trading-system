# Elite Trading System - Backend API

A clean, modern Python backend API for fetching stock data from Finviz Elite API.

## 🚀 Features

- **Stock Screener API**: Get filtered stock lists from Finviz
- **Quote/Chart Data API**: Get historical price data for trading charts
- **Environment Configuration**: Easy configuration via `.env` file
- **Clean Architecture**: Well-organized service layer and API endpoints
- **API Test Tools**: Built-in testing utilities

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **HTTP Client**: httpx (async)
- **Configuration**: pydantic-settings, python-dotenv
- **Data Validation**: Pydantic

## 📋 Prerequisites

- Python 3.11 or higher
- Finviz Elite API key
- pip (Python package manager)

## 🔧 Installation

### 1. Navigate to Backend Directory

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

### 4. Configure Environment

Copy `.env.example` to `.env` and update with your API key:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` file:

```env
# Application Settings
PORT=8001
HOST=0.0.0.0

# Finviz API
FINVIZ_API_KEY=your_api_key_here
FINVIZ_SCREENER_FILTERS=cap_midover,sh_avgvol_o500,sh_price_o10
```

## 🚀 Running the Server

### Development Mode

```bash
python start_server.py
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

The API will be available at:
- **API**: http://localhost:8001
- **Interactive Docs**: http://localhost:8001/docs
- **Alternative Docs**: http://localhost:8001/redoc

## 📡 API Endpoints

### 1. Get Stock List

**GET** `/api/v1/stocks/list`

Get filtered stock list from Finviz screener.

**Query Parameters:**
- `filters` (optional): Comma-separated filter parameters
- `version` (optional): Screener version
- `filter_type` (optional): Filter type
- `columns` (optional): Comma-separated column names to export

**Example:**
```bash
curl "http://localhost:8001/api/v1/stocks/list"
```

**With custom filters:**
```bash
curl "http://localhost:8000/api/v1/stocks/list?filters=cap_midover,sh_avgvol_o500"
```

### 2. Get Quote Data

**GET** `/api/v1/quotes/{ticker}`

Get historical price data for a specific ticker.

**Path Parameters:**
- `ticker`: Stock ticker symbol (e.g., MSFT, AAPL)

**Query Parameters:**
- `p` (optional): Timeframe/unit - i1, i3, i5, i15, i30, h, d, w, m (default: from config)
- `r` (optional): Duration/range - d1, d5, m1, m3, m6, ytd, y1, y2, y5, max

**Example:**
```bash
curl "http://localhost:8001/api/v1/quotes/MSFT"
```

**With timeframe:**
```bash
curl "http://localhost:8001/api/v1/quotes/MSFT?p=d"
```

**With duration:**
```bash
curl "http://localhost:8001/api/v1/quotes/MSFT?p=d&r=ytd"
```

**With both timeframe and duration:**
```bash
curl "http://localhost:8001/api/v1/quotes/MSFT?p=d&r=y1"
```

## 🧪 Testing

### Test Backend API

Run the API test tool:

```bash
python tools/test_api.py
```

This will test:
- Health check endpoint
- Stock list endpoint
- Quote data endpoint

### Test Finviz API Directly

Test Finviz API directly (bypasses backend):

```bash
python tools/test_finviz_direct.py
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── stocks.py       # Stock screener endpoints
│   │       └── quotes.py       # Quote/chart data endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Application configuration
│   └── services/
│       ├── __init__.py
│       └── finviz_service.py   # Finviz API service
├── tools/
│   ├── __init__.py
│   ├── test_api.py             # Backend API test tool
│   └── test_finviz_direct.py   # Direct Finviz API test tool
├── .env                        # Environment variables (create from .env.example)
├── .env.example                # Example environment file
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## ⚙️ Configuration

All configuration is done via `.env` file:

```env
# Finviz API
FINVIZ_API_KEY=your_api_key_here
FINVIZ_BASE_URL=https://elite.finviz.com

# Screener Filters
FINVIZ_SCREENER_FILTERS=cap_midover,sh_avgvol_o500,sh_price_o10
FINVIZ_SCREENER_VERSION=111
FINVIZ_SCREENER_FILTER_TYPE=4

# Quote Settings
FINVIZ_QUOTE_TIMEFRAME=d
```

### Filter Options

You can customize screener filters in `.env`:

- `cap_midover`: Mid-cap stocks and above
- `sh_avgvol_o500`: Average volume over 500K
- `sh_price_o10`: Price over $10

See [Finviz Screener Documentation](https://elite.finviz.com) for more filter options.

## 🔒 Security Notes

- Never commit `.env` file to version control
- Keep your API key secure
- Use environment variables in production
- Configure CORS appropriately for production

## 📚 Documentation

- **FastAPI Docs**: http://localhost:8001/docs (interactive)
- **ReDoc**: http://localhost:8001/redoc (alternative)

## 🐛 Troubleshooting

### API Key Issues

If you get authentication errors:
1. Verify your API key in `.env`
2. Check that the key is valid in Finviz Elite
3. Ensure no extra spaces in `.env` file

### Connection Timeouts

If requests timeout:
1. Check your internet connection
2. Verify Finviz API is accessible
3. Increase timeout in `finviz_service.py` if needed

## 📝 License

Copyright © 2025 Elite Trading System. All rights reserved.

