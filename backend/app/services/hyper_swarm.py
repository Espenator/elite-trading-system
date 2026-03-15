"""HyperSwarm — orchestrates 50+ concurrent micro-analysis swarms via local LLMs.

The original SwarmSpawner runs 5 full council evaluations (17 agents each).
HyperSwarm takes a different approach: spawn HUNDREDS of lightweight micro-swarms
that each use a single local Ollama call (<500ms, free) for rapid triage.

Only signals that pass micro-swarm triage get escalated to the full council.

Architecture:
    TurboScanner -> HyperSwarm
        -> 50 concurrent micro-swarm workers
        -> Each worker: local LLM triage (1 call, <500ms)
        -> High-confidence results -> full SwarmSpawner council
        -> All results stored for pattern learning

2-PC Scaling:
    - Configure OLLAMA_POOL for multi-node (e.g., [localhost:11434, pc2:11434])
    - Each node can handle 5-10 concurrent Ollama requests
    - 2 nodes × 10 concurrent = 20 parallel LLM calls
    - Each call <500ms = 40 analyses/second throughput

Micro-Swarm Types:
    1. QuickScore — score signal quality (0-100) in one LLM call
    2. DirectionConfirm — confirm bullish/bearish with technicals
    3. RiskCheck — quick risk assessment (position size, stop level)
    4. ContextEnrich — add macro/sector context to a signal
    5. HistoricalMatch — find similar historical setups
"""
import asyncio
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

MAX_CONCURRENT_MICRO_SWARMS = 50       # Total concurrent micro-analysis tasks
MAX_CONCURRENT_PER_OLLAMA = 10         # Max concurrent requests per Ollama node
MICRO_SWARM_TIMEOUT = 15.0             # Seconds per micro-swarm task
ESCALATION_THRESHOLD = 65              # Score >= 65 → escalate to full council
QUEUE_SIZE = 2000                      # Micro-swarm queue depth
MAX_HISTORY = 1000                     # Keep last 1000 results

# Ollama pool — populated from env: SCANNER_OLLAMA_URLS
DEFAULT_OLLAMA_URLS = ["http://localhost:11434"]


@dataclass
class MicroSwarmResult:
    """Result of a single micro-swarm analysis."""
    signal_id: str
    symbol: str
    signal_type: str
    score: int                    # 0-100 composite score
    direction: str                # bullish/bearish/neutral
    confidence: float             # 0-1
    reasoning: str
    risk_level: str = "medium"    # low/medium/high
    suggested_entry: str = ""
    suggested_stop: str = ""
    escalated: bool = False       # True if sent to full council
    ollama_node: str = ""
    latency_ms: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "score": self.score,
            "direction": self.direction,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "risk_level": self.risk_level,
            "suggested_entry": self.suggested_entry,
            "suggested_stop": self.suggested_stop,
            "escalated": self.escalated,
            "latency_ms": round(self.latency_ms, 1),
            "created_at": self.created_at,
        }


class HyperSwarm:
    """Orchestrates hundreds of micro-swarm analyses via local LLM pool."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._workers: List[asyncio.Task] = []
        self._results: List[MicroSwarmResult] = []
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_MICRO_SWARMS)
        from app.services.ollama_node_pool import get_ollama_pool
        self._pool = get_ollama_pool()
        self._ollama_urls = self._pool.urls
        self._stats = {
            "total_processed": 0,
            "total_escalated": 0,
            "total_filtered": 0,
            "total_errors": 0,
            "avg_score": 0.0,
            "avg_latency_ms": 0.0,
            "by_signal_type": defaultdict(int),
            "by_direction": defaultdict(int),
            "scores_distribution": defaultdict(int),  # 0-10, 10-20, ..., 90-100
        }

    async def start(self):
        if self._running:
            return
        self._running = True

        # Subscribe to triage.escalated — IdeaTriageService (E3) pre-filters
        # swarm.idea events before HyperSwarm consumes them.
        if self._bus:
            await self._bus.subscribe("triage.escalated", self._on_signal)

        # Start worker pool
        worker_count = min(MAX_CONCURRENT_MICRO_SWARMS, len(self._ollama_urls) * MAX_CONCURRENT_PER_OLLAMA)
        for i in range(worker_count):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)

        logger.info(
            "HyperSwarm: %d workers across %d nodes (escalation_threshold=%d)",
            worker_count, len(self._ollama_urls), ESCALATION_THRESHOLD,
        )

    async def stop(self):
        self._running = False
        for w in self._workers:
            w.cancel()
        for w in self._workers:
            try:
                await w
            except asyncio.CancelledError:
                pass
        self._workers.clear()
        logger.info("HyperSwarm stopped")

    # ──────────────────────────────────────────────────────────────────────
    # Signal Handling
    # ──────────────────────────────────────────────────────────────────────
    async def _on_signal(self, data: Dict[str, Any]):
        """Receive signals from MessageBus (from TurboScanner and other sources)."""
        try:
            self._queue.put_nowait(data)
        except asyncio.QueueFull:
            logger.debug("HyperSwarm queue full, dropping signal for %s", data.get("symbols", []))

    async def submit(self, signal_data: Dict[str, Any]):
        """Directly submit a signal for micro-swarm analysis."""
        try:
            self._queue.put_nowait(signal_data)
        except asyncio.QueueFull:
            pass

    # ──────────────────────────────────────────────────────────────────────
    # Worker Pool
    # ──────────────────────────────────────────────────────────────────────
    async def _worker(self, worker_id: int):
        while self._running:
            try:
                signal_data = await asyncio.wait_for(self._queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            async with self._semaphore:
                try:
                    result = await self._run_micro_swarm(signal_data, worker_id)
                    if result:
                        self._results.append(result)
                        self._update_stats(result)

                        # Publish micro-swarm result for downstream observability/UI.
                        if self._bus:
                            try:
                                await self._bus.publish(
                                    "swarm.result",
                                    {
                                        "type": "micro_swarm_result",
                                        "result": result.to_dict(),
                                        "input": {
                                            "source": signal_data.get("source", "unknown"),
                                            "symbols": signal_data.get("symbols", []),
                                            "direction": signal_data.get("direction", "unknown"),
                                            "triage": signal_data.get("triage"),
                                        },
                                        "timestamp": time.time(),
                                        "source": "hyper_swarm",
                                    },
                                )
                            except Exception:
                                pass

                        # Escalate high-scoring signals to full council
                        if result.score >= ESCALATION_THRESHOLD:
                            await self._escalate(signal_data, result)
                            result.escalated = True

                        if len(self._results) > MAX_HISTORY:
                            self._results = self._results[-MAX_HISTORY:]
                except Exception as e:
                    self._stats["total_errors"] += 1
                    logger.debug("Micro-swarm worker %d error: %s", worker_id, e)

                self._queue.task_done()

    async def _run_micro_swarm(self, signal_data: Dict, worker_id: int) -> Optional[MicroSwarmResult]:
        """Execute a micro-swarm analysis using local Ollama."""
        symbols = signal_data.get("symbols", [])
        if not symbols:
            return None

        symbol = symbols[0]
        direction = signal_data.get("direction", "unknown")
        reasoning = signal_data.get("reasoning", "")
        signal_type = signal_data.get("metadata", {}).get("signal_type", "unknown")
        source = signal_data.get("source", "unknown")

        # Get technical context from DuckDB
        context = await self._get_symbol_context(symbol)

        # Build prompt for local LLM
        prompt = self._build_triage_prompt(symbol, direction, reasoning, signal_type, context)

        # Call Ollama with round-robin node selection
        t0 = time.monotonic()
        ollama_url = self._get_next_ollama()
        try:
            response = await self._call_ollama(ollama_url, prompt)
            latency = (time.monotonic() - t0) * 1000
        except Exception as e:
            logger.debug("Ollama call failed (%s): %s", ollama_url, e)
            # Fallback: score based on raw signal data
            return self._fallback_score(symbol, signal_type, direction, reasoning, signal_data)

        # Parse LLM response
        result = self._parse_response(
            response, symbol, signal_type, direction, source, ollama_url, latency
        )
        return result

    def _build_triage_prompt(
        self, symbol: str, direction: str, reasoning: str,
        signal_type: str, context: Dict,
    ) -> str:
        """Build a concise triage prompt for the local LLM."""
        rsi = context.get("rsi", "N/A")
        adx = context.get("adx", "N/A")
        ret_5d = context.get("ret_5d", "N/A")
        volume_ratio = context.get("volume_ratio", "N/A")
        sma_stack = context.get("sma_stack", "N/A")

        return f"""Score this trading signal 0-100. Be harsh — only score above 65 if the setup is genuinely strong.

SIGNAL: {signal_type} on {symbol}
DIRECTION: {direction}
REASONING: {reasoning}

TECHNICALS:
- RSI(14): {rsi}
- ADX(14): {adx}
- 5d return: {ret_5d}
- Volume ratio: {volume_ratio}x avg
- SMA stack: {sma_stack}

Respond in exactly this format (no other text):
SCORE: [0-100]
DIRECTION: [bullish/bearish/neutral]
CONFIDENCE: [0.0-1.0]
RISK: [low/medium/high]
REASON: [one sentence]"""

    async def _get_symbol_context(self, symbol: str) -> Dict[str, Any]:
        """Fetch technical context from DuckDB for the symbol."""
        def _query() -> Optional[tuple]:
            from app.data.duckdb_storage import duckdb_store

            conn = duckdb_store.get_thread_cursor()
            return conn.execute(
                """
                SELECT t.rsi_14, t.adx_14, t.macd, t.sma_20, t.sma_50, t.sma_200,
                       o.close, o.volume,
                       o.close / NULLIF(LAG(o.close, 5) OVER (PARTITION BY o.symbol ORDER BY o.date), 0) - 1 as ret_5d,
                       o.volume / NULLIF(AVG(o.volume) OVER (PARTITION BY o.symbol ORDER BY o.date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING), 0) as vol_ratio
                FROM technical_indicators t
                JOIN daily_ohlcv o ON t.symbol = o.symbol AND t.date = o.date
                WHERE t.symbol = ?
                ORDER BY t.date DESC
                LIMIT 1
                """,
                [symbol],
            ).fetchone()

        try:
            # Hot-path purity: never block the event loop on DuckDB.
            row = await asyncio.wait_for(asyncio.to_thread(_query), timeout=1.0)
            if not row:
                return {}

            close = float(row[6] or 0)
            sma20 = float(row[3] or 0)
            sma50 = float(row[4] or 0)
            sma200 = float(row[5] or 0)
            if close > sma20 > sma50 > sma200:
                sma_stack = "bullish (close>20>50>200)"
            elif close < sma20 < sma50 < sma200:
                sma_stack = "bearish (close<20<50<200)"
            else:
                sma_stack = "mixed"
            return {
                "rsi": round(float(row[0] or 50), 1),
                "adx": round(float(row[1] or 0), 1),
                "macd": round(float(row[2] or 0), 4),
                "close": close,
                "ret_5d": f"{float(row[8] or 0):.1%}" if row[8] else "N/A",
                "volume_ratio": f"{float(row[9] or 1):.1f}" if row[9] else "N/A",
                "sma_stack": sma_stack,
            }
        except asyncio.TimeoutError:
            return {}
        except Exception:
            return {}

    # ──────────────────────────────────────────────────────────────────────
    # Ollama Pool Management
    # ──────────────────────────────────────────────────────────────────────
    def _get_next_ollama(self) -> str:
        """Round-robin Ollama node selection via shared pool."""
        url = self._pool.get_next_node()
        return url or (self._pool.urls[0] if self._pool.urls else "http://localhost:11434")

    async def _call_ollama(self, base_url: str, prompt: str) -> str:
        """Call Ollama with per-node concurrency limiting."""
        import httpx

        sem = self._pool.get_semaphore(base_url)
        if sem:
            await sem.acquire()

        try:
            url = f"{base_url.rstrip('/')}/v1/chat/completions"
            payload = {
                "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 200,
                "stream": False,
            }
            async with httpx.AsyncClient(timeout=MICRO_SWARM_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        finally:
            if sem:
                sem.release()

    def _parse_response(
        self, response: str, symbol: str, signal_type: str,
        direction: str, source: str, ollama_url: str, latency: float,
    ) -> MicroSwarmResult:
        """Parse structured LLM response into MicroSwarmResult."""
        score = 50
        conf = 0.5
        risk = "medium"
        reason = response.strip()
        parsed_direction = direction

        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("SCORE:"):
                try:
                    score = int(line.split(":", 1)[1].strip().split()[0])
                    score = max(0, min(100, score))
                except (ValueError, IndexError):
                    pass
            elif line.startswith("DIRECTION:"):
                d = line.split(":", 1)[1].strip().lower()
                if d in ("bullish", "bearish", "neutral"):
                    parsed_direction = d
            elif line.startswith("CONFIDENCE:"):
                try:
                    conf = float(line.split(":", 1)[1].strip())
                    conf = max(0.0, min(1.0, conf))
                except (ValueError, IndexError):
                    pass
            elif line.startswith("RISK:"):
                r = line.split(":", 1)[1].strip().lower()
                if r in ("low", "medium", "high"):
                    risk = r
            elif line.startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()

        return MicroSwarmResult(
            signal_id=f"{symbol}:{signal_type}:{int(time.time())}",
            symbol=symbol,
            signal_type=signal_type,
            score=score,
            direction=parsed_direction,
            confidence=conf,
            reasoning=reason,
            risk_level=risk,
            ollama_node=ollama_url,
            latency_ms=latency,
        )

    def _fallback_score(
        self, symbol: str, signal_type: str, direction: str,
        reasoning: str, signal_data: Dict,
    ) -> MicroSwarmResult:
        """Score without LLM when Ollama is unavailable."""
        raw_score = signal_data.get("metadata", {}).get("score", 0.5)
        score = int(raw_score * 100) if isinstance(raw_score, float) and raw_score <= 1 else int(raw_score)
        return MicroSwarmResult(
            signal_id=f"{symbol}:{signal_type}:{int(time.time())}",
            symbol=symbol,
            signal_type=signal_type,
            score=score,
            direction=direction,
            confidence=raw_score if isinstance(raw_score, float) else 0.5,
            reasoning=f"[Fallback scoring] {reasoning}",
            risk_level="medium",
            ollama_node="none",
            latency_ms=0,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Escalation to Full Council
    # ──────────────────────────────────────────────────────────────────────
    async def _escalate(self, signal_data: Dict, result: MicroSwarmResult):
        """Escalate high-scoring micro-swarm results to the canonical council path.

        Contract: publish to signal.generated (0-100 score). CouncilGate is the
        only runtime consumer that can publish council.verdict.
        """
        self._stats["total_escalated"] += 1
        if self._bus:
            # Map bullish/bearish into buy/sell; neutral -> hold.
            d = (result.direction or "").strip().lower()
            if d in ("bullish", "buy", "long", "up"):
                final_direction = "buy"
            elif d in ("bearish", "sell", "short", "down"):
                final_direction = "sell"
            else:
                final_direction = "hold"

            await self._bus.publish(
                "signal.generated",
                {
                    "symbol": result.symbol,
                    "score": float(result.score),
                    "direction": final_direction,
                    "label": f"hyper_swarm_{result.signal_type}",
                    "price": signal_data.get("price") or signal_data.get("metadata", {}).get("price") or 0,
                    "regime": "HYPERSWARM",
                    "source": "hyper_swarm",
                    "metadata": {
                        "micro_swarm_score": result.score,
                        "micro_swarm_confidence": result.confidence,
                        "risk_level": result.risk_level,
                        "signal_type": result.signal_type,
                        "reasoning": result.reasoning,
                        "triage": signal_data.get("triage"),
                    },
                },
            )
        logger.info(
            "HyperSwarm ESCALATED: %s %s score=%d -> signal.generated",
            result.symbol, result.direction, result.score,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────────────────────────────────
    def _update_stats(self, result: MicroSwarmResult):
        self._stats["total_processed"] += 1
        if result.score < ESCALATION_THRESHOLD:
            self._stats["total_filtered"] += 1
        self._stats["by_signal_type"][result.signal_type] += 1
        self._stats["by_direction"][result.direction] += 1
        bucket = f"{(result.score // 10) * 10}-{(result.score // 10) * 10 + 9}"
        self._stats["scores_distribution"][bucket] += 1
        # Running average
        n = self._stats["total_processed"]
        self._stats["avg_score"] = ((self._stats["avg_score"] * (n - 1)) + result.score) / n
        self._stats["avg_latency_ms"] = ((self._stats["avg_latency_ms"] * (n - 1)) + result.latency_ms) / n

    # ──────────────────────────────────────────────────────────────────────
    # Status / API
    # ──────────────────────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "queue_depth": self._queue.qsize(),
            "workers": len(self._workers),
            "ollama_nodes": self._pool.urls,
            "escalation_threshold": ESCALATION_THRESHOLD,
            "stats": {
                k: (dict(v) if isinstance(v, defaultdict) else round(v, 1) if isinstance(v, float) else v)
                for k, v in self._stats.items()
            },
            "recent_results": [r.to_dict() for r in self._results[-20:]],
            "recent_escalations": [
                r.to_dict() for r in self._results[-100:] if r.escalated
            ][-10:],
        }

    def get_results(self, limit: int = 50, min_score: int = 0) -> List[Dict]:
        results = [r for r in self._results if r.score >= min_score]
        return [r.to_dict() for r in results[-limit:]]

    def get_escalations(self, limit: int = 20) -> List[Dict]:
        escalated = [r for r in self._results if r.escalated]
        return [r.to_dict() for r in escalated[-limit:]]


# Module-level singleton
_hyper_swarm: Optional[HyperSwarm] = None

def get_hyper_swarm() -> HyperSwarm:
    global _hyper_swarm
    if _hyper_swarm is None:
        _hyper_swarm = HyperSwarm()
    return _hyper_swarm
