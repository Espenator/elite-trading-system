"""
API Routes for Paper Trading - Glass House UI Backend
Handles trade execution and portfolio management
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import json
import uuid
import os

router = APIRouter(prefix="/api", tags=["trading"])
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "trading.db")


class TradeRequest(BaseModel):
    symbol: str
    action: str
    quantity: int
    orderType: str = "MARKET"
    price: Optional[float] = None
    stopLoss: Optional[float] = None
    takeProfit: Optional[float] = None


class TradeResponse(BaseModel):
    tradeId: str
    status: str
    executedPrice: float
    executedAt: str
    message: str


class Position(BaseModel):
    symbol: str
    quantity: int
    avgPrice: float
    currentPrice: float
    unrealizedPL: float
    unrealizedPLPercent: float
    marketValue: float
    todaysPL: float


class Portfolio(BaseModel):
    accountValue: float
    cash: float
    positions: List[Position]


class Trade(BaseModel):
    id: str
    timestamp: str
    symbol: str
    action: str
    quantity: int
    price: float
    total: float
    pl: Optional[float] = None
    plPercent: Optional[float] = None


def get_db_connection():
    """Create database connection"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total REAL NOT NULL,
                pl REAL,
                pl_percent REAL,
                status TEXT DEFAULT 'EXECUTED'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                symbol TEXT PRIMARY KEY,
                quantity INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                cash REAL NOT NULL DEFAULT 1000000.0,
                last_updated TEXT NOT NULL
            )
        """)
        
        cursor.execute("SELECT COUNT(*) FROM portfolio")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO portfolio (id, cash, last_updated) VALUES (1, 1000000.0, ?)", (datetime.now().isoformat(),))
        
        conn.commit()
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/trades", response_model=TradeResponse)
async def execute_trade(trade: TradeRequest):
    """Execute a paper trade (BUY or SELL)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        import yfinance as yf
        ticker = yf.Ticker(trade.symbol)
        current_price = trade.price or float(ticker.info.get('currentPrice', ticker.history(period='1d')['Close'].iloc[-1]))
        
        trade_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        total = current_price * trade.quantity
        
        cursor.execute("SELECT cash FROM portfolio WHERE id = 1")
        cash = cursor.fetchone()[0]
        
        if trade.action == "BUY":
            if cash < total:
                raise HTTPException(status_code=400, detail="Insufficient funds")
            
            cursor.execute("UPDATE portfolio SET cash = cash - ?, last_updated = ? WHERE id = 1", (total, timestamp))
            
            cursor.execute("SELECT quantity, avg_price FROM positions WHERE symbol = ?", (trade.symbol,))
            existing = cursor.fetchone()
            
            if existing:
                old_qty, old_avg = existing
                new_qty = old_qty + trade.quantity
                new_avg = ((old_qty * old_avg) + (trade.quantity * current_price)) / new_qty
                cursor.execute("UPDATE positions SET quantity = ?, avg_price = ?, last_updated = ? WHERE symbol = ?", (new_qty, new_avg, timestamp, trade.symbol))
            else:
                cursor.execute("INSERT INTO positions (symbol, quantity, avg_price, last_updated) VALUES (?, ?, ?, ?)", (trade.symbol, trade.quantity, current_price, timestamp))
            
            cursor.execute("INSERT INTO trades (id, timestamp, symbol, action, quantity, price, total, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'EXECUTED')", (trade_id, timestamp, trade.symbol, trade.action, trade.quantity, current_price, total))
            
            conn.commit()
            
            return {"tradeId": trade_id, "status": "EXECUTED", "executedPrice": current_price, "executedAt": timestamp, "message": f"Successfully bought {trade.quantity} shares of {trade.symbol}"}
        
        elif trade.action == "SELL":
            cursor.execute("SELECT quantity, avg_price FROM positions WHERE symbol = ?", (trade.symbol,))
            position = cursor.fetchone()
            
            if not position or position[0] < trade.quantity:
                raise HTTPException(status_code=400, detail="Insufficient shares to sell")
            
            qty, avg_price = position
            pl = (current_price - avg_price) * trade.quantity
            pl_percent = ((current_price - avg_price) / avg_price) * 100
            
            cursor.execute("UPDATE portfolio SET cash = cash + ?, last_updated = ? WHERE id = 1", (total, timestamp))
            
            new_qty = qty - trade.quantity
            if new_qty == 0:
                cursor.execute("DELETE FROM positions WHERE symbol = ?", (trade.symbol,))
            else:
                cursor.execute("UPDATE positions SET quantity = ?, last_updated = ? WHERE symbol = ?", (new_qty, timestamp, trade.symbol))
            
            cursor.execute("INSERT INTO trades (id, timestamp, symbol, action, quantity, price, total, pl, pl_percent, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'EXECUTED')", (trade_id, timestamp, trade.symbol, trade.action, trade.quantity, current_price, total, pl, pl_percent))
            
            conn.commit()
            
            return {"tradeId": trade_id, "status": "EXECUTED", "executedPrice": current_price, "executedAt": timestamp, "message": f"Successfully sold {trade.quantity} shares of {trade.symbol}. P/L: ${pl:.2f} ({pl_percent:.2f}%)"}
        
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Must be BUY or SELL")
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {str(e)}")
    finally:
        conn.close()


@router.get("/portfolio", response_model=Portfolio)
async def get_portfolio():
    """Get current portfolio with positions and P/L"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT cash FROM portfolio WHERE id = 1")
        cash = cursor.fetchone()[0]
        
        cursor.execute("SELECT symbol, quantity, avg_price FROM positions")
        positions_data = cursor.fetchall()
        
        positions = []
        total_market_value = 0
        
        import yfinance as yf
        for symbol, quantity, avg_price in positions_data:
            try:
                ticker = yf.Ticker(symbol)
                current_price = float(ticker.info.get('currentPrice', ticker.history(period='1d')['Close'].iloc[-1]))
                
                market_value = current_price * quantity
                unrealized_pl = (current_price - avg_price) * quantity
                unrealized_pl_percent = ((current_price - avg_price) / avg_price) * 100
                
                positions.append({
                    "symbol": symbol,
                    "quantity": quantity,
                    "avgPrice": round(avg_price, 2),
                    "currentPrice": round(current_price, 2),
                    "unrealizedPL": round(unrealized_pl, 2),
                    "unrealizedPLPercent": round(unrealized_pl_percent, 2),
                    "marketValue": round(market_value, 2),
                    "todaysPL": 0.0
                })
                
                total_market_value += market_value
            except:
                continue
        
        account_value = cash + total_market_value
        
        return {"accountValue": round(account_value, 2), "cash": round(cash, 2), "positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching portfolio: {str(e)}")
    finally:
        conn.close()


@router.get("/portfolio/history", response_model=dict)
async def get_trade_history(limit: int = 100):
    """Get trade history"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, timestamp, symbol, action, quantity, price, total, pl, pl_percent FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,))
        
        trades = []
        total_pl = 0
        wins = 0
        losses = 0
        
        for row in cursor.fetchall():
            trade = {"id": row[0], "timestamp": row[1], "symbol": row[2], "action": row[3], "quantity": row[4], "price": row[5], "total": row[6], "pl": row[7], "plPercent": row[8]}
            trades.append(trade)
            
            if row[7]:
                total_pl += row[7]
                if row[7] > 0:
                    wins += 1
                else:
                    losses += 1
        
        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        return {"trades": trades, "totalTrades": len(trades), "winRate": round(win_rate, 2), "totalPL": round(total_pl, 2), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")
    finally:
        conn.close()
