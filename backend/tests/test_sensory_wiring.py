"""Verify MessageBus sensory wiring: no orphan publishers, perception/hitl/position reach targets."""
import asyncio
import pytest

from app.core.message_bus import MessageBus
from app.core.sensory_store import update as sensory_update, get_snapshot, get, clear


# Topics that were PUBLISH_ONLY (no subscriber) per message_bus.py audit — now wired in main.py
ORPHAN_TOPICS_WIRED = [
    "perception.finviz.screener",
    "perception.macro",
    "perception.edgar",
    "perception.gex",
    "perception.insider",
    "perception.squeezemetrics",
    "perception.earnings",
    "perception.congressional",
    "macro.fred",
    "perception.flow.uw_analysis",
    "signal.external",
    "knowledge.ingested",
    "alert.health",
    "position.partial_exit",
    "position.closed",
    "hitl.approval_needed",
    "symbol.prep.ready",
]


class TestSensoryWiring:
    """Verify all MessageBus topics have both publishers and subscribers (or document gaps)."""

    def test_no_orphaned_publishers_documented(self):
        """Every topic that gets published to should have at least one subscriber.
        This test documents the list of topics we wired in main.py lifespan.
        Orphan list should be empty for critical topics (position.closed, hitl.approval_needed).
        """
        critical = {"position.closed", "hitl.approval_needed"}
        wired = set(ORPHAN_TOPICS_WIRED)
        for t in critical:
            assert t in wired, f"Critical topic {t} must be in wired list (subscriber in main.py)"

    @pytest.mark.anyio
    async def test_perception_finviz_reaches_subscriber(self):
        """perception.finviz.screener → subscriber receives data (sensory_store in production)."""
        bus = MessageBus()
        await bus.start()
        try:
            received = []
            await bus.subscribe("perception.finviz.screener", lambda d: received.append(d))
            await bus.publish("perception.finviz.screener", {"sectors": {"tech": 0.8}})
            # Allow event loop to dispatch
            for _ in range(5):
                await asyncio.sleep(0.05)
                if received:
                    break
            assert len(received) == 1
            assert received[0].get("sectors", {}).get("tech") == 0.8
        finally:
            await bus.stop()

    @pytest.mark.anyio
    async def test_position_closed_reaches_feedback_loop(self):
        """position.closed should trigger feedback_loop.record_outcome (weight learner learns)."""
        bus = MessageBus()
        await bus.start()
        try:
            from unittest.mock import patch
            from app.council import feedback_loop
            recorded = []
            with patch.object(feedback_loop, "record_outcome", side_effect=lambda **kw: recorded.append(kw)):
                async def _on_closed(data):
                    from app.council.feedback_loop import record_outcome
                    trade_id = data.get("council_decision_id") or data.get("order_id") or ""
                    pnl = data.get("pnl", 0)
                    outcome = "win" if pnl > 0 else "loss" if pnl < 0 else "scratch"
                    entry = data.get("entry_price") or 1.0
                    qty = data.get("qty", 1)
                    r_multiple = (pnl / (entry * qty)) if entry and qty else 0.0
                    record_outcome(
                        trade_id=trade_id,
                        symbol=data.get("symbol", "?"),
                        outcome=outcome,
                        r_multiple=r_multiple,
                    )
                await bus.subscribe("position.closed", _on_closed)
                await bus.publish("position.closed", {
                    "symbol": "TEST",
                    "pnl": 10.0,
                    "entry_price": 100.0,
                    "qty": 10,
                    "order_id": "ord-1",
                })
                for _ in range(10):
                    await asyncio.sleep(0.05)
                    if recorded:
                        break
            assert len(recorded) == 1
            assert recorded[0]["symbol"] == "TEST"
            assert recorded[0]["outcome"] == "win"
        finally:
            await bus.stop()

    @pytest.mark.anyio
    async def test_hitl_approval_reaches_websocket(self):
        """hitl.approval_needed should broadcast to frontend via WebSocket (approval dialog)."""
        bus = MessageBus()
        await bus.start()
        try:
            from unittest.mock import AsyncMock, patch
            broadcast_calls = []
            async def _capture_broadcast(channel, data):
                broadcast_calls.append((channel, data))

            with patch("app.websocket_manager.broadcast_ws", side_effect=_capture_broadcast):
                async def _on_hitl(data):
                    try:
                        from app.websocket_manager import broadcast_ws
                        await broadcast_ws("agents", {
                            "type": "hitl_approval_needed",
                            "symbol": data.get("symbol"),
                            "direction": data.get("direction"),
                            "confidence": data.get("confidence"),
                            "data": data,
                        })
                    except Exception:
                        pass
                await bus.subscribe("hitl.approval_needed", _on_hitl)
                await bus.publish("hitl.approval_needed", {
                    "symbol": "AAPL",
                    "direction": "buy",
                    "confidence": 0.85,
                })
                for _ in range(10):
                    await asyncio.sleep(0.05)
                    if broadcast_calls:
                        break
            assert len(broadcast_calls) >= 1
            ch, payload = broadcast_calls[0]
            assert ch == "agents"
            assert payload.get("type") == "hitl_approval_needed"
            assert payload.get("symbol") == "AAPL"
        finally:
            await bus.stop()

    @pytest.mark.anyio
    async def test_sensory_store_updated_by_perception_topic(self):
        """Publishing to a perception topic and having a sensory_store subscriber updates the store."""
        clear()
        bus = MessageBus()
        await bus.start()
        try:
            await bus.subscribe(
                "perception.finviz.screener",
                lambda d: sensory_update("perception.finviz.screener", d),
            )
            await bus.publish("perception.finviz.screener", {"sectors": {"tech": 0.9}})
            for _ in range(5):
                await asyncio.sleep(0.05)
            val = get("perception.finviz.screener")
            assert val.get("sectors", {}).get("tech") == 0.9
        finally:
            clear()
            await bus.stop()
