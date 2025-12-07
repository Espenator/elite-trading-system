"""
API Routes for ML Configuration
Allows frontend to save and retrieve ML model settings
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import json
import os

router = APIRouter(prefix="/api/ml", tags=["ml-config"])

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "ml_config.json")


class MLConfig(BaseModel):
    confidenceThreshold: int
    volumeWeight: int
    rvolWeight: int
    darkPoolWeight: int
    optionsFlowWeight: int
    lastUpdated: str


@router.get("/config", response_model=MLConfig)
async def get_ml_config():
    """Get current ML configuration"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config
        
        # Default config
        return {
            "confidenceThreshold": 80,
            "volumeWeight": 30,
            "rvolWeight": 25,
            "darkPoolWeight": 25,
            "optionsFlowWeight": 20,
            "lastUpdated": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading ML config: {str(e)}")


@router.post("/config", response_model=MLConfig)
async def update_ml_config(config: MLConfig):
    """Update ML configuration"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        config_dict = config.dict()
        config_dict["lastUpdated"] = datetime.now().isoformat()
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        return config_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving ML config: {str(e)}")


@router.post("/config/reset")
async def reset_ml_config():
    """Reset ML configuration to defaults"""
    default_config = {
        "confidenceThreshold": 80,
        "volumeWeight": 30,
        "rvolWeight": 25,
        "darkPoolWeight": 25,
        "optionsFlowWeight": 20,
        "lastUpdated": datetime.now().isoformat()
    }
    
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)
        return {"message": "ML config reset to defaults", "config": default_config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting config: {str(e)}")
