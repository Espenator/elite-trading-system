#!/usr/bin/env python3
"""uw_agents.py v1.0 - Unusual Whales Auto-Spawning Agent Swarm

Automatically spawns specialized agents for each Unusual Whales API
category.  Each agent runs as an independent async task, polls its
own set of UW endpoints, and publishes structured signals to the
Blackboard for downstream scoring and execution.

Agent Architecture:
  UWAgentOrchestrator (master)
    |-- WhaleTrackerAgent      -> /option-trades/flow-alerts  (sweeps, blocks)
    |-- ShadowLiquidityAgent   -> /darkpool/recent            (dark pool prints)
    |-- PolicyFrontrunnerAgent -> /congress/recent-trades      (congressional)
    |-- GammaPinAgent          -> /stock/{t}/greek-exposure    (GEX / dealer)
    |-- MarketTideAgent        -> /market/market-tide          (put/call sentiment)
    |-- InsiderWatchAgent      -> /insider/recent-transactions (insider buys/sells)

Key Design:
  - Each agent is a subclass of BaseUWAgent with its own poll loop
  - Orchestrator spawns all agents as asyncio tasks
  - Heartbeats published every 30s so streaming_engine knows we're alive
  - Graceful degradation: if one agent fails, others keep running
  - All agents share a single rate-limited HTTP session
"""
import asyncio
import os
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    from config import (
        UNUSUALWHALES_API_KEY, UNUSUALWHALES_BASE_URL,
        AGENT_HEARTBEAT_INTERVAL, TOPIC_ALPHA_SIGNALS,
        TOPIC_HEARTBEAT, WHALE_MIN_PREMIUM,
    )
except ImportError:
    UNUSUALWHALES_API_KEY = os.getenv("UNUSUALWHALES_API_KEY", "")
    UNUSUALWHALES_BASE_URL = "https://api.unusualwhales.com/api"
    AGENT_HEARTBEAT_INTERVAL = 30
    TOPIC_ALPHA_SIGNALS = "alpha_signals"
    TOPIC_HEARTBEAT = "heartbeat"
    WHALE_MIN_PREMIUM = 100000

try:
    from streaming_engine import get_blackboard, BlackboardMessage, Topic
except ImportError:
    get_blackboard = None
    BlackboardMessage = None
    Topic = None

logger = logging.getLogger(__name__)


# ============================================================
#  SHARED RATE-LIMITED HTTP CLIENT
# ============================================================
class UWHttpClient:
    """Thread-safe, rate-limited HTTP client shared by all UW agents."""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or UNUSUALWHALES_API_KEY
        self.base_url = (base_url or UNUSUALWHALES_BASE_URL).rstrip("/")
        self._last_call: float = 0.0
        self._min_interval: float = 1.0  # 1 req/sec rate limit
        self._session: Optional[aiohttp.ClientSession] = None
        self._total_requests: int = 0
        self._total_errors: int = 0

    async def _get_session(self) -> "aiohttp.ClientSession":
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json",
                }
            )
        return self._session

    async def get(self, path: str, params: Dict = None, retries: int = 3) -> Optional[Dict]:
        """Rate-limited GET with exponential backoff retry."""
        if not self.api_key:
            logger.warning("[UWHttp] No API key configured")
            return None
        url = f"{self.base_url}{path}"
        for attempt in range(retries):
            # Rate limit
            elapsed = time.time() - self._last_call
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_call = time.time()
            try:
                session = await self._get_session()
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    self._total_requests += 1
                    resp.raise_for_status()
                    return await resp.json()
            except Exception as e:
                self._total_errors += 1
                logger.warning(f"[UWHttp] {path} attempt {attempt+1}/{retries}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
        logger.error(f"[UWHttp] {path} failed after {retries} attempts")
        return None

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def stats(self) -> Dict:
        return {"total_requests": self._total_requests, "total_errors": self._total_errors}


# ============================================================
#  BASE AGENT (abstract)
# ============================================================
class BaseUWAgent(ABC):
    """Abstract base for all Unusual Whales agents."""

    NAME: str = "base"
    POLL_INTERVAL: int = 120  # seconds
    TOPIC: str = TOPIC_ALPHA_SIGNALS

    def __init__(self, http: UWHttpClient, blackboard=None):
        self.http = http
        self.bb = blackboard
        self._published: set = set()
        self._cycle_count: int = 0
        self._signals_total: int = 0
        self._running: bool = False
        self._last_heartbeat: float = 0.0

    # -- subclass must implement --
    @abstractmethod
    async def fetch(self) -> List[Dict]:
        """Hit UW API and return raw records."""

    @abstractmethod
    def transform(self, raw: List[Dict]) -> List[Dict]:
        """Normalise raw API data into Blackboard-ready signals."""

    # -- shared logic --
    def _sig_id(self, sig: Dict) -> str:
        """Unique key per signal for deduplication."""
        return f"{self.NAME}_{sig.get('ticker','')}_{sig.get('key','')}"

    async def _publish(self, signals: List[Dict]) -> int:
        if not self.bb or not BlackboardMessage:
            return 0
        count = 0
        for sig in signals:
            sid = self._sig_id(sig)
            if sid in self._published:
                continue
            try:
                msg = BlackboardMessage(
                    topic=self.TOPIC,
                    payload={**sig, "agent": self.NAME},
                    source=f"uw_agents.{self.NAME}",
                )
                self.bb.publish(msg)
                self._published.add(sid)
                count += 1
            except Exception as e:
                logger.warning(f"[{self.NAME}] publish error: {e}")
        self._signals_total += count
        return count

    async def _heartbeat(self):
        now = time.time()
        if now - self._last_heartbeat < AGENT_HEARTBEAT_INTERVAL:
            return
        self._last_heartbeat = now
        if self.bb and BlackboardMessage:
            try:
                self.bb.publish(BlackboardMessage(
                    topic=TOPIC_HEARTBEAT,
                    payload={
                        "agent": self.NAME,
                        "alive": True,
                        "cycles": self._cycle_count,
                        "signals": self._signals_total,
                        "ts": datetime.utcnow().isoformat(),
                    },
                    source=f"uw_agents.{self.NAME}",
                ))
            except Exception:
                pass

    async def run_forever(self):
        """Main poll loop - called by orchestrator."""
        self._running = True
        logger.info(f"[{self.NAME}] agent spawned (poll every {self.POLL_INTERVAL}s)")
        while self._running:
            try:
                await self._heartbeat()
                raw = await self.fetch()
                if raw:
                    signals = self.transform(raw)
                    published = await self._publish(signals)
                    logger.info(f"[{self.NAME}] cycle {self._cycle_count}: {len(raw)} raw -> {len(signals)} signals -> {published} new")
                else:
                    logger.debug(f"[{self.NAME}] no data this cycle")
                self._cycle_count += 1
            except Exception as e:
                logger.error(f"[{self.NAME}] cycle error: {e}")
            await asyncio.sleep(self.POLL_INTERVAL)

    def stop(self):
        self._running = False

    @property
    def stats(self) -> Dict:
        return {
            "name": self.NAME, "cycles": self._cycle_count,
            "signals_published": self._signals_total,
            "unique_tracked": len(self._published), "running": self._running,
        }


# ============================================================
#  AGENT 1: WHALE TRACKER  (options flow sweeps & blocks)
# ============================================================
class WhaleTrackerAgent(BaseUWAgent):
    """Monitors /option-trades/flow-alerts for high-premium institutional sweeps."""

    NAME = "whale_tracker"
    POLL_INTERVAL = 90  # aggressive polling for flow
    MIN_PREMIUM = int(os.getenv("UW_WHALE_MIN_PREMIUM", str(WHALE_MIN_PREMIUM)))

    async def fetch(self) -> List[Dict]:
        data = await self.http.get(
            "/option-trades/flow-alerts",
            params={
                "limit": 100,
                "min_premium": self.MIN_PREMIUM,
                "min_dte": 7,
                "max_dte": 60,
                "issue_types[]": "Common Stock",
            },
        )
        return data.get("data", []) if data else []

    def transform(self, raw: List[Dict]) -> List[Dict]:
        signals = []
        for r in raw:
            try:
                premium = float(r.get("total_premium", 0))
                if premium < self.MIN_PREMIUM:
                    continue
                vol = int(r.get("volume", 0) or 0)
                oi = int(r.get("open_interest", 0) or 0)
                ask_prem = float(r.get("total_ask_side_prem", 0) or 0)
                bid_prem = float(r.get("total_bid_side_prem", 0) or 0)
                opt = r.get("type", "").lower()
                if ask_prem > bid_prem:
                    sentiment = "bullish" if opt == "call" else "bearish"
                else:
                    sentiment = "bearish" if opt == "call" else "bullish"
                trade_type = "sweep" if r.get("has_sweep") else ("floor" if r.get("has_floor") else "block")
                signals.append({
                    "ticker": r.get("ticker", ""),
                    "signal_type": "whale_flow",
                    "option_type": opt,
                    "strike": r.get("strike"),
                    "expiry": r.get("expiry"),
                    "premium": premium,
                    "sentiment": sentiment,
                    "trade_type": trade_type,
                    "volume": vol,
                    "open_interest": oi,
                    "oi_ratio": round(vol / oi, 2) if oi > 0 else 0,
                    "key": f"{r.get('ticker')}_{r.get('expiry')}_{r.get('strike')}_{trade_type}",
                })
            except Exception as e:
                logger.debug(f"[whale_tracker] skip: {e}")
        return signals


# ============================================================
#  AGENT 2: SHADOW LIQUIDITY  (dark pool prints)
# ============================================================
class ShadowLiquidityAgent(BaseUWAgent):
    """Monitors /darkpool/recent for large off-exchange prints that map hidden S/R."""

    NAME = "shadow_liquidity"
    POLL_INTERVAL = 180
    MIN_SIZE = int(os.getenv("UW_DARKPOOL_MIN_SIZE", "500000"))  # $500K min notional

    async def fetch(self) -> List[Dict]:
        data = await self.http.get("/darkpool/recent", params={"limit": 100})
        return data.get("data", []) if data else []

    def transform(self, raw: List[Dict]) -> List[Dict]:
        signals = []
        for r in raw:
            try:
                notional = float(r.get("notional_value", 0) or r.get("premium", 0) or 0)
                if notional < self.MIN_SIZE:
                    continue
                ticker = r.get("ticker", "")
                price = float(r.get("price", 0) or 0)
                size = int(r.get("size", 0) or r.get("volume", 0) or 0)
                signals.append({
                    "ticker": ticker,
                    "signal_type": "dark_pool",
                    "price": price,
                    "size": size,
                    "notional": notional,
                    "exchange": r.get("exchange", "dark"),
                    "executed_at": r.get("executed_at", ""),
                    "key": f"{ticker}_{price}_{size}",
                })
            except Exception as e:
                logger.debug(f"[shadow_liquidity] skip: {e}")
        return signals


# ============================================================
#  AGENT 3: POLICY FRONTRUNNER  (congressional trades)
# ============================================================
class PolicyFrontrunnerAgent(BaseUWAgent):
    """Monitors /congress/recent-trades for politician stock buys/sells."""

    NAME = "policy_frontrunner"
    POLL_INTERVAL = 900  # 15 min - congressional filings are slower

    # Star traders to highlight
    STAR_TRADERS = {
        "nancy pelosi", "dan crenshaw", "tommy tuberville",
        "marjorie taylor greene", "josh gottheimer", "ro khanna",
    }

    async def fetch(self) -> List[Dict]:
        data = await self.http.get("/congress/recent-trades", params={"limit": 50})
        return data.get("data", []) if data else []

    def transform(self, raw: List[Dict]) -> List[Dict]:
        signals = []
        for r in raw:
            try:
                ticker = r.get("ticker", "") or r.get("asset", "")
                if not ticker or ticker == "--":
                    continue
                member = r.get("politician", "") or r.get("representative", "")
                txn_type = (r.get("transaction_type", "") or r.get("type", "")).lower()
                amount = r.get("amount", "")
                filed = r.get("filed_date", "") or r.get("disclosure_date", "")
                is_star = member.lower() in self.STAR_TRADERS if member else False
                sentiment = "bullish" if "purchase" in txn_type else ("bearish" if "sale" in txn_type else "neutral")
                signals.append({
                    "ticker": ticker.upper(),
                    "signal_type": "congress_trade",
                    "politician": member,
                    "transaction": txn_type,
                    "amount_range": amount,
                    "filed_date": filed,
                    "is_star_trader": is_star,
                    "sentiment": sentiment,
                    "key": f"{ticker}_{member}_{filed}",
                })
            except Exception as e:
                logger.debug(f"[policy_frontrunner] skip: {e}")
        return signals


# ============================================================
#  AGENT 4: GAMMA PIN  (GEX / market maker exposure)
# ============================================================
class GammaPinAgent(BaseUWAgent):
    """Reads /stock/{ticker}/greek-exposure for GEX levels.
    Requires a watchlist of tickers to check (from Blackboard or config).
    """

    NAME = "gamma_pin"
    POLL_INTERVAL = 300  # 5 min - GEX updates slowly
    WATCHLIST_MAX = 10

    def __init__(self, http: UWHttpClient, blackboard=None, watchlist: List[str] = None):
        super().__init__(http, blackboard)
        self._watchlist = watchlist or []

    def set_watchlist(self, tickers: List[str]):
        self._watchlist = tickers[:self.WATCHLIST_MAX]

    async def fetch(self) -> List[Dict]:
        results = []
        for ticker in self._watchlist:
            data = await self.http.get(f"/stock/{ticker}/greek-exposure")
            if data and data.get("data"):
                results.append({"ticker": ticker, "gex": data["data"]})
        return results

    def transform(self, raw: List[Dict]) -> List[Dict]:
        signals = []
        for item in raw:
            try:
                ticker = item["ticker"]
                gex = item["gex"]
                if isinstance(gex, list):
                    # Find strike with highest absolute gamma
                    max_gex = max(gex, key=lambda x: abs(float(x.get("gex", 0) or 0)), default={})
                    pin_strike = max_gex.get("strike", 0)
                    pin_gamma = float(max_gex.get("gex", 0) or 0)
                    total_gex = sum(float(x.get("gex", 0) or 0) for x in gex)
                    signals.append({
                        "ticker": ticker,
                        "signal_type": "gamma_pin",
                        "pin_strike": pin_strike,
                        "pin_gamma": pin_gamma,
                        "total_gex": round(total_gex, 2),
                        "gex_bias": "positive" if total_gex > 0 else "negative",
                        "num_strikes": len(gex),
                        "key": f"{ticker}_gex_{date.today().isoformat()}",
                    })
            except Exception as e:
                logger.debug(f"[gamma_pin] skip {item.get('ticker','?')}: {e}")
        return signals


# ============================================================
#  AGENT 5: MARKET TIDE  (put/call sentiment gauge)
# ============================================================
class MarketTideAgent(BaseUWAgent):
    """Reads /market/market-tide for overall market put/call sentiment."""

    NAME = "market_tide"
    POLL_INTERVAL = 120

    async def fetch(self) -> List[Dict]:
        data = await self.http.get("/market/market-tide")
        if data and data.get("data"):
            return [data["data"]] if isinstance(data["data"], dict) else data["data"]
        return []

    def transform(self, raw: List[Dict]) -> List[Dict]:
        signals = []
        for r in raw:
            try:
                call_prem = float(r.get("call_premium", 0) or r.get("total_call_premium", 0) or 0)
                put_prem = float(r.get("put_premium", 0) or r.get("total_put_premium", 0) or 0)
                total = call_prem + put_prem
                if total == 0:
                    continue
                call_ratio = round(call_prem / total, 3)
                if call_ratio > 0.60:
                    bias = "strongly_bullish"
                elif call_ratio > 0.52:
                    bias = "bullish"
                elif call_ratio < 0.40:
                    bias = "strongly_bearish"
                elif call_ratio < 0.48:
                    bias = "bearish"
                else:
                    bias = "neutral"
                signals.append({
                    "ticker": "$MARKET",
                    "signal_type": "market_tide",
                    "call_premium": call_prem,
                    "put_premium": put_prem,
                    "call_ratio": call_ratio,
                    "bias": bias,
                    "key": f"tide_{date.today().isoformat()}_{datetime.utcnow().hour}",
                })
            except Exception as e:
                logger.debug(f"[market_tide] skip: {e}")
        return signals


# ============================================================
#  AGENT 6: INSIDER WATCH  (insider buys/sells)
# ============================================================
class InsiderWatchAgent(BaseUWAgent):
    """Monitors /insider/recent-transactions for insider buying clusters."""

    NAME = "insider_watch"
    POLL_INTERVAL = 600  # 10 min
    MIN_VALUE = int(os.getenv("UW_INSIDER_MIN_VALUE", "100000"))  # $100K

    async def fetch(self) -> List[Dict]:
        data = await self.http.get("/insider/recent-transactions", params={"limit": 50})
        return data.get("data", []) if data else []

    def transform(self, raw: List[Dict]) -> List[Dict]:
        signals = []
        for r in raw:
            try:
                ticker = r.get("ticker", "") or r.get("symbol", "")
                if not ticker:
                    continue
                value = float(r.get("value", 0) or r.get("total_value", 0) or 0)
                if value < self.MIN_VALUE:
                    continue
                txn = (r.get("transaction_type", "") or r.get("type", "")).lower()
                name = r.get("insider_name", "") or r.get("name", "")
                title = r.get("insider_title", "") or r.get("title", "")
                sentiment = "bullish" if "buy" in txn or "purchase" in txn else "bearish"
                signals.append({
                    "ticker": ticker.upper(),
                    "signal_type": "insider_trade",
                    "insider_name": name,
                    "insider_title": title,
                    "transaction": txn,
                    "value": value,
                    "sentiment": sentiment,
                    "filed_date": r.get("filed_date", ""),
                    "key": f"{ticker}_{name}_{r.get('filed_date','')}",
                })
            except Exception as e:
                logger.debug(f"[insider_watch] skip: {e}")
        return signals


# ============================================================
#  AGENT REGISTRY  (auto-discovery)
# ============================================================
AGENT_CLASSES: Dict[str, type] = {
    "whale_tracker":      WhaleTrackerAgent,
    "shadow_liquidity":   ShadowLiquidityAgent,
    "policy_frontrunner": PolicyFrontrunnerAgent,
    "gamma_pin":          GammaPinAgent,
    "market_tide":        MarketTideAgent,
    "insider_watch":      InsiderWatchAgent,
}


# ============================================================
#  ORCHESTRATOR  (auto-spawns all agents)
# ============================================================
class UWAgentOrchestrator:
    """Master controller that auto-spawns one agent per UW API category.

    Usage:
        orch = UWAgentOrchestrator()
        await orch.run()   # spawns all agents as concurrent tasks
    """

    def __init__(self, blackboard=None, enabled_agents: List[str] = None):
        self.http = UWHttpClient()
        self.bb = blackboard
        if not self.bb and get_blackboard:
            try:
                self.bb = get_blackboard()
            except Exception as e:
                logger.warning(f"[UWOrch] Could not get Blackboard: {e}")

        # Determine which agents to spawn
        enabled = enabled_agents or list(AGENT_CLASSES.keys())
        self.agents: Dict[str, BaseUWAgent] = {}
        for name in enabled:
            cls = AGENT_CLASSES.get(name)
            if cls:
                if name == "gamma_pin":
                    self.agents[name] = cls(self.http, self.bb, watchlist=["SPY", "QQQ", "AAPL", "NVDA", "TSLA"])
                else:
                    self.agents[name] = cls(self.http, self.bb)

        self._tasks: Dict[str, asyncio.Task] = {}
        self._start_time: Optional[float] = None

    async def run(self):
        """Spawn all agents as concurrent asyncio tasks."""
        self._start_time = time.time()
        agent_count = len(self.agents)
        logger.info(f"[UWOrch] Spawning {agent_count} Unusual Whales agents...")

        for name, agent in self.agents.items():
            task = asyncio.create_task(self._run_agent(name, agent))
            self._tasks[name] = task
            logger.info(f"[UWOrch]   -> {name} (poll every {agent.POLL_INTERVAL}s)")

        logger.info(f"[UWOrch] All {agent_count} agents running. Monitoring health...")

        # Health monitor loop - restart failed agents
        while True:
            await asyncio.sleep(60)
            for name, task in list(self._tasks.items()):
                if task.done():
                    exc = task.exception() if not task.cancelled() else None
                    logger.warning(f"[UWOrch] Agent '{name}' died: {exc}. Restarting...")
                    agent = self.agents[name]
                    agent._running = False
                    self._tasks[name] = asyncio.create_task(self._run_agent(name, agent))

    async def _run_agent(self, name: str, agent: BaseUWAgent):
        """Wrapper with error isolation per agent."""
        try:
            await agent.run_forever()
        except asyncio.CancelledError:
            logger.info(f"[UWOrch] Agent '{name}' cancelled")
        except Exception as e:
            logger.error(f"[UWOrch] Agent '{name}' fatal: {e}")
            raise

    async def shutdown(self):
        """Graceful shutdown of all agents."""
        logger.info("[UWOrch] Shutting down all agents...")
        for name, agent in self.agents.items():
            agent.stop()
        for name, task in self._tasks.items():
            task.cancel()
        await self.http.close()
        logger.info("[UWOrch] All agents stopped")

    @property
    def stats(self) -> Dict:
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "uptime_seconds": round(uptime),
            "http": self.http.stats,
            "agents": {n: a.stats for n, a in self.agents.items()},
        }


# ============================================================
#  PUBLIC API  (for streaming_engine integration)
# ============================================================
async def run(blackboard=None) -> None:
    """Entry point called by streaming_engine to spawn the UW swarm."""
    orch = UWAgentOrchestrator(blackboard=blackboard)
    try:
        await orch.run()
    except asyncio.CancelledError:
        await orch.shutdown()


def get_orchestrator(blackboard=None, agents: List[str] = None) -> UWAgentOrchestrator:
    """Factory for external callers who want more control."""
    return UWAgentOrchestrator(blackboard=blackboard, enabled_agents=agents)


# ============================================================
#  CLI
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenClaw UW Agent Swarm")
    parser.add_argument(
        "--agents", nargs="*", default=None,
        choices=list(AGENT_CLASSES.keys()),
        help="Specific agents to spawn (default: all)",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List available agents and exit",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.list:
        print("Available Unusual Whales Agents:")
        for name, cls in AGENT_CLASSES.items():
            print(f"  {name:25s}  poll={cls.POLL_INTERVAL:>4d}s  {cls.__doc__.strip().split(chr(10))[0]}")
        raise SystemExit(0)

    async def _main():
        orch = UWAgentOrchestrator(enabled_agents=args.agents)
        try:
            await orch.run()
        except KeyboardInterrupt:
            await orch.shutdown()

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.info("[UWAgents] Interrupted - shutting down")
