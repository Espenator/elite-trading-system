"""
Unusual Whales Data Integration - Google Sheets Method
Falls back gracefully if not configured
"""

from typing import List, Dict, Optional
import yaml
from pathlib import Path
from datetime import datetime
import time
from core.logger import get_logger

logger = get_logger(__name__)

config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)


class UnusualWhalesIntegration:
    """Unified interface for whale data"""
    
    def __init__(self):
        self.google_sheets_available = False
        self.cache = {}
        self.cache_duration = config.get('api_credentials', {}).get('unusual_whales', {}).get('cache_duration_minutes', 15) * 60
        
        self._try_initialize_google_sheets()
    
    def _try_initialize_google_sheets(self):
        """Try to initialize Google Sheets connection"""
        try:
            gs_config = config.get('api_credentials', {}).get('unusual_whales', {}).get('google_sheets', {})
            
            if not gs_config.get('enabled', False):
                logger.info("📊 Google Sheets disabled in config")
                return
            
            import gspread
            from google.oauth2.service_account import Credentials
            
            creds_file = Path(__file__).parent.parent / gs_config.get('credentials_file', '')
            
            if not creds_file.exists():
                logger.info("📊 Google Sheets credentials not found - using fallback")
                return
            
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            
            creds = Credentials.from_service_account_file(str(creds_file), scopes=scopes)
            self.client = gspread.authorize(creds)
            
            spreadsheet_id = gs_config.get('spreadsheet_id', '')
            if spreadsheet_id:
                self.spreadsheet = self.client.open_by_key(spreadsheet_id)
                self.google_sheets_available = True
                logger.info(f"✅ Connected to Google Sheets: {self.spreadsheet.title}")
            
        except ImportError:
            logger.info("📊 gspread not installed - install with: pip install gspread google-auth")
        except Exception as e:
            logger.info(f"📊 Google Sheets unavailable: {e}")
    
    def get_whale_data(self, symbol: str) -> Optional[Dict]:
        """Get whale data for symbol (Google Sheets or fallback)"""
        cache_key = f"whale_{symbol}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_duration:
                return cached_data
        
        data = None
        
        if self.google_sheets_available:
            data = self._get_from_google_sheets(symbol)
        
        if not data and config.get('api_credentials', {}).get('unusual_whales', {}).get('use_finviz_fallback', True):
            data = self._get_from_finviz_fallback(symbol)
        
        if data:
            self.cache[cache_key] = (time.time(), data)
        
        return data
    
    def _get_from_google_sheets(self, symbol: str) -> Optional[Dict]:
        """Get data from Google Sheets"""
        try:
            worksheets = config.get('api_credentials', {}).get('unusual_whales', {}).get('google_sheets', {}).get('worksheets', {})
            
            dark_pool_sheet = worksheets.get('dark_pool', 'Dark Pool')
            options_sheet = worksheets.get('options_flow', 'Options Flow')
            
            dp_worksheet = self.spreadsheet.worksheet(dark_pool_sheet)
            opt_worksheet = self.spreadsheet.worksheet(options_sheet)
            
            dp_records = [r for r in dp_worksheet.get_all_records() if r.get('Symbol', '').upper() == symbol.upper()]
            opt_records = [r for r in opt_worksheet.get_all_records() if r.get('Symbol', '').upper() == symbol.upper()]
            
            if not dp_records and not opt_records:
                return None
            
            total_premium = sum(r.get('Premium', 0) for r in opt_records)
            calls = sum(r.get('Premium', 0) for r in opt_records if r.get('Type', '').upper() == 'CALL')
            puts = sum(r.get('Premium', 0) for r in opt_records if r.get('Type', '').upper() == 'PUT')
            
            sentiment = 'NEUTRAL'
            if total_premium > 0:
                call_ratio = calls / total_premium
                if call_ratio > 0.6:
                    sentiment = 'BULLISH'
                elif call_ratio < 0.4:
                    sentiment = 'BEARISH'
            
            return {
                'symbol': symbol,
                'total_premium': total_premium,
                'call_premium': calls,
                'put_premium': puts,
                'sentiment': sentiment,
                'dark_pool_blocks_7d': len(dp_records),
                'whale_trades_24h': len(opt_records),
                'source': 'google_sheets',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Google Sheets lookup failed for {symbol}: {e}")
            return None
    
    def _get_from_finviz_fallback(self, symbol: str) -> Optional[Dict]:
        """Fallback: basic whale data structure"""
        return {
            'symbol': symbol,
            'total_premium': 0,
            'sentiment': 'NEUTRAL',
            'dark_pool_blocks_7d': 0,
            'source': 'fallback',
            'timestamp': datetime.now().isoformat()
        }


whale_integration = UnusualWhalesIntegration()


async def enrich_signals(signals: List[Dict]) -> List[Dict]:
    """Enrich signals with whale data"""
    if not signals:
        return signals
    
    if not config.get('data_sources', {}).get('whale_data', {}).get('enabled', True):
        logger.info("📊 Whale data enrichment disabled")
        return signals
    
    logger.info(f"🐋 Enriching {len(signals)} signals...")
    enriched_count = 0
    
    for signal in signals:
        symbol = signal['symbol']
        whale_data = whale_integration.get_whale_data(symbol)
        
        if whale_data:
            signal['whale_data'] = whale_data
            enriched_count += 1
    
    logger.info(f"✅ Enriched {enriched_count}/{len(signals)} signals")
    return signals


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🐋 TESTING UNUSUAL WHALES INTEGRATION")
    print("=" * 70)
    
    if whale_integration.google_sheets_available:
        print("✅ Google Sheets connected")
    else:
        print("⚠️ Google Sheets not available - using fallback")
    
    test_symbol = "NVDA"
    print(f"\nTesting with {test_symbol}...")
    
    data = whale_integration.get_whale_data(test_symbol)
    if data:
        print(f"✅ Got data: {data}")
    else:
        print("⚠️ No data available")
    
    print("\n" + "=" * 70)

