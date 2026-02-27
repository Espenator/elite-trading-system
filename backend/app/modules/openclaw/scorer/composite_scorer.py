#!/usr/bin/env python3
"""
Composite Scorer for OpenClaw v5.0 - Tier 2 Scoring Agent
100-Point 5-Pillar Scoring System with Confidence Weighting

Swarm Integration (v5.0):
  - Subscribes to WHALE_SIGNALS from Tier 1 (whale_flow)
  - Publishes EXECUTION_ORDERS to Tier 3 (auto_executor)
  - Memory-weighted scoring (win rate feedback loop)
  - Async Blackboard consumer/publisher
  - Robust imports with try/except fallbacks

v2.2 Changes:
  - Expected Moves (FOM) integration for entry quality
  - Sector rotation momentum weighting
  - Weighted confidence calc (pillars weighted by importance)
  - Signal age decay penalty for stale setups
  - Safe numeric helpers to prevent type errors
  - Score quality metric (pillar agreement)
  - Memory win-rate feedback scales bonus dynamically

v2.0 Changes:
  - HMM regime confidence integration (scales regime pillar)
  - Adaptive thresholds per regime (tighter in YELLOW/RED)
  - Hurst-adjusted momentum scoring
  - Sector momentum weighting from rotation data
  - Score confidence output (how reliable is this score)

Pillars:
  1. Regime  (20 pts) - Market regime + HMM confidence
  2. Trend   (25 pts) - Trend strength & structure
  3. Pullback(25 pts) - Pullback quality & entry zone
  4. Momentum(20 pts) - Momentum confirmation + Hurst
  5. Pattern (10 pts) - Chart pattern & volume

Bonus/Penalty modifiers applied after base score.
  Threshold: 55+ = Tradeable, 70+ = High Conviction, 82+ = SLAM
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import asyncio

# Robust imports with graceful fallbacks
try:
  from streaming_engine import get_blackboard, BlackboardMessage, Topic
except ImportError:
  get_blackboard = None
  BlackboardMessage = None
  Topic = None

try:
  from memory import trade_memory
except ImportError:
  trade_memory = None

logger = logging.getLogger(__name__)


# ========== SAFE HELPERS ==========

def _safe_float(val, default: float = 0.0) -> float:
    """Safely convert any value to float, avoiding TypeError on None/str."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_bool(val, default: bool = False) -> bool:
    """Safely convert any value to bool."""
    if val is None:
        return default
    return bool(val)


# ========== THRESHOLDS ==========

SCORE_SLAM = 82
SCORE_HIGH = 70
SCORE_TRADEABLE = 55
SCORE_WATCH = 50

# Regime-adaptive thresholds
REGIME_THRESHOLDS = {
    "GREEN":  {"tradeable": 50, "high": 65, "slam": 78},
    "YELLOW": {"tradeable": 55, "high": 70, "slam": 82},
    "RED":    {"tradeable": 75, "high": 85, "slam": 92},
}

# Pillar weights for confidence calculation
PILLAR_WEIGHTS = {
    "regime": 0.20,
    "trend": 0.25,
    "pullback": 0.25,
    "momentum": 0.20,
    "pattern": 0.10,
}


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of a composite score."""
    ticker: str = ''
    regime_score: float = 0.0
    trend_score: float = 0.0
    pullback_score: float = 0.0
    momentum_score: float = 0.0
    pattern_score: float = 0.0
    em_score: float = 0.0
    bonus: float = 0.0
    penalty: float = 0.0
    total: float = 0.0
    tier: str = 'NO_TRADE'
    confidence: float = 0.0
    score_quality: float = 0.0
        kelly_edge: float = 0.0
    kelly_fraction: float = 0.0
    expected_value: float = 0.0
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'regime': self.regime_score,
            'trend': self.trend_score,
            'pullback': self.pullback_score,
            'momentum': self.momentum_score,
            'pattern': self.pattern_score,
            'em_score': self.em_score,
            'bonus': self.bonus,
            'penalty': self.penalty,
            'total': self.total,
            'tier': self.tier,
            'confidence': self.confidence,
            'score_quality': self.score_quality,
            'details': self.details,
        }

    def summary(self) -> str:
        return (
            f"{self.ticker}: {self.total:.0f}/100 [{self.tier}] "
            f"R:{self.regime_score:.0f} T:{self.trend_score:.0f} "
            f"P:{self.pullback_score:.0f} M:{self.momentum_score:.0f} "
            f"Pat:{self.pattern_score:.0f} EM:{self.em_score:.0f} "
            f"B/P:{self.bonus:+.0f}/{self.penalty:+.0f} "
            f"conf:{self.confidence:.0%} qual:{self.score_quality:.0%}"
        )


class CompositeScorer:
    """
    100-Point Composite Scoring Engine v2.2.
    HMM confidence, regime-adaptive thresholds, Hurst integration,
    Expected Moves scoring, and weighted confidence.
    """

    def __init__(self, regime_data=None, macro_data=None, hmm_data=None):
        self.regime_data = regime_data or {}
        self.macro_data = macro_data or {}
        self.hmm_data = hmm_data or {}
        self.regime = self.regime_data.get('regime', 'UNKNOWN')
        if isinstance(self.regime, dict):
            self.regime = self.regime.get('regime', 'UNKNOWN')

    def score_candidate(self, ticker: str, technicals: Dict,
                        whale_data: Optional[Dict] = None,
                        mtf_data: Optional[Dict] = None,
                        memory_data: Optional[Dict] = None) -> ScoreBreakdown:
        """Score a single candidate across all 5 pillars with confidence."""
        breakdown = ScoreBreakdown(ticker=ticker)

        breakdown.regime_score = self._score_regime()
        breakdown.trend_score = self._score_trend(technicals, mtf_data)
        breakdown.pullback_score = self._score_pullback(technicals)
        breakdown.momentum_score = self._score_momentum(technicals)
        breakdown.pattern_score = self._score_pattern(technicals)
        breakdown.em_score = self._score_expected_move(technicals)

        breakdown.bonus = self._calc_bonus(technicals, whale_data, memory_data)
        breakdown.penalty = self._calc_penalty(technicals)

        raw = (breakdown.regime_score + breakdown.trend_score +
               breakdown.pullback_score + breakdown.momentum_score +
               breakdown.pattern_score + breakdown.em_score +
               breakdown.bonus + breakdown.penalty)
        breakdown.total = max(0, min(100, raw))

        # Weighted confidence: each pillar's % of max, weighted by importance
        pillar_max = {"regime": 20, "trend": 25, "pullback": 25,
                      "momentum": 20, "pattern": 10}
        pillar_vals = {"regime": breakdown.regime_score,
                       "trend": breakdown.trend_score,
                       "pullback": breakdown.pullback_score,
                       "momentum": breakdown.momentum_score,
                       "pattern": breakdown.pattern_score}
        weighted_conf = 0.0
        for name, maxv in pillar_max.items():
            pct = pillar_vals[name] / maxv if maxv > 0 else 0
            weighted_conf += pct * PILLAR_WEIGHTS.get(name, 0.2)
        breakdown.confidence = min(1.0, weighted_conf)

        # HMM confidence boost
        hmm_conf = _safe_float(self.hmm_data.get('hmm_confidence', 0))
        if hmm_conf > 0.7:
            breakdown.confidence = min(1.0, breakdown.confidence + 0.1)

        # Score quality: how many pillars scored above 50% of their max
        strong = sum(1 for n, m in pillar_max.items()
                     if pillar_vals[n] >= m * 0.5)
        breakdown.score_quality = strong / len(pillar_max)

                # Kelly edge from composite score
        prob_up = min(0.95, max(0.30, 0.40 + (breakdown.total / 100) * 0.50))
        avg_win = 0.025 + (breakdown.total / 100) * 0.025
        avg_loss = 0.02 - (breakdown.total / 100) * 0.005
        b = avg_win / max(avg_loss, 0.001)
        edge = prob_up * b - (1 - prob_up)
        breakdown.kelly_edge = round(max(0, edge), 4)
        breakdown.kelly_fraction = round(max(0, edge / max(b, 0.001)) * 0.5, 4)
        breakdown.expected_value = round(edge * prob_up, 4) if edge > 0 else 0

        breakdown.tier = self._classify_tier(breakdown.total)
        breakdown.details = {
            'regime_data': self.regime_data,
            'hmm_confidence': hmm_conf,
            'hurst': _safe_float(self.hmm_data.get('hurst_exponent', 0.5)),
            'technicals_used': list(technicals.keys()),
            'pillar_pcts': {n: round(pillar_vals[n] / m * 100, 1)
                           for n, m in pillar_max.items() if m > 0},
        }

        logger.info(f"Scored {breakdown.summary()}")
        return breakdown

    # ========== PILLAR 1: REGIME (20 pts) ==========

    def _score_regime(self) -> float:
        score = 0.0
        regime = self.regime
        vix = _safe_float(self.macro_data.get('vix', 20), 20)
        hmm_conf = _safe_float(self.hmm_data.get('hmm_confidence', 0))

        if regime == 'GREEN':
            score += 15
        elif regime == 'YELLOW':
            score += 8
        elif regime == 'RED':
            score += 0
        elif regime == 'RED_RECOVERY':
            score += 5
        else:
            score += 5

        # VIX bonus
        if vix < 15:
            score += 5
        elif vix < 20:
            score += 3
        elif vix < 25:
            score += 1

        # Scale by HMM confidence (if available)
        if hmm_conf > 0:
            score = score * (0.7 + 0.3 * hmm_conf)

        return min(20, score)

    # ========== PILLAR 2: TREND (25 pts) ==========

    def _score_trend(self, tech: Dict, mtf: Optional[Dict] = None) -> float:
        score = 0.0
        price = _safe_float(tech.get('price', 0))
        sma_20 = _safe_float(tech.get('sma_20', 0))
        sma_200 = _safe_float(tech.get('sma_200', 0))
        ema_50 = _safe_float(tech.get('ema_50', 0))
        adx = _safe_float(tech.get('adx', 0))

        if price > 0 and sma_20 > 0 and price > sma_20:
            score += 5
        if price > 0 and sma_200 > 0 and price > sma_200:
            score += 5
        if sma_20 > 0 and sma_200 > 0 and sma_20 > sma_200:
            score += 3

        if adx >= 25:
            score += 5
        elif adx >= 20:
            score += 3
        elif adx >= 15:
            score += 1

        if price > 0 and ema_50 > 0 and price > ema_50:
            score += 2

        if mtf:
            mtf_score = _safe_float(mtf.get('alignment_score', 0))
            score += min(5, mtf_score)

        return min(25, score)

    # ========== PILLAR 3: PULLBACK (25 pts) ==========

    def _score_pullback(self, tech: Dict) -> float:
        score = 0.0
        williams_r = _safe_float(tech.get('williams_r', -50), -50)
        rsi = _safe_float(tech.get('rsi', 50), 50)
        price = _safe_float(tech.get('price', 0))
        sma_20 = _safe_float(tech.get('sma_20', 0))
        atr = _safe_float(tech.get('atr', 0))
        basing = _safe_bool(tech.get('basing', False))

        if williams_r <= -80:
            score += 10
        elif williams_r <= -60:
            score += 7
        elif williams_r <= -40:
            score += 4
        elif williams_r <= -20:
            score += 1

        if 30 <= rsi <= 45:
            score += 5
        elif 45 < rsi <= 55:
            score += 3
        elif 25 <= rsi < 30:
            score += 2

        if price > 0 and sma_20 > 0 and atr > 0:
            distance = abs(price - sma_20) / atr
            if distance <= 0.5:
                score += 5
            elif distance <= 1.0:
                score += 3
            elif distance <= 1.5:
                score += 1

        if basing:
            score += 5

        return min(25, score)

    # ========== PILLAR 4: MOMENTUM (20 pts) + Hurst ==========

    def _score_momentum(self, tech: Dict) -> float:
        score = 0.0
        macd_hist = _safe_float(tech.get('macd_hist', 0))
        rsi = _safe_float(tech.get('rsi', 50), 50)
        volume_ratio = _safe_float(tech.get('volume_ratio', 1.0), 1.0)
        price_change_5d = _safe_float(tech.get('price_change_5d', 0))

        if macd_hist > 0:
            score += 4
            if macd_hist > _safe_float(tech.get('macd_hist_prev', 0)):
                score += 2  # Accelerating MACD
        elif macd_hist < 0 and macd_hist > _safe_float(tech.get('macd_hist_prev', -999)):
            score += 2  # Recovering MACD

        if 50 <= rsi <= 65:
            score += 5
        elif 40 <= rsi < 50:
            score += 3
        elif 65 < rsi <= 75:
            score += 2

        if volume_ratio >= 2.0:
            score += 5
        elif volume_ratio >= 1.5:
            score += 4
        elif volume_ratio >= 1.2:
            score += 2
        elif volume_ratio >= 0.8:
            score += 1

        if 2 <= price_change_5d <= 8:
            score += 4
        elif 0 < price_change_5d < 2:
            score += 2
        elif price_change_5d > 8:
            score += 1  # Overextended = less momentum credit

        # Hurst bonus: trending market gets momentum boost
        hurst = _safe_float(self.hmm_data.get('hurst_exponent', 0.5), 0.5)
        if hurst > 0.55:
            score = score * 1.1  # 10% boost in trending
        elif hurst < 0.45:
            score = score * 0.9  # 10% reduction in mean-reverting

        return min(20, score)

    # ========== PILLAR 5: PATTERN (10 pts) ==========

    def _score_pattern(self, tech: Dict) -> float:
        score = 0.0

        if _safe_bool(tech.get('elephant_bar', False)):
            score += 3
        if _safe_bool(tech.get('channel_up', False)):
            score += 3
        if _safe_bool(tech.get('breakout', False)):
            score += 2
        if _safe_bool(tech.get('amd_detected', False)):
            score += 2

        return min(10, score)

    # ========== EXPECTED MOVE SCORING (bonus up to 5 pts) ==========

    def _score_expected_move(self, tech: Dict) -> float:
        """Score based on FOM expected move data if available.
        Rewards entries near expected move boundaries (high R:R zones).
        """
        em_data = tech.get('expected_move', {})
        if not em_data:
            return 0.0

        score = 0.0
        price = _safe_float(tech.get('price', 0))
        em_low = _safe_float(em_data.get('lower_bound', 0))
        em_high = _safe_float(em_data.get('upper_bound', 0))
        em_pct = _safe_float(em_data.get('move_pct', 0))

        if price > 0 and em_low > 0 and em_high > 0:
            em_range = em_high - em_low
            if em_range > 0:
                # Where is price within the expected move range?
                position = (price - em_low) / em_range
                # Best entries near the lower bound (0.0-0.3)
                if position <= 0.2:
                    score += 5  # Near lower EM bound = great entry
                elif position <= 0.4:
                    score += 3
                elif position <= 0.6:
                    score += 1
                # Above 0.6 = price near top of expected range, no bonus

        # Wider expected moves = more opportunity
        if em_pct >= 5.0:
            score += 0  # Already reflected in position scoring

        return min(5, score)

    # ========== BONUS MODIFIERS ==========

    def _calc_bonus(self, tech: Dict, whale: Optional[Dict] = None,
                    memory: Optional[Dict] = None) -> float:
        bonus = 0.0

        if whale:
            premium = _safe_float(whale.get('total_premium', 0))
            sentiment = whale.get('dominant_sentiment', '')
            if premium >= 500000 and sentiment == 'bullish':
                bonus += 3
            elif premium >= 100000 and sentiment == 'bullish':
                bonus += 1

        if _safe_bool(tech.get('sector_hot', False)):
            bonus += 2

        # Sector rotation momentum bonus
        sector_score = _safe_float(tech.get('sector_momentum', 0))
        if sector_score >= 0.7:
            bonus += 2
        elif sector_score >= 0.4:
            bonus += 1

        if memory:
            win_rate = _safe_float(memory.get('win_rate', 0))
            trade_count = _safe_float(memory.get('trade_count', 0))
            # Only trust memory with enough sample size
            if trade_count >= 3:
                if win_rate >= 0.7:
                    bonus += 3
                elif win_rate >= 0.5:
                    bonus += 1
                elif win_rate < 0.3:
                    bonus -= 2  # Negative memory feedback

        if _safe_bool(tech.get('earnings_safe', True)):
            bonus += 2

        return min(10, bonus)

    # ========== PENALTY MODIFIERS ==========

    def _calc_penalty(self, tech: Dict) -> float:
        penalty = 0.0

        rsi = _safe_float(tech.get('rsi', 50), 50)
        if rsi > 75:
            penalty -= 5

        vol = _safe_float(tech.get('volume_ratio', 1.0), 1.0)
        if vol < 0.5:
            penalty -= 3

        if not _safe_bool(tech.get('earnings_safe', True), True):
            penalty -= 5

        price = _safe_float(tech.get('price', 0))
        sma_200 = _safe_float(tech.get('sma_200', 0))
        if price > 0 and sma_200 > 0 and price < sma_200:
            penalty -= 2

        # RED regime extra penalty
        if self.regime == 'RED':
            penalty -= 5

        # Signal age decay: stale signals lose value
        signal_age_hours = _safe_float(tech.get('signal_age_hours', 0))
        if signal_age_hours > 48:
            penalty -= 3
        elif signal_age_hours > 24:
            penalty -= 1

        return max(-15, penalty)

    # ========== TIER CLASSIFICATION ==========

    def _classify_tier(self, score: float) -> str:
        """Classify with regime-adaptive thresholds."""
        thresholds = REGIME_THRESHOLDS.get(self.regime, {})
        slam = thresholds.get('slam', SCORE_SLAM)
        high = thresholds.get('high', SCORE_HIGH)
        tradeable = thresholds.get('tradeable', SCORE_TRADEABLE)

        if score >= slam:
            return 'SLAM'
        elif score >= high:
            return 'HIGH_CONVICTION'
        elif score >= tradeable:
            return 'TRADEABLE'
        elif score >= SCORE_WATCH:
            return 'WATCHLIST'
        else:
            return 'NO_TRADE'

    # ========== BATCH SCORING ==========

    def score_watchlist(self, candidates: List[Dict],
                        whale_map: Optional[Dict] = None,
                        memory_map: Optional[Dict] = None) -> List[ScoreBreakdown]:
        whale_map = whale_map or {}
        memory_map = memory_map or {}
        results = []

        for candidate in candidates:
            ticker = candidate.get('ticker', '')
            if not ticker:
                continue
            whale = whale_map.get(ticker)
            memory = memory_map.get(ticker)
            mtf = candidate.get('mtf_data')
            try:
                breakdown = self.score_candidate(
                    ticker=ticker, technicals=candidate,
                    whale_data=whale, mtf_data=mtf, memory_data=memory,
                )
                results.append(breakdown)
            except Exception as e:
                logger.error(f"Failed to score {ticker}: {e}")

        results.sort(key=lambda x: (x.total, x.confidence), reverse=True)
        return results

    def get_tradeable(self, results: List[ScoreBreakdown],
                      min_score: float = SCORE_TRADEABLE) -> List[ScoreBreakdown]:
        return [r for r in results if r.total >= min_score]

    def format_slack_message(self, results: List[ScoreBreakdown]) -> str:
        if not results:
            return ":chart_with_downwards_trend: No candidates scored above threshold."

        lines = [":robot_face: *OpenClaw Composite Scores v2.2*\n"]
        lines.append(f":bar_chart: Regime: *{self.regime}* | HMM conf: {_safe_float(self.hmm_data.get('hmm_confidence', 0)):.0%}\n")

        slams = [r for r in results if r.tier == 'SLAM']
        highs = [r for r in results if r.tier == 'HIGH_CONVICTION']
        trades = [r for r in results if r.tier == 'TRADEABLE']
        watches = [r for r in results if r.tier == 'WATCHLIST']

        if slams:
            lines.append(":fire: *SLAM TRADES:*")
            for s in slams:
                lines.append(f"  :star: *{s.ticker}* {s.total:.0f}/100 conf:{s.confidence:.0%} qual:{s.score_quality:.0%}")
            lines.append("")
        if highs:
            lines.append(":dart: *HIGH CONVICTION:*")
            for h in highs:
                lines.append(f"  *{h.ticker}* {h.total:.0f}/100 conf:{h.confidence:.0%} qual:{h.score_quality:.0%}")
            lines.append("")
        if trades:
            lines.append(":chart_with_upwards_trend: *TRADEABLE:*")
            for t in trades:
                lines.append(f"  {t.ticker} {t.total:.0f}/100 conf:{t.confidence:.0%}")
            lines.append("")
        if watches:
            lines.append(":eyes: *WATCHLIST:*")
            for w in watches[:5]:
                lines.append(f"  {w.ticker} {w.total:.0f}/100")

        return '\n'.join(lines)


# ========== MODULE-LEVEL CONVENIENCE ==========

def score_candidates(candidates: List[Dict], regime_data: Dict = None,
                     macro_data: Dict = None, hmm_data: Dict = None,
                     whale_map: Dict = None,
                     memory_map: Dict = None) -> List[ScoreBreakdown]:
    scorer = CompositeScorer(regime_data=regime_data, macro_data=macro_data,
                             hmm_data=hmm_data)
    return scorer.score_watchlist(candidates, whale_map, memory_map)


def get_tradeable_tickers(results: List[ScoreBreakdown],
                          min_score: float = SCORE_TRADEABLE) -> List[str]:
    return [r.ticker for r in results if r.total >= min_score]


# ========== LLM-ENHANCED SCORING (v2.1) ==========

def score_with_llm_rationale(candidates: List[Dict], regime_data: Dict = None,
                             macro_data: Dict = None, hmm_data: Dict = None,
                             whale_map: Dict = None,
                             memory_map: Dict = None) -> List[ScoreBreakdown]:
    """Score candidates and attach LLM trade rationale for top picks."""
    results = score_candidates(candidates, regime_data, macro_data,
                               hmm_data, whale_map, memory_map)

    # Attach LLM rationale to tradeable candidates
    try:
        from llm_client import get_llm
        llm = get_llm()
        status = llm.status()
        if not (status.get('local_available') or status.get('perplexity_available')):
            logger.info("[SCORER] No LLM backends available, skipping rationale")
            return results

        regime = (regime_data or {}).get('regime', 'UNKNOWN')
        if isinstance(regime, dict):
            regime = regime.get('regime', 'UNKNOWN')

        tradeable = [r for r in results if r.total >= SCORE_TRADEABLE]
        for breakdown in tradeable[:5]:  # Top 5 only to limit API calls
            try:
                score_data = breakdown.to_dict()
                rationale = llm.get_trade_rationale(
                    breakdown.ticker, score_data, regime
                )
                if rationale:
                    breakdown.details['llm_rationale'] = rationale
                    logger.info(f"[SCORER] LLM rationale for {breakdown.ticker}: {len(rationale)} chars")
            except Exception as e:
                logger.warning(f"[SCORER] LLM rationale failed for {breakdown.ticker}: {e}")
    except ImportError:
        logger.debug("[SCORER] llm_client not available")
    except Exception as e:
        logger.warning(f"[SCORER] LLM scoring enhancement failed: {e}")

    return results


# ========== BLACKBOARD PUB/SUB (v5.0 Tier 2) ==========

def _publish_execution_order(breakdown: ScoreBreakdown, blackboard=None,
                            entry_price: float = None,
                            stop_price: float = None) -> bool:
  """Publish a scored signal as EXECUTION_ORDER to Blackboard for Tier 3."""
  if not blackboard or not BlackboardMessage or not Topic:
    return False
  if breakdown.tier in ('NO_TRADE', 'WATCHLIST'):
    return False

  try:
    msg = BlackboardMessage(
      topic=Topic.EXECUTION_ORDERS,
      payload={
        'ticker': breakdown.ticker,
        'score': breakdown.total,
        'tier': breakdown.tier,
        'confidence': breakdown.confidence,
        'score_quality': breakdown.score_quality,
                        'kelly_edge': breakdown.kelly_edge,
                'kelly_fraction': breakdown.kelly_fraction,
                'expected_value': breakdown.expected_value,
        'trigger': f'composite_scorer_{breakdown.tier.lower()}',
        'regime': breakdown.details.get('regime_data', {}).get('regime', 'UNKNOWN'),
        'em_pct': breakdown.em_score,
        'entry_price': entry_price,
        'stop_price': stop_price,
        'breakdown': {
          'regime': breakdown.regime_score,
          'trend': breakdown.trend_score,
          'pullback': breakdown.pullback_score,
          'momentum': breakdown.momentum_score,
          'pattern': breakdown.pattern_score,
        },
      },
      source='composite_scorer',
    )
    blackboard.publish(msg)
    logger.info(f"[Scorer] Published EXECUTION_ORDER for {breakdown.ticker} "
                f"({breakdown.total:.0f}/100 {breakdown.tier})")
    return True
  except Exception as e:
    logger.warning(f"[Scorer] Failed to publish execution order: {e}")
    return False


async def async_blackboard_scorer(blackboard=None,
                                  regime_data: Dict = None,
                                  macro_data: Dict = None,
                                  hmm_data: Dict = None) -> None:
  """
  Tier 2 Blackboard consumer/publisher:
  - Subscribes to WHALE_SIGNALS from Tier 1
  - Scores each signal through the 5-pillar system
  - Publishes tradeable signals as EXECUTION_ORDERS to Tier 3
  """
  if not blackboard and get_blackboard:
    try:
      blackboard = get_blackboard()
    except Exception as e:
      logger.error(f"[Scorer] Failed to get Blackboard: {e}")
      return

  if not blackboard:
    logger.warning("[Scorer] No Blackboard available")
    return

  scorer = CompositeScorer(
    regime_data=regime_data or {},
    macro_data=macro_data or {},
    hmm_data=hmm_data or {},
  )

  signals_scored = 0
  orders_published = 0

  async def _handle_whale_signal(msg):
    nonlocal signals_scored, orders_published
    try:
      payload = msg.payload if hasattr(msg, 'payload') else msg
      ticker = payload.get('ticker')
      if not ticker:
        return

      logger.info(f"[Scorer] Received whale signal for {ticker}")

      # Build technicals dict from whale signal payload
      technicals = {
        'ticker': ticker,
        'premium': payload.get('premium', 0),
        'sentiment': payload.get('sentiment', 'neutral'),
        'trade_type': payload.get('trade_type', 'unknown'),
      }

      # Get memory data for this ticker if available
      memory_data = None
      if trade_memory:
        try:
          memory_data = trade_memory.get_ticker_stats(ticker)
        except Exception:
          pass

      # Build whale data for scoring
      whale_data = {
        'has_whale_flow': True,
        'total_premium': payload.get('premium', 0),
        'dominant_sentiment': payload.get('sentiment', 'neutral'),
        'has_sweep': payload.get('trade_type') == 'sweep',
        'has_block': payload.get('trade_type') == 'block',
      }

      # Score through 5-pillar system
      memory_map = {ticker: memory_data} if memory_data else None
      breakdown = scorer.score_candidate(
        ticker=ticker,
        technicals=technicals,
        whale_data=whale_data,
        memory_data=memory_data,
      )
      signals_scored += 1

      # Publish tradeable signals to Tier 3
      if breakdown.total >= SCORE_TRADEABLE:
        published = _publish_execution_order(breakdown, blackboard=blackboard)
        if published:
          orders_published += 1

      logger.info(
        f"[Scorer] {ticker}: {breakdown.total:.0f}/100 [{breakdown.tier}] "
        f"(scored: {signals_scored}, published: {orders_published})"
      )

    except Exception as e:
      logger.error(f"[Scorer] Blackboard handler error: {e}")

  # Subscribe to whale signals
  if hasattr(blackboard, 'subscribe'):
    try:
      if Topic:
        blackboard.subscribe(Topic.WHALE_SIGNALS, _handle_whale_signal)
      else:
        blackboard.subscribe('whale_signals', _handle_whale_signal)
      logger.info("[Scorer] Subscribed to WHALE_SIGNALS on Blackboard")
    except Exception as e:
      logger.error(f"[Scorer] Failed to subscribe: {e}")

  # Keep consumer alive
  while True:
    await asyncio.sleep(1)


async def run(mode: str = "blackboard",
              regime_data: Dict = None,
              macro_data: Dict = None,
              hmm_data: Dict = None) -> None:
  """
  Main async entry point for the Tier 2 scoring agent.
  Modes:
    blackboard: Subscribe to Blackboard and score whale signals
    standalone: Run without Blackboard (legacy mode)
  """
  logger.info(f"[Scorer] Starting Tier 2 Scoring Agent (mode={mode})")

  if mode == "blackboard" and get_blackboard:
    await async_blackboard_scorer(
      regime_data=regime_data,
      macro_data=macro_data,
      hmm_data=hmm_data,
    )
  else:
    logger.info("[Scorer] Standalone mode - use score_candidates() directly")
    while True:
      await asyncio.sleep(60)


# ========== CLI ENTRY POINT ==========

if __name__ == '__main__':
  import argparse

  parser = argparse.ArgumentParser(
    description='OpenClaw Tier 2 Composite Scorer'
  )
  parser.add_argument(
    '--mode',
    choices=['blackboard', 'standalone'],
    default='blackboard',
    help='Run mode: blackboard (subscribe/publish) or standalone',
  )
  args = parser.parse_args()

  logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
  )

  try:
    asyncio.run(run(mode=args.mode))
  except KeyboardInterrupt:
    logger.info("[Scorer] Shutting down gracefully...")
  except Exception as e:
    logger.error(f"[Scorer] Fatal error: {e}")
    raise

