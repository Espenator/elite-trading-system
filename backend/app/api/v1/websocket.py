# app/api/v1/websocket.py
"""
WebSocket endpoint for live signal feed.
Streams real-time trading signals to connected clients.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set, List
import asyncio
import json
import logging
from datetime import datetime

from app.services.live_data_service import live_data_service
from app.services.signal_engine import signal_engine
from app.db.session import SessionLocal
from app.db.models import Stock

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._scanner_task: asyncio.Task = None
        self._is_running = False
        
        # Watchlist loaded from database
        self._watchlist: List[str] = []
        self._watchlist_loaded = False
        
        self.scan_interval = 10  # seconds between scans
    
    @property
    def default_watchlist(self) -> List[str]:
        """Get watchlist from database, with fallback to defaults"""
        if not self._watchlist_loaded:
            self._load_watchlist_from_db()
        return self._watchlist
    
    def _load_watchlist_from_db(self, limit: int = 5) -> None:
        """Load top tickers from the stocks database (limited to avoid rate limiting)"""
        # Use a very small fixed watchlist to avoid Yahoo Finance rate limiting
        # Yahoo Finance has aggressive rate limits (429 errors)
        self._watchlist = self._get_default_tickers()
        logger.info(f"Using {len(self._watchlist)} default tickers to avoid rate limiting")
        
        # Skip database loading to avoid hitting rate limits
        # The code below is disabled but kept for reference
        """
        try:
            db = SessionLocal()
            try:
                tickers = (
                    db.query(Stock.ticker)
                    .distinct()
                    .order_by(Stock.updated_at.desc())
                    .limit(limit)
                    .all()
                )
                self._watchlist = [t[0] for t in tickers if t[0]]
                
                if self._watchlist:
                    logger.info(f"Loaded {len(self._watchlist)} tickers from database")
                else:
                    self._watchlist = self._get_default_tickers()
                    logger.warning("No tickers in database, using default watchlist")
                    
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error loading watchlist from database: {e}")
            self._watchlist = self._get_default_tickers()
        
        self._watchlist_loaded = True
        """
    
    def _get_default_tickers(self) -> List[str]:
        """Fallback default tickers if database is empty"""
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD',
            'SPY', 'QQQ', 'IWM'
        ]
    
    def refresh_watchlist(self) -> int:
        """Refresh watchlist from database. Returns count of tickers loaded."""
        self._watchlist_loaded = False
        return len(self.default_watchlist)
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")
        
        # Send connection confirmation
        await self._send_to_client(websocket, {
            'type': 'connection',
            'message': 'Connected to Elite Trading Signal Feed',
            'timestamp': datetime.now().isoformat(),
            'watchlist_size': len(self.default_watchlist)
        })
        
        # Start scanner if not already running
        if not self._is_running:
            self._start_scanner()
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")
        
        # Stop scanner if no clients
        if not self.active_connections:
            self._stop_scanner()
    
    async def _send_to_client(self, websocket: WebSocket, message: dict):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
            self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        if not self.active_connections:
            return
        
        # Send to all clients concurrently
        disconnected = set()
        
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.active_connections -= disconnected
    
    def _start_scanner(self):
        """Start the background market scanner"""
        if self._scanner_task and not self._scanner_task.done():
            return
        
        self._is_running = True
        self._scanner_task = asyncio.create_task(self._scanner_loop())
        logger.info("Started market scanner")
    
    def _stop_scanner(self):
        """Stop the background market scanner"""
        self._is_running = False
        if self._scanner_task:
            self._scanner_task.cancel()
            self._scanner_task = None
        logger.info("Stopped market scanner")
    
    async def _scanner_loop(self):
        """Main scanner loop - uses yfinance WebSocket for real-time data"""
        logger.info(f"Scanner loop started. Monitoring {len(self.default_watchlist)} symbols")
        
        # Try WebSocket streaming first, fallback to polling
        try:
            await self._run_websocket_stream()
        except Exception as e:
            logger.warning(f"WebSocket streaming unavailable ({e}), falling back to polling...")
            await self._run_polling_loop()
    
    async def _run_websocket_stream(self):
        """
        Real-time streaming using yfinance WebSocket:
        
            async with yf.AsyncWebSocket() as ws:
                await ws.subscribe(["AAPL", "MSFT"])
                await ws.listen(on_message)
        """
        import yfinance as yf
        
        async def on_realtime_message(msg):
            """Handle real-time WebSocket messages"""
            if not self._is_running or not self.active_connections:
                return
            
            try:
                symbol = msg.get('id') or msg.get('symbol')
                if not symbol:
                    return
                
                # Build market data from real-time message
                market_data = {
                    'symbol': symbol,
                    'price': msg.get('price', 0),
                    'change_pct': msg.get('changePercent', 0),
                    'volume': msg.get('dayVolume', 0),
                    'volume_ratio': 1.5,  # Would need historical avg for accurate calc
                    'momentum': msg.get('changePercent', 0),
                    'high': msg.get('dayHigh', 0),
                    'low': msg.get('dayLow', 0),
                    'prev_close': msg.get('previousClose', 0),
                }
                
                # Analyze and check for signal
                signal = signal_engine.analyze(market_data)
                
                if signal:
                    await self.broadcast({
                        'type': 'new_signal',
                        'signal': signal.to_dict(),
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.info(f"Real-time signal: {symbol} - {signal.signal_type.value}")
                
                # Also broadcast quote update
                await self.broadcast({
                    'type': 'quote_update',
                    'data': market_data,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error processing real-time message: {e}")
        
        logger.info("Starting yfinance WebSocket stream...")
        
        async with yf.AsyncWebSocket() as ws:
            await ws.subscribe(self.default_watchlist)
            logger.info(f"Subscribed to {len(self.default_watchlist)} symbols via WebSocket")
            
            await self.broadcast({
                'type': 'status',
                'message': f'Connected to real-time feed - {len(self.default_watchlist)} symbols',
                'timestamp': datetime.now().isoformat()
            })
            
            await ws.listen(on_realtime_message)
    
    async def _run_polling_loop(self):
        """Fallback polling loop when WebSocket is unavailable"""
        logger.info("Running in polling mode...")
        
        while self._is_running and self.active_connections:
            try:
                # Broadcast status
                await self.broadcast({
                    'type': 'status',
                    'message': 'Scanning market...',
                    'timestamp': datetime.now().isoformat()
                })
                
                # Fetch market data for all watchlist symbols
                market_data = await live_data_service.get_multiple_tickers(self.default_watchlist)
                
                if market_data:
                    # Analyze data and generate signals
                    signals = signal_engine.batch_analyze(market_data)
                    
                    if signals:
                        # Convert signals to dicts for JSON serialization
                        signal_dicts = [s.to_dict() for s in signals]
                        
                        # Broadcast signals update
                        await self.broadcast({
                            'type': 'signals_update',
                            'signals': signal_dicts,
                            'count': len(signal_dicts),
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        logger.info(f"Generated {len(signals)} signals")
                    else:
                        # Send empty update to show system is working
                        await self.broadcast({
                            'type': 'scan_complete',
                            'message': 'Scan complete - no signals above threshold',
                            'symbols_scanned': len(market_data),
                            'timestamp': datetime.now().isoformat()
                        })
                
                # Wait before next scan
                await asyncio.sleep(self.scan_interval)
                
            except asyncio.CancelledError:
                logger.info("Scanner loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scanner loop: {e}")
                await asyncio.sleep(5)  # Wait before retry
        
        logger.info("Scanner loop ended")
    
    async def handle_client_message(self, websocket: WebSocket, message: str):
        """Handle incoming messages from clients"""
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')
            
            if msg_type == 'subscribe':
                # Client wants to subscribe to specific symbols
                symbols = data.get('symbols', [])
                if symbols:
                    # For now, just acknowledge - could implement per-client watchlists
                    await self._send_to_client(websocket, {
                        'type': 'subscribed',
                        'symbols': symbols,
                        'timestamp': datetime.now().isoformat()
                    })
            
            elif msg_type == 'get_quote':
                # Client requesting specific quote
                symbol = data.get('symbol', '')
                if symbol:
                    quote = await live_data_service.get_ticker_data(symbol)
                    if quote:
                        await self._send_to_client(websocket, {
                            'type': 'quote',
                            'data': quote,
                            'timestamp': datetime.now().isoformat()
                        })
            
            elif msg_type == 'get_movers':
                # Client requesting market movers
                movers = await live_data_service.get_market_movers()
                await self._send_to_client(websocket, {
                    'type': 'movers',
                    'data': movers,
                    'timestamp': datetime.now().isoformat()
                })
            
            elif msg_type == 'ping':
                await self._send_to_client(websocket, {
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                })
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message from client: {message}")
        except Exception as e:
            logger.error(f"Error handling client message: {e}")


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for live signal feed.
    
    Connects clients to the real-time signal stream.
    
    Message Types (Server -> Client):
    - connection: Initial connection confirmation
    - status: Scanner status updates
    - signals_update: Array of new trading signals
    - scan_complete: Notification when scan finishes (even with no signals)
    - quote: Single stock quote (on request)
    - movers: Market movers data (on request)
    
    Message Types (Client -> Server):
    - subscribe: Subscribe to specific symbols
    - get_quote: Request single stock quote
    - get_movers: Request market movers
    - ping: Keepalive ping
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Wait for messages from client
            message = await websocket.receive_text()
            await manager.handle_client_message(websocket, message)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
