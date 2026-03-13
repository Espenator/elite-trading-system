"""Embodier Trader — Service Supervisor with Auto-Restart & Auto-Debug.

Monitors all Embodier services (backend, frontend, brain_service, Ollama),
auto-restarts crashed processes, runs health checks, and logs diagnostics.

Works on both PC1 (ESPENMAIN) and PC2 (ProfitTrader) — auto-detects role
from backend/.env PC_ROLE setting.

Usage:
    python scripts/service_supervisor.py              # Auto-detect PC role
    python scripts/service_supervisor.py --role pc2    # Force PC2 mode
    python scripts/service_supervisor.py --dry-run     # Show what would start

Features:
    - Auto-restart: crashed services restart within 5 seconds
    - Health checks: HTTP pings every 30 seconds
    - Auto-debug: captures crash logs, last 50 lines of stderr
    - Exponential backoff: prevents restart storms (max 5 min between retries)
    - Crash budget: stops restarting after 10 failures in 15 minutes
    - Graceful shutdown: CTRL+C stops all services cleanly
    - Structured logging to scripts/logs/supervisor.log
"""
import asyncio
import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend-v2"
BRAIN_DIR = REPO_ROOT / "brain_service"
DESKTOP_DIR = REPO_ROOT / "desktop"
LOG_DIR = REPO_ROOT / "scripts" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE = LOG_DIR / "supervisor.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_FILE), mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("supervisor")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HEALTH_CHECK_INTERVAL = 30        # seconds between health pings
RESTART_DELAY_BASE = 3            # initial restart delay (seconds)
RESTART_DELAY_MAX = 300           # max restart delay (5 min)
CRASH_BUDGET_WINDOW = 900         # 15 minutes
CRASH_BUDGET_MAX = 10             # max crashes in window before giving up
STARTUP_GRACE_PERIOD = 15         # seconds to wait before first health check


def detect_pc_role() -> str:
    """Detect PC role from backend/.env."""
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("PC_ROLE="):
                role = line.split("=", 1)[1].strip().strip('"').strip("'")
                return role
    # Fallback: check hostname
    import socket
    hostname = socket.gethostname().upper()
    if "PROFIT" in hostname:
        return "secondary"
    return "primary"


def detect_backend_port() -> int:
    """Get backend port from .env."""
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("PORT="):
                try:
                    return int(line.split("=", 1)[1].strip().strip('"'))
                except ValueError:
                    pass
    return 8000


def get_venv_python() -> str:
    """Get path to Python in the backend venv."""
    if sys.platform == "win32":
        venv_python = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    else:
        venv_python = BACKEND_DIR / "venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def get_venv_uvicorn() -> str:
    """Get path to uvicorn in the backend venv."""
    if sys.platform == "win32":
        uvicorn_path = BACKEND_DIR / "venv" / "Scripts" / "uvicorn.exe"
    else:
        uvicorn_path = BACKEND_DIR / "venv" / "bin" / "uvicorn"
    if uvicorn_path.exists():
        return str(uvicorn_path)
    return "uvicorn"


# ---------------------------------------------------------------------------
# Service Definition
# ---------------------------------------------------------------------------
class ServiceConfig:
    """Configuration for a managed service."""

    def __init__(
        self,
        name: str,
        cmd: List[str],
        cwd: str,
        health_url: Optional[str] = None,
        env_extra: Optional[Dict] = None,
        enabled: bool = True,
        startup_order: int = 0,
    ):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.health_url = health_url
        self.env_extra = env_extra or {}
        self.enabled = enabled
        self.startup_order = startup_order


class ManagedService:
    """A supervised service with auto-restart and health monitoring."""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.restart_count = 0
        self.crash_times: deque = deque(maxlen=CRASH_BUDGET_MAX + 1)
        self.last_restart_delay = RESTART_DELAY_BASE
        self.started_at: Optional[datetime] = None
        self.last_health_ok: Optional[datetime] = None
        self.status = "stopped"
        self.last_error = ""
        self._log_file = LOG_DIR / f"{config.name}.log"
        self._err_file = LOG_DIR / f"{config.name}.err.log"

    @property
    def is_running(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def _check_crash_budget(self) -> bool:
        """Return True if we've exceeded the crash budget."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=CRASH_BUDGET_WINDOW)
        recent = [t for t in self.crash_times if t > cutoff]
        return len(recent) >= CRASH_BUDGET_MAX

    def start(self) -> bool:
        """Start the service process."""
        if not self.config.enabled:
            logger.info(f"[{self.config.name}] SKIPPED (disabled)")
            self.status = "disabled"
            return False

        if self.is_running:
            logger.info(f"[{self.config.name}] Already running (PID {self.process.pid})")
            return True

        if self._check_crash_budget():
            logger.error(
                f"[{self.config.name}] CRASH BUDGET EXCEEDED — "
                f"{CRASH_BUDGET_MAX} crashes in {CRASH_BUDGET_WINDOW}s. "
                f"Not restarting. Manual intervention required."
            )
            self.status = "crash_budget_exceeded"
            return False

        env = os.environ.copy()
        env.update(self.config.env_extra)

        try:
            log_f = open(str(self._log_file), "a", encoding="utf-8")
            err_f = open(str(self._err_file), "a", encoding="utf-8")

            logger.info(
                f"[{self.config.name}] Starting: {' '.join(self.config.cmd)}"
            )
            log_f.write(f"\n{'='*60}\n")
            log_f.write(f"Starting at {datetime.now().isoformat()}\n")
            log_f.write(f"Command: {' '.join(self.config.cmd)}\n")
            log_f.write(f"{'='*60}\n")
            log_f.flush()

            self.process = subprocess.Popen(
                self.config.cmd,
                cwd=self.config.cwd,
                env=env,
                stdout=log_f,
                stderr=err_f,
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    if sys.platform == "win32"
                    else 0
                ),
            )
            self.started_at = datetime.now()
            self.status = "starting"
            self.last_restart_delay = RESTART_DELAY_BASE
            logger.info(
                f"[{self.config.name}] Started (PID {self.process.pid})"
            )
            return True

        except Exception as e:
            self.last_error = str(e)
            self.status = "start_failed"
            logger.error(f"[{self.config.name}] Failed to start: {e}")
            self._capture_debug_info(f"Start failure: {e}")
            return False

    def stop(self):
        """Gracefully stop the service."""
        if self.process and self.is_running:
            logger.info(f"[{self.config.name}] Stopping (PID {self.process.pid})...")
            try:
                if sys.platform == "win32":
                    self.process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"[{self.config.name}] Force killing...")
                    self.process.kill()
                    self.process.wait(timeout=5)
            except Exception as e:
                logger.error(f"[{self.config.name}] Stop error: {e}")
            self.status = "stopped"
            logger.info(f"[{self.config.name}] Stopped")

    def check_and_restart(self) -> bool:
        """Check if service crashed and restart if needed. Returns True if restarted."""
        if not self.config.enabled:
            return False
        if self.is_running:
            return False

        # Service has crashed
        exit_code = self.process.returncode if self.process else -1
        self.crash_times.append(datetime.now())
        self.restart_count += 1
        self.status = "crashed"

        self._capture_debug_info(f"Crashed with exit code {exit_code}")

        logger.warning(
            f"[{self.config.name}] CRASHED (exit={exit_code}, "
            f"restarts={self.restart_count}). "
            f"Restarting in {self.last_restart_delay}s..."
        )

        # Exponential backoff
        time.sleep(self.last_restart_delay)
        self.last_restart_delay = min(
            self.last_restart_delay * 2, RESTART_DELAY_MAX
        )

        return self.start()

    def health_check(self) -> bool:
        """Run HTTP health check. Returns True if healthy."""
        if not self.config.health_url:
            return self.is_running

        if not self.is_running:
            return False

        # Grace period after startup
        if self.started_at:
            elapsed = (datetime.now() - self.started_at).total_seconds()
            if elapsed < STARTUP_GRACE_PERIOD:
                return True  # still starting up

        try:
            import urllib.request
            req = urllib.request.Request(
                self.config.health_url, method="GET"
            )
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    self.last_health_ok = datetime.now()
                    self.status = "healthy"
                    return True
                else:
                    self.status = "unhealthy"
                    self.last_error = f"HTTP {resp.status}"
                    return False
        except Exception as e:
            self.status = "unhealthy"
            self.last_error = str(e)
            return False

    def _capture_debug_info(self, reason: str):
        """Auto-debug: capture diagnostic info on failure."""
        debug_file = LOG_DIR / f"{self.config.name}_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        lines = []
        lines.append(f"AUTO-DEBUG REPORT: {self.config.name}")
        lines.append(f"Timestamp: {datetime.now().isoformat()}")
        lines.append(f"Reason: {reason}")
        lines.append(f"Restart count: {self.restart_count}")
        lines.append(f"Command: {' '.join(self.config.cmd)}")
        lines.append(f"CWD: {self.config.cwd}")
        lines.append("")

        # Capture last 50 lines of stderr
        if self._err_file.exists():
            try:
                err_lines = self._err_file.read_text(encoding="utf-8", errors="replace").splitlines()
                lines.append("=== LAST 50 LINES OF STDERR ===")
                for line in err_lines[-50:]:
                    lines.append(line)
                lines.append("")
            except Exception:
                pass

        # Capture last 50 lines of stdout
        if self._log_file.exists():
            try:
                log_lines = self._log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                lines.append("=== LAST 50 LINES OF STDOUT ===")
                for line in log_lines[-50:]:
                    lines.append(line)
                lines.append("")
            except Exception:
                pass

        # System info
        lines.append("=== SYSTEM INFO ===")
        try:
            import platform
            lines.append(f"Platform: {platform.platform()}")
            lines.append(f"Python: {sys.version}")
            lines.append(f"Hostname: {platform.node()}")
        except Exception:
            pass

        # Port check
        lines.append("")
        lines.append("=== PORT STATUS ===")
        try:
            import socket
            for port in [8000, 8001, 3000, 5173, 50051, 11434]:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("localhost", port))
                status = "OPEN" if result == 0 else "CLOSED"
                lines.append(f"  Port {port}: {status}")
                sock.close()
        except Exception:
            pass

        try:
            debug_file.write_text("\n".join(lines), encoding="utf-8")
            logger.info(f"[{self.config.name}] Debug report saved: {debug_file}")
        except Exception as e:
            logger.error(f"[{self.config.name}] Failed to write debug report: {e}")

    def status_dict(self) -> dict:
        return {
            "name": self.config.name,
            "status": self.status,
            "pid": self.process.pid if self.process and self.is_running else None,
            "restart_count": self.restart_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_health_ok": self.last_health_ok.isoformat() if self.last_health_ok else None,
            "last_error": self.last_error,
        }


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------
class Supervisor:
    """Manages all Embodier services."""

    def __init__(self, role: str, dry_run: bool = False):
        self.role = role
        self.dry_run = dry_run
        self.services: Dict[str, ManagedService] = {}
        self._running = True
        self._setup_services()

    def _setup_services(self):
        """Configure services based on PC role."""
        port = detect_backend_port()
        venv_python = get_venv_python()
        uvicorn_cmd = get_venv_uvicorn()

        # --- Backend (both PCs) ---
        self.services["backend"] = ManagedService(ServiceConfig(
            name="backend",
            cmd=[uvicorn_cmd, "app.main:app",
                 "--host", "0.0.0.0", "--port", str(port), "--reload"],
            cwd=str(BACKEND_DIR),
            health_url=f"http://localhost:{port}/api/v1/health",
            startup_order=1,
        ))

        # --- Frontend (both PCs) ---
        # Vite port comes from frontend-v2/vite.config.js VITE_PORT (default 3000)
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        self.services["frontend"] = ManagedService(ServiceConfig(
            name="frontend",
            cmd=[npm_cmd, "run", "dev"],
            cwd=str(FRONTEND_DIR),
            health_url="http://localhost:3000",
            startup_order=2,
        ))

        if self.role == "secondary":
            # --- PC2-specific: Brain Service (gRPC) ---
            self.services["brain_service"] = ManagedService(ServiceConfig(
                name="brain_service",
                cmd=[venv_python, "server.py"],
                cwd=str(BRAIN_DIR),
                health_url=None,  # gRPC — no HTTP health check
                startup_order=3,
            ))

            # --- PC2-specific: Ollama ---
            ollama_cmd = "ollama" if sys.platform != "win32" else "ollama.exe"
            self.services["ollama"] = ManagedService(ServiceConfig(
                name="ollama",
                cmd=[ollama_cmd, "serve"],
                cwd=str(REPO_ROOT),
                health_url="http://localhost:11434/api/tags",
                startup_order=0,  # start first
                enabled=self._check_ollama_available(),
            ))

        if self.role == "primary":
            # --- PC1-specific: Electron Desktop ---
            electron_enabled = (DESKTOP_DIR / "node_modules").exists()
            self.services["desktop"] = ManagedService(ServiceConfig(
                name="desktop",
                cmd=[npm_cmd, "start"],
                cwd=str(DESKTOP_DIR),
                health_url=None,
                startup_order=3,
                enabled=electron_enabled,
            ))

    def _check_ollama_available(self) -> bool:
        """Check if ollama is installed."""
        import shutil
        return shutil.which("ollama") is not None

    def start_all(self):
        """Start all enabled services in order."""
        logger.info(f"{'='*60}")
        logger.info(f"Embodier Supervisor starting — role={self.role}")
        logger.info(f"{'='*60}")

        if self.dry_run:
            logger.info("DRY RUN — showing what would start:")
            for name, svc in sorted(
                self.services.items(), key=lambda x: x[1].config.startup_order
            ):
                status = "ENABLED" if svc.config.enabled else "DISABLED"
                logger.info(
                    f"  [{status}] {name}: {' '.join(svc.config.cmd)}"
                )
            return

        ordered = sorted(
            self.services.values(), key=lambda s: s.config.startup_order
        )
        for svc in ordered:
            svc.start()
            if svc.config.enabled:
                time.sleep(2)  # stagger startups

    def stop_all(self):
        """Stop all services."""
        logger.info("Supervisor shutting down all services...")
        for name, svc in self.services.items():
            svc.stop()
        logger.info("All services stopped.")

    def monitor_loop(self):
        """Main monitoring loop — runs forever until CTRL+C."""
        logger.info(f"Monitoring {len(self.services)} services (health check every {HEALTH_CHECK_INTERVAL}s)...")

        while self._running:
            try:
                # Check each service
                for name, svc in self.services.items():
                    if not svc.config.enabled:
                        continue

                    # Auto-restart crashed services
                    if not svc.is_running and svc.status not in ("stopped", "disabled", "crash_budget_exceeded"):
                        svc.check_and_restart()

                    # Health check
                    if svc.is_running:
                        healthy = svc.health_check()
                        if not healthy and svc.status == "unhealthy":
                            logger.warning(f"[{name}] Health check FAILED: {svc.last_error}")

                # Log status summary
                self._log_status_summary()

                # Sleep until next check
                for _ in range(HEALTH_CHECK_INTERVAL):
                    if not self._running:
                        break
                    time.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(5)

    def _log_status_summary(self):
        """Log a compact status line."""
        parts = []
        for name, svc in self.services.items():
            if not svc.config.enabled:
                continue
            icon = {
                "healthy": "OK",
                "starting": "..",
                "unhealthy": "!!",
                "crashed": "XX",
                "crash_budget_exceeded": "DEAD",
                "stopped": "--",
            }.get(svc.status, "??")
            pid_str = f":{svc.process.pid}" if svc.process and svc.is_running else ""
            parts.append(f"{name}={icon}{pid_str}")
        logger.info(f"STATUS: {' | '.join(parts)}")

    def handle_signal(self, signum, frame):
        """Handle CTRL+C / SIGTERM."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._running = False

    def get_status(self) -> dict:
        """Get full status for API endpoint."""
        return {
            "role": self.role,
            "timestamp": datetime.now().isoformat(),
            "services": {
                name: svc.status_dict() for name, svc in self.services.items()
            },
        }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Embodier Trader Service Supervisor")
    parser.add_argument(
        "--role", choices=["pc1", "pc2", "primary", "secondary"],
        help="Force PC role (default: auto-detect from .env)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would start without starting anything"
    )
    args = parser.parse_args()

    # Determine role
    if args.role:
        role_map = {"pc1": "primary", "pc2": "secondary", "primary": "primary", "secondary": "secondary"}
        role = role_map[args.role]
    else:
        role = detect_pc_role()

    logger.info(f"Detected PC role: {role}")

    supervisor = Supervisor(role=role, dry_run=args.dry_run)

    # Register signal handlers
    signal.signal(signal.SIGINT, supervisor.handle_signal)
    signal.signal(signal.SIGTERM, supervisor.handle_signal)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, supervisor.handle_signal)

    # Start all services
    supervisor.start_all()

    if args.dry_run:
        return

    # Enter monitoring loop
    try:
        supervisor.monitor_loop()
    finally:
        supervisor.stop_all()

    # Write final status
    status_file = LOG_DIR / "last_status.json"
    try:
        status_file.write_text(
            json.dumps(supervisor.get_status(), indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    logger.info("Supervisor exited.")


if __name__ == "__main__":
    main()
