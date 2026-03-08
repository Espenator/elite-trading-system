"""WebSocket bridge registration - centralized event-to-WS forwarding.

This module provides explicit registration of MessageBus event topics
to WebSocket channels, making the bridge configuration auditable and
maintainable.

All bridges follow the pattern:
    MessageBus topic -> WebSocket channel -> Frontend subscribers
"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def register_all_bridges(message_bus) -> Dict[str, str]:
    """Register all event-to-WebSocket bridges.

    Args:
        message_bus: MessageBus instance (required dependency)

    Returns:
        Dict mapping topic to WS channel (for audit/debugging)
    """
    from app.websocket_manager import broadcast_ws

    bridges = {}

    # Signal bridge: signal.generated -> WS "signal"
    async def _bridge_signal_to_ws(signal_data):
        try:
            await broadcast_ws("signal", {"type": "new_signal", "signal": signal_data})
        except Exception as e:
            logger.debug("WS broadcast failed (signal): %s", e)

    await message_bus.subscribe("signal.generated", _bridge_signal_to_ws)
    bridges["signal.generated"] = "signal"
    logger.info("✅ Signal->WebSocket bridge active")

    # Order bridges: order.* -> WS "order"
    async def _bridge_order_to_ws(order_data):
        try:
            await broadcast_ws("order", {"type": "order_update", "order": order_data})
        except Exception as e:
            logger.debug("WS order broadcast failed: %s", e)

    await message_bus.subscribe("order.submitted", _bridge_order_to_ws)
    await message_bus.subscribe("order.filled", _bridge_order_to_ws)
    await message_bus.subscribe("order.cancelled", _bridge_order_to_ws)
    bridges["order.submitted"] = "order"
    bridges["order.filled"] = "order"
    bridges["order.cancelled"] = "order"
    logger.info("✅ Order->WebSocket bridges active")

    # Council bridge: council.verdict -> WS "council"
    async def _bridge_council_to_ws(verdict_data):
        try:
            await broadcast_ws("council", {"type": "council_verdict", "verdict": verdict_data})
        except Exception as e:
            logger.debug("WS council broadcast failed: %s", e)

    await message_bus.subscribe("council.verdict", _bridge_council_to_ws)
    bridges["council.verdict"] = "council"
    logger.info("✅ Council->WebSocket bridge active")

    # Market data bridge: market_data.bar -> WS "market"
    async def _bridge_market_data_to_ws(bar_data):
        try:
            await broadcast_ws("market", {"type": "price_update", "bar": bar_data})
        except Exception as e:
            logger.debug("WS market broadcast failed: %s", e)

    await message_bus.subscribe("market_data.bar", _bridge_market_data_to_ws)
    bridges["market_data.bar"] = "market"
    logger.info("✅ MarketData->WebSocket bridge active")

    # Swarm bridge: swarm.result -> WS "swarm"
    async def _bridge_swarm_to_ws(result_data):
        try:
            await broadcast_ws("swarm", {"type": "swarm_result", "result": result_data})
        except Exception as e:
            logger.debug("WS swarm broadcast failed: %s", e)

    await message_bus.subscribe("swarm.result", _bridge_swarm_to_ws)
    bridges["swarm.result"] = "swarm"
    logger.info("✅ Swarm->WebSocket bridge active")

    # Macro event bridge: scout.discovery -> WS "risk"
    async def _bridge_macro_to_ws(event_data):
        try:
            await broadcast_ws("risk", {"type": "macro_event", "event": event_data})
        except Exception as e:
            logger.debug("WS macro broadcast failed: %s", e)

    await message_bus.subscribe("scout.discovery", _bridge_macro_to_ws)
    bridges["scout.discovery"] = "risk"
    logger.info("✅ MacroEvent->WebSocket bridge active")

    logger.info("✅ WebSocket bridges registered (%d topic->channel mappings)", len(bridges))
    return bridges


async def register_persistence_handler(message_bus) -> None:
    """Register market_data.bar -> DuckDB persistence handler.

    This is separate from WebSocket bridges because it's a critical
    data path, not a UI convenience.

    Args:
        message_bus: MessageBus instance (required dependency)
    """
    async def _persist_bar_to_duckdb(bar_data):
        """Write a market_data.bar event to DuckDB daily_ohlcv table (non-blocking)."""
        try:
            from app.data.duckdb_storage import duckdb_store

            symbol = bar_data.get("symbol")
            timestamp = bar_data.get("timestamp", "")
            if not symbol or not timestamp:
                return

            # Extract date from timestamp (could be ISO format or date string)
            date_str = str(timestamp)[:10]  # YYYY-MM-DD

            await duckdb_store.async_insert(
                """
                INSERT OR REPLACE INTO daily_ohlcv (symbol, date, open, high, low, close, volume, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    symbol,
                    date_str,
                    float(bar_data.get("open") or 0),
                    float(bar_data.get("high") or 0),
                    float(bar_data.get("low") or 0),
                    float(bar_data.get("close") or 0),
                    int(bar_data.get("volume") or 0),
                    bar_data.get("source", "stream"),
                ],
            )
        except Exception as e:
            logger.debug("DuckDB bar persist failed: %s", e)

    await message_bus.subscribe("market_data.bar", _persist_bar_to_duckdb)
    logger.info("✅ market_data.bar -> DuckDB persistence subscriber active")
