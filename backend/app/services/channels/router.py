from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Tuple

import httpx

from app.services.channels.schemas import SensoryEvent

logger = logging.getLogger(__name__)


class SensoryRouter:
    """Routes SensoryEvent into MessageBus topics with minimal enrichment."""

    def __init__(self, message_bus: Any):
        self._bus = message_bus
        self._metrics: Dict[str, int] = {
            "events_routed": 0,
            "events_failed": 0,
            "events_to_awareness": 0,
        }

        self._awareness_mode = os.getenv("AWARENESS_MODE", "topic").strip().lower()
        self._awareness_url = os.getenv("PC2_BRAIN_URL", "") or os.getenv("AWARENESS_URL", "")
        self._awareness_timeout_s = float(os.getenv("AWARENESS_TIMEOUT_S", "6.0"))

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self._metrics)

    async def route_and_publish(self, event: SensoryEvent) -> List[str]:
        topics, payloads = self._route(event)

        published: List[str] = []
        for topic, payload in zip(topics, payloads):
            await self._bus.publish(topic, payload)
            published.append(topic)

        self._metrics["events_routed"] += 1
        return published

    def _route(self, event: SensoryEvent) -> Tuple[List[str], List[Dict[str, Any]]]:
        topics: List[str] = []
        payloads: List[Dict[str, Any]] = []

        if os.getenv("INGEST_PUBLISH_RAW", "true").lower() in ("1", "true", "yes"):
            topics.append("ingest.raw")
            payloads.append({"event": event.model_dump(mode="json")})

        if event.source == "alpaca" and event.event_type == "bar":
            bar = dict(event.raw)
            bar["event_id"] = event.event_id
            topics.append("market_data.bar")
            payloads.append(bar)

            if self._is_attention_worthy_bar(event):
                idea = self._bar_to_idea(event)
                topics.append("swarm.idea")
                payloads.append(idea)

        elif event.source == "discord":
            idea = self._discord_to_idea(event)
            topics.append("swarm.idea")
            payloads.append(idea)

        elif event.source == "unusual_whales":
            idea = self._uw_to_idea(event)
            topics.append("swarm.idea")
            payloads.append(idea)
        elif event.source == "finviz":
            idea = self._finviz_to_idea(event)
            topics.append("swarm.idea")
            payloads.append(idea)
        elif event.source == "news":
            idea = self._news_to_idea(event)
            topics.append("swarm.idea")
            payloads.append(idea)
        else:
            if event.event_type in ("idea", "anomaly", "alert", "news", "options_flow", "dark_pool", "filing", "screener_hit"):
                topics.append("swarm.idea")
                payloads.append(self._generic_to_idea(event))

        if self._should_send_to_awareness(event):
            event.routing.to_awareness = True
            self._metrics["events_to_awareness"] += 1
            if self._awareness_mode == "http" and self._awareness_url:
                asyncio.create_task(self._send_to_awareness_http(event))
            else:
                topics.append("ingest.to_awareness")
                payloads.append({"event": event.model_dump(mode="json")})

        event.routing.topics = list(dict.fromkeys(topics))
        return topics, payloads

    def _is_attention_worthy_bar(self, event: SensoryEvent) -> bool:
        try:
            close = float(event.normalized.get("close") or 0)
            open_ = float(event.normalized.get("open") or close)
            vol = float(event.normalized.get("volume") or 0)
            if close <= 0 or open_ <= 0:
                return False
            ret = abs((close - open_) / open_)
            ret_th = float(os.getenv("FIREHOSE_BAR_RET_TH", "0.02"))
            vol_th = float(os.getenv("FIREHOSE_BAR_VOL_TH", "500000"))
            return ret >= ret_th or vol >= vol_th
        except Exception:
            return False

    def _bar_to_idea(self, event: SensoryEvent) -> Dict[str, Any]:
        sym = (event.symbols[0] if event.symbols else "").upper()
        close = event.normalized.get("close")
        vol = event.normalized.get("volume")
        reasoning = f"Firehose bar anomaly: {sym} close={close} volume={vol}"
        return {
            "source": f"firehose:alpaca:{sym}",
            "symbols": [sym] if sym else [],
            "direction": "unknown",
            "reasoning": reasoning,
            "raw_content": "",
            "priority": 2,
            "metadata": {
                "event_id": event.event_id,
                "sensory": event.model_dump(mode="json"),
            },
            "tags": list(dict.fromkeys(event.tags + ["anomaly", "alpaca"])),
            "data_quality": event.data_quality,
            "alignment_preflight_required": True,
        }

    def _discord_to_idea(self, event: SensoryEvent) -> Dict[str, Any]:
        text = (event.normalized.get("text") or "")[:2000]
        direction = event.normalized.get("direction") or "unknown"
        channel = event.normalized.get("channel") or "unknown"
        reasoning = f"Discord [{channel}]: {text[:300]}"
        return {
            "source": "discord",
            "symbols": event.symbols[:5],
            "direction": direction,
            "reasoning": reasoning,
            "raw_content": text,
            "priority": max(1, min(5, int((100 - event.priority) / 20) + 1)),
            "metadata": {
                "event_id": event.event_id,
                "sensory": event.model_dump(mode="json"),
            },
            "tags": list(dict.fromkeys(event.tags)),
            "data_quality": event.data_quality,
            "alignment_preflight_required": True,
        }

    def _uw_to_idea(self, event: SensoryEvent) -> Dict[str, Any]:
        """Build swarm.idea payload for Unusual Whales flow/congress/insider/darkpool."""
        sym = (event.symbols[0] if event.symbols else "").upper()
        premium = event.normalized.get("premium")
        payload_type = event.normalized.get("payload_type") or event.event_type
        reasoning = f"UW {event.event_type}: {sym}"
        if premium is not None:
            reasoning += f" premium={premium}"
        reasoning += f" type={payload_type}"
        return {
            "source": "firehose:unusual_whales",
            "symbols": event.symbols[:5],
            "direction": "unknown",
            "reasoning": reasoning,
            "raw_content": str(event.raw.get("data", ""))[:2000],
            "priority": 3,
            "metadata": {"event_id": event.event_id, "sensory": event.model_dump(mode="json")},
            "tags": list(dict.fromkeys(event.tags)),
            "data_quality": event.data_quality,
            "alignment_preflight_required": True,
        }

    def _finviz_to_idea(self, event: SensoryEvent) -> Dict[str, Any]:
        """Build swarm.idea payload for Finviz screener hit."""
        sym = (event.symbols[0] if event.symbols else "").upper()
        price = event.normalized.get("price")
        change_pct = event.normalized.get("change_pct")
        reasoning = f"Finviz screener: {sym}"
        if price is not None:
            reasoning += f" price={price}"
        if change_pct is not None:
            reasoning += f" change={change_pct}"
        return {
            "source": "firehose:finviz",
            "symbols": event.symbols[:5],
            "direction": "unknown",
            "reasoning": reasoning,
            "raw_content": str(event.raw)[:2000],
            "priority": 2,
            "metadata": {"event_id": event.event_id, "sensory": event.model_dump(mode="json")},
            "tags": list(dict.fromkeys(event.tags)),
            "data_quality": event.data_quality,
            "alignment_preflight_required": True,
        }

    def _news_to_idea(self, event: SensoryEvent) -> Dict[str, Any]:
        """Build swarm.idea payload for news headline."""
        headline = (event.normalized.get("headline") or event.normalized.get("text") or "")[:500]
        source = event.normalized.get("news_source") or "news"
        urgency = event.normalized.get("urgency") or "background"
        direction = "unknown"
        if event.normalized.get("sentiment") == "bullish":
            direction = "bullish"
        elif event.normalized.get("sentiment") == "bearish":
            direction = "bearish"
        reasoning = f"[{urgency.upper()}] {headline[:200]}"
        return {
            "source": "firehose:news",
            "symbols": event.symbols[:5],
            "direction": direction,
            "reasoning": reasoning,
            "raw_content": headline,
            "priority": 1 if urgency == "breaking" else (3 if urgency == "developing" else 5),
            "metadata": {
                "event_id": event.event_id,
                "sensory": event.model_dump(mode="json"),
                "news_source": source,
                "urgency": urgency,
            },
            "tags": list(dict.fromkeys(event.tags)),
            "data_quality": event.data_quality,
            "alignment_preflight_required": True,
        }

    def _generic_to_idea(self, event: SensoryEvent) -> Dict[str, Any]:
        return {
            "source": f"firehose:{event.source}",
            "symbols": event.symbols[:5],
            "direction": event.normalized.get("direction", "unknown"),
            "reasoning": event.normalized.get("reasoning", f"{event.source}:{event.event_type}"),
            "raw_content": (event.normalized.get("text") or "")[:2000],
            "priority": 3,
            "metadata": {"event_id": event.event_id, "sensory": event.model_dump(mode="json")},
            "tags": list(dict.fromkeys(event.tags)),
            "data_quality": event.data_quality,
            "alignment_preflight_required": True,
        }

    def _should_send_to_awareness(self, event: SensoryEvent) -> bool:
        if os.getenv("AWARENESS_MODE", "topic").strip().lower() in ("off", "false", "0", "disabled"):
            return False
        if event.source in ("discord", "news", "youtube", "x"):
            return True
        if event.event_type in ("news", "transcript", "social_post", "alert", "idea", "anomaly"):
            txt = str(event.normalized.get("text") or "")
            return len(txt) >= 80
        return False

    async def _send_to_awareness_http(self, event: SensoryEvent) -> None:
        url = self._awareness_url.rstrip("/") + "/awareness/enrich"
        payload = {"events": [event.model_dump(mode="json")]}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self._awareness_timeout_s)) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code >= 400:
                    logger.debug("Awareness enrich HTTP %s: %s", resp.status_code, resp.text[:200])
                    return
                data = resp.json()
            await self._bus.publish("ingest.awareness_enriched", {"result": data, "event_id": event.event_id})
        except Exception as exc:
            logger.debug("Awareness HTTP failed: %s", exc)
