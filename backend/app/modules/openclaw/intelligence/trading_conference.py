"""
Trading Conference Agent v1.0 — Deterministic DAG-based multi-agent consensus system.

LangGraph-style pattern using a strict execution DAG:
    Researcher → Risk Officer → Adversary → Consensus Arbitrator

Each agent is a pure function that reads the shared state and appends its analysis.
No LLM dependency for the core logic — uses structured data + scoring.
Optional LLM enhancement via intelligence/llm_client.py for narrative generation.

Integrates with:
    - intelligence/llm_client.py (optional narrative enhancement)
    - intelligence/macro_context.py (FRED macro data)
    - intelligence/hmm_regime.py (market regime detection)
    - intelligence/performance_tracker.py (historical accuracy)
    - ml_engine/ (XGBoost/LSTM signals)
    - services/alpaca_service.py (portfolio context)
    - services/unusual_whales_service.py (options flow)

Usage:
    from app.modules.openclaw.intelligence.trading_conference import TradingConference
    conference = TradingConference()
    result = await conference.convene(symbol="AAPL", timeframe="1d")
    # result.decision -> "BUY" | "SELL" | "HOLD" | "NO_TRADE"
    # result.confidence -> 0.0 to 1.0
    # result.transcript -> full deliberation log
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and data structures
# ---------------------------------------------------------------------------

class Decision(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NO_TRADE = "NO_TRADE"


class ConferenceStage(str, Enum):
    RESEARCH = "research"
    RISK = "risk_assessment"
    ADVERSARY = "adversary_challenge"
    CONSENSUS = "consensus"
    COMPLETE = "complete"


@dataclass
class AgentOpinion:
    """One agent's contribution to the conference."""
    agent_name: str = ""
    agent_role: str = ""
    decision: str = ""
    confidence: float = 0.0
    rationale: str = ""
    data_points: Dict[str, Any] = field(default_factory=dict)
    risk_flags: List[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConferenceState:
    """Shared mutable state passed through the DAG."""
    session_id: str = ""
    symbol: str = ""
    timeframe: str = "1d"
    stage: str = ConferenceStage.RESEARCH.value
    opinions: List[Dict] = field(default_factory=list)
    market_data: Dict[str, Any] = field(default_factory=dict)
    ml_signals: Dict[str, Any] = field(default_factory=dict)
    macro_context: Dict[str, Any] = field(default_factory=dict)
    options_flow: Dict[str, Any] = field(default_factory=dict)
    portfolio_context: Dict[str, Any] = field(default_factory=dict)
    risk_metrics: Dict[str, Any] = field(default_factory=dict)
    regime: str = "unknown"
    final_decision: str = Decision.NO_TRADE.value
    final_confidence: float = 0.0
    transcript: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    created_at: str = ""
    completed_at: str = ""
    duration_ms: int = 0

    def add_transcript(self, agent: str, message: str):
        entry = f"[{agent}] {message}"
        self.transcript.append(entry)
        log.debug(entry)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConferenceResult:
    """Final output of the trading conference."""
    session_id: str = ""
    symbol: str = ""
    decision: str = Decision.NO_TRADE.value
    confidence: float = 0.0
    position_size_pct: float = 0.0
    stop_loss_pct: float = 0.0
    take_profit_pct: float = 0.0
    risk_reward_ratio: float = 0.0
    opinions: List[Dict] = field(default_factory=list)
    transcript: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    regime: str = "unknown"
    duration_ms: int = 0
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Individual Agent implementations
# ---------------------------------------------------------------------------

class ResearcherAgent:
    """
    Agent 1: Researcher — Gathers and synthesizes all available data.
    Produces a preliminary directional view with supporting evidence.
    """

    AGENT_NAME = "Researcher"
    AGENT_ROLE = "Data synthesis and preliminary direction"

    async def analyze(self, state: ConferenceState) -> AgentOpinion:
        state.add_transcript(self.AGENT_NAME, f"Beginning research for {state.symbol}")

        # Gather all signal inputs
        signals = state.ml_signals
        macro = state.macro_context
        flow = state.options_flow
        data = state.market_data

        # Score components
        scores: Dict[str, float] = {}
        data_points: Dict[str, Any] = {}

        # ML signal score (-1 to +1)
        ml_prob = signals.get("prob_up", 0.5)
        ml_score = (ml_prob - 0.5) * 2  # Normalize to [-1, 1]
        scores["ml_direction"] = ml_score
        data_points["ml_prob_up"] = ml_prob

        # Multi-task signals if available
        if "magnitude" in signals:
            scores["ml_magnitude"] = signals["magnitude"]
            data_points["expected_magnitude"] = signals["magnitude"]
        if "volatility" in signals:
            data_points["expected_volatility"] = signals["volatility"]

        # Trend strength from price data
        if data:
            ma_dist = data.get("ma_20_dist", 0)
            scores["trend"] = max(-1, min(1, ma_dist * 10))
            data_points["ma_20_dist"] = ma_dist
            data_points["return_1d"] = data.get("return_1d", 0)
            data_points["vol_20"] = data.get("vol_20", 0)

        # Options flow signal
        if flow:
            pcr = flow.get("pcr_volume", flow.get("flow_pcr_vol", 1.0))
            # PCR < 0.7 = bullish, > 1.3 = bearish
            flow_score = max(-1, min(1, (1.0 - pcr) * 2))
            scores["options_flow"] = flow_score
            data_points["put_call_ratio"] = pcr
            net_prem = flow.get("net_premium", 0)
            data_points["net_premium"] = net_prem

        # Macro context
        if macro:
            regime = macro.get("regime", state.regime)
            data_points["macro_regime"] = regime
            vix = macro.get("vix", 20)
            data_points["vix"] = vix
            # High VIX → reduce conviction
            if vix > 30:
                scores["macro_fear"] = -0.3
            elif vix < 15:
                scores["macro_calm"] = 0.1

        # Composite score (weighted)
        weights = {"ml_direction": 0.35, "trend": 0.25, "options_flow": 0.20, "macro_fear": 0.10, "macro_calm": 0.10}
        weighted_sum = sum(scores.get(k, 0) * weights.get(k, 0.1) for k in scores)
        total_weight = sum(weights.get(k, 0.1) for k in scores if k in scores)
        composite = weighted_sum / max(total_weight, 0.01)

        # Decision
        if composite > 0.15:
            decision = Decision.BUY.value
        elif composite < -0.15:
            decision = Decision.SELL.value
        else:
            decision = Decision.HOLD.value

        confidence = min(1.0, abs(composite) * 1.5)

        rationale = (
            f"Composite score: {composite:.3f} from {len(scores)} signals. "
            f"ML P(up)={ml_prob:.2f}, trend={scores.get('trend', 0):.2f}, "
            f"flow={scores.get('options_flow', 0):.2f}. "
            f"Regime: {state.regime}."
        )

        state.add_transcript(self.AGENT_NAME, f"Verdict: {decision} (conf={confidence:.2f}) — {rationale}")

        return AgentOpinion(
            agent_name=self.AGENT_NAME,
            agent_role=self.AGENT_ROLE,
            decision=decision,
            confidence=confidence,
            rationale=rationale,
            data_points=data_points,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


class RiskOfficerAgent:
    """
    Agent 2: Risk Officer — Evaluates risk exposure, position limits, and portfolio impact.
    Can downgrade or veto the Researcher's recommendation.
    """

    AGENT_NAME = "Risk Officer"
    AGENT_ROLE = "Risk assessment and position sizing"

    # Risk thresholds
    MAX_SINGLE_POSITION_PCT = 5.0     # Max 5% of portfolio in one position
    MAX_DAILY_LOSS_PCT = 2.0          # Max 2% daily portfolio loss
    HIGH_VOL_THRESHOLD = 0.03         # 3% daily vol → reduced sizing

    async def analyze(self, state: ConferenceState) -> AgentOpinion:
        state.add_transcript(self.AGENT_NAME, "Evaluating risk parameters")

        researcher_opinion = state.opinions[-1] if state.opinions else {}
        researcher_decision = researcher_opinion.get("decision", Decision.HOLD.value)
        researcher_confidence = researcher_opinion.get("confidence", 0)

        risk_flags: List[str] = []
        risk_data: Dict[str, Any] = {}
        risk_adjustment = 1.0  # Multiplier on confidence

        # 1. Volatility check
        vol = state.market_data.get("vol_20", 0.02)
        risk_data["realized_vol_20d"] = vol
        if vol > self.HIGH_VOL_THRESHOLD:
            risk_flags.append(f"HIGH_VOLATILITY: {vol:.4f} > {self.HIGH_VOL_THRESHOLD}")
            risk_adjustment *= 0.6
        elif vol > self.HIGH_VOL_THRESHOLD * 0.7:
            risk_flags.append(f"ELEVATED_VOLATILITY: {vol:.4f}")
            risk_adjustment *= 0.8

        # 2. VIX regime check
        vix = state.macro_context.get("vix", 20)
        risk_data["vix"] = vix
        if vix > 35:
            risk_flags.append(f"EXTREME_VIX: {vix}")
            risk_adjustment *= 0.4
        elif vix > 25:
            risk_flags.append(f"HIGH_VIX: {vix}")
            risk_adjustment *= 0.7

        # 3. Portfolio concentration check
        portfolio = state.portfolio_context
        existing_exposure = portfolio.get("symbol_weight_pct", 0)
        risk_data["existing_exposure_pct"] = existing_exposure
        if existing_exposure > self.MAX_SINGLE_POSITION_PCT:
            risk_flags.append(f"OVERCONCENTRATED: {existing_exposure:.1f}% > {self.MAX_SINGLE_POSITION_PCT}%")
            risk_adjustment *= 0.3

        # 4. Drawdown check
        daily_pnl_pct = portfolio.get("daily_pnl_pct", 0)
        risk_data["daily_pnl_pct"] = daily_pnl_pct
        if daily_pnl_pct < -self.MAX_DAILY_LOSS_PCT:
            risk_flags.append(f"DAILY_LOSS_LIMIT: {daily_pnl_pct:.2f}% exceeded")
            risk_adjustment = 0.0  # Full veto

        # 5. Regime check
        if state.regime in ("bear", "crisis", "high_vol"):
            risk_flags.append(f"ADVERSE_REGIME: {state.regime}")
            risk_adjustment *= 0.5

        # Position sizing (Kelly-inspired)
        adj_confidence = researcher_confidence * risk_adjustment
        position_size_pct = min(self.MAX_SINGLE_POSITION_PCT, adj_confidence * 8)  # Scale 0-5%

        # Stop loss / take profit (ATR-based)
        atr_pct = state.market_data.get("atr_14_pct", vol * 2)
        stop_loss_pct = max(0.5, atr_pct * 2 * 100)   # 2x ATR
        take_profit_pct = max(1.0, atr_pct * 3 * 100)  # 3x ATR
        risk_reward = take_profit_pct / max(stop_loss_pct, 0.01)

        risk_data["position_size_pct"] = round(position_size_pct, 2)
        risk_data["stop_loss_pct"] = round(stop_loss_pct, 2)
        risk_data["take_profit_pct"] = round(take_profit_pct, 2)
        risk_data["risk_reward_ratio"] = round(risk_reward, 2)
        risk_data["risk_adjustment"] = round(risk_adjustment, 2)

        # Store for consensus
        state.risk_metrics = risk_data

        # Decision: maintain or downgrade
        if risk_adjustment == 0:
            decision = Decision.NO_TRADE.value
            rationale = f"VETO: {', '.join(risk_flags)}"
        elif risk_adjustment < 0.5:
            decision = Decision.HOLD.value
            rationale = f"Downgraded to HOLD due to: {', '.join(risk_flags)}"
        else:
            decision = researcher_decision
            rationale = f"Approved with adjustment={risk_adjustment:.2f}. Size={position_size_pct:.1f}%, SL={stop_loss_pct:.1f}%, TP={take_profit_pct:.1f}%"

        confidence = adj_confidence
        state.add_transcript(self.AGENT_NAME, f"Verdict: {decision} (adj_conf={confidence:.2f}, flags={len(risk_flags)}) — {rationale}")

        return AgentOpinion(
            agent_name=self.AGENT_NAME,
            agent_role=self.AGENT_ROLE,
            decision=decision,
            confidence=confidence,
            rationale=rationale,
            data_points=risk_data,
            risk_flags=risk_flags,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


class AdversaryAgent:
    """
    Agent 3: Adversary — Devil's advocate that challenges the prevailing consensus.
    Actively looks for reasons the trade would fail.
    """

    AGENT_NAME = "Adversary"
    AGENT_ROLE = "Contrarian challenge and stress testing"

    async def analyze(self, state: ConferenceState) -> AgentOpinion:
        state.add_transcript(self.AGENT_NAME, "Mounting contrarian challenge")

        # Get prevailing view from earlier agents
        opinions = state.opinions
        researcher = opinions[0] if len(opinions) > 0 else {}
        risk_officer = opinions[1] if len(opinions) > 1 else {}
        prevailing = researcher.get("decision", Decision.HOLD.value)

        challenges: List[str] = []
        data_points: Dict[str, Any] = {}
        challenge_strength = 0.0

        # 1. Mean reversion risk for momentum trades
        returns = state.market_data
        ret_5d = returns.get("return_5d", returns.get("return_1d", 0) * 3)
        if prevailing == Decision.BUY.value and ret_5d > 0.05:
            challenges.append(f"MEAN_REVERSION: Already up {ret_5d*100:.1f}% in 5d — overextended")
            challenge_strength += 0.3
        elif prevailing == Decision.SELL.value and ret_5d < -0.05:
            challenges.append(f"BOUNCE_RISK: Already down {ret_5d*100:.1f}% in 5d — oversold bounce likely")
            challenge_strength += 0.3

        # 2. Contrarian options flow
        flow = state.options_flow
        pcr = flow.get("pcr_volume", flow.get("flow_pcr_vol", 1.0))
        if prevailing == Decision.BUY.value and pcr > 1.2:
            challenges.append(f"OPTIONS_BEARISH: PCR={pcr:.2f} — smart money positioning bearish")
            challenge_strength += 0.25
        elif prevailing == Decision.SELL.value and pcr < 0.6:
            challenges.append(f"OPTIONS_BULLISH: PCR={pcr:.2f} — smart money positioning bullish")
            challenge_strength += 0.25

        # 3. ML confidence challenge
        ml_prob = state.ml_signals.get("prob_up", 0.5)
        ml_conf = abs(ml_prob - 0.5) * 2
        if ml_conf < 0.2:
            challenges.append(f"WEAK_ML_SIGNAL: P(up)={ml_prob:.2f} — model barely above coin flip")
            challenge_strength += 0.2

        # 4. Volatility crush / expansion risk
        vol = state.market_data.get("vol_20", 0.02)
        vol_ratio = state.market_data.get("vol_ratio_5_60", 1.0)
        if vol_ratio > 1.5:
            challenges.append(f"VOL_EXPANSION: Short-term vol {vol_ratio:.1f}x long-term — regime shift possible")
            challenge_strength += 0.15
        elif vol_ratio < 0.5:
            challenges.append(f"VOL_COMPRESSION: Breakout imminent — direction uncertain")
            challenge_strength += 0.1

        # 5. Macro headwinds
        macro = state.macro_context
        if macro.get("fed_hawkish", False) and prevailing == Decision.BUY.value:
            challenges.append("FED_HAWKISH: Tightening cycle headwind for longs")
            challenge_strength += 0.15

        # 6. Crowded trade check
        data_points["challenges_raised"] = len(challenges)
        data_points["challenge_strength"] = round(challenge_strength, 3)

        # Adversary decision
        if challenge_strength > 0.6:
            decision = Decision.NO_TRADE.value
            confidence = challenge_strength
            rationale = f"STRONG OBJECTION ({len(challenges)} flags): {'; '.join(challenges[:3])}"
        elif challenge_strength > 0.3:
            decision = Decision.HOLD.value
            confidence = 0.5
            rationale = f"Moderate concerns ({len(challenges)} flags): {'; '.join(challenges[:3])}"
        else:
            # Concede to prevailing view
            decision = prevailing
            confidence = researcher.get("confidence", 0.5) * 0.9
            rationale = f"No strong objections. Minor notes: {'; '.join(challenges) if challenges else 'None'}"

        state.add_transcript(self.AGENT_NAME, f"Challenge: {rationale}")

        return AgentOpinion(
            agent_name=self.AGENT_NAME,
            agent_role=self.AGENT_ROLE,
            decision=decision,
            confidence=confidence,
            rationale=rationale,
            data_points=data_points,
            risk_flags=challenges,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


class ConsensusArbitrator:
    """
    Agent 4: Consensus Arbitrator — Synthesizes all opinions into a final decision.
    Uses weighted voting with veto power for Risk Officer and strong Adversary objections.
    """

    AGENT_NAME = "Arbitrator"
    AGENT_ROLE = "Final decision synthesis"

    # Voting weights
    WEIGHTS = {
        "Researcher": 0.40,
        "Risk Officer": 0.35,
        "Adversary": 0.25,
    }

    # Minimum agreement for action
    MIN_CONFIDENCE = 0.30
    MIN_AGREE_COUNT = 2  # At least 2 of 3 agents must agree on direction

    async def synthesize(self, state: ConferenceState) -> ConferenceResult:
        state.add_transcript(self.AGENT_NAME, "Synthesizing conference opinions")

        opinions = state.opinions
        if not opinions:
            return ConferenceResult(
                session_id=state.session_id,
                symbol=state.symbol,
                decision=Decision.NO_TRADE.value,
                confidence=0.0,
                errors=["No opinions to synthesize"],
            )

        # Count votes
        decision_votes: Dict[str, float] = {}
        weighted_confidence = 0.0
        total_weight = 0.0

        for op in opinions:
            agent = op.get("agent_name", "")
            w = self.WEIGHTS.get(agent, 0.1)
            d = op.get("decision", Decision.HOLD.value)
            c = op.get("confidence", 0)

            decision_votes[d] = decision_votes.get(d, 0) + w
            weighted_confidence += c * w
            total_weight += w

        avg_confidence = weighted_confidence / max(total_weight, 0.01)

        # Check for Risk Officer veto
        risk_opinion = next((o for o in opinions if o.get("agent_name") == "Risk Officer"), {})
        if risk_opinion.get("decision") == Decision.NO_TRADE.value:
            state.add_transcript(self.AGENT_NAME, "Risk Officer VETO — overriding to NO_TRADE")
            return self._build_result(state, Decision.NO_TRADE.value, 0.0)

        # Check for strong Adversary objection
        adversary = next((o for o in opinions if o.get("agent_name") == "Adversary"), {})
        adv_strength = adversary.get("data_points", {}).get("challenge_strength", 0)
        if adv_strength > 0.6 and adversary.get("decision") == Decision.NO_TRADE.value:
            state.add_transcript(self.AGENT_NAME, f"Adversary strong objection (strength={adv_strength:.2f}) — downgrading to HOLD")
            return self._build_result(state, Decision.HOLD.value, avg_confidence * 0.3)

        # Majority decision
        best_decision = max(decision_votes, key=decision_votes.get)
        agree_count = sum(1 for o in opinions if o.get("decision") == best_decision)

        # Confidence gate
        if avg_confidence < self.MIN_CONFIDENCE:
            state.add_transcript(self.AGENT_NAME, f"Confidence {avg_confidence:.2f} below threshold {self.MIN_CONFIDENCE} — HOLD")
            return self._build_result(state, Decision.HOLD.value, avg_confidence)

        # Agreement gate
        if agree_count < self.MIN_AGREE_COUNT and best_decision in (Decision.BUY.value, Decision.SELL.value):
            state.add_transcript(self.AGENT_NAME, f"Insufficient agreement ({agree_count}/{len(opinions)}) — HOLD")
            return self._build_result(state, Decision.HOLD.value, avg_confidence * 0.5)

        state.add_transcript(
            self.AGENT_NAME,
            f"CONSENSUS: {best_decision} (conf={avg_confidence:.2f}, agree={agree_count}/{len(opinions)})"
        )
        return self._build_result(state, best_decision, avg_confidence)

    def _build_result(self, state: ConferenceState, decision: str, confidence: float) -> ConferenceResult:
        risk = state.risk_metrics
        return ConferenceResult(
            session_id=state.session_id,
            symbol=state.symbol,
            decision=decision,
            confidence=round(confidence, 4),
            position_size_pct=risk.get("position_size_pct", 0) if decision in (Decision.BUY.value, Decision.SELL.value) else 0,
            stop_loss_pct=risk.get("stop_loss_pct", 0),
            take_profit_pct=risk.get("take_profit_pct", 0),
            risk_reward_ratio=risk.get("risk_reward_ratio", 0),
            opinions=state.opinions,
            transcript=state.transcript,
            errors=state.errors,
            regime=state.regime,
            duration_ms=state.duration_ms,
            created_at=state.created_at,
        )


# ---------------------------------------------------------------------------
# Trading Conference Orchestrator (DAG runner)
# ---------------------------------------------------------------------------

class TradingConference:
    """
    Orchestrates the deterministic DAG:
        Researcher → Risk Officer → Adversary → Consensus Arbitrator

    Usage:
        conference = TradingConference()
        result = await conference.convene("AAPL")
    """

    def __init__(self):
        self.researcher = ResearcherAgent()
        self.risk_officer = RiskOfficerAgent()
        self.adversary = AdversaryAgent()
        self.arbitrator = ConsensusArbitrator()

    async def convene(
        self,
        symbol: str,
        timeframe: str = "1d",
        market_data: Optional[Dict] = None,
        ml_signals: Optional[Dict] = None,
        macro_context: Optional[Dict] = None,
        options_flow: Optional[Dict] = None,
        portfolio_context: Optional[Dict] = None,
        regime: str = "unknown",
    ) -> ConferenceResult:
        """
        Run the full conference DAG for a symbol.

        Args:
            symbol: Ticker symbol.
            timeframe: Trading timeframe.
            market_data: Latest price/volume features dict.
            ml_signals: ML model predictions dict (prob_up, magnitude, volatility).
            macro_context: FRED macro data dict.
            options_flow: Options flow aggregate dict.
            portfolio_context: Current portfolio context dict.
            regime: Market regime string from HMM.

        Returns:
            ConferenceResult with final decision and full transcript.
        """
        start_time = time.time()
        session_id = hashlib.md5(f"{symbol}_{time.time()}".encode()).hexdigest()[:12]

        state = ConferenceState(
            session_id=session_id,
            symbol=symbol.upper(),
            timeframe=timeframe,
            market_data=market_data or {},
            ml_signals=ml_signals or {},
            macro_context=macro_context or {},
            options_flow=options_flow or {},
            portfolio_context=portfolio_context or {},
            regime=regime,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        state.add_transcript("Conference", f"=== Trading Conference for {symbol} ===")

        try:
            # Stage 1: Researcher
            state.stage = ConferenceStage.RESEARCH.value
            researcher_opinion = await self.researcher.analyze(state)
            state.opinions.append(researcher_opinion.to_dict())

            # Stage 2: Risk Officer
            state.stage = ConferenceStage.RISK.value
            risk_opinion = await self.risk_officer.analyze(state)
            state.opinions.append(risk_opinion.to_dict())

            # Stage 3: Adversary
            state.stage = ConferenceStage.ADVERSARY.value
            adversary_opinion = await self.adversary.analyze(state)
            state.opinions.append(adversary_opinion.to_dict())

            # Stage 4: Consensus
            state.stage = ConferenceStage.CONSENSUS.value
            elapsed_ms = int((time.time() - start_time) * 1000)
            state.duration_ms = elapsed_ms

            result = await self.arbitrator.synthesize(state)
            result.duration_ms = elapsed_ms

            state.stage = ConferenceStage.COMPLETE.value
            state.add_transcript("Conference", f"=== Decision: {result.decision} (conf={result.confidence:.2f}) in {elapsed_ms}ms ===")

            log.info(
                "Conference %s for %s: %s (conf=%.2f) in %dms",
                session_id, symbol, result.decision, result.confidence, elapsed_ms
            )

        except Exception as e:
            log.error("Conference failed for %s: %s", symbol, e, exc_info=True)
            state.errors.append(str(e))
            result = ConferenceResult(
                session_id=session_id,
                symbol=symbol,
                decision=Decision.NO_TRADE.value,
                confidence=0.0,
                errors=state.errors,
                transcript=state.transcript,
            )

        return result

    async def convene_batch(
        self, symbols: List[str], **kwargs
    ) -> List[ConferenceResult]:
        """Run conferences for multiple symbols concurrently."""
        tasks = [self.convene(symbol=s, **kwargs) for s in symbols]
        return await asyncio.gather(*tasks, return_exceptions=False)


# ---------------------------------------------------------------------------
# FastAPI integration helper
# ---------------------------------------------------------------------------

def get_conference() -> TradingConference:
    """Factory for use in FastAPI dependency injection."""
    return TradingConference()
