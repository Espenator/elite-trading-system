"""Council Coordinator — distributed DAG execution across PCs via Redis Streams.

Splits the 33-agent council across PC1 and PC2 using Redis Streams for
task dispatch and result collection. Sequential stages (Strategy, Critic,
Arbiter) always stay on PC1 for consistency.

Work Distribution:
    PC1: 6 perception + 4 technical + 1 hypothesis + Strategy(seq) +
         2 risk + Debate + Critic(seq) + Arbiter(deterministic)
    PC2: 7 perception + 4 technical + 1 memory + 1 execution + Red Team

Redis Streams:
    council:tasks    — PC1 dispatches agent tasks for PC2 (XADD)
    council:results  — PC2 writes completed votes back (XADD)
    Consumer group:  council_workers / consumer: pc2

Part of Phase 4 — Council Optimization (#39)
"""
import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Stream names
TASKS_STREAM = "council:tasks"
RESULTS_STREAM = "council:results"
CONSUMER_GROUP = "council_workers"

# ── Agent-to-PC assignment ──────────────────────────────────────────────────
# PC1: 6 perception + 4 technical + hypothesis + strategy(seq) + 2 risk + debate + critic(seq) + arbiter
PC1_AGENTS: Set[str] = {
    # Stage 1 perception (6)
    "market_perception", "flow_perception", "regime",
    "social_perception", "news_catalyst", "youtube_knowledge",
    # Stage 2 technical (4)
    "rsi", "bbv", "ema_trend", "relative_strength",
    # Stage 3 (1)
    "hypothesis",
    # Stage 4 — strategy (sequential, always PC1)
    "strategy",
    # Stage 5 (2)
    "risk", "portfolio_optimizer_agent",
    # Stage 6 — critic (sequential, always PC1)
    "critic",
}

# PC2: 7 perception + 4 technical + memory + execution + red team
PC2_AGENTS: Set[str] = {
    # Stage 1 perception (7)
    "intermarket", "gex_agent", "insider_agent",
    "finbert_sentiment_agent", "earnings_tone_agent",
    "dark_pool_agent", "macro_regime_agent",
    # Stage 2 technical (4)
    "cycle_timing", "supply_chain_agent",
    "institutional_flow_agent", "congressional_agent",
    # Stage 3 (1)
    "layered_memory_agent",
    # Stage 5 (1)
    "execution",
    # Stage 5.5 — Red Team
    "red_team",
}

# Stages that must run sequentially on PC1 (never distributed)
SEQUENTIAL_PC1_STAGES = {"strategy", "critic", "arbiter"}


@dataclass
class StageLatency:
    """Tracks per-stage latency on each PC."""
    stage: str
    pc: str  # "pc1" or "pc2"
    start_ms: float = 0.0
    end_ms: float = 0.0
    agent_count: int = 0
    failed_count: int = 0

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "pc": self.pc,
            "duration_ms": round(self.duration_ms, 1),
            "agent_count": self.agent_count,
            "failed_count": self.failed_count,
        }


@dataclass
class DistributedResult:
    """Result from a distributed stage execution."""
    votes: List[Dict[str, Any]] = field(default_factory=list)
    latencies: List[StageLatency] = field(default_factory=list)
    pc2_available: bool = False
    fell_back_to_local: bool = False


class CouncilCoordinator:
    """Orchestrates distributed council execution across PCs via Redis Streams.

    When Redis is available and PC2 worker is connected, splits work between
    PCs per the assignment tables above. Falls back to local-only execution
    when Redis/PC2 is unavailable.
    """

    def __init__(self):
        self._redis = None
        self._available = False
        self._pc2_last_seen: float = 0.0
        self._pc2_timeout: float = 30.0  # Consider PC2 dead after 30s no heartbeat
        self._total_dispatches: int = 0
        self._total_fallbacks: int = 0
        self._result_timeout: float = 25.0  # Max wait for PC2 results per stage

        self._connect_redis()

    def _connect_redis(self) -> None:
        """Connect to Redis and ensure streams/consumer groups exist."""
        redis_url = ""
        try:
            from app.core.config import settings
            redis_url = getattr(settings, "REDIS_URL", "") or ""
        except Exception:
            pass
        if not redis_url:
            redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            logger.info("CouncilCoordinator: no REDIS_URL — local-only mode")
            return

        try:
            import redis as sync_redis
            self._redis = sync_redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            self._redis.ping()

            # Ensure streams and consumer groups exist
            for stream in (TASKS_STREAM, RESULTS_STREAM):
                try:
                    self._redis.xgroup_create(
                        stream, CONSUMER_GROUP, id="0", mkstream=True,
                    )
                except Exception:
                    pass  # Group already exists

            self._available = True
            logger.info("CouncilCoordinator: Redis connected, distributed mode enabled")
        except Exception as e:
            logger.warning("CouncilCoordinator: Redis unavailable (%s) — local-only mode", e)
            self._redis = None
            self._available = False

    @property
    def is_distributed(self) -> bool:
        """True if Redis is connected and PC2 worker has been seen recently."""
        if not self._available or not self._redis:
            return False
        # Check if PC2 has sent a heartbeat recently
        if self._pc2_last_seen > 0:
            age = time.time() - self._pc2_last_seen
            return age < self._pc2_timeout
        # If we've never seen PC2, check Redis for recent results
        try:
            info = self._redis.xinfo_groups(TASKS_STREAM)
            for group in info:
                if group.get("consumers", 0) > 0:
                    return True
        except Exception:
            pass
        return False

    def update_pc2_heartbeat(self) -> None:
        """Called when we receive any result from PC2."""
        self._pc2_last_seen = time.time()

    def get_pc_assignment(self, agent_type: str) -> str:
        """Return 'pc1' or 'pc2' for an agent type."""
        if agent_type in PC2_AGENTS:
            return "pc2"
        return "pc1"

    def split_stage_agents(
        self, agent_types: List[str],
    ) -> Tuple[List[str], List[str]]:
        """Split a list of agents into PC1 and PC2 groups.

        Returns (pc1_agents, pc2_agents).
        """
        pc1 = [a for a in agent_types if a not in PC2_AGENTS]
        pc2 = [a for a in agent_types if a in PC2_AGENTS]
        return pc1, pc2

    def dispatch_to_pc2(
        self,
        decision_id: str,
        stage: str,
        agents: List[Dict[str, Any]],
    ) -> int:
        """Dispatch agent tasks to PC2 via Redis Stream.

        Args:
            decision_id: Council decision UUID
            stage: Stage name (e.g., "1", "2", "3")
            agents: List of agent config dicts with keys:
                agent_type, symbol, timeframe, features_json, context_json, model_tier

        Returns:
            Number of tasks dispatched.
        """
        if not self._redis or not self._available:
            return 0

        dispatched = 0
        for agent_cfg in agents:
            try:
                self._redis.xadd(TASKS_STREAM, {
                    "decision_id": decision_id,
                    "stage": stage,
                    "agent_type": agent_cfg["agent_type"],
                    "symbol": agent_cfg["symbol"],
                    "timeframe": agent_cfg.get("timeframe", "1d"),
                    "features_json": agent_cfg.get("features_json", "{}"),
                    "context_json": agent_cfg.get("context_json", "{}"),
                    "model_tier": agent_cfg.get("model_tier", "fast"),
                    "dispatched_at": str(time.time()),
                }, maxlen=5000)
                dispatched += 1
            except Exception as e:
                logger.warning(
                    "CouncilCoordinator: failed to dispatch %s: %s",
                    agent_cfg.get("agent_type"), e,
                )

        self._total_dispatches += dispatched
        logger.info(
            "CouncilCoordinator: dispatched %d/%d agents to PC2 (stage=%s, decision=%s)",
            dispatched, len(agents), stage, decision_id[:8],
        )
        return dispatched

    async def collect_results(
        self,
        decision_id: str,
        expected_count: int,
        timeout: float = 0,
    ) -> List[Dict[str, Any]]:
        """Collect results from PC2 via Redis Stream.

        Polls the results stream for votes matching this decision_id.
        Returns as soon as all expected results arrive or timeout.

        Args:
            decision_id: Council decision UUID to match
            expected_count: Number of results to wait for
            timeout: Max seconds to wait (0 = use default)

        Returns:
            List of vote dicts from PC2.
        """
        if not self._redis or not self._available:
            return []

        timeout = timeout or self._result_timeout
        results = []
        deadline = time.time() + timeout
        poll_interval = 0.1  # 100ms polling

        while time.time() < deadline and len(results) < expected_count:
            try:
                # Read from results stream — use sync Redis in thread
                entries = await asyncio.to_thread(
                    self._redis.xread,
                    {RESULTS_STREAM: "0-0"},
                    count=expected_count * 2,
                    block=int(poll_interval * 1000),
                )

                for stream_name, messages in (entries or []):
                    for msg_id, fields in messages:
                        if fields.get("decision_id") == decision_id:
                            results.append(fields)
                            self.update_pc2_heartbeat()
                            # ACK the message
                            try:
                                await asyncio.to_thread(
                                    self._redis.xack,
                                    RESULTS_STREAM, CONSUMER_GROUP, msg_id,
                                )
                            except Exception:
                                pass

                if len(results) >= expected_count:
                    break

                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.warning("CouncilCoordinator: result collection error: %s", e)
                break

        if len(results) < expected_count:
            logger.warning(
                "CouncilCoordinator: only got %d/%d results for %s (timeout=%.1fs)",
                len(results), expected_count, decision_id[:8], timeout,
            )

        return results

    async def execute_distributed_stage(
        self,
        decision_id: str,
        stage: str,
        all_agents: List[Dict[str, Any]],
        spawner: Any,
    ) -> Tuple[List[Any], List[StageLatency]]:
        """Execute a stage with agents split between PC1 (local) and PC2 (remote).

        For agents assigned to PC1: runs locally via spawner.
        For agents assigned to PC2: dispatches to Redis Stream, collects results.
        Both execute in parallel.

        Args:
            decision_id: Council decision UUID
            stage: Stage name
            all_agents: Full list of agent config dicts for the stage
            spawner: TaskSpawner instance for local execution

        Returns:
            (votes, latencies) — merged votes from both PCs + latency records.
        """
        from app.council.schemas import AgentVote

        # Split agents between PCs
        pc1_configs = []
        pc2_configs = []
        for cfg in all_agents:
            if cfg["agent_type"] in PC2_AGENTS:
                pc2_configs.append(cfg)
            else:
                pc1_configs.append(cfg)

        latencies = []
        all_votes = []

        if not self.is_distributed or not pc2_configs:
            # All local — no PC2 available or no PC2 agents in this stage
            start = time.monotonic() * 1000
            local_votes = await spawner.spawn_parallel(all_agents)
            end = time.monotonic() * 1000
            latencies.append(StageLatency(
                stage=stage, pc="pc1", start_ms=start, end_ms=end,
                agent_count=len(all_agents),
                failed_count=sum(1 for v in local_votes if v.confidence <= 0),
            ))
            return local_votes, latencies

        # ── Distributed execution ────────────────────────────────────────
        logger.info(
            "Distributed stage %s: PC1=%d agents, PC2=%d agents",
            stage, len(pc1_configs), len(pc2_configs),
        )

        # Prepare PC2 dispatch data
        for cfg in pc2_configs:
            if "features_json" not in cfg:
                cfg["features_json"] = json.dumps(
                    cfg.get("features", {}), default=str,
                )
            if "context_json" not in cfg:
                # Strip non-serializable blackboard from context
                ctx = {
                    k: v for k, v in cfg.get("context", {}).items()
                    if k != "blackboard"
                }
                cfg["context_json"] = json.dumps(ctx, default=str)

        # Dispatch to PC2
        pc2_start = time.monotonic() * 1000
        dispatched = await asyncio.to_thread(
            self.dispatch_to_pc2, decision_id, stage, pc2_configs,
        )

        # Run PC1 agents locally + collect PC2 results in parallel
        pc1_start = time.monotonic() * 1000
        pc1_coro = spawner.spawn_parallel(pc1_configs) if pc1_configs else asyncio.sleep(0)
        pc2_coro = self.collect_results(
            decision_id, expected_count=dispatched,
            timeout=self._result_timeout,
        )

        pc1_result, pc2_raw = await asyncio.gather(
            pc1_coro, pc2_coro, return_exceptions=True,
        )

        pc1_end = time.monotonic() * 1000
        pc2_end = time.monotonic() * 1000

        # Process PC1 results
        if isinstance(pc1_result, list):
            all_votes.extend(pc1_result)
            latencies.append(StageLatency(
                stage=stage, pc="pc1", start_ms=pc1_start, end_ms=pc1_end,
                agent_count=len(pc1_configs),
                failed_count=sum(1 for v in pc1_result if v.confidence <= 0),
            ))
        elif isinstance(pc1_result, Exception):
            logger.warning("PC1 stage %s failed: %s", stage, pc1_result)

        # Process PC2 results — convert raw dicts to AgentVotes
        pc2_votes = []
        if isinstance(pc2_raw, list):
            for raw in pc2_raw:
                try:
                    vote = AgentVote(
                        agent_name=raw.get("agent_name", "unknown"),
                        direction=raw.get("direction", "hold"),
                        confidence=float(raw.get("confidence", 0)),
                        reasoning=raw.get("reasoning", ""),
                        veto=raw.get("veto", "false").lower() == "true" if isinstance(raw.get("veto"), str) else bool(raw.get("veto", False)),
                        veto_reason=raw.get("veto_reason", ""),
                        metadata=json.loads(raw.get("metadata_json", "{}")) if isinstance(raw.get("metadata_json"), str) else {},
                        blackboard_ref=decision_id,
                    )
                    pc2_votes.append(vote)
                except Exception as e:
                    logger.warning("CouncilCoordinator: bad PC2 result: %s", e)

            all_votes.extend(pc2_votes)
            latencies.append(StageLatency(
                stage=stage, pc="pc2", start_ms=pc2_start, end_ms=pc2_end,
                agent_count=dispatched,
                failed_count=dispatched - len(pc2_votes),
            ))
        elif isinstance(pc2_raw, Exception):
            logger.warning("PC2 stage %s collection failed: %s", stage, pc2_raw)

        # Fallback: if PC2 didn't return all results, run missing agents locally
        returned_agents = {v.agent_name for v in pc2_votes}
        missing = [
            cfg for cfg in pc2_configs
            if cfg["agent_type"] not in returned_agents
        ]
        if missing:
            logger.warning(
                "CouncilCoordinator: %d PC2 agents missing, running locally: %s",
                len(missing), [c["agent_type"] for c in missing],
            )
            self._total_fallbacks += len(missing)
            fallback_votes = await spawner.spawn_parallel(missing)
            all_votes.extend(fallback_votes)

        return all_votes, latencies

    def get_status(self) -> Dict[str, Any]:
        """Return coordinator status for monitoring."""
        return {
            "available": self._available,
            "distributed": self.is_distributed,
            "redis_connected": self._redis is not None,
            "pc2_last_seen_age_s": (
                round(time.time() - self._pc2_last_seen, 1)
                if self._pc2_last_seen > 0 else None
            ),
            "total_dispatches": self._total_dispatches,
            "total_fallbacks": self._total_fallbacks,
            "pc1_agents": sorted(PC1_AGENTS),
            "pc2_agents": sorted(PC2_AGENTS),
        }


# ── PC2 Worker — runs on the remote machine ─────────────────────────────────

class CouncilWorker:
    """Worker process for PC2 — reads tasks from Redis Stream, executes agents.

    Run this on PC2 with:
        python -m app.council.council_coordinator --worker
    """

    def __init__(self, consumer_name: str = "pc2"):
        self._consumer_name = consumer_name
        self._redis = None
        self._running = False
        self._tasks_processed = 0

        self._connect_redis()

    def _connect_redis(self) -> None:
        """Connect to Redis."""
        redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            try:
                from app.core.config import settings
                redis_url = getattr(settings, "REDIS_URL", "") or ""
            except Exception:
                pass
        if not redis_url:
            raise RuntimeError("CouncilWorker: REDIS_URL required")

        import redis as sync_redis
        self._redis = sync_redis.from_url(
            redis_url, decode_responses=True, socket_connect_timeout=5,
        )
        self._redis.ping()

        # Ensure consumer group exists
        for stream in (TASKS_STREAM, RESULTS_STREAM):
            try:
                self._redis.xgroup_create(
                    stream, CONSUMER_GROUP, id="0", mkstream=True,
                )
            except Exception:
                pass

        logger.info("CouncilWorker: Redis connected as consumer '%s'", self._consumer_name)

    async def run(self) -> None:
        """Main worker loop — reads tasks, executes agents, writes results."""
        from app.council.blackboard import BlackboardState
        from app.council.task_spawner import TaskSpawner

        self._running = True
        logger.info("CouncilWorker: starting worker loop")

        while self._running:
            try:
                # Block-read from tasks stream with consumer group
                entries = await asyncio.to_thread(
                    self._redis.xreadgroup,
                    CONSUMER_GROUP,
                    self._consumer_name,
                    {TASKS_STREAM: ">"},
                    count=10,
                    block=1000,  # 1s block
                )

                if not entries:
                    continue

                for stream_name, messages in entries:
                    for msg_id, fields in messages:
                        await self._process_task(fields, msg_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("CouncilWorker: loop error: %s", e)
                await asyncio.sleep(1)

        logger.info("CouncilWorker: stopped after %d tasks", self._tasks_processed)

    async def _process_task(self, fields: Dict[str, str], msg_id: str) -> None:
        """Execute a single agent task and write the result."""
        from app.council.blackboard import BlackboardState
        from app.council.task_spawner import TaskSpawner

        agent_type = fields.get("agent_type", "")
        decision_id = fields.get("decision_id", "")
        symbol = fields.get("symbol", "")
        timeframe = fields.get("timeframe", "1d")
        model_tier = fields.get("model_tier", "fast")

        start = time.monotonic()

        try:
            features = json.loads(fields.get("features_json", "{}"))
            context = json.loads(fields.get("context_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            features = {}
            context = {}

        # Create a minimal blackboard for this agent
        blackboard = BlackboardState(symbol=symbol, raw_features=features)
        blackboard.council_decision_id = decision_id
        context["blackboard"] = blackboard
        context["model_tier"] = model_tier

        # Spawn the agent
        spawner = TaskSpawner(blackboard)
        spawner.register_all_agents()

        vote = await spawner.spawn(
            agent_type=agent_type,
            symbol=symbol,
            timeframe=timeframe,
            features=features,
            context=context,
            model_tier=model_tier,
        )

        elapsed_ms = (time.monotonic() - start) * 1000

        # Write result to results stream
        try:
            result_data = {
                "decision_id": decision_id,
                "agent_name": vote.agent_name if vote else agent_type,
                "direction": vote.direction if vote else "hold",
                "confidence": str(vote.confidence if vote else 0.0),
                "reasoning": (vote.reasoning[:500] if vote and vote.reasoning else ""),
                "veto": str(vote.veto if vote else False),
                "veto_reason": (vote.veto_reason if vote else ""),
                "metadata_json": json.dumps(vote.metadata if vote and vote.metadata else {}, default=str),
                "latency_ms": str(round(elapsed_ms, 1)),
                "completed_at": str(time.time()),
            }
            await asyncio.to_thread(
                self._redis.xadd, RESULTS_STREAM, result_data, maxlen=5000,
            )
            # ACK the task
            await asyncio.to_thread(
                self._redis.xack, TASKS_STREAM, CONSUMER_GROUP, msg_id,
            )
            self._tasks_processed += 1

            logger.info(
                "CouncilWorker: completed %s for %s in %.0fms (decision=%s)",
                agent_type, symbol, elapsed_ms, decision_id[:8],
            )
        except Exception as e:
            logger.warning("CouncilWorker: result write failed for %s: %s", agent_type, e)

    def stop(self) -> None:
        """Signal the worker to stop."""
        self._running = False


# ── Module-level singleton ───────────────────────────────────────────────────
_coordinator: Optional[CouncilCoordinator] = None


def get_council_coordinator() -> CouncilCoordinator:
    """Get or create the singleton CouncilCoordinator."""
    global _coordinator
    if _coordinator is None:
        _coordinator = CouncilCoordinator()
    return _coordinator


# ── CLI entrypoint for PC2 worker ────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if "--worker" in sys.argv:
        logging.basicConfig(level=logging.INFO)
        worker = CouncilWorker()
        asyncio.run(worker.run())
    else:
        print("Usage: python -m app.council.council_coordinator --worker")
        print("  Starts the PC2 council worker that reads agent tasks from Redis.")
