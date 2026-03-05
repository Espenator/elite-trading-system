"""Heuristic Engine — extracts statistically significant patterns into transferable rules.

Mines the memory bank for recurring patterns that meet statistical thresholds:
    MIN_SAMPLE = 25 observations
    MIN_WIN_RATE = 0.55
    CONFIDENCE_THRESHOLD = 0.65 (Bayesian via Beta distribution posterior)

Generates human-readable heuristics like:
    "RSI divergence in trending_bull regime predicts reversals 73% of the time (n=42)"

Implements neuromorphic-inspired temporal decay: unused heuristics fade,
frequently-used ones get reinforced.

Runs nightly or every N trades.
"""
import json
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Heuristic:
    """A learned trading heuristic."""

    def __init__(
        self,
        heuristic_id: str = "",
        agent_name: str = "",
        regime: str = "",
        pattern_name: str = "",
        description: str = "",
        trigger_conditions: Dict[str, Any] = None,
        win_rate: float = 0.0,
        avg_r_multiple: float = 0.0,
        sample_size: int = 0,
        bayesian_confidence: float = 0.0,
        decay_factor: float = 1.0,
        active: bool = True,
    ):
        self.heuristic_id = heuristic_id or str(uuid.uuid4())
        self.agent_name = agent_name
        self.regime = regime
        self.pattern_name = pattern_name
        self.description = description
        self.trigger_conditions = trigger_conditions or {}
        self.win_rate = win_rate
        self.avg_r_multiple = avg_r_multiple
        self.sample_size = sample_size
        self.bayesian_confidence = bayesian_confidence
        self.decay_factor = decay_factor
        self.active = active
        self.created_at = datetime.now(timezone.utc)
        self.last_used_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heuristic_id": self.heuristic_id,
            "agent_name": self.agent_name,
            "regime": self.regime,
            "pattern_name": self.pattern_name,
            "description": self.description,
            "win_rate": round(self.win_rate, 4),
            "avg_r_multiple": round(self.avg_r_multiple, 3),
            "sample_size": self.sample_size,
            "bayesian_confidence": round(self.bayesian_confidence, 4),
            "decay_factor": round(self.decay_factor, 4),
            "active": self.active,
        }


class HeuristicEngine:
    """Extracts and manages learned heuristics from agent memories.

    Periodically scans the memory bank, clusters similar observations,
    and generates heuristics that meet statistical thresholds.
    """

    MIN_SAMPLE = 25
    MIN_WIN_RATE = 0.55
    CONFIDENCE_THRESHOLD = 0.65
    DECAY_FACTOR = 0.995  # per-day decay for unused heuristics
    DEACTIVATION_THRESHOLD = 0.3

    def __init__(self):
        self._heuristics: Dict[str, Heuristic] = {}  # heuristic_id -> Heuristic
        self._load_from_store()

    def extract_heuristics(self, agent_name: str) -> List[Heuristic]:
        """Extract heuristics from an agent's memory bank.

        Clusters similar resolved observations, computes win_rate and avg_R
        per cluster, generates human-readable descriptions, and computes
        Bayesian confidence via Beta distribution posterior.

        Args:
            agent_name: Agent to extract heuristics for

        Returns:
            List of newly created heuristics
        """
        from app.knowledge.memory_bank import get_memory_bank

        bank = get_memory_bank()
        # Load resolved memories
        memories = bank._load_from_store(agent_name, limit=1000)
        resolved = [m for m in memories if m.was_correct is not None]

        if len(resolved) < self.MIN_SAMPLE:
            logger.debug(
                "HeuristicEngine: not enough resolved memories for %s (%d < %d)",
                agent_name, len(resolved), self.MIN_SAMPLE,
            )
            return []

        # Group by regime
        regime_groups: Dict[str, List] = {}
        for m in resolved:
            regime = m.regime or "unknown"
            if regime not in regime_groups:
                regime_groups[regime] = []
            regime_groups[regime].append(m)

        new_heuristics = []

        for regime, group in regime_groups.items():
            if len(group) < self.MIN_SAMPLE:
                continue

            # Compute stats per vote direction
            for direction in ("buy", "sell"):
                dir_group = [m for m in group if m.agent_vote == direction]
                if len(dir_group) < self.MIN_SAMPLE:
                    continue

                wins = sum(1 for m in dir_group if m.was_correct)
                total = len(dir_group)
                win_rate = wins / total

                if win_rate < self.MIN_WIN_RATE:
                    continue

                # Bayesian confidence via Beta distribution
                # Beta(wins + 1, losses + 1) posterior
                alpha = wins + 1
                beta_param = (total - wins) + 1
                bayesian_conf = self._beta_confidence(alpha, beta_param)

                if bayesian_conf < self.CONFIDENCE_THRESHOLD:
                    continue

                # Compute average R-multiple
                r_values = [m.outcome_r_multiple for m in dir_group if m.outcome_r_multiple is not None]
                avg_r = sum(r_values) / len(r_values) if r_values else 0.0

                pattern_name = f"{agent_name}_{direction}_in_{regime}"
                description = (
                    f"{agent_name} voting {direction} in {regime} regime "
                    f"has {win_rate:.0%} win rate (n={total}, avg_R={avg_r:.2f})"
                )

                # Check if this heuristic already exists
                existing = self._find_existing(agent_name, regime, direction)
                if existing:
                    # Update existing
                    existing.win_rate = win_rate
                    existing.avg_r_multiple = avg_r
                    existing.sample_size = total
                    existing.bayesian_confidence = bayesian_conf
                    existing.description = description
                    existing.decay_factor = min(1.0, existing.decay_factor + 0.1)
                    self._persist_heuristic(existing)
                else:
                    # Create new
                    h = Heuristic(
                        agent_name=agent_name,
                        regime=regime,
                        pattern_name=pattern_name,
                        description=description,
                        trigger_conditions={"direction": direction, "regime": regime},
                        win_rate=win_rate,
                        avg_r_multiple=avg_r,
                        sample_size=total,
                        bayesian_confidence=bayesian_conf,
                    )
                    self._heuristics[h.heuristic_id] = h
                    new_heuristics.append(h)
                    self._persist_heuristic(h)
                    logger.info("New heuristic: %s", description)

        return new_heuristics

    def apply_temporal_decay(self) -> int:
        """Apply neuromorphic-inspired temporal decay to all heuristics.

        Unused heuristics fade (decay_factor *= 0.995).
        Deactivate when decay < 0.3.

        Returns:
            Number of heuristics deactivated
        """
        deactivated = 0
        for h in self._heuristics.values():
            if not h.active:
                continue
            h.decay_factor *= self.DECAY_FACTOR
            if h.decay_factor < self.DEACTIVATION_THRESHOLD:
                h.active = False
                deactivated += 1
                logger.info("Deactivated heuristic: %s (decay=%.3f)", h.pattern_name, h.decay_factor)
            self._persist_heuristic(h)
        return deactivated

    def reinforce_heuristic(self, heuristic_id: str) -> None:
        """Boost decay_factor when a heuristic proves useful."""
        h = self._heuristics.get(heuristic_id)
        if h:
            h.decay_factor = min(1.0, h.decay_factor + 0.1)
            h.last_used_at = datetime.now(timezone.utc)
            self._persist_heuristic(h)

    def get_active_heuristics(
        self, agent_name: str = None, regime: str = None
    ) -> List[Heuristic]:
        """Get active heuristics, optionally filtered."""
        results = [h for h in self._heuristics.values() if h.active]
        if agent_name:
            results = [h for h in results if h.agent_name == agent_name]
        if regime:
            results = [h for h in results if h.regime == regime or not h.regime]
        return sorted(results, key=lambda h: h.bayesian_confidence, reverse=True)

    def get_applicable_heuristics(
        self, agent_name: str, regime: str, direction: str
    ) -> List[Dict[str, Any]]:
        """Get heuristics that match current conditions.

        Returns list of heuristic dicts with confidence-adjusted recommendations.
        """
        applicable = []
        for h in self.get_active_heuristics(agent_name, regime):
            trigger = h.trigger_conditions
            if trigger.get("direction") == direction and trigger.get("regime") == regime:
                applicable.append({
                    "heuristic_id": h.heuristic_id,
                    "description": h.description,
                    "win_rate": h.win_rate,
                    "avg_r": h.avg_r_multiple,
                    "confidence": h.bayesian_confidence * h.decay_factor,
                    "sample_size": h.sample_size,
                })
        return applicable

    def _beta_confidence(self, alpha: int, beta: int) -> float:
        """Compute Bayesian confidence using Beta distribution.

        Returns the probability that the true win rate > 0.5.
        Uses normal approximation for large samples.
        """
        if alpha + beta < 4:
            return 0.5
        mean = alpha / (alpha + beta)
        var = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
        std = math.sqrt(var)
        if std == 0:
            return 1.0 if mean > 0.5 else 0.0
        # P(p > 0.5) approximated via normal CDF
        z = (mean - 0.5) / std
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))

    def _find_existing(self, agent_name: str, regime: str, direction: str) -> Optional[Heuristic]:
        """Find an existing heuristic matching these conditions."""
        for h in self._heuristics.values():
            if (
                h.agent_name == agent_name
                and h.regime == regime
                and h.trigger_conditions.get("direction") == direction
            ):
                return h
        return None

    def _persist_heuristic(self, h: Heuristic) -> None:
        """Persist a heuristic to DuckDB."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            conn.execute("""
                INSERT OR REPLACE INTO heuristics
                (heuristic_id, agent_name, regime, pattern_name, description,
                 trigger_conditions, win_rate, avg_r_multiple, sample_size,
                 bayesian_confidence, decay_factor, active, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                h.heuristic_id, h.agent_name, h.regime, h.pattern_name,
                h.description, json.dumps(h.trigger_conditions), h.win_rate,
                h.avg_r_multiple, h.sample_size, h.bayesian_confidence,
                h.decay_factor, h.active,
                h.last_used_at.isoformat() if h.last_used_at else None,
            ])
        except Exception as e:
            logger.debug("Heuristic persist failed: %s", e)

    def _load_from_store(self) -> None:
        """Load heuristics from DuckDB."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            rows = conn.execute("SELECT * FROM heuristics WHERE active = TRUE").fetchall()
            cols = [desc[0] for desc in conn.description] if rows else []
            for row in rows:
                d = dict(zip(cols, row))
                h = Heuristic(
                    heuristic_id=d.get("heuristic_id", ""),
                    agent_name=d.get("agent_name", ""),
                    regime=d.get("regime", ""),
                    pattern_name=d.get("pattern_name", ""),
                    description=d.get("description", ""),
                    trigger_conditions=json.loads(d.get("trigger_conditions", "{}"))
                        if isinstance(d.get("trigger_conditions"), str) else d.get("trigger_conditions", {}),
                    win_rate=float(d.get("win_rate", 0)),
                    avg_r_multiple=float(d.get("avg_r_multiple", 0)),
                    sample_size=int(d.get("sample_size", 0)),
                    bayesian_confidence=float(d.get("bayesian_confidence", 0)),
                    decay_factor=float(d.get("decay_factor", 1.0)),
                    active=bool(d.get("active", True)),
                )
                self._heuristics[h.heuristic_id] = h
            if rows:
                logger.info("Loaded %d active heuristics from DuckDB", len(rows))
        except Exception as e:
            logger.debug("Heuristic load failed: %s", e)


# Singleton
_engine: Optional[HeuristicEngine] = None


def get_heuristic_engine() -> HeuristicEngine:
    global _engine
    if _engine is None:
        _engine = HeuristicEngine()
    return _engine
