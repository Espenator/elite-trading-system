"""Cluster status API — /api/v1/cluster

Exposes cluster health: nodes, streams, GPU utilization, model pinning,
telemetry, and LLM dispatcher state.

Part of #39 — E0.5 + E1.7
"""
import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/cluster", tags=["cluster"])


@router.get("/status")
async def cluster_status():
    """Return full cluster health: nodes, streams, GPU utilization,
    model pinning, dispatcher, telemetry, and Redis bridge status."""
    from app.services.node_discovery import get_node_discovery
    discovery = get_node_discovery()
    status = discovery.get_cluster_status()

    # Enrich with Redis MessageBus bridge status
    try:
        from app.core.message_bus import get_message_bus
        bus_metrics = get_message_bus().get_metrics()
        status["redis"] = bus_metrics.get("redis", {})
    except Exception:
        status["redis"] = {"connected": False, "error": "message_bus unavailable"}

    return status


@router.get("/telemetry")
async def cluster_telemetry():
    """Return raw GPU telemetry for all nodes."""
    try:
        from app.services.gpu_telemetry import get_gpu_telemetry
        return get_gpu_telemetry().get_status()
    except Exception as e:
        logger.warning("GPU telemetry unavailable: %s", e)
        return {"error": "Service unavailable", "enabled": False}


@router.get("/dispatcher")
async def cluster_dispatcher():
    """Return LLM dispatcher state: per-node health, routing stats."""
    try:
        from app.services.llm_dispatcher import get_llm_dispatcher
        return get_llm_dispatcher().get_status()
    except Exception as e:
        logger.warning("LLM dispatcher unavailable: %s", e)
        return {"error": "Service unavailable", "enabled": False}


@router.get("/pinning")
async def cluster_pinning():
    """Return model pinning registry: which models/tasks are pinned where."""
    try:
        from app.services.model_pinning import get_model_pinning
        return get_model_pinning().get_status()
    except Exception as e:
        logger.warning("Model pinning unavailable: %s", e)
        return {"error": "Service unavailable"}
