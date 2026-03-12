"""Start the FastAPI server.

PC1 (ESPENMAIN): Use --workers 4 to match 4 P-cores for optimal FastAPI throughput.
Reload (DEBUG) runs single-worker only.
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    kwargs = {
        "host": settings.HOST,
        "port": settings.effective_port,
        "reload": settings.DEBUG,
        "log_level": settings.LOG_LEVEL.lower(),
        "loop": "asyncio",  # uvloop causes CPU spin with many concurrent tasks
    }
    # PC1: 4 workers when not in reload (matches 4 P-cores for peak load)
    if not settings.DEBUG:
        kwargs["workers"] = getattr(settings, "UVICORN_WORKERS", 4)
    uvicorn.run("app.main:app", **kwargs)

