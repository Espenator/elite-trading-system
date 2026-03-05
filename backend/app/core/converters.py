"""Shared type conversion utilities used across API routes and services."""

from typing import Any


def safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert a value to float with fallback to default."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val: Any, default: int = 0) -> int:
    """Safely convert a value to int with fallback to default."""
    if val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default
