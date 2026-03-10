"""Features API — compute and retrieve feature vectors with versioning support.

GET  /api/v1/features/latest?symbol=X&timeframe=1d&pipeline_version=2.0.0  → latest stored features
POST /api/v1/features/compute  {symbol, timeframe}   → compute + persist + return
GET  /api/v1/features/versions?symbol=X&timeframe=1d → available pipeline versions
GET  /api/v1/features/compatibility?symbol=X&version=2.0.0 → check version compatibility
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.security import require_auth
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class FeatureComputeRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    pipeline_version: Optional[str] = None


@router.get("/latest")
async def get_latest_features(
    symbol: str,
    timeframe: str = "1d",
    pipeline_version: Optional[str] = Query(None, description="Filter by specific pipeline version")
):
    """Retrieve the most recent stored feature vector for a symbol.

    Args:
        symbol: Stock symbol
        timeframe: Timeframe (default: 1d)
        pipeline_version: Optional pipeline version filter
    """
    try:
        from app.data.feature_store import feature_store
        result = feature_store.get_latest_features(symbol, timeframe, pipeline_version)
        if result is None:
            return {
                "status": "not_found",
                "symbol": symbol,
                "timeframe": timeframe,
                "pipeline_version": pipeline_version
            }
        return {"status": "ok", **result}
    except Exception as e:
        logger.exception("Error fetching features for %s", symbol)
        return {"status": "error", "message": str(e)}


@router.post("/compute", dependencies=[Depends(require_auth)])
async def compute_features(req: FeatureComputeRequest):
    """Compute feature vector for a symbol, persist to store, and return."""
    try:
        from app.features.feature_aggregator import aggregate
        fv = await aggregate(req.symbol, timeframe=req.timeframe, persist=True)
        return {"status": "ok", **fv.to_dict()}
    except Exception as e:
        logger.exception("Error computing features for %s", req.symbol)
        return {"status": "error", "message": str(e)}


@router.get("/versions")
async def get_available_versions(
    symbol: Optional[str] = Query(None, description="Filter by specific symbol"),
    timeframe: str = Query("1d", description="Timeframe filter")
):
    """Get all available pipeline versions in the feature store.

    Returns version statistics including record counts, date ranges, and feature counts.
    """
    try:
        from app.data.feature_store import feature_store
        versions = feature_store.get_available_versions(symbol, timeframe)
        return {
            "status": "ok",
            "symbol": symbol,
            "timeframe": timeframe,
            "versions": versions
        }
    except Exception as e:
        logger.exception("Error fetching available versions")
        return {"status": "error", "message": str(e)}


@router.get("/compatibility")
async def check_version_compatibility(
    symbol: str,
    version: str,
    timeframe: str = Query("1d", description="Timeframe filter")
):
    """Check if features exist for a specific pipeline version.

    Returns compatibility information including record counts and date ranges.
    """
    try:
        from app.data.feature_store import feature_store
        compat = feature_store.check_version_compatibility(version, symbol, timeframe)
        return {"status": "ok", **compat}
    except Exception as e:
        logger.exception("Error checking version compatibility")
        return {"status": "error", "message": str(e)}
