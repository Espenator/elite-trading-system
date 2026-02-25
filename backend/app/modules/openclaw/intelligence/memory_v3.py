#!/usr/bin/env python3
"""
memory_v3.py - Enhanced Agent Memory System for OpenClaw v3.0

SQLite + ChromaDB Hybrid with Causal Graph, Vector Similarity, and Alpha Decay.

Key capabilities:
  - SQLite persistent storage (WAL mode for concurrent reads)
  - ChromaDB vector store for embedding-based trade similarity search
  - Causal graph: tracks signal→trade→outcome chains with NetworkX
  - Alpha decay: recent trades weighted exponentially (half-life configurable)
  - Hybrid retrieval: structured SQL queries + semantic vector search
  - Blackboard integration: subscribes to trade_outcomes, publishes memory_updates
  - Regime-partitioned stats: separate win rates per GREEN/YELLOW/RED
  - Expectancy tracking per source, setup, agent, regime, score-bin
  - Backward compatible: imports as drop-in for memory.py v2.0 callers
  - Local Ollama LLM integration for trade pattern analysis
  - MACRO BRAIN: Neuromorphic oscillator + regime-spawned teams (v3.1+)

Usage:
    from memory_v3 import trade_memory
    trade_memory.record_signal('AAPL', 'finviz', 'momentum', score=82, regime='GREEN')
    trade_memory.record_outcome('AAPL', 'finviz', won=True, pnl_pct=3.2)
    weights = trade_memory.get_source_weights()
    similar = trade_memory.find_similar_trades('AAPL', score=80, regime='GREEN')
    graph = trade_memory.get_causal_chain('AAPL')

    # NEW: Macro Brain (v3.1)
    trade_memory.macro_brain.update_oscillator(25.0)  # Fear = 25/100
    print(trade_memory.macro_brain.to_dict())
    # Output: {'oscillator': 25.0, 'wave_state': 'EXTREME_FEAR', 'contrarian_bias': 1.5, ...}
"""

import os
import sys
import json
import math
import sqlite3
import logging
import hashlib
import asyncio
import argparse
import threading
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, field, asdict

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

try:
    from streaming_engine import get_blackboard, BlackboardMessage, Topic
    HAS_BLACKBOARD = True
except ImportError:
    HAS_BLACKBOARD = False

try:
    from llm_client import get_llm
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

logger = logging.getLogger(__name__)

# ========== CONFIGURATION ==========
DATA_DIR = Path(__file__).parent / 'data'
DB_FILE = DATA_DIR / 'openclaw_memory_v3.db'
CHROMA_DIR = DATA_DIR / 'chroma_store'
LEGACY_JSON = Path(__file__).parent / 'openclaw_memory.json'

# Flywheel tuning
DEFAULT_WEIGHTS = {
    'finviz': 20, 'uw': 25, 'discord': 15,
    'chart': 20, 'regime': 10, 'sentiment': 10,
}
MIN_TRADES_TO_ADJUST = 5
ALPHA_DECAY_HALF_LIFE_DAYS = 30
AGENT_MIN_TRADES = 5
AGENT_PRUNE_WR = 0.30
AGENT_PROMOTE_WR = 0.65
AGENT_PROMOTE_MIN = 10
BLACKLIST_CONSECUTIVE = 3
BLACKLIST_COOLDOWN_DAYS = 7
STALE_DAYS = 90

# ChromaDB vector dimensions
# Feature vector: [score_norm, regime_enc, source_enc(6), setup_enc(5), pnl_norm, hold_norm, vol_norm, decay_weight]
EMBEDDING_DIM = 17

# Source and setup encodings for feature vectors
SOURCE_INDEX = {'finviz': 0, 'uw': 1, 'discord': 2, 'chart': 3, 'sentiment': 4, 'legacy': 5}
SETUP_INDEX = {'momentum': 0, 'pullback': 1, 'mean_reversion': 2, 'breakout': 3, 'unknown': 4}
REGIME_MAP = {'GREEN': 1.0, 'YELLOW': 0.5, 'RED': 0.0, 'UNKNOWN': 0.25}

# ========== MACRO BRAIN CONFIG ==========
OSCILLATOR_THRESHOLDS = {
    'extreme_fear': (0, 25),
    'fear': (25, 40),
    'neutral': (40, 60),
    'greed': (60, 75),
    'extreme_greed': (75, 100),
}

WAVE_STATE_MAP = {
    'EXTREME_FEAR': 1.5,      # Contrarian long bias
    'FEAR': 1.2,
    'NEUTRAL': 1.0,
    'GREED': 0.8,
    'EXTREME_GREED': 0.5,      # Contrarian short bias
}

TEAM_SPAWNING_CONFIG = {
    'EXTREME_FEAR': {'team': 'bounce_hunters', 'count': 5, 'agents': ['rebound_detector', 'pullback_detector']},
    'FEAR': {'team': 'defensive_swings', 'count': 3, 'agents': ['technical_checker', 'mtf_alignment']},
    'NEUTRAL': {'team': 'core_momentum', 'count': 42, 'agents': ['ensemble_scorer', 'composite_scorer']},  # All agents
    'GREED': {'team': 'caution_momentum', 'count': 3, 'agents': ['risk_governor', 'position_sizer']},
    'EXTREME_GREED': {'team': 'fade_climbers', 'count': 5, 'agents': ['short_detector', 'whale_flow']},
}

# ========== SQLITE SCHEMA ==========
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    source TEXT NOT NULL,
    setup TEXT DEFAULT 'unknown',
    score REAL DEFAULT 0,
    regime TEXT DEFAULT 'UNKNOWN',
    entry_price REAL DEFAULT 0,
    timestamp TEXT NOT NULL,
    date_key TEXT NOT NULL,
    embedding_json TEXT DEFAULT NULL,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER REFERENCES signals(id),
    ticker TEXT NOT NULL,
    source TEXT NOT NULL,
    setup TEXT DEFAULT 'unknown',
    regime TEXT DEFAULT 'UNKNOWN',
    won INTEGER NOT NULL,
    pnl_pct REAL DEFAULT 0,
    exit_price REAL DEFAULT 0,
    hold_minutes INTEGER DEFAULT 0,
    timestamp TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    setup TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    signals INTEGER DEFAULT 0,
    outcomes INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    total_pnl_pct REAL DEFAULT 0,
    promotion_count INTEGER DEFAULT 0,
    prune_count INTEGER DEFAULT 0,
    created TEXT NOT NULL,
    last_outcome TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS blacklist (
    ticker TEXT PRIMARY KEY,
    reason TEXT DEFAULT 'consecutive_losses',
    expiry TEXT NOT NULL,
    created TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS weights (
    source TEXT PRIMARY KEY,
    weight REAL NOT NULL,
    default_weight REAL NOT NULL,
    last_updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS causal_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_node TEXT NOT NULL,
    to_node TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    metadata_json TEXT DEFAULT '{}',
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expectancy_cache (
    cache_key TEXT PRIMARY KEY,
    expectancy REAL DEFAULT 0,
    sample_size INTEGER DEFAULT 0,
    decay_weighted_wr REAL DEFAULT 0.5,
    avg_win REAL DEFAULT 0,
    avg_loss REAL DEFAULT 0,
    last_updated TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date_key);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_regime ON signals(regime);

CREATE TABLE IF NOT EXISTS semantic_rules (
    rule_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    setup TEXT NOT NULL,
    regime TEXT NOT NULL,
    rule_text TEXT NOT NULL,
    win_rate REAL,
    sample_size INTEGER,
    last_updated TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signals_score ON signals(score);
CREATE INDEX IF NOT EXISTS idx_outcomes_ticker ON outcomes(ticker);
CREATE INDEX IF NOT EXISTS idx_outcomes_signal ON outcomes(signal_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_source ON outcomes(source);
CREATE INDEX IF NOT EXISTS idx_outcomes_regime ON outcomes(regime);
CREATE INDEX IF NOT EXISTS idx_causal_from ON causal_edges(from_node);
CREATE INDEX IF NOT EXISTS idx_causal_to ON causal_edges(to_node);
"""


@dataclass
class TradeSignalRecord:
    ticker: str
    source: str
    setup: str = 'unknown'
    score: float = 0
    regime: str = 'UNKNOWN'
    entry_price: float = 0
    timestamp: str = ''
    signal_id: int = 0


@dataclass
class TradeOutcomeRecord:
    ticker: str
    source: str
    setup: str = 'unknown'
    regime: str = 'UNKNOWN'
    won: bool = False
    pnl_pct: float = 0
    exit_price: float = 0
    hold_minutes: int = 0
    signal_id: int = 0


@dataclass
class MacroEpisode:
    """Records a macro brain learning episode (wave cycle → outcome)."""
    episode_id: str
    wave_state: str
    oscillator_value: float
    signals_generated: int
    winning_signals: int
    total_pnl: float
    timestamp: str = ''
    lesson: str = ''
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MacroBrainState:
    """
    Neuromorphic market regime oscillator + team spawning intelligence.
    
    Central blackboard state machine:
    - Oscillator (0-100): fear←→greed axis
    - Wave state: EXTREME_FEAR, FEAR, NEUTRAL, GREED, EXTREME_GREED
    - Contrarian bias: multiply signal scores based on fear/greed extremes
    - Active teams: spawned sub-swarms for regime-specific strategies
    - Episodes: learning memory (wave_state → outcome → lesson)
    
    Thread-safe: all updates protected by RWLock.
    """
    
    def __init__(self):
        self.oscillator = 50.0  # Start neutral
        self.wave_state = 'NEUTRAL'
        self.contrarian_bias = 1.0
        self.confidence = 0.5
        self.active_teams: Dict[str, Dict] = {}  # team_name → {agents, spawn_time, signal_count}
        self.episodes: List[MacroEpisode] = []
        self.last_update = datetime.now().isoformat()
        self._lock = threading.RLock()
        logger.info('[MacroBrainState] Initialized at NEUTRAL oscillator=50.0')
    
    def update_oscillator(self, value: float, confidence: float = 0.5):
        """
        Update fear/greed oscillator (0-100 scale).
        Triggers wave_state transition and team spawning.
        
        Args:
            value: 0=Extreme Fear, 50=Neutral, 100=Extreme Greed
            confidence: 0-1 confidence in the reading
        """
        with self._lock:
            old_state = self.wave_state
            self.oscillator = max(0.0, min(100.0, value))
            self.confidence = max(0.0, min(1.0, confidence))
            self.last_update = datetime.now().isoformat()
            
            # Determine new wave state from oscillator thresholds
            new_state = 'NEUTRAL'
            for state_name, (lo, hi) in OSCILLATOR_THRESHOLDS.items():
                if lo <= self.oscillator < hi:
                    new_state = state_name.upper()
                    break
            
            self.wave_state = new_state
            self.contrarian_bias = WAVE_STATE_MAP.get(new_state, 1.0)
            
            if old_state != new_state:
                logger.info(f'[MacroBrainState] Wave transition: {old_state} → {new_state} "
                            f"(osc={self.oscillator:.1f}, bias={self.contrarian_bias:.2f})")
                # Spawn regime-specific teams
                self._spawn_teams_for_wave(new_state)
            
            return {'old_state': old_state, 'new_state': new_state, 'oscillator': self.oscillator}
    
    def _spawn_teams_for_wave(self, wave_state: str):
        """
        Auto-spawn regime-tuned agent teams based on wave state.
        Example: EXTREME_FEAR → spawn 'bounce_hunters' team (5 agents).
        """
        config = TEAM_SPAWNING_CONFIG.get(wave_state)
        if not config:
            return
        
        team_name = config['team']
        team_count = config['count']
        agents = config['agents']
        
        # Kill old team if exists
        if team_name in self.active_teams:
            old = self.active_teams[team_name]
            logger.info(f"[MacroBrainState] Killing old {team_name} team (active {old['signal_count']} signals)")
            del self.active_teams[team_name]
        
        # Spawn new team
        self.active_teams[team_name] = {
            'wave_state': wave_state,
            'agents': agents,
            'spawn_time': self.last_update,
            'signal_count': 0,
            'max_agents': team_count,
        }
        logger.info(f"[MacroBrainState] Spawned {team_name} team (up to {team_count} agents) for {wave_state}")
    
    def record_signal(self, ticker: str, score: float):
        """Called when a signal is generated; tracks active team activity."""
        with self._lock:
            for team_name, team_info in self.active_teams.items():
                team_info['signal_count'] = team_info.get('signal_count', 0) + 1
    
    def record_episode(self, winning_signals: int, total_pnl: float, lesson: str = ''):
        """
        Record a macro brain learning episode.
        Used to build episodic memory of what works in which wave states.
        """
        with self._lock:
            episode_id = f"{self.wave_state}_{datetime.now().timestamp()}"
            ep = MacroEpisode(
                episode_id=episode_id,
                wave_state=self.wave_state,
                oscillator_value=self.oscillator,
                signals_generated=sum(t.get('signal_count', 0) for t in self.active_teams.values()),
                winning_signals=winning_signals,
                total_pnl=total_pnl,
                lesson=lesson,
            )
            self.episodes.append(ep)
            if len(self.episodes) > 100:  # Keep last 100 episodes
                self.episodes.pop(0)
            logger.info(f"[MacroBrainState] Episode recorded: {ep.wave_state} "
                       f"won={winning_signals} pnl={total_pnl:+.2f}% lesson='{lesson[:40]}'")
            return episode_id
    
    def get_active_teams(self) -> Dict[str, Dict]:
        """Return copy of active teams."""
        with self._lock:
            return {k: v.copy() for k, v in self.active_teams.items()}
    
    def kill_team(self, team_name: str) -> bool:
        """Manually kill a team."""
        with self._lock:
            if team_name in self.active_teams:
                del self.active_teams[team_name]
                logger.info(f"[MacroBrainState] Killed team: {team_name}")
                return True
            return False
    
    def to_dict(self) -> Dict:
        """Serialize state for API responses."""
        with self._lock:
            return {
                'oscillator': round(self.oscillator, 2),
                'wave_state': self.wave_state,
                'contrarian_bias': round(self.contrarian_bias, 2),
                'confidence': round(self.confidence, 2),
                'active_teams': {k: v.copy() for k, v in self.active_teams.items()},
                'recent_episodes': [asdict(e) for e in self.episodes[-5:]],  # Last 5
                'last_update': self.last_update,
            }


# ================================================================== #
# FEATURE VECTOR ENCODER                                               #
# ================================================================== #

def encode_trade_vector(score: float = 0, regime: str = 'UNKNOWN',
                        source: str = 'unknown', setup: str = 'unknown',
                        pnl_pct: float = 0, hold_minutes: int = 0,
                        volume_ratio: float = 1.0, days_ago: float = 0) -> List[float]:
    """
    Encode a trade into a fixed-length feature vector for ChromaDB.
    17 dimensions: score(1) + regime(1) + source_onehot(6) + setup_onehot(5) +
                   pnl(1) + hold(1) + volume(1) + decay(1)
    """
    vec = []
    # 1. Normalized score [0, 1]
    vec.append(min(1.0, max(0.0, score / 100.0)))

    # 2. Regime encoding
    vec.append(REGIME_MAP.get(regime.upper(), 0.25))

    # 3. Source one-hot (6 dims)
    src_vec = [0.0] * 6
    idx = SOURCE_INDEX.get(source.lower(), 5)
    src_vec[idx] = 1.0
    vec.extend(src_vec)

    # 4. Setup one-hot (5 dims)
    setup_vec = [0.0] * 5
    idx = SETUP_INDEX.get(setup.lower(), 4)
    setup_vec[idx] = 1.0
    vec.extend(setup_vec)

    # 5. Normalized PnL [-1, 1] (clamped at ±20%)
    vec.append(max(-1.0, min(1.0, pnl_pct / 20.0)))

    # 6. Normalized hold time [0, 1] (capped at 8 hours = 480 min)
    vec.append(min(1.0, hold_minutes / 480.0))

    # 7. Volume ratio [0, 1] (capped at 5x)
    vec.append(min(1.0, volume_ratio / 5.0))

    # 8. Decay weight
    if days_ago <= 0:
        decay = 1.0
    else:
        decay = math.exp(-0.693 * days_ago / ALPHA_DECAY_HALF_LIFE_DAYS)
    vec.append(decay)

    return vec


# ================================================================== #
# MEMORY V3 — HYBRID ENGINE                                            #
# ================================================================== #

class MemoryV3:
    """
    Enhanced persistent memory: SQLite + ChromaDB hybrid.
    - SQLite: structured storage, weight flywheel, agent evaluation
    - ChromaDB: vector embeddings for semantic trade similarity
    - NetworkX: causal graph for signal→outcome chain tracking
    - Alpha decay: exponential recency weighting across all analytics
    - MACRO BRAIN: Neuromorphic oscillator + regime-spawned teams (NEW)

    Drop-in replacement for TradeMemory (memory.py v2.0).
    Integrates with Blackboard pub/sub for real-time outcome ingestion.
    """

    def __init__(self, db_path: Path = DB_FILE, chroma_path: Path = CHROMA_DIR):
        self.db_path = db_path
        self.chroma_path = chroma_path
        self._signals_today: List[str] = []
        self._last_reset = ''
        self._graph = nx.DiGraph() if HAS_NETWORKX else None
        self._chroma_collection = None
        
        # NEW: Macro Brain state machine
        self.macro_brain = MacroBrainState()

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._init_weights()
        self._init_chromadb()
        self._migrate_legacy()
        self._load_graph()
        logger.info(f"[MemoryV3] Initialized: SQLite={self.db_path} "
                    f"ChromaDB={'active' if self._chroma_collection else 'disabled'} "
                    f"CausalGraph={'active' if self._graph is not None else 'disabled'} "
                    f"MacroBrain=active")

    # ------------------------------------------------------------------ #
    # DATABASE INIT                                                        #
    # ------------------------------------------------------------------ #

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=5000')
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()

    def _init_weights(self):
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            for src, w in DEFAULT_WEIGHTS.items():
                conn.execute(
                    'INSERT OR IGNORE INTO weights (source, weight, default_weight, last_updated) '
                    'VALUES (?, ?, ?, ?)', (src, w, w, now)
                )
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # CHROMADB INIT                                                        #
    # ------------------------------------------------------------------ #

    def _init_chromadb(self):
        if not HAS_CHROMADB:
            logger.info("[MemoryV3] ChromaDB not installed — vector search disabled")
            return
        try:
            self.chroma_path.mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=str(self.chroma_path),
            )
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name="openclaw_trades",
                metadata={
                    "hnsw:space": "cosine",
                    "description": "OpenClaw trade signal and outcome embeddings",
                },
            )
            count = self._chroma_collection.count()
            logger.info(f"[MemoryV3] ChromaDB initialized: {count} vectors in collection")
        except Exception as e:
            logger.error(f"[MemoryV3] ChromaDB init failed: {e}")
            self._chroma_collection = None

    def _upsert_vector(self, doc_id: str, embedding: List[float],
                       metadata: Dict, document: str = ""):
        """Upsert a single trade vector into ChromaDB."""
        if not self._chroma_collection:
            return
        try:
            self._chroma_collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[document],
            )
        except Exception as e:
            logger.warning(f"[MemoryV3] ChromaDB upsert failed for {doc_id}: {e}")

    def _query_vectors(self, query_embedding: List[float], n_results: int = 10,
                       where: Dict = None, where_document: Dict = None) -> List[Dict]:
        """Query ChromaDB for similar trade vectors."""
        if not self._chroma_collection:
            return []
        try:
            kwargs = {
                'query_embeddings': [query_embedding],
                'n_results': min(n_results, self._chroma_collection.count() or 1),
            }
            if where:
                kwargs['where'] = where
            if where_document:
                kwargs['where_document'] = where_document
            results = self._chroma_collection.query(**kwargs)
            hits = []
            if results and results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    hit = {
                        'id': doc_id,
                        'distance': results['distances'][0][i] if results.get('distances') else 0,
                        'similarity': 1.0 - (results['distances'][0][i] if results.get('distances') else 0),
                        'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                        'document': results['documents'][0][i] if results.get('documents') else '',
                    }
                    hits.append(hit)
            return hits
        except Exception as e:
            logger.warning(f"[MemoryV3] ChromaDB query failed: {e}")
            return []

    def _backfill_chromadb(self):
        """Backfill ChromaDB from existing SQLite signals+outcomes."""
        if not self._chroma_collection:
            return
        existing_count = self._chroma_collection.count()
        conn = self._get_conn()
        try:
            total_signals = conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
            if existing_count >= total_signals:
                return
            rows = conn.execute(
                'SELECT s.id, s.ticker, s.source, s.setup, s.score, s.regime, '
                's.entry_price, s.timestamp, o.won, o.pnl_pct, o.hold_minutes '
                'FROM signals s LEFT JOIN outcomes o ON o.signal_id = s.id '
                'ORDER BY s.id'
            ).fetchall()
            batch_ids, batch_embs, batch_metas, batch_docs = [], [], [], []
            for r in rows:
                doc_id = f"signal_{r['id']}"
                days_ago = self._days_since(r['timestamp'])
                embedding = encode_trade_vector(
                    score=r['score'] or 0,
                    regime=r['regime'] or 'UNKNOWN',
                    source=r['source'] or 'unknown',
                    setup=r['setup'] or 'unknown',
                    pnl_pct=r['pnl_pct'] or 0,
                    hold_minutes=r['hold_minutes'] or 0,
                    days_ago=days_ago,
                )
                meta = {
                    'ticker': r['ticker'],
                    'source': r['source'],
                    'setup': r['setup'] or 'unknown',
                    'score': float(r['score'] or 0),
                    'regime': r['regime'] or 'UNKNOWN',
                    'won': int(r['won']) if r['won'] is not None else -1,
                    'pnl_pct': float(r['pnl_pct'] or 0),
                    'signal_id': int(r['id']),
                    'timestamp': r['timestamp'],
                }
                doc = (f"{r['ticker']} {r['source']}:{r['setup']} "
                       f"score={r['score']} regime={r['regime']} "
                       f"{'WIN' if r['won'] else 'LOSS' if r['won'] is not None else 'PENDING'}")
                batch_ids.append(doc_id)
                batch_embs.append(embedding)
                batch_metas.append(meta)
                batch_docs.append(doc)
                if len(batch_ids) >= 100:
                    self._chroma_collection.upsert(
                        ids=batch_ids, embeddings=batch_embs,
                        metadatas=batch_metas, documents=batch_docs,
                    )
                    batch_ids, batch_embs, batch_metas, batch_docs = [], [], [], []
            if batch_ids:
                self._chroma_collection.upsert(
                    ids=batch_ids, embeddings=batch_embs,
                    metadatas=batch_metas, documents=batch_docs,
                )
            logger.info(f"[MemoryV3] Backfilled {len(rows)} vectors into ChromaDB")
        except Exception as e:
            logger.warning(f"[MemoryV3] ChromaDB backfill failed: {e}")
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # LEGACY MIGRATION                                                     #
    # ------------------------------------------------------------------ #

    def _migrate_legacy(self):
        if not LEGACY_JSON.exists():
            return
        conn = self._get_conn()
        try:
            existing = conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
            if existing > 0:
                self._backfill_chromadb()
                return
            with open(LEGACY_JSON, 'r') as f:
                old = json.load(f)
            count = 0
            for ticker, stats in old.get('tickers', {}).items():
                for entry in stats.get('scores_at_entry', []):
                    conn.execute(
                        'INSERT INTO signals (ticker, source, setup, score, regime, timestamp, date_key) '
                        'VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (ticker, 'legacy', 'unknown', entry.get('score', 0),
                         entry.get('regime', 'UNKNOWN'),
                         entry.get('date', datetime.now().isoformat()),
                         entry.get('date', date.today().isoformat())[:10])
                    )
                    count += 1
            for agent_id, ag in old.get('agents', {}).items():
                conn.execute(
                    'INSERT OR IGNORE INTO agents '
                    '(agent_id, source, setup, status, signals, outcomes, wins, losses, '
                    'total_pnl_pct, promotion_count, prune_count, created, last_outcome) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (agent_id, ag.get('source', ''), ag.get('setup', ''),
                     ag.get('status', 'active'), ag.get('signals', 0),
                     ag.get('outcomes', 0), ag.get('wins', 0), ag.get('losses', 0),
                     ag.get('total_pnl_pct', 0), ag.get('promotion_count', 0),
                     ag.get('prune_count', 0), ag.get('created', datetime.now().isoformat()),
                     ag.get('last_outcome'))
                )
            conn.commit()
            logger.info(f"[MemoryV3] Migrated {count} legacy signals")
            self._backfill_chromadb()
        except Exception as e:
            logger.warning(f"[MemoryV3] Legacy migration failed: {e}")
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # ALPHA DECAY                                                          #
    # ------------------------------------------------------------------ #

    def _decay_weight(self, days_ago: float) -> float:
        if days_ago <= 0:
            return 1.0
        return math.exp(-0.693 * days_ago / ALPHA_DECAY_HALF_LIFE_DAYS)

    def _days_since(self, ts_str: str) -> float:
        try:
            ts = datetime.fromisoformat(ts_str)
            return (datetime.now() - ts).total_seconds() / 86400
        except Exception:
            return 999

    # ------------------------------------------------------------------ #
    # CAUSAL GRAPH                                                         #
    # ------------------------------------------------------------------ #

    def _load_graph(self):
        if not self._graph:
            return
        conn = self._get_conn()
        try:
            rows = conn.execute('SELECT * FROM causal_edges ORDER BY id').fetchall()
            for r in rows:
                meta = json.loads(r['metadata_json'] or '{}')
                self._graph.add_edge(
                    r['from_node'], r['to_node'],
                    edge_type=r['edge_type'], weight=r['weight'],
                    timestamp=r['timestamp'], **meta
                )
            logger.info(f"[MemoryV3] Loaded causal graph: {self._graph.number_of_nodes()} nodes, "
                        f"{self._graph.number_of_edges()} edges")
        finally:
            conn.close()

    def _add_causal_edge(self, from_node: str, to_node: str,
                         edge_type: str, weight: float = 1.0,
                         metadata: Dict = None):
        now = datetime.now().isoformat()
        meta_json = json.dumps(metadata or {})
        conn = self._get_conn()
        try:
            conn.execute(
                'INSERT INTO causal_edges (from_node, to_node, edge_type, weight, metadata_json, timestamp) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (from_node, to_node, edge_type, weight, meta_json, now)
            )
            conn.commit()
        finally:
            conn.close()
        if self._graph:
            self._graph.add_edge(from_node, to_node, edge_type=edge_type,
                                 weight=weight, timestamp=now)

    def get_causal_chain(self, ticker: str, depth: int = 3) -> Dict:
        """Traverse the causal graph around a ticker to depth N."""
        if not self._graph or ticker not in self._graph:
            node_key = f"ticker:{ticker.upper()}"
            if not self._graph or node_key not in self._graph:
                return {'nodes': [], 'edges': []}
            ticker = node_key
        subgraph_nodes = set()
        subgraph_nodes.add(ticker)
        frontier = {ticker}
        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                next_frontier.update(self._graph.successors(node))
                next_frontier.update(self._graph.predecessors(node))
            subgraph_nodes.update(next_frontier)
            frontier = next_frontier
        sub = self._graph.subgraph(subgraph_nodes)
        return {
            'nodes': list(sub.nodes()),
            'edges': [{'from': u, 'to': v, **d} for u, v, d in sub.edges(data=True)],
        }

    def get_causal_path(self, source_node: str, target_node: str) -> List[str]:
        """Find shortest causal path between two nodes."""
        if not self._graph:
            return []
        try:
            return nx.shortest_path(self._graph, source_node, target_node)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_causal_influence(self, source: str) -> Dict[str, float]:
        """Compute influence scores from a source node using PageRank-like weighting."""
        if not self._graph or source not in self._graph:
            return {}
        try:
            personalization = {n: 0.0 for n in self._graph.nodes()}
            personalization[source] = 1.0
            ranks = nx.pagerank(self._graph, personalization=personalization, alpha=0.85)
            sorted_ranks = sorted(ranks.items(), key=lambda x: -x[1])
            return {k: round(v, 6) for k, v in sorted_ranks[:20] if v > 0.001}
        except Exception:
            return {}

    # ------------------------------------------------------------------ #
    # RECORDING                                                            #
    # ------------------------------------------------------------------ #

    def record_signal(self, ticker: str, source: str,
                      setup: str = 'unknown', score: int = 0,
                      regime: str = 'UNKNOWN', entry_price: float = 0,
                      metadata: Dict = None) -> int:
        ticker = ticker.upper()
        source = source.lower()
        setup = setup.lower()
        regime = regime.upper()
        now = datetime.now().isoformat()
        date_key = date.today().isoformat()
        if ticker not in self._signals_today:
            self._signals_today.append(ticker)

        embedding = encode_trade_vector(
            score=score, regime=regime, source=source, setup=setup,
            days_ago=0,
        )

        conn = self._get_conn()
        try:
            cur = conn.execute(
                'INSERT INTO signals (ticker, source, setup, score, regime, '
                'entry_price, timestamp, date_key, embedding_json, metadata_json) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (ticker, source, setup, score, regime, entry_price,
                 now, date_key, json.dumps(embedding), json.dumps(metadata or {}))
            )
            signal_id = cur.lastrowid

            agent_id = f"{source}:{setup}"
            conn.execute(
                'INSERT INTO agents (agent_id, source, setup, created, signals) '
                'VALUES (?, ?, ?, ?, 1) '
                'ON CONFLICT(agent_id) DO UPDATE SET signals = signals + 1',
                (agent_id, source, setup, now)
            )
            conn.commit()

            # Upsert into ChromaDB
            chroma_meta = {
                'ticker': ticker, 'source': source, 'setup': setup,
                'score': float(score), 'regime': regime,
                'won': -1, 'pnl_pct': 0.0, 'signal_id': signal_id,
                'timestamp': now, 'entry_price': float(entry_price),
            }
            doc_text = f"{ticker} {source}:{setup} score={score} regime={regime} PENDING"
            self._upsert_vector(f"signal_{signal_id}", embedding, chroma_meta, doc_text)

            # Causal edges
            self._add_causal_edge(f"source:{source}", f"signal:{signal_id}",
                                  'generated', score / 100.0,
                                  {'ticker': ticker, 'regime': regime})
            self._add_causal_edge(f"signal:{signal_id}", f"ticker:{ticker}",
                                  'targets', 1.0)
            
            # NEW: Macro brain signal tracking
            self.macro_brain.record_signal(ticker, score)

            logger.info(f"[MemoryV3] Signal #{signal_id}: {ticker} via {source}:{setup} "
                        f"score={score} regime={regime}")
            return signal_id
        finally:
            conn.close()

    def record_outcome(self, ticker: str, source: str,
                       won: bool, pnl_pct: float = 0.0,
                       setup: str = 'unknown', regime: str = 'UNKNOWN',
                       signal_id: int = None, exit_price: float = 0,
                       hold_minutes: int = 0, metadata: Dict = None) -> int:
        ticker = ticker.upper()
        source = source.lower()
        setup = setup.lower()
        regime = regime.upper()
        now = datetime.now().isoformat()

        if signal_id is None:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    'SELECT id FROM signals WHERE ticker=? AND source=? '
                    'ORDER BY id DESC LIMIT 1', (ticker, source)
                ).fetchone()
                signal_id = row['id'] if row else 0
            finally:
                conn.close()

        conn = self._get_conn()
        try:
            cur = conn.execute(
                'INSERT INTO outcomes (signal_id, ticker, source, setup, regime, '
                'won, pnl_pct, exit_price, hold_minutes, timestamp, metadata_json) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (signal_id, ticker, source, setup, regime,
                 1 if won else 0, pnl_pct, exit_price,
                 hold_minutes, now, json.dumps(metadata or {}))
            )
            outcome_id = cur.lastrowid

            agent_id = f"{source}:{setup}"
            win_inc = 1 if won else 0
            loss_inc = 0 if won else 1
            conn.execute(
                'UPDATE agents SET outcomes = outcomes + 1, '
                'wins = wins + ?, losses = losses + ?, '
                'total_pnl_pct = total_pnl_pct + ?, last_outcome = ? '
                'WHERE agent_id = ?',
                (win_inc, loss_inc, pnl_pct, now, agent_id)
            )

            # Blacklist check
            if not won:
                recent_losses = conn.execute(
                    'SELECT COUNT(*) FROM outcomes WHERE ticker=? AND won=0 '
                    'ORDER BY id DESC LIMIT ?', (ticker, BLACKLIST_CONSECUTIVE)
                ).fetchone()[0]
                if recent_losses >= BLACKLIST_CONSECUTIVE:
                    expiry = (datetime.now() + timedelta(days=BLACKLIST_COOLDOWN_DAYS)).isoformat()[:10]
                    conn.execute(
                        'INSERT OR REPLACE INTO blacklist (ticker, reason, expiry, created) '
                        'VALUES (?, ?, ?, ?)',
                        (ticker, 'consecutive_losses', expiry, now)
                    )
                    logger.warning(f"[MemoryV3] BLACKLISTED {ticker} until {expiry}")

            conn.commit()

            # Update ChromaDB vector with outcome data
            sig_row = conn.execute('SELECT * FROM signals WHERE id=?', (signal_id,)).fetchone()
            if sig_row:
                days_ago = self._days_since(sig_row['timestamp'])
                updated_embedding = encode_trade_vector(
                    score=sig_row['score'] or 0, regime=regime,
                    source=source, setup=setup,
                    pnl_pct=pnl_pct, hold_minutes=hold_minutes,
                    days_ago=days_ago,
                )
                chroma_meta = {
                    'ticker': ticker, 'source': source, 'setup': setup,
                    'score': float(sig_row['score'] or 0), 'regime': regime,
                    'won': 1 if won else 0, 'pnl_pct': float(pnl_pct),
                    'signal_id': signal_id, 'timestamp': sig_row['timestamp'],
                    'hold_minutes': hold_minutes,
                }
                doc_text = (f"{ticker} {source}:{setup} score={sig_row['score']} "
                            f"regime={regime} {'WIN' if won else 'LOSS'} {pnl_pct:+.1f}%")
                self._upsert_vector(f"signal_{signal_id}", updated_embedding, chroma_meta, doc_text)

            # Causal edges
            self._add_causal_edge(f"signal:{signal_id}", f"outcome:{outcome_id}",
                                  'resulted_in', pnl_pct,
                                  {'won': won, 'regime': regime})

            self._recalculate_weights()
            self._evaluate_agents()
            self._update_expectancy_cache(source, setup, regime)

            logger.info(f"[MemoryV3] Outcome #{outcome_id}: {ticker} "
                        f"{'WIN' if won else 'LOSS'} {pnl_pct:+.1f}%")
            return outcome_id
        finally:
            conn.close()

    def reset_daily(self):
        today = date.today().isoformat()
        if self._last_reset != today:
            self._signals_today = []
            self._last_reset = today

            # Remove expired blacklist
            conn = self._get_conn()
            try:
                conn.execute('DELETE FROM blacklist WHERE expiry <= ?', (today,))
                conn.commit()
            finally:
                conn.close()

            # Compact and prune old memory (replaces raw DELETE)
            self.compact_memory()

            logger.info('[MemoryV3] Daily reset and memory compaction complete')
    
    # ------------------------------------------------------------------ #
    # FLYWHEEL: WEIGHT RECALCULATION                                       #
    # ------------------------------------------------------------------ #

    def _recalculate_weights(self):
        conn = self._get_conn()
        try:
            for src, default_pts in DEFAULT_WEIGHTS.items():
                rows = conn.execute(
                    'SELECT won, pnl_pct, timestamp FROM outcomes WHERE source=?',
                    (src,)
                ).fetchall()
                if len(rows) < MIN_TRADES_TO_ADJUST:
                    continue
                weighted_wins = 0.0
                weighted_total = 0.0
                weighted_win_pnl = 0.0
                weighted_loss_pnl = 0.0
                for r in rows:
                    decay = self._decay_weight(self._days_since(r['timestamp']))
                    weighted_total += decay
                    if r['won']:
                        weighted_wins += decay
                        weighted_win_pnl += abs(r['pnl_pct']) * decay
                    else:
                        weighted_loss_pnl += abs(r['pnl_pct']) * decay
                if weighted_total == 0:
                    continue
                wr = weighted_wins / weighted_total
                avg_win = weighted_win_pnl / weighted_wins if weighted_wins > 0 else 0
                avg_loss = weighted_loss_pnl / (weighted_total - weighted_wins) if (weighted_total - weighted_wins) > 0 else 0
                expectancy = avg_win * wr - avg_loss * (1 - wr)
                exp_bonus = 1.1 if expectancy > 0.5 else (0.9 if expectancy < -0.5 else 1.0)
                scale = max(0.5, min(1.5, (0.2 + wr * 1.6) * exp_bonus))
                new_weight = round(default_pts * scale)
                now = datetime.now().isoformat()
                conn.execute(
                    'UPDATE weights SET weight=?, last_updated=? WHERE source=?',
                    (new_weight, now, src)
                )
            conn.commit()
        finally:
            conn.close()

    def _evaluate_agents(self):
        conn = self._get_conn()
        try:
            agents = conn.execute('SELECT * FROM agents').fetchall()
            for ag in agents:
                outcomes = ag['outcomes']
                if outcomes < AGENT_MIN_TRADES:
                    continue
                wr = ag['wins'] / outcomes if outcomes > 0 else 0
                old_status = ag['status']
                if outcomes >= AGENT_PROMOTE_MIN and wr >= AGENT_PROMOTE_WR:
                    new_status = 'promoted'
                    promo_inc = 1 if old_status != 'promoted' else 0
                    conn.execute(
                        'UPDATE agents SET status=?, promotion_count=promotion_count+? WHERE agent_id=?',
                        (new_status, promo_inc, ag['agent_id'])
                    )
                    if old_status != 'promoted':
                        logger.info(f"[MemoryV3] PROMOTED: {ag['agent_id']} WR={wr:.0%}")
                elif wr < AGENT_PRUNE_WR:
                    new_status = 'pruned'
                    prune_inc = 1 if old_status != 'pruned' else 0
                    conn.execute(
                        'UPDATE agents SET status=?, prune_count=prune_count+? WHERE agent_id=?',
                        (new_status, prune_inc, ag['agent_id'])
                    )
                    if old_status != 'pruned':
                        logger.warning(f"[MemoryV3] PRUNED: {ag['agent_id']} WR={wr:.0%}")
                else:
                    conn.execute('UPDATE agents SET status=? WHERE agent_id=?',
                                 ('active', ag['agent_id']))
            conn.commit()
        finally:
            conn.close()

    def _update_expectancy_cache(self, source: str, setup: str, regime: str):
        """Update the expectancy cache for a source:setup:regime combination."""
        conn = self._get_conn()
        try:
            for cache_key_parts, where_clause, params in [
                ((source,), 'source=?', (source,)),
                ((source, setup), 'source=? AND setup=?', (source, setup)),
                ((source, setup, regime), 'source=? AND setup=? AND regime=?', (source, setup, regime)),
                (('regime', regime), 'regime=?', (regime,)),
            ]:
                cache_key = ':'.join(cache_key_parts)
                rows = conn.execute(
                    f'SELECT won, pnl_pct, timestamp FROM outcomes WHERE {where_clause}',
                    params
                ).fetchall()
                if not rows:
                    continue
                w_wins, w_total, w_win_pnl, w_loss_pnl = 0.0, 0.0, 0.0, 0.0
                for r in rows:
                    d = self._decay_weight(self._days_since(r['timestamp']))
                    w_total += d
                    if r['won']:
                        w_wins += d
                        w_win_pnl += abs(r['pnl_pct']) * d
                    else:
                        w_loss_pnl += abs(r['pnl_pct']) * d
                if w_total == 0:
                    continue
                wr = w_wins / w_total
                avg_w = w_win_pnl / w_wins if w_wins > 0 else 0
                avg_l = w_loss_pnl / (w_total - w_wins) if (w_total - w_wins) > 0 else 0
                expectancy = avg_w * wr - avg_l * (1 - wr)
                conn.execute(
                    'INSERT INTO expectancy_cache (cache_key, expectancy, sample_size, '
                    'decay_weighted_wr, avg_win, avg_loss, last_updated) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?) '
                    'ON CONFLICT(cache_key) DO UPDATE SET '
                    'expectancy=?, sample_size=?, decay_weighted_wr=?, '
                    'avg_win=?, avg_loss=?, last_updated=?',
                    (cache_key, expectancy, len(rows), wr, avg_w, avg_l,
                     datetime.now().isoformat(),
                     expectancy, len(rows), wr, avg_w, avg_l,
                     datetime.now().isoformat())
                )
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # QUERIES                                                              #
    # ------------------------------------------------------------------ #

    def get_source_weights(self) -> Dict:
        conn = self._get_conn()
        try:
            rows = conn.execute('SELECT source, weight FROM weights').fetchall()
            return {r['source']: r['weight'] for r in rows}
        finally:
            conn.close()

    def get_ticker_stats(self, ticker: str) -> Optional[Dict]:
        ticker = ticker.upper()
        conn = self._get_conn()
        try:
            sigs = conn.execute('SELECT COUNT(*) as c FROM signals WHERE ticker=?', (ticker,)).fetchone()['c']
            if sigs == 0:
                return None
            outs = conn.execute(
                'SELECT COUNT(*) as total, SUM(won) as wins, '
                'SUM(CASE WHEN won=0 THEN 1 ELSE 0 END) as losses, '
                'SUM(pnl_pct) as total_pnl, AVG(pnl_pct) as avg_pnl '
                'FROM outcomes WHERE ticker=?', (ticker,)
            ).fetchone()
            avg_score = conn.execute(
                'SELECT AVG(score) as avg FROM signals WHERE ticker=?', (ticker,)
            ).fetchone()['avg'] or 0
            sources = conn.execute(
                'SELECT DISTINCT source FROM signals WHERE ticker=?', (ticker,)
            ).fetchall()
            last = conn.execute(
                'SELECT timestamp FROM signals WHERE ticker=? ORDER BY id DESC LIMIT 1', (ticker,)
            ).fetchone()
            return {
                'signals': sigs,
                'outcomes': outs['total'] or 0,
                'wins': outs['wins'] or 0,
                'losses': outs['losses'] or 0,
                'total_pnl_pct': round(outs['total_pnl'] or 0, 2),
                'avg_pnl': round(outs['avg_pnl'] or 0, 2),
                'avg_score': round(avg_score, 1),
                'sources': [r['source'] for r in sources],
                'last_seen': last['timestamp'] if last else None,
            }
        finally:
            conn.close()

    def get_win_rate(self, ticker: str) -> float:
        stats = self.get_ticker_stats(ticker)
        if not stats or stats['outcomes'] == 0:
            return 0.5
        return round(stats['wins'] / stats['outcomes'], 3)

    def get_confidence(self, ticker: str) -> float:
        stats = self.get_ticker_stats(ticker)
        if not stats:
            return 0.0
        outcomes = stats['outcomes']
        if outcomes == 0:
            return 0.0
        return round(min(0.95, 1.0 - math.exp(-0.15 * outcomes)), 2)

    def is_blacklisted(self, ticker: str) -> bool:
        conn = self._get_conn()
        try:
            row = conn.execute(
                'SELECT expiry FROM blacklist WHERE ticker=?', (ticker.upper(),)
            ).fetchone()
            if not row:
                return False
            return row['expiry'] > date.today().isoformat()
        finally:
            conn.close()

    def get_blacklisted_tickers(self) -> List[str]:
        conn = self._get_conn()
        try:
            today = date.today().isoformat()
            rows = conn.execute('SELECT ticker FROM blacklist WHERE expiry > ?', (today,)).fetchall()
            return [r['ticker'] for r in rows]
        finally:
            conn.close()

    def get_agent_rankings(self) -> List[Dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute('SELECT * FROM agents ORDER BY '
                                'CASE WHEN outcomes > 0 THEN CAST(wins AS REAL)/outcomes ELSE 0 END DESC'
                                ).fetchall()
            result = []
            for r in rows:
                wr = (r['wins'] / r['outcomes'] * 100) if r['outcomes'] > 0 else 0
                result.append({
                    'agent_id': r['agent_id'], 'source': r['source'],
                    'setup': r['setup'], 'status': r['status'],
                    'outcomes': r['outcomes'], 'win_rate': round(wr, 1),
                    'total_pnl_pct': r['total_pnl_pct'],
                    'promotions': r['promotion_count'], 'prunes': r['prune_count'],
                })
            return result
        finally:
            conn.close()

    def get_active_agents(self) -> List[str]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT agent_id FROM agents WHERE status != 'pruned'").fetchall()
            return [r['agent_id'] for r in rows]
        finally:
            conn.close()

    def get_regime_stats(self) -> Dict:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                'SELECT regime, COUNT(*) as total, SUM(won) as wins, '
                'AVG(pnl_pct) as avg_pnl FROM outcomes GROUP BY regime'
            ).fetchall()
            return {
                r['regime']: {
                    'outcomes': r['total'],
                    'win_rate': round((r['wins'] or 0) / r['total'] * 100, 1) if r['total'] > 0 else 0,
                    'avg_pnl': round(r['avg_pnl'] or 0, 2),
                } for r in rows
            }
        finally:
            conn.close()

    def get_score_bin_stats(self) -> Dict:
        conn = self._get_conn()
        try:
            bins = {'80-100': (80, 101), '70-79': (70, 80), '60-69': (60, 70),
                    '50-59': (50, 60), '0-49': (0, 50)}
            result = {}
            for label, (lo, hi) in bins.items():
                row = conn.execute(
                    'SELECT COUNT(*) as total, SUM(o.won) as wins FROM outcomes o '
                    'JOIN signals s ON o.signal_id = s.id '
                    'WHERE s.score >= ? AND s.score < ?', (lo, hi)
                ).fetchone()
                if row['total'] and row['total'] > 0:
                    result[label] = {
                        'outcomes': row['total'],
                        'win_rate': round((row['wins'] or 0) / row['total'] * 100, 1),
                    }
            return result
        finally:
            conn.close()

    def get_top_tickers(self, n: int = 10) -> List[Tuple]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                'SELECT ticker, COUNT(*) as total, SUM(won) as wins '
                'FROM outcomes GROUP BY ticker HAVING total >= 2 '
                'ORDER BY CAST(wins AS REAL)/total DESC LIMIT ?', (n,)
            ).fetchall()
            return [(r['ticker'], round(r['wins']/r['total'], 3) if r['total'] > 0 else 0, {})
                    for r in rows]
        finally:
            conn.close()

    def get_expectancy(self, cache_key: str) -> Optional[Dict]:
        """Retrieve cached expectancy for a source, setup, or regime combo."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                'SELECT * FROM expectancy_cache WHERE cache_key=?', (cache_key,)
            ).fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # VECTOR SIMILARITY SEARCH (ChromaDB Hybrid)                           #
    # ------------------------------------------------------------------ #

    def find_similar_trades(self, ticker: str = None, score: float = None,
                            regime: str = None, source: str = None,
                            setup: str = None, limit: int = 10,
                            use_vector: bool = True) -> List[Dict]:
        """
        Hybrid similarity search:
        1. If ChromaDB available and use_vector=True: vector cosine similarity
        2. Fallback: SQLite range-based query
        Results are merged and ranked by combined relevance score.
        """
        vector_results = []
        sql_results = []

        # --- ChromaDB vector search ---
        if use_vector and self._chroma_collection and self._chroma_collection.count() > 0:
            query_vec = encode_trade_vector(
                score=score or 50,
                regime=regime or 'UNKNOWN',
                source=source or 'unknown',
                setup=setup or 'unknown',
            )
            where_filter = {}
            if ticker:
                where_filter['ticker'] = ticker.upper()
            if regime:
                where_filter['regime'] = regime.upper()

            hits = self._query_vectors(
                query_vec, n_results=limit * 2,
                where=where_filter if where_filter else None,
            )
            for h in hits:
                m = h.get('metadata', {})
                vector_results.append({
                    'signal_id': m.get('signal_id', 0),
                    'ticker': m.get('ticker', ''),
                    'source': m.get('source', ''),
                    'setup': m.get('setup', ''),
                    'score': m.get('score', 0),
                    'regime': m.get('regime', ''),
                    'won': m.get('won', -1),
                    'pnl_pct': m.get('pnl_pct', 0),
                    'similarity': round(h.get('similarity', 0), 4),
                    'match_type': 'vector',
                })

        # --- SQLite structured search ---
        conn = self._get_conn()
        try:
            query = ('SELECT s.*, o.won, o.pnl_pct, o.hold_minutes FROM signals s '
                     'LEFT JOIN outcomes o ON o.signal_id = s.id WHERE 1=1')
            params = []
            if ticker:
                query += ' AND s.ticker = ?'
                params.append(ticker.upper())
            if regime:
                query += ' AND s.regime = ?'
                params.append(regime.upper())
            if source:
                query += ' AND s.source = ?'
                params.append(source.lower())
            if setup:
                query += ' AND s.setup = ?'
                params.append(setup.lower())
            if score is not None:
                query += ' AND s.score BETWEEN ? AND ?'
                params.extend([score - 10, score + 10])
            query += ' ORDER BY s.id DESC LIMIT ?'
            params.append(limit * 2)
            rows = conn.execute(query, params).fetchall()
            for r in rows:
                sql_results.append({
                    'signal_id': r['id'],
                    'ticker': r['ticker'],
                    'source': r['source'],
                    'setup': r['setup'] or 'unknown',
                    'score': r['score'] or 0,
                    'regime': r['regime'] or 'UNKNOWN',
                    'won': r['won'] if r['won'] is not None else -1,
                    'pnl_pct': r['pnl_pct'] or 0,
                    'similarity': 0.5,
                    'match_type': 'sql',
                })
        finally:
            conn.close()

        # --- Merge and deduplicate with Confidence Weighting ---
        seen_ids = set()
        merged = []
        for item in vector_results + sql_results:
            sid = item.get('signal_id', 0)
            if sid in seen_ids:
                continue
            seen_ids.add(sid)

            # Confidence Weighting: Adjust similarity by sample size trust
            cache_key = f"{item.get('source', '')}:{item.get('setup', '')}:{item.get('regime', '')}"
            exp_data = self.get_expectancy(cache_key)
            confidence = 0.5  # Default middle confidence
            if exp_data and exp_data.get('sample_size', 0) > 0:
                samples = exp_data['sample_size']
                confidence = min(1.0, samples / 20.0)  # Max confidence at 20+ trades

            # Final ranking score: 70% semantic/SQL relevance, 30% statistical confidence
            base_sim = item.get('similarity', 0.5)
            item['relevance_score'] = round((base_sim * 0.7) + (confidence * 0.3), 4)
            item['confidence'] = round(confidence, 2)
            merged.append(item)

        # Sort by the new confidence-weighted relevance score
        merged.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return merged[:limit]

    def find_winning_patterns(self, regime: str = None, source: str = None,
                              min_score: float = 70, limit: int = 20) -> List[Dict]:
        """Find historically winning trade patterns using vector search."""
        if not self._chroma_collection or self._chroma_collection.count() == 0:
            return []

        query_vec = encode_trade_vector(
            score=min_score, regime=regime or 'GREEN',
            source=source or 'unknown', setup='momentum',
            pnl_pct=5.0,
        )
        where = {'won': 1}
        if regime:
            where['regime'] = regime.upper()

        hits = self._query_vectors(query_vec, n_results=limit, where=where)
        return [
            {
                'ticker': h['metadata'].get('ticker', ''),
                'source': h['metadata'].get('source', ''),
                'setup': h['metadata'].get('setup', ''),
                'score': h['metadata'].get('score', 0),
                'regime': h['metadata'].get('regime', ''),
                'pnl_pct': h['metadata'].get('pnl_pct', 0),
                'similarity': round(h.get('similarity', 0), 4),
            }
            for h in hits
        ]

    # ------------------------------------------------------------------ #
    # DECAY-WEIGHTED ANALYTICS                                             #
    # ------------------------------------------------------------------ #

    def get_decay_weighted_wr(self, source: str) -> float:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                'SELECT won, timestamp FROM outcomes WHERE source=?', (source,)
            ).fetchall()
            if not rows:
                return 0.5
            w_wins = sum(self._decay_weight(self._days_since(r['timestamp']))
                         for r in rows if r['won'])
            w_total = sum(self._decay_weight(self._days_since(r['timestamp']))
                          for r in rows)
            return round(w_wins / w_total, 3) if w_total > 0 else 0.5
        finally:
            conn.close()

    def get_decay_weighted_expectancy(self, source: str = None,
                                      setup: str = None,
                                      regime: str = None) -> Dict:
        """Compute full decay-weighted expectancy for a filter combination."""
        conn = self._get_conn()
        try:
            query = 'SELECT won, pnl_pct, timestamp FROM outcomes WHERE 1=1'
            params = []
            if source:
                query += ' AND source=?'
                params.append(source)
            if setup:
                query += ' AND setup=?'
                params.append(setup)
            if regime:
                query += ' AND regime=?'
                params.append(regime)
            rows = conn.execute(query, params).fetchall()
            if not rows:
                return {'expectancy': 0, 'win_rate': 0.5, 'avg_win': 0,
                        'avg_loss': 0, 'sample_size': 0, 'confidence': 0}
            w_wins, w_total, w_win_pnl, w_loss_pnl = 0.0, 0.0, 0.0, 0.0
            for r in rows:
                d = self._decay_weight(self._days_since(r['timestamp']))
                w_total += d
                if r['won']:
                    w_wins += d
                    w_win_pnl += abs(r['pnl_pct']) * d
                else:
                    w_loss_pnl += abs(r['pnl_pct']) * d
            if w_total == 0:
                return {'expectancy': 0, 'win_rate': 0.5, 'avg_win': 0,
                        'avg_loss': 0, 'sample_size': len(rows), 'confidence': 0}
            wr = w_wins / w_total
            avg_w = w_win_pnl / w_wins if w_wins > 0 else 0
            avg_l = w_loss_pnl / (w_total - w_wins) if (w_total - w_wins) > 0 else 0
            expectancy = avg_w * wr - avg_l * (1 - wr)
            confidence = min(0.95, 1.0 - math.exp(-0.15 * len(rows)))
            return {
                'expectancy': round(expectancy, 3),
                'win_rate': round(wr, 3),
                'avg_win': round(avg_w, 2),
                'avg_loss': round(avg_l, 2),
                'sample_size': len(rows),
                'confidence': round(confidence, 2),
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # LLM PATTERN ANALYSIS                                                 #
    # ------------------------------------------------------------------ #

    def analyze_patterns(self, ticker: str = None) -> Optional[str]:
        if not HAS_LLM:
            return None
        conn = self._get_conn()
        try:
            if ticker:
                recent = conn.execute(
                    'SELECT s.ticker, s.source, s.setup, s.score, s.regime, '
                    'o.won, o.pnl_pct FROM signals s '
                    'LEFT JOIN outcomes o ON o.signal_id = s.id '
                    'WHERE s.ticker = ? ORDER BY s.id DESC LIMIT 20',
                    (ticker.upper(),)
                ).fetchall()
            else:
                recent = conn.execute(
                    'SELECT s.ticker, s.source, s.setup, s.score, s.regime, '
                    'o.won, o.pnl_pct FROM signals s '
                    'LEFT JOIN outcomes o ON o.signal_id = s.id '
                    'ORDER BY s.id DESC LIMIT 50'
                ).fetchall()
            if not recent:
                return None

            # Enrich with vector similarity context
            vector_context = ""
            if self._chroma_collection and self._chroma_collection.count() > 0:
                winning = self.find_winning_patterns(limit=5)
                if winning:
                    vector_context = "\n\nTop winning pattern matches (by vector similarity):\n"
                    vector_context += "\n".join(
                        f"  {w['ticker']} {w['source']}:{w['setup']} "
                        f"score={w['score']} pnl={w['pnl_pct']:+.1f}% "
                        f"sim={w['similarity']:.3f}"
                        for w in winning
                    )

            trades_text = '\n'.join(
                f"{r['ticker']} {r['source']}:{r['setup']} score={r['score']} "
                f"regime={r['regime']} {'WIN' if r['won'] else 'LOSS'} "
                f"{r['pnl_pct']:+.1f}%" if r['won'] is not None
                else f"{r['ticker']} {r['source']}:{r['setup']} score={r['score']} (pending)"
                for r in recent
            )
            prompt = (
                f"Analyze these recent OpenClaw trades for patterns:\n{trades_text}"
                f"{vector_context}\n\n"
                "Identify: 1) Which sources/setups win most 2) Score ranges that work "
                "3) Regime-specific patterns 4) Actionable improvements. Be concise."
            )
            llm = get_llm()
            result = llm.query(prompt, task='score_analysis', temperature=0.3)
            return result.get('content')
        except Exception as e:
            logger.error(f"[MemoryV3] LLM analysis error: {e}")
            return None
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # EPISODIC & SEMANTIC PIPELINES (NEW)                                 #
    # ------------------------------------------------------------------ #

    def consolidate_episodic_to_semantic(self):
        """Promote high-value episodic trades into semantic patterns (learned rules).
        Scans expectancy_cache for statistically significant patterns and saves them."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                'SELECT * FROM expectancy_cache WHERE sample_size >= 5'
            ).fetchall()
            for r in rows:
                parts = r['cache_key'].split(':')
                if len(parts) == 3:
                    source, setup, regime = parts
                    wr = r['decay_weighted_wr']
                    samples = r['sample_size']
                    exp = r['expectancy']
                    if exp > 0.1 and wr > 0.60:
                        rule_text = f"High Probability: {source} {setup} in {regime} regime has a {wr*100:.1f}% win rate over {samples} trades with positive expectancy ({exp:+.2f})."
                    elif exp < -0.1 and wr < 0.40:
                        rule_text = f"Danger Pattern: {source} {setup} in {regime} regime has a poor {wr*100:.1f}% win rate over {samples} trades with negative expectancy ({exp:+.2f})."
                    else:
                        continue
                    conn.execute(
                        'INSERT INTO semantic_rules (rule_id, source, setup, regime, rule_text, win_rate, sample_size, last_updated) '
                        'VALUES (?, ?, ?, ?, ?, ?, ?, ?) '
                        'ON CONFLICT(rule_id) DO UPDATE SET '
                        'rule_text=?, win_rate=?, sample_size=?, last_updated=?',
                        (r['cache_key'], source, setup, regime, rule_text, wr, samples, datetime.now().isoformat(),
                         rule_text, wr, samples, datetime.now().isoformat())
                    )
            conn.commit()
            logger.info("[MemoryV3] Episodic to semantic consolidation complete.")
        finally:
            conn.close()

    def compact_memory(self):
        """Summarize old trades into aggregate statistics before pruning.
        Prevents intelligence loss while saving disk space."""
        cutoff = (datetime.now() - timedelta(days=STALE_DAYS)).isoformat()
        conn = self._get_conn()
        try:
            self.consolidate_episodic_to_semantic()
            deleted_outcomes = conn.execute(
                'DELETE FROM outcomes WHERE timestamp < ?', (cutoff,)
            ).rowcount
            deleted_signals = conn.execute(
                'DELETE FROM signals WHERE timestamp < ?', (cutoff,)
            ).rowcount
            conn.commit()
            if deleted_signals > 0:
                logger.info(f"[MemoryV3] Compaction: Pruned {deleted_signals} old signals, {deleted_outcomes} outcomes. Intelligence retained in expectancy_cache.")
        finally:
            conn.close()

    def recall(self, ticker: str, score: float = 50, regime: str = 'UNKNOWN') -> Dict:
        """3-Stage Recall Pipeline:
        1. Deterministic Preload (Recent Context)
        2. Semantic Vector Search
        3. Structured Facts (Expectancy / Ticker Stats / Semantic Rules)"""
        conn = self._get_conn()
        recent_trades = []
        semantic_rules = []
        try:
            cutoff = (datetime.now() - timedelta(days=2)).isoformat()
            rows = conn.execute(
                'SELECT s.ticker, s.source, s.setup, s.score, s.regime, o.won, o.pnl_pct '
                'FROM signals s LEFT JOIN outcomes o ON s.id = o.signal_id '
                'WHERE s.ticker = ? AND s.timestamp >= ? ORDER BY s.id DESC',
                (ticker.upper(), cutoff)
            ).fetchall()
            recent_trades = [dict(r) for r in rows]
            rules = conn.execute(
                'SELECT rule_text FROM semantic_rules WHERE regime = ?', (regime.upper(),)
            ).fetchall()
            semantic_rules = [r['rule_text'] for r in rules]
        finally:
            conn.close()
        similar_trades = self.find_similar_trades(ticker=ticker, score=score, regime=regime, limit=5)
        stats = self.get_ticker_stats(ticker)
        return {
            'ticker': ticker.upper(),
            'recent_context': recent_trades,
            'semantic_memory': similar_trades,
            'structured_facts': stats,
            'learned_rules': semantic_rules
        }

    def get_memory_quality_score(self) -> Dict:
        """Returns a 0-100 rating of memory system intelligence based on freshness,
        coverage across regimes, and expectancy confidence levels."""
        conn = self._get_conn()
        try:
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent_count = conn.execute('SELECT COUNT(*) FROM signals WHERE timestamp >= ?', (week_ago,)).fetchone()[0]
            freshness_score = min(100, (recent_count / 50.0) * 100)
            regimes = conn.execute('SELECT COUNT(DISTINCT regime) FROM outcomes').fetchone()[0]
            coverage_score = min(100, (regimes / 3.0) * 100)
            avg_samples = conn.execute('SELECT AVG(sample_size) FROM expectancy_cache').fetchone()[0] or 0
            confidence_score = min(100, (avg_samples / 15.0) * 100)
            iq_score = int((freshness_score * 0.3) + (coverage_score * 0.3) + (confidence_score * 0.4))
            return {
                'memory_iq': iq_score,
                'freshness': round(freshness_score, 1),
                'coverage': round(coverage_score, 1),
                'confidence': round(confidence_score, 1),
                'total_semantic_rules': conn.execute('SELECT COUNT(*) FROM semantic_rules').fetchone()[0]
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # BLACKBOARD INTEGRATION                                               #
    # ------------------------------------------------------------------ #

    async def start_blackboard_listener(self):
        if not HAS_BLACKBOARD:
            logger.info("[MemoryV3] Blackboard not available, skipping listener")
            return
        bb = get_blackboard()
        queue = await bb.subscribe(Topic.TRADE_OUTCOMES, 'memory_v3')
        logger.info("[MemoryV3] Listening on trade_outcomes topic")
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=5.0)
                if isinstance(msg, BlackboardMessage) and not msg.is_expired():
                    p = msg.payload
                    self.record_outcome(
                        ticker=p.get('ticker', ''),
                        source=p.get('source', msg.source_agent),
                        won=p.get('won', False),
                        pnl_pct=p.get('pnl_pct', 0),
                        setup=p.get('setup', 'unknown'),
                        regime=p.get('regime', 'UNKNOWN'),
                        signal_id=p.get('signal_id'),
                        exit_price=p.get('exit_price', 0),
                        hold_minutes=p.get('hold_minutes', 0),
                    )
                    await bb.publish(BlackboardMessage(
                        topic='memory_updates',
                        payload={'event': 'outcome_recorded', 'ticker': p.get('ticker'),
                                 'weights': self.get_source_weights()},
                        source_agent='memory_v3',
                        priority=5, ttl_seconds=120,
                    ))
                await bb.heartbeat('memory_v3')
            except asyncio.TimeoutError:
                try:
                    await bb.heartbeat('memory_v3')
                except Exception:
                    pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MemoryV3] Blackboard listener error: {e}")
                await asyncio.sleep(2)

    # ------------------------------------------------------------------ #
    # BACKWARD COMPAT: data property for v2.0 callers                      #
    # ------------------------------------------------------------------ #

    @property
    def data(self) -> Dict:
        conn = self._get_conn()
        try:
            total_sigs = conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
            total_outs = conn.execute('SELECT COUNT(*) FROM outcomes').fetchone()[0]
            chroma_count = self._chroma_collection.count() if self._chroma_collection else 0
            return {
                'total_signals': total_sigs,
                'total_outcomes': total_outs,
                'chroma_vectors': chroma_count,
                'weights': self.get_source_weights(),
                'last_reset': self._last_reset or date.today().isoformat(),
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # DIAGNOSTICS                                                          #
    # ------------------------------------------------------------------ #

    def get_health(self) -> Dict:
        """System health check for all subsystems."""
        conn = self._get_conn()
        try:
            sigs = conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
            outs = conn.execute('SELECT COUNT(*) FROM outcomes').fetchone()[0]
            agents = conn.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
            edges = conn.execute('SELECT COUNT(*) FROM causal_edges').fetchone()[0]
        finally:
            conn.close()

        return {
            'sqlite': {
                'status': 'ok',
                'signals': sigs,
                'outcomes': outs,
                'agents': agents,
                'causal_edges': edges,
                'db_path': str(self.db_path),
            },
            'chromadb': {
                'status': 'ok' if self._chroma_collection else 'disabled',
                'vectors': self._chroma_collection.count() if self._chroma_collection else 0,
                'path': str(self.chroma_path),
            },
            'causal_graph': {
                'status': 'ok' if self._graph is not None else 'disabled',
                'nodes': self._graph.number_of_nodes() if self._graph else 0,
                'edges': self._graph.number_of_edges() if self._graph else 0,
            },
            'macro_brain': {
                'status': 'active',
                'oscillator': round(self.macro_brain.oscillator, 2),
                'wave_state': self.macro_brain.wave_state,
                'active_teams': len(self.macro_brain.active_teams),
                'episodes': len(self.macro_brain.episodes),
            },
            'blackboard': {
                'status': 'available' if HAS_BLACKBOARD else 'disabled',
            },
            'llm': {
                'status': 'available' if HAS_LLM else 'disabled',
            },
        }

    # ------------------------------------------------------------------ #
    # SLACK SUMMARY                                                        #
    # ------------------------------------------------------------------ #

    def get_summary_text(self) -> str:
        d = self.data
        health = self.get_health()
        lines = ['*:brain: OpenClaw Agent Memory v3.0 + Macro Brain (SQLite + ChromaDB Hybrid)*\n']
        lines.append(f"*Total Signals:* {d['total_signals']} | "
                     f"*Outcomes:* {d['total_outcomes']} | "
                     f"*Vectors:* {d['chroma_vectors']}")
        
        # Macro brain status
        mb = health['macro_brain']
        lines.append(f"\n*:wave: Macro Brain:* {mb['wave_state']} (osc={mb['oscillator']}) "
                    f"{mb['active_teams']} teams | {mb['episodes']} episodes")

        lines.append('\n*Source Win Rates (decay-weighted):*')
        for src in DEFAULT_WEIGHTS:
            wr = self.get_decay_weighted_wr(src)
            w = d['weights'].get(src, '?')
            exp = self.get_expectancy(src)
            exp_str = f" E={exp['expectancy']:+.2f}" if exp else ""
            lines.append(f"  `{src}`: {wr*100:.1f}% WR weight={w}pts{exp_str}")

        agents = self.get_agent_rankings()
        if agents:
            lines.append('\n*:robot_face: Agent Leaderboard:*')
            for ag in agents[:8]:
                icon = ':star:' if ag['status'] == 'promoted' else \
                       ':x:' if ag['status'] == 'pruned' else ':gear:'
                lines.append(f"  {icon} `{ag['agent_id']}` "
                             f"{ag['win_rate']}% WR ({ag['outcomes']} trades) "
                             f"P&L={ag['total_pnl_pct']:+.1f}%")

        bins = self.get_score_bin_stats()
        if bins:
            lines.append('\n*Score Range Win Rates:*')
            for b in sorted(bins.keys(), reverse=True):
                s = bins[b]
                lines.append(f"  `{b}`: {s['win_rate']}% WR ({s['outcomes']} trades)")

        regimes = self.get_regime_stats()
        if regimes:
            lines.append('\n*Regime Performance:*')
            for r, s in regimes.items():
                lines.append(f"  `{r}`: {s['win_rate']}% WR "
                             f"avg={s['avg_pnl']:+.2f}% ({s['outcomes']} trades)")

        bl = self.get_blacklisted_tickers()
        if bl:
            lines.append(f"\n*:no_entry: Blacklisted ({len(bl)}):* {', '.join(bl)}")

        # System status
        lines.append('\n*:gear: Subsystem Status:*')
        for sub, info in health.items():
            status = info.get('status', 'unknown')
            icon = ':white_check_mark:' if status in ('ok', 'available', 'active') else ':warning:'
            detail = ''
            if sub == 'chromadb':
                detail = f" ({info.get('vectors', 0)} vectors)"
            elif sub == 'causal_graph':
                detail = f" ({info.get('nodes', 0)}N/{info.get('edges', 0)}E)"
            elif sub == 'macro_brain':
                detail = f" ({info.get('active_teams', 0)} teams)"
            lines.append(f"  {icon} `{sub}`: {status}{detail}")

        lines.append(f"\n_Storage: SQLite WAL + ChromaDB Cosine | "
                     f"Decay half-life: {ALPHA_DECAY_HALF_LIFE_DAYS}d | "
                     f"Embedding dim: {EMBEDDING_DIM} | "
                     f"Macro Brain: Active_")
        return '\n'.join(lines)


# ========== SINGLETON ==========
trade_memory = MemoryV3()


# ========== CLI ==========
def main():
    parser = argparse.ArgumentParser(description='OpenClaw Memory v3.0 + Macro Brain — SQLite + ChromaDB Hybrid')
    parser.add_argument('--summary', action='store_true', help='Print memory summary')
    parser.add_argument('--health', action='store_true', help='Show subsystem health')
    parser.add_argument('--stats', type=str, help='Show stats for a ticker')
    parser.add_argument('--agents', action='store_true', help='Show agent rankings')
    parser.add_argument('--regimes', action='store_true', help='Show regime stats')
    parser.add_argument('--similar', type=str, help='Find similar trades for ticker')
    parser.add_argument('--winning', action='store_true', help='Find winning patterns via vector search')
    parser.add_argument('--graph', type=str, help='Show causal chain for ticker')
    parser.add_argument('--influence', type=str, help='Show causal influence from a node')
    parser.add_argument('--analyze', type=str, nargs='?', const='', help='LLM pattern analysis')
    parser.add_argument('--expectancy', type=str, help='Show expectancy for source:setup:regime')
    parser.add_argument('--weights', action='store_true', help='Show source weights')
    parser.add_argument('--blacklist', action='store_true', help='Show blacklisted tickers')
    parser.add_argument('--backfill', action='store_true', help='Backfill ChromaDB from SQLite')
    parser.add_argument('--macro', action='store_true', help='Show macro brain state')
    parser.add_argument('--daemon', action='store_true', help='Run Blackboard listener')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(name)s %(levelname)s %(message)s')
    mem = trade_memory

    if args.summary:
        print(mem.get_summary_text())
    elif args.health:
        print(json.dumps(mem.get_health(), indent=2))
    elif args.stats:
        stats = mem.get_ticker_stats(args.stats)
        if stats:
            print(json.dumps(stats, indent=2, default=str))
        else:
            print(f"No data for {args.stats}")
    elif args.agents:
        for ag in mem.get_agent_rankings():
            print(f"  {ag['status']:>8s} {ag['agent_id']:<25s} "
                  f"{ag['win_rate']:>5.1f}% WR ({ag['outcomes']} trades) "
                  f"P&L={ag['total_pnl_pct']:+.1f}%")
    elif args.regimes:
        print(json.dumps(mem.get_regime_stats(), indent=2))
    elif args.similar:
        trades = mem.find_similar_trades(ticker=args.similar)
        for t in trades:
            print(json.dumps(t, indent=2, default=str))
    elif args.winning:
        patterns = mem.find_winning_patterns()
        for p in patterns:
            print(json.dumps(p, indent=2, default=str))
    elif args.graph:
        chain = mem.get_causal_chain(args.graph)
        print(json.dumps(chain, indent=2, default=str))
    elif args.influence:
        inf = mem.get_causal_influence(args.influence)
        for node, score in inf.items():
            print(f"  {node}: {score:.6f}")
    elif args.analyze is not None:
        ticker = args.analyze if args.analyze else None
        result = mem.analyze_patterns(ticker)
        print(result or 'No analysis available (LLM not configured)')
    elif args.expectancy:
        parts = args.expectancy.split(':')
        exp = mem.get_decay_weighted_expectancy(
            source=parts[0] if len(parts) > 0 else None,
            setup=parts[1] if len(parts) > 1 else None,
            regime=parts[2] if len(parts) > 2 else None,
        )
        print(json.dumps(exp, indent=2))
    elif args.weights:
        print(json.dumps(mem.get_source_weights(), indent=2))
    elif args.blacklist:
        bl = mem.get_blacklisted_tickers()
        print(f"Blacklisted: {', '.join(bl)}" if bl else "No blacklisted tickers")
    elif args.backfill:
        mem._backfill_chromadb()
        print("ChromaDB backfill complete")
    elif args.macro:
        print(json.dumps(mem.macro_brain.to_dict(), indent=2, default=str))
    elif args.daemon:
        print('OpenClaw Memory v3.0 + Macro Brain — Blackboard Listener (SQLite + ChromaDB)')
        asyncio.run(mem.start_blackboard_listener())
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
