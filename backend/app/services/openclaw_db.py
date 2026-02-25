Made with Perplexity
"""
OpenClaw Bridge Database Service (ENHANCED - Memory Intelligence v2)
Raw sqlite3 — matches DatabaseService pattern in database.py

ORIGINAL Tables: openclaw_ingests, openclaw_signals
NEW Phase 1: ChromaDB semantic vector store (Semantic RAG)
NEW Phase 2: core_memory table (Letta-style Core Memory)
NEW Phase 3: Neo4j graph store (GraphRAG correlation wrapper)

DB: backend/data/trading_orders.db (same file as orders)
"""
from __future__ import annotations
import json
import math
import sqlite3
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "trading_orders.db"
VECTOR_STORE_DIR = Path(__file__).parent.parent.parent / "data" / "vector_store"

# ---------------------------------------------------------------------------
# Optional dependency imports (graceful degradation)
# ---------------------------------------------------------------------------
try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    logger.info("[OpenClawDB] chromadb not installed — Semantic RAG disabled")

try:
    from sentence_transformers import SentenceTransformer
    HAS_SBERT = True
except ImportError:
    HAS_SBERT = False
    logger.info("[OpenClawDB] sentence-transformers not installed — using doc-hash fallback")

try:
    from neo4j import GraphDatabase as Neo4jDriver
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False
    logger.info("[OpenClawDB] neo4j driver not installed — GraphRAG disabled")


class OpenClawDBService:
    """Persists OpenClaw bridge ingests + signals to SQLite.
    Enhanced with Semantic RAG, Core Memory, and GraphRAG layers."""

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()  # one conn per thread
        self._init_tables()

        # Phase 1: Semantic RAG — ChromaDB + embeddings
        self._embedding_model = None
        self._chroma_client = None
        self._chroma_collection = None
        self._init_semantic_rag()

        # Phase 3: GraphRAG — Neo4j
        self._neo4j_driver = None
        self._init_neo4j()

    # -- connection (thread-safe) -----------------------------------------
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(DB_PATH))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    # -- schema -----------------------------------------------------------
    def _init_tables(self):
        conn = self._conn()
        conn.executescript(
            """
            -- Original tables --
            CREATE TABLE IF NOT EXISTS openclaw_ingests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id      TEXT NOT NULL UNIQUE,
                received_at TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                regime_state      TEXT,
                regime_confidence REAL,
                regime_source     TEXT,
                universe_json     TEXT,
                signal_count      INTEGER NOT NULL DEFAULT 0,
                payload_hash      TEXT
            );

            CREATE TABLE IF NOT EXISTS openclaw_signals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ingest_id   INTEGER NOT NULL
                                REFERENCES openclaw_ingests(id)
                                ON DELETE CASCADE,
                run_id      TEXT NOT NULL,
                symbol      TEXT NOT NULL,
                direction   TEXT NOT NULL,
                score       REAL NOT NULL,
                subscores_json TEXT,
                entry       REAL,
                stop        REAL,
                target      REAL,
                timeframe   TEXT,
                reasons_json TEXT,
                raw_json    TEXT,
                received_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_oc_signals_symbol
                ON openclaw_signals(symbol);
            CREATE INDEX IF NOT EXISTS idx_oc_signals_run
                ON openclaw_signals(run_id);
            CREATE INDEX IF NOT EXISTS idx_oc_signals_received
                ON openclaw_signals(received_at DESC);
            CREATE INDEX IF NOT EXISTS idx_oc_ingests_received
                ON openclaw_ingests(received_at DESC);

            -- ======================================================== --
            -- PHASE 2: Core Memory (Letta-style self-editing memory)    --
            -- ======================================================== --
            CREATE TABLE IF NOT EXISTS core_memory (
                key         TEXT PRIMARY KEY,
                category    TEXT NOT NULL DEFAULT 'general',
                content     TEXT NOT NULL,
                priority    INTEGER NOT NULL DEFAULT 50,
                source      TEXT NOT NULL DEFAULT 'system',
                ttl_days    INTEGER,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_core_mem_category
                ON core_memory(category);
            CREATE INDEX IF NOT EXISTS idx_core_mem_priority
                ON core_memory(priority DESC);

            -- ======================================================== --
            -- PHASE 3: Local causal edges (fallback if Neo4j offline)   --
            -- ======================================================== --
            CREATE TABLE IF NOT EXISTS graph_edges (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node   TEXT NOT NULL,
                to_node     TEXT NOT NULL,
                edge_type   TEXT NOT NULL,
                weight      REAL DEFAULT 1.0,
                meta_json   TEXT DEFAULT '{}',
                created_at  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_graph_from ON graph_edges(from_node);
            CREATE INDEX IF NOT EXISTS idx_graph_to   ON graph_edges(to_node);
            CREATE INDEX IF NOT EXISTS idx_graph_type  ON graph_edges(edge_type);
            """
        )
        conn.commit()

    # ================================================================== #
    #  PHASE 1: SEMANTIC RAG — ChromaDB + Sentence Transformers          #
    # ================================================================== #

    def _init_semantic_rag(self):
        """Initialize ChromaDB persistent store and embedding model."""
        if not HAS_CHROMADB:
            return
        try:
            VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=str(VECTOR_STORE_DIR)
            )
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name="openclaw_semantic",
                metadata={"hnsw:space": "cosine"},
            )
            count = self._chroma_collection.count()
            logger.info(
                "[OpenClawDB] Semantic RAG initialized: %d vectors in store", count
            )
        except Exception as e:
            logger.error("[OpenClawDB] ChromaDB init failed: %s", e)
            self._chroma_collection = None

        # Load sentence-transformer model (lazy, first call)
        if HAS_SBERT:
            try:
                import os
                model_name = os.getenv(
                    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
                )
                self._embedding_model = SentenceTransformer(model_name)
                logger.info("[OpenClawDB] Embedding model loaded: %s", model_name)
            except Exception as e:
                logger.warning("[OpenClawDB] Embedding model load failed: %s", e)

    def _embed(self, text: str) -> List[float]:
        """Generate embedding vector for text.
        Falls back to a deterministic hash-based pseudo-embedding if
        sentence-transformers is unavailable."""
        if self._embedding_model is not None:
            return self._embedding_model.encode(text).tolist()
        # Fallback: 384-dim deterministic hash embedding
        h = hashlib.sha384(text.encode()).digest()
        return [((b / 255.0) * 2.0 - 1.0) for b in h]

    def _build_signal_document(self, signal: Dict, regime: Optional[Dict] = None) -> str:
        """Convert a structured signal dict into a rich text document for embedding."""
        parts = []
        sym = signal.get("symbol", "?")
        direction = signal.get("direction", "?")
        score = signal.get("score", 0)
        parts.append(f"{sym} {direction} signal score={score}")

        # Regime context
        if regime:
            parts.append(f"regime={regime.get('state', 'UNKNOWN')}")
        elif signal.get("_regime"):
            r = signal["_regime"]
            parts.append(f"regime={r.get('state', 'UNKNOWN')}")

        # Entry/stop/target
        if signal.get("entry"):
            parts.append(f"entry={signal['entry']}")
        if signal.get("stop"):
            parts.append(f"stop={signal['stop']}")
        if signal.get("target"):
            parts.append(f"target={signal['target']}")

        # Timeframe
        if signal.get("timeframe"):
            parts.append(f"timeframe={signal['timeframe']}")

        # Subscores
        subscores = signal.get("subscores") or signal.get("subscores_json")
        if isinstance(subscores, str):
            try:
                subscores = json.loads(subscores)
            except Exception:
                subscores = None
        if isinstance(subscores, dict):
            for k, v in subscores.items():
                parts.append(f"{k}={v}")

        # Reasons
        reasons = signal.get("reasons") or signal.get("reasons_json")
        if isinstance(reasons, str):
            try:
                reasons = json.loads(reasons)
            except Exception:
                reasons = None
        if isinstance(reasons, (list, tuple)):
            parts.append("reasons: " + "; ".join(str(r) for r in reasons[:5]))

        return " | ".join(parts)

    def semantic_upsert_signal(
        self, signal_db_id: int, signal: Dict, regime: Optional[Dict] = None
    ) -> bool:
        """Embed and upsert a signal into the semantic vector store."""
        if not self._chroma_collection:
            return False
        try:
            doc_text = self._build_signal_document(signal, regime)
            embedding = self._embed(doc_text)
            doc_id = f"sig_{signal_db_id}"
            meta = {
                "symbol": signal.get("symbol", ""),
                "direction": signal.get("direction", ""),
                "score": float(signal.get("score", 0)),
                "regime": (regime.get("state", "UNKNOWN") if regime
                           else signal.get("_regime", {}).get("state", "UNKNOWN")
                           if isinstance(signal.get("_regime"), dict) else "UNKNOWN"),
                "signal_db_id": signal_db_id,
                "received_at": signal.get("received_at", datetime.utcnow().isoformat()),
                "doc_type": "signal",
            }
            self._chroma_collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[meta],
                documents=[doc_text],
            )
            return True
        except Exception as e:
            logger.warning("[OpenClawDB] Semantic upsert failed: %s", e)
            return False

    def semantic_upsert_text(
        self, doc_id: str, text: str, metadata: Optional[Dict] = None
    ) -> bool:
        """Embed and upsert arbitrary text (news, discord, notes)."""
        if not self._chroma_collection:
            return False
        try:
            embedding = self._embed(text)
            meta = metadata or {}
            meta.setdefault("doc_type", "text")
            meta.setdefault("received_at", datetime.utcnow().isoformat())
            self._chroma_collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[meta],
                documents=[text],
            )
            return True
        except Exception as e:
            logger.warning("[OpenClawDB] Semantic text upsert failed: %s", e)
            return False

    def semantic_search(
        self,
        query: str,
        k: int = 10,
        symbol: Optional[str] = None,
        regime: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> List[Dict]:
        """Semantic similarity search over the vector store.
        Returns list of {id, document, metadata, similarity} dicts."""
        if not self._chroma_collection or self._chroma_collection.count() == 0:
            return []
        try:
            query_emb = self._embed(query)
            where_filter = {}
            if symbol:
                where_filter["symbol"] = symbol.upper()
            if regime:
                where_filter["regime"] = regime.upper()
            if doc_type:
                where_filter["doc_type"] = doc_type

            kwargs: Dict[str, Any] = {
                "query_embeddings": [query_emb],
                "n_results": min(k, self._chroma_collection.count()),
            }
            if where_filter:
                if len(where_filter) == 1:
                    kwargs["where"] = where_filter
                else:
                    kwargs["where"] = {"$and": [{kk: vv} for kk, vv in where_filter.items()]}

            results = self._chroma_collection.query(**kwargs)
            hits = []
            if results and results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    dist = results["distances"][0][i] if results.get("distances") else 0
                    hits.append({
                        "id": doc_id,
                        "document": results["documents"][0][i] if results.get("documents") else "",
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "similarity": round(1.0 - dist, 4),
                    })
            return hits
        except Exception as e:
            logger.warning("[OpenClawDB] Semantic search failed: %s", e)
            return []

    def semantic_build_context(
        self,
        query: str,
        k: int = 5,
        symbol: Optional[str] = None,
        regime: Optional[str] = None,
    ) -> str:
        """Build a compact context string from top-k semantic hits for LLM prompts."""
        hits = self.semantic_search(query, k=k, symbol=symbol, regime=regime)
        if not hits:
            return ""
        lines = []
        for i, h in enumerate(hits, 1):
            sim = h.get("similarity", 0)
            doc = h.get("document", "")[:200]
            lines.append(f"[{i}] (sim={sim:.3f}) {doc}")
        return "\n".join(lines)

    def semantic_health(self) -> Dict:
        """Return semantic store health metrics."""
        return {
            "chromadb": "active" if self._chroma_collection else "disabled",
            "embedding_model": "sbert" if self._embedding_model else "hash_fallback",
            "vector_count": self._chroma_collection.count() if self._chroma_collection else 0,
            "store_path": str(VECTOR_STORE_DIR),
        }

    def semantic_backfill(self, limit: int = 1000) -> int:
        """Backfill the vector store from existing SQLite signals."""
        if not self._chroma_collection:
            return 0
        existing = self._chroma_collection.count()
        conn = self._conn()
        rows = conn.execute(
            """SELECT s.id, s.symbol, s.direction, s.score, s.subscores_json,
                      s.entry, s.stop, s.target, s.timeframe, s.reasons_json,
                      s.received_at, i.regime_state
               FROM openclaw_signals s
               JOIN openclaw_ingests i ON s.ingest_id = i.id
               ORDER BY s.id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        count = 0
        for r in rows:
            sig = dict(r)
            regime = {"state": r["regime_state"] or "UNKNOWN"}
            if self.semantic_upsert_signal(r["id"], sig, regime):
                count += 1
        logger.info("[OpenClawDB] Backfilled %d/%d signals into vector store", count, len(rows))
        return count

    # ================================================================== #
    #  PHASE 2: CORE MEMORY — Letta-style self-editing agent memory      #
    # ================================================================== #

    CORE_MEMORY_CATEGORIES = [
        "risk",        # Risk management rules / lessons
        "execution",   # Execution patterns / preferences
        "regime",      # Regime-specific playbooks
        "preferences", # User/operator preferences
        "lessons",     # Lessons learned from outcomes
        "general",     # Uncategorized beliefs
    ]

    def core_memory_upsert(
        self,
        key: str,
        content: str,
        category: str = "general",
        priority: int = 50,
        source: str = "system",
        ttl_days: Optional[int] = None,
    ) -> bool:
        """Insert or update a core memory entry."""
        now = datetime.utcnow().isoformat() + "Z"
        conn = self._conn()
        try:
            conn.execute(
                """INSERT INTO core_memory
                   (key, category, content, priority, source, ttl_days, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                       content=excluded.content,
                       category=excluded.category,
                       priority=excluded.priority,
                       source=excluded.source,
                       ttl_days=excluded.ttl_days,
                       updated_at=excluded.updated_at""",
                (key, category, content, priority, source, ttl_days, now, now),
            )
            conn.commit()
            # Also embed into semantic store for cross-search
            self.semantic_upsert_text(
                doc_id=f"core_{key}",
                text=f"[CORE MEMORY] [{category}] {content}",
                metadata={"doc_type": "core_memory", "category": category, "key": key},
            )
            return True
        except Exception as e:
            logger.error("[OpenClawDB] Core memory upsert failed: %s", e)
            return False

    def core_memory_get(self, key: str) -> Optional[Dict]:
        """Retrieve a single core memory entry by key."""
        row = self._conn().execute(
            "SELECT * FROM core_memory WHERE key = ?", (key,)
        ).fetchone()
        return dict(row) if row else None

    def core_memory_delete(self, key: str) -> bool:
        """Delete a core memory entry."""
        conn = self._conn()
        conn.execute("DELETE FROM core_memory WHERE key = ?", (key,))
        conn.commit()
        return True

    def core_memory_list(
        self,
        category: Optional[str] = None,
        top_n: int = 50,
    ) -> List[Dict]:
        """Retrieve top-N core memory entries by priority, optionally filtered."""
        conn = self._conn()
        if category:
            rows = conn.execute(
                """SELECT * FROM core_memory WHERE category = ?
                   ORDER BY priority DESC, updated_at DESC LIMIT ?""",
                (category, top_n),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM core_memory
                   ORDER BY priority DESC, updated_at DESC LIMIT ?""",
                (top_n,),
            ).fetchall()
        return [dict(r) for r in rows]

    def core_memory_inject(self, top_n: int = 10) -> str:
        """Build a compact string of top-priority core memories for LLM injection.
        This is the 'always-on' context block that goes into every agent prompt."""
        entries = self.core_memory_list(top_n=top_n)
        if not entries:
            return ""
        lines = ["=== CORE MEMORY (always active) ==="]
        for e in entries:
            lines.append(f"[{e['category'].upper()}] {e['content']}")
        lines.append("=== END CORE MEMORY ===")
        return "\n".join(lines)

    def core_memory_prune_expired(self) -> int:
        """Remove core memory entries past their TTL."""
        conn = self._conn()
        now = datetime.utcnow().isoformat()
        cur = conn.execute(
            """DELETE FROM core_memory
               WHERE ttl_days IS NOT NULL
                 AND datetime(updated_at, '+' || ttl_days || ' days') < ?""",
            (now,),
        )
        conn.commit()
        pruned = cur.rowcount
        if pruned > 0:
            logger.info("[OpenClawDB] Pruned %d expired core memory entries", pruned)
        return pruned

    def core_memory_consolidate(self, lessons: List[Dict]) -> int:
        """Batch-write lessons learned (from post-market review or LLM analysis).
        Each lesson: {key, content, category, priority, source, ttl_days}."""
        count = 0
        for lesson in lessons:
            ok = self.core_memory_upsert(
                key=lesson.get("key", f"lesson_{datetime.utcnow().timestamp()}"),
                content=lesson["content"],
                category=lesson.get("category", "lessons"),
                priority=lesson.get("priority", 60),
                source=lesson.get("source", "llm"),
                ttl_days=lesson.get("ttl_days", 90),
            )
            if ok:
                count += 1
        self.core_memory_prune_expired()
        logger.info("[OpenClawDB] Consolidated %d/%d lessons into core memory", count, len(lessons))
        return count

    def core_memory_health(self) -> Dict:
        """Return core memory health metrics."""
        conn = self._conn()
        total = conn.execute("SELECT COUNT(*) FROM core_memory").fetchone()[0]
        by_cat = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM core_memory GROUP BY category"
        ).fetchall()
        return {
            "total_entries": total,
            "by_category": {r["category"]: r["cnt"] for r in by_cat},
        }

    # ================================================================== #
    #  PHASE 3: GRAPHRAG — Neo4j + SQLite fallback                       #
    # ================================================================== #

    def _init_neo4j(self):
        """Initialize Neo4j connection if configured."""
        if not HAS_NEO4J:
            return
        import os
        uri = os.getenv("NEO4J_URI", "")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        if not uri or not password:
            logger.info("[OpenClawDB] NEO4J_URI/NEO4J_PASSWORD not set — GraphRAG uses SQLite fallback")
            return
        try:
            self._neo4j_driver = Neo4jDriver.driver(uri, auth=(user, password))
            self._neo4j_driver.verify_connectivity()
            self._neo4j_ensure_constraints()
            logger.info("[OpenClawDB] Neo4j GraphRAG connected: %s", uri)
        except Exception as e:
            logger.warning("[OpenClawDB] Neo4j connection failed: %s — using SQLite fallback", e)
            self._neo4j_driver = None

    def _neo4j_ensure_constraints(self):
        """Create Neo4j indexes/constraints for the trading graph."""
        if not self._neo4j_driver:
            return
        with self._neo4j_driver.session() as session:
            for q in [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Ticker) REQUIRE t.symbol IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Signal) REQUIRE s.signal_id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Regime) REQUIRE r.state IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (src:Source) REQUIRE src.name IS UNIQUE",
                "CREATE INDEX IF NOT EXISTS FOR (s:Signal) ON (s.score)",
                "CREATE INDEX IF NOT EXISTS FOR (s:Signal) ON (s.received_at)",
            ]:
                try:
                    session.run(q)
                except Exception:
                    pass

    def _neo4j_run(self, cypher: str, params: Dict = None):
        """Execute a Cypher statement (fire-and-forget for writes)."""
        if not self._neo4j_driver:
            return None
        try:
            with self._neo4j_driver.session() as session:
                result = session.run(cypher, params or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning("[OpenClawDB] Neo4j query failed: %s", e)
            return None

    def graph_upsert_signal(
        self, signal_db_id: int, signal: Dict, regime: Optional[Dict] = None
    ) -> bool:
        """Write signal as graph nodes + edges.
        Creates: (:Source)-[:GENERATED]->(:Signal)-[:ON]->(:Ticker)
                 (:Signal)-[:DURING]->(:Regime)
        Falls back to SQLite graph_edges if Neo4j is offline."""
        sym = signal.get("symbol", "?").upper()
        direction = signal.get("direction", "?")
        score = float(signal.get("score", 0))
        source_name = signal.get("_source", "openclaw_bridge")
        regime_state = "UNKNOWN"
        if regime:
            regime_state = regime.get("state", "UNKNOWN")
        elif isinstance(signal.get("_regime"), dict):
            regime_state = signal["_regime"].get("state", "UNKNOWN")
        now = datetime.utcnow().isoformat() + "Z"

        if self._neo4j_driver:
            # Neo4j path
            cypher = """
            MERGE (t:Ticker {symbol: $symbol})
            MERGE (src:Source {name: $source})
            MERGE (r:Regime {state: $regime})
            CREATE (s:Signal {
                signal_id: $sig_id, score: $score,
                direction: $direction, received_at: $ts
            })
            CREATE (src)-[:GENERATED]->(s)
            CREATE (s)-[:ON]->(t)
            CREATE (s)-[:DURING]->(r)
            """
            self._neo4j_run(cypher, {
                "symbol": sym, "source": source_name, "regime": regime_state,
                "sig_id": signal_db_id, "score": score,
                "direction": direction, "ts": now,
            })
            return True
        else:
            # SQLite fallback
            conn = self._conn()
            edges = [
                (f"source:{source_name}", f"signal:{signal_db_id}", "GENERATED", score, json.dumps({"symbol": sym}), now),
                (f"signal:{signal_db_id}", f"ticker:{sym}", "ON", 1.0, json.dumps({"direction": direction}), now),
                (f"signal:{signal_db_id}", f"regime:{regime_state}", "DURING", 1.0, "{}", now),
            ]
            conn.executemany(
                """INSERT INTO graph_edges (from_node, to_node, edge_type, weight, meta_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                edges,
            )
            conn.commit()
            return True

    def graph_add_correlation(
        self, ticker_a: str, ticker_b: str, correlation: float,
        edge_type: str = "CORRELATED_WITH", metadata: Optional[Dict] = None,
    ) -> bool:
        """Add a correlation edge between two tickers."""
        now = datetime.utcnow().isoformat() + "Z"
        if self._neo4j_driver:
            cypher = """
            MERGE (a:Ticker {symbol: $sym_a})
            MERGE (b:Ticker {symbol: $sym_b})
            MERGE (a)-[r:CORRELATED_WITH]->(b)
            SET r.weight = $weight, r.updated_at = $ts
            """
            self._neo4j_run(cypher, {
                "sym_a": ticker_a.upper(), "sym_b": ticker_b.upper(),
                "weight": correlation, "ts": now,
            })
            return True
        else:
            conn = self._conn()
            conn.execute(
                """INSERT INTO graph_edges (from_node, to_node, edge_type, weight, meta_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (f"ticker:{ticker_a.upper()}", f"ticker:{ticker_b.upper()}",
                 edge_type, correlation, json.dumps(metadata or {}), now),
            )
            conn.commit()
            return True

    def graph_add_catalyst(
        self, ticker: str, headline: str, catalyst_type: str = "news",
    ) -> bool:
        """Add a catalyst event node linked to a ticker."""
        now = datetime.utcnow().isoformat() + "Z"
        cat_id = hashlib.md5(f"{ticker}:{headline}:{now}".encode()).hexdigest()[:12]
        if self._neo4j_driver:
            cypher = """
            MERGE (t:Ticker {symbol: $symbol})
            CREATE (c:Catalyst {id: $cat_id, headline: $headline, type: $ctype, ts: $ts})
            CREATE (t)-[:HAS_CATALYST]->(c)
            """
            self._neo4j_run(cypher, {
                "symbol": ticker.upper(), "cat_id": cat_id,
                "headline": headline[:500], "ctype": catalyst_type, "ts": now,
            })
        else:
            conn = self._conn()
            conn.execute(
                """INSERT INTO graph_edges (from_node, to_node, edge_type, weight, meta_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (f"ticker:{ticker.upper()}", f"catalyst:{cat_id}",
                 "HAS_CATALYST", 1.0, json.dumps({"headline": headline[:500], "type": catalyst_type}), now),
            )
            conn.commit()
        # Also embed the catalyst into semantic store
        self.semantic_upsert_text(
            doc_id=f"catalyst_{cat_id}",
            text=f"{ticker.upper()} catalyst ({catalyst_type}): {headline}",
            metadata={"doc_type": "catalyst", "symbol": ticker.upper(), "catalyst_type": catalyst_type},
        )
        return True

    def graph_neighborhood(
        self, ticker: str, depth: int = 2, limit: int = 50,
    ) -> Dict:
        """Retrieve the graph neighborhood around a ticker."""
        ticker = ticker.upper()
        if self._neo4j_driver:
            cypher = """
            MATCH path = (t:Ticker {symbol: $symbol})-[*1..$depth]-(connected)
            WITH DISTINCT connected, relationships(path) AS rels
            UNWIND rels AS r
            WITH DISTINCT
                startNode(r) AS from_n, endNode(r) AS to_n, type(r) AS rel_type,
                properties(r) AS rel_props, connected
            RETURN
                labels(from_n)[0] AS from_label,
                COALESCE(from_n.symbol, from_n.signal_id, from_n.name, from_n.state, from_n.id, from_n.headline) AS from_id,
                labels(to_n)[0] AS to_label,
                COALESCE(to_n.symbol, to_n.signal_id, to_n.name, to_n.state, to_n.id, to_n.headline) AS to_id,
                rel_type, rel_props
            LIMIT $limit
            """
            records = self._neo4j_run(cypher, {"symbol": ticker, "depth": depth, "limit": limit})
            if records is None:
                records = []
            nodes = set()
            edges = []
            for r in records:
                fn = f"{r.get('from_label', '?')}:{r.get('from_id', '?')}"
                tn = f"{r.get('to_label', '?')}:{r.get('to_id', '?')}"
                nodes.add(fn)
                nodes.add(tn)
                edges.append({
                    "from": fn, "to": tn,
                    "type": r.get("rel_type", ""),
                    "props": dict(r.get("rel_props", {})),
                })
            return {"ticker": ticker, "nodes": list(nodes), "edges": edges}
        else:
            # SQLite fallback
            conn = self._conn()
            node_key = f"ticker:{ticker}"
            visited = {node_key}
            frontier = {node_key}
            all_edges = []
            for _ in range(depth):
                if not frontier:
                    break
                placeholders = ",".join("?" * len(frontier))
                rows = conn.execute(
                    f"""SELECT * FROM graph_edges
                        WHERE from_node IN ({placeholders}) OR to_node IN ({placeholders})
                        LIMIT ?""",
                    list(frontier) + list(frontier) + [limit],
                ).fetchall()
                next_frontier = set()
                for r in rows:
                    all_edges.append({
                        "from": r["from_node"], "to": r["to_node"],
                        "type": r["edge_type"], "weight": r["weight"],
                    })
                    for n in (r["from_node"], r["to_node"]):
                        if n not in visited:
                            visited.add(n)
                            next_frontier.add(n)
                frontier = next_frontier
            return {"ticker": ticker, "nodes": list(visited), "edges": all_edges}

    def graph_query_natural(self, question: str, ticker: Optional[str] = None) -> Dict:
        """Answer a natural-language question using graph facts + semantic context.
        Returns both graph neighborhood and semantic search results."""
        graph_facts = {}
        if ticker:
            graph_facts = self.graph_neighborhood(ticker, depth=2)

        semantic_hits = self.semantic_search(
            query=question, k=5, symbol=ticker
        )

        return {
            "question": question,
            "graph": graph_facts,
            "semantic_context": semantic_hits,
        }

    def graph_health(self) -> Dict:
        """Return graph store health metrics."""
        conn = self._conn()
        sqlite_edges = conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
        return {
            "neo4j": "connected" if self._neo4j_driver else "disabled",
            "sqlite_fallback_edges": sqlite_edges,
        }

    # ================================================================== #
    #  COMBINED HEALTH CHECK                                              #
    # ================================================================== #
    def get_intelligence_health(self) -> Dict:
        """Full health check across all 3 memory intelligence layers."""
        return {
            "semantic_rag": self.semantic_health(),
            "core_memory": self.core_memory_health(),
            "graph_rag": self.graph_health(),
        }

    # ================================================================== #
    #  ORIGINAL METHODS (unchanged)                                       #
    # ================================================================== #

    # -- writes -----------------------------------------------------------
    def insert_ingest(
        self,
        *,
        run_id: str,
        timestamp: str,
        regime: Optional[Dict] = None,
        universe: Optional[Dict] = None,
        signal_count: int = 0,
        payload_hash: Optional[str] = None,
    ) -> int:
        """Insert an ingest header row. Returns the new row id."""
        now = datetime.utcnow().isoformat() + "Z"
        conn = self._conn()
        cur = conn.execute(
            """INSERT INTO openclaw_ingests
               (run_id, received_at, timestamp,
                regime_state, regime_confidence, regime_source,
                universe_json, signal_count, payload_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, now, timestamp,
                regime.get("state") if regime else None,
                regime.get("confidence") if regime else None,
                regime.get("source") if regime else None,
                json.dumps(universe) if universe else None,
                signal_count, payload_hash,
            ),
        )
        conn.commit()
        return cur.lastrowid

    def insert_signals(self, ingest_id: int, run_id: str, signals: List[Dict[str, Any]]) -> int:
        """Bulk-insert signal rows for one ingest. Returns count.
        ENHANCED: Also upserts into semantic store + graph."""
        now = datetime.utcnow().isoformat() + "Z"
        conn = self._conn()
        rows = [
            (
                ingest_id, run_id, s["symbol"], s["direction"], s["score"],
                json.dumps(s.get("subscores")) if s.get("subscores") else None,
                s.get("entry"), s.get("stop"), s.get("target"),
                s.get("timeframe"),
                json.dumps(s.get("reasons")) if s.get("reasons") else None,
                json.dumps(s.get("raw")) if s.get("raw") else None,
                now,
            )
            for s in signals
        ]
        conn.executemany(
            """INSERT INTO openclaw_signals
               (ingest_id, run_id, symbol, direction, score,
                subscores_json, entry, stop, target, timeframe,
                reasons_json, raw_json, received_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()

        # --- PHASE 1+3 HOOK: Embed signals + write to graph ---
        # Fetch the inserted IDs (last N)
        inserted = conn.execute(
            """SELECT id, symbol, direction, score, subscores_json,
                      entry, stop, target, timeframe, reasons_json, received_at
               FROM openclaw_signals
               WHERE ingest_id = ? ORDER BY id""",
            (ingest_id,),
        ).fetchall()

        # Get regime from ingest
        ingest_row = conn.execute(
            "SELECT regime_state FROM openclaw_ingests WHERE id = ?", (ingest_id,)
        ).fetchone()
        regime = {"state": ingest_row["regime_state"]} if ingest_row and ingest_row["regime_state"] else None

        for row in inserted:
            sig_dict = dict(row)
            # Phase 1: Semantic upsert
            self.semantic_upsert_signal(row["id"], sig_dict, regime)
            # Phase 3: Graph upsert
            self.graph_upsert_signal(row["id"], sig_dict, regime)

        return len(rows)

    # -- reads (all original, unchanged) ----------------------------------
    def get_latest_ingest(self) -> Optional[Dict]:
        row = self._conn().execute("SELECT * FROM openclaw_ingests ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def get_signals_for_ingest(self, ingest_id: int) -> List[Dict]:
        rows = self._conn().execute(
            "SELECT * FROM openclaw_signals WHERE ingest_id = ? ORDER BY score DESC",
            (ingest_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_latest_signals(self, limit: int = 50) -> List[Dict]:
        rows = self._conn().execute(
            """SELECT s.*, i.regime_state, i.regime_confidence
               FROM openclaw_signals s
               JOIN openclaw_ingests i ON s.ingest_id = i.id
               ORDER BY s.received_at DESC, s.score DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_signals_by_symbol(self, symbol: str, limit: int = 20) -> List[Dict]:
        rows = self._conn().execute(
            """SELECT s.*, i.regime_state, i.regime_confidence
               FROM openclaw_signals s
               JOIN openclaw_ingests i ON s.ingest_id = i.id
               WHERE s.symbol = ?
               ORDER BY s.received_at DESC LIMIT ?""",
            (symbol.upper(), limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_ingest_history(self, limit: int = 20) -> List[Dict]:
        rows = self._conn().execute(
            """SELECT id, run_id, received_at, timestamp,
                      regime_state, regime_confidence, signal_count
               FROM openclaw_ingests ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def count_signals(self, since: Optional[str] = None) -> int:
        if since:
            row = self._conn().execute(
                "SELECT COUNT(*) FROM openclaw_signals WHERE received_at >= ?", (since,),
            ).fetchone()
        else:
            row = self._conn().execute("SELECT COUNT(*) FROM openclaw_signals").fetchone()
        return row[0] if row else 0

    def get_signals_for_training(self, window_days: int = 252) -> List[Dict]:
        since = (datetime.utcnow() - timedelta(days=int(window_days))).isoformat()
        rows = self._conn().execute(
            """SELECT score, entry, stop, target, direction, received_at
               FROM openclaw_signals WHERE received_at >= ?
               ORDER BY received_at ASC""",
            (since,),
        ).fetchall()
        return [dict(r) for r in rows]


# -- global instance (matches database.py pattern) -----------------------
openclaw_db = OpenClawDBService()
