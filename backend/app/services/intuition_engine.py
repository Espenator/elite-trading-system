"""Intuition Engine — embedding-based pattern matching from episodic memory.

Looks up similar past episodes before the council runs to provide
"intuition" — a prior based on what happened in similar situations.

Uses DuckDB's list_cosine_similarity for vector search against
episodic_memory embeddings.

Usage:
    from app.services.intuition_engine import get_intuition_engine
    engine = get_intuition_engine()
    intuition = await engine.get_intuition("AAPL", regime="bull_quiet", signal_score=78.5)
"""

import logging
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntuitionEngine:
    """Embedding-based pattern lookup for council pre-priming.

    Before the council evaluates a signal, the IntuitionEngine searches
    episodic memory for similar past situations and returns a "gut feeling"
    based on how those situations resolved.
    """

    def __init__(self, top_k: int = 5, min_similarity: float = 0.7):
        self.top_k = top_k
        self.min_similarity = min_similarity
        self._query_count: int = 0
        self._hit_count: int = 0

    async def get_intuition(
        self,
        symbol: str,
        regime: str = "",
        signal_score: float = 0.0,
        features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query episodic memory for similar past situations.

        Parameters
        ----------
        symbol : str
            The ticker being evaluated.
        regime : str
            Current market regime.
        signal_score : float
            Current signal score.
        features : dict, optional
            Current feature vector for embedding computation.

        Returns
        -------
        Dict with intuition data:
          - prior_direction: suggested direction from similar episodes
          - prior_confidence: how confident the intuition is
          - similar_episodes: list of matched episodes
          - episode_count: number of matches found
        """
        self._query_count += 1

        # Try embedding-based search first
        similar = await self._search_by_embedding(symbol, regime, signal_score, features)

        if not similar:
            # Fall back to regime + symbol search
            similar = await self._search_by_regime(symbol, regime)

        if not similar:
            return {
                "prior_direction": "hold",
                "prior_confidence": 0.0,
                "similar_episodes": [],
                "episode_count": 0,
                "source": "no_memory",
            }

        self._hit_count += 1

        # Aggregate outcomes from similar episodes
        directions = {"buy": 0.0, "sell": 0.0, "hold": 0.0}
        total_weight = 0.0
        wins = 0
        total_resolved = 0

        for ep in similar:
            outcome = ep.get("outcome", "")
            direction = ep.get("direction", "hold")
            similarity = ep.get("similarity", 0.5)

            if outcome in ("win", "profit"):
                directions[direction] = directions.get(direction, 0) + similarity
                wins += 1
                total_resolved += 1
            elif outcome in ("loss", "stop_loss"):
                # Opposite direction would have been right
                opp = "sell" if direction == "buy" else "buy"
                directions[opp] = directions.get(opp, 0) + similarity
                total_resolved += 1
            else:
                directions[direction] = directions.get(direction, 0) + similarity * 0.5

            total_weight += similarity

        # Find dominant direction
        if total_weight > 0:
            for d in directions:
                directions[d] /= total_weight

        prior_direction = max(directions, key=directions.get)
        prior_confidence = directions[prior_direction]

        win_rate = wins / max(total_resolved, 1)

        return {
            "prior_direction": prior_direction,
            "prior_confidence": round(prior_confidence, 3),
            "win_rate": round(win_rate, 3),
            "similar_episodes": similar[:3],  # top 3 for context
            "episode_count": len(similar),
            "source": "episodic_memory",
        }

    async def _search_by_embedding(
        self,
        symbol: str,
        regime: str,
        signal_score: float,
        features: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Search episodic memory using cosine similarity on embeddings."""
        if not features:
            return []

        try:
            # Generate a simple feature hash as embedding proxy
            # In production this would use a real embedding model
            embedding = self._features_to_embedding(features)
            if not embedding:
                return []

            from app.data.duckdb_storage import duckdb_store

            # DuckDB cosine similarity search
            rows = duckdb_store.query(
                """SELECT episode_id, symbol, regime, direction, outcome,
                          confidence, pnl, r_multiple,
                          list_cosine_similarity(embedding, ?::DOUBLE[768]) as similarity
                   FROM episodic_memory
                   WHERE embedding IS NOT NULL
                     AND outcome IS NOT NULL
                   ORDER BY similarity DESC
                   LIMIT ?""",
                [embedding, self.top_k],
            ).fetchall()

            results = []
            for row in rows:
                sim = row[8] if row[8] is not None else 0.0
                if sim >= self.min_similarity:
                    results.append({
                        "episode_id": row[0],
                        "symbol": row[1],
                        "regime": row[2],
                        "direction": row[3],
                        "outcome": row[4],
                        "confidence": row[5],
                        "pnl": row[6],
                        "r_multiple": row[7],
                        "similarity": round(sim, 4),
                    })
            return results

        except Exception as e:
            logger.debug("Embedding search failed: %s", e)
            return []

    async def _search_by_regime(
        self, symbol: str, regime: str
    ) -> List[Dict[str, Any]]:
        """Fallback: search by regime and symbol match."""
        try:
            from app.data.duckdb_storage import duckdb_store

            rows = duckdb_store.query(
                """SELECT episode_id, symbol, regime, direction, outcome,
                          confidence, pnl, r_multiple
                   FROM episodic_memory
                   WHERE outcome IS NOT NULL
                     AND (symbol = ? OR regime = ?)
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                [symbol.upper(), regime, self.top_k * 2],
            ).fetchall()

            results = []
            for row in rows:
                # Compute a simple similarity based on symbol/regime match
                sim = 0.5
                if row[1] == symbol.upper():
                    sim += 0.25
                if row[2] == regime:
                    sim += 0.25
                results.append({
                    "episode_id": row[0],
                    "symbol": row[1],
                    "regime": row[2],
                    "direction": row[3],
                    "outcome": row[4],
                    "confidence": row[5],
                    "pnl": row[6],
                    "r_multiple": row[7],
                    "similarity": sim,
                })

            # Sort by similarity descending
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:self.top_k]

        except Exception as e:
            logger.debug("Regime search failed: %s", e)
            return []

    def _features_to_embedding(self, features: Dict[str, Any]) -> Optional[List[float]]:
        """Convert feature dict to a 768-dim embedding proxy.

        In production, use a proper embedding model (e.g., sentence-transformers).
        This creates a deterministic hash-based embedding for development.
        """
        try:
            feature_str = json.dumps(features, sort_keys=True, default=str)
            digest = hashlib.sha256(feature_str.encode()).hexdigest()

            # Convert hex digest to 768 floats in [-1, 1]
            embedding = []
            for i in range(768):
                # Use overlapping 2-char hex slices, cycling through the digest
                idx = (i * 2) % len(digest)
                val = int(digest[idx:idx + 2], 16) / 255.0 * 2 - 1
                embedding.append(round(val, 6))
            return embedding
        except Exception:
            return None

    def get_status(self) -> Dict[str, Any]:
        """Return engine status."""
        hit_rate = self._hit_count / max(self._query_count, 1)
        return {
            "queries": self._query_count,
            "hits": self._hit_count,
            "hit_rate": round(hit_rate, 3),
            "top_k": self.top_k,
            "min_similarity": self.min_similarity,
        }


_instance: Optional[IntuitionEngine] = None


def get_intuition_engine() -> IntuitionEngine:
    """Get or create the global IntuitionEngine singleton."""
    global _instance
    if _instance is None:
        _instance = IntuitionEngine()
    return _instance
