"""Standalone PC2 Awareness Worker: exposes POST /awareness/enrich only.

Run on PC2 (RTX/CUDA) for GPU-backed enrichment, or use for local testing:
  python -m uvicorn awareness_main:app --host 0.0.0.0 --port 8001

Set AWARENESS_URL or PC2_BRAIN_URL on PC1 to http://<pc2>:8001 to use this worker.
"""
from fastapi import FastAPI

from app.api.v1.awareness import router as awareness_router

app = FastAPI(title="Awareness Worker (PC2)", version="0.1.0")
app.include_router(awareness_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "awareness_worker"}
