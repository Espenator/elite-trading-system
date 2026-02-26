#!/usr/bin/env python3
"""
Finviz Scanner Module for OpenClaw
Scans Finviz Elite for stocks matching PAS v8 Gate criteria.

Uses the Finviz Elite Export API:
  https://elite.finviz.com/export.ashx?v=111&f=[filters]&auth=[token]

Filter presets:
  - Channel Up + PA>20SMA + PA>200SMA  (PAS v8 Gate PASS)
  - Swing pullback: 20SMA cross + above 200SMA
  - Breakout: New High + volume surge
"""
import os
import csv
import io
import logging
import requests
from datetime import datetime, date
from config import FINVIZ_EXPORT_BASE_URL, FINVIZ_API_KEY

logger = logging.getLogger(__name__)

# Finviz -> standard symbol mapping (Finviz strips dots from tickers like BRK.B)
SYMBOL_MAP = {
    'BRKB': 'BRK-B',
    'BRKA': 'BRK-A',
}

# ========== FILTER PRESETS ==========
FINVIZ_FILTERS = {
    'pas_v8_gate': {
        'description': 'Channel Up + PA>20SMA + PA>200SMA (PAS v8 Gate PASS)',
        'filters': 'ta_pattern_channelup,ta_sma20_pa,ta_sma200_pa',
        'sort': '-change',
    },
    'swing_pullback': {
        'description': 'Channel Up + 20SMA support + above 200SMA',
        'filters': 'ta_pattern_channelup,ta_sma20_cross20above,ta_sma200_pa',
        'sort': '-change',
    },
    'breakout': {
        'description': 'New High + Volume surge + above all SMAs',
        'filters': 'ta_highlow52w_nh,sh_avgvol_o500,ta_sma20_pa,ta_sma200_pa',
        'sort': '-change',
    },
    'momentum': {
        'description': 'SMA20 rising + PA>20 + PA>200 + high rel volume',
        'filters': 'ta_sma20_pa,ta_sma200_pa,sh_relvol_o1.5',
        'sort': '-change',
    },
}

# Custom column sets for export
FINVIZ_COLUMNS = {
    'default': '',  # Use Finviz default columns
    'pas_v8': '0,1,2,3,4,5,6,7,65,66,67,68,69,70',  # Ticker,Company,Sector,Industry,Country,MCap,Price,Change,SMA20,SMA50,SMA200,Volume,RelVol,AvgVol
}


class FinvizScanner:
    """
    Scans Finviz Elite screener via Export API.
    Authenticates with &auth= token per Finviz Elite docs.
    """

    def __init__(self):
        self.api_key = FINVIZ_API_KEY or os.getenv('FINVIZ_API_KEY', '')
        self.base_url = FINVIZ_EXPORT_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def scan(self, preset='pas_v8_gate', max_results=50, columns='default'):
        """
        Run a Finviz scan using a preset filter.
        Returns list of dicts with symbol data.
        """
        if not self.api_key:
            logger.error("No FINVIZ_API_KEY configured. Set in .env file.")
            return []

        if preset not in FINVIZ_FILTERS:
            logger.error(f"Unknown preset: {preset}")
            return []

        filter_config = FINVIZ_FILTERS[preset]
        url = self._build_url(filter_config, columns)

        try:
            logger.info(f"Finviz scan: {filter_config['description']}")
            logger.info(f"URL: {url[:80]}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            results = self._parse_csv(response.text, preset)
            logger.info(f"Finviz: {len(results)} results returned")
            return results[:max_results]

        except requests.RequestException as e:
            logger.error(f"Finviz scan failed: {e}")
            return []

    def _build_url(self, filter_config, columns='default'):
        """
        Build Finviz Elite export URL.
        Format: https://elite.finviz.com/export.ashx?v=111&f=[filters]&ft=4&o=[sort]&auth=[token]
        """
        url = f"{self.base_url}?v=111&f={filter_config['filters']}&ft=4&o={filter_config['sort']}"

        # Add custom columns if specified
        col_str = FINVIZ_COLUMNS.get(columns, '')
        if col_str:
            url += f"&c={col_str}"

        # Add auth token (required for Elite export)
        url += f"&auth={self.api_key}"
        return url

    def _parse_csv(self, csv_text, preset='pas_v8_gate'):
        """
        Parse Finviz CSV export into list of dicts.
        Handles the standard Finviz Elite export format.
        """
        results = []
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
        except Exception as e:
            logger.error(f"CSV parse init failed: {e}")
            return []

        for row in reader:
            try:
                # Parse change% - Finviz returns as "5.50%" or "-2.30%"
                change_raw = row.get('Change', '0')
                if isinstance(change_raw, str):
                    change_raw = change_raw.replace('%', '').strip()
                change_pct = float(change_raw) if change_raw else 0.0

                # Parse price
                price_raw = row.get('Price', '0')
                price = float(price_raw) if price_raw else 0.0

                results.append({
                    'ticker': SYMBOL_MAP.get(row.get('Ticker', '').strip(), row.get('Ticker', '').strip()),
                    'company': row.get('Company', '').strip(),
                    'sector': row.get('Sector', '').strip(),
                    'industry': row.get('Industry', '').strip(),
                    'market_cap': row.get('Market Cap', ''),
                    'price': price,
                    'change_pct': change_pct,
                    'volume': row.get('Volume', ''),
                    'avg_volume': row.get('Avg Volume', ''),
                    'rel_volume': row.get('Relative Volume', ''),
                    'sma20': row.get('SMA20', ''),
                    'sma50': row.get('SMA50', ''),
                    'sma200': row.get('SMA200', ''),
                    'rsi': row.get('RSI (14)', ''),
                    'atr': row.get('ATR (14)', ''),
                    'pattern': row.get('Pattern', ''),
                    'scan_date': date.today().isoformat(),
                    'preset': preset,
                    'source': 'finviz',
                })
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping row: {e}")
                continue

        return results

    def get_top_symbols(self, preset='pas_v8_gate', limit=20):
        """Get just the ticker symbols from a scan."""
        results = self.scan(preset=preset, max_results=limit)
        return [r['ticker'] for r in results if r['ticker']]

    def scan_multiple_presets(self, presets=None, max_per_preset=20):
        """
        Run multiple preset scans and merge results.
        Symbols appearing in multiple presets get higher priority.
        """
        if presets is None:
            presets = ['pas_v8_gate', 'breakout']

        all_results = {}
        for preset in presets:
            results = self.scan(preset=preset, max_results=max_per_preset)
            for r in results:
                ticker = r['ticker']
                if ticker in all_results:
                    all_results[ticker]['preset_count'] += 1
                    all_results[ticker]['presets'].append(preset)
                else:
                    r['preset_count'] = 1
                    r['presets'] = [preset]
                    all_results[ticker] = r

        # Sort by preset_count (multi-preset hits first), then by change%
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: (x['preset_count'], x['change_pct']),
            reverse=True
        )
        return sorted_results

    def format_scan_summary(self, results, limit=15):
        """Format scan results as a Slack-friendly message."""
        if not results:
            return "No results found."

        today = date.today().strftime('%b %d')
        lines = [f"*Finviz PAS v8 Gate Scan - {today}*"]
        lines.append(f"Filter: Channel Up + PA>20SMA + PA>200SMA")
        lines.append(f"Results: {len(results)} symbols\n")

        for i, r in enumerate(results[:limit], 1):
            chg = r.get('change_pct', 0)
            emoji = ':chart_with_upwards_trend:' if chg > 0 else ':small_red_triangle_down:'
            sector = r.get('sector', '')[:12]
            lines.append(
                f"{emoji} *{r['ticker']}* ${r['price']:.2f} "
                f"({chg:+.2f}%) | {sector}"
            )

        return '\n'.join(lines)


# Singleton
finviz_scanner = FinvizScanner()
