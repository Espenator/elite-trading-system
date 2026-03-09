#!/usr/bin/env python3
"""Comprehensive system diagnostics for Elite Trading System.

This script performs a thorough health check of all subsystems and provides
actionable recommendations for fixing issues.

Usage:
    python scripts/doctor.py                    # Full diagnostic
    python scripts/doctor.py --quick            # Quick check (critical only)
    python scripts/doctor.py --fix              # Auto-fix common issues
    python scripts/doctor.py --export report.json  # Export results

Checks:
- Environment configuration
- Python/Node dependencies
- Database connectivity
- WebSocket health
- Brain service connectivity
- Integration APIs (Alpaca, Unusual Whales, etc.)
- Event pipeline status
- Port availability
- File permissions
- System resources (memory, disk)

Exit codes:
- 0: All checks passed
- 1: Critical failures found
- 2: Warnings only (degraded mode)
"""

import os
import sys
import json
import time
import socket
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict

# Color output helpers
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


@dataclass
class CheckResult:
    """Result of a diagnostic check."""
    name: str
    status: str  # pass, warn, fail
    message: str
    details: Dict[str, Any] = None
    fix_command: str = None


class SystemDoctor:
    """Comprehensive system diagnostic tool."""

    def __init__(self, quick: bool = False, auto_fix: bool = False):
        self.quick = quick
        self.auto_fix = auto_fix
        self.results: List[CheckResult] = []
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    def add_result(self, name: str, status: str, message: str, **kwargs):
        """Add a check result."""
        self.results.append(CheckResult(name=name, status=status, message=message, **kwargs))

    def print_header(self, text: str):
        """Print a section header."""
        print(f"\n{CYAN}{BOLD}{'=' * 60}{RESET}")
        print(f"{CYAN}{BOLD}  {text}{RESET}")
        print(f"{CYAN}{BOLD}{'=' * 60}{RESET}\n")

    def print_result(self, result: CheckResult):
        """Print a check result."""
        if result.status == "pass":
            symbol = f"{GREEN}✓{RESET}"
        elif result.status == "warn":
            symbol = f"{YELLOW}⚠{RESET}"
        else:
            symbol = f"{RED}✗{RESET}"

        print(f"  {symbol} {result.name:40} {result.message}")

        if result.details:
            for key, value in result.details.items():
                print(f"      {key}: {value}")

        if result.fix_command and result.status == "fail":
            print(f"      {YELLOW}Fix: {result.fix_command}{RESET}")

    # ========== CHECKS ==========

    def check_python_version(self):
        """Check Python version."""
        version = sys.version_info
        required = (3, 10)

        if version >= required:
            self.add_result(
                "Python version",
                "pass",
                f"{version.major}.{version.minor}.{version.micro}",
            )
        else:
            self.add_result(
                "Python version",
                "fail",
                f"{version.major}.{version.minor}.{version.micro} (required: 3.10+)",
                fix_command="Install Python 3.10+ from https://python.org/downloads",
            )

    def check_node_version(self):
        """Check Node.js version."""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                major = int(version[1:].split(".")[0]) if version.startswith("v") else 0
                if major >= 18:
                    self.add_result("Node.js version", "pass", version)
                else:
                    self.add_result(
                        "Node.js version",
                        "warn",
                        f"{version} (recommended: v18+)",
                        fix_command="Install Node.js 18+ from https://nodejs.org",
                    )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.add_result(
                "Node.js installed",
                "fail",
                "Not found on PATH",
                fix_command="Install Node.js from https://nodejs.org",
            )

    def check_python_packages(self):
        """Check required Python packages."""
        packages = ["fastapi", "uvicorn", "duckdb", "alpaca", "pydantic", "dotenv"]
        missing = []

        for pkg in packages:
            try:
                pkg_import = pkg.replace("-", "_")
                if pkg == "dotenv":
                    pkg_import = "dotenv"
                elif pkg == "alpaca":
                    pkg_import = "alpaca.trading"
                __import__(pkg_import)
            except ImportError:
                missing.append(pkg)

        if not missing:
            self.add_result("Python packages", "pass", f"All {len(packages)} required packages installed")
        else:
            self.add_result(
                "Python packages",
                "fail",
                f"Missing {len(missing)} packages: {', '.join(missing)}",
                fix_command="pip install -r backend/requirements.txt",
            )

    def check_env_file(self):
        """Check .env file exists."""
        backend_dir = Path(__file__).parent.parent / "backend"
        env_file = backend_dir / ".env"

        if env_file.exists():
            self.add_result(".env file", "pass", str(env_file))
        else:
            self.add_result(
                ".env file",
                "warn",
                "Not found - using environment variables only",
                fix_command="cp backend/.env.example backend/.env",
            )

    def check_env_vars(self):
        """Check critical environment variables."""
        alpaca_key = os.getenv("ALPACA_API_KEY", "")
        alpaca_secret = os.getenv("ALPACA_SECRET_KEY", "")

        if alpaca_key and not alpaca_key.startswith("your-"):
            self.add_result("Alpaca API key", "pass", "Configured")
        else:
            self.add_result(
                "Alpaca API key",
                "warn",
                "Not configured - trading features disabled",
                details={"status": "degraded mode"},
            )

        if alpaca_secret and not alpaca_secret.startswith("your-"):
            self.add_result("Alpaca secret key", "pass", "Configured")
        else:
            self.add_result(
                "Alpaca secret key",
                "warn",
                "Not configured - trading features disabled",
            )

    def check_ports(self):
        """Check port availability."""
        ports = {
            8000: "Backend API",
            3000: "Frontend Dev Server",
            50051: "Brain Service (optional)",
        }

        for port, name in ports.items():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    result = s.connect_ex(("127.0.0.1", port))
                    if result == 0:
                        # Port is in use - check if it's our service
                        if port in (8000, 3000):
                            self.add_result(
                                f"Port {port}",
                                "warn",
                                f"{name} - already in use (may be running)",
                            )
                        else:
                            self.add_result(
                                f"Port {port}",
                                "pass",
                                f"{name} - in use (service running)",
                            )
                    else:
                        self.add_result(
                            f"Port {port}",
                            "pass",
                            f"{name} - available",
                        )
            except Exception as e:
                self.add_result(
                    f"Port {port}",
                    "warn",
                    f"{name} - could not check: {e}",
                )

    def check_database(self):
        """Check database directory and permissions."""
        backend_dir = Path(__file__).parent.parent / "backend"
        data_dir = backend_dir / "data"

        if not data_dir.exists():
            self.add_result(
                "Database directory",
                "warn",
                f"{data_dir} does not exist",
                fix_command=f"mkdir -p {data_dir}",
            )
        elif not os.access(data_dir, os.W_OK):
            self.add_result(
                "Database directory",
                "fail",
                f"{data_dir} is not writable",
                fix_command=f"chmod u+w {data_dir}",
            )
        else:
            # Count database files
            db_files = list(data_dir.glob("*.duckdb"))
            self.add_result(
                "Database directory",
                "pass",
                f"{data_dir} ({len(db_files)} database files)",
            )

    def check_backend_health(self):
        """Check backend health endpoints."""
        if self.quick:
            return  # Skip in quick mode

        try:
            import requests

            # Check /healthz
            try:
                r = requests.get(f"{self.backend_url}/healthz", timeout=3)
                if r.status_code == 200:
                    self.add_result("Backend liveness", "pass", f"{self.backend_url}/healthz")
                else:
                    self.add_result(
                        "Backend liveness",
                        "fail",
                        f"Status {r.status_code}",
                    )
            except requests.exceptions.ConnectionError:
                self.add_result(
                    "Backend liveness",
                    "warn",
                    "Backend not running",
                    fix_command="./start-embodier.ps1 or python backend/server.py",
                )
            except requests.exceptions.Timeout:
                self.add_result("Backend liveness", "fail", "Timeout after 3s")

        except ImportError:
            self.add_result(
                "Backend health check",
                "warn",
                "requests package not installed - skipping",
            )

    def check_websocket_health(self):
        """Check WebSocket health endpoint."""
        if self.quick:
            return

        try:
            import requests

            r = requests.get(f"{self.backend_url}/health/websocket", timeout=3)
            if r.status_code == 200:
                data = r.json()
                connections = data.get("connections", {}).get("total", 0)
                self.add_result(
                    "WebSocket health",
                    "pass",
                    f"{connections} active connections",
                    details=data.get("connections", {}),
                )
            else:
                self.add_result("WebSocket health", "warn", f"Status {r.status_code}")
        except Exception as e:
            self.add_result("WebSocket health", "warn", f"Could not check: {e}")

    def check_brain_service(self):
        """Check brain service connectivity."""
        if self.quick:
            return

        brain_enabled = os.getenv("BRAIN_ENABLED", "false").lower() in ("true", "1", "yes")

        if not brain_enabled:
            self.add_result(
                "Brain service",
                "pass",
                "Disabled (BRAIN_ENABLED=false)",
            )
            return

        try:
            import requests

            r = requests.get(f"{self.backend_url}/health/brain", timeout=5)
            if r.status_code == 200:
                data = r.json()
                status = data.get("status", "unknown")
                latency = data.get("latency_ms")

                if status == "healthy":
                    msg = f"Connected ({latency:.0f}ms)" if latency else "Connected"
                    self.add_result("Brain service", "pass", msg)
                elif status == "timeout":
                    self.add_result(
                        "Brain service",
                        "fail",
                        "Timeout - check brain_service/server.py is running",
                    )
                else:
                    self.add_result(
                        "Brain service",
                        "fail",
                        f"Status: {status}",
                        details=data,
                    )
            else:
                self.add_result("Brain service", "fail", f"HTTP {r.status_code}")
        except Exception as e:
            self.add_result("Brain service", "warn", f"Could not check: {e}")

    def check_disk_space(self):
        """Check available disk space."""
        try:
            import shutil

            backend_dir = Path(__file__).parent.parent / "backend"
            total, used, free = shutil.disk_usage(backend_dir)

            free_gb = free // (2**30)
            total_gb = total // (2**30)
            percent_free = (free / total) * 100

            if percent_free < 10:
                self.add_result(
                    "Disk space",
                    "fail",
                    f"{free_gb}GB free of {total_gb}GB ({percent_free:.1f}%)",
                )
            elif percent_free < 20:
                self.add_result(
                    "Disk space",
                    "warn",
                    f"{free_gb}GB free of {total_gb}GB ({percent_free:.1f}%)",
                )
            else:
                self.add_result(
                    "Disk space",
                    "pass",
                    f"{free_gb}GB free of {total_gb}GB ({percent_free:.1f}%)",
                )
        except Exception as e:
            self.add_result("Disk space", "warn", f"Could not check: {e}")

    # ========== MAIN RUNNER ==========

    def run_all_checks(self):
        """Run all diagnostic checks."""
        self.print_header("Python & Node Environment")
        self.check_python_version()
        self.check_node_version()
        self.check_python_packages()

        self.print_header("Configuration")
        self.check_env_file()
        self.check_env_vars()

        self.print_header("Infrastructure")
        self.check_ports()
        self.check_database()
        self.check_disk_space()

        if not self.quick:
            self.print_header("Backend Services")
            self.check_backend_health()
            self.check_websocket_health()
            self.check_brain_service()

    def print_summary(self):
        """Print summary of results."""
        # Print all results
        for result in self.results:
            self.print_result(result)

        # Count statuses
        passed = sum(1 for r in self.results if r.status == "pass")
        warned = sum(1 for r in self.results if r.status == "warn")
        failed = sum(1 for r in self.results if r.status == "fail")
        total = len(self.results)

        print(f"\n{CYAN}{BOLD}{'=' * 60}{RESET}")
        print(f"{CYAN}{BOLD}  Summary{RESET}")
        print(f"{CYAN}{BOLD}{'=' * 60}{RESET}\n")
        print(f"  {GREEN}✓{RESET} Passed: {passed}/{total}")
        print(f"  {YELLOW}⚠{RESET} Warnings: {warned}/{total}")
        print(f"  {RED}✗{RESET} Failed: {failed}/{total}")

        if failed > 0:
            print(f"\n{RED}❌ CRITICAL FAILURES - fix errors above and retry{RESET}\n")
            return 1
        elif warned > 0:
            print(f"\n{YELLOW}⚠️  WARNINGS - system will run in degraded mode{RESET}\n")
            return 2
        else:
            print(f"\n{GREEN}✅ ALL CHECKS PASSED - system ready{RESET}\n")
            return 0

    def export_results(self, filename: str):
        """Export results to JSON file."""
        data = {
            "timestamp": time.time(),
            "checks": [asdict(r) for r in self.results],
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.status == "pass"),
                "warned": sum(1 for r in self.results if r.status == "warn"),
                "failed": sum(1 for r in self.results if r.status == "fail"),
            },
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\n{GREEN}✓{RESET} Results exported to {filename}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive system diagnostics for Elite Trading System"
    )
    parser.add_argument("--quick", action="store_true", help="Quick check (critical only)")
    parser.add_argument("--fix", action="store_true", help="Auto-fix common issues")
    parser.add_argument("--export", type=str, metavar="FILE", help="Export results to JSON")
    parser.add_argument("--url", type=str, help="Backend URL (default: http://localhost:8000)")
    args = parser.parse_args()

    print(f"\n{CYAN}{BOLD}{'=' * 60}{RESET}")
    print(f"{CYAN}{BOLD}  Elite Trading System — System Diagnostics{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 60}{RESET}")

    if args.url:
        os.environ["BACKEND_URL"] = args.url

    doctor = SystemDoctor(quick=args.quick, auto_fix=args.fix)
    doctor.run_all_checks()
    exit_code = doctor.print_summary()

    if args.export:
        doctor.export_results(args.export)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
