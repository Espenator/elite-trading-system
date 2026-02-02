"""
Chart Patterns — pattern library and detection pipeline.

Defines and detects patterns (e.g. head & shoulders, flags); stores results;
outputs (symbol, pattern_type, timeframe, confidence) for the ML engine.
"""

# Placeholder: real implementation will use OHLCV and pattern definitions
def get_status() -> dict:
    """Return detector status (enabled, last_run, error). For glass-box UI."""
    return {"status": "stopped", "last_run": None, "error": None}


def get_recent_detections(limit: int = 20) -> list:
    """Return recent pattern detections. Stub for now."""
    return []
