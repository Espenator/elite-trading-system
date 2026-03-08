#!/usr/bin/env python3
"""
fix_indentation.py - Scan and fix Python indentation errors across the backend.

This script:
1. Finds all .py files under backend/
2. Runs py_compile on each to detect syntax/indentation errors
3. Runs autopep8 to auto-fix indentation (if installed)
4. Reports which files still need manual attention

Usage:
    cd elite-trading-system
    pip install autopep8  # one-time install
    python scripts/fix_indentation.py --scan        # scan only, report errors
    python scripts/fix_indentation.py --fix         # auto-fix with autopep8
    python scripts/fix_indentation.py --fix --check # fix then verify

Created: 2026-02-28 by Espen (via Comet)
Assigned to: Oleh - Monday 2026-03-02
"""
import argparse
import os
import py_compile
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent / "backend"

# Known problematic directories
SCAN_DIRS = [
    BACKEND_ROOT / "app" / "api" / "v1",
    BACKEND_ROOT / "app" / "services",
    BACKEND_ROOT / "app" / "schemas",
    BACKEND_ROOT / "app" / "models",
    BACKEND_ROOT / "app" / "core",
    BACKEND_ROOT / "app" / "modules",
    BACKEND_ROOT / "app" / "strategy",
    BACKEND_ROOT / "app",
    BACKEND_ROOT / "tests",
]


def find_python_files():
    """Find all .py files under backend/."""
    seen = set()
    files = []
    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for py_file in scan_dir.rglob("*.py"):
            real = py_file.resolve()
            if real not in seen:
                seen.add(real)
                files.append(py_file)
    return sorted(files)


def scan_file(filepath):
    """Check a single file for syntax errors. Returns error message or None."""
    try:
        py_compile.compile(str(filepath), doraise=True)
        return None
    except py_compile.PyCompileError as e:
        return str(e)


def scan_all():
    """Scan all Python files and report errors."""
    files = find_python_files()
    print(f"Scanning {len(files)} Python files under {BACKEND_ROOT}...")
    print("=" * 70)

    errors = []
    clean = 0

    for f in files:
        rel = f.relative_to(BACKEND_ROOT.parent)
        err = scan_file(f)
        if err:
            errors.append((rel, err))
            print(f"  FAIL  {rel}")
            # Extract just the error line for readability
            for line in err.split("\n"):
                if "Error" in line or "indent" in line.lower():
                    print(f"         -> {line.strip()}")
        else:
            clean += 1

    print("=" * 70)
    print(f"Results: {clean} OK, {len(errors)} FAILED out of {len(files)} files")

    if errors:
        print("\nFiles needing fixes:")
        for rel, err in errors:
            print(f"  - {rel}")
        return 1
    else:
        print("\nAll files compile successfully!")
        return 0


def fix_with_autopep8():
    """Run autopep8 on all Python files to fix indentation."""
    # Check if autopep8 is installed
    try:
        import autopep8  # noqa: F401
    except ImportError:
        print("ERROR: autopep8 not installed. Run: pip install autopep8")
        return 1

    files = find_python_files()
    print(f"Fixing {len(files)} Python files with autopep8...")
    print("=" * 70)

    fixed = 0
    for f in files:
        rel = f.relative_to(BACKEND_ROOT.parent)
        # Read original
        original = f.read_text(encoding="utf-8")

        # Run autopep8 in-place with aggressive mode for indentation
        result = subprocess.run(
            [
                sys.executable, "-m", "autopep8",
                "--in-place",
                "--aggressive",
                "--aggressive",
                "--max-line-length", "120",
                "--indent-size", "4",
                str(f),
            ],
            capture_output=True,
            text=True,
        )

        # Check if file changed
        after = f.read_text(encoding="utf-8")
        if original != after:
            fixed += 1
            print(f"  FIXED {rel}")
        else:
            print(f"  ok    {rel}")

    print("=" * 70)
    print(f"Fixed {fixed} files out of {len(files)}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Scan and fix Python indentation errors in the backend."
    )
    parser.add_argument(
        "--scan", action="store_true",
        help="Scan only - report files with syntax/indentation errors"
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Auto-fix files using autopep8"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="After fixing, verify all files compile"
    )
    args = parser.parse_args()

    if not args.scan and not args.fix:
        print("Usage: python scripts/fix_indentation.py --scan    (report only)")
        print("       python scripts/fix_indentation.py --fix     (auto-fix)")
        print("       python scripts/fix_indentation.py --fix --check (fix + verify)")
        return 1

    if args.scan:
        return scan_all()

    if args.fix:
        rc = fix_with_autopep8()
        if rc != 0:
            return rc
        if args.check:
            print("\nVerifying fixes...")
            return scan_all()
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
