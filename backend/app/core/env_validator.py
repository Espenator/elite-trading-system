"""Environment validation for Elite Trading System backend.

This module provides fail-fast validation of environment variables
before the FastAPI application starts. It checks for:
- Required configuration (Alpaca keys)
- Optional integrations (Unusual Whales, Finviz, etc.)
- Database paths and permissions
- Port availability
- Feature flag consistency

Usage:
    from app.core.env_validator import validate_env_or_exit

    # In main.py lifespan or startup
    validate_env_or_exit(fail_fast=True)
"""

import os
import sys
import socket
from pathlib import Path
from typing import Dict, List, Tuple
import logging

log = logging.getLogger(__name__)


class EnvValidationError(Exception):
    """Raised when critical environment validation fails."""
    pass


def check_port_available(port: int) -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex(("127.0.0.1", port))
            return result != 0  # Port is available if connect fails
    except Exception:
        return True  # Assume available if we can't check


def validate_env_vars() -> Tuple[List[str], List[str]]:
    """Validate environment variables.

    Returns:
        Tuple[List[str], List[str]]: (errors, warnings)
    """
    errors = []
    warnings = []

    # Required variables
    alpaca_key = os.getenv("ALPACA_API_KEY", "")
    alpaca_secret = os.getenv("ALPACA_SECRET_KEY", "")

    if not alpaca_key or alpaca_key.startswith("your-"):
        warnings.append("ALPACA_API_KEY not configured - trading features will be disabled")

    if not alpaca_secret or alpaca_secret.startswith("your-"):
        warnings.append("ALPACA_SECRET_KEY not configured - trading features will be disabled")

    # Optional but recommended
    optional_keys = {
        "UNUSUAL_WHALES_API_KEY": "Options flow data",
        "FINVIZ_API_KEY": "Stock screener",
        "FRED_API_KEY": "Economic data",
        "NEWS_API_KEY": "News headlines",
    }

    for key, desc in optional_keys.items():
        val = os.getenv(key, "")
        if not val or val.startswith("your-"):
            log.debug(f"{key} not configured - {desc} will be unavailable")

    # Feature flag consistency
    brain_enabled = os.getenv("BRAIN_ENABLED", "false").lower() in ("true", "1", "yes")
    if brain_enabled:
        brain_host = os.getenv("BRAIN_HOST", "localhost")
        brain_port = int(os.getenv("BRAIN_PORT", "50051"))
        log.info(f"Brain service enabled - expecting gRPC at {brain_host}:{brain_port}")

    llm_enabled = os.getenv("LLM_ENABLED", "true").lower() in ("true", "1", "yes")
    if llm_enabled and not brain_enabled:
        warnings.append("LLM_ENABLED=true but BRAIN_ENABLED=false - LLM features may be limited")

    return errors, warnings


def validate_database_path() -> List[str]:
    """Validate database path exists and is writable.

    Returns:
        List[str]: List of errors
    """
    errors = []

    # Check data directory
    backend_dir = Path(__file__).parent.parent
    data_dir = backend_dir / "data"

    if not data_dir.exists():
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"Created database directory: {data_dir}")
        except Exception as e:
            errors.append(f"Cannot create database directory {data_dir}: {e}")
            return errors

    if not os.access(data_dir, os.W_OK):
        errors.append(f"Database directory {data_dir} is not writable")

    return errors


def validate_ports() -> List[str]:
    """Validate required ports are available.

    Returns:
        List[str]: List of warnings about port conflicts
    """
    warnings = []

    port = int(os.getenv("PORT", "8000"))
    if not check_port_available(port):
        warnings.append(f"Port {port} may already be in use - startup may fail")

    # Check brain service port if enabled
    brain_enabled = os.getenv("BRAIN_ENABLED", "false").lower() in ("true", "1", "yes")
    if brain_enabled:
        brain_port = int(os.getenv("BRAIN_PORT", "50051"))
        brain_host = os.getenv("BRAIN_HOST", "localhost")
        if brain_host in ("localhost", "127.0.0.1"):
            if not check_port_available(brain_port):
                warnings.append(f"Brain service port {brain_port} may already be in use")

    return warnings


def validate_environment(fail_fast: bool = False) -> bool:
    """Validate complete environment before startup.

    Args:
        fail_fast: If True, raise exception on critical errors

    Returns:
        bool: True if validation passed

    Raises:
        EnvValidationError: If fail_fast=True and critical errors found
    """
    all_errors = []
    all_warnings = []

    # Run all validations
    env_errors, env_warnings = validate_env_vars()
    all_errors.extend(env_errors)
    all_warnings.extend(env_warnings)

    db_errors = validate_database_path()
    all_errors.extend(db_errors)

    port_warnings = validate_ports()
    all_warnings.extend(port_warnings)

    # Log results
    if all_errors:
        log.error("=" * 60)
        log.error("ENVIRONMENT VALIDATION FAILED")
        log.error("=" * 60)
        for error in all_errors:
            log.error(f"❌ {error}")
        log.error("=" * 60)

        if fail_fast:
            raise EnvValidationError(
                f"Environment validation failed with {len(all_errors)} errors. "
                "Fix the errors above and restart."
            )
        return False

    if all_warnings:
        log.warning("=" * 60)
        log.warning("ENVIRONMENT VALIDATION WARNINGS")
        log.warning("=" * 60)
        for warning in all_warnings:
            log.warning(f"⚠️  {warning}")
        log.warning("=" * 60)

    if not all_errors and not all_warnings:
        log.info("✅ Environment validation passed - all checks OK")
    elif not all_errors:
        log.info(f"✅ Environment validation passed with {len(all_warnings)} warnings")

    return True


def validate_env_or_exit(fail_fast: bool = True):
    """Validate environment or exit process.

    Args:
        fail_fast: If True, exit(1) on critical errors
    """
    try:
        if not validate_environment(fail_fast=fail_fast):
            if fail_fast:
                log.error("Exiting due to environment validation failures")
                sys.exit(1)
    except EnvValidationError as e:
        log.error(str(e))
        if fail_fast:
            sys.exit(1)
