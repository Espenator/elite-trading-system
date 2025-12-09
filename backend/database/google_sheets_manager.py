"""
Google Sheets Manager - Read/Write using gspread
"""

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import List, Dict, Optional
from pathlib import Path
import os
from dotenv import load_dotenv

from backend.core.logger import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

class GoogleSheetsManager:
    """
    Manages all Google Sheets operations
    """
    
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.connected = False
        
        try:
            self._connect()
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
    
    def _connect(self):
        """Connect to Google Sheets"""
        # Get credentials path
        creds_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE')
        spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
        
        if not creds_file or not spreadsheet_id:
            logger.warning("Google Sheets credentials not configured in .env")
            return
        
        creds_path = Path(__file__).parent.parent / creds_file
        
        if not creds_path.exists():
            logger.warning(f"Credentials file not found: {creds_path}")
            return
        
        # Authenticate
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        self.client = gspread.authorize(creds)
        
        # Open spreadsheet
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        
        self.connected = True
        logger.info(f"✅ Connected to Google Sheets: {self.spreadsheet.title}")
    
    def write_signals(self, signals: List[Dict]):
        """
        Write signals to 'Scan Results (Top 40)' tab
        
        Args:
            signals: List of signal dictionaries
        """
        if not self.connected:
            logger.warning("Not connected to Google Sheets")
            return
        
        try:
            # Get or create worksheet
            try:
                worksheet = self.spreadsheet.worksheet('Scan Results (Top 40)')
            except:
                worksheet = self.spreadsheet.add_worksheet(
                    title='Scan Results (Top 40)',
                    rows=100,
                    cols=20
                )
            
            # Prepare data
            rows = [['Symbol', 'Direction', 'Score', 'Velez', 'Explosive', 'Fresh', 
                     'Entry', 'Stop', 'Target', 'Timestamp']]
            
            for signal in signals[:40]:  # Top 40 only
                velez = signal['velez_score']['composite']
                explosive = '✅' if signal['explosive_signal'] else '❌'
                fresh_mins = signal['fresh_ignition']['minutes_since_breakout']
                fresh_icon = '🟢' if fresh_mins < 30 else '🟡'
                
                rows.append([
                    signal['symbol'],
                    signal['direction'],
                    f"{signal['score']:.1f}",
                    f"{velez:.1f}",
                    explosive,
                    f"{fresh_icon} {fresh_mins}m",
                    f"${signal['entry_price']:.2f}",
                    f"${signal['stop_price']:.2f}",
                    f"${signal['target_price']:.2f}",
                    signal['timestamp']
                ])
            
            # Clear and update
            worksheet.clear()
            worksheet.update('A1', rows)
            
            logger.info(f"✅ Wrote {len(signals)} signals to Google Sheets")
            
        except Exception as e:
            logger.error(f"Failed to write signals: {e}")
    
    def write_positions(self, positions: List[Dict]):
        """
        Write open positions to 'Paper Positions' tab
        
        Args:
            positions: List of position dictionaries
        """
        if not self.connected:
            return
        
        try:
            # Get or create worksheet
            try:
                worksheet = self.spreadsheet.worksheet('Paper Positions')
            except:
                worksheet = self.spreadsheet.add_worksheet(
                    title='Paper Positions',
                    rows=50,
                    cols=15
                )
            
            # Prepare data
            rows = [['Symbol', 'Direction', 'Shares', 'Entry', 'Current', 'Stop',
                     'P&L', 'R-Multiple', 'Entry Time']]
            
            for pos in positions:
                rows.append([
                    pos['symbol'],
                    pos['direction'],
                    pos['shares'],
                    f"${pos['entry_price']:.2f}",
                    f"${pos['current_price']:.2f}",
                    f"${pos['stop_loss']:.2f}",
                    f"${pos['unrealized_pnl']:.2f}",
                    f"{pos['r_multiple']:.2f}R",
                    pos['entry_time']
                ])
            
            # Clear and update
            worksheet.clear()
            worksheet.update('A1', rows)
            
            logger.debug(f"Updated {len(positions)} positions in Google Sheets")
            
        except Exception as e:
            logger.error(f"Failed to write positions: {e}")
    
    def append_trade(self, trade: Dict):
        """
        Append completed trade to 'Trade History' tab
        
        Args:
            trade: Trade dictionary
        """
        if not self.connected:
            return
        
        try:
            # Get or create worksheet
            try:
                worksheet = self.spreadsheet.worksheet('Trade History')
            except:
                worksheet = self.spreadsheet.add_worksheet(
                    title='Trade History',
                    rows=1000,
                    cols=15
                )
                # Add header
                worksheet.update('A1', [['Date', 'Symbol', 'Direction', 'Entry', 'Exit',
                                         'Shares', 'P&L', 'R-Multiple', 'Outcome', 'Reason']])
            
            # Append row
            row = [
                trade.get('exit_time', trade.get('entry_time')),
                trade['symbol'],
                trade['direction'],
                f"${trade['entry_price']:.2f}",
                f"${trade['exit_price']:.2f}",
                trade['shares'],
                f"${trade['pnl']:.2f}",
                f"{trade['r_multiple']:.2f}R",
                trade['outcome'],
                trade.get('reason', 'N/A')
            ]
            
            worksheet.append_row(row)
            
            logger.info(f"Trade appended to history: {trade['symbol']}")
            
        except Exception as e:
            logger.error(f"Failed to append trade: {e}")
    
    def write_ai_memory(self, insight: Dict):
        """
        Write AI learning insight to 'AI Learning Memory' tab
        
        Args:
            insight: AI insight dictionary
        """
        if not self.connected:
            return
        
        try:
            # Get or create worksheet
            try:
                worksheet = self.spreadsheet.worksheet('AI Learning Memory')
            except:
                worksheet = self.spreadsheet.add_worksheet(
                    title='AI Learning Memory',
                    rows=500,
                    cols=10
                )
                # Add header
                worksheet.update('A1', [['Timestamp', 'Type', 'Finding', 'Confidence',
                                         'Recommendation', 'Result']])
            
            # Append row
            row = [
                insight['timestamp'],
                insight['type'],
                insight['finding'],
                insight['confidence'],
                insight['recommendation'],
                insight.get('result', 'Testing...')
            ]
            
            worksheet.append_row(row)
            
            logger.info(f"AI insight written: {insight['type']}")
            
        except Exception as e:
            logger.error(f"Failed to write AI insight: {e}")

# Global instance
sheets_manager = GoogleSheetsManager()

# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def write_signals(signals: List[Dict]):
    """Write signals to Google Sheets"""
    sheets_manager.write_signals(signals)

def write_positions(positions: List[Dict]):
    """Write positions to Google Sheets"""
    sheets_manager.write_positions(positions)

def log_trade(trade: Dict):
    """Log trade to Google Sheets"""
    sheets_manager.append_trade(trade)

def log_ai_insight(insight: Dict):
    """Log AI insight to Google Sheets"""
    sheets_manager.write_ai_memory(insight)

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    print("\n📊 Testing Google Sheets connection...")
    
    if sheets_manager.connected:
        print(f"✅ Connected to: {sheets_manager.spreadsheet.title}")
        
        # Test write signals
        test_signals = [{
            'symbol': 'AAPL',
            'direction': 'LONG',
            'score': 92.5,
            'velez_score': {'composite': 85.0},
            'explosive_signal': True,
            'fresh_ignition': {'minutes_since_breakout': 12},
            'entry_price': 180.0,
            'stop_price': 175.0,
            'target_price': 190.0,
            'timestamp': '2024-12-04T10:00:00'
        }]
        
        write_signals(test_signals)
        print("✅ Test signal written")
    else:
        print("❌ Not connected - check .env file")
