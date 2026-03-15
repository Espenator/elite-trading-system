"""
Embodier Trader Backend — Entry point for PyInstaller bundle.
Starts the FastAPI server via uvicorn.
"""
import os
import sys

# Debug: detect event loop blocking (any callback >0.5s)
# os.environ["PYTHONASYNCIODEBUG"] = "1"  # Disabled — massive overhead on Windows ProactorEventLoop

# When running as PyInstaller bundle, set the working directory
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
    # Ensure the app package is importable
    sys.path.insert(0, os.path.dirname(sys.executable))

from dotenv import load_dotenv
load_dotenv(override=True)  # override=True so .env values win over empty system env vars

import uvicorn


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("UVICORN_WORKERS", "1"))

    # Auto-detect uvloop (Linux only — 2-4x faster event loop)
    loop_impl = "asyncio"
    if sys.platform != "win32":
        try:
            import uvloop  # noqa: F401
            loop_impl = "uvloop"
        except ImportError:
            pass

    # Auto-detect httptools (C extension — 2-4x faster HTTP parsing)
    http_impl = "auto"
    try:
        import httptools  # noqa: F401
        http_impl = "httptools"
    except ImportError:
        pass

    # Multi-worker: Set UVICORN_WORKERS=4 in .env to use i7 cores on PC1.
    # NOTE: workers>1 spawns separate processes (no shared in-memory state).
    # DuckDB WAL mode handles concurrent reads safely; writes are serialized
    # per-process via _write_lock. Default=1 is safe for current architecture.
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
        access_log=False,
        loop=loop_impl,
        http=http_impl,
        timeout_keep_alive=60,  # Keep connections warm for dashboard polling
        backlog=2048,         # Handle burst connections during heavy scans
    )


if __name__ == "__main__":
    main()
