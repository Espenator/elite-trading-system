#!/usr/bin/env python3
"""
bridge_sender.py - OpenClaw -> Elite Trading System Signal Sender

Sends scored OpenClaw signals TO Elite's POST /openclaw/signals endpoint.
This is the PC1 -> PC2 direction (complementing lstm_bridge_service.py
which handles PC2 -> PC1 polling).

v2.0: Added real-time Blackboard subscriber that listens for
FLOW_AUDITED + SCORED_SIGNALS topics and pushes to Elite PC2
immediately (sub-second latency, no caching).

Usage:
    python bridge_sender.py              # Send test signal
    python bridge_sender.py --health     # Health check only
    python bridge_sender.py --realtime   # Start real-time bridge listener
"""

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from config import ELITE_API_URL, ELITE_API_PREFIX

logger = logging.getLogger(__name__)

# ============================================================
# Configuration
# ============================================================
ELITE_INGEST_ENDPOINT = f"{ELITE_API_URL}{ELITE_API_PREFIX}/openclaw/signals"
OPENCLAW_BRIDGE_TOKEN = os.getenv("OPENCLAW_BRIDGE_TOKEN", "")
HTTPX_TIMEOUT = 15.0


async def send_signals_to_elite(
    signals: List[Dict[str, Any]],
    regime: Optional[Dict[str, Any]] = None,
    universe: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a batch of scored signals to Elite Trading System."""
    if not signals:
        return {"run_id": None, "accepted": 0, "error": "No signals provided"}

    run_id = run_id or (
        f"openclaw_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        f"_{uuid.uuid4().hex[:8]}"
    )

    payload = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "regime": regime,
        "universe": universe,
        "signals": signals,
    }

    async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT) as client:
        resp = await client.post(
            ELITE_INGEST_ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-OpenClaw-Token": OPENCLAW_BRIDGE_TOKEN,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def check_elite_health() -> Dict[str, Any]:
    """Check if Elite Trading System API is reachable."""
    health_url = f"{ELITE_API_URL}{ELITE_API_PREFIX}/openclaw/health"
    async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT) as client:
        resp = await client.get(health_url)
        resp.raise_for_status()
        return resp.json()


# ============================================================
# Real-Time Blackboard Subscriber (v2.0)
# Subscribes to FLOW_AUDITED + SCORED_SIGNALS on the Blackboard
# and POSTs each signal to Elite PC2 immediately.
# ============================================================
class EliteBridgeListener:
    """Real-time bridge: listens to Blackboard topics and pushes to Elite."""

    def __init__(self):
        self._stats = {"sent": 0, "errors": 0, "last_sent": None}
        self._running = False

    async def _push_one(self, payload: Dict):
        """Push a single signal payload to Elite PC2."""
        try:
            result = await send_signals_to_elite(
                signals=[payload],
                regime={"state": payload.get("regime", "GREEN")},
            )
            self._stats["sent"] += 1
            self._stats["last_sent"] = datetime.now().isoformat()
            ticker = payload.get("ticker", payload.get("symbol", "?"))
            logger.info(
                f"[EliteBridge] Pushed {ticker} to Elite "
                f"(accepted={result.get('accepted', '?')})"
            )
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"[EliteBridge] Push failed: {e}")

    async def run_realtime(self):
        """Subscribe to Blackboard topics and push signals in real-time."""
        try:
            from streaming_engine import get_blackboard, Topic, BlackboardMessage
        except ImportError:
            logger.error("[EliteBridge] Cannot import streaming_engine")
            return

        bb = get_blackboard()
        flow_q = await bb.subscribe("flow_audited", "elite_bridge_flow")
        scored_q = await bb.subscribe("scored_signals", "elite_bridge_scored")
        logger.info("[EliteBridge] Listening on flow_audited + scored_signals")
        self._running = True

        while self._running:
            try:
                # Poll both queues with short timeout for sub-second latency
                for q in [flow_q, scored_q]:
                    try:
                        msg = await asyncio.wait_for(q.get(), timeout=0.25)
                        if isinstance(msg, BlackboardMessage) and not msg.is_expired():
                            await self._push_one(msg.payload)
                    except asyncio.TimeoutError:
                        pass
                await bb.heartbeat("elite_bridge_sender")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[EliteBridge] Loop error: {e}")
                await asyncio.sleep(1)

        logger.info(f"[EliteBridge] Stopped. Stats: {self._stats}")


# ============================================================
# CLI
# ============================================================
async def _test_bridge():
    """CLI test: health check + send a test signal."""
    print(f"Elite endpoint: {ELITE_INGEST_ENDPOINT}")
    print(f"Token configured: {'YES' if OPENCLAW_BRIDGE_TOKEN else 'NO'}")

    # Health check
    try:
        health = await check_elite_health()
        print(f"Health check: {health.get('status', 'unknown')}")
    except Exception as e:
        print(f"Health check FAILED: {e}")
        return

    # Send test signal
    test_signals = [{
        "symbol": "TEST",
        "direction": "LONG",
        "score": 85.0,
        "subscores": {"technical": 80, "flow": 90},
        "entry": 100.0,
        "stop": 98.0,
        "target": 105.0,
        "reasons": ["Bridge test signal"],
    }]

    try:
        result = await send_signals_to_elite(
            signals=test_signals,
            regime={"state": "GREEN", "confidence": 0.9},
        )
        print(f"SUCCESS: {result}")
    except httpx.HTTPStatusError as e:
        print(f"HTTP ERROR {e.response.status_code}: {e.response.text}")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    if "--health" in sys.argv:
        asyncio.run(check_elite_health())
    elif "--realtime" in sys.argv:
        print("Starting real-time Elite bridge listener...")
        listener = EliteBridgeListener()
        asyncio.run(listener.run_realtime())
    else:
        asyncio.run(_test_bridge())
