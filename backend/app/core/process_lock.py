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


def _is_process_alive(pid: int) -> bool:
    """Check if a process with given PID is still running."""
    if pid <= 0:
        return False
    try:
        # os.kill with signal 0 checks existence without killing
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _is_healthy_backend(port: int, timeout: float = 2.0) -> bool:
    """Check if a healthy Embodier backend is responding on the given port."""
    try:
        import urllib.request
        url = f"http://127.0.0.1:{port}/health"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
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


def _get_master_pid() -> int:
    """Get the master process PID (parent uvicorn for multi-worker, self for single)."""
    ppid = os.getppid()
    # In multi-worker mode, parent is the uvicorn master that binds the port.
    # In single-worker/reload mode, we ARE the process that binds the port.
    # Heuristic: if parent is also a python/uvicorn process, use parent PID.
    if ppid > 1 and _is_process_alive(ppid):
        try:
            # Check if parent is uvicorn (not init/systemd/shell)
            import pathlib
            cmdline = pathlib.Path(f"/proc/{ppid}/cmdline").read_bytes().decode(errors="ignore")
            if "uvicorn" in cmdline or "python" in cmdline:
                return ppid
        except (FileNotFoundError, PermissionError):
            # Not on Linux or no /proc — Windows doesn't have /proc
            # On Windows, multi-worker uses subprocess spawning, parent is python
            pass
    return os.getpid()


def _write_pid_file(port: int) -> None:
    """Write current process info to PID file."""
    master_pid = _get_master_pid()
    _PID_FILE.write_text(
        f"pid={master_pid}\n"
        f"port={port}\n"
        f"started={time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
        f"worker_pid={os.getpid()}\n"
    )


def acquire_lock(port: int) -> None:
    """
    Acquire the process lock. If another healthy instance is running, exit.

    Decision logic:
    1. No PID file → we're first, take the lock
    2. PID file exists, process dead → stale lock, take over
    3. PID file exists, process alive, health check passes → ABORT (duplicate)
    4. PID file exists, process alive, health check fails → zombie, take over
    """
    global _LOCK_ACQUIRED

    existing = _read_pid_file()
    our_master = _get_master_pid()

    # If we're a worker of the same master process, skip (don't fight siblings)
    if existing:
        old_pid = int(existing.get("pid", 0))
        if old_pid == our_master:
            log.info("Process lock already held by our master (PID %d), worker skipping", our_master)
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
                    time.sleep(1)
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
