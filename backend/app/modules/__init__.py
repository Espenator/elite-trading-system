"""
Modular components for the Elite Trading System.

See MODULAR_ARCHITECTURE.md at repo root for the full design.
- symbol_universe: Stock/symbol database and watchlists
- social_news_engine: Real-time social media and news search/compute
- chart_patterns: Pattern library and detection pipeline
- ml_engine: ML and algorithms (signal fusion, learning)
- execution_engine: Paper/live order execution (Alpaca)
"""

__all__ = [
    "symbol_universe",
    "social_news_engine",
    "chart_patterns",
    "ml_engine",
    "execution_engine",
]
