"""
Backend process lock to prevent duplicate uvicorn instances.

Lock file states:
- missing: acquire lock
- stale pid: take over
- live + healthy: reject duplicate startup
- live + unhealthy: terminate stale process and take over
- current process is a child of lock owner: allow (multi-worker sibling)
"""

from __future__ import annotations

import json
import logging
import os
import signal
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from app.core.config import settings

log = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_LOCK_FILE = _BACKEND_DIR / ".embodier.pid"


def _is_pid_alive(pid: int) -> bool:
    """Return True when PID exists and is accessible."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _is_backend_healthy(port: int) -> bool:
    """Quick HTTP probe against /healthz on localhost."""
    url = f"http://127.0.0.1:{port}/healthz"
    try:
        with urlopen(url, timeout=0.8) as response:
            return getattr(response, "status", 0) == 200
    except Exception:
        return False


def _read_lock() -> dict[str, Any] | None:
    if not _LOCK_FILE.exists():
        return None
    try:
        return json.loads(_LOCK_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_lock(pid: int) -> None:
    payload = {
        "pid": pid,
        "ppid": os.getppid(),
        "created_at": int(time.time()),
    }
    _LOCK_FILE.write_text(json.dumps(payload), encoding="utf-8")


def _terminate_pid(pid: int) -> None:
    """Best effort terminate process for lock recovery."""
    if not _is_pid_alive(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass

    deadline = time.time() + 2.0
    while time.time() < deadline:
        if not _is_pid_alive(pid):
            return
        time.sleep(0.1)

    try:
        os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def acquire_lock() -> bool:
    """
    Acquire backend process lock.

    Returns False if a healthy duplicate backend is already running.
    """
    current_pid = os.getpid()
    existing = _read_lock()

    if not existing:
        _write_lock(current_pid)
        return True

    existing_pid = int(existing.get("pid", 0) or 0)

    # Multi-worker sibling: allow child process of lock owner to continue.
    if existing_pid and os.getppid() == existing_pid:
        log.debug("Process lock shared with parent pid=%s", existing_pid)
        return True

    if not _is_pid_alive(existing_pid):
        _write_lock(current_pid)
        return True

    port = settings.effective_port
    if _is_backend_healthy(port):
        log.error(
            "Backend already running and healthy (pid=%s, port=%s). Duplicate startup blocked.",
            existing_pid,
            port,
        )
        return False

    log.warning(
        "Found live but unhealthy backend process (pid=%s). Reclaiming lock.",
        existing_pid,
    )
    _terminate_pid(existing_pid)
    _write_lock(current_pid)
    return True


def release_lock() -> None:
    """Release lock only if owned by current process."""
    existing = _read_lock()
    if not existing:
        return
    if int(existing.get("pid", 0) or 0) != os.getpid():
        return
    try:
        _LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass
