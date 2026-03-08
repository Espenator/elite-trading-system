"""Cluster status API — /api/v1/cluster

Exposes cluster health: nodes, streams, GPU utilization, model pinning,
telemetry, and LLM dispatcher state.

Part of #39 — E0.5 + E1.7
"""
from fastapi import APIRouter

router = APIRouter(tags=["cluster"])


@router.get("/status")
async def cluster_status():
    """Return full cluster health: nodes, streams, GPU utilization,
    model pinning, dispatcher, telemetry."""
    from app.services.node_discovery import get_node_discovery
    discovery = get_node_discovery()
    return discovery.get_cluster_status()


@router.get("/nodes")
async def cluster_nodes():
    """Return all registered compute nodes with capabilities and health."""
    from app.services.node_registry import get_node_registry
    return get_node_registry().to_status_dict()


@router.get("/telemetry")
async def cluster_telemetry():
    """Return raw GPU telemetry for all nodes."""
    try:
        from app.services.gpu_telemetry import get_gpu_telemetry
        return get_gpu_telemetry().get_status()
    except Exception as e:
        return {"error": str(e), "enabled": False}


@router.get("/dispatcher")
async def cluster_dispatcher():
    """Return LLM dispatcher state: per-node health, routing stats."""
    try:
        from app.services.llm_dispatcher import get_llm_dispatcher
        return get_llm_dispatcher().get_status()
    except Exception as e:
        return {"error": str(e), "enabled": False}


@router.get("/pinning")
async def cluster_pinning():
    """Return model pinning registry: which models/tasks are pinned where."""
    try:
        from app.services.model_pinning import get_model_pinning
        return get_model_pinning().get_status()
    except Exception as e:
        return {"error": str(e)}
