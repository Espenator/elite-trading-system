"""Knowledge Graph — connects cross-agent insights for exponential compounding.

Builds edges between heuristics that co-occur in successful trades:
    - "confirms": heuristics that frequently co-occur in wins
    - "contradicts": heuristics that appear in opposing outcomes
    - "precedes": temporal ordering (one heuristic fires before another)
    - "amplifies": combined occurrence yields higher R than individual

This creates a network of institutional knowledge that compounds
across agents — the system learns not just what works, but what
works TOGETHER.
"""
import json
import logging
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class KnowledgeEdge:
    """An edge connecting two heuristics in the knowledge graph."""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        relationship: str,  # "confirms", "contradicts", "precedes", "amplifies"
        strength: float = 0.5,
        co_occurrence_count: int = 0,
    ):
        self.edge_id = str(uuid.uuid4())
        self.source_id = source_id
        self.target_id = target_id
        self.relationship = relationship
        self.strength = strength
        self.co_occurrence_count = co_occurrence_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "strength": round(self.strength, 4),
            "co_occurrence_count": self.co_occurrence_count,
        }


class KnowledgeGraph:
    """Connects heuristics into a knowledge network.

    Analyzes co-occurrence patterns across successful trades to
    discover cross-agent synergies and contradictions.
    """

    MIN_CO_OCCURRENCE = 5  # minimum trades together to form edge

    def __init__(self):
        self._edges: Dict[str, KnowledgeEdge] = {}
        self._adjacency: Dict[str, List[str]] = defaultdict(list)  # heuristic_id -> edge_ids
        self._load_from_store()

    def build_edges(self) -> int:
        """Analyze heuristic co-occurrences and build edges.

        Scans the memory bank for trades where multiple heuristics
        were active, and creates edges based on outcome patterns.

        Returns:
            Number of new edges created
        """
        from app.knowledge.heuristic_engine import get_heuristic_engine
        from app.knowledge.memory_bank import get_memory_bank

        engine = get_heuristic_engine()
        bank = get_memory_bank()

        active = engine.get_active_heuristics()
        if len(active) < 2:
            return 0

        # Group memories by trade_id to find co-occurrences
        trade_heuristics: Dict[str, Dict[str, Any]] = {}  # trade_id -> {heuristic_ids, outcome}

        for h in active:
            # Find memories that match this heuristic's conditions
            agent_memories = bank._load_from_store(h.agent_name, h.regime, limit=500)
            for m in agent_memories:
                if m.trade_id and m.was_correct is not None:
                    conditions = h.trigger_conditions
                    if (
                        m.agent_vote == conditions.get("direction")
                        and m.regime == conditions.get("regime")
                    ):
                        if m.trade_id not in trade_heuristics:
                            trade_heuristics[m.trade_id] = {
                                "heuristic_ids": set(),
                                "was_correct": m.was_correct,
                                "r_multiple": m.outcome_r_multiple or 0,
                            }
                        trade_heuristics[m.trade_id]["heuristic_ids"].add(h.heuristic_id)

        # Count co-occurrences
        pair_stats: Dict[Tuple[str, str], Dict[str, int]] = {}
        for trade_data in trade_heuristics.values():
            ids = sorted(trade_data["heuristic_ids"])
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    pair = (ids[i], ids[j])
                    if pair not in pair_stats:
                        pair_stats[pair] = {"wins": 0, "losses": 0, "total": 0, "r_sum": 0.0}
                    pair_stats[pair]["total"] += 1
                    if trade_data["was_correct"]:
                        pair_stats[pair]["wins"] += 1
                    else:
                        pair_stats[pair]["losses"] += 1
                    pair_stats[pair]["r_sum"] += trade_data["r_multiple"]

        # Create edges for significant co-occurrences
        new_edges = 0
        for (h1, h2), stats in pair_stats.items():
            if stats["total"] < self.MIN_CO_OCCURRENCE:
                continue

            win_rate = stats["wins"] / stats["total"]
            avg_r = stats["r_sum"] / stats["total"]

            # Determine relationship type
            if win_rate > 0.65:
                relationship = "confirms"
                strength = win_rate
            elif win_rate < 0.35:
                relationship = "contradicts"
                strength = 1.0 - win_rate
            elif avg_r > 1.5:
                relationship = "amplifies"
                strength = min(1.0, avg_r / 3.0)
            else:
                continue  # Not significant enough

            # Check if edge already exists
            existing = self._find_edge(h1, h2)
            if existing:
                existing.strength = strength
                existing.co_occurrence_count = stats["total"]
                self._persist_edge(existing)
            else:
                edge = KnowledgeEdge(
                    source_id=h1,
                    target_id=h2,
                    relationship=relationship,
                    strength=strength,
                    co_occurrence_count=stats["total"],
                )
                self._edges[edge.edge_id] = edge
                self._adjacency[h1].append(edge.edge_id)
                self._adjacency[h2].append(edge.edge_id)
                self._persist_edge(edge)
                new_edges += 1
                logger.info(
                    "Knowledge edge: %s %s %s (strength=%.2f, n=%d)",
                    h1[:8], relationship, h2[:8], strength, stats["total"],
                )

        return new_edges

    def get_confirming_patterns(
        self, active_heuristic_ids: Set[str]
    ) -> List[Dict[str, Any]]:
        """Find cross-agent patterns that reinforce current signals.

        Args:
            active_heuristic_ids: Set of heuristic IDs currently active

        Returns:
            List of confirming pattern dicts with strength and descriptions
        """
        confirming = []
        for h_id in active_heuristic_ids:
            edge_ids = self._adjacency.get(h_id, [])
            for eid in edge_ids:
                edge = self._edges.get(eid)
                if not edge:
                    continue
                # Check if the other end is also active
                other_id = edge.target_id if edge.source_id == h_id else edge.source_id
                if other_id in active_heuristic_ids and edge.relationship == "confirms":
                    confirming.append({
                        "edge_id": edge.edge_id,
                        "heuristic_1": edge.source_id,
                        "heuristic_2": edge.target_id,
                        "relationship": edge.relationship,
                        "strength": edge.strength,
                        "co_occurrences": edge.co_occurrence_count,
                    })

        return sorted(confirming, key=lambda x: x["strength"], reverse=True)

    def get_contradictions(
        self, active_heuristic_ids: Set[str]
    ) -> List[Dict[str, Any]]:
        """Find contradicting patterns among active heuristics."""
        contradictions = []
        for h_id in active_heuristic_ids:
            for eid in self._adjacency.get(h_id, []):
                edge = self._edges.get(eid)
                if not edge:
                    continue
                other_id = edge.target_id if edge.source_id == h_id else edge.source_id
                if other_id in active_heuristic_ids and edge.relationship == "contradicts":
                    contradictions.append(edge.to_dict())
        return contradictions

    def get_stats(self) -> Dict[str, Any]:
        rel_counts = defaultdict(int)
        for e in self._edges.values():
            rel_counts[e.relationship] += 1
        return {
            "total_edges": len(self._edges),
            "relationships": dict(rel_counts),
            "nodes_connected": len(self._adjacency),
        }

    def _find_edge(self, h1: str, h2: str) -> Optional[KnowledgeEdge]:
        """Find an existing edge between two heuristics."""
        for eid in self._adjacency.get(h1, []):
            edge = self._edges.get(eid)
            if edge and (
                (edge.source_id == h1 and edge.target_id == h2)
                or (edge.source_id == h2 and edge.target_id == h1)
            ):
                return edge
        return None

    def _persist_edge(self, edge: KnowledgeEdge) -> None:
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            conn.execute("""
                INSERT OR REPLACE INTO knowledge_edges
                (edge_id, source_heuristic_id, target_heuristic_id,
                 relationship, strength, co_occurrence_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                edge.edge_id, edge.source_id, edge.target_id,
                edge.relationship, edge.strength, edge.co_occurrence_count,
            ])
        except Exception as e:
            logger.debug("Knowledge edge persist failed: %s", e)

    def _load_from_store(self) -> None:
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            rows = conn.execute("SELECT * FROM knowledge_edges").fetchall()
            cols = [desc[0] for desc in conn.description] if rows else []
            for row in rows:
                d = dict(zip(cols, row))
                edge = KnowledgeEdge(
                    source_id=d.get("source_heuristic_id", ""),
                    target_id=d.get("target_heuristic_id", ""),
                    relationship=d.get("relationship", ""),
                    strength=float(d.get("strength", 0.5)),
                    co_occurrence_count=int(d.get("co_occurrence_count", 0)),
                )
                edge.edge_id = d.get("edge_id", edge.edge_id)
                self._edges[edge.edge_id] = edge
                self._adjacency[edge.source_id].append(edge.edge_id)
                self._adjacency[edge.target_id].append(edge.edge_id)
            if rows:
                logger.info("Loaded %d knowledge edges from DuckDB", len(rows))
        except Exception as e:
            logger.debug("Knowledge graph load failed: %s", e)


# Singleton
_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph()
    return _graph
