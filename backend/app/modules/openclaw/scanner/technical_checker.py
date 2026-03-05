#!/usr/bin/env python3
"""
Technical Checker for OpenClaw v2.1
Calculates technical indicators for each candidate using Alpaca bars.

Indicators computed:
  - 20 SMA, 200 SMA, 50 EMA
  - Williams %R (14-period)
  - RSI (14-period)
  - ADX (14-period)
  - MACD histogram
  - ATR (14-period)
  - Volume ratio (vs 20-day avg)
  - Basing detection (tight range)
  - Elephant bar detection
  - Channel-up detection (NEW)
  - Breakout from base detection (NEW)
  - AMD pattern detection (NEW)
  - Sector lookup via sector_rotation (NEW)

Fixes v2.1:
  - Added 'feed' param to Alpaca v2 bars endpoint
  - Added sector field for composite_scorer sector rotation
  - channel_up now computed (higher highs + higher lows over 20 bars)
  - breakout now computed (price breaks above 20-bar high after basing)
  - amd_detected now computed (overnight consolidation + breakout)
  - Alpaca asset endpoint used for sector lookup

Data source: Alpaca Markets API (free tier compatible)
"""
import os
import logging
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
_data_url = os.getenv('ALPACA_DATA_URL', 'https://data.alpaca.markets').rstrip('/')
ALPACA_DATA_URL = _data_url if _data_url.endswith('/v2') else _data_url + '/v2'
_trade_url = os.getenv('ALPACA_BASE_URL', 'https://api.alpaca.markets').rstrip('/')
ALPACA_TRADE_URL = _trade_url if _trade_url.endswith('/v2') else _trade_url + '/v2'
ALPACA_FEED = os.getenv('ALPACA_FEED', 'sip')

# Sector lookup cache with TTL to avoid repeated API calls and unbounded growth
_SECTOR_CACHE: Dict[str, tuple] = {}  # {ticker: (sector, timestamp)}
_SECTOR_CACHE_TTL = 86400  # 24 hours

def _evict_sector_cache():
  """Evict oldest entries if cache exceeds 500 to prevent unbounded growth."""
  if len(_SECTOR_CACHE) > 500:
    sorted_entries = sorted(_SECTOR_CACHE.items(), key=lambda x: x[1][1])
    for key, _ in sorted_entries[:100]:
      del _SECTOR_CACHE[key]


class TechnicalChecker:
    """
    Fetches price bars from Alpaca and computes technical indicators
    needed by CompositeScorer.
    """

    def __init__(self, api_key=None, secret_key=None):
        self.api_key = api_key or ALPACA_API_KEY
        self.secret_key = secret_key or ALPACA_SECRET_KEY
        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.secret_key,
        }

    def get_bars(self, ticker: str, timeframe: str = '1Day',
                 limit: int = 250) -> List[Dict]:
        """Fetch OHLCV bars from Alpaca v2 with proper feed param."""
        url = f"{ALPACA_DATA_URL}/stocks/{ticker}/bars"
        params = {
            'timeframe': timeframe,
            'limit': limit,
            'adjustment': 'split',
            'feed': ALPACA_FEED,
                'start': (datetime.now() - timedelta(days=int(limit * 1.6))).strftime('%Y-%m-%d'),
        }
        try:
            resp = requests.get(url, headers=self.headers,
                                params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data.get('bars') or []
        except Exception as e:
            logger.error(f"Failed to get bars for {ticker}: {e}")
            return []

    def get_sector(self, ticker: str) -> str:
        """
        Look up sector for a ticker. Uses sector_rotation module
        STOCK_SECTOR_HINTS first, then falls back to Alpaca asset API.
        Results are cached.
        """
        if ticker in _SECTOR_CACHE:
            sector, ts = _SECTOR_CACHE[ticker]
            if time.time() - ts < _SECTOR_CACHE_TTL:
                return sector

        # Try sector_rotation hints first
        try:
            from sector_rotation import STOCK_SECTOR_HINTS
            if ticker in STOCK_SECTOR_HINTS:
                sector = STOCK_SECTOR_HINTS[ticker]
                _SECTOR_CACHE[ticker] = (sector, time.time()); _evict_sector_cache()
                return sector
        except ImportError:
            pass

        # Fallback: Alpaca asset endpoint
        try:
            url = f"{ALPACA_TRADE_URL}/assets/{ticker}"
            resp = requests.get(url, headers=self.headers, timeout=5)
            if resp.ok:
                data = resp.json()
                sector = data.get('sector', '')
                _SECTOR_CACHE[ticker] = (sector, time.time()); _evict_sector_cache()
                return sector
        except Exception:
            pass

        _SECTOR_CACHE[ticker] = ('', time.time()); _evict_sector_cache()
        return ''

    def compute_technicals(self, ticker: str, bars: List[Dict] = None) -> Dict:
        """
        Compute all technical indicators for a ticker.
        Returns dict ready for CompositeScorer.
        v2.1: Now includes sector, channel_up, breakout, amd_detected.
        """
        if not bars:
            bars = self.get_bars(ticker)

        if len(bars) < 200:
            logger.warning(f"{ticker}: Only {len(bars)} bars (need 200+)")
            if len(bars) < 20:
                return {'ticker': ticker, 'error': 'insufficient_data'}

        closes = [b['c'] for b in bars]
        highs = [b['h'] for b in bars]
        lows = [b['l'] for b in bars]
        volumes = [b['v'] for b in bars]

        price = closes[-1] if closes else 0

        result = {
            'ticker': ticker,
            'price': price,
            'sector': self.get_sector(ticker),
            'sma_20': self._sma(closes, 20),
            'sma_200': self._sma(closes, 200) if len(closes) >= 200 else 0,
            'ema_50': self._ema(closes, 50) if len(closes) >= 50 else 0,
            'williams_r': self._williams_r(highs, lows, closes, 14),
            'rsi': self._rsi(closes, 14),
            'adx': self._adx(highs, lows, closes, 14),
            'macd_hist': 0,
            'macd_hist_prev': 0,
            'atr': self._atr(highs, lows, closes, 14),
            'volume_ratio': self._volume_ratio(volumes, 20),
            'basing': self._detect_basing(closes, highs, lows),
            'elephant_bar': self._detect_elephant(bars),
            'price_change_5d': self._price_change(closes, 5),
            'channel_up': self._detect_channel_up(highs, lows, 20),
            'breakout': self._detect_breakout(closes, highs, lows),
            'amd_detected': self._detect_amd(bars),
        }

        # MACD
        macd_line, signal_line, histogram = self._macd(closes)
        if histogram:
            result['macd_hist'] = histogram[-1]
            result['macd_hist_prev'] = histogram[-2] if len(histogram) > 1 else 0

        return result

    # ========== INDICATOR CALCULATIONS ==========

    @staticmethod
    def _sma(data: List[float], period: int) -> float:
        """Simple Moving Average."""
        if len(data) < period:
            return 0
        return sum(data[-period:]) / period

    @staticmethod
    def _ema(data: List[float], period: int) -> float:
        """Exponential Moving Average."""
        if len(data) < period:
            return 0
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    @staticmethod
    def _rsi(closes: List[float], period: int = 14) -> float:
        """Relative Strength Index."""
        if len(closes) < period + 1:
            return 50
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _williams_r(highs: List[float], lows: List[float],
                    closes: List[float], period: int = 14) -> float:
        """Williams %R."""
        if len(highs) < period:
            return -50
        highest = max(highs[-period:])
        lowest = min(lows[-period:])
        if highest == lowest:
            return -50
        return ((highest - closes[-1]) / (highest - lowest)) * -100

    @staticmethod
    def _atr(highs: List[float], lows: List[float],
             closes: List[float], period: int = 14) -> float:
        """Average True Range."""
        if len(highs) < period + 1:
            return 0
        true_ranges = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return 0
        atr = sum(true_ranges[:period]) / period
        for tr in true_ranges[period:]:
            atr = (atr * (period - 1) + tr) / period
        return atr

    @staticmethod
    def _adx(highs: List[float], lows: List[float],
             closes: List[float], period: int = 14) -> float:
        """Average Directional Index (simplified)."""
        if len(highs) < period * 2:
            return 0
        plus_dm = []
        minus_dm = []
        tr_list = []
        for i in range(1, len(highs)):
            up = highs[i] - highs[i-1]
            down = lows[i-1] - lows[i]
            plus_dm.append(up if up > down and up > 0 else 0)
            minus_dm.append(down if down > up and down > 0 else 0)
            tr = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i-1]),
                     abs(lows[i] - closes[i-1]))
            tr_list.append(tr)

        atr = sum(tr_list[:period]) / period
        plus_di_sum = sum(plus_dm[:period]) / period
        minus_di_sum = sum(minus_dm[:period]) / period

        for i in range(period, len(tr_list)):
            atr = (atr * (period - 1) + tr_list[i]) / period
            plus_di_sum = (plus_di_sum * (period - 1) + plus_dm[i]) / period
            minus_di_sum = (minus_di_sum * (period - 1) + minus_dm[i]) / period

        if atr == 0:
            return 0
        plus_di = 100 * plus_di_sum / atr
        minus_di = 100 * minus_di_sum / atr
        dx_sum = plus_di + minus_di
        if dx_sum == 0:
            return 0
        dx = 100 * abs(plus_di - minus_di) / dx_sum
        return dx

    def _macd(self, closes: List[float],
              fast: int = 12, slow: int = 26, signal: int = 9):
        """MACD line, signal line, histogram."""
        if len(closes) < slow + signal:
            return [], [], []
        fast_ema = self._ema_series(closes, fast)
        slow_ema = self._ema_series(closes, slow)
        macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
        signal_line = (self._ema_series(macd_line, signal)
                       if len(macd_line) >= signal else [])
        min_len = min(len(macd_line), len(signal_line))
        histogram = [macd_line[-(min_len-i)] - signal_line[-(min_len-i)]
                     for i in range(min_len)]
        return macd_line, signal_line, histogram

    @staticmethod
    def _ema_series(data: List[float], period: int) -> List[float]:
        """Full EMA series."""
        if len(data) < period:
            return []
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        result = [ema]
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
            result.append(ema)
        return result

    @staticmethod
    def _volume_ratio(volumes: List[int], period: int = 20) -> float:
        """Current volume vs average volume ratio."""
        if len(volumes) < period + 1:
            return 1.0
        avg_vol = sum(volumes[-(period+1):-1]) / period
        if avg_vol == 0:
            return 1.0
        return volumes[-1] / avg_vol

    @staticmethod
    def _detect_basing(closes: List[float], highs: List[float],
                       lows: List[float], lookback: int = 10) -> bool:
        """Detect tight price consolidation (basing)."""
        if len(closes) < lookback:
            return False
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        price_range = max(recent_highs) - min(recent_lows)
        avg_price = sum(closes[-lookback:]) / lookback
        if avg_price == 0:
            return False
        return (price_range / avg_price) < 0.05

    @staticmethod
    def _detect_elephant(bars: List[Dict], lookback: int = 20) -> bool:
        """Detect elephant bar (large bullish candle)."""
        if len(bars) < lookback:
            return False
        recent = bars[-lookback:]
        avg_range = sum(b['h'] - b['l'] for b in recent) / lookback
        last = bars[-1]
        body = last['c'] - last['o']
        bar_range = last['h'] - last['l']
        return body > 0 and bar_range > (avg_range * 2)

    @staticmethod
    def _price_change(closes: List[float], days: int = 5) -> float:
        """Percent price change over N days."""
        if len(closes) < days + 1:
            return 0
        old = closes[-(days+1)]
        if old == 0:
            return 0
        return ((closes[-1] - old) / old) * 100

    # ========== NEW v2.1 PATTERN DETECTORS ==========

    @staticmethod
    def _detect_channel_up(highs: List[float], lows: List[float],
                           lookback: int = 20) -> bool:
        """
        Detect ascending channel (higher highs + higher lows).
        Checks 4 segments of the lookback period.
        """
        if len(highs) < lookback:
            return False
        recent_h = highs[-lookback:]
        recent_l = lows[-lookback:]
        seg = lookback // 4
        if seg < 2:
            return False
        seg_highs = []
        seg_lows = []
        for i in range(4):
            s = i * seg
            e = s + seg
            seg_highs.append(max(recent_h[s:e]))
            seg_lows.append(min(recent_l[s:e]))
        hh = all(seg_highs[i] < seg_highs[i+1] for i in range(3))
        hl = all(seg_lows[i] < seg_lows[i+1] for i in range(3))
        return hh and hl

    @staticmethod
    def _detect_breakout(closes: List[float], highs: List[float],
                         lows: List[float], lookback: int = 20) -> bool:
        """
        Detect breakout from base: tight range then price
        breaks above the consolidation high.
        """
        if len(closes) < lookback + 5:
            return False
        base_h = highs[-(lookback+5):-5]
        base_l = lows[-(lookback+5):-5]
        base_c = closes[-(lookback+5):-5]
        avg_p = sum(base_c) / len(base_c) if base_c else 1
        b_range = max(base_h) - min(base_l)
        was_basing = (b_range / avg_p) < 0.06 if avg_p > 0 else False
        if not was_basing:
            return False
        return closes[-1] > max(base_h)

    @staticmethod
    def _detect_amd(bars: List[Dict], lookback: int = 5) -> bool:
        """
        Simplified AMD detection: tight consolidation
        followed by large move with volume surge.
        """
        if len(bars) < lookback + 1:
            return False
        accum = bars[-(lookback+1):-1]
        a_range = max(b['h'] for b in accum) - min(b['l'] for b in accum)
        avg_p = sum(b['c'] for b in accum) / len(accum)
        if avg_p == 0:
            return False
        if (a_range / avg_p) >= 0.04:
            return False
        last = bars[-1]
        body = abs(last['c'] - last['o'])
        avg_body = sum(abs(b['c'] - b['o']) for b in accum) / len(accum)
        avg_vol = sum(b['v'] for b in accum) / len(accum)
        big = body > (avg_body * 2) if avg_body > 0 else False
        vol = last['v'] > (avg_vol * 1.5) if avg_vol > 0 else False
        return big and vol

    # ========== BATCH PROCESSING ==========

    def check_tickers(self, tickers: List[str]) -> List[Dict]:
        """Compute technicals for a list of tickers."""
        results = []
        for ticker in tickers:
            try:
                tech = self.compute_technicals(ticker)
                results.append(tech)
                logger.info(
                    f"Checked {ticker}: "
                    f"RSI={tech.get('rsi', 0):.1f} "
                    f"W%R={tech.get('williams_r', 0):.1f}"
                )
            except Exception as e:
                logger.error(f"Tech check failed for {ticker}: {e}")
        return results


# ========== MODULE-LEVEL CONVENIENCE ==========
technical_checker = TechnicalChecker()


def check_technicals(tickers: List[str]) -> List[Dict]:
    """Convenience function for pipeline use."""
    return technical_checker.check_tickers(tickers)


# ========== PHASE 5: ENHANCED INDICATORS v2.2 ==========

def compute_vwap(bars: List[Dict]) -> float:
  """Calculate VWAP from intraday bars."""
  if not bars:
    return 0.0
  try:
    total_vp = 0.0
    total_vol = 0.0
    for b in bars:
      typical = (b['h'] + b['l'] + b['c']) / 3
      vol = b.get('v', 0)
      total_vp += typical * vol
      total_vol += vol
    return total_vp / total_vol if total_vol > 0 else 0.0
  except Exception:
    return 0.0


def detect_rsi_divergence(closes: List[float], rsi_values: List[float],
                          lookback: int = 20) -> str:
  """
  Detect RSI divergence vs price.
  Returns: 'bullish_div', 'bearish_div', or 'none'
  """
  if len(closes) < lookback or len(rsi_values) < lookback:
    return 'none'
  try:
    mid = lookback // 2
    price_first = min(closes[-lookback:-mid])
    price_second = min(closes[-mid:])
    rsi_first = min(rsi_values[-lookback:-mid])
    rsi_second = min(rsi_values[-mid:])
    # Bullish: price lower low but RSI higher low
    if price_second < price_first and rsi_second > rsi_first:
      return 'bullish_div'
    price_first_h = max(closes[-lookback:-mid])
    price_second_h = max(closes[-mid:])
    rsi_first_h = max(rsi_values[-lookback:-mid])
    rsi_second_h = max(rsi_values[-mid:])
    # Bearish: price higher high but RSI lower high
    if price_second_h > price_first_h and rsi_second_h < rsi_first_h:
      return 'bearish_div'
    return 'none'
  except Exception:
    return 'none'


def compute_rsi_series(closes: List[float], period: int = 14) -> List[float]:
  """Full RSI series for divergence detection."""
  if len(closes) < period + 1:
    return [50.0] * len(closes)
  deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
  gains = [d if d > 0 else 0 for d in deltas]
  losses = [-d if d < 0 else 0 for d in deltas]
  avg_gain = sum(gains[:period]) / period
  avg_loss = sum(losses[:period]) / period
  rsi_list = [50.0] * period
  for i in range(period, len(gains)):
    avg_gain = (avg_gain * (period - 1) + gains[i]) / period
    avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
      rsi_list.append(100.0)
    else:
      rs = avg_gain / avg_loss
      rsi_list.append(100 - (100 / (1 + rs)))
  return rsi_list


def compute_enhanced_technicals(ticker: str, checker: 'TechnicalChecker' = None) -> Dict:
  """Enhanced technical computation with VWAP, RSI divergence."""
  if checker is None:
    checker = technical_checker
  base = checker.compute_technicals(ticker)
  if base.get('error'):
    return base
  try:
    bars = checker.get_bars(ticker)
    if bars:
      base['vwap'] = compute_vwap(bars)
      closes = [b['c'] for b in bars]
      rsi_series = compute_rsi_series(closes, 14)
      base['rsi_divergence'] = detect_rsi_divergence(closes, rsi_series)
      # Distance from VWAP in ATR units
      if base.get('vwap') and base.get('atr') and base['atr'] > 0:
        base['vwap_distance_atr'] = (base['price'] - base['vwap']) / base['atr']
      else:
        base['vwap_distance_atr'] = 0
  except Exception as e:
    logger.error(f"Enhanced technicals failed for {ticker}: {e}")
  return base


def check_enhanced_technicals(tickers: List[str]) -> List[Dict]:
  """Enhanced convenience function with VWAP + RSI divergence."""
  results = []
  for ticker in tickers:
    try:
      tech = compute_enhanced_technicals(ticker)
      results.append(tech)
    except Exception as e:
      logger.error(f"Enhanced tech check failed for {ticker}: {e}")
  return results
