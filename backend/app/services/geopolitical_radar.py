"""GeopoliticalRadar — continuous real-time macro event detection and response.

This is the system's "always-on" geopolitical awareness layer. It runs
continuously, scanning for high-impact world events and mapping them to
tradeable responses BEFORE the market moves.

When war breaks out tonight:
  1. Radar detects "military conflict" event via Perplexity scan
  2. MacroEventPlaybook maps it -> oil up, gold up, VIX up, equities down
  3. AlertEscalation overrides normal scan intervals -> IMMEDIATE swarm
  4. Swarms spawn for all affected instruments simultaneously
  5. Council evaluates each instrument with the event context injected
  6. Trades execute within seconds of detection

Event Types Detected:
  - Military conflict / war
  - Central bank emergency (rate decisions, interventions)
  - Political crisis (government collapse, sanctions)
  - Natural disaster (with economic impact)
  - Pandemic / health emergency
  - Financial crisis (bank failures, currency collapse)
  - Trade war / tariffs
  - Cyber attack on infrastructure
  - Energy crisis (supply disruption, OPEC decisions)
  - Terrorist attack

Usage:
    radar = GeopoliticalRadar(message_bus)
    await radar.start()  # Starts continuous scanning every 60s
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EventSeverity(str, Enum):
    """How market-moving is this event?"""
    CRITICAL = "critical"   # War, financial crisis — trade immediately
    HIGH = "high"           # Rate surprise, sanctions — trade within minutes
    MEDIUM = "medium"       # Tariff changes, political shift — analyze then trade
    LOW = "low"             # Background noise — log and monitor


class EventType(str, Enum):
    MILITARY_CONFLICT = "military_conflict"
    CENTRAL_BANK = "central_bank"
    POLITICAL_CRISIS = "political_crisis"
    NATURAL_DISASTER = "natural_disaster"
    PANDEMIC = "pandemic"
    FINANCIAL_CRISIS = "financial_crisis"
    TRADE_WAR = "trade_war"
    CYBER_ATTACK = "cyber_attack"
    ENERGY_CRISIS = "energy_crisis"
    TERRORIST_ATTACK = "terrorist_attack"
    EARNINGS_SHOCK = "earnings_shock"
    REGULATORY = "regulatory"
    UNKNOWN = "unknown"


@dataclass
class MacroEvent:
    """A detected macro/geopolitical event."""
    event_type: str
    severity: str
    headline: str
    description: str
    affected_regions: List[str] = field(default_factory=list)
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "perplexity"
    id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "severity": self.severity,
            "headline": self.headline,
            "description": self.description,
            "affected_regions": self.affected_regions,
            "detected_at": self.detected_at,
            "source": self.source,
            "id": self.id,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MACRO EVENT PLAYBOOK — maps events to tradeable instruments
# ═══════════════════════════════════════════════════════════════════════════════

# Each playbook entry: event_type -> list of (symbol, direction, rationale)
MACRO_PLAYBOOK: Dict[str, List[Dict[str, str]]] = {
    EventType.MILITARY_CONFLICT: [
        {"symbol": "USO", "direction": "buy", "rationale": "Oil surges on supply disruption fears"},
        {"symbol": "XLE", "direction": "buy", "rationale": "Energy sector benefits from oil spike"},
        {"symbol": "GLD", "direction": "buy", "rationale": "Gold safe haven bid"},
        {"symbol": "GDX", "direction": "buy", "rationale": "Gold miners follow gold"},
        {"symbol": "ITA", "direction": "buy", "rationale": "Defense/aerospace ETF benefits"},
        {"symbol": "LMT", "direction": "buy", "rationale": "Lockheed Martin — defense spending surge"},
        {"symbol": "RTX", "direction": "buy", "rationale": "Raytheon — defense contractor"},
        {"symbol": "NOC", "direction": "buy", "rationale": "Northrop Grumman — defense"},
        {"symbol": "VIX", "direction": "buy", "rationale": "Volatility spikes on uncertainty"},
        {"symbol": "UVXY", "direction": "buy", "rationale": "Long volatility on fear"},
        {"symbol": "SPY", "direction": "sell", "rationale": "Broad market sells off on war risk"},
        {"symbol": "QQQ", "direction": "sell", "rationale": "Tech sells off on risk-off rotation"},
        {"symbol": "EFA", "direction": "sell", "rationale": "International developed markets sell off"},
        {"symbol": "TLT", "direction": "buy", "rationale": "Treasury flight to safety"},
        {"symbol": "UUP", "direction": "buy", "rationale": "Dollar strengthens as safe haven"},
    ],
    EventType.CENTRAL_BANK: [
        {"symbol": "TLT", "direction": "contextual", "rationale": "Bonds move inversely to rate expectations"},
        {"symbol": "XLF", "direction": "contextual", "rationale": "Financials sensitive to rate changes"},
        {"symbol": "GLD", "direction": "contextual", "rationale": "Gold inversely correlated to real rates"},
        {"symbol": "SPY", "direction": "contextual", "rationale": "Equities react to rate surprise direction"},
        {"symbol": "QQQ", "direction": "contextual", "rationale": "Growth/tech most rate-sensitive"},
        {"symbol": "IWM", "direction": "contextual", "rationale": "Small caps sensitive to credit conditions"},
        {"symbol": "UUP", "direction": "contextual", "rationale": "Dollar moves with rate expectations"},
    ],
    EventType.ENERGY_CRISIS: [
        {"symbol": "USO", "direction": "buy", "rationale": "Oil prices spike on supply fears"},
        {"symbol": "XLE", "direction": "buy", "rationale": "Energy sector outperforms"},
        {"symbol": "UNG", "direction": "buy", "rationale": "Natural gas spike"},
        {"symbol": "XOP", "direction": "buy", "rationale": "Oil & gas exploration benefits"},
        {"symbol": "XLU", "direction": "sell", "rationale": "Utilities hurt by energy costs"},
        {"symbol": "XLI", "direction": "sell", "rationale": "Industrials hurt by input costs"},
        {"symbol": "JETS", "direction": "sell", "rationale": "Airlines crushed by fuel costs"},
    ],
    EventType.FINANCIAL_CRISIS: [
        {"symbol": "GLD", "direction": "buy", "rationale": "Gold safe haven surge"},
        {"symbol": "TLT", "direction": "buy", "rationale": "Flight to treasuries"},
        {"symbol": "UVXY", "direction": "buy", "rationale": "Volatility explosion"},
        {"symbol": "XLF", "direction": "sell", "rationale": "Financials sell off hard"},
        {"symbol": "KRE", "direction": "sell", "rationale": "Regional banks collapse"},
        {"symbol": "SPY", "direction": "sell", "rationale": "Broad market crash"},
        {"symbol": "HYG", "direction": "sell", "rationale": "High yield credit spreads blow out"},
        {"symbol": "UUP", "direction": "buy", "rationale": "Dollar strengthens on deleveraging"},
    ],
    EventType.TRADE_WAR: [
        {"symbol": "EEM", "direction": "sell", "rationale": "Emerging markets hit by trade barriers"},
        {"symbol": "FXI", "direction": "sell", "rationale": "China ETF sells off"},
        {"symbol": "SPY", "direction": "sell", "rationale": "Global trade uncertainty hits equities"},
        {"symbol": "GLD", "direction": "buy", "rationale": "Gold benefits from uncertainty"},
        {"symbol": "XLI", "direction": "sell", "rationale": "Industrials hurt by tariffs"},
        {"symbol": "XLP", "direction": "buy", "rationale": "Consumer staples — domestic defensive"},
    ],
    EventType.PANDEMIC: [
        {"symbol": "XBI", "direction": "buy", "rationale": "Biotech benefits from treatment/vaccine demand"},
        {"symbol": "MRNA", "direction": "buy", "rationale": "mRNA vaccine maker"},
        {"symbol": "ZM", "direction": "buy", "rationale": "Remote work demand surges"},
        {"symbol": "JETS", "direction": "sell", "rationale": "Airlines crushed by travel restrictions"},
        {"symbol": "XLE", "direction": "sell", "rationale": "Energy demand collapse"},
        {"symbol": "SPY", "direction": "sell", "rationale": "Broad market sells off on growth fears"},
    ],
    EventType.POLITICAL_CRISIS: [
        {"symbol": "GLD", "direction": "buy", "rationale": "Gold safe haven"},
        {"symbol": "UVXY", "direction": "buy", "rationale": "Volatility spike"},
        {"symbol": "SPY", "direction": "sell", "rationale": "Uncertainty weighs on equities"},
        {"symbol": "TLT", "direction": "buy", "rationale": "Flight to safety"},
    ],
    EventType.TERRORIST_ATTACK: [
        {"symbol": "UVXY", "direction": "buy", "rationale": "Fear-driven volatility spike"},
        {"symbol": "GLD", "direction": "buy", "rationale": "Safe haven bid"},
        {"symbol": "ITA", "direction": "buy", "rationale": "Defense spending expected to increase"},
        {"symbol": "JETS", "direction": "sell", "rationale": "Airlines/travel sector sell off"},
        {"symbol": "SPY", "direction": "sell", "rationale": "Broad market risk-off"},
    ],
    EventType.NATURAL_DISASTER: [
        {"symbol": "XLU", "direction": "contextual", "rationale": "Utilities — rebuild vs damage"},
        {"symbol": "XHB", "direction": "buy", "rationale": "Homebuilders for reconstruction"},
        {"symbol": "CAT", "direction": "buy", "rationale": "Caterpillar — heavy equipment for rebuild"},
    ],
    EventType.CYBER_ATTACK: [
        {"symbol": "HACK", "direction": "buy", "rationale": "Cybersecurity ETF benefits"},
        {"symbol": "CRWD", "direction": "buy", "rationale": "CrowdStrike — cybersecurity leader"},
        {"symbol": "PANW", "direction": "buy", "rationale": "Palo Alto Networks — cybersecurity"},
        {"symbol": "SPY", "direction": "sell", "rationale": "Market uncertainty on infrastructure attack"},
    ],
    EventType.REGULATORY: [
        {"symbol": "SPY", "direction": "contextual", "rationale": "Depends on regulation target"},
    ],
}

# Event detection keywords — used for fast classification
EVENT_KEYWORDS: Dict[str, List[str]] = {
    EventType.MILITARY_CONFLICT: [
        "war", "invasion", "missile strike", "military attack", "armed conflict",
        "bombing", "airstrike", "troops deployed", "declaration of war",
        "nuclear threat", "military escalation", "combat operations",
        "ground offensive", "naval blockade", "no-fly zone",
    ],
    EventType.CENTRAL_BANK: [
        "rate cut", "rate hike", "emergency rate", "fed pivot", "qe restart",
        "quantitative easing", "quantitative tightening", "fomc emergency",
        "ecb rate", "boj intervention", "currency intervention",
        "central bank emergency", "rate surprise",
    ],
    EventType.ENERGY_CRISIS: [
        "opec", "oil embargo", "pipeline attack", "refinery explosion",
        "energy shortage", "natural gas crisis", "oil supply disruption",
        "strait of hormuz", "oil production", "oil prices surge",
        "oil supply", "energy crisis", "fuel shortage", "production cut",
    ],
    EventType.FINANCIAL_CRISIS: [
        "bank fail", "bank run", "credit crisis", "lehman moment",
        "systemic risk", "contagion", "liquidity crisis", "margin call",
        "sovereign default", "currency collapse", "bond market crash",
        "bank collapse", "fdic", "financial crisis", "banking crisis",
        "credit crunch", "insolvency", "bailout",
    ],
    EventType.TRADE_WAR: [
        "tariff", "trade war", "trade ban", "export controls", "sanctions",
        "import duty", "trade restrictions", "embargo",
    ],
    EventType.PANDEMIC: [
        "pandemic", "outbreak", "epidemic", "lockdown", "quarantine",
        "new variant", "public health emergency", "travel ban",
    ],
    EventType.POLITICAL_CRISIS: [
        "coup", "government collapse", "impeachment", "martial law",
        "civil unrest", "revolution", "political crisis", "regime change",
    ],
    EventType.TERRORIST_ATTACK: [
        "terrorist attack", "terrorism", "bombing attack", "hostage",
    ],
    EventType.CYBER_ATTACK: [
        "cyber attack", "ransomware", "infrastructure hack", "power grid attack",
        "data breach", "state-sponsored hack",
    ],
    EventType.NATURAL_DISASTER: [
        "earthquake", "hurricane", "tsunami", "volcanic eruption", "wildfire",
        "flooding", "category 5",
    ],
}

# Severity rules — which event types default to which severity
DEFAULT_SEVERITY: Dict[str, str] = {
    EventType.MILITARY_CONFLICT: EventSeverity.CRITICAL,
    EventType.FINANCIAL_CRISIS: EventSeverity.CRITICAL,
    EventType.CENTRAL_BANK: EventSeverity.HIGH,
    EventType.ENERGY_CRISIS: EventSeverity.HIGH,
    EventType.TERRORIST_ATTACK: EventSeverity.HIGH,
    EventType.TRADE_WAR: EventSeverity.HIGH,
    EventType.PANDEMIC: EventSeverity.HIGH,
    EventType.CYBER_ATTACK: EventSeverity.MEDIUM,
    EventType.POLITICAL_CRISIS: EventSeverity.MEDIUM,
    EventType.NATURAL_DISASTER: EventSeverity.MEDIUM,
    EventType.REGULATORY: EventSeverity.LOW,
    EventType.EARNINGS_SHOCK: EventSeverity.MEDIUM,
    EventType.UNKNOWN: EventSeverity.LOW,
}

# Scan intervals by alert level
SCAN_INTERVALS = {
    "normal": 120,      # 2 min scan interval in normal conditions
    "elevated": 30,     # 30 sec when something is brewing
    "critical": 10,     # 10 sec during active crisis
}


class GeopoliticalRadar:
    """Continuous macro event scanner that detects and responds to world events."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._alert_level = "normal"
        self._active_events: List[MacroEvent] = []
        self._seen_headlines: Set[str] = set()
        self._last_scan: float = 0
        self._event_counter = 0
        self._stats = {
            "scans": 0,
            "events_detected": 0,
            "swarms_triggered": 0,
            "critical_events": 0,
            "errors": 0,
        }
        # Cooldowns to prevent re-triggering same event
        self._event_cooldowns: Dict[str, float] = {}

    async def start(self):
        """Start the continuous geopolitical radar scan."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())
        logger.info("GeopoliticalRadar started (alert_level=%s)", self._alert_level)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("GeopoliticalRadar stopped")

    async def _scan_loop(self):
        """Main scanning loop — adapts interval based on alert level."""
        await asyncio.sleep(10)  # Initial warmup
        while self._running:
            try:
                events = await self._scan_for_events()
                if events:
                    for event in events:
                        await self._respond_to_event(event)
                self._stats["scans"] += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._stats["errors"] += 1
                logger.warning("Radar scan error: %s", e)

            interval = SCAN_INTERVALS.get(self._alert_level, 120)
            await asyncio.sleep(interval)

    async def _scan_for_events(self) -> List[MacroEvent]:
        """Scan multiple sources for macro events."""
        events = []

        # Source 1: Perplexity real-time news scan
        perplexity_events = await self._scan_perplexity()
        events.extend(perplexity_events)

        # Source 2: News API headlines
        news_events = await self._scan_news_api()
        events.extend(news_events)

        # Filter already-seen events
        new_events = []
        for event in events:
            headline_key = event.headline[:100].lower()
            if headline_key not in self._seen_headlines:
                self._seen_headlines.add(headline_key)
                new_events.append(event)

        # Trim seen headlines cache
        if len(self._seen_headlines) > 1000:
            self._seen_headlines = set(list(self._seen_headlines)[-500:])

        return new_events

    async def _scan_perplexity(self) -> List[MacroEvent]:
        """Use Perplexity to scan for breaking geopolitical/macro events."""
        try:
            from app.services.llm_router import get_llm_router, Tier

            router = get_llm_router()
            messages = [
                {"role": "system", "content": (
                    "You are a geopolitical risk analyst for an algorithmic trading system. "
                    "Return ONLY valid JSON. Focus on events that will move financial markets "
                    "in the next 1-24 hours. Only report SIGNIFICANT events, not routine news."
                )},
                {"role": "user", "content": (
                    "Scan for any breaking geopolitical, military, economic, or financial events "
                    "happening RIGHT NOW that could move markets significantly. Include:\n"
                    "1. Military conflicts, escalations, or de-escalations\n"
                    "2. Central bank emergency actions or surprise decisions\n"
                    "3. Political crises, coups, or sanctions\n"
                    "4. Energy supply disruptions or OPEC surprises\n"
                    "5. Financial system stress (bank failures, credit events)\n"
                    "6. Natural disasters with economic impact\n\n"
                    "Return JSON: {\"events\": [{\"headline\": str, \"description\": str, "
                    "\"event_type\": str, \"severity\": \"critical\"|\"high\"|\"medium\"|\"low\", "
                    "\"affected_regions\": [str], \"market_impact\": str}], "
                    "\"alert_level\": \"normal\"|\"elevated\"|\"critical\"}"
                )},
            ]

            result = await router.route_with_fallback(
                tier=Tier.CORTEX,
                messages=messages,
                task="geopolitical_scan",
                temperature=0.1,
                max_tokens=2048,
            )

            if result.error:
                return []

            parsed = self._parse_json(result.content)
            if not parsed:
                return []

            # Update alert level based on scan
            new_level = parsed.get("alert_level", "normal")
            if new_level in SCAN_INTERVALS:
                if new_level != self._alert_level:
                    logger.warning("Radar alert level changed: %s -> %s", self._alert_level, new_level)
                self._alert_level = new_level

            events = []
            for item in parsed.get("events", []):
                event_type = self._classify_event(
                    item.get("headline", ""),
                    item.get("description", ""),
                    item.get("event_type", ""),
                )
                severity = item.get("severity", DEFAULT_SEVERITY.get(event_type, "low"))

                self._event_counter += 1
                events.append(MacroEvent(
                    event_type=event_type,
                    severity=severity,
                    headline=item.get("headline", ""),
                    description=item.get("description", ""),
                    affected_regions=item.get("affected_regions", []),
                    source="perplexity",
                    id=f"geo-{self._event_counter}",
                ))

            return events
        except ImportError:
            logger.debug("LLM router not available for Perplexity scan")
            return []
        except Exception as e:
            logger.debug("Perplexity scan error: %s", e)
            return []

    async def _scan_news_api(self) -> List[MacroEvent]:
        """Scan News API for breaking headlines with event keywords."""
        try:
            from app.core.config import settings
            import aiohttp

            if not settings.NEWS_API_KEY:
                return []

            url = "https://newsapi.org/v2/top-headlines"
            params = {
                "category": "business",
                "language": "en",
                "pageSize": 20,
                "apiKey": settings.NEWS_API_KEY,
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()

            events = []
            for article in data.get("articles", []):
                title = article.get("title", "")
                desc = article.get("description", "") or ""
                combined = f"{title} {desc}".lower()

                event_type = self._classify_event(title, desc)
                if event_type == EventType.UNKNOWN:
                    continue  # Skip non-event headlines

                severity = DEFAULT_SEVERITY.get(event_type, "low")
                self._event_counter += 1
                events.append(MacroEvent(
                    event_type=event_type,
                    severity=severity,
                    headline=title,
                    description=desc[:500],
                    source="news_api",
                    id=f"news-{self._event_counter}",
                ))

            return events
        except Exception as e:
            logger.debug("News API scan error: %s", e)
            return []

    def _classify_event(self, headline: str, description: str = "", hint: str = "") -> str:
        """Classify an event based on keyword matching."""
        combined = f"{headline} {description} {hint}".lower()

        best_type = EventType.UNKNOWN
        best_score = 0

        for event_type, keywords in EVENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > best_score:
                best_score = score
                best_type = event_type

        return best_type

    async def _respond_to_event(self, event: MacroEvent):
        """Respond to a detected event by spawning swarms for affected instruments."""
        # Check cooldown
        cooldown_key = f"{event.event_type}:{event.headline[:50]}"
        now = time.time()
        if cooldown_key in self._event_cooldowns:
            if now - self._event_cooldowns[cooldown_key] < 300:  # 5 min cooldown
                return
        self._event_cooldowns[cooldown_key] = now

        self._stats["events_detected"] += 1
        self._active_events.append(event)
        if len(self._active_events) > 50:
            self._active_events = self._active_events[-50:]

        if event.severity == EventSeverity.CRITICAL:
            self._stats["critical_events"] += 1

        logger.warning(
            "MACRO EVENT DETECTED [%s/%s]: %s",
            event.severity.upper(), event.event_type, event.headline,
        )

        # Get playbook trades for this event type
        plays = MACRO_PLAYBOOK.get(event.event_type, [])
        if not plays:
            logger.info("No playbook entries for event type: %s", event.event_type)
            return

        # Determine priority based on severity
        priority_map = {
            EventSeverity.CRITICAL: 1,
            EventSeverity.HIGH: 2,
            EventSeverity.MEDIUM: 4,
            EventSeverity.LOW: 7,
        }
        priority = priority_map.get(event.severity, 5)

        # Spawn swarms for each playbook trade
        for play in plays:
            if play["direction"] == "contextual":
                # Need more context — spawn analysis without direction bias
                direction = "unknown"
            else:
                direction = "bullish" if play["direction"] == "buy" else "bearish"

            await self._trigger_swarm(
                symbols=[play["symbol"]],
                direction=direction,
                reasoning=(
                    f"MACRO EVENT [{event.severity.upper()}]: {event.headline}. "
                    f"Playbook: {play['rationale']}"
                ),
                raw_content=event.description,
                priority=priority,
                event=event,
            )
            self._stats["swarms_triggered"] += 1

        # Also ensure these symbols are being streamed for real-time data
        await self._expand_symbol_universe(plays, event)

        # Publish event to MessageBus for other components
        if self._bus:
            await self._bus.publish("scout.discovery", {
                "type": "macro_event",
                "event": event.to_dict(),
                "plays": len(plays),
                "priority": priority,
            })

    async def _trigger_swarm(
        self,
        symbols: List[str],
        direction: str,
        reasoning: str,
        raw_content: str = "",
        priority: int = 1,
        event: Optional[MacroEvent] = None,
    ):
        """Trigger immediate swarm analysis."""
        if self._bus:
            await self._bus.publish("swarm.idea", {
                "source": "geopolitical_radar",
                "symbols": symbols,
                "direction": direction,
                "reasoning": reasoning,
                "raw_content": raw_content,
                "priority": priority,
                "metadata": {
                    "event_type": event.event_type if event else "unknown",
                    "severity": event.severity if event else "unknown",
                    "macro_event": True,
                },
            })
        else:
            try:
                from app.services.swarm_spawner import get_swarm_spawner, SwarmIdea
                spawner = get_swarm_spawner()
                await spawner.spawn_analysis(SwarmIdea(
                    source="geopolitical_radar",
                    symbols=symbols,
                    direction=direction,
                    reasoning=reasoning,
                    raw_content=raw_content,
                    priority=priority,
                    metadata={
                        "event_type": event.event_type if event else "unknown",
                        "severity": event.severity if event else "unknown",
                        "macro_event": True,
                    },
                ))
            except Exception as e:
                logger.warning("Failed to trigger swarm: %s", e)

    async def _expand_symbol_universe(self, plays: List[Dict], event: MacroEvent):
        """Ensure all playbook symbols are in the tracked universe and have data."""
        try:
            from app.modules.symbol_universe import get_tracked_symbols, set_tracked_symbols
            current = set(get_tracked_symbols())
            new_symbols = [p["symbol"] for p in plays if p["symbol"] not in current]

            if new_symbols:
                all_symbols = list(current) + new_symbols
                set_tracked_symbols(all_symbols, source=f"radar_{event.event_type}")
                logger.info("Symbol universe expanded by %d: %s", len(new_symbols), new_symbols)

                # Auto-ingest data for new symbols
                try:
                    from app.services.data_ingestion import data_ingestion
                    for sym in new_symbols[:10]:
                        try:
                            await data_ingestion.ingest_daily_bars([sym], days=30)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception as e:
            logger.debug("Symbol universe expansion failed: %s", e)

    def _parse_json(self, text: str) -> Optional[Dict]:
        """Parse JSON from LLM response."""
        import json
        import re
        if not text:
            return None
        try:
            return json.loads(text.strip())
        except (json.JSONDecodeError, TypeError):
            pass
        patterns = [
            r'```json\s*\n(.*?)\n\s*```',
            r'```\s*\n(.*?)\n\s*```',
            r'\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\}',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1) if match.lastindex else match.group())
                except (json.JSONDecodeError, TypeError, IndexError):
                    continue
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "alert_level": self._alert_level,
            "scan_interval_seconds": SCAN_INTERVALS.get(self._alert_level, 120),
            "active_events": [e.to_dict() for e in self._active_events[-10:]],
            "stats": dict(self._stats),
        }

    def get_playbook(self, event_type: str = None) -> Dict[str, Any]:
        """Return the macro event playbook (all or filtered by event type)."""
        if event_type:
            return {event_type: MACRO_PLAYBOOK.get(event_type, [])}
        return dict(MACRO_PLAYBOOK)

    def inject_event(self, event: MacroEvent):
        """Manually inject an event (for testing or user override)."""
        asyncio.create_task(self._respond_to_event(event))


# Module-level singleton
_radar: Optional[GeopoliticalRadar] = None


def get_geopolitical_radar() -> GeopoliticalRadar:
    global _radar
    if _radar is None:
        _radar = GeopoliticalRadar()
    return _radar
