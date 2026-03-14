"""Stale Order Cleanup — Issue #76.

Cancels all unfilled orders older than 1 day on server boot.
Runs once at startup as a background task.

Usage (in main.py lifespan):
    from app.services.stale_order_cleanup import cancel_stale_orders
    asyncio.create_task(cancel_stale_orders())
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


async def cancel_stale_orders(max_age_hours: int = 24) -> dict:
    """Cancel all open/unfilled orders older than max_age_hours.

    Called once at server startup. Wraps everything in try/except
    to never block the startup sequence.

    Returns dict with cancellation results.
    """
    results = {"cancelled": [], "errors": [], "total_open": 0}

    try:
        from app.services.alpaca_service import alpaca_service

        # Fetch all open orders
        orders = await alpaca_service.get_orders(status="open", limit=200)
        if not orders:
            logger.info("Stale order cleanup: no open orders found")
            return results

        results["total_open"] = len(orders)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        for order in orders:
            order_id = order.get("id", "")
            symbol = order.get("symbol", "?")
            status = order.get("status", "")
            created_at = order.get("created_at", "")

            # Skip already-terminal orders
            if status in ("filled", "cancelled", "expired", "replaced"):
                continue

            # Parse creation time
            try:
                if created_at:
                    # Alpaca returns ISO format: 2026-03-14T10:30:00Z
                    created_dt = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    if created_dt > cutoff:
                        continue  # Not stale yet
                else:
                    continue  # No timestamp — skip to be safe
            except (ValueError, TypeError):
                continue

            # Cancel stale order
            try:
                result = await alpaca_service.cancel_order(order_id)
                if result is not None:
                    results["cancelled"].append({
                        "order_id": order_id,
                        "symbol": symbol,
                        "status": status,
                        "created_at": created_at,
                    })
                    logger.info(
                        "Cancelled stale order: %s %s (created %s, status=%s)",
                        order_id, symbol, created_at, status,
                    )
                else:
                    results["errors"].append({
                        "order_id": order_id,
                        "symbol": symbol,
                        "error": "cancel returned None",
                    })
            except Exception as e:
                results["errors"].append({
                    "order_id": order_id,
                    "symbol": symbol,
                    "error": str(e),
                })
                logger.warning("Failed to cancel stale order %s: %s", order_id, e)

        cancelled_count = len(results["cancelled"])
        error_count = len(results["errors"])
        logger.info(
            "Stale order cleanup complete: %d open orders, %d cancelled, %d errors",
            results["total_open"], cancelled_count, error_count,
        )

    except Exception as e:
        logger.warning("Stale order cleanup failed (non-fatal): %s", e)
        results["errors"].append({"error": str(e)})

    return results
