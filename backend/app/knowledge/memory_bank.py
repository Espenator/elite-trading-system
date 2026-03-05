"""Memory Bank — persistent agent observation storage with embeddings.

Each agent's observation for every trade is stored with a vector embedding,
enabling similarity-based recall of relevant past experiences. This is the
foundation of compound intelligence — every trade teaches the system.

Architecture:
    - DuckDB for structured storage and fast retrieval
    - RTX GPU for embedding generation via sentence-transformers
    - Cosine similarity search for memory recall
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class AgentMemory:
    """A single agent observation stored in the memory bank."""

    def __init__(
        self,
        agent_name: str,
        symbol: str,
        regime: str = "",
        market_context: Dict[str, Any] = None,
        agent_observation: Dict[str, Any] = None,
        agent_vote: str = "hold",
        confidence: float = 0.0,
        trade_id: str = "",
        embedding: np.ndarray = None,
    ):
        self.memory_id = str(uuid.uuid4())
        self.agent_name = agent_name
        self.trade_id = trade_id
        self.symbol = symbol
        self.timestamp = datetime.now(timezone.utc)
        self.regime = regime
        self.market_context = market_context or {}
        self.agent_observation = agent_observation or {}
        self.agent_vote = agent_vote
        self.confidence = confidence
        self.embedding = embedding
        self.outcome_r_multiple: Optional[float] = None
        self.was_correct: Optional[bool] = None


class MemoryBank:
    """Persistent memory bank for agent observations.

    Stores every agent observation with embedding vectors for
    similarity-based recall. Updated with outcomes when trades resolve.
    """

    def __init__(self):
        self._cache: Dict[str, List[AgentMemory]] = {}  # agent_name -> recent memories
        self._init_schema()

    def _init_schema(self) -> None:
        """Ensure agent_memories table exists (created by DuckDB storage init)."""
        pass  # Table created in duckdb_storage._init_schema()

    def store_observation(self, memory: AgentMemory) -> str:
        """Store an agent observation with embedding.

        Args:
            memory: AgentMemory object with observation data

        Returns:
            memory_id of the stored observation
        """
        # Generate embedding if not provided
        if memory.embedding is None:
            memory.embedding = self._generate_embedding(memory)

        # Cache in-memory for fast recall
        if memory.agent_name not in self._cache:
            self._cache[memory.agent_name] = []
        self._cache[memory.agent_name].append(memory)
        # Keep cache bounded
        if len(self._cache[memory.agent_name]) > 500:
            self._cache[memory.agent_name] = self._cache[memory.agent_name][-500:]

        # Persist to DuckDB
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            conn.execute("""
                INSERT INTO agent_memories
                (memory_id, agent_name, trade_id, symbol, timestamp, regime,
                 market_context, agent_observation, agent_vote, confidence, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                memory.memory_id,
                memory.agent_name,
                memory.trade_id,
                memory.symbol,
                memory.timestamp.isoformat(),
                memory.regime,
                json.dumps(memory.market_context, default=str),
                json.dumps(memory.agent_observation, default=str),
                memory.agent_vote,
                memory.confidence,
                memory.embedding.tolist() if memory.embedding is not None else None,
            ])
        except Exception as e:
            logger.debug("Memory bank persist failed: %s", e)

        return memory.memory_id

    def recall_similar(
        self,
        agent_name: str,
        current_context: Dict[str, Any],
        regime: str = "",
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Recall similar past observations for an agent.

        Uses embedding similarity to find the most relevant past
        experiences, optionally filtered by regime.

        Args:
            agent_name: Agent to recall memories for
            current_context: Current market context for embedding
            regime: Optional regime filter
            top_k: Number of memories to return

        Returns:
            List of memory dicts sorted by relevance
        """
        from app.knowledge.embedding_service import get_embedding_engine
        engine = get_embedding_engine()

        # Generate query embedding from current context
        context_text = self._context_to_text(current_context, regime)
        query_embedding = engine.embed_single(context_text)

        # Try in-memory cache first
        memories = self._cache.get(agent_name, [])

        # If cache is sparse, load from DuckDB
        if len(memories) < top_k:
            memories = self._load_from_store(agent_name, regime, limit=200)

        if not memories:
            return []

        # Filter by regime if specified
        if regime:
            memories = [m for m in memories if m.regime == regime or not m.regime]

        if not memories:
            return []

        # Build embedding matrix
        embeddings = []
        valid_memories = []
        for m in memories:
            if m.embedding is not None:
                embeddings.append(m.embedding)
                valid_memories.append(m)

        if not embeddings:
            return []

        corpus = np.array(embeddings, dtype=np.float32)
        similar = engine.find_similar(query_embedding, corpus, top_k=top_k)

        results = []
        for idx, score in similar:
            if idx < len(valid_memories):
                m = valid_memories[idx]
                results.append({
                    "memory_id": m.memory_id,
                    "symbol": m.symbol,
                    "regime": m.regime,
                    "vote": m.agent_vote,
                    "confidence": m.confidence,
                    "was_correct": m.was_correct,
                    "r_multiple": m.outcome_r_multiple,
                    "similarity": round(score, 4),
                    "observation": m.agent_observation,
                })

        return results

    def update_outcome(
        self, trade_id: str, r_multiple: float, was_correct: bool
    ) -> None:
        """Update memories with trade outcome.

        Called by OutcomeTracker after trade resolution.
        """
        # Update cache
        for agent_memories in self._cache.values():
            for m in agent_memories:
                if m.trade_id == trade_id:
                    m.outcome_r_multiple = r_multiple
                    m.was_correct = was_correct

        # Update DuckDB
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            conn.execute("""
                UPDATE agent_memories
                SET outcome_r_multiple = ?, was_correct = ?
                WHERE trade_id = ?
            """, [r_multiple, was_correct, trade_id])
        except Exception as e:
            logger.debug("Memory bank outcome update failed: %s", e)

    def _generate_embedding(self, memory: AgentMemory) -> np.ndarray:
        """Generate embedding from memory content."""
        from app.knowledge.embedding_service import get_embedding_engine
        engine = get_embedding_engine()

        text = self._context_to_text(
            memory.market_context | memory.agent_observation,
            memory.regime,
        )
        return engine.embed_single(text)

    def _context_to_text(self, context: Dict[str, Any], regime: str = "") -> str:
        """Convert a context dict to a text string for embedding."""
        parts = []
        if regime:
            parts.append(f"regime:{regime}")
        for key, value in context.items():
            if isinstance(value, (int, float)):
                parts.append(f"{key}={value:.4f}" if isinstance(value, float) else f"{key}={value}")
            elif isinstance(value, str) and len(value) < 200:
                parts.append(f"{key}:{value}")
        return " ".join(parts[:50])  # Limit to prevent excessively long text

    def _load_from_store(
        self, agent_name: str, regime: str = "", limit: int = 200
    ) -> List[AgentMemory]:
        """Load memories from DuckDB."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()

            query = "SELECT * FROM agent_memories WHERE agent_name = ?"
            params = [agent_name]
            if regime:
                query += " AND regime = ?"
                params.append(regime)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            columns = [desc[0] for desc in conn.execute(query, params).description] if rows else []

            memories = []
            for row in rows:
                row_dict = dict(zip(columns, row)) if columns else {}
                m = AgentMemory(
                    agent_name=row_dict.get("agent_name", ""),
                    symbol=row_dict.get("symbol", ""),
                    regime=row_dict.get("regime", ""),
                    agent_vote=row_dict.get("agent_vote", "hold"),
                    confidence=float(row_dict.get("confidence", 0)),
                    trade_id=row_dict.get("trade_id", ""),
                )
                m.memory_id = row_dict.get("memory_id", "")
                m.outcome_r_multiple = row_dict.get("outcome_r_multiple")
                m.was_correct = row_dict.get("was_correct")
                emb = row_dict.get("embedding")
                if emb and isinstance(emb, list):
                    m.embedding = np.array(emb, dtype=np.float32)
                memories.append(m)
            return memories
        except Exception as e:
            logger.debug("Memory bank load failed: %s", e)
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Return memory bank statistics."""
        total_cached = sum(len(v) for v in self._cache.values())
        return {
            "agents_in_cache": len(self._cache),
            "total_cached_memories": total_cached,
            "agent_counts": {k: len(v) for k, v in self._cache.items()},
        }


# Singleton
_bank: Optional[MemoryBank] = None


def get_memory_bank() -> MemoryBank:
    global _bank
    if _bank is None:
        _bank = MemoryBank()
    return _bank
