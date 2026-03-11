"""Health monitor + auto-restart for Embodier Trader on PC1 (ESPENMAIN).

Polls /healthz and /readyz endpoints. Restarts the backend if unhealthy.

Usage:
    python scripts/health_monitor.py

Runs as a separate process alongside the main backend. Can be launched
via start-embodier.ps1 or as a Windows scheduled task.

Configuration via env vars:
    HEALTH_CHECK_URL     = http://localhost:8000/healthz  (default)
    HEALTH_CHECK_INTERVAL = 30  (seconds between checks)
    MAX_FAILURES         = 3   (restart after N consecutive failures)
    RESTART_COMMAND      = (auto-detected: uvicorn or run_server.py)
"""

import logging
import os
import subprocess
import sys
import time

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HEALTH] %(levelname)s %(message)s",
)
logger = logging.getLogger("health_monitor")

BASE_URL = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000")
CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
MAX_FAILURES = int(os.getenv("MAX_FAILURES", "3"))
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

consecutive_failures = 0


def check_health() -> bool:
    """Check /healthz endpoint. Returns True if healthy."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{BASE_URL}/healthz")
            if resp.status_code == 200:
                return True
            logger.warning("Health check returned %d", resp.status_code)
            return False
    except Exception as e:
        logger.warning("Health check failed: %s", e)
        return False


def check_readiness() -> dict:
    """Check /readyz endpoint for detailed readiness."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{BASE_URL}/readyz")
            return resp.json()
    except Exception:
        return {"status": "unreachable"}


def restart_backend():
    """Restart the backend process."""
    logger.warning("Restarting backend...")
    backend_dir = os.path.join(BACKEND_DIR, "backend")

    # Try to find the right command
    if sys.platform == "win32":
        # Windows: use the PowerShell launcher
        script = os.path.join(BACKEND_DIR, "start-embodier.ps1")
        if os.path.exists(script):
            subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", script],
                cwd=BACKEND_DIR,
            )
        else:
            # Direct uvicorn restart
            subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
                cwd=backend_dir,
            )
    else:
        # Linux: direct uvicorn
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=backend_dir,
        )


def main():
    global consecutive_failures

    logger.info("Health monitor started — checking %s every %ds", BASE_URL, CHECK_INTERVAL)
    logger.info("Will restart after %d consecutive failures", MAX_FAILURES)

    while True:
        healthy = check_health()

        if healthy:
            if consecutive_failures > 0:
                logger.info("Backend recovered after %d failures", consecutive_failures)
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            logger.warning(
                "Health check failed (%d/%d)",
                consecutive_failures,
                MAX_FAILURES,
            )

            if consecutive_failures >= MAX_FAILURES:
                readiness = check_readiness()
                logger.error(
                    "Max failures reached. Readiness: %s. Triggering restart.",
                    readiness.get("status", "unknown"),
                )
                restart_backend()
                consecutive_failures = 0
                # Wait longer after restart
                time.sleep(CHECK_INTERVAL * 3)
                continue

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
