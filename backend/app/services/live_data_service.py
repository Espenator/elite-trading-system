# app/services/live_data_service.py
"""
Live market data service using yfinance.
Provides quotes and historical data for signal generation.
"""
import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# from app.db.session import SessionLocal
# from app.db.models import Stock

logger = logging.getLogger(__name__)


class LiveDataService:
    """
    Service for fetching market data using yfinance REST API.
    Used as data source for the signal engine.
    """
    
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=5)  # Reduced workers to limit concurrent requests
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 60  # seconds (increased to avoid rate limits)
        
    def _generate_sample_data(self, symbol: str) -> dict:
        """Generate sample data when live data is unavailable (rate limits, etc.)"""
        import random
        
        # Base prices for common symbols
        base_prices = {
            'SPY': 590.0, 'QQQ': 520.0, 'AAPL': 195.0, 'MSFT': 430.0, 'NVDA': 140.0,
            'META': 580.0, 'GOOGL': 175.0, 'AMZN': 225.0, 'TSLA': 400.0, 'AMD': 140.0
        }
        
        base_price = base_prices.get(symbol.upper(), 100.0)
        
        # Add some random variation
        price = base_price * (1 + random.uniform(-0.02, 0.02))
        prev_close = base_price * (1 + random.uniform(-0.01, 0.01))
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        
        return {
            'symbol': symbol,
            'price': round(price, 2),
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
            'volume': random.randint(1000000, 10000000),
            'avg_volume': 5000000,
            'volume_ratio': round(random.uniform(0.8, 2.5), 2),
            'momentum': round(random.uniform(-3, 3), 2),
            'rsi': round(random.uniform(30, 70), 2),
            'vwap': round(price * 0.998, 2),
            'high': round(price * 1.01, 2),
            'low': round(price * 0.99, 2),
            'open': round(prev_close, 2),
            'prev_close': round(prev_close, 2),
            'market_cap': random.randint(100000000000, 3000000000000),
            'sector': 'Technology',
            'timestamp': datetime.now().isoformat(),
            'is_sample': True  # Flag indicating this is sample data
        }
    
    def _get_ticker_data_sync(self, symbol: str) -> dict:
        """Synchronous method to fetch ticker data (runs in thread pool)"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get current quote info
            info = ticker.info or {}
            
            # Get intraday data (last 5 days, 5min intervals for momentum calc)
            hist = ticker.history(period="5d", interval="5m")
            
            if hist.empty:
                # Return sample data if live data unavailable
                logger.warning(f"No live data for {symbol}, using sample data")
                return self._generate_sample_data(symbol)
                
            current_price = hist['Close'].iloc[-1] if not hist.empty else info.get('regularMarketPrice', 0)
            prev_close = info.get('previousClose', current_price)
            
            # Calculate metrics
            change = current_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            
            # Volume analysis
            current_volume = hist['Volume'].iloc[-1] if not hist.empty else 0
            avg_volume = hist['Volume'].mean() if not hist.empty else 1
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Price momentum (5-period)
            if len(hist) >= 5:
                momentum = (hist['Close'].iloc[-1] - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5] * 100
            else:
                momentum = 0
            
            # RSI calculation (14 periods)
            rsi = self._calculate_rsi(hist['Close'], 14)
            
            # VWAP
            vwap = self._calculate_vwap(hist)
            
            return {
                'symbol': symbol,
                'price': round(current_price, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'volume': int(current_volume),
                'avg_volume': int(avg_volume),
                'volume_ratio': round(volume_ratio, 2),
                'momentum': round(momentum, 2),
                'rsi': round(rsi, 2) if rsi else None,
                'vwap': round(vwap, 2) if vwap else None,
                'high': round(hist['High'].iloc[-1], 2) if not hist.empty else 0,
                'low': round(hist['Low'].iloc[-1], 2) if not hist.empty else 0,
                'open': round(hist['Open'].iloc[-1], 2) if not hist.empty else 0,
                'prev_close': round(prev_close, 2),
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', 'Unknown'),
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            # Return sample data on error (including rate limits)
            return self._generate_sample_data(symbol)
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        """Calculate RSI indicator"""
        try:
            if len(prices) < period + 1:
                return None
            
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
        except:
            return None
    
    def _calculate_vwap(self, hist: pd.DataFrame) -> Optional[float]:
        """Calculate VWAP"""
        try:
            if hist.empty:
                return None
            
            typical_price = (hist['High'] + hist['Low'] + hist['Close']) / 3
            vwap = (typical_price * hist['Volume']).cumsum() / hist['Volume'].cumsum()
            
            return float(vwap.iloc[-1]) if not pd.isna(vwap.iloc[-1]) else None
        except:
            return None
    
    async def get_ticker_data(self, symbol: str) -> Optional[dict]:
        """Async method to fetch ticker data (uses REST API with caching)"""
        # Check cache
        cache_key = f"{symbol}_data"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if (datetime.now() - cached_time).seconds < self._cache_ttl:
                return cached_data
        
        # Fetch fresh data
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(self._executor, self._get_ticker_data_sync, symbol)
        
        if data:
            self._cache[cache_key] = (datetime.now(), data)
        
        return data
    
    async def get_multiple_tickers(self, symbols: List[str]) -> List[dict]:
        """Fetch data for multiple tickers concurrently"""
        tasks = [self.get_ticker_data(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if r and not isinstance(r, Exception)]
    
    def _get_tickers_from_db(self, limit: int = 50) -> List[str]:
        """Return default tickers for now to avoid rate limiting"""
        # TODO: Re-enable database query when rate limiting is resolved
        # try:
        #     db = SessionLocal()
        #     try:
        #         tickers = (
        #             db.query(Stock.ticker)
        #             .distinct()
        #             .order_by(Stock.updated_at.desc())
        #             .limit(limit)
        #             .all()
        #         )
        #         result = [t[0] for t in tickers if t[0]]
        #         if result:
        #             logger.info(f"Loaded {len(result)} tickers from database")
        #             return result
        #     finally:
        #         db.close()
        # except Exception as e:
        #     logger.error(f"Error loading tickers from database: {e}")
        
        # Using fixed list of 10 popular tickers to avoid Yahoo Finance rate limiting
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'SPY', 'QQQ']
    
    def _get_gainers_losers_sync(self, limit: int = 20) -> dict:
        """Fetch top gainers and losers (sync, for thread pool)"""
        try:
            # Get tickers from database
            watch_list = self._get_tickers_from_db()
            
            data = yf.download(watch_list, period="1d", interval="1m", progress=False, group_by='ticker')
            
            results = []
            for symbol in watch_list:
                try:
                    if symbol in data.columns.get_level_values(0):
                        ticker_data = data[symbol]
                        if not ticker_data.empty:
                            current = ticker_data['Close'].iloc[-1]
                            open_price = ticker_data['Open'].iloc[0]
                            change_pct = (current - open_price) / open_price * 100 if open_price else 0
                            volume = ticker_data['Volume'].sum()
                            
                            results.append({
                                'symbol': symbol,
                                'price': round(current, 2),
                                'change_pct': round(change_pct, 2),
                                'volume': int(volume)
                            })
                except:
                    continue
            
            # Sort by change percent
            results.sort(key=lambda x: x['change_pct'], reverse=True)
            
            return {
                'gainers': results[:limit],
                'losers': results[-limit:][::-1]
            }
        except Exception as e:
            logger.error(f"Error fetching gainers/losers: {e}")
            return {'gainers': [], 'losers': []}
    
    async def get_market_movers(self, limit: int = 20) -> dict:
        """Get top gainers and losers"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._get_gainers_losers_sync, limit)
    
    def shutdown(self):
        """Cleanup resources"""
        self._executor.shutdown(wait=False)


# Singleton instance
live_data_service = LiveDataService()
