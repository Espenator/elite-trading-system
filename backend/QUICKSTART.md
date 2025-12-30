# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Create Virtual Environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Create .env File

Create a `.env` file in the `backend` directory with the following content:

```env
# Application Settings
PORT=8001
HOST=0.0.0.0

# Finviz API Configuration
FINVIZ_API_KEY=4475cd42-70ea-4fa7-9630-0d9cd30d9620
FINVIZ_BASE_URL=https://elite.finviz.com

# Screener Filters
FINVIZ_SCREENER_FILTERS=cap_midover,sh_avgvol_o500,sh_price_o10
FINVIZ_SCREENER_VERSION=111
FINVIZ_SCREENER_FILTER_TYPE=4

# Quote Settings
FINVIZ_QUOTE_TIMEFRAME=d
```

**Important:** Replace `4475cd42-70ea-4fa7-9630-0d9cd30d9620` with your actual Finviz API key.

### Step 4: Start the Server

```bash
# Windows
start.bat

# Or directly
python start_server.py

# Or with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Step 5: Test the API

Open your browser and visit:
- **API Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

Or use the test tools:

```bash
# Test backend API
python tools/test_api.py

# Test Finviz API directly
python tools/test_finviz_direct.py
```

## 📡 API Examples

### Get Stock List

```bash
curl http://localhost:8001/api/v1/stocks/list
```

### Get Quote Data for MSFT

```bash
curl http://localhost:8001/api/v1/quotes/MSFT
```

### Get Quote Data with Duration

```bash
# Year to date
curl "http://localhost:8001/api/v1/quotes/MSFT?p=d&r=ytd"

# 1 year
curl "http://localhost:8001/api/v1/quotes/MSFT?p=d&r=y1"

# Maximum available data
curl "http://localhost:8001/api/v1/quotes/MSFT?p=d&r=max"
```

## 🎯 Next Steps

1. Customize filters in `.env` file
2. Integrate with your frontend
3. Add more endpoints as needed

For more details, see [README.md](README.md).

