"""Services layer — organized into sub-packages for logical grouping.

Sub-packages (all re-export from this flat directory — no import breakage):
    broker/         — Alpaca execution, orders, positions, Kelly sizing
    intelligence/   — LLM routing, Perplexity/Claude reasoning, cognitive telemetry
    scanning/       — Signal engine, TurboScanner, correlation, patterns, news
    trading/        — Outcome tracking, backtesting, walk-forward, unified scorer
    data_sources/   — DuckDB, Finviz, FRED, SEC EDGAR, Unusual Whales
    ml/             — XGBoost scoring, ML training, feature engineering

Remaining flat services (not yet sub-packaged):
    swarm_spawner, hyper_swarm, discord_swarm_bridge  — swarm orchestration
    openclaw_bridge_service, openclaw_db              — OpenClaw integration
    settings_service, knowledge_ingest                — misc utilities

Usage:
    # Old style (still works):
    from app.services.alpaca_service import AlpacaService

    # New style (organized):
    from app.services.broker import alpaca_service
"""
