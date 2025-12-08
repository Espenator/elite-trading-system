"""
YFinance Price Data Client
===========================

Fetches real-time and historical price data using yfinance.
Stores data in database for prediction engine consumption.

Handles market-closed scenarios with current price fallback.

Author: Elite Trading Team
Date: December 5, 2025
"""

import logging
import time
import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


class YFinanceClient:
    """
    Fetch price data from Yahoo Finance.
    
    Features:
    - Real-time price quotes
    - Historical OHLCV data
    - Technical indicators (ATR, Volume)
    - Batch symbol fetching
    - Market-closed handling
    """
    
    def __init__(self, db_manager=None):
        """Initialize YFinance client"""
        self.db = db_manager
        self.max_retries = 3
        self.retry_delays = [1, 2, 3]  # seconds
        logger.info("✅ YFinance client initialized")
    
    def _fetch_symbol(self, symbol: str, period: str = '1d', interval: str = '1m') -> Optional[pd.DataFrame]:
        """
        Fetch data for a single symbol with retry logic.
        
        Args:
            symbol: Ticker symbol
            period: Data period (1d, 5d, 1mo, etc.)
            interval: Data interval (1m, 5m, 1h, 1d)
            
        Returns:
            DataFrame with OHLCV data or None
        """
        for attempt in range(self.max_retries):
            try:
                ticker = yf.Ticker(symbol)
                
                # Try to fetch historical data
                df = ticker.history(period=period, interval=interval)
                
                if df.empty:
                    # If empty, try current info as fallback
                    logger.warning(f"No historical data for {symbol}, trying current price...")
                    info = ticker.info
                    
                    if info and 'regularMarketPrice' in info:
                        # Create single-row dataframe with current price
                        current_price = info['regularMarketPrice']
                        prev_close = info.get('previousClose', current_price)
                        
                        df = pd.DataFrame({
                            'Open': [prev_close],
                            'High': [current_price],
                            'Low': [current_price],
                            'Close': [current_price],
                            'Volume': [info.get('volume', 0)]
                        }, index=[pd.Timestamp.now()])
                        
                        logger.info(f"✅ Using current price for {symbol}: ${current_price:.2f}")
                        return df
                    
                    logger.warning(f"No data available for {symbol}")
                    return None
                
                return df
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delays[attempt]
                    logger.warning(f"⚠️ Attempt {attempt + 1} failed for {symbol}: {e}")
                    logger.info(f"   Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ All retries failed for {symbol}: {e}")
                    return None
        
        return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Stock ticker
            
        Returns:
            Current price or None
        """
        try:
            df = self._fetch_symbol(symbol, period='1d', interval='1m')
            
            if df is None or df.empty:
                return None
            
            current_price = df['Close'].iloc[-1]
            return float(current_price)
            
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None
    
    def get_stock_data(self, symbol: str, period: str = '5d', interval: str = '1h') -> Optional[Dict]:
        """
        Get comprehensive stock data with metrics.
        
        Args:
            symbol: Stock ticker
            period: Data period ('1d', '5d', '1mo', etc.)
            interval: Bar interval ('1m', '5m', '1h', '1d')
            
        Returns:
            Dictionary with OHLCV + metrics
        """
        try:
            df = self._fetch_symbol(symbol, period=period, interval=interval)
            
            if df is None or df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Current price
            current_price = df['Close'].iloc[-1]
            
            # Calculate metrics
            high_5d = df['High'].max()
            low_5d = df['Low'].min()
            avg_volume = df['Volume'].mean()
            current_volume = df['Volume'].iloc[-1]
            
            # Volume surge
            volume_surge = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Price move (last bar)
            price_change_pct = ((df['Close'].iloc[-1] - df['Open'].iloc[-1]) / 
                               df['Open'].iloc[-1] * 100) if df['Open'].iloc[-1] > 0 else 0.0
            
            # ATR (Average True Range) - simple approximation
            df['TR'] = df['High'] - df['Low']
            atr = df['TR'].tail(14).mean()
            
            return {
                'symbol': symbol,
                'current_price': round(current_price, 2),
                'open': round(df['Open'].iloc[-1], 2),
                'high': round(df['High'].iloc[-1], 2),
                'low': round(df['Low'].iloc[-1], 2),
                'close': round(current_price, 2),
                'volume': int(current_volume),
                'high_5d': round(high_5d, 2),
                'low_5d': round(low_5d, 2),
                'atr': round(atr, 2),
                'volume_surge': round(volume_surge, 2),
                'price_change_pct': round(price_change_pct, 2),
                'avg_volume': int(avg_volume),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def fetch_and_store(self, symbol: str, period: str = '5d') -> bool:
        """
        Fetch price data and store in database.
        
        Args:
            symbol: Stock ticker
            period: Data period
            
        Returns:
            Success boolean
        """
        try:
            data = self.get_stock_data(symbol, period=period, interval='1h')
            
            if not data:
                logger.warning(f"No data available for {symbol}")
                return False
            
            if not self.db:
                logger.warning("No database manager - skipping storage")
                return False
            
            # Store in database
            success = self.db.insert_market_data(symbol, {
                'timestamp': data['timestamp'],
                'open': data['open'],
                'high': data['high'],
                'low': data['low'],
                'close': data['close'],
                'volume': data['volume']
            })
            
            if success:
                logger.info(f"✅ Stored price data for {symbol}: ${data['current_price']}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to fetch and store {symbol}: {e}")
            return False
    
    def batch_fetch_and_store(self, symbols: List[str], period: str = '5d') -> int:
        """
        Fetch and store data for multiple symbols.
        
        Args:
            symbols: List of tickers
            period: Data period
            
        Returns:
            Number of successful fetches
        """
        logger.info(f"📊 Fetching price data for {len(symbols)} symbols...")
        
        successful = 0
        
        for symbol in symbols:
            if self.fetch_and_store(symbol, period):
                successful += 1
            time.sleep(0.5)  # Rate limiting
        
        logger.info(f"✅ Stored price data for {successful}/{len(symbols)} symbols")
        
        return successful
    
    def get_historical_data(self, symbol: str, start_date: datetime, 
                           end_date: datetime = None) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data.
        
        Args:
            symbol: Stock ticker
            start_date: Start date
            end_date: End date (defaults to now)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            if end_date is None:
                end_date = datetime.now()
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                logger.warning(f"No historical data for {symbol}")
                return None
            
            logger.info(f"✅ Fetched {len(df)} bars for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return None

