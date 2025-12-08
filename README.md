# 🚀 Elite Trading System v7.0 - Glass House Edition

**Real-time ML Price Predictions + Unusual Whales Flow Analysis**

A production-grade quantitative trading system that combines machine learning predictions with institutional options flow data, featuring the Glass House Next.js UI.

---

## 🎯 Key Features

### 🏛️ Glass House UI (Next.js)
- **Modern React interface**: Built with Next.js 14 and TypeScript
- **Real-time updates**: WebSocket integration for live data
- **Command bar**: Quick access to all features (Cmd/Ctrl+K)
- **Intelligence Radar**: Live candidate scanning and analysis
- **Tactical Charts**: Advanced charting with TradingView integration
- **Execution Deck**: Portfolio management and position sizing

### 🤖 AI Prediction Engine
- **Multi-horizon predictions**: 1-hour, 1-day, 1-week price targets
- **XGBoost models**: 50+ engineered features per prediction
- **Real-time updates**: Continuous prediction generation
- **Confidence scoring**: Each prediction includes confidence level (30-95%)
- **Auto-resolution**: Predictions auto-resolve and track accuracy

### 📊 Unusual Whales Integration
- **Options flow**: Real-time call/put activity
- **Dark pool**: Large block trades and unusual activity
- **Whale alerts**: Massive premium transactions ($250K+)
- **Market tide**: Aggregate market sentiment
- **Sector flow**: Industry-level options activity

### ⚡ TimescaleDB Backend
- **High-performance**: Optimized for time-series data
- **Automatic compression**: 1-month retention, 1-year compressed
- **Hypertables**: Fast queries on millions of rows
- **JSONB storage**: Flexible raw data preservation

### 📈 Tracked Assets
- **Core 4**: SPY, QQQ, IBIT, ETHT (always tracked)
- **Dynamic tracking**: Top 50 symbols by options flow
- **Market indices**: Correlation tracking vs SPY/QQQ/IWM

---

## 📋 Prerequisites

### Required Software
```bash
# Python 3.11 or 3.13
python --version

# Node.js 18+ (for Glass House UI)
node --version
npm --version

# PostgreSQL 14+ with TimescaleDB extension
psql --version
```

### Required API Keys
- **Unusual Whales API** key (get from unusualwhales.com)
- **Alpha Vantage** key (get from alphavantage.co - free tier OK)

---

## 🚀 Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/Espenator/elite-trading-system.git
cd elite-trading-system
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Install Glass House UI Dependencies
```bash
cd glass-house-ui
npm install
cd ..
```

### Step 4: Setup TimescaleDB

#### Option A: Docker (Recommended)
```bash
docker run -d --name timescaledb \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=your_secure_password \
  timescale/timescaledb:latest-pg14
```

#### Option B: Local Installation

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql-14 timescaledb-2-postgresql-14
```

**macOS:**
```bash
brew install timescaledb
```

**Windows:**
Download installer from [timescale.com](https://www.timescale.com)

### Step 5: Initialize Database
```bash
# Connect to PostgreSQL
psql -U postgres -h localhost

# Create database
CREATE DATABASE elite_trading;
\q

# Load schema
psql -U postgres -h localhost -d elite_trading -f database/schema.sql
```

### Step 6: Configure System
```bash
# Edit configuration file
notepad config/config.yaml  # Windows
nano config/config.yaml     # Linux/Mac
```

**Required configuration:**
```yaml
database:
  host: localhost
  port: 5432
  database: elite_trading
  user: postgres
  password: your_secure_password

unusual_whales:
  api_key: YOUR_UW_API_KEY_HERE

alpha_vantage:
  api_key: YOUR_AV_API_KEY_HERE
```

---

## 🎮 Usage

### Quick Launch (Recommended)

**Windows:**
```powershell
# Double-click or run:
.\LAUNCH_GLASS_HOUSE.bat

# OR use Aurora launcher:
.\LAUNCH_AURORA.ps1
```

**Manual Launch:**
```bash
# Terminal 1: Start Backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start Glass House UI
cd glass-house-ui
npm run dev
```

### Access Points
- **Glass House UI**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs

---

## 📊 System Architecture

```
elite-trading-system/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── routers/             # API endpoints
│   └── services/            # Business logic
│
├── glass-house-ui/          # Next.js frontend
│   ├── app/                 # Next.js app router
│   ├── components/          # React components
│   └── lib/                 # Utilities
│
├── database/
│   ├── schema.sql           # TimescaleDB schema
│   ├── models.py            # SQLAlchemy ORM models
│   └── timescale_manager.py # Database operations
│
├── data_ingestion/
│   └── unusual_whales_client.py  # UW API client
│
├── prediction_engine/
│   └── predictor.py         # ML prediction engine
│
├── core/
│   └── orchestrator.py      # System orchestrator
│
├── config/
│   └── config.yaml          # Configuration
│
├── LAUNCH_AURORA.ps1        # PowerShell launcher
├── LAUNCH_GLASS_HOUSE.bat   # Batch launcher
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

---

## 🔧 Configuration Options

### Database Settings
```yaml
database:
  host: localhost
  port: 5432
  database: elite_trading
  user: postgres
  password: your_password
  pool_size: 10
  max_overflow: 20
```

### Unusual Whales Settings
```yaml
unusual_whales:
  api_key: YOUR_API_KEY
  base_url: https://api.unusualwhales.com/api
  max_requests_per_minute: 100
  
  polling:
    options_flow_seconds: 60
    darkpool_seconds: 60
    market_tide_seconds: 300
```

### Prediction Engine Settings
```yaml
prediction_engine:
  horizons: ['1H', '1D', '1W']
  min_confidence_to_display: 50
  
  update_intervals:
    prediction_1h: 60      # Generate predictions every 60s
    prediction_1d: 900     # Generate predictions every 15min
    resolution_1h: 60      # Check for resolved predictions
  
  models:
    max_depth: 6
    learning_rate: 0.1
    n_estimators: 100
```

### Symbol Tracking
```yaml
symbols:
  core_4: ['SPY', 'QQQ', 'IBIT', 'ETHT']  # Always tracked
  indices: ['SPY', 'QQQ', 'IWM', 'DIA']
  etfs: ['XLF', 'XLE', 'XLK', 'XLV']
```

---

## 📈 Glass House UI Features

### Zone 0: Command Bar
- **Keyboard shortcuts**: Cmd/Ctrl+K to open
- **Quick navigation**: Jump to any feature instantly
- **Search**: Find stocks, execute commands

### Zone 1: Intelligence Radar
- **Live candidates**: Real-time scanning results
- **Scoring**: Multi-factor analysis (Velez, ML, Flow)
- **Watchlist**: Track favorites
- **Filters**: Price, volume, sector, regime

### Zone 2: Tactical Chart
- **TradingView integration**: Professional charting
- **Signal overlay**: Entry/exit points
- **Multi-timeframe**: 1m to 1W analysis
- **Comparison**: Side-by-side analysis

### Zone 3: Execution Deck
- **Position sizing**: Kelly Criterion calculator
- **Portfolio tracking**: Real-time P&L
- **Risk management**: Stop-loss automation
- **Order execution**: Direct broker integration (coming soon)

### Zone 4: Live Feed
- **Real-time signals**: As they happen
- **Notifications**: Desktop alerts
- **Signal history**: Track all generated signals
- **Export**: CSV download for analysis

---

## 🎯 Example Usage Flow

1. **Launch System**: Run `LAUNCH_GLASS_HOUSE.bat`
2. **Monitor Radar**: Watch Zone 1 for high-score candidates
3. **Analyze Chart**: Click candidate → Opens Zone 2 tactical view
4. **Size Position**: Use Zone 3 calculator for risk-appropriate sizing
5. **Execute Trade**: Manual execution (auto-execution coming Q1 2025)
6. **Track Performance**: Monitor in Zone 3 portfolio panel

---

## 🛠️ Troubleshooting

### Glass House UI Won't Start
```bash
# Check Node.js version
node --version  # Should be 18+

# Reinstall dependencies
cd glass-house-ui
rm -rf node_modules package-lock.json
npm install
```

### Backend API Connection Failed
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check logs
tail -f backend/logs/app.log
```

### Database Connection Failed
```bash
# Check TimescaleDB is running
docker ps | grep timescaledb

# Verify connection
psql -U postgres -h localhost -d elite_trading
```

### API Rate Limit Errors
```yaml
# Reduce polling frequency in config.yaml
unusual_whales:
  polling:
    options_flow_seconds: 120  # Increase from 60
```

---

## 📚 Database Schema

### Core Tables
- `symbols` - Tracked ticker symbols
- `price_data` - OHLCV price history
- `technical_indicators` - RSI, MACD, etc.
- `market_regime` - Daily market state

### Unusual Whales Tables
- `uw_options_flow` - Real-time options transactions
- `uw_darkpool` - Dark pool block trades
- `uw_whale_alerts` - Large premium alerts
- `uw_market_tide` - Market-wide sentiment

### ML Tables
- `predictions` - Generated predictions
- `prediction_outcomes` - Resolved predictions with accuracy
- `model_weights` - Feature weight tracking
- `ml_models` - Trained model metadata

---

## 🚀 Roadmap

**v7.1 (Q1 2025)**
- [x] Glass House UI (Next.js)
- [ ] WebSocket real-time updates
- [ ] Broker integration (Alpaca, IBKR)
- [ ] Telegram alerts

**v7.2 (Q2 2025)**
- [ ] Auto-execution with risk controls
- [ ] Advanced backtesting
- [ ] Portfolio optimization
- [ ] Paper trading simulator

**v8.0 (Q3 2025)**
- [ ] Mobile app (React Native)
- [ ] Multi-account support
- [ ] Social trading features
- [ ] Advanced analytics dashboard

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 📧 Contact

Questions? Issues? Reach out:
- GitHub Issues: [Create an issue](https://github.com/Espenator/elite-trading-system/issues)
- Repository: [Elite Trading System](https://github.com/Espenator/elite-trading-system)

---

## ⚠️ Disclaimer

This software is for educational and research purposes only. Trading involves substantial risk of loss. Past performance does not guarantee future results. Always do your own research and consult with a licensed financial advisor before making investment decisions.

---

**Built with ❤️ by the Elite Trading Team**
**Glass House Edition - Version 7.0**
