#!/usr/bin/env python3
"""
Live Trading Setup Verification Script
Checks all external dependencies required for live trading.

Usage:
    cd backend
    python scripts/verify_live_trading_setup.py
"""
import os
import sys
import socket
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def check(name: str) -> bool:
    """Print check name and return a context manager for status."""
    print(f"  Checking {name}...", end=" ")
    return True


def success(msg: str = "OK"):
    """Print success message."""
    print(f"{GREEN}✅ {msg}{RESET}")


def warning(msg: str):
    """Print warning message."""
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def error(msg: str):
    """Print error message."""
    print(f"{RED}❌ {msg}{RESET}")


def info(msg: str):
    """Print info message."""
    print(f"{BLUE}ℹ️  {msg}{RESET}")


class SetupVerifier:
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_warnings = 0
        self.errors: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []

    def verify_network(self) -> bool:
        """Verify network connectivity to external APIs."""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}1. Network Connectivity{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        endpoints = [
            ("Alpaca Paper API", "paper-api.alpaca.markets", 443),
            ("Alpaca Data API", "data.alpaca.markets", 443),
            ("FRED API", "api.stlouisfed.org", 443),
            ("NewsAPI", "newsapi.org", 443),
        ]

        all_passed = True
        for name, host, port in endpoints:
            check(name)
            try:
                socket.create_connection((host, port), timeout=5)
                success()
                self.checks_passed += 1
            except (socket.gaierror, socket.timeout, OSError) as e:
                error(f"Failed - {e}")
                self.checks_failed += 1
                self.errors.append((name, f"Cannot reach {host}:{port}"))
                all_passed = False

        return all_passed

    def verify_env_file(self) -> bool:
        """Verify .env file exists and has required keys."""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}2. Environment Configuration{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        env_path = Path("..") / ".env"  # Relative to backend/scripts/
        if not env_path.exists():
            env_path = Path(".env")  # Try current directory

        check(".env file")
        if not env_path.exists():
            error("Not found")
            self.checks_failed += 1
            self.errors.append((".env file", "File does not exist. Copy from .env.example"))
            return False

        success("Found")
        self.checks_passed += 1

        # Load .env (simple parser, doesn't handle all edge cases)
        env_vars = {}
        try:
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            error(f"Failed to parse .env: {e}")
            return False

        # Check critical settings
        critical_keys = [
            ("ALPACA_API_KEY", "Alpaca API key"),
            ("ALPACA_SECRET_KEY", "Alpaca secret key"),
            ("LLM_ENABLED", "LLM enabled flag"),
        ]

        for key, description in critical_keys:
            check(description)
            value = env_vars.get(key, "")
            if not value or value in ("your-alpaca-live-api-key", "test-key", ""):
                warning(f"Not set or using placeholder")
                self.checks_warnings += 1
                self.warnings.append((description, f"{key} should be set to a real value"))
            elif key == "LLM_ENABLED" and value.lower() not in ("true", "1", "yes"):
                warning(f"LLM disabled (council will not run)")
                self.checks_warnings += 1
                self.warnings.append(("LLM", "Set LLM_ENABLED=true to enable council"))
            else:
                success("Set")
                self.checks_passed += 1

        # Check recommended settings
        recommended_keys = [
            ("FRED_API_KEY", "FRED API key (FREE)"),
            ("FERNET_KEY", "Encryption key"),
            ("API_AUTH_TOKEN", "API auth token"),
        ]

        for key, description in recommended_keys:
            check(description)
            value = env_vars.get(key, "")
            if not value or value.startswith("your-"):
                warning("Not set (recommended)")
                self.checks_warnings += 1
                self.warnings.append((description, f"{key} recommended for production"))
            else:
                success("Set")
                self.checks_passed += 1

        return True

    def verify_llm(self) -> bool:
        """Verify LLM service (Ollama) is accessible."""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}3. LLM Service (Ollama){RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        check("Ollama service")
        try:
            import httpx
            resp = httpx.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                success("Running")
                self.checks_passed += 1

                # Check for models
                data = resp.json()
                models = data.get("models", [])
                check("Available models")
                if models:
                    model_names = [m["name"] for m in models]
                    success(f"{len(models)} found: {', '.join(model_names[:3])}")
                    self.checks_passed += 1
                else:
                    warning("No models downloaded")
                    self.checks_warnings += 1
                    self.warnings.append(("Ollama models", "Run: ollama pull llama3.2"))

                return True
            else:
                error(f"HTTP {resp.status_code}")
                self.checks_failed += 1
                self.errors.append(("Ollama", "Service responding but returned error"))
                return False
        except ImportError:
            warning("httpx not installed (skipping LLM check)")
            info("Install: pip install httpx")
            self.checks_warnings += 1
            return True
        except Exception as e:
            error(f"Not accessible - {e}")
            self.checks_failed += 1
            self.errors.append(("Ollama", "Service not running. Start: ollama serve"))
            return False

    def verify_database(self) -> bool:
        """Verify database files exist and are accessible."""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}4. Database Files{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        db_files = [
            ("SQLite database", Path("data/elite_trading.db")),
            ("DuckDB analytics", Path("data/analytics.duckdb")),
        ]

        for name, path in db_files:
            check(name)
            if path.exists():
                size_mb = path.stat().st_size / 1024 / 1024
                success(f"Found ({size_mb:.1f} MB)")
                self.checks_passed += 1
            else:
                warning("Not found (will be created on startup)")
                self.checks_warnings += 1

        # Check DuckDB has data
        check("DuckDB historical data")
        try:
            import duckdb
            conn = duckdb.connect("data/analytics.duckdb", read_only=True)
            result = conn.execute("SELECT COUNT(*) FROM daily_ohlcv").fetchone()
            row_count = result[0] if result else 0
            conn.close()

            if row_count > 0:
                success(f"{row_count} rows")
                self.checks_passed += 1
            else:
                warning("Empty (no historical data)")
                self.checks_warnings += 1
                self.warnings.append(
                    ("Historical data", "Backfill: python -m app.jobs.backfill_bars --symbol SPY --days 365")
                )
        except ImportError:
            warning("duckdb not installed (skipping)")
            self.checks_warnings += 1
        except Exception as e:
            warning(f"Cannot query DuckDB: {e}")
            self.checks_warnings += 1

        return True

    def verify_python_deps(self) -> bool:
        """Verify Python dependencies are installed."""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}5. Python Dependencies{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        critical_packages = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "pandas",
            "numpy",
            "duckdb",
            "alpaca",
        ]

        for package in critical_packages:
            check(package)
            try:
                __import__(package.replace("-", "_"))
                success("Installed")
                self.checks_passed += 1
            except ImportError:
                error("Missing")
                self.checks_failed += 1
                self.errors.append((package, f"Install: pip install {package}"))

        # Optional packages
        optional_packages = [
            ("torch", "PyTorch (for LSTM models)"),
            ("httpx", "HTTP client (for external APIs)"),
        ]

        for package, description in optional_packages:
            check(description)
            try:
                __import__(package)
                success("Installed")
                self.checks_passed += 1
            except ImportError:
                warning("Not installed (optional)")
                self.checks_warnings += 1

        return True

    def verify_ports(self) -> bool:
        """Verify required ports are available."""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}6. Port Availability{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        ports = [
            (8000, "Backend API"),
            (3000, "Frontend dev server (optional)"),
        ]

        for port, service in ports:
            check(f"Port {port} ({service})")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()

            if result == 0:
                warning(f"Already in use (service may be running)")
                self.checks_warnings += 1
            else:
                success("Available")
                self.checks_passed += 1

        return True

    def print_summary(self):
        """Print verification summary."""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}VERIFICATION SUMMARY{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        print(f"\n{GREEN}✅ Passed: {self.checks_passed}{RESET}")
        print(f"{YELLOW}⚠️  Warnings: {self.checks_warnings}{RESET}")
        print(f"{RED}❌ Failed: {self.checks_failed}{RESET}")

        if self.errors:
            print(f"\n{RED}Critical Errors:{RESET}")
            for name, msg in self.errors:
                print(f"  • {name}: {msg}")

        if self.warnings:
            print(f"\n{YELLOW}Warnings:{RESET}")
            for name, msg in self.warnings:
                print(f"  • {name}: {msg}")

        print(f"\n{BLUE}{'='*60}{RESET}")

        if self.checks_failed == 0:
            if self.checks_warnings == 0:
                print(f"{GREEN}🎉 All checks passed! Ready for live trading.{RESET}")
                print(f"\n{BLUE}Next steps:{RESET}")
                print("  1. Start backend: python start_server.py")
                print("  2. Start frontend: cd frontend-v2 && npm run dev")
                print("  3. Open browser: http://localhost:3000")
                return 0
            else:
                print(f"{YELLOW}✅ Core functionality ready, but some warnings present.{RESET}")
                print(f"{YELLOW}Review warnings above and fix for production deployment.{RESET}")
                print(f"\n{BLUE}You can start in test mode:{RESET}")
                print("  python start_server.py")
                return 0
        else:
            print(f"{RED}❌ Critical errors detected. Fix errors before proceeding.{RESET}")
            print(f"\n{BLUE}See LIVE_TRADING_SETUP.md for detailed setup instructions.{RESET}")
            return 1

    def run_all(self) -> int:
        """Run all verification checks."""
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Elite Trading System - Live Trading Setup Verification{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        self.verify_network()
        self.verify_env_file()
        self.verify_llm()
        self.verify_database()
        self.verify_python_deps()
        self.verify_ports()

        return self.print_summary()


def main():
    """Main entry point."""
    # Change to backend directory if running from scripts/
    if Path(__file__).parent.name == "scripts":
        os.chdir(Path(__file__).parent.parent)

    verifier = SetupVerifier()
    exit_code = verifier.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
