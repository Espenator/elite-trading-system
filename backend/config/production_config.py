"""
Production Configuration
Environment-specific settings for deployment
"""
import os
from typing import Optional

class Config:
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    DEBUG = ENVIRONMENT == 'development'
    
    # API Settings
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 8000))
    
    # Database
    DB_PATH = os.getenv('DB_PATH', 'data/elite_trader.db')
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL = int(os.getenv('WS_HEARTBEAT_INTERVAL', 30))
    WS_MAX_CONNECTIONS = int(os.getenv('WS_MAX_CONNECTIONS', 100))
    
    # Signal Generation
    SIGNAL_SCAN_INTERVAL = int(os.getenv('SIGNAL_SCAN_INTERVAL', 60))
    MAX_SIGNALS_PER_SCAN = int(os.getenv('MAX_SIGNALS_PER_SCAN', 100))
    
    # Performance
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', 4))
    CACHE_TTL = int(os.getenv('CACHE_TTL', 300))
    
    # Security
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:3001').split(',')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/elite_trader.log')
    
    @classmethod
    def get_config(cls) -> dict:
        """Get all config as dictionary"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and key.isupper()
        }
    
    @classmethod
    def print_config(cls):
        """Print current configuration"""
        print("\n" + "="*50)
        print("??  ELITE TRADER CONFIGURATION")
        print("="*50)
        for key, value in cls.get_config().items():
            # Mask sensitive values
            display_value = value
            if 'KEY' in key or 'SECRET' in key or 'PASSWORD' in key:
                display_value = '***REDACTED***'
            print(f"{key}: {display_value}")
        print("="*50 + "\n")

config = Config()
