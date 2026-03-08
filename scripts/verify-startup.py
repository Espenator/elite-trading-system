#!/usr/bin/env python3
"""Verify that all critical backend endpoints are responding correctly.

This script is run AFTER startup to confirm the system is operational.

Usage:
    python scripts/verify-startup.py [--url http://localhost:8000]

Exit codes:
- 0: All checks passed
- 1: One or more checks failed
"""

import sys
import argparse
import time

try:
    import requests
except ImportError:
    print("ERROR: requests package not found. Install with: pip install requests")
    sys.exit(1)

from typing import Tuple

RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def test_endpoint(url: str, name: str, timeout: int = 5) -> Tuple[bool, str]:
    """Test an HTTP endpoint."""
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return True, f"OK ({r.status_code})"
        elif r.status_code == 503:
            return False, f"Service unavailable ({r.status_code})"
        else:
            return False, f"Status {r.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="Verify backend startup")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--wait", type=int, default=0, help="Wait N seconds before checking")
    args = parser.parse_args()

    base_url = args.url

    if args.wait > 0:
        print(f"{CYAN}Waiting {args.wait} seconds for backend to start...{RESET}")
        time.sleep(args.wait)

    print(f"\n{CYAN}{'=' * 60}{RESET}")
    print(f"{CYAN}  Startup Verification{RESET}")
    print(f"{CYAN}  Target: {base_url}{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")

    tests = [
        (f"{base_url}/healthz", "Liveness probe"),
        (f"{base_url}/readyz", "Readiness probe"),
        (f"{base_url}/health", "Health diagnostics"),
        (f"{base_url}/api/v1/status", "Status API"),
        (f"{base_url}/api/v1/council/status", "Council status"),
        (f"{base_url}/docs", "API documentation"),
    ]

    all_passed = True
    for url, name in tests:
        passed, details = test_endpoint(url, name)
        symbol = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        print(f"  {symbol} {name:30} {details}")
        if not passed:
            all_passed = False

    print(f"\n{CYAN}{'=' * 60}{RESET}")
    if all_passed:
        print(f"{GREEN}✅ All checks passed — system is operational{RESET}\n")
        return 0
    else:
        print(f"{RED}❌ Some checks failed — see errors above{RESET}")
        print(f"{YELLOW}Tip: Check logs/backend.log for error details{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
