"""Unusual Whales API service and incremental poller.

Architecture decision
---------------------
The Unusual Whales API exposes only REST (HTTP/JSON) endpoints — there is
no WebSocket or Server-Sent-Events interface.  The correct pattern is
therefore an **incremental poller** with durable cursor/timestamp
checkpointing and event-level deduplication so the system:

1. Never re-publishes an event that was already emitted (dedupe).
2. Resumes from the last-seen cursor after a restart (checkpoint).
3. Emits normalised :class:`~app.models.source_event.SourceEvent` objects
   to the ``perception.unusualwhales`` MessageBus topic.

The original :class:`UnusualWhalesService` is preserved unchanged so that
all existing callers continue to work.  :class:`UnusualWhalesPoller` wraps
it and adds the incremental/checkpoint layer.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set

import httpx

from app.core.config import settings
from app.core.message_bus import get_message_bus

logger = logging.getLogger(__name__)

# Maximum number of seen event-IDs kept in the checkpoint.
# Older entries are pruned once the set exceeds this size.
_MAX_SEEN_IDS = 5_000

# Keys used inside CheckpointStore
_KEY_LAST_TS = "unusual_whales:last_ts"
_KEY_SEEN_IDS = "unusual_whales:seen_ids"


def _extract_alerts(data: Any) -> List[Dict]:
    """Normalise the various response shapes the UW API can return."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "items", "alerts", "results"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def _event_id(alert: Dict) -> str:
    """Return a stable SHA-256 hex-digest for *alert*.

    Uses the native ``id`` field when present; otherwise hashes a
    deterministic subset of stable content fields.
    """
    if alert.get("id"):
        return str(alert["id"])
    # Build a canonical string from the most stable content fields.
    stable = json.dumps(
        {
            "ticker": alert.get("ticker") or alert.get("symbol") or "",
            "option_type": alert.get("option_type") or alert.get("type") or "",
            "expiry": alert.get("expiry") or alert.get("expiration_date") or "",
            "strike": alert.get("strike") or alert.get("strike_price") or "",
            "traded_at": (
                alert.get("traded_at") or alert.get("date") or alert.get("created_at") or ""
            ),
        },
        sort_keys=True,
    )
    return hashlib.sha256(stable.encode()).hexdigest()[:32]


def _event_timestamp(alert: Dict) -> float:
    """Return the alert's Unix timestamp (float), falling back to now."""
    for field in ("traded_at", "created_at", "date", "timestamp"):
        raw = alert.get(field)
        if not raw:
            continue
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            # Try ISO-8601 string parsing
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return dt.timestamp()
            except ValueError:
                pass
    return time.time()


class UnusualWhalesService:
    """Service for Unusual Whales options flow API."""

    def __init__(self):
        self.base_url = (
            getattr(settings, "UNUSUAL_WHALES_BASE_URL", None)
            or "https://api.unusualwhales.com/api"
        ).rstrip("/")
        self.api_key = (getattr(settings, "UNUSUAL_WHALES_API_KEY", None) or "").strip()
        flow_path = (getattr(settings, "UNUSUAL_WHALES_FLOW_PATH", None) or "").strip()
        self.flow_path = flow_path or "/option-trades/flow-alerts"
        if not self.flow_path.startswith("/"):
            self.flow_path = "/" + self.flow_path

    def _validate_api_key(self) -> None:
        if not self.api_key:
            raise ValueError(
                "UNUSUAL_WHALES_API_KEY is not set. Set it in .env for options flow (see api.unusualwhales.com/docs)."
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    async def get_flow_alerts(self) -> Any:
        """
        Fetch flow alerts from the configured flow path.
        Returns raw response JSON (list or dict with count/total/items).
        """
        self._validate_api_key()
        url = f"{self.base_url}{self.flow_path}"
        logger.debug("Unusual Whales get_flow_alerts: %s", url)
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        if not r.content:
            return []
        data = r.json()

        # Publish to MessageBus so downstream consumers (council, screeners) receive flow data
        try:
            bus = get_message_bus()
            if bus._running:
                await bus.publish("perception.unusualwhales", {
                    "type": "unusual_whales_alerts",
                    "alerts": data,
                    "source": "unusual_whales_service",
                    "timestamp": time.time(),
                })
        except Exception:
            pass

        return data

    async def get_flow_count(self) -> int:
        """
        Get number of flow entries from the last response (for logging).
        Returns 0 if response is not a list or has no count/total.
        """
        try:
            data = await self.get_flow_alerts()
            if isinstance(data, list):
                return len(data)
            if isinstance(data, dict):
                return int(data.get("count") or data.get("total") or 0)
            return 0
        except Exception:
            return 0

    async def get_congress_trades(self) -> Any:
        """Fetch congress trading activity (paid plan)."""
        self._validate_api_key()
        url = f"{self.base_url}/congress/trading"
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json() if r.content else []

    async def get_insider_trades(self) -> Any:
        """Fetch insider trading activity (paid plan)."""
        self._validate_api_key()
        url = f"{self.base_url}/insider/trading"
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json() if r.content else []

    async def get_darkpool_flow(self) -> Any:
        """Fetch dark pool transaction data (paid plan)."""
        self._validate_api_key()
        url = f"{self.base_url}/darkpool/recent"
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json() if r.content else []


# ---------------------------------------------------------------------------
# Incremental poller — polling-only API, checkpoint + dedupe layer
# ---------------------------------------------------------------------------

class UnusualWhalesPoller:
    """Incremental poller for the Unusual Whales REST API.

    Polls the flow-alerts endpoint on a configurable interval and
    publishes only **new** (not-yet-seen) events to the MessageBus topic
    ``perception.unusualwhales``.  State is durable: the last-seen
    timestamp and the seen-IDs set survive restarts via
    :class:`~app.data.checkpoint_store.CheckpointStore`.

    Usage::

        poller = UnusualWhalesPoller()
        await poller.start()   # runs until poller.stop() is called
        ...
        await poller.stop()
    """

    def __init__(
        self,
        poll_interval: float = 60.0,
        checkpoint_store=None,
        service: Optional[UnusualWhalesService] = None,
    ) -> None:
        self._poll_interval = poll_interval
        self._service = service or UnusualWhalesService()
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Lazy import to avoid circular imports at module load time
        if checkpoint_store is None:
            from app.data.checkpoint_store import CheckpointStore
            checkpoint_store = CheckpointStore()
        self._store = checkpoint_store

        # In-memory cache of seen IDs (loaded from checkpoint on start)
        self._seen_ids: Set[str] = set()
        self._last_ts: float = 0.0
        self._stats = {
            "polls": 0,
            "new_events": 0,
            "duplicate_events": 0,
            "errors": 0,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Load checkpoint state and begin polling loop."""
        if self._running:
            return
        self._running = True
        self._load_checkpoint()
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(
            "UnusualWhalesPoller started (interval=%.0fs, cursor=%.0f, seen_ids=%d)",
            self._poll_interval,
            self._last_ts,
            len(self._seen_ids),
        )

    async def stop(self) -> None:
        """Stop polling and save final checkpoint."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._save_checkpoint()
        logger.info(
            "UnusualWhalesPoller stopped — polls=%d new=%d dupes=%d errors=%d",
            self._stats["polls"],
            self._stats["new_events"],
            self._stats["duplicate_events"],
            self._stats["errors"],
        )

    # ------------------------------------------------------------------
    # Core poll logic (also callable directly in tests)
    # ------------------------------------------------------------------

    async def poll_once(self) -> int:
        """Execute one poll cycle.

        Fetches alerts, deduplicates, publishes new events, updates
        checkpoint, and returns the number of **new** events emitted.
        """
        from app.models.source_event import SourceEvent

        try:
            data = await self._service.get_flow_alerts()
        except ValueError:
            # Missing API key — not an error condition worth logging as error
            logger.debug("UnusualWhalesPoller: API key not configured, skipping poll")
            return 0
        except Exception as exc:
            self._stats["errors"] += 1
            logger.warning("UnusualWhalesPoller: fetch error: %s", exc)
            return 0

        alerts = _extract_alerts(data)
        if not alerts:
            return 0

        new_count = 0
        max_ts = self._last_ts
        bus = get_message_bus()

        for alert in alerts:
            evt_id = _event_id(alert)
            evt_ts = _event_timestamp(alert)

            if evt_id in self._seen_ids:
                self._stats["duplicate_events"] += 1
                continue

            # New event — emit it
            symbol = (alert.get("ticker") or alert.get("symbol") or "").upper() or None
            event = SourceEvent(
                source="unusual_whales",
                event_type="flow_alert",
                event_id=evt_id,
                timestamp=evt_ts,
                symbol=symbol,
                payload=alert,
            )

            try:
                if bus._running:
                    await bus.publish(
                        "perception.unusualwhales",
                        event.to_bus_payload(),
                    )
            except Exception as pub_exc:
                logger.warning("UnusualWhalesPoller: publish error: %s", pub_exc)

            self._seen_ids.add(evt_id)
            max_ts = max(max_ts, evt_ts)
            new_count += 1
            self._stats["new_events"] += 1

        # Advance cursor and prune stale seen-IDs
        if max_ts > self._last_ts:
            self._last_ts = max_ts

        self._prune_seen_ids()
        self._save_checkpoint()
        self._stats["polls"] += 1
        return new_count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Background coroutine: poll repeatedly until stopped."""
        while self._running:
            await self.poll_once()
            # Use short sleep slices so stop() is responsive
            elapsed = 0.0
            while self._running and elapsed < self._poll_interval:
                await asyncio.sleep(1.0)
                elapsed += 1.0

    def _load_checkpoint(self) -> None:
        self._last_ts = float(self._store.get(_KEY_LAST_TS, 0.0))
        raw = self._store.get(_KEY_SEEN_IDS, [])
        self._seen_ids = set(raw) if isinstance(raw, list) else set()

    def _save_checkpoint(self) -> None:
        self._store.set(_KEY_LAST_TS, self._last_ts)
        self._store.set(_KEY_SEEN_IDS, list(self._seen_ids))

    def _prune_seen_ids(self) -> None:
        """Keep the seen-IDs set bounded to avoid unbounded memory growth."""
        if len(self._seen_ids) > _MAX_SEEN_IDS:
            # Convert to list, drop oldest half (approximate — set has no order)
            keep = list(self._seen_ids)[_MAX_SEEN_IDS // 2:]
            self._seen_ids = set(keep)

    @property
    def stats(self) -> Dict:
        """Return a snapshot of poller statistics."""
        return dict(self._stats)


# ---------------------------------------------------------------------------
# Module-level singleton + convenience function aliases
# ---------------------------------------------------------------------------

# A module-level singleton used by autonomous_scout and other ad-hoc callers.
# It is NOT auto-started — callers that want incremental polling should use
# UnusualWhalesPoller directly.
unusual_whales_service = UnusualWhalesService()


async def get_flow_alerts(symbol: Optional[str] = None) -> Any:
    """Module-level convenience wrapper for :meth:`UnusualWhalesService.get_flow_alerts`."""
    return await unusual_whales_service.get_flow_alerts()


async def get_insider_trades(symbol: Optional[str] = None) -> Any:
    """Module-level convenience wrapper for insider trades."""
    return await unusual_whales_service.get_insider_trades()


async def get_dark_pool_flow(symbol: Optional[str] = None) -> Any:
    """Module-level convenience wrapper for dark pool flow."""
    return await unusual_whales_service.get_darkpool_flow()


async def get_institutional_flow(symbol: Optional[str] = None) -> Any:
    """Module-level convenience wrapper — returns flow alerts as proxy for institutional flow."""
    return await unusual_whales_service.get_flow_alerts()


async def get_options_chain(symbol: Optional[str] = None) -> Any:
    """Module-level convenience wrapper — returns flow alerts as options chain proxy."""
    return await unusual_whales_service.get_flow_alerts()
