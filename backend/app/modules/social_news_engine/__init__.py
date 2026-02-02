"""
Social / News Engine — real-time search and compute over social media and news.

Ingests Twitter/X, Reddit, news APIs; computes sentiment and correlations;
outputs time-stamped signals per symbol/theme for the ML engine.
"""

# Placeholder: real implementation will run scanners on a schedule or on-demand
def get_status() -> dict:
    """Return engine status (running, last_run, error). For glass-box UI."""
    return {"status": "stopped", "last_run": None, "error": None}


def run_scan_now() -> dict:
    """Run one scan now; return summary. Stub for now."""
    return {"status": "not_implemented", "message": "Add data sources and compute pipeline"}
