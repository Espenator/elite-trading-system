from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # Scanner settings
    scan_interval: int = 300  # 5 minutes
    watchlist: List[str] = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMD"]
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
