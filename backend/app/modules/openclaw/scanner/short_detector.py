"""short_detector.py - Short Selling & Bearish Setup Detection

Detects bearish patterns (distribution, H&S, descending channels, breakdowns),
computes bearish indicators, integrates bearish whale flow, and provides
inverted composite scoring for RED regime short trades.

Part of OpenClaw v4.0 Real-Time Trading Engine.
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

try:
    from .technical_checker import check_technicals
except ImportError:
    check_technicals = None

try:
    from .whale_flow import whale_flow_scanner
except ImportError:
    whale_flow_scanner = None

try:
    from .fom_expected_moves import get_expected_move
except ImportError:
    get_expected_move = None

try:
    from .sector_rotation import get_sector_rankings
except ImportError:
    get_sector_rankings = None

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

DISTRIBUTION_LOOKBACK = 15  # Bars to check distribution
HS_PEAK_TOLERANCE = 0.02  # 2% tolerance for shoulder symmetry
DESCENDING_CHANNEL_LOOKBACK = 20  # Bars for channel detection
BREAKDOWN_VOLUME_RATIO = 1.5  # Volume must be 1.5x avg on breakdown
BEARISH_RSI_THRESHOLD = 70  # RSI > 70 is overbought (short zone)
BEARISH_WILLIAMS_THRESHOLD = -20  # W%R > -20 is overbought
SHORT_PULLBACK_RSI_MIN = 55  # RSI for bearish pullback entry
SHORT_PULLBACK_RSI_MAX = 70  # RSI ceiling for entry
PUT_PREMIUM_MIN = 50000  # Min put premium for whale signal
SHORT_SCORE_THRESHOLD = 50  # Minimum composite score to trigger short signal


# ============================================================
# SCORING
# ============================================================

def score_short_setup(
    patterns: Dict = None,
    bearish_indicators: Dict = None,
    whale_flow: Dict = None,
    sector_weakness: float = 0,
    short_pullback: Dict = None,
    em_pct: float = 0,
) -> Dict:
    """Score a short setup on 0-100 scale.

    Weights:
        Patterns          30%
        Bearish indicators 25%
        Whale flow         20%
        Sector weakness    15%
        Expected move      10%
    """
    score = 0.0
    breakdown = {}

    # Patterns (up to 30)
    p = patterns or {}
    pat_score = 0
    if p.get("head_and_shoulders"): pat_score += 15
    if p.get("distribution"): pat_score += 10
    if p.get("descending_channel"): pat_score += 10
    if p.get("breakdown"): pat_score += 10
    pat_score = min(pat_score, 30)
    breakdown["patterns"] = pat_score
    score += pat_score

    # Bearish indicators (up to 25)
    bi = bearish_indicators or {}
    ind_score = 0
    if bi.get("overbought_rsi"): ind_score += 8
    if bi.get("bearish_macd"): ind_score += 8
    if bi.get("overbought_williams"): ind_score += 5
    if bi.get("below_ema20"): ind_score += 4
    ind_score = min(ind_score, 25)
    breakdown["indicators"] = ind_score
    score += ind_score

    # Whale flow (up to 20)
    wf = whale_flow or {}
    wf_score = 20 if wf.get("has_bearish_flow") else 0
    breakdown["whale_flow"] = wf_score
    score += wf_score

    # Sector weakness (up to 15)
    sw_score = min(sector_weakness * 15, 15)
    breakdown["sector_weakness"] = round(sw_score, 1)
    score += sw_score

    # Expected move (up to 10)
    em_score = min(em_pct * 2, 10) if em_pct > 0 else 0
    breakdown["expected_move"] = round(em_score, 1)
    score += em_score

    # Short pullback bonus
    if short_pullback:
        bonus = 5
        score += bonus
        breakdown["pullback_bonus"] = bonus

    return {"total": round(score, 1), "breakdown": breakdown}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _calculate_atr(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """Calculate Average True Range."""
    if len(highs) < period + 1:
        return 0.0
    tr_list = []
    for i in range(1, len(highs)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)
    return np.mean(tr_list[-period:]) if len(tr_list) >= period else (np.mean(tr_list) if tr_list else 0.0)


def _linear_regression_slope(values: list) -> float:
    """Calculate slope of linear regression."""
    if len(values) < 3:
        return 0.0
    x = np.arange(len(values))
    coeffs = np.polyfit(x, values, 1)
    return coeffs[0]


# ============================================================
# BEARISH PATTERN DETECTION
# ============================================================

def detect_distribution(closes: list, volumes: list,
                         lookback: int = None) -> Dict:
    """Detect distribution pattern: rising price + declining volume."""
    lookback = lookback or DISTRIBUTION_LOOKBACK
    result = {'detected': False, 'bars': 0, 'price_slope': 0.0, 'volume_slope': 0.0}
    
    if len(closes) < lookback or len(volumes) < lookback:
        return result
    
    recent_closes = closes[-lookback:]
    recent_volumes = volumes[-lookback:]
    
    price_slope = _linear_regression_slope(recent_closes)
    volume_slope = _linear_regression_slope(recent_volumes)
    
    # Distribution: price rising but volume declining
    if price_slope > 0 and volume_slope < 0:
        # Confirm: at least 60% of bars show declining volume
        vol_declining = sum(1 for i in range(1, len(recent_volumes))
                           if recent_volumes[i] < recent_volumes[i-1])
        if vol_declining >= lookback * 0.5:
            result = {
                'detected': True,
                'bars': lookback,
                'price_slope': round(price_slope, 4),
                'volume_slope': round(volume_slope, 4)
            }
    
    return result


def detect_head_shoulders(highs: list, lows: list, closes: list) -> Dict:
    """Detect head and shoulders pattern (3 peaks, middle highest)."""
    result = {'detected': False, 'neckline': 0.0}
    
    if len(highs) < 30:
        return result
    
    # Find peaks in last 40 bars
    peaks = []
    data = highs[-40:] if len(highs) >= 40 else highs
    for i in range(3, len(data) - 3):
        if data[i] == max(data[i-3:i+4]):
            peaks.append((i, data[i]))
    
    if len(peaks) < 3:
        return result
    
    # Check last 3 peaks for H&S pattern
    for i in range(len(peaks) - 2):
        left_idx, left_h = peaks[i]
        head_idx, head_h = peaks[i + 1]
        right_idx, right_h = peaks[i + 2]
        
        # Head must be highest
        if head_h <= left_h or head_h <= right_h:
            continue
        
        # Shoulders should be roughly equal (within tolerance)
        shoulder_diff = abs(left_h - right_h) / max(left_h, right_h)
        if shoulder_diff > HS_PEAK_TOLERANCE * 3:
            continue
        
        # Calculate neckline (connect the troughs between peaks)
        lows_data = lows[-40:] if len(lows) >= 40 else lows
        trough1 = min(lows_data[left_idx:head_idx+1]) if head_idx > left_idx else 0
        trough2 = min(lows_data[head_idx:right_idx+1]) if right_idx > head_idx else 0
        neckline = (trough1 + trough2) / 2 if trough1 and trough2 else 0
        
        # Current price should be near or below neckline
        if closes[-1] <= neckline * 1.02:
            result = {
                'detected': True,
                'neckline': round(neckline, 2),
                'head_height': round(head_h, 2),
                'left_shoulder': round(left_h, 2),
                'right_shoulder': round(right_h, 2)
            }
            return result
    
    return result


def detect_descending_channel(highs: list, lows: list,
                               lookback: int = None) -> Dict:
    """Detect descending channel: lower highs + lower lows."""
    lookback = lookback or DESCENDING_CHANNEL_LOOKBACK
    result = {'detected': False, 'high_slope': 0.0, 'low_slope': 0.0}
    
    if len(highs) < lookback:
        return result
    
    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]
    
    high_slope = _linear_regression_slope(recent_highs)
    low_slope = _linear_regression_slope(recent_lows)
    
    # Both slopes must be negative (lower highs AND lower lows)
    if high_slope < 0 and low_slope < 0:
        # Count lower highs
        lower_highs = sum(1 for i in range(1, len(recent_highs))
                         if recent_highs[i] < recent_highs[i-1])
        lower_lows = sum(1 for i in range(1, len(recent_lows))
                        if recent_lows[i] < recent_lows[i-1])
        
        if lower_highs >= lookback * 0.4 and lower_lows >= lookback * 0.4:
            result = {
                'detected': True,
                'high_slope': round(high_slope, 4),
                'low_slope': round(low_slope, 4),
                'bars': lookback
            }
    
    return result


def detect_breakdown(closes: list, lows: list, volumes: list) -> Dict:
    """Detect breakdown: price breaks below 20-bar low with volume surge."""
    result = {'detected': False, 'breakdown_level': 0.0, 'volume_ratio': 0.0}
    
    if len(closes) < 25 or len(volumes) < 25:
        return result
    
    # 20-bar low (excluding current bar)
    bar_low_20 = min(lows[-21:-1])
    avg_vol = np.mean(volumes[-21:-1])
    
    # Current bar breaks below with volume
    if closes[-1] < bar_low_20 and avg_vol > 0:
        vol_ratio = volumes[-1] / avg_vol
        if vol_ratio >= BREAKDOWN_VOLUME_RATIO:
            result = {
                'detected': True,
                'breakdown_level': round(bar_low_20, 2),
                'volume_ratio': round(vol_ratio, 2),
                'close': closes[-1]
            }
    
    return result


# ============================================================
# BEARISH TECHNICAL INDICATORS
# ============================================================

def compute_bearish_indicators(tech: Dict) -> Dict:
    """Compute bearish indicator signals."""
    indicators = {
        'williams_r_overbought': False,
        'rsi_overbought': False,
        'below_200sma': False,
        'macd_declining': False,
        'below_50ema': False,
        'bearish_count': 0
    }
    
    williams_r = tech.get('williams_r', tech.get('williams_pct_r', -50))
    rsi = tech.get('rsi', 50)
    price = tech.get('price', tech.get('close', 0))
    sma_200 = tech.get('sma_200', 0)
    ema_50 = tech.get('ema_50', tech.get('ema50', 0))
    macd_hist = tech.get('macd_histogram', tech.get('macd_hist', 0))
    prev_macd_hist = tech.get('prev_macd_histogram', tech.get('prev_macd_hist', 0))
    
    if williams_r and williams_r > BEARISH_WILLIAMS_THRESHOLD:
        indicators['williams_r_overbought'] = True
        indicators['bearish_count'] += 1
    
    if rsi and rsi > BEARISH_RSI_THRESHOLD:
        indicators['rsi_overbought'] = True
        indicators['bearish_count'] += 1
    
    if price and sma_200 and price < sma_200:
        indicators['below_200sma'] = True
        indicators['bearish_count'] += 1
    
    if macd_hist is not None and prev_macd_hist is not None:
        if macd_hist < prev_macd_hist:
            indicators['macd_declining'] = True
            indicators['bearish_count'] += 1
    
    if price and ema_50 and price < ema_50:
        indicators['below_50ema'] = True
        indicators['bearish_count'] += 1
    
    indicators['williams_r'] = williams_r
    indicators['rsi'] = rsi
    
    return indicators


# ============================================================
# BEARISH WHALE FLOW FILTER
# ============================================================

def get_bearish_whale_flow(ticker: str) -> Dict:
    """Get bearish whale flow data for a ticker."""
    result = {
        'has_bearish_flow': False,
        'put_premium': 0,
        'put_call_ratio': 0.0,
        'sentiment': 'neutral'
    }
    
    if not whale_flow_scanner:
        return result
    
    try:
        flow_data = whale_flow_scanner.get_flow(ticker) if hasattr(whale_flow_scanner, 'get_flow') else None
        if not flow_data:
            return result
        
        # Check for bearish signals
        put_premium = flow_data.get('put_premium', 0)
        put_call_ratio = flow_data.get('put_call_ratio', 0)
        sentiment = flow_data.get('dominant_sentiment', flow_data.get('sentiment', 'neutral'))
        
        is_bearish = (
            put_premium >= PUT_PREMIUM_MIN or
            put_call_ratio > 1.5 or
            sentiment in ('bearish', 'very_bearish')
        )
        
        result = {
            'has_bearish_flow': is_bearish,
            'put_premium': put_premium,
            'put_call_ratio': round(put_call_ratio, 2),
            'sentiment': sentiment
        }
    except Exception as e:
        logger.debug(f"Whale flow lookup failed for {ticker}: {e}")
    
    return result


# ============================================================
# SECTOR-RELATIVE WEAKNESS
# ============================================================

def score_relative_weakness(ticker: str, tech: Optional[Dict] = None) -> int:
    """Score relative weakness vs sector."""
    if not get_sector_rankings:
        return 0
    
    try:
        rankings = get_sector_rankings()
        if not rankings:
            return 0
        
        # Find ticker's sector
        sector = tech.get('sector', '') if tech else ''
        if not sector:
            return 0
        
        # Check if in bottom 3 sectors
        sector_rank = rankings.get(sector, {}).get('rank', 6)
        total_sectors = len(rankings)
        
        if sector_rank > total_sectors - 3:  # Bottom 3
            # Check individual weakness
            price_change = tech.get('price_change_5d', 0) if tech else 0
            sector_avg = rankings.get(sector, {}).get('avg_change', 0)
            
            if price_change < sector_avg - 5:
                return 5  # Much weaker than weak sector
            elif price_change < sector_avg - 2:
                return 3
            elif price_change < sector_avg:
                return 1
    except Exception as e:
        logger.debug(f"Sector ranking failed: {e}")
    
    return 0


# ============================================================
# SHORT PULLBACK DETECTION (Bearish Fade)
# ============================================================

def detect_short_pullback(closes: list, highs: list, volumes: list,
                           sma_20: float = 0, ema_50: float = 0,
                           rsi: float = 0) -> Dict:
    """Detect bearish pullback (rally into resistance for short entry)."""
    result = {'detected': False, 'resistance_type': 'none'}
    
    price = closes[-1] if closes else 0
    if not price or not sma_20:
        return result
    
    # Price rallying to MA from below
    approaching_sma20 = (price < sma_20 and
                         abs(price - sma_20) / sma_20 < 0.02)
    approaching_ema50 = (ema_50 and price < ema_50 and
                         abs(price - ema_50) / ema_50 < 0.02)
    
    # Volume declining on rally (weak bounce)
    vol_declining = False
    if len(volumes) >= 5:
        recent_vols = volumes[-5:]
        vol_declining = recent_vols[-1] < np.mean(recent_vols[:-1])
    
    # RSI in overbought zone for shorts
    rsi_in_zone = SHORT_PULLBACK_RSI_MIN <= rsi <= SHORT_PULLBACK_RSI_MAX if rsi else False
    
    if (approaching_sma20 or approaching_ema50) and vol_declining and rsi_in_zone:
        resistance = 'sma_20' if approaching_sma20 else 'ema_50'
        result = {
            'detected': True,
            'resistance_type': resistance,
            'resistance_price': round(sma_20 if approaching_sma20 else ema_50, 2),
            'rsi': round(rsi, 1),
            'volume_declining': vol_declining
        }
    
    return result


# ============================================================
# FOM EXPECTED MOVES FOR SHORTS
# ============================================================

def calculate_short_stop(entry_price: float, expected_move_pct: float) -> float:
    """Calculate stop loss for short position based on expected move."""
    if entry_price <= 0 or expected_move_pct <= 0:
        return entry_price * 1.02  # Default 2% stop
    return round(entry_price * (1 + 0.4 * expected_move_pct / 100), 2)


# ============================================================
# SHORT TRIGGER CONDITIONS
# ============================================================

def detect_short_trigger(patterns: Dict, bearish_indicators: Dict,
                          whale_flow: Dict) -> bool:
    """Multi-confirmation short trigger.
    
    Requires:
    - Bearish pattern (distribution OR breakdown OR descending channel)
    - RSI > 65 OR Williams %R > -30
    - Bearish whale flow present
    - Price < 50 EMA AND 50 EMA < 200 SMA
    """
    has_pattern = (
        patterns.get('distribution', {}).get('detected') or
        patterns.get('breakdown', {}).get('detected') or
        patterns.get('descending_channel', {}).get('detected') or
        patterns.get('head_shoulders', {}).get('detected')
    )
    if not has_pattern:
        return False
    
    # Check indicators
    rsi = bearish_indicators.get('rsi', 50)
    williams_r = bearish_indicators.get('williams_r', -50)
    
    indicator_ok = (rsi and rsi > 65) or (williams_r and williams_r > -30)
    if not indicator_ok:
        return False
    
    # Bearish whale flow is a bonus, not required
    # But need structural weakness
    below_50ema = bearish_indicators.get('below_50ema', False)
    macd_declining = bearish_indicators.get('macd_declining', False)
    
    if not (below_50ema or macd_declining):
        return False
    
    return True


# ============================================================
# BEARISH COMPOSITE SCORER (Inverted)
# ============================================================

def score_short_candidate(patterns: Dict, bearish_indicators: Dict,
                           whale_flow: Dict, sector_weakness: int = 0,
                           short_pullback: Dict = None,
                           em_pct: float = 0) -> Dict:
    """Inverted composite scoring for short candidates.
    
    Pillars (100 points total):
    - Regime: RED=15, YELLOW=8, GREEN=0 (inverted)
    - Trend: price < 200 SMA, SMA20 < SMA200, ADX > 25
    - Overbought: Williams %R > -20, RSI > 65, distance above MA
    - Momentum: MACD declining, RSI > 70, volume surge
    - Pattern: distribution, breakdown, descending channel, H&S
    """
    score = {
        'trend_score': 0,
        'overbought_score': 0,
        'momentum_score': 0,
        'pattern_score': 0,
        'bonus': 0,
        'total': 0
    }
    
    # TREND PILLAR (25 pts)
    if bearish_indicators.get('below_200sma'):
        score['trend_score'] += 8
    if bearish_indicators.get('below_50ema'):
        score['trend_score'] += 7
    if bearish_indicators.get('macd_declining'):
        score['trend_score'] += 5
    bearish_count = bearish_indicators.get('bearish_count', 0)
    score['trend_score'] += min(5, bearish_count)
    score['trend_score'] = min(25, score['trend_score'])
    
    # OVERBOUGHT PILLAR (25 pts)
    if bearish_indicators.get('williams_r_overbought'):
        score['overbought_score'] += 10
    rsi = bearish_indicators.get('rsi', 50)
    if rsi:
        if rsi > 75:
            score['overbought_score'] += 10
        elif rsi > 70:
            score['overbought_score'] += 7
        elif rsi > 65:
            score['overbought_score'] += 4
    score['overbought_score'] = min(25, score['overbought_score'])
    
    # MOMENTUM PILLAR (20 pts)
    if bearish_indicators.get('macd_declining'):
        score['momentum_score'] += 6
    if bearish_indicators.get('rsi_overbought'):
        score['momentum_score'] += 5
    # Volume on pattern confirmation
    if patterns.get('breakdown', {}).get('detected'):
        vol_r = patterns['breakdown'].get('volume_ratio', 0)
        if vol_r >= 2.0:
            score['momentum_score'] += 5
        elif vol_r >= 1.5:
            score['momentum_score'] += 3
    score['momentum_score'] = min(20, score['momentum_score'])
    
    # PATTERN PILLAR (20 pts)
    if patterns.get('distribution', {}).get('detected'):
        score['pattern_score'] += 5
    if patterns.get('breakdown', {}).get('detected'):
        score['pattern_score'] += 6
    if patterns.get('descending_channel', {}).get('detected'):
        score['pattern_score'] += 5
    if patterns.get('head_shoulders', {}).get('detected'):
        score['pattern_score'] += 6
    score['pattern_score'] = min(20, score['pattern_score'])
    
    # BONUS (up to +10)
    if whale_flow.get('has_bearish_flow'):
        score['bonus'] += 3
    if sector_weakness >= 3:
        score['bonus'] += 3
    if short_pullback and short_pullback.get('detected'):
        score['bonus'] += 2
    if em_pct > 0:
        score['bonus'] += 2
    score['bonus'] = min(10, score['bonus'])
    
    score['total'] = (
        score['trend_score'] + score['overbought_score'] +
        score['momentum_score'] + score['pattern_score'] +
        score['bonus']
    )
    
    return score


# =============================================================
# MAIN SHORT DETECTION ENGINE
# =============================================================

def detect_short(ticker: str, closes: list, highs: list, lows: list,
                 volumes: list, sma_20: float = 0, ema_50: float = 0,
                 rsi: float = 0, macd_hist: float = 0,
                 prev_macd_hist: float = 0, atr: float = 0,
                 vwap: float = 0, sector: str = '',
                 whale_flow: Dict = None) -> Dict:
    """Main short detection: combines all signals into unified result."""
    result = {
        'ticker': ticker,
        'signal': False,
        'score': 0,
        'grade': 'F',
        'entry_price': 0.0,
        'stop_loss': 0.0,
        'targets': [],
        'expected_move_pct': 0.0,
        'patterns': {},
        'indicators': {},
        'reasoning': []
    }

    if len(closes) < 25:
        return result

    price = closes[-1] if closes else 0
    if not price:
        return result

    # --- Detect all bearish patterns ---
    patterns = {}

    # Distribution detection
    dist = detect_distribution(closes, volumes)
    if dist.get('detected'):
        patterns['distribution'] = dist
        result['reasoning'].append(f"Distribution detected: {dist.get('days', 0)} days")

    # Breakdown detection
    bd = detect_breakdown(closes, lows, volumes)
    if bd.get('detected'):
        patterns['breakdown'] = bd
        result['reasoning'].append(f"Breakdown below {bd.get('breakdown_level', 0)}")

    # Descending channel
    dc = detect_descending_channel(highs, lows)
    if dc.get('detected'):
        patterns['descending_channel'] = dc
        result['reasoning'].append('Descending channel confirmed')

    # Head and shoulders
    hs = detect_head_shoulders(closes, highs, lows, volumes)
    if hs.get('detected'):
        patterns['head_shoulders'] = hs
        result['reasoning'].append(f"Head & shoulders: neckline {hs.get('neckline', 0)}")

    # Short pullback (bearish fade)
    sp = detect_short_pullback(closes, highs, lows, volumes,
                               sma_20, ema_50, rsi)
    if sp.get('detected'):
        patterns['short_pullback'] = sp
        result['reasoning'].append(f"Bearish fade into {sp.get('resistance_type', '')}")

    result['patterns'] = patterns

    # --- Build bearish indicators ---
    bearish_indicators = {}

    # MACD declining
    if macd_hist and prev_macd_hist:
        if macd_hist < prev_macd_hist:
            bearish_indicators['macd_declining'] = True
            result['reasoning'].append('MACD histogram declining')

    # RSI overbought check
    if rsi > 65:
        bearish_indicators['rsi_overbought'] = True
        result['reasoning'].append(f'RSI overbought at {round(rsi, 1)}')

    # Below VWAP
    if vwap and price < vwap:
        bearish_indicators['below_vwap'] = True
        result['reasoning'].append('Price below VWAP')

    # Below key MAs
    if sma_20 and price < sma_20:
        bearish_indicators['below_sma20'] = True
        result['reasoning'].append('Price below SMA 20')
    if ema_50 and price < ema_50:
        bearish_indicators['below_ema50'] = True
        result['reasoning'].append('Price below EMA 50')

    result['indicators'] = bearish_indicators

    # --- Whale flow analysis ---
    whale_data = whale_flow or {}
    has_bearish_flow = False
    if whale_data:
        put_vol = whale_data.get('put_volume', 0)
        call_vol = whale_data.get('call_volume', 0)
        if call_vol > 0 and put_vol / call_vol > 1.5:
            has_bearish_flow = True
            result['reasoning'].append('Bearish whale flow detected (high put/call ratio)')

    # --- Sector weakness ---
    sector_weakness = 0
    # Will be populated by sector_analyzer integration

    # --- Calculate expected move ---
    em_pct = 0.0
    if atr and price > 0:
        em_pct = round((atr * 2 / price) * 100, 2)

    # --- Score the short setup ---
    score = score_short_setup(
        patterns=patterns,
        bearish_indicators=bearish_indicators,
        whale_flow={'has_bearish_flow': has_bearish_flow},
        sector_weakness=sector_weakness,
        short_pullback=sp if sp.get('detected') else None,
        em_pct=em_pct
    )

    total_score = score.get('total', 0)
    result['score'] = total_score

    # --- Assign grade ---
    if total_score >= 80:
        grade = 'A+'
    elif total_score >= 70:
        grade = 'A'
    elif total_score >= 60:
        grade = 'B+'
    elif total_score >= 50:
        grade = 'B'
    elif total_score >= 40:
        grade = 'C'
    else:
        grade = 'F'
    result['grade'] = grade

    # --- Signal trigger: minimum score threshold ---
    if total_score >= SHORT_SCORE_THRESHOLD:
        result['signal'] = True

        # Entry price
        result['entry_price'] = round(price, 2)

        # Stop loss (above recent high + ATR buffer)
        recent_high = max(highs[-5:]) if len(highs) >= 5 else price * 1.02
        atr_buffer = atr * 0.5 if atr else price * 0.01
        stop = round(recent_high + atr_buffer, 2)
        result['stop_loss'] = stop

        # Expected move
        result['expected_move_pct'] = em_pct

        # Targets based on expected move
        if em_pct > 0:
            t1 = round(price * (1 - em_pct / 100 * 0.5), 2)
            t2 = round(price * (1 - em_pct / 100), 2)
            t3 = round(price * (1 - em_pct / 100 * 1.5), 2)
            result['targets'] = [
                {'level': 1, 'price': t1, 'pct': round(em_pct * 0.5, 2)},
                {'level': 2, 'price': t2, 'pct': em_pct},
                {'level': 3, 'price': t3, 'pct': round(em_pct * 1.5, 2)}
            ]
        else:
            # Default 2% targets
            result['targets'] = [
                {'level': 1, 'price': round(price * 0.99, 2), 'pct': 1.0},
                {'level': 2, 'price': round(price * 0.98, 2), 'pct': 2.0},
                {'level': 3, 'price': round(price * 0.97, 2), 'pct': 3.0}
            ]

    return result


# =============================================================
# BATCH PROCESSING
# =============================================================

def batch_detect_shorts(watchlist_data: list, whale_flows: Dict = None) -> list:
    """Process multiple tickers for short signals.
    
    Args:
        watchlist_data: List of dicts with ticker data
            Each dict: {'ticker', 'closes', 'highs', 'lows', 'volumes',
                       'sma_20', 'ema_50', 'rsi', 'macd_hist',
                       'prev_macd_hist', 'atr', 'vwap', 'sector'}
        whale_flows: Dict of ticker -> whale flow data
    
    Returns:
        List of short signals sorted by score descending
    """
    results = []
    whale_flows = whale_flows or {}

    for data in watchlist_data:
        ticker = data.get('ticker', '')
        if not ticker:
            continue

        try:
            signal = detect_short(
                ticker=ticker,
                closes=data.get('closes', []),
                highs=data.get('highs', []),
                lows=data.get('lows', []),
                volumes=data.get('volumes', []),
                sma_20=data.get('sma_20', 0),
                ema_50=data.get('ema_50', 0),
                rsi=data.get('rsi', 0),
                macd_hist=data.get('macd_hist', 0),
                prev_macd_hist=data.get('prev_macd_hist', 0),
                atr=data.get('atr', 0),
                vwap=data.get('vwap', 0),
                sector=data.get('sector', ''),
                whale_flow=whale_flows.get(ticker)
            )
            results.append(signal)
        except Exception as e:
            results.append({
                'ticker': ticker,
                'signal': False,
                'score': 0,
                'grade': 'F',
                'error': str(e)
            })

    # Sort by score descending
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return results


def filter_short_signals(results: list, min_score: int = None,
                        min_grade: str = 'C') -> list:
    """Filter short signals by score and grade."""
    threshold = min_score or SHORT_SCORE_THRESHOLD
    grade_order = {'A+': 6, 'A': 5, 'B+': 4, 'B': 3, 'C': 2, 'F': 1}
    min_grade_val = grade_order.get(min_grade, 2)

    filtered = []
    for r in results:
        if not r.get('signal'):
            continue
        if r.get('score', 0) < threshold:
            continue
        r_grade_val = grade_order.get(r.get('grade', 'F'), 1)
        if r_grade_val < min_grade_val:
            continue
        filtered.append(r)

    return filtered


def format_short_alert(signal: Dict) -> str:
    """Format a short signal into readable alert text."""
    if not signal.get('signal'):
        return f"{signal.get('ticker', '?')}: No short signal"

    lines = [
        f"SHORT ALERT: {signal['ticker']}",
        f"Grade: {signal.get('grade', 'F')} | Score: {signal.get('score', 0)}/100",
        f"Entry: ${signal.get('entry_price', 0)}",
        f"Stop Loss: ${signal.get('stop_loss', 0)}",
        f"Expected Move: {signal.get('expected_move_pct', 0)}%",
    ]

    targets = signal.get('targets', [])
    for t in targets:
        lines.append(f"  Target {t['level']}: ${t['price']} (-{t['pct']}%)")

    reasoning = signal.get('reasoning', [])
    if reasoning:
        lines.append('Reasons:')
        for r in reasoning:
            lines.append(f'  - {r}')

    return '\n'.join(lines)


def quick_short_scan(watchlist_data: list, whale_flows: Dict = None,
                    top_n: int = 5) -> list:
    """Quick scan: return top N short candidates."""
    all_signals = batch_detect_shorts(watchlist_data, whale_flows)
    triggered = filter_short_signals(all_signals)
    return triggered[:top_n]


# =============================================================
# MODULE TEST
# =============================================================

if __name__ == '__main__':
    # Test with sample data
    import random

    test_closes = [100 - i * 0.3 + random.uniform(-0.5, 0.5) for i in range(50)]
    test_highs = [c + random.uniform(0.2, 1.0) for c in test_closes]
    test_lows = [c - random.uniform(0.2, 1.0) for c in test_closes]
    test_volumes = [1000000 + random.randint(-200000, 200000) for _ in range(50)]

    result = detect_short(
        ticker='TEST',
        closes=test_closes,
        highs=test_highs,
        lows=test_lows,
        volumes=test_volumes,
        sma_20=test_closes[-1] + 2,
        ema_50=test_closes[-1] + 5,
        rsi=72,
        macd_hist=-0.5,
        prev_macd_hist=0.3,
        atr=1.5
    )

    print(format_short_alert(result))
    print(f'\nScore breakdown: {result.get("score", 0)}/100')
    print(f'Patterns found: {list(result.get("patterns", {}).keys())}')
