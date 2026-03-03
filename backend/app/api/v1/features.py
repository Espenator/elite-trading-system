"""Features API — compute and retrieve feature vectors.

GET  /api/v1/features/latest?symbol=X&timeframe=1d  → latest stored features
POST /api/v1/features/compute  {symbol, timeframe}   → compute + persist + return
"""
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class FeatureComputeRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"


@router.get("/latest")
async def get_latest_features(symbol: str, timeframe: str = "1d"):
    """Retrieve the most recent stored feature vector for a symbol."""
    try:
        from app.data.feature_store import feature_store
        result = feature_store.get_latest_features(symbol, timeframe)
        if result is None:
            return {"status": "not_found", "symbol": symbol, "timeframe": timeframe}
        return {"status": "ok", **result}
    except Exception as e:
        logger.exception("Error fetching features for %s", symbol)
        return {"status": "error", "message": str(e)}


@router.post("/compute")
async def compute_features(req: FeatureComputeRequest):
    """Compute feature vector for a symbol, persist to store, and return."""
    try:
        from app.features.feature_aggregator import aggregate
        fv = await aggregate(req.symbol, timeframe=req.timeframe, persist=True)
        return {"status": "ok", **fv.to_dict()}
    except Exception as e:
        logger.exception("Error computing features for %s", req.symbol)
        return {"status": "error", "message": str(e)}
