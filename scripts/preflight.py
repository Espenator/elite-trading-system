#!/usr/bin/env python3
"""Preflight validation for Embodier Trading System startup.

Checks:
- Python 3.10+ installed
- Required Python packages available
- .env file exists and is valid
- Required env vars present
- Optional env vars present (warns if missing)
- Ports 8000, 3000, 50051 available
- DuckDB directory writable

Exit codes:
- 0: All checks passed
- 1: Critical failure (missing required dependency)
- 2: Degraded mode (optional dependency missing)
"""

import os
import sys
import socket
from pathlib import Path

# Color output helpers
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"

def check(name: str, status: bool, details: str = ""):
    symbol = f"{GREEN}✓{RESET}" if status else f"{RED}✗{RESET}"
    msg = f"  {symbol} {name}"
    if details:
        msg += f" — {details}"
    print(msg)
    return status

def warn(name: str, details: str = ""):
    print(f"  {YELLOW}⚠{RESET} {name} — {details}")

def info(msg: str):
    print(f"{CYAN}{msg}{RESET}")

def check_python_version():
    version = sys.version_info
    required = (3, 10)
    ok = version >= required
    check("Python version", ok, f"{version.major}.{version.minor}.{version.micro} (required: 3.10+)")
    return ok

def check_python_packages():
    packages = ["fastapi", "uvicorn", "duckdb", "alpaca", "pydantic", "dotenv"]
    all_ok = True
    for pkg in packages:
        try:
            pkg_import = pkg.replace("-", "_")
            if pkg == "dotenv":
                pkg_import = "dotenv"
            elif pkg == "alpaca":
                pkg_import = "alpaca.trading"
            __import__(pkg_import)
            check(f"Package {pkg}", True)
        except ImportError:
            check(f"Package {pkg}", False, "Not installed - run: pip install -r backend/requirements.txt")
            all_ok = False
    return all_ok

def check_env_file():
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    exists = env_path.exists()
    if not exists:
        check(".env file exists", False, f"Copy backend/.env.example to backend/.env")
    else:
        check(".env file exists", True, str(env_path))
    return exists

def check_env_vars():
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    load_dotenv(env_path)

    required = {
        "ALPACA_API_KEY": "Alpaca trading (can be placeholder for dev)",
        "ALPACA_SECRET_KEY": "Alpaca trading",
    }

    optional = {
        "UNUSUAL_WHALES_API_KEY": "Options flow data",
        "FINVIZ_API_KEY": "Stock screener",
        "FRED_API_KEY": "Economic data",
        "NEWS_API_KEY": "News headlines",
        "YOUTUBE_API_KEY": "YouTube knowledge agent",
    }

    all_ok = True
    info("\n  Checking required environment variables:")
    for key, desc in required.items():
        val = os.getenv(key, "")
        if val and not val.startswith("your-"):
            check(f"  {key}", True, desc)
        else:
            warn(f"  {key}", f"Not set or placeholder — {desc}")

    info("\n  Checking optional environment variables:")
    for key, desc in optional.items():
        val = os.getenv(key, "")
        if val and not val.startswith("your-"):
            check(f"  {key}", True, desc)
        else:
            warn(f"  {key}", f"Not set — {desc} will be disabled")

    return all_ok

def check_port(port: int, name: str):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex(("127.0.0.1", port))
            if result == 0:
                check(f"Port {port} ({name})", False, "Already in use - kill stale processes")
                return False
            else:
                check(f"Port {port} ({name})", True, "Available")
                return True
    except Exception as e:
        warn(f"Port {port} ({name})", f"Could not check: {e}")
        return True  # Assume OK

def check_duckdb_dir():
    db_dir = Path(__file__).parent.parent / "backend" / "data"
    exists = db_dir.exists()
    if not exists:
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
            check("DuckDB directory", True, f"Created {db_dir}")
            return True
        except Exception as e:
            check("DuckDB directory", False, f"Cannot create: {e}")
            return False
    writable = os.access(db_dir, os.W_OK)
    check("DuckDB directory", writable, str(db_dir))
    return writable

def check_node():
    """Check Node.js version for frontend."""
    try:
        import subprocess
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            version_str = result.stdout.strip()
            # Parse version (e.g., "v20.11.0" -> 20)
            if version_str.startswith("v"):
                major = int(version_str[1:].split(".")[0])
                ok = major >= 18
                check("Node.js version", ok, f"{version_str} (required: v18+)")
                return ok
            else:
                check("Node.js version", True, version_str)
                return True
        else:
            check("Node.js version", False, "node command failed")
            return False
    except FileNotFoundError:
        check("Node.js installed", False, "node not found on PATH - install from nodejs.org")
        return False
    except Exception as e:
        warn("Node.js check", str(e))
        return True  # Assume OK if we can't check

def main():
    print(f"\n{CYAN}{'=' * 60}{RESET}")
    print(f"{CYAN}  Embodier Trading System — Preflight Check{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")

    checks = []

    # Critical checks
    info("1. Critical Dependencies")
    checks.append(("Python version", check_python_version()))
    checks.append(("Python packages", check_python_packages()))
    checks.append(("Node.js", check_node()))
    checks.append((".env file", check_env_file()))
    checks.append(("DuckDB directory", check_duckdb_dir()))

    # Environment variables
    info("\n2. Environment Configuration")
    check_env_vars()

    # Port availability
    info("\n3. Port Availability")
    checks.append(("Backend port", check_port(8000, "Backend API")))
    checks.append(("Frontend port", check_port(3000, "Frontend Dev Server")))
    check_port(50051, "Brain Service (optional)")

    # Summary
    critical_passed = all(passed for _, passed in checks)

    print(f"\n{CYAN}{'=' * 60}{RESET}")
    if critical_passed:
        print(f"{GREEN}✅ Preflight check PASSED — ready to start{RESET}")
        print(f"\nRun: {CYAN}./start-embodier.ps1{RESET} (Windows) or {CYAN}docker-compose up -d{RESET}\n")
        return 0
    else:
        print(f"{RED}❌ Preflight check FAILED — fix errors above{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
