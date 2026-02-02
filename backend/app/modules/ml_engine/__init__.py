"""
ML / Algorithms Engine — learning, signal fusion, regime and risk.

Consumes Symbol Universe, Social/News, Chart Patterns, and execution outcomes;
produces signal scores, regime, sit-out flags, and insights for UI.
"""

# Placeholder: real implementation will use River, XGBoost, etc.
def get_status() -> dict:
    """Return ML engine status (model_loaded, last_trained, error). For glass-box UI."""
    return {"status": "stopped", "model_loaded": False, "last_trained": None, "error": None}


def get_latest_signals(limit: int = 20) -> list:
    """Return latest signal scores per symbol. Stub for now."""
    return []
