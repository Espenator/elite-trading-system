"""Cluster status API — /api/v1/cluster

Exposes cluster health: nodes, streams, GPU utilization.

Part of #39 — E0.5
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/cluster", tags=["cluster"])


@router.get("/status")
async def cluster_status():
    """Return cluster health: nodes, streams, GPU utilization."""
    from app.services.node_discovery import get_node_discovery
    discovery = get_node_discovery()
    return discovery.get_cluster_status()
