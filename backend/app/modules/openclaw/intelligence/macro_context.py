#!/usr/bin/env python3
"""
macro_context.py - Macro Economic Context Module for OpenClaw

Fetches real-time macroeconomic data from FRED (Federal Reserve Economic Data)
to provide context for the RegimeDetector and daily scan pipeline.

Data sources:
    - FRED API: VIX (VIXCLS), HY spread (BAMLH0A0HYM2), Fed Funds Rate (FEDFUNDS),
                10Y-2Y spread (T10Y2Y), SPY breadth via FRED proxies
    - Fallback: requests-based polling if fredapi not available

Used by:
    - regime.py: get_vix(), detect_crash(), get_regime_summary()
    - daily_scanner.py: Step 0 macro context enrichment
"""
import os
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# FRED series IDs for key macro indicators
FRED_SERIES = {
    'vix': 'VIXCLS',              # CBOE VIX
    'hy_spread': 'BAMLH0A0HYM2', # ICE BofA HY OAS spread
    'fed_funds': 'FEDFUNDS',      # Federal Funds Rate
    'yield_curve': 'T10Y2Y',      # 10Y-2Y Treasury spread
    'unemployment': 'UNRATE',     # Unemployment rate
    'inflation': 'CPIAUCSL',      # CPI (YoY proxy)
    'sp500': 'SP500',             # S&P 500 level
    'ny_spread': 'TEDRATE',       # TED spread (proxy for NY Fed spread)
}

# Cache TTL in seconds (FRED updates daily, so 4 hours is fine)
CACHE_TTL_SECONDS = 4 * 3600


class MacroContext:
    """
    Fetches and caches macroeconomic data from FRED.
    Provides clean interfaces for regime detection.
    """

    def __init__(self, fred_api_key: Optional[str] = None):
        self.api_key = fred_api_key or os.getenv('FRED_API_KEY', '')
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._fred = None
        self._init_fred_client()

    def _init_fred_client(self):
        """Initialize the fredapi client if available."""
        if not self.api_key:
            logger.warning("FRED_API_KEY not set - macro context will use fallback values")
            return
        try:
            from fredapi import Fred
            self._fred = Fred(api_key=self.api_key)
            logger.info("FRED API client initialized")
        except ImportError:
            logger.warning("fredapi not installed - run: pip install fredapi")
        except Exception as e:
            logger.error(f"FRED API init failed: {e}")

    def _is_cached(self, key: str) -> bool:
        """Check if a cached value is still fresh."""
        if key not in self._cache or key not in self._cache_time:
            return False
        age = (datetime.now() - self._cache_time[key]).total_seconds()
        return age < CACHE_TTL_SECONDS

    def _fetch_series_latest(self, series_id: str) -> Optional[float]:
        """Fetch the most recent value for a FRED series."""
        if not self._fred:
            return None
        cache_key = f"fred_{series_id}"
        if self._is_cached(cache_key):
            return self._cache[cache_key]
        try:
            series = self._fred.get_series(series_id, limit=5)
            if series is not None and len(series) > 0:
                value = float(series.dropna().iloc[-1])
                self._cache[cache_key] = value
                self._cache_time[cache_key] = datetime.now()
                logger.debug(f"FRED {series_id}: {value}")
                return value
        except Exception as e:
            logger.error(f"FRED fetch failed for {series_id}: {e}")
        return None

    def get_vix(self) -> float:
        """
        Get current VIX level from FRED.
        Returns cached value or fallback of 18.0 (neutral).
        """
        vix = self._fetch_series_latest(FRED_SERIES['vix'])
        if vix is not None:
            return vix
                # Fallback: try Alpaca snapshot API
        vix = self._fetch_vix_fallback()
        return vix if vix else 18.0

    def _fetch_vix_fallback(self) -> Optional[float]:
        """Fallback VIX fetch via Finviz if FRED unavailable.

        Uses Finviz quote page for VIXY (VIX proxy ETF) as a rough
        approximation.  No Yahoo Finance / yfinance dependency.
        """
        try:
            import requests
            # Use Finviz quote page for VIX proxy
            url = "https://finviz.com/quote.ashx?t=VIXY"
            resp = requests.get(
                url, timeout=5,
                headers={"User-Agent": "Embodier/1.0"},
            )
            if resp.status_code == 200 and "<title>" in resp.text:
                # VIXY price is NOT the VIX index itself, but a rough
                # directional proxy.  Map VIXY price to approximate VIX:
                # VIXY ~$15 ≈ VIX 15, VIXY ~$25 ≈ VIX 25 (very rough)
                import re
                match = re.search(r'class="snapshot-td2-cp".*?>(\d+\.\d+)', resp.text)
                if match:
                    vixy_price = float(match.group(1))
                    logger.info(f"VIX fallback (Finviz VIXY): {vixy_price}")
                    return vixy_price
        except Exception as e:
            logger.warning(f"VIX fallback failed: {e}")
        return None

    def get_hy_spread(self) -> float:
        """
        Get High Yield OAS spread from FRED.
        Used for crash detection (threshold: >700bps = stress).
        Returns spread in basis points.
        """
        spread = self._fetch_series_latest(FRED_SERIES['hy_spread'])
        # FRED returns in percentage (e.g., 3.5 = 350bps)
        if spread is not None:
            return spread * 100  # convert to bps
        return 350.0  # neutral fallback

    def get_yield_curve(self) -> float:
        """
        Get 10Y-2Y Treasury spread from FRED.
        Negative = inverted = recession signal.
        """
        spread = self._fetch_series_latest(FRED_SERIES['yield_curve'])
        return spread if spread is not None else 0.5

    def get_fed_funds_rate(self) -> float:
        """Get current Federal Funds Rate from FRED."""
        rate = self._fetch_series_latest(FRED_SERIES['fed_funds'])
        return rate if rate is not None else 5.25

    def get_full_macro_snapshot(self) -> Dict[str, Any]:
        """
        Fetch all macro indicators at once.
        Returns a dict with all key economic metrics.
        """
        vix = self.get_vix()
        hy_spread = self.get_hy_spread()
        yield_curve = self.get_yield_curve()
        fed_funds = self.get_fed_funds_rate()

        # Compute macro risk score (0-10, higher = more risk)
        macro_risk = 0.0
        if vix > 30:
            macro_risk += 3.0
        elif vix > 20:
            macro_risk += 1.5
        if hy_spread > 700:
            macro_risk += 3.0
        elif hy_spread > 500:
            macro_risk += 1.5
        if yield_curve < 0:
            macro_risk += 2.0
        elif yield_curve < 0.5:
            macro_risk += 0.5
        if fed_funds > 5.0:
            macro_risk += 1.0
        macro_risk = min(macro_risk, 10.0)

        snapshot = {
            'vix': vix,
            'hy_spread_bps': hy_spread,
            'yield_curve_10y2y': yield_curve,
            'fed_funds_rate': fed_funds,
            'macro_risk_score': macro_risk,
            'macro_regime': self._score_to_regime(macro_risk),
            'regime': self._score_to_regime(macro_risk),  # alias for daily_scanner.py
            'fear_greed_value': self._get_fear_greed_value(),
            'fear_greed_label': self._get_fear_greed_label(),
            'fetched_at': datetime.now().isoformat(),
        }
        logger.info(
            f"Macro snapshot: VIX={vix:.1f}, HY={hy_spread:.0f}bps, "
            f"Curve={yield_curve:.2f}%, Risk={macro_risk:.1f}/10"
        )
        return snapshot

    def _get_fear_greed_value(self) -> Optional[int]:
        """Fetch CNN Fear & Greed index value (0-100) via public API."""
        cache_key = 'fear_greed'
        if self._is_cached(cache_key):
            return self._cache[cache_key]
        try:
            import requests
            url = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata'
            resp = requests.get(url, timeout=5, headers={'User-Agent': 'OpenClaw/1.0'})
            if resp.status_code == 200:
                data = resp.json()
                value = int(data['fear_and_greed']['score'])
                self._cache[cache_key] = value
                self._cache_time[cache_key] = datetime.now()
                logger.info(f"Fear & Greed: {value}")
                return value
        except Exception as e:
            logger.warning(f"Fear & Greed fetch failed: {e}")
        return None

    def _get_fear_greed_label(self) -> str:
        """Return Fear & Greed label string based on value."""
        value = self._get_fear_greed_value()
        if value is None:
            return 'N/A'
        if value <= 25:
            return 'Extreme Fear'
        elif value <= 45:
            return 'Fear'
        elif value <= 55:
            return 'Neutral'
        elif value <= 75:
            return 'Greed'
        else:
            return 'Extreme Greed'

    def _score_to_regime(self, score: float) -> str:
        """Convert macro risk score to regime label."""
        if score >= 6.0:
            return 'RED'
        elif score >= 3.0:
            return 'YELLOW'
        else:
            return 'GREEN'

    def is_crash_environment(self) -> bool:
        """
        Returns True if macro indicators suggest crash/stress conditions.
        Used by regime.py detect_crash() as real data source.
        """
        vix = self.get_vix()
        hy_spread = self.get_hy_spread()
        # Crash conditions:
        # - VIX single-day spike > 40 (extreme fear)
        # - HY spread > 700bps (credit stress)
        if vix > 40:
            logger.warning(f"CRASH SIGNAL: VIX={vix:.1f} > 40")
            return True
        if hy_spread > 700:
            logger.warning(f"CRASH SIGNAL: HY spread={hy_spread:.0f}bps > 700")
            return True
        return False

    def get_breadth_proxy(self) -> float:
        """
        Estimate market breadth using yield curve as proxy.
        Returns a 0-1 float (higher = broader market participation).
        Falls back to 0.5 (neutral).
        """
        curve = self.get_yield_curve()
        # Normalize: -1% to +2% -> 0 to 1
        normalized = max(0.0, min(1.0, (curve + 1.0) / 3.0))
        return normalized


# Module-level singleton
macro_context = MacroContext()


def get_macro_snapshot() -> Dict[str, Any]:
    """Convenience function for daily_scanner.py integration."""
    return macro_context.get_full_macro_snapshot()


def get_vix() -> float:
    """Quick VIX access for regime.py."""
    return macro_context.get_vix()


def is_crash_environment() -> bool:
    """Quick crash check for regime.py."""
    return macro_context.is_crash_environment()
