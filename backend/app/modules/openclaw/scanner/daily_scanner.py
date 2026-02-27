#!/usr/bin/env python3
"""
Daily Scanner Orchestrator for OpenClaw v3.0
Runs the full daily scan pipeline WITH v2 module integration:
1. Finviz Elite screener (PAS v8 Gate criteria)
2. Unusual Whales flow scan
3. Cross-reference for confluence
4. ** NEW: Technical indicator calculations via Alpaca **
5. ** NEW: Multi-timeframe alignment scoring **
6. ** NEW: 100-point composite scoring (5-pillar system) **
7. ** NEW: Earnings calendar safety filter **
8. ** NEW: Sector rotation bonus/penalty **
9. ** NEW: Position sizing recommendations **
10. Post scored watchlist to Slack #oc-trade-desk
11. Update TradingView watchlist via webhook
12. Fetch FOM expected moves from Discord and post to Slack
Scheduled to run daily at configurable times (pre-market, post-market).
"""
import os
import logging
import json
import time
from datetime import datetime, date
from finviz_scanner import finviz_scanner
from whale_flow import whale_flow_scanner
from regime import regime_detector
from config import *
from fom_expected_moves import run_fom_em_scrape, run_fom_em_post
from macro_context import get_macro_snapshot
from tradingview_watchlist import tv_watchlist
try:
    from memory import trade_memory
except ImportError:
    trade_memory = None

# ========== v2.0 MODULE IMPORTS ==========
# Track failed imports for startup health check
_FAILED_IMPORTS = []
_LOADED_MODULES = []
try:
    from composite_scorer import CompositeScorer
    _LOADED_MODULES.append('CompositeScorer')
except ImportError as _e:
    CompositeScorer = None
    _FAILED_IMPORTS.append(('composite_scorer', str(_e)))
try:
    from technical_checker import TechnicalChecker as _TC
    check_technicals = _TC().check_batch if _TC else None
    _LOADED_MODULES.append('TechnicalChecker')
except ImportError as _e:
    check_technicals = None
    _FAILED_IMPORTS.append(('technical_checker', str(_e)))
try:
    from mtf_alignment import get_mtf_alignment, batch_mtf_alignment
    _LOADED_MODULES.append('mtf_alignment')
except ImportError as _e:
    get_mtf_alignment = None
    batch_mtf_alignment = None
    _FAILED_IMPORTS.append(('mtf_alignment', str(_e)))
try:
    from position_sizer import calculate_position
    _LOADED_MODULES.append('position_sizer')
except ImportError as _e:
    calculate_position = None
    _FAILED_IMPORTS.append(('position_sizer', str(_e)))
try:
    from earnings_calendar import filter_by_earnings, get_earnings_penalties
    _LOADED_MODULES.append('earnings_calendar')
except ImportError as _e:
    filter_by_earnings = None
    get_earnings_penalties = None
    _FAILED_IMPORTS.append(('earnings_calendar', str(_e)))
try:
    from sector_rotation import get_sector_rankings
    _LOADED_MODULES.append('sector_rotation')
except ImportError as _e:
    get_sector_rankings = None
    _FAILED_IMPORTS.append(('sector_rotation', str(_e)))
try:
    from session_monitor import get_current_session
    _LOADED_MODULES.append('session_monitor')
except ImportError as _e:
    get_current_session = None
    _FAILED_IMPORTS.append(('session_monitor', str(_e)))
try:
    from alpaca_client import alpaca_client
    _LOADED_MODULES.append('alpaca_client')
except ImportError as _e:
    alpaca_client = None
    _FAILED_IMPORTS.append(('alpaca_client', str(_e)))

logger = logging.getLogger(__name__)

# Slack channel IDs
OC_TRADE_DESK = os.getenv('OC_TRADE_DESK_CHANNEL', 'C0AF9RW7W94')
OC_SIGNALS_RAW = os.getenv('OC_SIGNALS_RAW_CHANNEL', 'C0AFQR1GUSV')


# ========== STARTUP HEALTH CHECK ==========
def _log_module_health():
    """Log which v2.0 modules loaded successfully vs failed."""
    if _LOADED_MODULES:
        logger.info(
            f"[HEALTH] Loaded modules ({len(_LOADED_MODULES)}): "
            f"{', '.join(_LOADED_MODULES)}"
        )
    if _FAILED_IMPORTS:
        for mod, err in _FAILED_IMPORTS:
            severity = 'CRITICAL' if mod in ('composite_scorer', 'technical_checker') else 'WARNING'
            if severity == 'CRITICAL':
                logger.error(
                    f"[HEALTH] CRITICAL module missing: {mod} - {err}"
                )
            else:
                logger.warning(
                    f"[HEALTH] Optional module missing: {mod} - {err}"
                )
    if not _FAILED_IMPORTS:
        logger.info("[HEALTH] All v2.0 modules loaded OK")


# ========== RETRY UTILITY ==========
def _retry(func, *args, retries=3, backoff=2.0, label='call', **kwargs):
    """Retry a function with exponential backoff on exception."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            wait = backoff ** (attempt - 1)
            logger.warning(
                f"[RETRY] {label} failed (attempt {attempt}/{retries}): "
                f"{exc}. Retrying in {wait:.1f}s..."
            )
            if attempt < retries:
                time.sleep(wait)
    logger.error(f"[RETRY] {label} gave up after {retries} attempts: {last_exc}")
    raise last_exc


class DailyScanner:
    """
    Orchestrates the full daily scan pipeline.
    v3.0: Now integrates composite scoring, technicals, MTF,
    earnings safety, sector rotation, and position sizing.
    """
    def __init__(self, slack_client=None):
        self.slack_client = slack_client
        self.scan_results = {
            'finviz': [],
            'whale_flow': [],
            'confluence': [],
            'watchlist': [],
            'regime': '',
            'scan_date': '',
            'fom_expected_moves': None,
            'macro': None,
            'scored_results': [],
        }

    def run_full_scan(self):
        """
        Execute the complete daily scan pipeline.
        Returns the compiled and SCORED watchlist.
        """
        today = date.today().isoformat()
        self.scan_results['scan_date'] = today
        logger.info(f"Starting daily scan v3.0 for {today}")

        # Health check: log which modules are available
        _log_module_health()

        # Step 0: Get macro context snapshot
        try:
            macro = _retry(
                get_macro_snapshot,
                retries=3, backoff=2.0, label='macro_snapshot'
            )
            self.scan_results['macro'] = macro
            logger.info(f"Macro regime: {macro.get('regime', 'N/A')}, "
                        f"Fear/Greed: {macro.get('fear_greed_value', 'N/A')}")
        except Exception as e:
            logger.error(f"Macro snapshot failed: {e}")
            self.scan_results['macro'] = {}

        # Step 1: Get market regime
        try:
            regime = regime_detector.get_regime_summary()
            self.scan_results['regime'] = regime
            logger.info(f"Regime: {regime_detector.current_regime}")
        except Exception as e:
            logger.error(f"Regime check failed: {e}")
            self.scan_results['regime'] = 'UNKNOWN'

        # Step 2: Run Finviz scan (with retry)
        try:
            finviz_results = _retry(
                finviz_scanner.scan,
                preset='pas_v8_gate', max_results=30,
                retries=3, backoff=2.0, label='finviz_scan'
            )
            self.scan_results['finviz'] = finviz_results
            logger.info(f"Finviz: {len(finviz_results)} results")
        except Exception as e:
            logger.error(f"Finviz scan failed: {e}")

        # Step 3: Get whale flow (with retry)
        try:
            whale_tickers = _retry(
                whale_flow_scanner.get_whale_tickers,
                limit=20,
                retries=3, backoff=2.0, label='whale_tickers'
            )
            whale_flows = whale_flow_scanner.get_flow(limit=50)
            self.scan_results['whale_flow'] = whale_flows
            logger.info(f"Whale flow: {len(whale_tickers)} unique tickers")
        except Exception as e:
            logger.error(f"Whale flow scan failed: {e}")
            whale_tickers = []

        # Step 4: Find confluence
        finviz_tickers = set(r['ticker'] for r in self.scan_results['finviz'])
        whale_ticker_set = set(w['ticker'] for w in whale_tickers)
        confluence = finviz_tickers & whale_ticker_set
        self.scan_results['confluence'] = list(confluence)
        logger.info(f"Confluence symbols: {confluence}")

        # Step 5: Build initial watchlist (with sources/tiers)
        watchlist = self._build_watchlist(
            finviz_tickers, whale_tickers, confluence
        )

        # ============================================================
        # v3.0: ANALYTICAL BRAIN - Score every candidate
        # ============================================================
        all_tickers = [w['ticker'] for w in watchlist]
        logger.info(f"v3.0: Scoring {len(all_tickers)} candidates...")

        # Step 6: Technical indicator calculations via Alpaca (with retry)
        tech_map = {}
        if check_technicals and all_tickers:
            try:
                tech_results = _retry(
                    check_technicals, all_tickers,
                    retries=3, backoff=2.0, label='technical_checker'
                )
                tech_map = {
                    t['ticker']: t for t in tech_results
                    if t.get('ticker') and 'error' not in t
                }
                logger.info(
                    f"Technicals: {len(tech_map)}/{len(all_tickers)} computed"
                )
            except Exception as e:
                logger.error(f"Technical checker failed: {e}")
        else:
            logger.warning("technical_checker not available, skipping")

        # Step 7: Multi-timeframe alignment
        mtf_map = {}
        if batch_mtf_alignment and all_tickers:
            try:
                mtf_map = _retry(
                    batch_mtf_alignment, all_tickers,
                    retries=2, backoff=2.0, label='mtf_alignment'
                )
                logger.info(
                    f"MTF alignment: {len(mtf_map)} tickers analyzed"
                )
            except Exception as e:
                logger.error(f"MTF alignment failed: {e}")
        else:
            logger.warning("mtf_alignment not available, skipping")

        # Step 8: Earnings calendar safety filter
        earnings_map = {}
        if get_earnings_penalties and all_tickers:
            try:
                earnings_map = get_earnings_penalties(all_tickers)
                blocked = [
                    t for t, v in earnings_map.items()
                    if v.get('blocked', False)
                ]
                if blocked:
                    logger.warning(
                        f"Earnings blocked: {blocked}"
                    )
            except Exception as e:
                logger.error(f"Earnings calendar failed: {e}")
        else:
            logger.warning("earnings_calendar not available, skipping")

        # Step 9: Sector rotation rankings
        sector_data = {}
        if get_sector_rankings:
            try:
                sector_data = get_sector_rankings()
                logger.info("Sector rotation data loaded")
            except Exception as e:
                logger.error(f"Sector rotation failed: {e}")
        else:
            logger.warning("sector_rotation not available, skipping")

        # Step 10: Build whale data map for bonus scoring
        whale_map = {}
        for w in whale_tickers:
            whale_map[w['ticker']] = w

        # Step 11: Build memory map for adaptive feedback
        memory_map = {}
        if trade_memory:
            for ticker in all_tickers:
                try:
                    wr = trade_memory.get_win_rate(ticker)
                    if wr > 0:
                        memory_map[ticker] = {'win_rate': wr}
                except Exception:
                    pass

        # Step 12: COMPOSITE SCORING - the analytical brain
        scored_results = []
        if CompositeScorer and tech_map:
            try:
                regime_data = {
                    'regime': self.scan_results.get('regime', 'UNKNOWN'),
                }
                if isinstance(regime_data['regime'], dict):
                    regime_data = regime_data['regime']
                macro_data = self.scan_results.get('macro') or {}
                scorer = CompositeScorer(
                    regime_data=regime_data,
                    macro_data=macro_data,
                )

                # Build candidate list with technicals + MTF + earnings
                candidates = []
                for ticker in all_tickers:
                    tech = tech_map.get(ticker, {})
                    if not tech or tech.get('error'):
                        continue

                    # Merge earnings safety into technicals
                    earn = earnings_map.get(ticker, {})
                    tech['earnings_safe'] = not earn.get('blocked', False)
                    if earn.get('penalty', 0) < 0:
                        tech['earnings_penalty'] = earn['penalty']

                    # Merge sector hot/cold into technicals
                    if sector_data:
                        ticker_sector = tech.get('sector', '')
                        hot_sectors = sector_data.get('hot_sectors', [])
                        cold_sectors = sector_data.get('cold_sectors', [])
                        tech['sector_hot'] = ticker_sector in hot_sectors
                        tech['sector_cold'] = ticker_sector in cold_sectors

                    # Attach MTF data
                    mtf = mtf_map.get(ticker)
                    if mtf:
                        tech['mtf_data'] = mtf
                    candidates.append(tech)

                # Score all candidates
                scored_results = scorer.score_watchlist(
                    candidates,
                    whale_map=whale_map,
                    memory_map=memory_map,
                )
                logger.info(
                    f"Composite scoring complete: "
                    f"{len(scored_results)} candidates scored"
                )

                # Log top scores
                for r in scored_results[:5]:
                    logger.info(f"  {r.summary()}")

            except Exception as e:
                logger.error(f"Composite scoring failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            if not CompositeScorer:
                logger.warning("CompositeScorer not available")
            if not tech_map:
                logger.warning("No technicals data for scoring")

        self.scan_results['scored_results'] = scored_results

        # Step 13: Enrich watchlist with composite scores
        score_map = {}
        for r in scored_results:
            score_map[r.ticker] = r

        for item in watchlist:
            ticker = item['ticker']
            if ticker in score_map:
                breakdown = score_map[ticker]
                item['composite_score'] = breakdown.total
                item['score_tier'] = breakdown.tier
                item['regime_score'] = breakdown.regime_score
                item['trend_score'] = breakdown.trend_score
                item['pullback_score'] = breakdown.pullback_score
                item['momentum_score'] = breakdown.momentum_score
                item['pattern_score'] = breakdown.pattern_score
                item['score_summary'] = breakdown.summary()

                # Merge technicals into watchlist for main.py smart_entry
                tech = tech_map.get(ticker, {})
                if tech:
                    for key in ['rsi', 'atr', 'vwap', 'sma_20', 'sma_200',
                                 'ema_50', 'adx', 'volume_ratio', 'price',
                                 'williams_r', 'macd_hist', 'price_change_5d']:
                        if key in tech:
                            item[key] = tech[key]
            else:
                item['composite_score'] = 0
                item['score_tier'] = 'NO_DATA'

        # Re-sort by composite score (highest first)
        watchlist.sort(
            key=lambda x: x.get('composite_score', 0), reverse=True
        )
        self.scan_results['watchlist'] = watchlist

                # Step 13.5: Kelly edge + signal quality scoring
        try:
            from position_sizer import calculate_position
            for item in watchlist:
                score = item.get('composite_score', 0)
                # Convert composite score (0-100) to probability estimate
                prob_up = min(0.95, max(0.30, 0.40 + (score / 100) * 0.50))
                # Estimate win/loss from score tier
                avg_win = 0.025 + (score / 100) * 0.025  # 2.5-5% wins
                avg_loss = 0.02 - (score / 100) * 0.005  # 2.0-1.5% losses
                # Kelly edge = p*b - q where b = avg_win/avg_loss
                b = avg_win / max(avg_loss, 0.001)
                edge = prob_up * b - (1 - prob_up)
                kelly_raw = edge / max(b, 0.001) if edge > 0 else 0
                kelly_half = kelly_raw * 0.5
                item['kelly_edge'] = round(edge, 4)
                item['kelly_fraction'] = round(kelly_half, 4)
                item['prob_up'] = round(prob_up, 3)
                item['expected_value'] = round(edge * prob_up, 4)
                # Signal quality: composite of edge, score tier, volume
                vol_score = min(1.0, item.get('volume_ratio', 1.0) / 2.0)
                quality = (
                    0.4 * min(1.0, edge / 0.20)  # Edge contribution
                    + 0.3 * (score / 100)          # Composite score
                    + 0.15 * vol_score              # Volume confirmation
                    + 0.15 * (1 if item.get('mtf_aligned', False) else 0)
                )
                item['signal_quality'] = round(min(1.0, max(0, quality)), 3)
            logger.info(f"Kelly edge scored for {len(watchlist)} items")
        except Exception as e:
            logger.warning(f"Kelly edge scoring skipped: {e}")

        # Step 14: Position sizing recommendations
        if calculate_position and scored_results:
            try:
                # Determine regime string for position sizer
                regime_str = 'GREEN'
                regime_info = self.scan_results.get('regime', '')
                if isinstance(regime_info, dict):
                    r = regime_info.get('regime', 'GREEN').upper()
                    if 'RED' in r:
                        regime_str = 'RED'
                    elif 'YELLOW' in r:
                        regime_str = 'YELLOW'
                elif isinstance(regime_info, str):
                    if 'RED' in regime_info.upper():
                        regime_str = 'RED'
                    elif 'YELLOW' in regime_info.upper():
                        regime_str = 'YELLOW'

                for item in watchlist:
                    ticker = item['ticker']
                    tech = tech_map.get(ticker, {})
                    if tech and item.get('composite_score', 0) >= 70:
                        pos = calculate_position(
                            price=tech.get('price', 0),
                            atr=tech.get('atr', 0),
                            score_tier=item.get('score_tier', 'TRADEABLE'),
                            regime=regime_str,
                        )
                        item['position_size'] = pos
            except Exception as e:
                logger.error(f"Position sizing failed: {e}")

        # Step 15: Post to Slack
        if self.slack_client:
            self._post_to_slack(watchlist, confluence, whale_tickers)

        # Step 16: Fire TradingView webhook
        self._update_tradingview_watchlist(watchlist)

        # Step 17: Record signals in TradeMemory
        if trade_memory:
            try:
                for item in watchlist:
                    trade_memory.record_signal(
                        item['ticker'],
                        item['source'],
                        setup=item.get('score_tier', 'unknown'),
                        score=item.get('composite_score', 0),
                    )
                logger.info(
                    f"TradeMemory: recorded {len(watchlist)} signals"
                )
            except Exception as e:
                logger.error(f"TradeMemory record failed: {e}")

        # Step 18: Fetch FOM expected moves
        try:
            em_data = run_fom_em_scrape(lookback_hours=24)
            if em_data and em_data.get('tv_string'):
                self.scan_results['fom_expected_moves'] = em_data
                logger.info(
                    f"FOM-EM: {em_data.get('count', 0)} symbols fetched"
                )
                run_fom_em_post(em_data)
            else:
                logger.info("FOM-EM: No expected move data found")
        except Exception as e:
            logger.error(f"FOM expected moves failed: {e}")

        # ============================================================
        # Step 19: Execute trades via Alpaca (bracket orders)
        # ============================================================
        if alpaca_client and watchlist:
            try:
                # Get real account equity for position sizing
                equity = alpaca_client.get_equity()
                if equity > 0:
                    logger.info(f"Alpaca equity: ${equity:,.2f}")
                else:
                    equity = 100000  # fallback default
                    logger.warning("Using default equity $100,000")

                # Execute bracket orders for top tradeable signals
                trade_results = alpaca_client.execute_watchlist_trades(
                    watchlist, max_trades=3
                )
                successful = [r for r in trade_results if r.get('success')]
                failed = [r for r in trade_results if not r.get('success')]
                logger.info(
                    f"Alpaca trades: {len(successful)} placed, "
                    f"{len(failed)} skipped/failed"
                )
                self.scan_results['alpaca_trades'] = trade_results

                # Post trade summary to Slack
                if self.slack_client and successful:
                    trade_lines = [":moneybag: *Alpaca Trades Placed:*"]
                    for t in successful:
                        trade_lines.append(
                            f"  {t.get('symbol')} | "
                            f"{t.get('qty')} shares | "
                            f"stop=${t.get('stop_loss')} | "
                            f"tp=${t.get('take_profit')}"
                        )
                    try:
                        self.slack_client.chat_postMessage(
                            channel=OC_TRADE_DESK,
                            text='\n'.join(trade_lines),
                            mrkdwn=True,
                        )
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Alpaca trade execution failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            if not alpaca_client:
                logger.warning("alpaca_client not available, skipping trades")

        # ============================================================
        # Step 20: AI Bridge Export for Perplexity Tasks
        # ============================================================
        try:
            from api_data_bridge import export_and_push
            bridge_result = export_and_push(self.scan_results)
            logger.info(
                f"AI Bridge: exported {bridge_result.get('candidates', 0)} candidates, "
                f"sheets={'OK' if bridge_result.get('sheets_updated') else 'SKIP'}, "
                f"gist={'OK' if bridge_result.get('gist_url') else 'SKIP'}"
            )
            self.scan_results['bridge_result'] = bridge_result
        except Exception as e:
            logger.error(f"AI Bridge export failed: {e}")

        # ============================================================
        # Step 21: LLM Analysis (local Ollama + Perplexity hybrid)
        # ============================================================
        try:
            from llm_client import get_llm
            llm = get_llm()
            llm_st = llm.status()
            if llm_st.get('local_available') or llm_st.get('perplexity_available'):
                logger.info(
                    f"[LLM] Running hybrid analysis "
                    f"(local={llm_st.get('local_available')}, "
                    f"pplx={llm_st.get('perplexity_available')})"
                )
                # Check earnings for tradeable symbols via Perplexity
                tradeable = self.get_tradeable_tickers()
                if tradeable and llm_st.get('perplexity_available'):
                    earnings_info = llm.check_earnings(tradeable[:10])
                    if earnings_info:
                        self.scan_results['llm_earnings_check'] = earnings_info
                        logger.info(
                            f"[LLM] Earnings check: {len(tradeable[:10])} symbols"
                        )
                self.scan_results['llm_status'] = llm_st
                logger.info("[LLM] Analysis step complete")
            else:
                logger.info("[LLM] No backends available, skipping")
        except ImportError:
            logger.debug("[LLM] llm_client not installed, skipping")
        except Exception as e:
            logger.warning(f"[LLM] Analysis failed (non-fatal): {e}")

        return self.scan_results

    def _build_watchlist(self, finviz_tickers, whale_tickers, confluence):
        """
        Build prioritized watchlist:
        - Tier 1: Confluence (Finviz + Whale) -> highest priority
        - Tier 2: Finviz only (PAS v8 Gate PASS)
        - Tier 3: Whale flow only (unusual activity)
        Note: composite_score will be overwritten by the scorer.
        """
        watchlist = []

        # Tier 1: Confluence
        for ticker in confluence:
            finviz_data = next(
                (r for r in self.scan_results['finviz']
                 if r['ticker'] == ticker), {}
            )
            whale_data = next(
                (w for w in whale_tickers
                 if w['ticker'] == ticker), {}
            )
            watchlist.append({
                'ticker': ticker,
                'tier': 1,
                'source': 'confluence',
                'price': finviz_data.get('price', 0),
                'change_pct': finviz_data.get('change_pct', 0),
                'whale_premium': whale_data.get('total_premium', 0),
                'whale_sentiment': whale_data.get(
                    'dominant_sentiment', ''
                ),
                'scan_date': date.today().isoformat(),
                'composite_score': 0,
            })

        # Tier 2: Finviz only (top 15)
        for r in self.scan_results['finviz'][:15]:
            if r['ticker'] not in confluence:
                watchlist.append({
                    'ticker': r['ticker'],
                    'tier': 2,
                    'source': 'finviz',
                    'price': r.get('price', 0),
                    'change_pct': r.get('change_pct', 0),
                    'whale_premium': 0,
                    'whale_sentiment': '',
                    'scan_date': date.today().isoformat(),
                    'composite_score': 0,
                })

        # Tier 3: Whale flow only (top 10)
        for w in whale_tickers[:10]:
            if w['ticker'] not in finviz_tickers:
                watchlist.append({
                    'ticker': w['ticker'],
                    'tier': 3,
                    'source': 'whale_flow',
                    'price': 0,
                    'change_pct': 0,
                    'whale_premium': w.get('total_premium', 0),
                    'whale_sentiment': w.get(
                        'dominant_sentiment', ''
                    ),
                    'scan_date': date.today().isoformat(),
                    'composite_score': 0,
                })

        return watchlist

    def _post_to_slack(self, watchlist, confluence, whale_tickers):
        """Post the v3.0 scored daily scan summary to Slack."""
        if not self.slack_client:
            return

        today = date.today().strftime('%b %d, %Y')
        regime = self.scan_results.get('regime', 'N/A')
        macro = self.scan_results.get('macro') or {}

        lines = [
            f":robot_face: *OpenClaw Daily Scan v3.0 - {today}*",
            f"Regime: {regime}\n",
            f":bar_chart: *Macro:* {macro.get('regime', 'N/A')} | "
            f"VIX: {macro.get('vix', 'N/A')} | "
            f"F&G: {macro.get('fear_greed_value', 'N/A')} "
            f"({macro.get('fear_greed_label', '')})",
            f"*Finviz PAS v8 Gate:* "
            f"{len(self.scan_results['finviz'])} symbols",
            f"*Whale Flow:* {len(whale_tickers)} unique tickers",
            f"*Confluence:* {len(confluence)} symbols\n",
        ]

        # Scored results by tier
        scored = self.scan_results.get('scored_results', [])
        if scored:
            slams = [r for r in scored if r.tier == 'SLAM']
            highs = [r for r in scored if r.tier == 'HIGH_CONVICTION']
            trades = [r for r in scored if r.tier == 'TRADEABLE']

            if slams:
                lines.append(":fire: *SLAM TRADES (80+):*")
                for s in slams:
                    src = self._get_source(s.ticker, watchlist)
                    lines.append(
                        f"  :star: *{s.ticker}* {s.total:.0f}/100 "
                        f"[{src}] R:{s.regime_score:.0f} "
                        f"T:{s.trend_score:.0f} "
                        f"P:{s.pullback_score:.0f} "
                        f"M:{s.momentum_score:.0f}"
                    )
                lines.append("")

            if highs:
                lines.append(":dart: *HIGH CONVICTION (80+):*")
                for h in highs:
                    src = self._get_source(h.ticker, watchlist)
                    lines.append(
                        f"  *{h.ticker}* {h.total:.0f}/100 [{src}] "
                        f"R:{h.regime_score:.0f} T:{h.trend_score:.0f} "
                        f"P:{h.pullback_score:.0f} M:{h.momentum_score:.0f}"
                    )
                lines.append("")

            if trades:
                lines.append(
                    ":chart_with_upwards_trend: *TRADEABLE (55+):*"
                )
                for t in trades[:10]:
                    lines.append(
                        f"  {t.ticker} {t.total:.0f}/100"
                    )
                lines.append("")

            # Summary stats
            lines.append(
                f"_Scored {len(scored)} candidates | "
                f"SLAM: {len(slams)} | HIGH: {len(highs)} | "
                f"TRADEABLE: {len(trades)}_"
            )
        else:
            # Fallback to old-style posting if scoring unavailable
            lines.append("_Composite scoring unavailable - "
                         "showing raw scan results_")
            for item in watchlist[:15]:
                tier_emoji = {1: ':fire:', 2: ':chart_with_upwards_trend:', 3: ':whale:'}
                emoji = tier_emoji.get(item['tier'], '')
                lines.append(
                    f"  {emoji} *{item['ticker']}* T{item['tier']} "
                    f"| {item['source']}"
                )

        message = '\n'.join(lines)
        try:
            self.slack_client.chat_postMessage(
                channel=OC_TRADE_DESK,
                text=message,
                mrkdwn=True
            )
            logger.info("Daily scan v3.0 posted to #oc-trade-desk")
        except Exception as e:
            logger.error(f"Failed to post scan to Slack: {e}")

    @staticmethod
    def _get_source(ticker, watchlist):
        """Get source label for a ticker from watchlist."""
        for w in watchlist:
            if w['ticker'] == ticker:
                return w.get('source', '?')
        return '?'

    def _update_tradingview_watchlist(self, watchlist):
        """
        Update TradingView watchlist via internal API.
        Uses tradingview_watchlist module for direct API access.
        """
        try:
            tv_watchlist.update_daily_watchlist(watchlist)
        except Exception as e:
            logger.error(
                f"TradingView watchlist update failed: {e}"
            )

    def get_watchlist_tickers(self):
        """Return just the ticker list from the last scan."""
        return [
            w['ticker']
            for w in self.scan_results.get('watchlist', [])
        ]

    def get_tradeable_tickers(self):
        """Return only tickers scoring 55+ (tradeable)."""
        return [
            w['ticker']
            for w in self.scan_results.get('watchlist', [])
            if w.get('composite_score', 0) >= 55
        ]

    def get_slam_tickers(self):
        """Return only tickers scoring 80+ (SLAM)."""
        return [
            w['ticker']
            for w in self.scan_results.get('watchlist', [])
            if w.get('composite_score', 0) >= 80
        ]


# Module-level function for easy scheduling
def run_daily_scan(slack_client=None):
    """Convenience function to run the full daily scan."""
    scanner = DailyScanner(slack_client=slack_client)
    return scanner.run_full_scan()
