"""Adapter initialization - explicit startup wiring for data stream adapters.

This module centralizes initialization logic for:
- AlpacaStreamManager (multi-key WebSocket orchestrator)
- Symbol universe loading
- Stream health monitoring

Goals:
- Make adapter dependencies explicit
- Reduce duplication between main.py and market_data_agent.py
- Preserve event-driven flow
"""
import asyncio
import logging
from typing import List, Optional, Any

logger = logging.getLogger(__name__)


async def create_alpaca_stream_manager(
    message_bus,
    *,
    default_symbols: Optional[List[str]] = None,
) -> Optional[Any]:
    """Create and configure AlpacaStreamManager with explicit dependencies.

    Args:
        message_bus: MessageBus instance (required dependency)
        default_symbols: Fallback symbols if symbol_universe is empty

    Returns:
        AlpacaStreamManager instance or None if disabled/failed

    Raises:
        No exceptions - logs errors and returns None on failure
    """
    import os

    # Check if disabled via env var
    if os.getenv("DISABLE_ALPACA_DATA_STREAM", "").strip().lower() in ("1", "true", "yes"):
        logger.info("AlpacaStreamManager skipped (DISABLE_ALPACA_DATA_STREAM=1)")
        return None

    # Load tracked symbols from symbol universe
    symbols = await _load_tracked_symbols(default_symbols)

    if not symbols:
        logger.warning("AlpacaStreamManager: no symbols available, using defaults")
        symbols = default_symbols or [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
            "TSLA", "META", "SPY", "QQQ", "IWM",
        ]

    try:
        from app.services.alpaca_stream_manager import AlpacaStreamManager

        manager = AlpacaStreamManager(message_bus, symbols)
        logger.info(
            "✅ AlpacaStreamManager created (%d symbols, multi-key aware)",
            len(symbols)
        )
        return manager

    except Exception as e:
        logger.exception("AlpacaStreamManager creation failed: %s", e)
        return None


async def _load_tracked_symbols(fallback: Optional[List[str]] = None) -> List[str]:
    """Load tracked symbols from symbol_universe module.

    This is the canonical source of truth for which symbols to stream.
    Updated by market_data_agent via Finviz Elite scraping.

    Args:
        fallback: Default symbols if module is unavailable

    Returns:
        List of symbol tickers (empty list if unavailable)
    """
    try:
        from app.modules.symbol_universe import get_tracked_symbols
        tracked = get_tracked_symbols()

        if tracked:
            logger.info("Loaded %d tracked symbols from symbol_universe", len(tracked))
            return list(tracked)
        else:
            logger.info("symbol_universe returned empty, using fallback")
            return fallback or []

    except Exception as e:
        logger.warning("Failed to load tracked symbols: %s (using fallback)", e)
        return fallback or []


async def start_alpaca_stream_manager(manager) -> Optional[asyncio.Task]:
    """Start AlpacaStreamManager and return background task.

    Args:
        manager: AlpacaStreamManager instance

    Returns:
        asyncio.Task for the running stream or None if manager is None
    """
    if manager is None:
        return None

    try:
        task = asyncio.create_task(manager.start())
        logger.info("✅ AlpacaStreamManager task launched")
        return task

    except Exception as e:
        logger.exception("AlpacaStreamManager start failed: %s", e)
        return None
