# app/core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # App
    app_name: str = "Elite Trading System API"
    debug: bool = False
    
    # Database
    database_url: str = "sqlite:///./finviz_stocks.db"
    
    # Finviz
    finviz_use_elite: bool = False
    default_filters: str = "cap_midover,sh_avgvol_o500,sh_price_o10"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
