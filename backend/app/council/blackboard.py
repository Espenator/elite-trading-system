"""BlackboardState — shared context passed through the council DAG.

Replaces the raw features dict with a structured object that each
stage writes to. The blackboard is the single source of truth for
the entire council evaluation pipeline.

Usage:
    bb = BlackboardState(symbol="AAPL", raw_features=features)
    # Stage 1 agents write perceptions
    bb.perceptions["market_perception"] = vote.to_dict()
    # Stage 2 writes hypothesis
    bb.hypothesis = vote.to_dict()
    # etc.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

import numpy as np

logger = logging.getLogger(__name__)

try:
    import cupy as cp
    _GPU_AVAILABLE = True
except Exception:
    cp = None
    _GPU_AVAILABLE = False

logger.info(
    "Blackboard GPU acceleration: %s",
    "enabled (CuPy)" if _GPU_AVAILABLE else "disabled (NumPy fallback)",
)


def _append_numeric_values(payload: Any, values: List[float]) -> None:
    """Collect numeric feature values from nested payloads."""
    if isinstance(payload, bool):
        return
    if isinstance(payload, (int, float)):
        values.append(float(payload))
        return
    if isinstance(payload, dict):
        for value in payload.values():
            _append_numeric_values(value, values)
        return
    if isinstance(payload, (list, tuple)):
        for value in payload:
            _append_numeric_values(value, values)


@dataclass
class BlackboardState:
    """Shared context for a single council evaluation.

    Created at the start of run_council() and passed through all stages.
    Each agent reads upstream data and writes its output to the appropriate field.
    """

    symbol: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_features: Dict[str, Any] = field(default_factory=dict)

    # Stage outputs — written by agents during evaluation
    perceptions: Dict[str, Any] = field(default_factory=dict)  # S1 agents write here
    hypothesis: Optional[Dict[str, Any]] = None  # S2 writes here
    strategy: Optional[Dict[str, Any]] = None  # S3 writes here
    risk_assessment: Optional[Dict[str, Any]] = None  # S4 risk writes here
    execution_plan: Optional[Dict[str, Any]] = None  # S4 execution writes here
    critic_review: Optional[Dict[str, Any]] = None  # S5 writes here

    # Phase 1: LLM routing provenance
    llm_trace: list = field(default_factory=list)  # [{agent, provider, latency_ms}]

    # Phase 2: Debate + adversarial outputs (Stage 5.5)
    regime_belief: Dict[str, float] = field(default_factory=dict)  # state→probability
    debate: Optional[Dict[str, Any]] = None  # transcript + scores from debate engine
    red_team_report: Optional[Dict[str, Any]] = None  # stress test results

    # Phase 3: Knowledge system context
    knowledge_context: Optional[Dict[str, Any]] = None  # recalled heuristics + memories

    # ── Academic Edge Agent Namespaces ────────────────────────────────────

    # P0: GEX / Options Flow Swarm
    gex: Dict[str, Any] = field(default_factory=lambda: {
        "net_gamma": 0.0,       # Aggregate net GEX (positive = dampen, negative = amplify)
        "gamma_flip": 0.0,      # Price level of gamma flip
        "call_wall": 0.0,       # Highest call gamma strike
        "put_wall": 0.0,        # Highest put gamma strike
        "max_pain": 0.0,        # Max pain strike for nearest expiry
        "pin_probability": 0.0, # 0-1, increases as expiry approaches and price nears max_pain
        "regime": "neutral",    # "long_gamma" | "short_gamma" | "neutral"
    })

    # P0: SEC Form 4 Insider Filing
    insider: Dict[str, Any] = field(default_factory=lambda: {
        "latest_filings": [],    # Last 24h of Form 4 filings for watchlist
        "cluster_tickers": [],   # Tickers with active cluster buys
        "top_signal": None,      # Highest-scored insider event
        "sector_heat": {},       # Aggregate insider buying by sector
    })

    # P1: Earnings Call NLP / Tone Analysis
    earnings: Dict[str, Any] = field(default_factory=lambda: {
        "tone_score": 0.0,                # Aggregate tone score
        "cfo_delta": 0.0,                 # CFO tone change from prior quarter
        "ceo_tone": 0.0,                  # CEO tone score
        "cfo_tone": 0.0,                  # CFO tone score
        "surprise_tone_divergence": 0.0,  # Divergence between surprise and tone
        "hedging_ratio": 0.0,             # Hedging language frequency
        "last_transcript_ticker": "",     # Last processed ticker
    })

    # P1: Social Sentiment (FinBERT) Swarm
    sentiment: Dict[str, Any] = field(default_factory=lambda: {
        "ticker_scores": {},     # {ticker: -1 to +1}
        "volume_anomalies": [],  # Tickers with mention volume spikes
        "crowd_extremes": [],    # Tickers at >90% bullish or >90% bearish
        "wsb_momentum": {},      # WSB-specific momentum score
    })

    # P1: Supply Chain Knowledge Graph
    supply_chain: Dict[str, Any] = field(default_factory=lambda: {
        "contagion_alerts": [],      # Active contagion propagation alerts
        "second_order_targets": [],  # Trade ideas from supply chain events
        "sector_rotation": {},       # Aggregate sector flow
        "graph_nodes": 0,            # Number of nodes in knowledge graph
        "graph_edges": 0,            # Number of edges in knowledge graph
    })

    # P2: 13F Institutional Flow
    institutional: Dict[str, Any] = field(default_factory=lambda: {
        "consensus_buys": [],    # Tickers with 5+ fund consensus
        "consensus_sells": [],   # Tickers with consensus selling
        "crowded_longs": [],     # Tickers in 30%+ of portfolios
        "sector_rotation": {},   # Quarter-over-quarter sector shifts
        "top_funds_active": 0,   # Number of tracked funds
    })

    # P2: Congressional / Political Trading
    congressional: Dict[str, Any] = field(default_factory=lambda: {
        "recent_trades": [],     # Recent congressional trade disclosures
        "committee_signals": [], # High-signal committee-relevant trades
        "cluster_sectors": {},   # Sectors with multi-member trading
        "top_signal": None,      # Highest-scored political trade event
    })

    # P2: Dark Pool Accumulation
    dark_pool: Dict[str, Any] = field(default_factory=lambda: {
        "dix": 0.0,                   # Dark Index value
        "dix_20d_avg": 0.0,           # 20-day DIX average
        "dix_signal": "neutral",      # "bullish_accumulation" | "neutral" | "distribution"
        "ticker_dark_flow": {},       # Per-ticker dark pool volume anomalies
        "divergence_tickers": [],     # Tickers with dark pool / price divergence
    })

    # P3: Multi-Agent RL Portfolio Optimizer
    portfolio_optimization: Dict[str, Any] = field(default_factory=lambda: {
        "position_sizes": {},        # Optimized position sizes from RL agent
        "rebalance_trades": [],      # Pending rebalance trades
        "risk_parity_weights": {},   # Risk parity target weights
        "drawdown_level": 0.0,       # Current drawdown percentage
        "drawdown_action": "none",   # "none" | "reduce_25" | "reduce_50" | "halt"
    })

    # P3: Multi-Agent Bull/Bear Debate
    bull_bear_debate: Dict[str, Any] = field(default_factory=lambda: {
        "bull_case": None,        # Bull hypothesis with evidence
        "bear_case": None,        # Bear hypothesis with evidence
        "debate_rounds": 0,       # Number of debate rounds completed
        "synthesis": None,        # Final probability-weighted assessment
        "winner": "neutral",      # "bull" | "bear" | "neutral"
    })

    # P3: Layered Memory (FinMem)
    layered_memory: Dict[str, Any] = field(default_factory=lambda: {
        "short_term": [],         # Last 20 trades for current ticker
        "mid_term": {},           # Sector patterns over past quarter
        "long_term": {},          # Historical regime transition outcomes
        "reflection": {},         # Meta-analysis of agent performance
        "cognitive_span_days": 90,  # Adjustable memory window
    })

    # P4: Satellite / Alternative Data
    alt_data: Dict[str, Any] = field(default_factory=lambda: {
        "signals": [],            # Active alternative data signals
        "confidence": 0.0,        # Overall alt data confidence
        "sources": [],            # Data sources contributing
    })

    # P4: Cross-Asset Macro Regime (FRED enhancement)
    macro_regime: Dict[str, Any] = field(default_factory=lambda: {
        "yield_curve_spread": 0.0,   # T10Y2Y spread
        "yield_curve_inverted": False,
        "credit_spread": 0.0,        # High yield OAS
        "breakeven_inflation": 0.0,  # T10YIE
        "vix_regime": "normal",      # "complacency" | "normal" | "elevated" | "crisis"
        "leading_indicators": {},    # Composite leading indicators
        "macro_regime": "NORMAL",    # "RISK_ON" | "NORMAL" | "CAUTIOUS" | "RISK_OFF" | "CRISIS"
    })

    # Identity and lifecycle
    council_decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 30  # decision expires after 30s

    # ── ETBI Cognitive Telemetry ──────────────────────────────────────────
    cognitive_mode: str = "exploit"  # "explore" | "exploit" | "defensive"
    stage_latencies: Dict[str, float] = field(default_factory=dict)  # stage→ms
    council_start_ms: float = 0.0  # monotonic start time for total latency

    # Extensible metadata (circuit breaker results, directives, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)
    _gpu_buffer: Any = field(default=None, init=False, repr=False, compare=False)
    _gpu_pinned: bool = field(default=False, init=False, repr=False, compare=False)

    @property
    def is_expired(self) -> bool:
        """Check if this blackboard has exceeded its TTL."""
        elapsed = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

    @property
    def features(self) -> Dict[str, Any]:
        """Convenience accessor — returns raw_features for backward compat with agents."""
        return self.raw_features

    def _feature_vector(self) -> np.ndarray:
        """Build a deterministic numeric vector from raw feature payload."""
        feature_payload = self.raw_features.get("features", self.raw_features)
        values: List[float] = []
        _append_numeric_values(feature_payload, values)
        if not values:
            return np.empty(0, dtype=np.float32)
        return np.asarray(values, dtype=np.float32)

    def pin_to_gpu(self) -> bool:
        """Best-effort pin of numeric feature vector to GPU memory."""
        if not _GPU_AVAILABLE:
            return False
        try:
            self._gpu_buffer = cp.asarray(self._feature_vector(), dtype=cp.float32)
            self._gpu_pinned = True
            return True
        except Exception as exc:
            logger.debug("Failed to pin blackboard features to GPU: %s", exc)
            self._gpu_buffer = None
            self._gpu_pinned = False
            return False

    def gpu_features(self) -> np.ndarray:
        """Return numeric feature vector from GPU if available, else NumPy fallback."""
        if _GPU_AVAILABLE and self._gpu_pinned and self._gpu_buffer is not None:
            try:
                return cp.asnumpy(self._gpu_buffer)
            except Exception as exc:
                logger.debug("Failed to read GPU features, using CPU fallback: %s", exc)
                self._gpu_buffer = None
                self._gpu_pinned = False
        return self._feature_vector()

    def release_gpu(self) -> None:
        """Release GPU-backed buffers safely (no-op when GPU unavailable)."""
        try:
            self._gpu_buffer = None
            self._gpu_pinned = False
            if _GPU_AVAILABLE:
                cp.get_default_memory_pool().free_all_blocks()
        except Exception as exc:
            logger.debug("Failed to release blackboard GPU resources: %s", exc)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging, WebSocket broadcast, or postmortem storage."""
        return {
            "council_decision_id": self.council_decision_id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "perceptions": self.perceptions,
            "hypothesis": self.hypothesis,
            "strategy": self.strategy,
            "risk_assessment": self.risk_assessment,
            "execution_plan": self.execution_plan,
            "critic_review": self.critic_review,
            "llm_trace": self.llm_trace,
            "regime_belief": self.regime_belief,
            "debate": self.debate,
            "red_team_report": self.red_team_report,
            "knowledge_context": self.knowledge_context,
            "cognitive_mode": self.cognitive_mode,
            "stage_latencies": {k: round(v, 1) for k, v in self.stage_latencies.items()},
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
        }

    def to_snapshot(self) -> Dict[str, Any]:
        """Compact snapshot for postmortem storage (excludes raw_features bulk)."""
        return {
            "council_decision_id": self.council_decision_id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "perceptions": self.perceptions,
            "hypothesis": self.hypothesis,
            "strategy": self.strategy,
            "risk_assessment": self.risk_assessment,
            "execution_plan": self.execution_plan,
            "critic_review": self.critic_review,
        }
