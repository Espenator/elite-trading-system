"""Cognitive Telemetry API — Embodier Trader Being Intelligence (ETBI) metrics.

Provides the Research Dashboard with cognitive quality metrics from the council.

Glass Box cockpit additions:
  GET  /api/v1/cognitive/mode          -> Current cognitive mode (explore/exploit/defensive)
  GET  /api/v1/cognitive/brain-health  -> Brain service health summary
"""
from fastapi import APIRouter, HTTPException
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard")
async def get_dashboard():
    """Get aggregated cognitive telemetry for the Research Dashboard.

    Returns hypothesis diversity, agent agreement, confidence calibration,
    mode distribution, latency profiles, and exploration outcomes.
    """
    try:
        from app.services.cognitive_telemetry import get_cognitive_dashboard
        return get_cognitive_dashboard()
    except Exception as e:
        logger.error("Failed to get cognitive dashboard: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots")
async def get_recent_snapshots(limit: int = 50):
    """Get recent cognitive snapshots for time-series visualization."""
    try:
        from app.services.cognitive_telemetry import _get_store
        store = _get_store()
        snapshots = store.get("snapshots", [])
        return {"snapshots": snapshots[-limit:], "total": len(snapshots)}
    except Exception as e:
        logger.error("Failed to get cognitive snapshots: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calibration")
async def get_calibration():
    """Get confidence calibration data (Brier score + prediction history)."""
    try:
        from app.services.cognitive_telemetry import _get_store
        store = _get_store()
        calibration = store.get("calibration", {})
        predictions = calibration.get("predictions", [])

        brier = None
        if predictions:
            brier = sum((p["predicted_conf"] - p["actual"]) ** 2 for p in predictions) / len(predictions)

        return {
            "brier_score": round(brier, 4) if brier is not None else None,
            "total_predictions": len(predictions),
            "recent_predictions": predictions[-20:],
        }
    except Exception as e:
        logger.error("Failed to get calibration data: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-outcome")
async def record_trade_outcome(payload: dict):
    """Record a trade outcome for confidence calibration.

    Body: { "council_decision_id": "...", "outcome": "win"|"loss"|"scratch", "r_multiple": 1.5 }
    """
    try:
        from app.services.cognitive_telemetry import record_outcome
        record_outcome(
            council_decision_id=payload["council_decision_id"],
            outcome=payload["outcome"],
            r_multiple=payload.get("r_multiple", 0),
        )
        return {"status": "recorded"}
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing field: {e}")
    except Exception as e:
        logger.error("Failed to record outcome: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Glass Box: Cognitive mode + brain health
# ---------------------------------------------------------------------------
@router.get("/mode")
async def get_cognitive_mode():
    """Current cognitive mode (explore / exploit / defensive) with details.

    Pulls from the most recent council decision's cognitive metadata,
    plus exploration rate and mode switch history.
    """
    mode_info = {
        "mode": "exploit",
        "exploration_rate": 0.1,
        "mode_switches_24h": 0,
        "hypothesis_diversity": 0.0,
        "agent_agreement": 0.0,
    }

    # Try latest council decision
    try:
        from app.api.v1.council import _latest_decision
        if _latest_decision:
            cog = _latest_decision.get("cognitive") or {}
            mode_info["mode"] = cog.get("mode", "exploit")
            mode_info["hypothesis_diversity"] = cog.get("hypothesis_diversity", 0)
            mode_info["agent_agreement"] = cog.get("agent_agreement", 0)
            mode_info["mode_switches_24h"] = cog.get("mode_switches_24h", 0)
    except Exception:
        pass

    # Try cognitive telemetry store for exploration rate
    try:
        from app.services.cognitive_telemetry import _get_store
        store = _get_store()
        mode_info["exploration_rate"] = store.get("exploration_rate", 0.1)
    except Exception:
        pass

    return mode_info


@router.get("/brain-health")
async def get_brain_health():
    """Brain service health summary for Glass Box cockpit.

    Aggregates: ML model status, drift detection, cognitive calibration,
    council gate throughput, and memory bank stats.
    """
    health = {
        "ml_models": {"status": "unknown"},
        "drift_monitor": {"status": "unknown"},
        "calibration": {"brier_score": None},
        "memory_bank": {"status": "unknown"},
        "heuristic_engine": {"status": "unknown"},
        "council_gate": {"status": "unknown"},
    }

    # ML model registry
    try:
        from app.modules.ml_engine.model_registry import get_registry
        reg = get_registry()
        health["ml_models"] = reg.get_status() if hasattr(reg, "get_status") else {"status": "loaded"}
    except Exception:
        health["ml_models"] = {"status": "unavailable"}

    # Drift monitor
    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        mon = get_drift_monitor()
        health["drift_monitor"] = mon.get_status() if hasattr(mon, "get_status") else {"status": "loaded"}
    except Exception:
        health["drift_monitor"] = {"status": "unavailable"}

    # Calibration (Brier score)
    try:
        from app.services.cognitive_telemetry import _get_store
        store = _get_store()
        preds = store.get("calibration", {}).get("predictions", [])
        if preds:
            brier = sum((p["predicted_conf"] - p["actual"]) ** 2 for p in preds) / len(preds)
            health["calibration"] = {"brier_score": round(brier, 4), "sample_size": len(preds)}
    except Exception:
        pass

    # Memory bank stats
    try:
        from app.knowledge.memory_bank import get_memory_bank
        mb = get_memory_bank()
        health["memory_bank"] = mb.get_stats()
    except Exception:
        health["memory_bank"] = {"status": "unavailable"}

    # Heuristic engine stats
    try:
        from app.knowledge.heuristic_engine import get_heuristic_engine
        he = get_heuristic_engine()
        active = he.get_active_heuristics()
        health["heuristic_engine"] = {
            "status": "ok",
            "active_heuristics": len(active),
        }
    except Exception:
        health["heuristic_engine"] = {"status": "unavailable"}

    # Council gate
    try:
        import app.main as main_mod
        gate = getattr(main_mod, "_council_gate", None)
        if gate:
            health["council_gate"] = gate.get_status()
        else:
            health["council_gate"] = {"status": "not_running"}
    except Exception:
        pass

    return health


# ---------------------------------------------------------------------------
# Glass Box: Knowledge system endpoints
# ---------------------------------------------------------------------------
@router.get("/heuristics")
async def get_heuristics(agent_name: str = None, regime: str = None):
    """Pattern Memory Viewer — active heuristics from the heuristic engine."""
    try:
        from app.knowledge.heuristic_engine import get_heuristic_engine
        he = get_heuristic_engine()
        heuristics = he.get_active_heuristics(agent_name=agent_name, regime=regime)
        return {
            "heuristics": [h.to_dict() if hasattr(h, "to_dict") else h for h in heuristics],
            "total": len(heuristics),
        }
    except Exception as e:
        logger.error("Failed to get heuristics: %s", e)
        return {"heuristics": [], "total": 0, "error": str(e)}


@router.get("/similar-cases")
async def get_similar_cases(agent_name: str = "strategy", symbol: str = "SPY", regime: str = ""):
    """Similar Case Viewer — recall similar past situations from memory bank."""
    try:
        from app.knowledge.memory_bank import get_memory_bank
        mb = get_memory_bank()
        context = {"symbol": symbol}
        cases = mb.recall_similar(
            agent_name=agent_name,
            current_context=context,
            regime=regime,
            top_k=10,
        )
        return {"cases": cases, "total": len(cases)}
    except Exception as e:
        logger.error("Failed to recall similar cases: %s", e)
        return {"cases": [], "total": 0, "error": str(e)}


@router.get("/drift-status")
async def get_drift_status():
    """Drift Detection Panel — model drift metrics."""
    try:
        from app.modules.ml_engine.drift_detector import get_drift_monitor
        mon = get_drift_monitor()
        status = mon.get_status() if hasattr(mon, "get_status") else {}
        return {"status": "ok", "drift": status}
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}
