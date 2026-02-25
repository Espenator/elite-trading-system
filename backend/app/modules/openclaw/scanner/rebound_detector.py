"""rebound_detector.py - Reversal & Rebound Detection Module

Detects capitulation bounces, reversal patterns, VWAP reclaims,
RSI divergence with volume confirmation, and support bounces.
Integrates with composite_scorer.py for enhanced scoring.

Part of OpenClaw v4.0 Real-Time Trading Engine.
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Conditional imports for OpenClaw integration
try:
    from technical_checker import check_technicals
except ImportError:
    check_technicals = None

try:
    from fom_expected_moves import get_expected_move
except ImportError:
    get_expected_move = None

try:
    from pullback_detector import calculate_volume_profile
except ImportError:
    calculate_volume_profile = None

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

CAPITULATION_VOLUME_MULTIPLIER = 3.0  # Volume must be 3x 20-bar avg
REVERSAL_LOOKBACK = 3  # Bars to check for reversal after capitulation
VWAP_RECLAIM_VOLUME_RATIO = 1.2  # Min volume ratio on reclaim bar
DIVERGENCE_VOLUME_CONFIRM = 1.3  # Volume must be 1.3x on second low
SUPPORT_PROXIMITY_ATR = 0.5  # Within 0.5 ATR counts as "touching" support
SWING_LOOKBACK = 60  # Bars to look back for swing points
SWING_MIN_PERCENT = 3.0  # Min swing size in percent
RSI_OVERSOLD = 30  # RSI oversold threshold
RSI_RECOVERY = 35  # RSI must recover above this
DOWNTREND_LOOKBACK = 10  # Bars to confirm downtrend for patterns


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_bars_from_technicals(ticker: str, tech: Optional[Dict] = None) -> Optional[Dict]:
    """Get OHLCV bars data from technicals or fetch fresh."""
    if tech and 'bars' in tech:
        return tech['bars']
    if tech:
        return tech
    if check_technicals:
        try:
            results = check_technicals([ticker])
            if results and len(results) > 0:
                return results[0] if isinstance(results, list) else results
        except Exception as e:
            logger.error(f"Failed to fetch technicals for {ticker}: {e}")
    return None


def _is_downtrend(closes: list, lookback: int = 10) -> bool:
    """Check if price has been in a downtrend over lookback bars."""
    if len(closes) < lookback:
        return False
    recent = closes[-lookback:]
    # Count lower lows
    lower_count = sum(1 for i in range(1, len(recent)) if recent[i] < recent[i-1])
    return lower_count >= lookback * 0.6


def _find_swing_lows(lows: list, lookback: int = 5) -> List[Tuple[int, float]]:
    """Find swing low points in price data."""
    swing_lows = []
    if len(lows) < lookback * 2 + 1:
        return swing_lows
    for i in range(lookback, len(lows) - lookback):
        is_low = True
        for j in range(1, lookback + 1):
            if lows[i] > lows[i - j] or lows[i] > lows[i + j]:
                is_low = False
                break
        if is_low:
            swing_lows.append((i, lows[i]))
    return swing_lows


def _calculate_atr(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """Calculate Average True Range."""
    if len(highs) < period + 1:
        return 0.0
    tr_list = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        tr_list.append(tr)
    if len(tr_list) < period:
        return np.mean(tr_list) if tr_list else 0.0
    return np.mean(tr_list[-period:])


# ============================================================
# CAPITULATION VOLUME DETECTION
# ============================================================

def detect_capitulation(highs: list, lows: list, closes: list, opens: list,
                        volumes: list) -> Dict:
    """Detect capitulation volume events.
    
    Capitulation = volume spike 3x+ on a down day, followed by reversal.
    """
    result = {'detected': False, 'spike_ratio': 0.0, 'reversal_bar': 0}
    
    if len(volumes) < 25 or len(closes) < 25:
        return result
    
    # Check last 5 bars for capitulation events
    avg_vol_20 = np.mean(volumes[-25:-5]) if len(volumes) >= 25 else np.mean(volumes[:-5])
    if avg_vol_20 <= 0:
        return result
    
    for i in range(-5, -1):
        idx = len(closes) + i
        if idx < 1:
            continue
        
        # Must be a down day
        if closes[idx] >= opens[idx]:
            continue
        
        # Volume must be 3x+ average
        spike_ratio = volumes[idx] / avg_vol_20 if avg_vol_20 > 0 else 0
        if spike_ratio < CAPITULATION_VOLUME_MULTIPLIER:
            continue
        
        # Check for reversal within next 1-3 bars
        for rev_offset in range(1, min(REVERSAL_LOOKBACK + 1, len(closes) - idx)):
            rev_idx = idx + rev_offset
            if rev_idx >= len(closes):
                break
            # Reversal: close above prior candle's high
            if closes[rev_idx] > highs[idx]:
                result = {
                    'detected': True,
                    'spike_ratio': round(spike_ratio, 2),
                    'reversal_bar': rev_offset,
                    'capitulation_idx': idx,
                    'capitulation_volume': volumes[idx],
                    'avg_volume': avg_vol_20
                }
                return result
    
    return result


# ============================================================
# REVERSAL CANDLESTICK PATTERNS
# ============================================================

def detect_reversal_pattern(highs: list, lows: list, closes: list,
                            opens: list) -> str:
    """Detect bullish reversal candlestick patterns.
    
    Returns: 'hammer'|'engulfing'|'morning_star'|'piercing'|'none'
    """
    if len(closes) < 4:
        return 'none'
    
    # Check if in downtrend (required context for reversal patterns)
    if not _is_downtrend(closes[:-1], DOWNTREND_LOOKBACK):
        return 'none'
    
    # Current bar values
    o = opens[-1]
    h = highs[-1]
    l = lows[-1]
    c = closes[-1]
    body = abs(c - o)
    candle_range = h - l if h != l else 0.001
    
    # Prior bar values
    po = opens[-2]
    ph = highs[-2]
    pl = lows[-2]
    pc = closes[-2]
    p_body = abs(pc - po)
    
    # HAMMER: small body at top, long lower wick (2x body)
    if body > 0:
        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)
        if lower_wick >= 2 * body and upper_wick <= body * 0.5:
            if c >= o:  # Preferably green
                return 'hammer'
    
    # BULLISH ENGULFING: current green bar engulfs prior red bar
    if pc < po and c > o:  # Prior red, current green
        if o <= pc and c >= po:  # Current engulfs prior
            return 'engulfing'
    
    # MORNING STAR: 3-bar pattern (red, doji/small, green)
    if len(closes) >= 3:
        o3 = opens[-3]
        c3 = closes[-3]
        o2 = opens[-2]
        c2 = closes[-2]
        body3 = abs(c3 - o3)
        body2 = abs(c2 - o2)
        
        if (c3 < o3 and  # First bar red
            body2 < body3 * 0.3 and  # Middle bar small (doji)
            c > o and  # Last bar green
            c > (o3 + c3) / 2):  # Closes above midpoint of first
            return 'morning_star'
    
    # PIERCING LINE: green bar closes above 50% of prior red bar
    if pc < po and c > o:  # Prior red, current green
        prior_midpoint = (po + pc) / 2
        if o < pc and c > prior_midpoint and c < po:
            return 'piercing'
    
    return 'none'


# ============================================================
# RSI DIVERGENCE WITH VOLUME CONFIRMATION
# ============================================================

def detect_confirmed_divergence(closes: list, volumes: list,
                                 rsi_series: Optional[list] = None,
                                 period: int = 14) -> Dict:
    """Detect RSI divergence with volume confirmation.
    
    Bullish divergence: price makes lower low, RSI makes higher low,
    AND volume expands on second low (1.3x first low).
    """
    result = {'type': 'none', 'confirmed': False}
    
    if len(closes) < 30:
        return result
    
    # Calculate RSI if not provided
    if rsi_series is None or len(rsi_series) < 20:
        rsi_series = _calculate_rsi(closes, period)
    
    if len(rsi_series) < 20:
        return result
    
    # Find two recent swing lows in price
    price_lows = _find_swing_lows(closes[-30:], lookback=3)
    if len(price_lows) < 2:
        return result
    
    # Get the two most recent lows
    low1_idx, low1_price = price_lows[-2]
    low2_idx, low2_price = price_lows[-1]
    
    # Map to RSI indices
    rsi_offset = len(rsi_series) - 30
    rsi_idx1 = low1_idx + rsi_offset
    rsi_idx2 = low2_idx + rsi_offset
    
    if rsi_idx1 < 0 or rsi_idx2 < 0 or rsi_idx1 >= len(rsi_series) or rsi_idx2 >= len(rsi_series):
        return result
    
    rsi_low1 = rsi_series[rsi_idx1]
    rsi_low2 = rsi_series[rsi_idx2]
    
    # Map to volume indices
    vol_offset = len(volumes) - 30
    vol_idx1 = low1_idx + vol_offset
    vol_idx2 = low2_idx + vol_offset
    
    # BULLISH DIVERGENCE: lower price low, higher RSI low
    if low2_price < low1_price and rsi_low2 > rsi_low1:
        confirmed = False
        if (vol_idx1 >= 0 and vol_idx2 >= 0 and
            vol_idx1 < len(volumes) and vol_idx2 < len(volumes)):
            if volumes[vol_idx1] > 0:
                vol_ratio = volumes[vol_idx2] / volumes[vol_idx1]
                confirmed = vol_ratio >= DIVERGENCE_VOLUME_CONFIRM
        result = {
            'type': 'bullish',
            'confirmed': confirmed,
            'price_low1': low1_price,
            'price_low2': low2_price,
            'rsi_low1': round(rsi_low1, 1),
            'rsi_low2': round(rsi_low2, 1)
        }
    
    # BEARISH DIVERGENCE: higher price high, lower RSI high
    price_highs = []
    for i in range(3, len(closes[-30:]) - 3):
        if closes[-30+i] == max(closes[-30+i-3:-30+i+4]):
            price_highs.append((i, closes[-30+i]))
    
    if len(price_highs) >= 2:
        hi1_idx, hi1_price = price_highs[-2]
        hi2_idx, hi2_price = price_highs[-1]
        rsi_hi1 = rsi_series[hi1_idx + rsi_offset] if hi1_idx + rsi_offset < len(rsi_series) else 50
        rsi_hi2 = rsi_series[hi2_idx + rsi_offset] if hi2_idx + rsi_offset < len(rsi_series) else 50
        
        if hi2_price > hi1_price and rsi_hi2 < rsi_hi1:
            result = {
                'type': 'bearish',
                'confirmed': False,  # Bearish div doesnt need vol confirm for rebound
                'price_high1': hi1_price,
                'price_high2': hi2_price,
                'rsi_high1': round(rsi_hi1, 1),
                'rsi_high2': round(rsi_hi2, 1)
            }
    
    return result


def _calculate_rsi(closes: list, period: int = 14) -> list:
    """Calculate RSI series."""
    if len(closes) < period + 1:
        return []
    
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    rsi_values = []
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100.0 - (100.0 / (1.0 + rs)))
    
    return rsi_values


# ============================================================
# VWAP RECLAIM DETECTION
# ============================================================

def detect_vwap_reclaim(closes: list, volumes: list, highs: list,
                         lows: list, vwap: Optional[float] = None) -> Dict:
    """Detect when price crosses below VWAP then reclaims it with volume."""
    result = {'reclaimed': False, 'bars_below': 0, 'volume_ratio': 0.0}
    
    if not vwap or vwap <= 0 or len(closes) < 10:
        return result
    
    # Calculate VWAP if not provided (typical price * volume / cum volume)
    if vwap is None:
        tp = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]
        cum_tp_vol = np.cumsum([tp[i] * volumes[i] for i in range(len(tp))])
        cum_vol = np.cumsum(volumes)
        vwap_series = [cum_tp_vol[i] / cum_vol[i] if cum_vol[i] > 0 else 0 for i in range(len(cum_vol))]
        vwap = vwap_series[-1] if vwap_series else 0
    
    if vwap <= 0:
        return result
    
    # Look for VWAP reclaim pattern
    # Price was below VWAP, then crosses above with volume
    bars_below = 0
    was_below = False
    
    for i in range(max(0, len(closes) - 20), len(closes) - 1):
        if closes[i] < vwap:
            was_below = True
            bars_below += 1
    
    # Current bar reclaims VWAP
    if was_below and closes[-1] > vwap and bars_below >= 2:
        # Check volume on reclaim bar
        avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0
        
        if vol_ratio >= VWAP_RECLAIM_VOLUME_RATIO:
            result = {
                'reclaimed': True,
                'bars_below': bars_below,
                'volume_ratio': round(vol_ratio, 2),
                'vwap_price': round(vwap, 2),
                'reclaim_price': closes[-1]
            }
    
    return result


# ============================================================
# SUPPORT BOUNCE SCORING
# ============================================================

def score_support_bounce(highs: list, lows: list, closes: list,
                          volumes: list, sma_200: float = 0,
                          ema_50: float = 0, atr: float = 0) -> Dict:
    """Score bounce off support levels.
    
    Identifies support from: swing lows, volume nodes, round numbers, MAs.
    Scores based on how many support types converge.
    """
    result = {'score': 0, 'support_levels': [], 'support_types': 0}
    
    if len(closes) < 20 or atr <= 0:
        return result
    
    price = closes[-1]
    support_levels = []
    proximity = SUPPORT_PROXIMITY_ATR * atr
    
    # 1. Prior swing lows (last 3 in 60 bars)
    swing_lows = _find_swing_lows(lows[-60:] if len(lows) >= 60 else lows, lookback=5)
    for idx, low_price in swing_lows[-3:]:
        if abs(price - low_price) <= proximity:
            support_levels.append(('swing_low', low_price))
    
    # 2. High-volume nodes from volume profile
    if calculate_volume_profile and len(highs) >= 20:
        try:
            vol_prof = calculate_volume_profile(
                highs[-20:], lows[-20:], closes[-20:], volumes[-20:]
            )
            poc = vol_prof.get('poc', 0)
            if poc and abs(price - poc) <= proximity:
                support_levels.append(('poc', poc))
        except Exception:
            pass
    
    # 3. Round numbers
    round_levels = []
    if price > 100:
        base = int(price / 10) * 10
        round_levels = [base - 10, base, base + 10]
    elif price > 10:
        base = int(price / 5) * 5
        round_levels = [base - 5, base, base + 5]
    else:
        base = int(price)
        round_levels = [base - 1, base, base + 1]
    
    for rl in round_levels:
        if abs(price - rl) <= proximity:
            support_levels.append(('round_number', rl))
    
    # 4. Key moving averages
    if ema_50 and abs(price - ema_50) <= proximity:
        support_levels.append(('ema_50', ema_50))
    if sma_200 and abs(price - sma_200) <= proximity:
        support_levels.append(('sma_200', sma_200))
    
    # Score based on convergence
    unique_types = len(set(t for t, _ in support_levels))
    if unique_types >= 3:
        score = 10
    elif unique_types == 2:
        score = 8
    elif unique_types == 1:
        score = 5
    else:
        score = 0
    
    # Bonus: check if bouncing (price was near support and now moving up)
    if len(closes) >= 3 and score > 0:
        if closes[-1] > closes[-2] > closes[-3]:
            score = min(10, score + 2)  # Bounce confirmation
    
    result = {
        'score': score,
        'support_levels': [(t, round(p, 2)) for t, p in support_levels],
        'support_types': unique_types
    }
    
    return result


# ============================================================
# REBOUND QUALITY SCORING
# ============================================================

def score_rebound_quality(capitulation: Dict, reversal_pattern: str,
                          divergence: Dict, vwap_reclaim: Dict,
                          support_bounce: Dict,
                          price_above_200sma: bool = False) -> float:
    """Score overall rebound quality (0-100).
    
    Components:
    - Capitulation volume detected: 25 pts
    - Reversal pattern present: 20 pts
    - RSI divergence confirmed: 20 pts
    - VWAP reclaim: 15 pts
    - Support bounce score: 10 pts
    - Price > 200 SMA: 10 pts
    """
    score = 0.0
    
    # Capitulation volume (25 pts)
    if capitulation.get('detected'):
        base = 15
        spike = capitulation.get('spike_ratio', 0)
        if spike >= 5.0:
            base = 25
        elif spike >= 4.0:
            base = 22
        elif spike >= 3.0:
            base = 18
        score += base
    
    # Reversal pattern (20 pts)
    pattern_scores = {
        'engulfing': 20,
        'morning_star': 18,
        'hammer': 15,
        'piercing': 12,
        'none': 0
    }
    score += pattern_scores.get(reversal_pattern, 0)
    
    # RSI divergence confirmed (20 pts)
    if divergence.get('type') == 'bullish':
        score += 12
        if divergence.get('confirmed'):
            score += 8  # Volume confirmed
    
    # VWAP reclaim (15 pts)
    if vwap_reclaim.get('reclaimed'):
        base = 10
        vol_ratio = vwap_reclaim.get('volume_ratio', 0)
        if vol_ratio >= 1.5:
            base = 15
        elif vol_ratio >= 1.3:
            base = 12
        score += base
    
    # Support bounce (10 pts)
    support_score = support_bounce.get('score', 0)
    score += min(10, support_score)
    
    # Price above 200 SMA (10 pts)
    if price_above_200sma:
        score += 10
    
    return min(100.0, score)


# ============================================================
# REBOUND TRIGGER CONDITIONS
# ============================================================

def detect_rebound_trigger(reversal_pattern: str, rsi_values: list,
                            volume_ratio: float, vwap_reclaim: Dict,
                            support_bounce: Dict) -> bool:
    """Multi-confirmation rebound trigger.
    
    Requires:
    - Reversal pattern detected (hammer or engulfing)
    - RSI was < 30 in last 5 bars, now > 35
    - Volume ratio > 1.3 on reversal bar
    - Price reclaimed VWAP or touched support
    """
    # Must have reversal pattern
    if reversal_pattern not in ('hammer', 'engulfing', 'morning_star', 'piercing'):
        return False
    
    # RSI must have been oversold recently and now recovering
    rsi_was_oversold = False
    rsi_now_recovered = False
    if rsi_values and len(rsi_values) >= 5:
        for rsi in rsi_values[-5:]:
            if rsi < RSI_OVERSOLD:
                rsi_was_oversold = True
                break
        if rsi_values[-1] > RSI_RECOVERY:
            rsi_now_recovered = True
    
    if not (rsi_was_oversold and rsi_now_recovered):
        return False
    
    # Volume must be above average
    if volume_ratio < 1.3:
        return False
    
    # Must have VWAP reclaim OR support touch
    has_vwap_reclaim = vwap_reclaim.get('reclaimed', False)
    has_support = support_bounce.get('score', 0) >= 5
    
    if not (has_vwap_reclaim or has_support):
        return False
    
    return True


# ============================================================
# FOM EXPECTED MOVES FOR REBOUNDS
# ============================================================

def score_rebound_em_alignment(bounce_magnitude: float,
                                expected_move: float) -> int:
    """Score rebound relative to FOM expected move.
    
    Proportional rebounds (30-50% of EM) are meaningful vs noise.
    """
    if expected_move <= 0 or bounce_magnitude <= 0:
        return 0
    
    ratio = bounce_magnitude / expected_move
    
    if 0.3 <= ratio <= 0.5:
        return 5  # Optimal proportional rebound
    elif 0.2 <= ratio < 0.3 or 0.5 < ratio <= 0.7:
        return 3  # Acceptable rebound
    elif ratio > 0.7:
        return 1  # Too large, might be overextended
    
    return 0  # Too small, likely noise


# ============================================================
# MAIN REBOUND DETECTION FUNCTION
# ============================================================

def detect_rebound(ticker: str, tech: Optional[Dict] = None) -> Dict:
    """Run full rebound detection pipeline for a single ticker.
    
    Returns comprehensive rebound data structure.
    """
    result = {
        'ticker': ticker,
        'rebound_detected': False,
        'quality_score': 0.0,
        'capitulation': {'detected': False},
        'reversal_pattern': 'none',
        'rsi_divergence': {'type': 'none', 'confirmed': False},
        'vwap_reclaim': {'reclaimed': False, 'bars_below': 0, 'volume_ratio': 0.0},
        'support_bounce_score': 0,
        'trigger_active': False,
        'em_alignment_score': 0,
        'expected_move_pct': 0.0,
        'entry_zone': None,
        'confidence': 0.0
    }
    
    try:
        # Get bar data
        data = _get_bars_from_technicals(ticker, tech)
        if not data:
            return result
        
        # Extract OHLCV arrays
        closes = data.get('closes', data.get('close', []))
        opens = data.get('opens', data.get('open', []))
        highs = data.get('highs', data.get('high', []))
        lows = data.get('lows', data.get('low', []))
        volumes = data.get('volumes', data.get('volume', []))
        
        # Handle single values vs lists
        if not isinstance(closes, (list, np.ndarray)) or len(closes) < 20:
            return result
        
        # Extract indicator values
        rsi = data.get('rsi', None)
        sma_200 = data.get('sma_200', 0)
        ema_50 = data.get('ema_50', data.get('ema50', 0))
        vwap = data.get('vwap', 0)
        atr = data.get('atr', 0)
        price = closes[-1] if closes else 0
        
        if atr == 0:
            atr = _calculate_atr(list(highs), list(lows), list(closes))
        
        # Convert to lists if numpy arrays
        closes = list(closes)
        opens = list(opens)
        highs = list(highs)
        lows = list(lows)
        volumes = list(volumes)
        
        # 1. Capitulation volume detection
        capitulation = detect_capitulation(highs, lows, closes, opens, volumes)
        
        # 2. Reversal candlestick pattern
        reversal_pattern = detect_reversal_pattern(highs, lows, closes, opens)
        
        # 3. RSI divergence with volume confirmation
        rsi_series = None
        if isinstance(rsi, (list, np.ndarray)) and len(rsi) >= 20:
            rsi_series = list(rsi)
        divergence = detect_confirmed_divergence(closes, volumes, rsi_series)
        
        # 4. VWAP reclaim detection
        vwap_reclaim = detect_vwap_reclaim(closes, volumes, highs, lows, vwap)
        
        # 5. Support bounce scoring
        support_bounce = score_support_bounce(
            highs, lows, closes, volumes,
            sma_200=sma_200, ema_50=ema_50, atr=atr
        )
        
        # 6. Price above 200 SMA
        price_above_200sma = price > sma_200 if sma_200 and price else False
        
        # 7. Rebound quality score
        quality = score_rebound_quality(
            capitulation, reversal_pattern, divergence,
            vwap_reclaim, support_bounce, price_above_200sma
        )
        
        # 8. Volume ratio for trigger
        avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        current_vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0
        
        # 9. RSI values for trigger
        if rsi_series is None:
            rsi_series = _calculate_rsi(closes)
        
        # 10. Rebound trigger
        trigger_active = detect_rebound_trigger(
            reversal_pattern, rsi_series,
            current_vol_ratio, vwap_reclaim, support_bounce
        )
        
        # 11. FOM expected move alignment
        em_score = 0
        em_pct = 0.0
        if get_expected_move:
            try:
                em_data = get_expected_move(ticker)
                if em_data and isinstance(em_data, dict):
                    em_pct = em_data.get('em_pct', 0)
                elif em_data and isinstance(em_data, (int, float)):
                    em_pct = float(em_data)
                
                if em_pct > 0:
                    recent_low = min(lows[-10:]) if len(lows) >= 10 else min(lows)
                    bounce_mag = ((price - recent_low) / recent_low * 100) if recent_low > 0 else 0
                    em_score = score_rebound_em_alignment(bounce_mag, em_pct)
            except Exception as e:
                logger.debug(f"FOM lookup failed for {ticker}: {e}")
        
        # Determine if rebound detected
        rebound_detected = (
            quality >= 40 or
            trigger_active or
            (capitulation.get('detected') and reversal_pattern != 'none')
        )
        
        # Entry zone calculation
        entry_zone = None
        if rebound_detected:
            if vwap and vwap_reclaim.get('reclaimed'):
                entry_zone = vwap
            elif support_bounce.get('support_levels'):
                # Use highest support level
                levels = [p for _, p in support_bounce['support_levels']]
                entry_zone = max(levels) if levels else price
            else:
                entry_zone = price
        
        # Confidence calculation
        confidence = min(1.0, quality / 100)
        if trigger_active:
            confidence = min(1.0, confidence + 0.15)
        if divergence.get('confirmed'):
            confidence = min(1.0, confidence + 0.1)
        if capitulation.get('detected'):
            confidence = min(1.0, confidence + 0.1)
        
        result = {
            'ticker': ticker,
            'rebound_detected': rebound_detected,
            'quality_score': round(quality, 1),
            'capitulation': capitulation,
            'reversal_pattern': reversal_pattern,
            'rsi_divergence': divergence,
            'vwap_reclaim': vwap_reclaim,
            'support_bounce_score': support_bounce.get('score', 0),
            'trigger_active': trigger_active,
            'em_alignment_score': em_score,
            'expected_move_pct': round(em_pct, 2),
            'entry_zone': round(entry_zone, 2) if entry_zone else None,
            'confidence': round(confidence, 2)
        }
        
    except Exception as e:
        logger.error(f"Rebound detection failed for {ticker}: {e}")
    
    return result


# ============================================================
# BATCH PROCESSING
# ============================================================

def batch_detect_rebounds(tickers: List[str], max_workers: int = 5) -> Dict[str, Dict]:
    """Process multiple tickers for rebound detection."""
    results = {}
    
    if not tickers:
        return results
    
    # Get technicals for all tickers at once
    tech_map = {}
    if check_technicals:
        try:
            tech_results = check_technicals(tickers)
            tech_map = {
                t['ticker']: t for t in tech_results
                if t.get('ticker') and 'error' not in t
            }
        except Exception as e:
            logger.error(f"Batch technicals failed: {e}")
    
    def _detect_single(ticker):
        tech = tech_map.get(ticker)
        return detect_rebound(ticker, tech)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_detect_single, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                result = future.result()
                results[ticker] = result
            except Exception as e:
                logger.error(f"Rebound detection failed for {ticker}: {e}")
                results[ticker] = {
                    'ticker': ticker,
                    'rebound_detected': False,
                    'quality_score': 0
                }
    
    detected = sum(1 for r in results.values() if r.get('rebound_detected'))
    logger.info(f"Rebound detection: {detected}/{len(tickers)} rebounds found")
    
    return results
