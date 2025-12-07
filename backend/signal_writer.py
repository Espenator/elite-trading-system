"""
Signal Writer Service - Connects signal generation engines to database
Writes signals from composite_scorer, ignition_detector, etc. to SQLite
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "trading.db")


class SignalWriter:
    """Writes trading signals to database from signal generation engines"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self._initialize_database()
    
    def _initialize_database(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                tier TEXT NOT NULL,
                current_price REAL,
                net_change REAL,
                percent_change REAL,
                rvol REAL,
                global_confidence INTEGER,
                direction TEXT,
                factors TEXT,
                predictions TEXT,
                model_agreement REAL,
                volume REAL,
                market_cap REAL,
                timestamp TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT,
                db_latency INTEGER,
                ingestion_rate INTEGER,
                tier_counts TEXT,
                market_regime TEXT,
                timestamp TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def write_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        Write a single signal to database
        
        Expected signal_data structure:
        {
            'ticker': 'NVDA',
            'tier': 'CORE',  # or 'HOT' or 'LIQUID'
            'current_price': 875.30,
            'net_change': 12.45,
            'percent_change': 1.44,
            'rvol': 2.3,
            'global_confidence': 92,
            'direction': 'long',
            'factors': [
                {'name': 'Volume Surge', 'impact': 0.8, 'type': 'flow'},
                {'name': 'Compression', 'impact': 0.9, 'type': 'technical'}
            ],
            'predictions': {
                '1H': {'priceTarget': 880.0, 'confidence': 0.85},
                '1D': {'priceTarget': 920.0, 'confidence': 0.75}
            },
            'model_agreement': 0.88,
            'volume': 45123678.0,
            'market_cap': 2150000000000.0
        }
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            signal_id = f"{signal_data['ticker']}_{int(datetime.now().timestamp())}"
            
            cursor.execute("""
                INSERT OR REPLACE INTO signals (
                    id, ticker, tier, current_price, net_change, percent_change,
                    rvol, global_confidence, direction, factors, predictions,
                    model_agreement, volume, market_cap, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id,
                signal_data['ticker'],
                signal_data.get('tier', 'LIQUID'),
                signal_data['current_price'],
                signal_data.get('net_change', 0.0),
                signal_data.get('percent_change', 0.0),
                signal_data.get('rvol', 1.0),
                signal_data.get('global_confidence', 50),
                signal_data.get('direction', 'long'),
                json.dumps(signal_data.get('factors', [])),
                json.dumps(signal_data.get('predictions', {})),
                signal_data.get('model_agreement', 0.5),
                signal_data.get('volume', 0.0),
                signal_data.get('market_cap', 0.0),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error writing signal: {e}")
            return False
    
    def write_bulk_signals(self, signals: List[Dict[str, Any]]) -> int:
        """Write multiple signals at once, returns count of successful writes"""
        successful = 0
        for signal in signals:
            if self.write_signal(signal):
                successful += 1
        return successful
    
    def update_system_health(self, tier_counts: Dict[str, int], market_regime: str = "Unknown"):
        """Update system health metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO system_health (
                    status, db_latency, ingestion_rate, tier_counts, market_regime, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "operational",
                12,
                len(tier_counts),
                json.dumps(tier_counts),
                market_regime,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error updating system health: {e}")


# Singleton instance
signal_writer = SignalWriter()
