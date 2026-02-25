#!/usr/bin/env python3
"""
Performance Tracker for OpenClaw v2.0

Trade logging, analytics, and performance monitoring:
  - Atomic JSON writes using .tmp + .replace() pattern
  - Bounded journal size with auto-archival (max 5000 trades/file)
  - UUID-based trade IDs (prevent ID collisions on concurrent access)
  - Integration with memory.py via record_outcome() callbacks
  - Thread-safe file operations with Lock
  - Win/loss ratio and expectancy calculation
  - R-multiple tracking per trade
  - Regime-based performance breakdown
  - Session-based analytics
  - Entry grade effectiveness tracking
  - Daily/weekly/monthly P&L summaries
  - Slack-formatted performance reports

Data stored in: data/trade_journal.json
Archive stored in: data/trade_journal_archive/ (auto-created)
"""
import logging
import json
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")

# ========== CONFIG ==========
JOURNAL_FILE = Path("data/trade_journal.json")
ARCHIVE_DIR = Path("data/trade_journal_archive")
STATS_FILE = Path("data/performance_stats.json")
MAX_JOURNAL_SIZE = 5000  # Auto-archive after this many trades
JOURNAL_LOCK = threading.Lock()  # Thread-safe file access


def _ensure_dirs():
    """Ensure data directories exist."""
    JOURNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def _load_journal() -> List[Dict]:
    """Load trade journal from disk (thread-safe)."""
    with JOURNAL_LOCK:
        try:
            _ensure_dirs()
            if JOURNAL_FILE.exists():
                with open(JOURNAL_FILE, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load trade journal: {e}")
    return []


def _save_journal(trades: List[Dict]):
    """Save trade journal to disk atomically (thread-safe).
    Uses .tmp + .replace() pattern to prevent corruption.
    """
    with JOURNAL_LOCK:
        try:
            _ensure_dirs()
            tmp_file = JOURNAL_FILE.with_suffix('.tmp')
            with open(tmp_file, "w") as f:
                json.dump(trades, f, indent=2, default=str)
            tmp_file.replace(JOURNAL_FILE)  # Atomic rename
        except Exception as e:
            logger.error(f"Could not save trade journal: {e}")


def _archive_old_trades(trades: List[Dict]) -> List[Dict]:
    """Archive trades older than 90 days when journal exceeds MAX_JOURNAL_SIZE.
    Returns the pruned trade list.
    """
    if len(trades) <= MAX_JOURNAL_SIZE:
        return trades
    
    cutoff = (datetime.now(ET) - timedelta(days=90)).isoformat()
    old_trades = [t for t in trades if t.get("timestamp", "") < cutoff]
    recent_trades = [t for t in trades if t.get("timestamp", "") >= cutoff]
    
    if old_trades:
        archive_name = f"archive_{datetime.now(ET).strftime('%Y%m%d_%H%M%S')}.json"
        archive_path = ARCHIVE_DIR / archive_name
        try:
            with open(archive_path, "w") as f:
                json.dump(old_trades, f, indent=2, default=str)
            logger.info(f"[PerfTracker] Archived {len(old_trades)} trades to {archive_name}")
        except Exception as e:
            logger.error(f"[PerfTracker] Failed to archive trades: {e}")
    
    return recent_trades


def log_trade(trade: Dict) -> Dict:
    """Log a completed trade to the journal.
    
    Calls memory.record_outcome() to sync with learning flywheel.
    """
    trades = _load_journal()

    # Build trade record with UUID (prevents ID collisions)
    record = {
        "id": str(uuid.uuid4()),  # UUID instead of sequential
        "seq_id": len(trades) + 1,  # Sequential for human readability
        "timestamp": datetime.now(ET).isoformat(),
        "symbol": trade.get("symbol", ""),
        "side": trade.get("side", "buy"),
        "entry_price": trade.get("entry_price", 0),
        "exit_price": trade.get("exit_price", 0),
        "shares": trade.get("shares", 0),
        "pnl_dollars": trade.get("pnl_dollars", 0),
        "pnl_pct": trade.get("pnl_pct", 0),
        "r_multiple": trade.get("r_multiple", 0),
        "exit_reason": trade.get("exit_reason", "unknown"),
        "regime": trade.get("regime", "unknown"),
        "sector": trade.get("sector", "unknown"),
        "entry_grade": trade.get("entry_grade", "C"),
        "entry_score": trade.get("entry_score", 0),
        "session": trade.get("session", "unknown"),
        "hold_hours": trade.get("hold_hours", 0),
        "targets_hit": trade.get("targets_hit", 0),
        "partial_exits": trade.get("partial_exits", []),
        "composite_score": trade.get("composite_score", 0),
        "source": trade.get("source", "unknown"),  # For memory sync
        "setup": trade.get("setup", "unknown"),    # For memory sync
        "win": trade.get("pnl_dollars", 0) > 0,
        "closed": True,  # Mark as closed for memory sync filter
        "close_date": datetime.now(ET).strftime("%Y-%m-%d"),
    }

    trades.append(record)
    
    # Auto-archive if journal exceeds MAX_JOURNAL_SIZE
    trades = _archive_old_trades(trades)
    
    _save_journal(trades)
    logger.info(f"Trade logged: {record['symbol']} {'WIN' if record['win'] else 'LOSS'} "
                f"${record['pnl_dollars']:+.2f} ({record['r_multiple']:.1f}R) "
                f"id={record['seq_id']}")
    
    # ISSUE #7 FIX: Sync with memory.py learning system
    try:
        from memory import trade_memory
        trade_memory.record_outcome(
            ticker=record['symbol'],
            source=record['source'],
            won=record['win'],
            pnl_pct=record['pnl_pct'],
            setup=record['setup'],
            regime=record['regime']
        )
    except ImportError:
        logger.debug("[PerfTracker] memory.py not available for sync")
    except Exception as e:
        logger.warning(f"[PerfTracker] Failed to sync with memory: {e}")
    
    return record


def calculate_stats(days: int = None) -> Dict:
    """Calculate comprehensive performance statistics."""
    trades = _load_journal()
    if not trades:
        return {"error": "No trades in journal", "total_trades": 0}

    # Filter by date range if specified
    if days:
        cutoff = (datetime.now(ET) - timedelta(days=days)).isoformat()
        trades = [t for t in trades if t.get("timestamp", "") >= cutoff]
        if not trades:
            return {"error": f"No trades in last {days} days", "total_trades": 0}

    # Basic stats
    total = len(trades)
    wins = [t for t in trades if t.get("win", False)]
    losses = [t for t in trades if not t.get("win", False)]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = round(win_count / total * 100, 1) if total > 0 else 0

    # P&L
    total_pnl = sum(t.get("pnl_dollars", 0) for t in trades)
    avg_win = sum(t.get("pnl_dollars", 0) for t in wins) / win_count if win_count > 0 else 0
    avg_loss = sum(t.get("pnl_dollars", 0) for t in losses) / loss_count if loss_count > 0 else 0

    # Expectancy
    expectancy = (win_rate / 100 * avg_win) + ((100 - win_rate) / 100 * avg_loss) if total > 0 else 0

    # R-multiples
    r_multiples = [t.get("r_multiple", 0) for t in trades if t.get("r_multiple") is not None]
    avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0
    total_r = sum(r_multiples)

    # Profit factor
    gross_profit = sum(t.get("pnl_dollars", 0) for t in wins)
    gross_loss = abs(sum(t.get("pnl_dollars", 0) for t in losses))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

    # Streaks
    max_win_streak = 0
    max_loss_streak = 0
    current_streak = 0
    for t in trades:
        if t.get("win"):
            current_streak = current_streak + 1 if current_streak > 0 else 1
            max_win_streak = max(max_win_streak, current_streak)
        else:
            current_streak = current_streak - 1 if current_streak < 0 else -1
            max_loss_streak = max(max_loss_streak, abs(current_streak))

    # Largest win/loss
    largest_win = max((t.get("pnl_dollars", 0) for t in trades), default=0)
    largest_loss = min((t.get("pnl_dollars", 0) for t in trades), default=0)

    return {
        "total_trades": total,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": win_rate,
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
        "avg_r_multiple": round(avg_r, 2),
        "total_r": round(total_r, 2),
        "profit_factor": profit_factor,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "largest_win": round(largest_win, 2),
        "largest_loss": round(largest_loss, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "period_days": days or "all",
    }


def analyze_by_regime() -> Dict:
    """Breakdown performance by market regime."""
    trades = _load_journal()
    if not trades:
        return {"error": "No trades"}

    regimes = {}
    for t in trades:
        regime = t.get("regime", "unknown")
        if regime not in regimes:
            regimes[regime] = {"trades": 0, "wins": 0, "pnl": 0, "r_total": 0}
        regimes[regime]["trades"] += 1
        if t.get("win"):
            regimes[regime]["wins"] += 1
        regimes[regime]["pnl"] += t.get("pnl_dollars", 0)
        regimes[regime]["r_total"] += t.get("r_multiple", 0)

    results = {}
    for regime, data in regimes.items():
        total = data["trades"]
        results[regime] = {
            "trades": total,
            "win_rate": round(data["wins"] / total * 100, 1) if total > 0 else 0,
            "total_pnl": round(data["pnl"], 2),
            "avg_pnl": round(data["pnl"] / total, 2) if total > 0 else 0,
            "total_r": round(data["r_total"], 2),
            "avg_r": round(data["r_total"] / total, 2) if total > 0 else 0,
        }
    return results


def analyze_by_entry_grade() -> Dict:
    """Breakdown performance by entry quality grade."""
    trades = _load_journal()
    if not trades:
        return {"error": "No trades"}

    grades = {}
    for t in trades:
        grade = t.get("entry_grade", "C")
        if grade not in grades:
            grades[grade] = {"trades": 0, "wins": 0, "pnl": 0, "r_total": 0}
        grades[grade]["trades"] += 1
        if t.get("win"):
            grades[grade]["wins"] += 1
        grades[grade]["pnl"] += t.get("pnl_dollars", 0)
        grades[grade]["r_total"] += t.get("r_multiple", 0)

    results = {}
    for grade, data in grades.items():
        total = data["trades"]
        results[grade] = {
            "trades": total,
            "win_rate": round(data["wins"] / total * 100, 1) if total > 0 else 0,
            "total_pnl": round(data["pnl"], 2),
            "avg_r": round(data["r_total"] / total, 2) if total > 0 else 0,
        }
    return results


def analyze_by_session() -> Dict:
    """Breakdown performance by trading session."""
    trades = _load_journal()
    if not trades:
        return {"error": "No trades"}

    sessions = {}
    for t in trades:
        session = t.get("session", "unknown")
        if session not in sessions:
            sessions[session] = {"trades": 0, "wins": 0, "pnl": 0}
        sessions[session]["trades"] += 1
        if t.get("win"):
            sessions[session]["wins"] += 1
        sessions[session]["pnl"] += t.get("pnl_dollars", 0)

    results = {}
    for session, data in sessions.items():
        total = data["trades"]
        results[session] = {
            "trades": total,
            "win_rate": round(data["wins"] / total * 100, 1) if total > 0 else 0,
            "total_pnl": round(data["pnl"], 2),
        }
    return results


def analyze_by_exit_reason() -> Dict:
    """Breakdown performance by exit reason."""
    trades = _load_journal()
    if not trades:
        return {"error": "No trades"}

    reasons = {}
    for t in trades:
        reason = t.get("exit_reason", "unknown")
        if reason not in reasons:
            reasons[reason] = {"trades": 0, "wins": 0, "pnl": 0}
        reasons[reason]["trades"] += 1
        if t.get("win"):
            reasons[reason]["wins"] += 1
        reasons[reason]["pnl"] += t.get("pnl_dollars", 0)

    results = {}
    for reason, data in reasons.items():
        total = data["trades"]
        results[reason] = {
            "trades": total,
            "win_rate": round(data["wins"] / total * 100, 1) if total > 0 else 0,
            "total_pnl": round(data["pnl"], 2),
        }
    return results


def format_performance_report(days: int = None) -> str:
    """Generate Slack-formatted performance report."""
    stats = calculate_stats(days)
    if stats.get("error"):
        return f"No trade data available: {stats.get('error')}"

    period = f"Last {days} Days" if days else "All Time"
    pnl_emoji = "\U0001f7e2" if stats.get("total_pnl", 0) >= 0 else "\U0001f534"

    lines = [
        f"\U0001f4ca *Performance Report: {period}*",
        f"",
        f"{pnl_emoji} *Total P&L: ${stats['total_pnl']:+,.2f}*",
        f"  Trades: {stats['total_trades']} | Win Rate: {stats['win_rate']}%",
        f"  Avg Win: ${stats['avg_win']:+.2f} | Avg Loss: ${stats['avg_loss']:+.2f}",
        f"  Expectancy: ${stats['expectancy']:+.2f}/trade",
        f"  Profit Factor: {stats['profit_factor']}",
        f"",
        f"\U0001f3af *R-Multiples:*",
        f"  Avg R: {stats['avg_r_multiple']:.2f}R | Total R: {stats['total_r']:.1f}R",
        f"",
        f"\U0001f525 *Streaks:*",
        f"  Best Win Streak: {stats['max_win_streak']}",
        f"  Worst Loss Streak: {stats['max_loss_streak']}",
        f"  Largest Win: ${stats['largest_win']:+.2f}",
        f"  Largest Loss: ${stats['largest_loss']:+.2f}",
    ]
    return "\n".join(lines)


def format_regime_report() -> str:
    """Slack-formatted regime performance breakdown."""
    data = analyze_by_regime()
    if isinstance(data, dict) and "error" in data:
        return "No regime data available"

    lines = ["\U0001f30e *Performance by Market Regime:*", ""]
    for regime, stats in data.items():
        emoji = "\U0001f7e2" if stats["total_pnl"] >= 0 else "\U0001f534"
        lines.append(f"{emoji} *{regime.upper()}*: {stats['trades']} trades | "
                     f"WR: {stats['win_rate']}% | P&L: ${stats['total_pnl']:+.2f} | "
                     f"Avg R: {stats['avg_r']:.2f}R")
    return "\n".join(lines)


def format_grade_report() -> str:
    """Slack-formatted entry grade performance."""
    data = analyze_by_entry_grade()
    if isinstance(data, dict) and "error" in data:
        return "No grade data available"

    lines = ["\U0001f4dd *Performance by Entry Grade:*", ""]
    for grade in ["A+", "A", "B+", "B", "C+", "C", "D", "F"]:
        if grade in data:
            stats = data[grade]
            emoji = "\U0001f7e2" if stats["total_pnl"] >= 0 else "\U0001f534"
            lines.append(f"{emoji} Grade *{grade}*: {stats['trades']} trades | "
                         f"WR: {stats['win_rate']}% | P&L: ${stats['total_pnl']:+.2f} | "
                         f"Avg R: {stats['avg_r']:.2f}R")
    return "\n".join(lines)


def get_recent_trades(count: int = 10) -> List[Dict]:
    """Get the most recent N trades."""
    trades = _load_journal()
    return trades[-count:] if len(trades) >= count else trades


def get_trade_count() -> int:
    """Get total number of logged trades."""
    return len(_load_journal())
