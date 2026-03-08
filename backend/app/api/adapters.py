"""API endpoints for data ingestion adapter management."""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.services.ingestion import get_adapter_registry

router = APIRouter()


@router.get("/adapters", response_model=List[str])
async def list_adapters():
    """List all registered adapters.

    Returns:
        List of adapter IDs
    """
    registry = get_adapter_registry()
    return registry.get_adapter_ids()


@router.get("/adapters/health")
async def get_adapters_health():
    """Get health status for all adapters.

    Returns:
        Health summary with status for each adapter
    """
    registry = get_adapter_registry()
    return registry.get_health_summary()


@router.get("/adapters/{adapter_id}/health")
async def get_adapter_health(adapter_id: str):
    """Get health status for a specific adapter.

    Args:
        adapter_id: Unique identifier for the adapter

    Returns:
        Health status for the adapter
    """
    registry = get_adapter_registry()
    health = registry.get_health(adapter_id)

    if not health:
        raise HTTPException(status_code=404, detail=f"Adapter not found: {adapter_id}")

    return health[adapter_id].to_dict()


@router.post("/adapters/{adapter_id}/run")
async def run_adapter(adapter_id: str):
    """Manually trigger an adapter run.

    Args:
        adapter_id: Unique identifier for the adapter

    Returns:
        Number of events ingested
    """
    registry = get_adapter_registry()

    try:
        count = await registry.run_adapter(adapter_id)
        return {
            "adapter_id": adapter_id,
            "status": "success",
            "events_ingested": count
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Adapter run failed: {str(e)}")


@router.post("/adapters/run-all")
async def run_all_adapters():
    """Manually trigger all adapters to run.

    Returns:
        Results for each adapter
    """
    registry = get_adapter_registry()
    results = await registry.run_all()

    return {
        "status": "completed",
        "results": results
    }


@router.post("/adapters/{adapter_id}/reset-checkpoint")
async def reset_adapter_checkpoint(adapter_id: str):
    """Reset checkpoint for an adapter (forces full re-ingestion).

    Args:
        adapter_id: Unique identifier for the adapter

    Returns:
        Success message
    """
    registry = get_adapter_registry()

    try:
        registry.reset_checkpoint(adapter_id)
        return {
            "adapter_id": adapter_id,
            "status": "success",
            "message": "Checkpoint reset successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkpoint reset failed: {str(e)}")
