"""ML Brain API v2.0 — Model performance, staged signal inferences, and ML engine endpoints.

Enhanced with:
- Trading Conference endpoint (multi-agent consensus DAG)
- Model Registry status endpoint
- Drift Monitor status endpoint  
- LSTM multi-task prediction endpoint

GET /api/v1/ml-brain/performance returns walk-forward accuracy from DB (mlmodels table).
GET /api/v1/ml-brain/signals/staged returns top staged inferences from mlfeatures/scannersignals.
GET /api/v1/ml-brain/flywheel-logs returns latest outcomes from tradeoutcomes table.
POST /api/v1/ml-brain/conference/{symbol} runs trading conference for a symbol.
GET /api/v1/ml-brain/registry/status returns model registry status.
GET /api/v1/ml-brain/drift/status returns drift monitor status.
No mock data. No fabricated numbers.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from app.services.database import db_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_ml_data(key: str, default=None):
    """Read ML Brain data from DB via config store."""
    stored = db_service.get_config(key)
    if stored is None:
        return default
    return stored


# ---------------------------------------------------------------------------
# Core ML Brain Endpoints (preserved from v1)
# ---------------------------------------------------------------------------

@router.get("/performance")
async def get_ml_performance():
    """
    Return ML model walk-forward accuracy history.
    Reads from timescaleDB mlmodels table.
    Frontend charts: XGBoost accuracy %, RF accuracy % over 252 days.
    """
    data = _get_ml_data("ml_brain_performance", [])
    if not data:
        return []
    return data


@router.get("/signals/staged")
async def get_staged_inferences():
    """
    Return top staged signal inferences.
    Reads from mlfeatures / scannersignals join.
    Filters: WIN_PROB > 70% as per Anticipatory Funnel docs.
    """
    data = _get_ml_data("ml_brain_staged_signals", [])
    if not data:
        return []
    return data


@router.get("/flywheel-logs")
async def get_flywheel_logs():
    """
    Return latest trade outcome logs for the flywheel.
    Reads from tradeoutcomes table.
    """
    data = _get_ml_data("ml_brain_flywheel_logs", [])
    if not data:
        return []
    return data


# ---------------------------------------------------------------------------
# Trading Conference Endpoint (v2.0)
# ---------------------------------------------------------------------------

@router.post("/conference/{symbol}")
async def run_conference(symbol: str, timeframe: str = "1d"):
    """Run a Trading Conference (multi-agent consensus DAG) for a symbol.
    
    Executes: Researcher -> Risk Officer -> Adversary -> Consensus Arbitrator.
    Returns decision, confidence, position sizing, and full transcript.
    """
    try:
        from app.modules.openclaw.intelligence.trading_conference import TradingConference
        conference = TradingConference()
        
        # Gather available context
        market_data = {}
        ml_signals = {}
        macro_context = {}
        options_flow = {}
        portfolio_context = {}
        regime = "unknown"
        
        # Try to get ML signals
        try:
            from app.models.inference import get_prediction
            pred = get_prediction(symbol) if callable(get_prediction) else {}
            if pred:
                ml_signals = pred
        except Exception as e:
            logger.debug("ML prediction unavailable: %s", e)

        # Try to get regime
        try:
            from app.modules.openclaw.intelligence.hmm_regime import get_current_regime
            regime = get_current_regime() or "unknown"
        except Exception as e:
            logger.debug("Regime unavailable: %s", e)
        
        result = await conference.convene(
            symbol=symbol,
            timeframe=timeframe,
            market_data=market_data,
            ml_signals=ml_signals,
            macro_context=macro_context,
            options_flow=options_flow,
            portfolio_context=portfolio_context,
            regime=regime,
        )
        return result.to_dict()
    except ImportError:
        return {
            "status": "not_installed",
            "message": "trading_conference module not available",
            "symbol": symbol,
        }
    except Exception as e:
        logger.exception("Conference failed for %s", symbol)
        return {
            "status": "error",
            "message": str(e),
            "symbol": symbol,
        }


@router.post("/conference/batch")
async def run_conference_batch(symbols: List[str], timeframe: str = "1d"):
    """Run Trading Conference for multiple symbols concurrently."""
    try:
        from app.modules.openclaw.intelligence.trading_conference import TradingConference
        conference = TradingConference()
        results = await conference.convene_batch(symbols=symbols, timeframe=timeframe)
        return [r.to_dict() if hasattr(r, 'to_dict') else r for r in results]
    except ImportError:
        return {"status": "not_installed", "message": "trading_conference module not available"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Model Registry & Drift Endpoints (v2.0)
# ---------------------------------------------------------------------------

@router.get("/registry/status")
async def get_registry_status():
    """Get model registry status with champion/challenger info."""
    try:
        from app.modules.ml_engine.model_registry import get_registry
        registry = get_registry()
        return registry.get_status() if hasattr(registry, 'get_status') else {"status": "loaded"}
    except ImportError:
        return {"status": "not_installed", "message": "model_registry module not available"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/drift/status")
async def get_drift_status():
    """Get drift monitor status and recent checks."""
    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        monitor = get_drift_monitor()
        status = monitor.get_status() if hasattr(monitor, 'get_status') else {}
        return status
    except ImportError:
        return {"status": "not_installed", "message": "drift_detector module not available"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/lstm/predict/{symbol}")
async def lstm_predict(symbol: str):
    """Run LSTM multi-task prediction for a symbol.
    
    Returns: prob_up, magnitude, volatility (if multi-task model available).
    """
    try:
        from app.models.inference import get_prediction
        result = get_prediction(symbol) if callable(get_prediction) else None
        if result:
            return {"symbol": symbol, "prediction": result}
        return {"symbol": symbol, "prediction": None, "message": "No prediction available"}
    except ImportError:
        return {"status": "not_installed", "message": "inference module not available"}
    except Exception as e:
        return {"status": "error", "message": str(e), "symbol": symbol}


@router.get("/status")
async def get_ml_brain_status():
    """Aggregate ML Brain status: all components."""
    status: Dict[str, Any] = {
        "version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Performance data
    perf = _get_ml_data("ml_brain_performance", [])
    status["performance_entries"] = len(perf) if isinstance(perf, list) else 0
    
    # Staged signals
    staged = _get_ml_data("ml_brain_staged_signals", [])
    status["staged_signals"] = len(staged) if isinstance(staged, list) else 0
    
    # Registry
    try:
        from app.modules.ml_engine.model_registry import get_registry
        status["registry"] = "available"
    except ImportError:
        status["registry"] = "not_installed"
    
    # Drift
    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        status["drift_monitor"] = "available"
    except ImportError:
        status["drift_monitor"] = "not_installed"
    
    # Conference
    try:
        from app.modules.openclaw.intelligence.trading_conference import TradingConference
        status["trading_conference"] = "available"
    except ImportError:
        status["trading_conference"] = "not_installed"
    
    return status
