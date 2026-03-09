"""Unified Embodier Trader Backend Server Entry Point.

Combines development and production (PyInstaller bundle) support.
Replaces both start_server.py and run_server.py with a single entry point.

Usage:
    python server.py                    # Development mode with settings
    python server.py --frozen           # Simulates PyInstaller bundle mode
    ./embodier-backend.exe              # PyInstaller bundle (auto-detects)

Environment Variables:
    HOST                - Server host (default: from settings or 0.0.0.0)
    PORT                - Server port (default: from settings or 8000)
    DEBUG               - Enable hot-reload (default: from settings)
    LOG_LEVEL           - Logging level (default: from settings or INFO)
"""
import os
import sys
import argparse


def setup_frozen_environment():
    """Configure environment for PyInstaller bundle execution."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        bundle_dir = os.path.dirname(sys.executable)
        os.chdir(bundle_dir)
        sys.path.insert(0, bundle_dir)
        return True
    return False


def validate_environment():
    """Validate critical environment variables before startup.

    Returns:
        bool: True if validation passed, False otherwise
    """
    from pathlib import Path

    # Check .env file exists
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print(f"⚠️  WARNING: .env file not found at {env_file}")
        print("   Copy .env.example to .env and configure your API keys.")
        print("   Continuing with environment variables only...")

    # Check critical env vars
    alpaca_key = os.getenv("ALPACA_API_KEY", "")
    if not alpaca_key or alpaca_key.startswith("your-"):
        print("⚠️  WARNING: ALPACA_API_KEY not configured")
        print("   Trading features will be disabled.")
        print("   Set ALPACA_API_KEY in .env or environment variables.")

    return True


def main():
    """Main server entry point with unified development and production support."""
    parser = argparse.ArgumentParser(description="Embodier Trader Backend Server")
    parser.add_argument("--frozen", action="store_true",
                       help="Run in frozen/bundle mode (for testing)")
    parser.add_argument("--host", type=str, help="Server host (overrides settings)")
    parser.add_argument("--port", type=int, help="Server port (overrides settings)")
    parser.add_argument("--validate-only", action="store_true",
                       help="Validate environment and exit")
    args = parser.parse_args()

    # Setup frozen environment if needed
    is_frozen = setup_frozen_environment() or args.frozen

    # Validate environment
    if not validate_environment():
        print("\n❌ Environment validation failed. Fix errors above and retry.")
        return 1

    if args.validate_only:
        print("\n✅ Environment validation passed.")
        return 0

    # Import uvicorn after environment setup
    import uvicorn

    # Determine configuration mode
    if is_frozen:
        # PyInstaller bundle mode: simple config from env vars only
        host = args.host or os.getenv("HOST", "0.0.0.0")
        port = args.port or int(os.getenv("PORT", "8000"))
        log_level = os.getenv("LOG_LEVEL", "info").lower()
        reload = False
        access_log = False

        print(f"🚀 Starting in BUNDLE mode (frozen={getattr(sys, 'frozen', False)})")
    else:
        # Development mode: full settings support
        from app.core.config import settings

        host = args.host or settings.HOST
        port = args.port or settings.effective_port
        log_level = settings.LOG_LEVEL.lower()
        reload = settings.DEBUG
        access_log = settings.DEBUG

        print(f"🚀 Starting in DEVELOPMENT mode (debug={settings.DEBUG})")

    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Reload: {reload}")
    print(f"   Log Level: {log_level}")
    print()

    # Start uvicorn server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=reload,
        access_log=access_log,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
