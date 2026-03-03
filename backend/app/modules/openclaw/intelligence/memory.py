#!/usr/bin/env python3
"""
memory.py - Agent Memory & Self-Learning Flywheel for OpenClaw v2.0

Persistent memory system that enables the clawbot agent architecture:
  - Tracks trade outcomes by ticker, source, setup type, and regime
  - Adjusts source weights based on historical accuracy (flywheel)
  - Score-at-entry correlation: learns WHICH scores actually win
  - Regime-aware memory: learns what works in GREEN vs YELLOW vs RED
  - Recency-weighted stats: recent trades matter more than old ones
  - Agent strategy tracking: each strategy is an 'agent' that can be
    spawned (promoted) or pruned (demoted) based on performance
  - Ticker blacklist/cooldown: auto-stops repeating mistakes
  - Expectancy tracking: avg_win * WR - avg_loss * (1-WR) per source

Designed for 24/7 self-improving agent loop:
  1. Agents generate signals -> record_signal()
  2. Signals become trades -> auto_executor places them
  3. Trades close -> record_outcome() with real P&L
  4. Memory recalculates weights, promotes/prunes agents
  5. Next scan cycle uses updated weights -> smarter signals

Stores data as JSON on disk - survives restarts, zero dependencies.

Usage:
    from memory import trade_memory
    trade_memory.record_signal('AAPL', 'finviz', 'momentum', score=82, regime='GREEN')
    trade_memory.record_outcome('AAPL', 'finviz', won=True, pnl_pct=3.2)
    weights = trade_memory.get_source_weights()
    stats = trade_memory.get_ticker_stats('AAPL')
    blacklisted = trade_memory.get_blacklisted_tickers()
    top_agents = trade_memory.get_agent_rankings()
"""

import os
import json
import logging
import math
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Storage location - same dir as memory.py
MEMORY_FILE = Path(__file__).parent / 'openclaw_memory.json'

# Default source weights used in composite scoring
DEFAULT_WEIGHTS = {
    'finviz': 20,       # Finviz Technical score (max pts)
    'uw': 25,           # Unusual Whales Flow score
    'discord': 15,      # Discord signal score
    'chart': 20,        # Chart Setup score
    'regime': 10,       # Market Regime score
    'sentiment': 10,    # Sentiment score
}

# Minimum trades before we trust the stats enough to adjust weights
MIN_TRADES_TO_ADJUST = 5

# Recency decay: trades older than this get exponentially less weight
RECENCY_HALF_LIFE_DAYS = 30

# Agent pruning thresholds
AGENT_MIN_TRADES = 5           # Min trades before evaluating an agent
AGENT_PRUNE_WIN_RATE = 0.30    # Below this WR -> agent gets pruned
AGENT_PROMOTE_WIN_RATE = 0.65  # Above this WR -> agent gets promoted
AGENT_PROMOTE_MIN_TRADES = 10  # Need this many trades to promote

# Blacklist: consecutive losses before cooldown
BLACKLIST_CONSECUTIVE_LOSSES = 3
BLACKLIST_COOLDOWN_DAYS = 7

# Memory cleanup: purge tickers not seen in this many days
MEMORY_STALE_DAYS = 90


class TradeMemory:
    """
    Persistent memory system for OpenClaw agent architecture.

    Each 'source + setup' combination is treated as a strategy agent.
    Agents that perform well get promoted (higher weights).
    Agents that underperform get pruned (lower weights, eventually disabled).
    The system learns 24/7 from real trade outcomes.
    """

    def __init__(self, filepath: Path = MEMORY_FILE):
        self.filepath = filepath
        self._lock = threading.Lock()
        self.data = self._load()

    # ------------------------------------------------------------------ #
    # PERSISTENCE                                                          #
    # ------------------------------------------------------------------ #

    def _load(self) -> dict:
        """Load memory from disk, or create fresh structure."""
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                # Migrate: add new fields if upgrading from v1
                data.setdefault('agents', {})
                data.setdefault('blacklist', {})
                data.setdefault('regime_stats', {})
                data.setdefault('score_bins', {})
                logger.info(f"[Memory] Loaded {self.filepath} "
                            f"({len(data.get('tickers', {}))} tickers, "
                            f"{len(data.get('sources', {}))} sources, "
                            f"{len(data.get('agents', {}))} agents)")
                return data
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"[Memory] Corrupt file, starting fresh: {e}")

        return {
            'tickers': {},           # per-ticker win/loss history
            'sources': {},           # per-source accuracy stats
            'setups': {},            # per-setup-type stats
            'agents': {},            # source+setup combo = strategy agent
            'regime_stats': {},      # per-regime performance tracking
            'score_bins': {},        # score-range -> win rate mapping
            'blacklist': {},         # ticker -> cooldown expiry date
            'weights': dict(DEFAULT_WEIGHTS),
            'signals_today': [],
            'last_reset': datetime.now().strftime('%Y-%m-%d'),
            'total_signals': 0,
            'total_outcomes': 0,
        }

    def _save(self):
        """Write memory to disk atomically with thread safety (Issue #3 fix)."""
        with self._lock:
            tmp = self.filepath.with_suffix('.tmp')
            try:
                with open(tmp, 'w') as f:
                    json.dump(self.data, f, indent=2, default=str)
                tmp.replace(self.filepath)
            except Exception as e:
                logger.error(f"[Memory] Save failed: {e}")
    # ------------------------------------------------------------------ #
    # DAILY RESET                                                          #
    # ------------------------------------------------------------------ #

    def reset_daily(self):
        """Clear today's signal dedup list. Call at market open (9:30 AM)."""
        today = datetime.now().strftime('%Y-%m-%d')
        if self.data.get('last_reset') != today:
            self.data['signals_today'] = []
            self.data['last_reset'] = today
            # Clean expired blacklist entries
            self._clean_blacklist()
            # Purge stale tickers
            self._purge_stale_tickers()
            self._save()
            logger.info('[Memory] Daily reset complete.')

    def already_signaled_today(self, ticker: str) -> bool:
        """Return True if this ticker was already flagged today."""
        return ticker.upper() in self.data.get('signals_today', [])

    # ------------------------------------------------------------------ #
    # RECORDING                                                            #
    # ------------------------------------------------------------------ #

    def record_signal(self, ticker: str, source: str,
                      setup: str = 'unknown', score: int = 0,
                      regime: str = 'UNKNOWN'):
        """
        Log that a ticker was flagged as a candidate.
        Now tracks regime at time of signal and registers strategy agent.
        """
        ticker = ticker.upper()
        source = source.lower()
        setup = setup.lower()
        regime = regime.upper()

        # Mark as seen today
        if ticker not in self.data['signals_today']:
            self.data['signals_today'].append(ticker)

        # Ensure ticker record exists
        if ticker not in self.data['tickers']:
            self.data['tickers'][ticker] = {
                'signals': 0, 'outcomes': 0,
                'wins': 0, 'losses': 0,
                'consecutive_losses': 0,
                'total_pnl_pct': 0.0,
                'avg_score': 0.0,
                'sources': [],
                'last_seen': None,
                'scores_at_entry': [],
                'regime_history': [],
            }

        t = self.data['tickers'][ticker]
        t['signals'] += 1
        t['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M')

        # Rolling average score
        t['avg_score'] = round(
            (t['avg_score'] * (t['signals'] - 1) + score) / t['signals'], 1
        )
        if source not in t['sources']:
            t['sources'].append(source)

        # Track score at entry (keep last 50)
        t['scores_at_entry'] = t.get('scores_at_entry', [])[-49:]
        t['scores_at_entry'].append({
            'score': score, 'regime': regime,
            'date': datetime.now().strftime('%Y-%m-%d'),
        })

        # Source stats
        self._ensure_source(source)
        self.data['sources'][source]['signals'] += 1

        # Setup stats
        self._ensure_setup(setup)
        self.data['setups'][setup]['signals'] += 1

        # Register/update strategy agent (source+setup combo)
        agent_id = f"{source}:{setup}"
        self._ensure_agent(agent_id, source, setup)
        self.data['agents'][agent_id]['signals'] += 1

        # Regime-specific tracking
        self._ensure_regime_stats(regime)
        self.data['regime_stats'][regime]['signals'] += 1

        # Score bin tracking (learn which score ranges win)
        score_bin = self._score_to_bin(score)
        self.data['score_bins'].setdefault(score_bin, {
            'signals': 0, 'outcomes': 0, 'wins': 0
        })
        self.data['score_bins'][score_bin]['signals'] += 1

        self.data['total_signals'] += 1
        self._save()

    def record_outcome(self, ticker: str, source: str,
                       won: bool, pnl_pct: float = 0.0,
                       setup: str = 'unknown', regime: str = 'UNKNOWN'):
        """
        Log the outcome of a trade. This is where the flywheel learns.
        After recording, automatically recalculates weights and
        evaluates agent performance for promotion/pruning.
        """
        ticker = ticker.upper()
        source = source.lower()
        setup = setup.lower()
        regime = regime.upper()

        # Ticker outcome
        if ticker in self.data['tickers']:
            t = self.data['tickers'][ticker]
            t['outcomes'] = t.get('outcomes', 0) + 1
            t['total_pnl_pct'] = round(t.get('total_pnl_pct', 0) + pnl_pct, 2)
            if won:
                t['wins'] = t.get('wins', 0) + 1
                t['consecutive_losses'] = 0
            else:
                t['losses'] = t.get('losses', 0) + 1
                t['consecutive_losses'] = t.get('consecutive_losses', 0) + 1
                # Auto-blacklist after consecutive losses
                if t['consecutive_losses'] >= BLACKLIST_CONSECUTIVE_LOSSES:
                    self._blacklist_ticker(ticker)

        # Source outcome + expectancy
        self._ensure_source(source)
        s = self.data['sources'][source]
        s['outcomes'] += 1
        s['total_pnl_pct'] = round(s['total_pnl_pct'] + pnl_pct, 2)
        if won:
            s['wins'] += 1
            s['total_win_pnl'] = round(s.get('total_win_pnl', 0) + pnl_pct, 2)
        else:
            s['losses'] += 1
            s['total_loss_pnl'] = round(s.get('total_loss_pnl', 0) + abs(pnl_pct), 2)

        # Setup outcome
        self._ensure_setup(setup)
        u = self.data['setups'][setup]
        u['outcomes'] += 1
        if won:
            u['wins'] += 1
        else:
            u['losses'] += 1

        # Agent outcome (source+setup combo)
        agent_id = f"{source}:{setup}"
        self._ensure_agent(agent_id, source, setup)
        ag = self.data['agents'][agent_id]
        ag['outcomes'] += 1
        ag['total_pnl_pct'] = round(ag.get('total_pnl_pct', 0) + pnl_pct, 2)
        if won:
            ag['wins'] += 1
        else:
            ag['losses'] += 1
        ag['last_outcome'] = datetime.now().strftime('%Y-%m-%d')

        # Regime outcome
        self._ensure_regime_stats(regime)
        rs = self.data['regime_stats'][regime]
        rs['outcomes'] += 1
        rs['total_pnl_pct'] = round(rs.get('total_pnl_pct', 0) + pnl_pct, 2)
        if won:
            rs['wins'] += 1
        else:
            rs['losses'] += 1

        # Score bin outcome
        last_score = self._get_last_entry_score(ticker)
        if last_score is not None:
            score_bin = self._score_to_bin(last_score)
            if score_bin in self.data['score_bins']:
                self.data['score_bins'][score_bin]['outcomes'] += 1
                if won:
                    self.data['score_bins'][score_bin]['wins'] += 1

        self.data['total_outcomes'] += 1

        # FLYWHEEL: recalculate everything
        self._recalculate_weights()
        self._evaluate_agents()
        self._save()

        logger.info(f"[Memory] Outcome: {ticker} via {source}:{setup} "
                    f"{'WIN' if won else 'LOSS'} {pnl_pct:+.1f}% "
                    f"regime={regime}")

    # ------------------------------------------------------------------ #
    # INTERNAL HELPERS                                                     #
    # ------------------------------------------------------------------ #

    def _ensure_source(self, source: str):
        if source not in self.data['sources']:
            self.data['sources'][source] = {
                'signals': 0, 'outcomes': 0,
                'wins': 0, 'losses': 0,
                'total_pnl_pct': 0.0,
                'total_win_pnl': 0.0,
                'total_loss_pnl': 0.0,
            }

    def _ensure_setup(self, setup: str):
        if setup not in self.data['setups']:
            self.data['setups'][setup] = {
                'signals': 0, 'outcomes': 0,
                'wins': 0, 'losses': 0,
            }

    def _ensure_agent(self, agent_id: str, source: str, setup: str):
        """Register a strategy agent (source+setup combo)."""
        if agent_id not in self.data['agents']:
            self.data['agents'][agent_id] = {
                'source': source,
                'setup': setup,
                'signals': 0, 'outcomes': 0,
                'wins': 0, 'losses': 0,
                'total_pnl_pct': 0.0,
                'status': 'active',      # active, promoted, pruned
                'created': datetime.now().strftime('%Y-%m-%d'),
                'last_outcome': None,
                'promotion_count': 0,
                'prune_count': 0,
            }

    def _ensure_regime_stats(self, regime: str):
        if regime not in self.data['regime_stats']:
            self.data['regime_stats'][regime] = {
                'signals': 0, 'outcomes': 0,
                'wins': 0, 'losses': 0,
                'total_pnl_pct': 0.0,
            }

    def _score_to_bin(self, score: int) -> str:
        """Convert a score to a bin label for tracking win rates by range."""
        if score >= 80:
            return '80-100'
        elif score >= 70:
            return '70-79'
        elif score >= 60:
            return '60-69'
        elif score >= 50:
            return '50-59'
        else:
            return '0-49'

    def _get_last_entry_score(self, ticker: str) -> Optional[int]:
        """Get the most recent entry score for a ticker."""
        t = self.data['tickers'].get(ticker.upper(), {})
        entries = t.get('scores_at_entry', [])
        if entries:
            return entries[-1].get('score')
        return None

    def _blacklist_ticker(self, ticker: str):
        """Add ticker to blacklist with cooldown period."""
        expiry = (datetime.now() + timedelta(days=BLACKLIST_COOLDOWN_DAYS)
                  ).strftime('%Y-%m-%d')
        self.data['blacklist'][ticker.upper()] = expiry
        logger.warning(f"[Memory] BLACKLISTED {ticker} until {expiry} "
                       f"(consecutive losses)")

    def _clean_blacklist(self):
        """Remove expired blacklist entries."""
        today = datetime.now().strftime('%Y-%m-%d')
        expired = [t for t, exp in self.data['blacklist'].items()
                   if exp <= today]
        for t in expired:
            del self.data['blacklist'][t]
            logger.info(f"[Memory] Blacklist expired for {t}")

    def _purge_stale_tickers(self):
        """Remove tickers not seen in MEMORY_STALE_DAYS."""
        cutoff = (datetime.now() - timedelta(days=MEMORY_STALE_DAYS)
                  ).strftime('%Y-%m-%d')
        stale = []
        for ticker, stats in self.data['tickers'].items():
            last = stats.get('last_seen', '')
            if last and last[:10] < cutoff:
                stale.append(ticker)
        for t in stale:
            del self.data['tickers'][t]
        if stale:
            logger.info(f"[Memory] Purged {len(stale)} stale tickers")

    # ------------------------------------------------------------------ #
    # FLYWHEEL: WEIGHT RECALCULATION & AGENT EVALUATION                    #
    # ------------------------------------------------------------------ #

    def _recalculate_weights(self):
        """
        Adjust source weights based on win-rate vs baseline.
        Only adjusts sources with >= MIN_TRADES_TO_ADJUST outcomes.
        Weights are clamped between 50%-150% of their default value
        so we never completely zero-out a source.
        """
        for source, default_pts in DEFAULT_WEIGHTS.items():
            if source not in self.data['sources']:
                continue
            s = self.data['sources'][source]
            if s['outcomes'] < MIN_TRADES_TO_ADJUST:
                continue

            win_rate = self._get_recency_weighted_wr(source)

            # Expectancy factor: reward sources with good risk/reward
            expectancy = self._calc_expectancy(s)
            exp_bonus = 1.0
            if expectancy > 0.5:
                exp_bonus = 1.1
            elif expectancy < -0.5:
                exp_bonus = 0.9

            # Scale: 50% WR = 1.0x (neutral), 70% WR = 1.4x, 30% WR = 0.6x
            scale = 0.2 + (win_rate * 1.6)  # range ~0.2 - 1.8
            scale = max(0.5, min(1.5, scale * exp_bonus))  # clamp

            self.data['weights'][source] = round(default_pts * scale)

        logger.debug(f"[Memory] Weights updated: {self.data['weights']}")

    def _calc_expectancy(self, source_stats: dict) -> float:
        """Calculate expectancy: avg_win * WR - avg_loss * (1-WR)."""
        outcomes = source_stats.get('outcomes', 0)
        if outcomes == 0:
            return 0.0
        wins = source_stats.get('wins', 0)
        losses = source_stats.get('losses', 0)
        wr = wins / outcomes if outcomes > 0 else 0
        avg_win = (source_stats.get('total_win_pnl', 0) / wins) if wins > 0 else 0
        avg_loss = (source_stats.get('total_loss_pnl', 0) / losses) if losses > 0 else 0
        return round(avg_win * wr - avg_loss * (1 - wr), 3)

    def _evaluate_agents(self):
        """
        Core agent intelligence: evaluate each strategy agent.
        - Agents with high WR + enough trades -> PROMOTE (spawned)
        - Agents with low WR + enough trades -> PRUNE (demoted)
        - Agents with insufficient data -> stay ACTIVE (learning)

        This is the 'spawning and pruning' loop that makes the
        system get smarter over time.
        """
        for agent_id, ag in self.data['agents'].items():
            outcomes = ag.get('outcomes', 0)
            if outcomes < AGENT_MIN_TRADES:
                continue  # Not enough data yet

            wr = ag['wins'] / outcomes if outcomes > 0 else 0
            old_status = ag.get('status', 'active')

            if outcomes >= AGENT_PROMOTE_MIN_TRADES and wr >= AGENT_PROMOTE_WIN_RATE:
                ag['status'] = 'promoted'
                if old_status != 'promoted':
                    ag['promotion_count'] = ag.get('promotion_count', 0) + 1
                    logger.info(f"[Memory] AGENT PROMOTED: {agent_id} "
                                f"WR={wr:.0%} trades={outcomes} "
                                f"P&L={ag.get('total_pnl_pct', 0):+.1f}%")

            elif wr < AGENT_PRUNE_WIN_RATE:
                ag['status'] = 'pruned'
                if old_status != 'pruned':
                    ag['prune_count'] = ag.get('prune_count', 0) + 1
                    logger.warning(f"[Memory] AGENT PRUNED: {agent_id} "
                                   f"WR={wr:.0%} trades={outcomes} "
                                   f"P&L={ag.get('total_pnl_pct', 0):+.1f}%")
            else:
                ag['status'] = 'active'

    # ------------------------------------------------------------------ #
    # QUERIES                                                              #
    # ------------------------------------------------------------------ #

    def get_source_weights(self) -> dict:
        """Return current adjusted source weights for composite scoring."""
        return dict(self.data['weights'])

    def get_ticker_stats(self, ticker: str) -> Optional[dict]:
        """Return full stats for a specific ticker, or None if unknown."""
        return self.data['tickers'].get(ticker.upper())

    def get_source_stats(self, source: str) -> Optional[dict]:
        """Return win-rate and expectancy stats for a source."""
        s = self.data['sources'].get(source.lower())
        if not s or s['outcomes'] == 0:
            return None
        return {
            **s,
            'win_rate': round(s['wins'] / s['outcomes'] * 100, 1),
            'avg_pnl': round(s['total_pnl_pct'] / s['outcomes'], 2),
            'expectancy': self._calc_expectancy(s),
        }

    def get_setup_stats(self, setup: str) -> Optional[dict]:
        """Return win-rate stats for a setup type."""
        u = self.data['setups'].get(setup.lower())
        if not u or u.get('outcomes', 0) == 0:
            return None
        return {
            **u,
            'win_rate': round(u['wins'] / u['outcomes'] * 100, 1),
        }

    def get_win_rate(self, ticker: str) -> float:
        """Return historical win rate for a ticker (0.0-1.0).
        Returns 0.5 (neutral) if no history."""
        t = self.data['tickers'].get(ticker.upper())
        if not t or t.get('outcomes', 0) == 0:
            return 0.5
        return round(t['wins'] / t['outcomes'], 3)

    def get_confidence(self, ticker: str) -> float:
        """Return confidence in memory data for ticker (0.0-1.0).
        Based on sample size: more trades = higher confidence."""
        t = self.data['tickers'].get(ticker.upper())
        if not t:
            return 0.0
        outcomes = t.get('outcomes', 0)
        if outcomes == 0:
            return 0.0
        # Confidence curve: 1 trade=0.2, 5=0.6, 10=0.8, 20+=0.95
        return round(min(0.95, 1.0 - math.exp(-0.15 * outcomes)), 2)

    def get_top_tickers(self, n: int = 10) -> list:
        """Return top n tickers by win-rate (min 2 outcomes)."""
        ranked = []
        for ticker, stats in self.data['tickers'].items():
            if stats.get('outcomes', 0) >= 2:
                wr = stats['wins'] / stats['outcomes']
                ranked.append((ticker, wr, stats))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:n]

    def is_blacklisted(self, ticker: str) -> bool:
        """Check if ticker is currently blacklisted."""
        expiry = self.data['blacklist'].get(ticker.upper())
        if not expiry:
            return False
        return expiry > datetime.now().strftime('%Y-%m-%d')

    def get_blacklisted_tickers(self) -> List[str]:
        """Return list of currently blacklisted tickers."""
        today = datetime.now().strftime('%Y-%m-%d')
        return [t for t, exp in self.data['blacklist'].items() if exp > today]

    def get_agent_rankings(self) -> List[dict]:
        """Return all agents sorted by performance.
        This is the 'agent leaderboard' showing which strategies work."""
        rankings = []
        for agent_id, ag in self.data['agents'].items():
            outcomes = ag.get('outcomes', 0)
            wr = (ag['wins'] / outcomes * 100) if outcomes > 0 else 0
            rankings.append({
                'agent_id': agent_id,
                'source': ag.get('source', ''),
                'setup': ag.get('setup', ''),
                'status': ag.get('status', 'active'),
                'outcomes': outcomes,
                'win_rate': round(wr, 1),
                'total_pnl_pct': ag.get('total_pnl_pct', 0),
                'promotions': ag.get('promotion_count', 0),
                'prunes': ag.get('prune_count', 0),
            })
        rankings.sort(key=lambda x: (x['win_rate'], x['total_pnl_pct']),
                      reverse=True)
        return rankings

    def get_active_agents(self) -> List[str]:
        """Return agent_ids that are active or promoted (not pruned)."""
        return [aid for aid, ag in self.data['agents'].items()
                if ag.get('status') != 'pruned']

    def get_score_bin_stats(self) -> dict:
        """Return win rates by score range. Shows which scores actually win."""
        result = {}
        for bin_label, stats in self.data.get('score_bins', {}).items():
            outcomes = stats.get('outcomes', 0)
            if outcomes > 0:
                result[bin_label] = {
                    'signals': stats.get('signals', 0),
                    'outcomes': outcomes,
                    'win_rate': round(stats['wins'] / outcomes * 100, 1),
                }
        return result

    def get_regime_stats(self) -> dict:
        """Return performance by market regime."""
        result = {}
        for regime, stats in self.data.get('regime_stats', {}).items():
            outcomes = stats.get('outcomes', 0)
            if outcomes > 0:
                result[regime] = {
                    'outcomes': outcomes,
                    'win_rate': round(stats['wins'] / outcomes * 100, 1),
                    'avg_pnl': round(stats.get('total_pnl_pct', 0) / outcomes, 2),
                }
        return result

    # ------------------------------------------------------------------ #
    # SLACK SUMMARY                                                        #
    # ------------------------------------------------------------------ #

    def get_summary_text(self) -> str:
        """Return Slack-formatted summary for /oc memory command."""
        lines = ["*:brain: OpenClaw Agent Memory v2.0*\n"]

        lines.append(f"*Total Signals:* {self.data['total_signals']} | "
                     f"*Outcomes:* {self.data['total_outcomes']}")

        # Source performance
        lines.append("\n*Source Win Rates:*")
        for src, stats in self.data['sources'].items():
            if stats.get('outcomes', 0) == 0:
                continue
            wr = round(stats['wins'] / stats['outcomes'] * 100, 1)
            w = self.data['weights'].get(src, '?')
            exp = self._calc_expectancy(stats)
            lines.append(f"  `{src}`: {wr}% WR "
                         f"({stats['wins']}W/{stats['losses']}L) "
                         f"weight={w}pts exp={exp:+.2f}")

        # Agent leaderboard
        agents = self.get_agent_rankings()
        if agents:
            lines.append("\n*:robot_face: Agent Leaderboard:*")
            for ag in agents[:8]:
                status_icon = ':star:' if ag['status'] == 'promoted' else \
                    ':x:' if ag['status'] == 'pruned' else ':gear:'
                lines.append(
                    f"  {status_icon} `{ag['agent_id']}` "
                    f"{ag['win_rate']}% WR ({ag['outcomes']} trades) "
                    f"P&L={ag['total_pnl_pct']:+.1f}%"
                )

        # Score bin stats
        bins = self.get_score_bin_stats()
        if bins:
            lines.append("\n*Score Range Win Rates:*")
            for b in sorted(bins.keys(), reverse=True):
                s = bins[b]
                lines.append(f"  `{b}`: {s['win_rate']}% WR ({s['outcomes']} trades)")

        # Regime stats
        regimes = self.get_regime_stats()
        if regimes:
            lines.append("\n*Regime Performance:*")
            for r, s in regimes.items():
                lines.append(f"  `{r}`: {s['win_rate']}% WR "
                             f"avg={s['avg_pnl']:+.2f}% ({s['outcomes']} trades)")

        # Top tickers
        top = self.get_top_tickers(5)
        if top:
            lines.append("\n*Top 5 Tickers:*")
            for ticker, wr, stats in top:
                lines.append(f"  `{ticker}`: {round(wr*100,1)}% WR "
                             f"avg_score={stats.get('avg_score', 0)}")

        # Blacklist
        bl = self.get_blacklisted_tickers()
        if bl:
            lines.append(f"\n*:no_entry: Blacklisted ({len(bl)}):* {', '.join(bl)}")

        lines.append(f"\n_Last reset: {self.data.get('last_reset', 'N/A')}_")
        return '\n'.join(lines)



    # ------------------------------------------------------------------ #
    # Issue #3 FIXES: Recency, Journal Sync, Score Threshold, Thread Lock #
    # ------------------------------------------------------------------ #

    def _get_recency_weighted_wr(self, source: str) -> float:
        """Recency-weighted win rate using exponential decay.
        Trades from RECENCY_HALF_LIFE_DAYS ago get 0.5 weight,
        2x half-life ago get 0.25, etc. Returns 0.5 if no data."""
        s = self.data['sources'].get(source.lower())
        if not s or s.get('outcomes', 0) < MIN_TRADES_TO_ADJUST:
            return 0.5
        # For now use simple win_rate weighted by recency from last_outcome
        # Full implementation needs per-trade timestamps in sources
        wr = s['wins'] / s['outcomes'] if s['outcomes'] > 0 else 0.5
        # Apply mild recency bias: newer data from agents weigh more
        now = datetime.now()
        for agent_id, ag in self.data['agents'].items():
            if not agent_id.startswith(source):
                continue
            last = ag.get('last_outcome')
            if last:
                try:
                    days_ago = (now - datetime.strptime(last, '%Y-%m-%d')).days
                    decay = math.pow(0.5, days_ago / RECENCY_HALF_LIFE_DAYS)
                    agent_wr = ag['wins'] / ag['outcomes'] if ag.get('outcomes', 0) > 0 else 0.5
                    wr = wr * 0.6 + agent_wr * decay * 0.4
                except (ValueError, ZeroDivisionError):
                    pass
        return round(max(0.0, min(1.0, wr)), 3)

    def sync_from_journal(self, journal_path: str = None) -> int:
        """Read closed trades from performance_tracker journal and
        backfill memory outcomes. Returns number of new trades synced."""
        if journal_path is None:
            journal_path = str(Path(__file__).parent / 'data' / 'trade_journal.json')
        if not Path(journal_path).exists():
            logger.debug('[Memory] No trade journal found at %s', journal_path)
            return 0
        try:
            with open(journal_path, 'r') as f:
                journal = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning('[Memory] Failed to read journal: %s', e)
            return 0
        synced = 0
        existing_outcomes = self.data.get('total_outcomes', 0)
        trades = journal if isinstance(journal, list) else journal.get('trades', [])
        for trade in trades:
            if not trade.get('closed'):
                continue
            ticker = trade.get('symbol', trade.get('ticker', '')).upper()
            source = trade.get('source', 'unknown').lower()
            pnl_pct = trade.get('pnl_pct', 0.0)
            won = pnl_pct > 0
            setup = trade.get('setup', 'unknown')
            regime = trade.get('regime', 'UNKNOWN')
            # Skip if already in memory (simple dedup by ticker+date)
            close_date = trade.get('close_date', trade.get('date', ''))
            t = self.data['tickers'].get(ticker, {})
            if t.get('last_synced_date') == close_date:
                continue
            self.record_outcome(ticker, source, won, pnl_pct, setup, regime)
            if ticker in self.data['tickers']:
                self.data['tickers'][ticker]['last_synced_date'] = close_date
            synced += 1
        if synced:
            logger.info('[Memory] Synced %d trades from journal', synced)
            self._save()
        return synced

    def get_optimal_score_threshold(self) -> int:
        """Return minimum score with >50%% win rate based on score_bins.
        Used by composite_scorer to set dynamic thresholds."""
        best_threshold = 70  # safe default
        for bin_label in sorted(self.data.get('score_bins', {}).keys()):
            stats = self.data['score_bins'][bin_label]
            outcomes = stats.get('outcomes', 0)
            if outcomes >= 3:  # need minimum sample
                wr = stats['wins'] / outcomes
                if wr > 0.5:
                    # Extract lower bound of bin range
                    try:
                        threshold = int(bin_label.split('-')[0])
                        best_threshold = min(best_threshold, threshold)
                    except ValueError:
                        pass
        return best_threshold

    def get_pruned_agent_tickers(self) -> List[str]:
        """Return tickers with open signals from pruned agents.
        position_manager should apply tighter stops on these."""
        pruned_sources = set()
        for agent_id, ag in self.data['agents'].items():
            if ag.get('status') == 'pruned':
                pruned_sources.add(ag.get('source', ''))
        flagged = []
        for ticker, t in self.data['tickers'].items():
            if any(s in pruned_sources for s in t.get('sources', [])):
                flagged.append(ticker)
        return flagged

trade_memory = TradeMemory()
