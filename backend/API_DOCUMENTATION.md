# Elite Trading System API Documentation

## Base URL
```
http://localhost:8001
```

## Endpoints

### 1. Health Check

**GET** `/health`

Check if the API is running.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### 2. Get Stock List

**GET** `/api/v1/stocks/list`

Get filtered stock list from Finviz screener.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filters` | string | No | Comma-separated filter parameters (e.g., `cap_midover,sh_avgvol_o500,sh_price_o10`) |
| `version` | string | No | Screener version (default: from config) |
| `filter_type` | string | No | Filter type (default: from config) |
| `columns` | string | No | Optional comma-separated column names to export |

**Example Request:**
```bash
GET /api/v1/stocks/list
```

**Example Request with Custom Filters:**
```bash
GET /api/v1/stocks/list?filters=cap_midover,sh_avgvol_o500
```

**Example Response:**
```json
[
  {
    "No.": "1",
    "Ticker": "A",
    "Company": "Agilent Technologies Inc",
    "Sector": "Healthcare",
    "Industry": "Diagnostics & Research",
    "Country": "USA",
    "Market Cap": "39103.00",
    "P/E": "30.18",
    "Price": "137.93",
    "Change": "-0.33%",
    "Volume": "1640846"
  },
  {
    "No.": "2",
    "Ticker": "AA",
    "Company": "Alcoa Corp",
    "Sector": "Basic Materials",
    "Industry": "Aluminum",
    "Country": "USA",
    "Market Cap": "13924.50",
    "P/E": "12.21",
    "Price": "53.77",
    "Change": "-0.88%",
    "Volume": "4210957"
  }
]
```

---

### 3. Get Quote/Chart Data

**GET** `/api/v1/quotes/{ticker}`

Get historical price data for a specific ticker.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | Yes | Stock ticker symbol (e.g., MSFT, AAPL) |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `p` | string | No | Timeframe/unit (default: from config). See options below. |
| `r` | string | No | Duration/range (optional). See options below. |

**Timeframe Options (`p` parameter):**
- `i1` - 1 minute intervals
- `i3` - 3 minute intervals
- `i5` - 5 minute intervals
- `i15` - 15 minute intervals
- `i30` - 30 minute intervals
- `h` - Hourly
- `d` - Daily (default)
- `w` - Weekly
- `m` - Monthly

**Duration Options (`r` parameter):**
- `d1` - 1 day
- `d5` - 5 days
- `m1` - 1 month
- `m3` - 3 months
- `m6` - 6 months
- `ytd` - Year to date
- `y1` - 1 year
- `y2` - 2 years
- `y5` - 5 years
- `max` - Maximum available data

**Example Request:**
```bash
GET /api/v1/quotes/MSFT
```

**Example Request with Timeframe:**
```bash
GET /api/v1/quotes/MSFT?p=d
```

**Example Request with Duration:**
```bash
GET /api/v1/quotes/MSFT?p=d&r=ytd
```

**Example Request with Both:**
```bash
GET /api/v1/quotes/MSFT?p=d&r=y1
```

**Example Response:**
```json
[
  {
    "Date": "12/17/2015",
    "Open": "56.36",
    "High": "56.79",
    "Low": "55.535",
    "Close": "55.7",
    "Volume": "41280908"
  },
  {
    "Date": "12/18/2015",
    "Open": "55.77",
    "High": "56",
    "Low": "54.03",
    "Close": "54.13",
    "Volume": "84684160"
  },
  {
    "Date": "12/21/2015",
    "Open": "54.88",
    "High": "55.35",
    "Low": "54.226",
    "Close": "54.83",
    "Volume": "37246324"
  }
]
```

---

## Response Format

### Stock List Response

Each stock object contains:
- `No.` - Stock number in the list
- `Ticker` - Stock ticker symbol
- `Company` - Company name
- `Sector` - Business sector
- `Industry` - Industry classification
- `Country` - Country of origin
- `Market Cap` - Market capitalization
- `P/E` - Price to Earnings ratio
- `Price` - Current price
- `Change` - Price change percentage
- `Volume` - Trading volume

### Quote Data Response

Each quote object contains:
- `Date` - Date of the quote (format: MM/DD/YYYY)
- `Open` - Opening price
- `High` - Highest price
- `Low` - Lowest price
- `Close` - Closing price
- `Volume` - Trading volume

---

## Error Responses

### 500 Internal Server Error

```json
{
  "detail": "Error message description"
}
```

**Common Error Scenarios:**
- Invalid API key
- Invalid ticker symbol
- Network timeout
- Finviz API error

---

## Usage Examples

### cURL Examples

**Get stock list:**
```bash
curl http://localhost:8001/api/v1/stocks/list
```

**Get quote data for MSFT (daily, year to date):**
```bash
curl "http://localhost:8001/api/v1/quotes/MSFT?p=d&r=ytd"
```

**Get quote data for AAPL (weekly, 1 year):**
```bash
curl "http://localhost:8001/api/v1/quotes/AAPL?p=w&r=y1"
```

**Get quote data for NVDA (daily, maximum):**
```bash
curl "http://localhost:8001/api/v1/quotes/NVDA?p=d&r=max"
```

### JavaScript/Fetch Examples

**Get stock list:**
```javascript
const response = await fetch('http://localhost:8001/api/v1/stocks/list');
const stocks = await response.json();
console.log(stocks);
```

**Get quote data:**
```javascript
const ticker = 'MSFT';
const p = 'd';
const r = 'ytd';
const url = `http://localhost:8001/api/v1/quotes/${ticker}?p=${p}&r=${r}`;
const response = await fetch(url);
const quotes = await response.json();
console.log(quotes);
```

### Python Examples

**Get stock list:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://localhost:8001/api/v1/stocks/list")
    stocks = response.json()
    print(stocks)
```

**Get quote data:**
```python
import httpx

ticker = "MSFT"
p = "d"
r = "ytd"
url = f"http://localhost:8001/api/v1/quotes/{ticker}?p={p}&r={r}"

async with httpx.AsyncClient() as client:
    response = await client.get(url)
    quotes = response.json()
    print(quotes)
```

---

## Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

You can test all endpoints directly from these documentation pages.

---

## Configuration

All API settings can be configured in the `.env` file:

```env
PORT=8001
HOST=0.0.0.0
FINVIZ_API_KEY=your_api_key_here
FINVIZ_SCREENER_FILTERS=cap_midover,sh_avgvol_o500,sh_price_o10
FINVIZ_QUOTE_TIMEFRAME=d
```

---

## Rate Limits

Please be aware of Finviz API rate limits. The backend does not implement rate limiting, so ensure you don't exceed Finviz's limits when making requests.

---

## Support

For issues or questions, please refer to:
- [README.md](README.md) - Setup and installation guide
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide

