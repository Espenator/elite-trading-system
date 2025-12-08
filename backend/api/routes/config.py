"""
Configuration API Routes
Endpoints for system configuration and settings
"""
from fastapi import APIRouter
import os

router = APIRouter()

@router.get("/config")
async def get_config():
    """Get system configuration"""
    return {
        'version': '1.0.0',
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'features': {
            'ml_predictions': True,
            'real_time_updates': True,
            'paper_trading': True,
            'sound_alerts': True
        }
    }
