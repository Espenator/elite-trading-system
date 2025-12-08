# 🚀 QUICK START FOR OLEH

## What Just Got Fixed

✅ **CRITICAL FIX PUSHED** (Dec 8, 2025 12:10 PM)
- Added automatic signal broadcasting to `backend/api/websocket_endpoint.py`
- Scanner now runs every 5 minutes automatically
- Signals broadcast to all connected frontend clients
- **THE MAIN BLOCKER IS NOW FIXED**

---

## 3-Step Launch (5 Minutes)

### Step 1: Pull Latest Code
```powershell
cd C:\Users\Espen\OneDrive\Documents\GitHub\elite-trading-system
git pull origin main
```

### Step 2: Start Backend
```powershell
# In same directory
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
✅ FastAPI server initialized
✅ WebSocket manager ready
✅ Chart data endpoint ready
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Start Frontend
```powershell
# New terminal
cd C:\Users\Espen\OneDrive\Documents\GitHub\elite-trading-system\elite-trader-ui
npm run dev
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

---

## Test WebSocket Broadcasting

### Browser Console Test
Open http://localhost:3000, press F12, paste in console:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    console.log('✅ Connected to WebSocket');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('📡 Received:', data.type);
    
    if (data.type === 'signals_update') {
        console.log(`📢 Got ${data.signals.length} signals!`);
        console.table(data.signals.slice(0, 5)); // Show top 5
    }
};

ws.onerror = (error) => {
    console.error('❌ WebSocket error:', error);
};
```

**Expected Result:**
Within 30 seconds, you should see:
```
✅ Connected to WebSocket
📡 Received: connection
📡 Received: signals_update
📢 Got 20 signals!
```

---

## What You Should See

### Backend Terminal
```
🚀 Signal broadcasting loop started
⏰ Starting scheduled scan...
🚀 SCANNING YELLOW REGIME - REAL DATA - ALL STOCKS
✅ Finviz Elite: 150 stocks
📊 Downloading price data for ALL 150 stocks...
   Progress: 50/150 stocks processed
   Progress: 100/150 stocks processed
   Progress: 150/150 stocks processed
✅ SCAN COMPLETE: Scanned 142 stocks, returning top 20
   Top signal: TSLA (Score: 85.5)
✅ Generated 20 signals, broadcasting...
📡 Broadcast to 1 clients: signals_update
📡 Broadcast to 1 clients: new_signal
✅ Broadcast complete
⏳ Waiting 5 minutes until next scan...
```

### Frontend
You should see signals appearing in the LiveSignalFeed component automatically.

---

## If Something Breaks

### Backend Not Starting?
```powershell
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install -r requirements.txt

# Check port 8000 is free
netstat -ano | findstr :8000
```

### Frontend Not Starting?
```powershell
# Delete node_modules and reinstall
cd elite-trader-ui
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
npm run dev
```

### No Signals Broadcasting?
Check backend logs for:
- "🚀 Signal broadcasting loop started" (confirms loop running)
- "✅ Finviz Elite: X stocks" (confirms data source working)
- "✅ Generated X signals" (confirms scanner working)

If you see "Database fallback" - that's OK! It means Finviz API is down but system is using backup.

---

## Next Steps After This Works

### 1. Google Sheets API (30 minutes)
1. Visit: https://console.cloud.google.com/apis/library/sheets.googleapis.com?project=elite-trading-system-480216
2. Click "Enable"
3. Share spreadsheet: https://docs.google.com/spreadsheets/d/1KXlZobQ6lnF5DTtcFiUP4fpT8cEATX5D4C7wtTNuzU
4. Add email: `trading-bot@elite-trading-system-480216.iam.gserviceaccount.com`
5. Give "Editor" permission

### 2. Test Trade Logging
```python
from database.google_sheets_manager import GoogleSheetsManager

gsm = GoogleSheetsManager()
gsm.log_trade({
    "symbol": "AAPL",
    "action": "BUY",
    "price": 150.00,
    "quantity": 10,
    "timestamp": "2025-12-08 12:00:00"
})
```

### 3. Frontend State Management (1 hour)
Add symbol selection state in `elite-trader-ui/app/page.tsx`:

```typescript
const [selectedSymbol, setSelectedSymbol] = useState('SPY');

return (
  <>
    <LiveSignalFeed onSelectSymbol={setSelectedSymbol} />
    <ExecutionDeck symbol={selectedSymbol} />
    <TacticalChart symbol={selectedSymbol} />
  </>
);
```

---

## Success Criteria

**System is working when:**
- [x] Backend starts without errors
- [x] WebSocket connects successfully
- [x] Scan runs automatically every 5 minutes
- [x] Signals appear in browser console
- [ ] Frontend LiveSignalFeed updates automatically
- [ ] Clicking signal updates ExecutionDeck
- [ ] Chart loads for selected symbol
- [ ] Google Sheets logs trades

---

## Time Estimates

- **WebSocket working:** ✅ DONE (just pushed)
- **System fully functional:** 1 day (with Google Sheets)
- **Production polish:** 1 week (error handling, testing)

---

## Support Resources

- **Full Documentation:** `DEVELOPER_HANDOFF.md` (19KB)
- **GitHub Repo:** https://github.com/Espenator/elite-trading-system
- **API Docs:** http://localhost:8000/docs (when running)
- **Trade Spreadsheet:** https://docs.google.com/spreadsheets/d/1KXlZobQ6lnF5DTtcFiUP4fpT8cEATX5D4C7wtTNuzU

---

## Quick Commands Reference

```powershell
# Pull latest
git pull origin main

# Start backend
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend
cd elite-trader-ui && npm run dev

# Check backend logs
type data\logs\system.log

# Test scanner manually
python -c "import asyncio; from backend.scheduler import ScannerManager; asyncio.run(ScannerManager({}).run_scan({'regime': 'YELLOW', 'top_n': 10}))"
```

---

**Last Updated:** Dec 8, 2025, 12:10 PM EST  
**Status:** 🚀 Ready to launch - Critical fix applied
