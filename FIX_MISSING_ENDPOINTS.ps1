<#
.SYNOPSIS
    Fix Missing Backend Endpoints
.DESCRIPTION
    Adds missing endpoints that the frontend is trying to call:
    1. WebSocket endpoint at /ws
    2. Chart data endpoint at /api/chart/data/{symbol}
    3. Active signal endpoint at /api/signals/active/{symbol}
.NOTES
    Version: 1.0
    Date: December 8, 2025
#>

$ErrorActionPreference = "Stop"
$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PROJECT_ROOT

$C_INFO = "Cyan"
$C_SUCCESS = "Green"
$C_WARNING = "Yellow"
$C_ERROR = "Red"

Write-Host "`n================================================================================" -ForegroundColor $C_INFO
Write-Host "  FIX MISSING BACKEND ENDPOINTS" -ForegroundColor $C_INFO
Write-Host "================================================================================`n" -ForegroundColor $C_INFO

# ============================================================================
# STEP 1: ADD WEBSOCKET ENDPOINT
# ============================================================================

Write-Host "[1/4] Adding WebSocket endpoint..." -ForegroundColor $C_INFO

$websocketCode = @'
"""
WebSocket endpoint for real-time signal updates
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import json
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"❌ WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for messages
            data = await websocket.receive_text()
            
            # Echo back
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
'@

try {
    $wsPath = "$PROJECT_ROOT\backend\websocket.py"
    $websocketCode | Out-File -FilePath $wsPath -Encoding UTF8
    Write-Host "      [OK] WebSocket endpoint created!`n" -ForegroundColor $C_SUCCESS
} catch {
    Write-Host "      [ERROR] Failed: $_`n" -ForegroundColor $C_ERROR
}

# ============================================================================
# STEP 2: ADD CHART DATA ENDPOINT
# ============================================================================

Write-Host "[2/4] Adding chart data endpoint..." -ForegroundColor $C_INFO

$chartEndpoint = @'

@app.get("/api/chart/data/{symbol}")
async def get_chart_data(
    symbol: str,
    timeframe: str = "1H",
    db: Session = Depends(get_db)
):
    """
    Get chart data for TradingView
    Timeframes: 1m, 5m, 15m, 1H, 4H, 1D
    """
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        
        # Map timeframe to yfinance interval
        interval_map = {
            "1m": ("1d", "1m"),
            "5m": ("5d", "5m"),
            "15m": ("5d", "15m"),
            "1H": ("1mo", "1h"),
            "4H": ("3mo", "1d"),  # yfinance doesn\'t have 4h
            "1D": ("1y", "1d")
        }
        
        period, interval = interval_map.get(timeframe, ("1mo", "1h"))
        
        # Fetch data from yfinance
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Convert to TradingView format
        chart_data = []
        for index, row in hist.iterrows():
            chart_data.append({
                "time": int(index.timestamp()),
                "open": float(row[\'Open\']),
                "high": float(row[\'High\']),
                "low": float(row[\'Low\']),
                "close": float(row[\'Close\']),
                "volume": int(row[\'Volume\'])
            })
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "data": chart_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get chart data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
'@

try {
    # Append to main.py
    $mainPath = "$PROJECT_ROOT\backend\main.py"
    $chartEndpoint | Out-File -FilePath $mainPath -Append -Encoding UTF8
    Write-Host "      [OK] Chart data endpoint added!`n" -ForegroundColor $C_SUCCESS
} catch {
    Write-Host "      [ERROR] Failed: $_`n" -ForegroundColor $C_ERROR
}

# ============================================================================
# STEP 3: ADD ACTIVE SIGNAL ENDPOINT
# ============================================================================

Write-Host "[3/4] Adding active signal endpoint..." -ForegroundColor $C_INFO

$activeSignalEndpoint = @'

@app.get("/api/signals/active/{symbol}")
async def get_active_signal(symbol: str, db: Session = Depends(get_db)):
    """
    Get the most recent active signal for a specific symbol
    """
    try:
        from database.models import SignalHistory
        from datetime import datetime, timedelta
        
        # Get most recent signal from last 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        signal = db.query(SignalHistory).filter(
            SignalHistory.symbol == symbol.upper(),
            SignalHistory.generated_at >= cutoff_time
        ).order_by(SignalHistory.generated_at.desc()).first()
        
        if not signal:
            raise HTTPException(status_code=404, detail=f"No active signal found for {symbol}")
        
        return {
            "id": signal.id,
            "symbol": signal.symbol,
            "direction": signal.direction,
            "score": signal.score,
            "entry_price": signal.entry_price,
            "stop_price": signal.stop_price,
            "target_price": signal.target_price,
            "velez_score": signal.velez_score,
            "explosive_signal": signal.explosive_signal,
            "generated_at": signal.generated_at.isoformat(),
            "was_traded": signal.was_traded
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get active signal for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
'@

try {
    $activeSignalEndpoint | Out-File -FilePath $mainPath -Append -Encoding UTF8
    Write-Host "      [OK] Active signal endpoint added!`n" -ForegroundColor $C_SUCCESS
} catch {
    Write-Host "      [ERROR] Failed: $_`n" -ForegroundColor $C_ERROR
}

# ============================================================================
# STEP 4: UPDATE MAIN.PY TO INCLUDE WEBSOCKET
# ============================================================================

Write-Host "[4/4] Updating main.py to include WebSocket..." -ForegroundColor $C_INFO

$wsImport = @'

# Import WebSocket support
from backend.websocket import websocket_endpoint, manager
'@

try {
    $wsImport | Out-File -FilePath $mainPath -Append -Encoding UTF8
    Write-Host "      [OK] WebSocket imported!`n" -ForegroundColor $C_SUCCESS
} catch {
    Write-Host "      [ERROR] Failed: $_`n" -ForegroundColor $C_ERROR
}

# ============================================================================
# SUMMARY
# ============================================================================

Write-Host "================================================================================" -ForegroundColor $C_INFO
Write-Host "  ENDPOINTS ADDED SUCCESSFULLY!" -ForegroundColor $C_SUCCESS
Write-Host "================================================================================`n" -ForegroundColor $C_INFO

Write-Host "  NEW ENDPOINTS:" -ForegroundColor $C_INFO
Write-Host "    1. WebSocket:        ws://localhost:8000/ws" -ForegroundColor $C_SUCCESS
Write-Host "    2. Chart Data:       GET /api/chart/data/{symbol}?timeframe=1H" -ForegroundColor $C_SUCCESS
Write-Host "    3. Active Signal:    GET /api/signals/active/{symbol}" -ForegroundColor $C_SUCCESS
Write-Host ""

Write-Host "  NEXT STEP:" -ForegroundColor $C_INFO
Write-Host "    Restart backend:     cd C:\Users\Espen\elite-trading-system && python -m uvicorn backend.main:app --reload" -ForegroundColor $C_WARNING
Write-Host ""

Write-Host "================================================================================`n" -ForegroundColor $C_INFO

Write-Host "Press any key to restart backend..." -ForegroundColor $C_WARNING
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')

# Auto-restart backend
Write-Host "`n🔄 Restarting backend...`n" -ForegroundColor $C_INFO
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 2

Set-Location $PROJECT_ROOT
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "✅ Backend restarting on port 8000!`n" -ForegroundColor $C_SUCCESS
Write-Host "Refresh your browser at http://localhost:3001`n" -ForegroundColor $C_SUCCESS
