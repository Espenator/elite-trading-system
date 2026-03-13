#!/usr/bin/env python3
"""Run mypy on council + trading for pre-commit. Exits 0 so hook does not block."""
import os
import subprocess
import sys

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend = os.path.join(repo_root, "backend")
targets = [
    "app/council/",
    "app/services/order_executor.py",
    "app/services/kelly_position_sizer.py",
    "app/services/position_manager.py",
]
result = subprocess.run(
    [sys.executable, "-m", "mypy"] + targets + ["--ignore-missing-imports"],
    cwd=backend,
    capture_output=True,
    text=True,
)
if result.returncode != 0 and result.stdout:
    print(result.stdout, end="")
if result.stderr:
    print(result.stderr, end="", file=sys.stderr)
sys.exit(0)  # do not block commit
