#!/usr/bin/env python3
"""
Pullback Detector for OpenClaw v4.0
Sophisticated pullback detection with Fibonacci retracements,
volume profile, MA confluence, and FOM expected move alignment.

Features:
- Fibonacci retracement zone detection (23.6% to 78.6%)
- Volume Profile with Point of Control (POC) and Value Area
- Moving average confluence zones (20 SMA + 50 EMA + Fib)
- Pullback quality scoring (0-100)
- Mean-reversion trigger detection
- Pullback pattern classification
- FOM expected move alignment scoring
- Batch processing via ThreadPoolExecutor
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from technical_checker import check_technicals
except ImportError:
    check_technicals = None

try:
    from fom_expected_moves import get_expected_move
except ImportError:
    get_expected_move = None

logger = logging.getLogger(__name__)

# Fibonacci levels
FIB_LEVELS = [0.236, 0.382, 0.500, 0.618, 0.786]


def _find_swing_points(highs: list, lows: list, min_swing_pct: float = 3.0) -> List[Dict]:
    """Detect swing highs and lows using zigzag algorithm."""
    if len(highs) < 10:
        return []
    swings = []
    direction = 0  # 0=unknown, 1=up, -1=down
    last_high_idx = 0
    last_low_idx = 0
    last_high = highs[0]
    last_low = lows[0]

    for i in range(1, len(highs)):
        if highs[i] > last_high:
            last_high = highs[i]
            last_high_idx = i
        if lows[i] < last_low:
            last_low = lows[i]
            last_low_idx = i

        if direction != -1 and last_high > 0:
            pct_drop = (last_high - lows[i]) / last_high * 100
            if pct_drop >= min_swing_pct:
                swings.append({'type': 'high', 'price': last_high, 'index': last_high_idx})
                direction = -1
                last_low = lows[i]
                last_low_idx = i

        if direction != 1 and last_low > 0:
            pct_rise = (highs[i] - last_low) / last_low * 100
            if pct_rise >= min_swing_pct:
                swings.append({'type': 'low', 'price': last_low, 'index': last_low_idx})
                direction = 1
                last_high = highs[i]
                last_high_idx = i

    return swings


def detect_fib_pullback(highs: list, lows: list, closes: list, atr: float) -> Dict:
    """Detect Fibonacci retracement zones from swing points."""
    result = {'detected': False, 'level': None, 'price': None, 'distance_atr': None}
    if len(highs) < 20 or atr <= 0:
        return result

    swings = _find_swing_points(highs, lows)
    if len(swings) < 2:
        return result

    # Find most recent swing high and swing low
    swing_high = None
    swing_low = None
    for s in reversed(swings):
        if s['type'] == 'high' and swing_high is None:
            swing_high = s['price']
        elif s['type'] == 'low' and swing_low is None:
            swing_low = s['price']
        if swing_high and swing_low:
            break

    if not swing_high or not swing_low or swing_high <= swing_low:
        return result

    current_price = closes[-1]
    swing_range = swing_high - swing_low

    # Check which Fib level current price is near
    for level in FIB_LEVELS:
        fib_price = swing_high - (swing_range * level)
        distance = abs(current_price - fib_price)
        if distance <= 0.3 * atr:
            result = {
                'detected': True,
                'level': level,
                'price': round(fib_price, 2),
                'distance_atr': round(distance / atr, 2),
                'swing_high': round(swing_high, 2),
                'swing_low': round(swing_low, 2),
            }
            break

    return result


def calculate_volume_profile(closes: list, volumes: list, highs: list, lows: list, bins: int = 20) -> Dict:
    """Calculate Volume Profile with POC and Value Area."""
    result = {'poc': None, 'va_high': None, 'va_low': None}
    if len(closes) < 10:
        return result

    price_min = min(lows[-20:]) if len(lows) >= 20 else min(lows)
    price_max = max(highs[-20:]) if len(highs) >= 20 else max(highs)
    if price_max == price_min:
        return result

    bin_size = (price_max - price_min) / bins
    vol_profile = [0.0] * bins

    period = min(20, len(closes))
    for i in range(-period, 0):
        typical = (highs[i] + lows[i] + closes[i]) / 3
        bin_idx = min(int((typical - price_min) / bin_size), bins - 1)
        vol_profile[bin_idx] += volumes[i]

    # POC = price level with highest volume
    poc_idx = vol_profile.index(max(vol_profile))
    poc_price = price_min + (poc_idx + 0.5) * bin_size

    # Value Area = 70% of total volume around POC
    total_vol = sum(vol_profile)
    if total_vol == 0:
        return result

    target_vol = total_vol * 0.70
    va_vol = vol_profile[poc_idx]
    low_idx = poc_idx
    high_idx = poc_idx

    for _vp_iter in range(bins * 2):  # Bounded loop prevents infinite iteration
        if va_vol >= target_vol:
            break
        if low_idx <= 0 and high_idx >= bins - 1:
            break  # Expanded to full range, stop
        expand_low = vol_profile[low_idx - 1] if low_idx > 0 else 0
        expand_high = vol_profile[high_idx + 1] if high_idx < bins - 1 else 0
        if expand_low >= expand_high and low_idx > 0:
            low_idx -= 1
            va_vol += vol_profile[low_idx]
        elif high_idx < bins - 1:
            high_idx += 1
            va_vol += vol_profile[high_idx]
        else:
            break

    result = {
        'poc': round(poc_price, 2),
        'va_high': round(price_min + (high_idx + 1) * bin_size, 2),
        'va_low': round(price_min + low_idx * bin_size, 2),
    }
    return result


def detect_ma_confluence(sma_20: float, ema_50: float, fib_levels: Dict, atr: float) -> Dict:
    """Detect when MAs and Fib levels converge within 1 ATR."""
    result = {'detected': False, 'confluence_score': 0}
    if not sma_20 or not ema_50 or not atr or atr <= 0:
        return result

    prices = [sma_20, ema_50]
    if fib_levels.get('detected') and fib_levels.get('price'):
        prices.append(fib_levels['price'])

    if len(prices) < 2:
        return result

    spread = max(prices) - min(prices)
    if spread <= atr:
        tightness = 1.0 - (spread / atr)
        score = int(tightness * 10)
        result = {
            'detected': True,
            'confluence_score': min(10, max(0, score)),
            'spread_atr': round(spread / atr, 2),
            'levels': [round(p, 2) for p in prices],
        }
    return result


def score_pullback_quality(indicators: Dict, volumes: list = None) -> float:
    """Score pullback quality 0-100 based on multiple factors."""
    score = 0.0

    # Declining volume on pullback (30 pts)
    vol_ratio = indicators.get('volume_ratio')
    if vol_ratio is not None and vol_ratio < 0.8:
        score += 30
    elif vol_ratio is not None and vol_ratio < 1.0:
        score += 15

    # ATR compression (20 pts)
    atr = indicators.get('atr')
    atr_avg = indicators.get('atr_avg')
    if atr and atr_avg and atr < atr_avg:
        score += 20
    elif atr and atr_avg and atr < atr_avg * 1.2:
        score += 10

    # Staying above key MA (20 pts)
    price = indicators.get('price', 0)
    ema_50 = indicators.get('ema_50')
    sma_200 = indicators.get('sma_200')
    if ema_50 and price > ema_50:
        score += 12
    if sma_200 and price > sma_200:
        score += 8

    # RSI oversold but not panic (15 pts)
    rsi = indicators.get('rsi')
    if rsi is not None:
        if 30 < rsi < 45:
            score += 15
        elif 25 < rsi <= 30:
            score += 10
        elif 45 <= rsi < 50:
            score += 8

    # Williams %R entry zone (15 pts)
    wr = indicators.get('williams_r')
    if wr is not None:
        if -80 < wr < -60:
            score += 15
        elif -90 < wr <= -80:
            score += 10
        elif -60 <= wr < -50:
            score += 5

    return min(100.0, score)


def detect_mean_reversion_trigger(indicators: Dict) -> bool:
    """Multi-confirmation mean-reversion trigger."""
    rsi = indicators.get('rsi')
    wr = indicators.get('williams_r')
    price = indicators.get('price', 0)
    sma_200 = indicators.get('sma_200')
    vol_ratio = indicators.get('volume_ratio')

    # RSI < 30 OR Williams %R < -80
    oversold = (rsi is not None and rsi < 30) or (wr is not None and wr < -80)
    if not oversold:
        return False

    # Price > 200 SMA (still in uptrend)
    if not sma_200 or price <= sma_200:
        return False

    # Volume spike on reversal bar
    if not vol_ratio or vol_ratio < 1.3:
        return False

    return True


def classify_pullback(indicators: Dict, fib_data: Dict) -> str:
    """Classify pullback type."""
    rsi = indicators.get('rsi')
    price = indicators.get('price', 0)
    sma_200 = indicators.get('sma_200')
    vol_ratio = indicators.get('volume_ratio')
    fib_level = fib_data.get('level')

    if not sma_200 or price < sma_200:
        return 'failed'
    if vol_ratio and vol_ratio > 1.2:
        return 'failed'  # Volume increasing on pullback

    if fib_level and 0.35 <= fib_level <= 0.52:
        if vol_ratio and vol_ratio < 0.8:
            return 'healthy_retracement'
    if fib_level and fib_level >= 0.6:
        if rsi and rsi < 30:
            return 'deep_value'
    if vol_ratio and vol_ratio < 0.6:
        return 'consolidation'

    return 'moderate'


def score_em_alignment(pullback_distance_pct: float, expected_move_pct: float) -> int:
    """Score entry quality relative to FOM expected move."""
    if not expected_move_pct or expected_move_pct <= 0:
        return 0
    ratio = pullback_distance_pct / expected_move_pct
    if 0.5 <= ratio <= 0.7:
        return 5
    elif 0.4 <= ratio < 0.5 or 0.7 < ratio <= 0.8:
        return 3
    elif 0.3 <= ratio < 0.4:
        return 1
    return 0


def detect_pullback(ticker: str, technicals: Dict = None) -> Dict:
    """
    Full pullback detection for a single ticker.
    Returns comprehensive pullback analysis.
    """
    result = {
        'ticker': ticker,
        'pullback_detected': False,
        'quality_score': 0.0,
        'pattern': 'none',
        'fib_level': None,
        'fib_price': None,
        'poc': None,
        'ma_confluence': False,
        'mean_reversion_trigger': False,
        'em_alignment_score': 0,
        'expected_move_pct': 0,
        'entry_zone': None,
        'confidence': 0.0,
    }

    # Get technicals if not provided
    if not technicals and check_technicals:
        try:
            results = check_technicals([ticker])
            if results and len(results) > 0:
                technicals = results[0]
        except Exception as e:
            logger.error(f"Failed to get technicals for {ticker}: {e}")
            return result

    if not technicals or technicals.get('error'):
        return result

    # Extract bar data from technicals
    price = technicals.get('price', 0)
    rsi = technicals.get('rsi')
    wr = technicals.get('williams_r')
    atr = technicals.get('atr', 0)
    sma_20 = technicals.get('sma_20')
    sma_200 = technicals.get('sma_200')
    ema_50 = technicals.get('ema_50')
    vol_ratio = technicals.get('volume_ratio')

    if not price or price <= 0:
        return result

    # Build indicators dict for scoring
    ind = {
        'price': price, 'rsi': rsi, 'williams_r': wr,
        'atr': atr, 'sma_20': sma_20, 'sma_200': sma_200,
        'ema_50': ema_50, 'volume_ratio': vol_ratio,
                'atr_avg': atr,  # Placeholder - updated below with true ATR average for compression detection
    }

    # Fibonacci detection (use daily bars if available)
    highs = technicals.get('highs', [])
    lows = technicals.get('lows', [])
    closes = technicals.get('closes', [])
    volumes = technicals.get('volumes', [])

        # Calculate true ATR average from historical bars for compression detection
    if highs and lows and closes and len(highs) >= 20:
        trs = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            trs.append(tr)
        # Current ATR = mean of last 14 TRs
        current_atr = np.mean(trs[-14:]) if len(trs) >= 14 else np.mean(trs)
        # Historical ATR average = mean of last 20 ATR windows (rolling)
        atr_avg = np.mean(trs[-20:]) if len(trs) >= 20 else np.mean(trs)
        ind['atr'] = current_atr
        ind['atr_avg'] = atr_avg
    else:
        ind['atr_avg'] = atr  # fallback if not enough data

    fib_data = {'detected': False}
    if highs and lows and closes and atr > 0:
        fib_data = detect_fib_pullback(highs, lows, closes, atr)

    # Volume Profile
    vol_profile = {'poc': None}
    if closes and volumes and highs and lows:
        vol_profile = calculate_volume_profile(closes, volumes, highs, lows)

    # MA Confluence
    ma_conf = detect_ma_confluence(sma_20 or 0, ema_50 or 0, fib_data, atr)

    # Pullback Quality Score
    quality = score_pullback_quality(ind, volumes)

    # Mean Reversion Trigger
    mr_trigger = detect_mean_reversion_trigger(ind)

    # Pattern Classification
    pattern = classify_pullback(ind, fib_data)

    # FOM Expected Move Alignment
    em_score = 0
    em_pct = 0.0
    if get_expected_move:
        try:
            em_data = get_expected_move(ticker)
            if em_data and isinstance(em_data, dict):
                em_pct = em_data.get('em_pct', 0)
            elif em_data and isinstance(em_data, (int, float)):
                em_pct = float(em_data)
            if em_pct > 0 and sma_20 and price:
                pullback_pct = abs(price - sma_20) / sma_20 * 100
                em_score = score_em_alignment(pullback_pct, em_pct)
        except Exception:
            pass

    # Determine if pullback is detected
    pullback_detected = (
        quality >= 40
        or fib_data.get('detected', False)
        or mr_trigger
        or pattern in ('healthy_retracement', 'deep_value')
    )

    # Entry zone calculation
    entry_zone = None
    if pullback_detected:
        if fib_data.get('price'):
            entry_zone = fib_data['price']
        elif vol_profile.get('poc'):
            entry_zone = vol_profile['poc']
        elif sma_20:
            entry_zone = sma_20
        else:
            entry_zone = price

    # Confidence
    confidence = min(1.0, quality / 100)
    if fib_data.get('detected'):
        confidence = min(1.0, confidence + 0.1)
    if ma_conf.get('detected'):
        confidence = min(1.0, confidence + 0.1)
    if mr_trigger:
        confidence = min(1.0, confidence + 0.15)

    result = {
        'ticker': ticker,
        'pullback_detected': pullback_detected,
        'quality_score': round(quality, 1),
        'pattern': pattern,
        'fib_level': fib_data.get('level'),
        'fib_price': fib_data.get('price'),
        'poc': vol_profile.get('poc'),
        'ma_confluence': ma_conf.get('detected', False),
        'mean_reversion_trigger': mr_trigger,
        'em_alignment_score': em_score,
        'expected_move_pct': round(em_pct, 2),
        'entry_zone': round(entry_zone, 2) if entry_zone else None,
        'confidence': round(confidence, 2),
    }
    return result


def batch_detect_pullbacks(tickers: List[str], max_workers: int = 3) -> Dict[str, Dict]:
    """Process multiple tickers for pullback detection."""
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
        return detect_pullback(ticker, tech)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_detect_single, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                result = future.result()
                results[ticker] = result
            except Exception as e:
                logger.error(f"Pullback detection failed for {ticker}: {e}")
                results[ticker] = {'ticker': ticker, 'pullback_detected': False, 'quality_score': 0}

    detected = sum(1 for r in results.values() if r.get('pullback_detected'))
    logger.info(f"Pullback detection: {detected}/{len(tickers)} pullbacks found")
    return results
