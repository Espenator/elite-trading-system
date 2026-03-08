"""OpenClaw bridge adapter — snapshot/incremental with dedupe.

Wraps the existing ``openclaw_bridge`` service and emits normalised events
for regime, candidates, and whale flow onto the appropriate perception topics.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict

from app.services.ingestion.base import BaseSourceAdapter
from app.services.ingestion.models import SourceEvent, SourceKind

logger = logging.getLogger(__name__)


class OpenClawAdapter(BaseSourceAdapter):
    source_name = "openclaw"
    source_kind = SourceKind.SNAPSHOT
    poll_interval_seconds = 60.0

    async def poll_once(self) -> None:
        from app.services.openclaw_bridge_service import openclaw_bridge

        health = await openclaw_bridge.get_health()
        if not health.get("connected"):
            if not health.get("gist_id_configured"):
                return  # No Gist ID — nothing to fetch
            return

        # Regime
        try:
            regime = await openclaw_bridge.get_regime()
            regime_hash = hashlib.md5(str(regime).encode()).hexdigest()
            prev_hash = self._checkpoint.get("regime_hash", "")
            if regime_hash != prev_hash:
                self._checkpoint["regime_hash"] = regime_hash
                event = SourceEvent(
                    source=self.source_name,
                    source_kind=self.source_kind,
                    topic="perception.regime.openclaw",
                    payload={
                        "type": "regime_update",
                        "data": regime,
                        "source": "openclaw_adapter",
                        "timestamp": time.time(),
                    },
                    dedupe_key=f"openclaw-regime-{regime_hash}",
                )
                await self.publish_event(event)
        except Exception as exc:
            logger.warning("OpenClaw regime fetch failed: %s", exc)

        # Candidates
        try:
            candidates = await openclaw_bridge.get_top_candidates(n=10)
            cand_hash = hashlib.md5(str(candidates).encode()).hexdigest()
            prev_cand = self._checkpoint.get("candidates_hash", "")
            if cand_hash != prev_cand:
                self._checkpoint["candidates_hash"] = cand_hash
                event = SourceEvent(
                    source=self.source_name,
                    source_kind=self.source_kind,
                    topic="perception.scanner.daily",
                    payload={
                        "type": "openclaw_candidates",
                        "candidates": candidates,
                        "count": len(candidates),
                        "source": "openclaw_adapter",
                        "timestamp": time.time(),
                    },
                    dedupe_key=f"openclaw-cand-{cand_hash}",
                )
                await self.publish_event(event)
        except Exception as exc:
            logger.warning("OpenClaw candidates fetch failed: %s", exc)

        # Whale flow
        try:
            whale_flow = await openclaw_bridge.get_whale_flow()
            flow_hash = hashlib.md5(str(whale_flow).encode()).hexdigest()
            prev_flow = self._checkpoint.get("flow_hash", "")
            if flow_hash != prev_flow:
                self._checkpoint["flow_hash"] = flow_hash
                event = SourceEvent(
                    source=self.source_name,
                    source_kind=self.source_kind,
                    topic="perception.flow.whale",
                    payload={
                        "type": "whale_flow",
                        "alerts": whale_flow,
                        "count": len(whale_flow),
                        "source": "openclaw_adapter",
                        "timestamp": time.time(),
                    },
                    dedupe_key=f"openclaw-flow-{flow_hash}",
                )
                await self.publish_event(event)
        except Exception as exc:
            logger.warning("OpenClaw whale flow fetch failed: %s", exc)

        self._checkpoint["last_poll_at"] = time.time()
