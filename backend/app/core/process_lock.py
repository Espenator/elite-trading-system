"""
Process lock — prevents multiple backend instances from running simultaneously.

Uses a PID file + port health check to guarantee exactly ONE backend process.
This solves the constant port conflict / DuckDB lock issues caused by Cursor,
manual terminals, and launcher scripts all starting uvicorn independently.

Usage:
    from app.core.process_lock import acquire_lock, release_lock

    # At startup (in lifespan):
    acquire_lock(port=8000)  # Exits if another healthy instance owns the lock

    # At shutdown (in lifespan):
    release_lock()
"""
import atexit
import logging
import os
import signal
import sys
import time
from pathlib import Path

log = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_PID_FILE = _BACKEND_DIR / ".embodier.pid"
_LOCK_ACQUIRED = False

# Health check timeout (seconds). Must be long enough for a loaded backend to respond.
_HEALTH_CHECK_TIMEOUT = 5.0
# Number of health check retries before declaring a process dead.
_HEALTH_CHECK_RETRIES = 3
# Delay between retries (seconds).
_HEALTH_CHECK_RETRY_DELAY = 2.0


def _is_process_alive(pid: int) -> bool:
    """Check if a process with given PID is still running."""
    if pid <= 0:
        return False
    try:
        # os.kill with signal 0 checks existence without killing
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, SystemError):
        return False


def _is_healthy_backend(port: int) -> bool:
    """Check if a healthy Embodier backend is responding on the given port.

    Uses /api/v1/health (reliable JSON endpoint) with retries.
    Falls back to /health if /api/v1/health doesn't respond.
    """
    import urllib.request

    # Try /api/v1/health first (always returns JSON, most reliable)
    for attempt in range(_HEALTH_CHECK_RETRIES):
        try:
            url = f"http://127.0.0.1:{port}/api/v1/health"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=_HEALTH_CHECK_TIMEOUT) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass

        # On last retry, try /health as fallback
        if attempt == _HEALTH_CHECK_RETRIES - 1:
            try:
                url = f"http://127.0.0.1:{port}/health"
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=_HEALTH_CHECK_TIMEOUT) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                pass
        else:
            time.sleep(_HEALTH_CHECK_RETRY_DELAY)

    return False


def _read_pid_file() -> dict:
    """Read PID file, returns {pid, port, started} or empty dict."""
    try:
        if not _PID_FILE.exists():
            return {}
        text = _PID_FILE.read_text().strip()
        result = {}
        for line in text.splitlines():
            if "=" in line:
                key, val = line.split("=", 1)
                result[key.strip()] = val.strip()
        return result
    except Exception:
        return {}


def _write_pid_file(port: int) -> None:
    """Write current process info to PID file with file locking on Windows."""
    pid = os.getpid()
    content = (
        f"pid={pid}\n"
        f"port={port}\n"
        f"started={time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
    )

    # On Windows, use msvcrt file locking to prevent race conditions
    if sys.platform == "win32":
        try:
            import msvcrt

            fd = os.open(str(_PID_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                os.write(fd, content.encode())
                try:
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            finally:
                os.close(fd)
            return
        except (ImportError, OSError):
            pass  # Fall through to simple write

    # Non-Windows or fallback: simple write
    _PID_FILE.write_text(content)


def acquire_lock(port: int) -> None:
    """
    Acquire the process lock. If another healthy instance is running, exit.

    Decision logic:
    1. No PID file -> we're first, take the lock
    2. PID file exists, process dead -> stale lock, take over
    3. PID file exists, process alive, health check passes -> ABORT (duplicate)
    4. PID file exists, process alive, health check fails -> zombie, take over
    """
    global _LOCK_ACQUIRED

    existing = _read_pid_file()

    # If we already hold the lock (same PID), skip
    if existing:
        old_pid = int(existing.get("pid", 0))
        if old_pid == os.getpid():
            log.info("Process lock already held by us (PID %d), skipping", old_pid)
            _LOCK_ACQUIRED = True
            return

    if existing:
        old_pid = int(existing.get("pid", 0))
        old_port = int(existing.get("port", 0))

        if _is_process_alive(old_pid):
            # Process exists — is it actually serving?
            check_port = old_port or port
            if _is_healthy_backend(check_port):
                log.warning(
                    "Another Embodier backend is already running "
                    "(PID %d on port %d, started %s). "
                    "Not starting a duplicate. Exiting.",
                    old_pid,
                    check_port,
                    existing.get("started", "unknown"),
                )
                print(
                    f"\n  [PROCESS LOCK] Backend already running "
                    f"(PID {old_pid}, port {check_port}). "
                    f"Use scripts/stop_embodier.ps1 to stop it first.\n",
                    file=sys.stderr,
                )
                os._exit(3)  # EXIT_DUPLICATE — distinct from DuckDB exit code 2
            else:
                log.warning(
                    "Stale backend process found (PID %d not responding on port %d). "
                    "Taking over lock.",
                    old_pid,
                    check_port,
                )
                # Try to kill the zombie
                try:
                    os.kill(old_pid, signal.SIGTERM)
                    time.sleep(2)
                except (OSError, ProcessLookupError):
                    pass
        else:
            log.info(
                "Stale PID file found (PID %d no longer running). Taking over.",
                old_pid,
            )

    # Write our PID
    _write_pid_file(port)
    _LOCK_ACQUIRED = True
    log.info("Process lock acquired (PID %d, port %d)", os.getpid(), port)

    # Register cleanup
    atexit.register(release_lock)


def release_lock() -> None:
    """Release the process lock by removing the PID file."""
    global _LOCK_ACQUIRED
    if not _LOCK_ACQUIRED:
        return
    try:
        # Only remove if we own it (PID matches)
        existing = _read_pid_file()
        if existing and int(existing.get("pid", 0)) == os.getpid():
            _PID_FILE.unlink(missing_ok=True)
            log.info("Process lock released (PID %d)", os.getpid())
    except Exception as e:
        log.warning("Failed to release process lock: %s", e)
    _LOCK_ACQUIRED = False


def cleanup_stale_lock() -> bool:
    """Remove PID file if the process it references is dead. Returns True if cleaned."""
    existing = _read_pid_file()
    if not existing:
        return False
    old_pid = int(existing.get("pid", 0))
    if old_pid > 0 and not _is_process_alive(old_pid):
        try:
            _PID_FILE.unlink(missing_ok=True)
            log.info("Cleaned stale process lock (PID %d)", old_pid)
            return True
        except Exception:
            pass
    return False


def is_locked() -> bool:
    """Check if another instance holds the lock (without acquiring)."""
    existing = _read_pid_file()
    if not existing:
        return False
    old_pid = int(existing.get("pid", 0))
    return _is_process_alive(old_pid)


def get_lock_info() -> dict:
    """Return current lock state for diagnostics."""
    existing = _read_pid_file()
    if not existing:
        return {"locked": False}
    old_pid = int(existing.get("pid", 0))
    old_port = int(existing.get("port", 0))
    alive = _is_process_alive(old_pid)
    return {
        "locked": alive,
        "pid": old_pid,
        "port": old_port,
        "started": existing.get("started", ""),
        "is_current_process": old_pid == os.getpid(),
        "healthy": _is_healthy_backend(old_port) if alive else False,
    }
