"""Shared regime execution parameters — max_pos, kelly_scale, signal_mult.

Used by OrderExecutor (Gate 2b regime enforcement) and strategy API.
Import from here to avoid service→API layering violations.
"""
REGIME_PARAMS = {
    "GREEN": {"kelly_scale": 1.5, "max_pos": 6, "risk_pct": 2.0, "signal_mult": 1.10, "min_edge": 0.03, "desc": "Momentum - full Kelly, higher conviction"},
    "YELLOW": {"kelly_scale": 1.0, "max_pos": 5, "risk_pct": 1.5, "signal_mult": 1.0, "min_edge": 0.05, "desc": "Cautious - reduced sizing, tighter filters"},
    "RED": {"kelly_scale": 0.25, "max_pos": 0, "risk_pct": 0.0, "signal_mult": 0.85, "min_edge": 0.12, "desc": "Defensive - no new positions, protect capital"},
    "RED_RECOVERY": {"kelly_scale": 0.75, "max_pos": 4, "risk_pct": 1.0, "signal_mult": 0.95, "min_edge": 0.08, "desc": "Re-entry - cautious scaling back in"},
    # Legacy aliases for backward compatibility
    "BULL": {"kelly_scale": 1.5, "max_pos": 6, "risk_pct": 2.0, "signal_mult": 1.10, "min_edge": 0.03, "desc": "Alias for GREEN"},
    "NEUTRAL": {"kelly_scale": 1.0, "max_pos": 5, "risk_pct": 1.5, "signal_mult": 1.0, "min_edge": 0.05, "desc": "Alias for YELLOW"},
    "BEAR": {"kelly_scale": 0.25, "max_pos": 0, "risk_pct": 0.0, "signal_mult": 0.85, "min_edge": 0.12, "desc": "Alias for RED"},
    "CRISIS": {"kelly_scale": 0.0, "max_pos": 0, "risk_pct": 0.0, "signal_mult": 0.0, "min_edge": 1.0, "desc": "Full cash, zero exposure"},
}
