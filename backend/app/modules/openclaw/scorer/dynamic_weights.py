"""dynamic_weights.py - AI-Driven Dynamic Weight Optimization

Online Bayesian optimization system that learns optimal pillar weights
from actual trade outcomes. Uses Optuna for weight optimization per
regime state, with continuous learning and backtesting validation.

Prompt 5 of OpenClaw Real-Time Trading Engine.
"""

import json
import os
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Optuna for Bayesian optimization
try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False

# Setup logging
logger = logging.getLogger('dynamic_weights')
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# =============================================================
# CONFIGURATION & DEFAULTS
# =============================================================

# File paths
DATA_DIR = Path('data')
WEIGHTS_FILE = DATA_DIR / 'optimized_weights.json'
HISTORY_FILE = DATA_DIR / 'weight_history.json'

# Default pillar weights (sum = 100)
DEFAULT_WEIGHTS = {
    'GREEN': {
        'regime': 20, 'trend': 25, 'pullback': 25,
        'momentum': 20, 'pattern': 10, 'em_alignment': 0
    },
    'YELLOW': {
        'regime': 22, 'trend': 25, 'pullback': 25,
        'momentum': 18, 'pattern': 10, 'em_alignment': 0
    },
    'RED': {
        'regime': 25, 'trend': 20, 'pullback': 28,
        'momentum': 17, 'pattern': 10, 'em_alignment': 0
    }
}

# Optimization bounds for each pillar
WEIGHT_BOUNDS = {
    'regime': (10, 30),
    'trend': (15, 35),
    'pullback': (15, 35),
    'momentum': (10, 30),
    'pattern': (5, 15),
    'em_alignment': (0, 15)
}

# Optimization parameters
OPTUNA_TRIALS = 50
MIN_TRADES_FOR_OPTIMIZATION = 20
SHARPE_IMPROVEMENT_THRESHOLD = 0.1
CONFIDENCE_LOW_THRESHOLD = 20
CONFIDENCE_HIGH_THRESHOLD = 50
WEIGHT_SUM_TARGET = 100
TRAILING_WINDOW_DAYS = 30
BACKTEST_WINDOW = 100


# =============================================================
# PERFORMANCE METRICS
# =============================================================

def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate annualized Sharpe ratio from trade returns."""
    if not returns or len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    mean_return = np.mean(arr)
    std_return = np.std(arr, ddof=1)
    if std_return == 0:
        return 0.0
    # Annualize: assume ~252 trading days
    sharpe = (mean_return - risk_free_rate) / std_return * np.sqrt(252)
    return round(float(sharpe), 4)


def calculate_profit_factor(returns: List[float]) -> float:
    """Calculate profit factor = gross profits / gross losses."""
    if not returns:
        return 0.0
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    if gross_loss == 0:
        return 10.0 if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 4)


def calculate_max_drawdown(returns: List[float]) -> float:
    """Calculate maximum drawdown from sequential returns."""
    if not returns:
        return 0.0
    equity = [1.0]
    for r in returns:
        equity.append(equity[-1] * (1 + r))
    peak = equity[0]
    max_dd = 0.0
    for val in equity:
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 4)


def calculate_win_rate(returns: List[float]) -> float:
    """Calculate win rate from trade returns."""
    if not returns:
        return 0.0
    winners = sum(1 for r in returns if r > 0)
    return round(winners / len(returns), 4)


def calculate_avg_r_multiple(returns: List[float], risk_per_trade: float = 0.01) -> float:
    """Calculate average R-multiple (return / risk)."""
    if not returns or risk_per_trade == 0:
        return 0.0
    r_multiples = [r / risk_per_trade for r in returns]
    return round(float(np.mean(r_multiples)), 4)


def calculate_weight_performance(trades: List[Dict], weights: Dict) -> Dict:
    """Comprehensive performance metrics for a given weight set."""
    returns = [t.get('return_pct', 0) / 100 for t in trades if 'return_pct' in t]
    if not returns:
        return {
            'sharpe': 0.0, 'win_rate': 0.0, 'profit_factor': 0.0,
            'max_drawdown': 0.0, 'avg_r_multiple': 0.0, 'trades': 0
        }
    return {
        'sharpe': calculate_sharpe_ratio(returns),
        'win_rate': calculate_win_rate(returns),
        'profit_factor': calculate_profit_factor(returns),
        'max_drawdown': calculate_max_drawdown(returns),
        'avg_r_multiple': calculate_avg_r_multiple(returns),
        'trades': len(returns)
    }


# =============================================================
# WEIGHT PERSISTENCE
# =============================================================

def load_weights() -> Dict:
    """Load optimized weights from file, fallback to defaults."""
    try:
        if WEIGHTS_FILE.exists():
            with open(WEIGHTS_FILE, 'r') as f:
                data = json.load(f)
            logger.info('Loaded optimized weights from %s', WEIGHTS_FILE)
            return data
    except Exception as e:
        logger.warning('Failed to load weights: %s', e)

    logger.info('Using default weights')
    result = {}
    for regime in ['GREEN', 'YELLOW', 'RED']:
        result[regime] = {
            'weights': DEFAULT_WEIGHTS[regime].copy(),
            'performance': {
                'sharpe': 0.0, 'win_rate': 0.0,
                'profit_factor': 0.0, 'trades': 0
            },
            'last_updated': datetime.now().isoformat(),
            'confidence': 0.5
        }
    return result


def save_weights(weights_data: Dict) -> bool:
    """Save optimized weights to file."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(WEIGHTS_FILE, 'w') as f:
            json.dump(weights_data, f, indent=2, default=str)
        logger.info('Saved optimized weights to %s', WEIGHTS_FILE)
        return True
    except Exception as e:
        logger.error('Failed to save weights: %s', e)
        return False


def save_weight_history(entry: Dict) -> bool:
    """Append optimization result to history file."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        history = []
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        history.append(entry)
        # Keep last 100 entries
        history = history[-100:]
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2, default=str)
        return True
    except Exception as e:
        logger.error('Failed to save weight history: %s', e)
        return False


def get_regime_weights(regime: str) -> Dict:
    """Get current optimized weights for a specific regime."""
    data = load_weights()
    regime = regime.upper()
    if regime not in data:
        return DEFAULT_WEIGHTS.get(regime, DEFAULT_WEIGHTS['GREEN'])
    return data[regime].get('weights', DEFAULT_WEIGHTS.get(regime, {}))


def get_weight_confidence(regime: str) -> float:
    """Get confidence level for a regime's weight set (0.5-1.0)."""
    data = load_weights()
    regime = regime.upper()
    if regime not in data:
        return 0.5
    trades = data[regime].get('performance', {}).get('trades', 0)
    if trades < CONFIDENCE_LOW_THRESHOLD:
        return 0.5
    elif trades < CONFIDENCE_HIGH_THRESHOLD:
        # Linear interpolation between 0.5 and 1.0
        pct = (trades - CONFIDENCE_LOW_THRESHOLD) / (
            CONFIDENCE_HIGH_THRESHOLD - CONFIDENCE_LOW_THRESHOLD
        )
        return round(0.5 + pct * 0.5, 2)
    return 1.0


# =============================================================
# OPTUNA BAYESIAN OPTIMIZATION ENGINE
# =============================================================

def _simulate_score(trade: Dict, weights: Dict) -> float:
    """Re-score a historical trade with given weights.
    
    Takes a trade's pillar sub-scores and applies new weights
    to produce a composite score.
    """
    pillars = trade.get('pillar_scores', {})
    if not pillars:
        return 0.0

    # Normalize pillar raw scores to 0-1 range based on pillar max
    pillar_maxes = {
        'regime': 20, 'trend': 25, 'pullback': 25,
        'momentum': 20, 'pattern': 10, 'em_alignment': 10
    }

    score = 0.0
    for pillar, weight in weights.items():
        raw = pillars.get(pillar, 0)
        pmax = pillar_maxes.get(pillar, 10)
        normalized = min(raw / pmax, 1.0) if pmax > 0 else 0
        score += normalized * weight

    return score


def _compute_returns_for_weights(trades: List[Dict], weights: Dict,
                                 threshold: float = 50.0) -> List[float]:
    """Given weights, re-score trades and return list of returns
    for trades that would have been taken (score >= threshold)."""
    returns = []
    for trade in trades:
        score = _simulate_score(trade, weights)
        if score >= threshold:
            ret = trade.get('return_pct', 0) / 100
            returns.append(ret)
    return returns


def optimize_weights(trade_history: List[Dict],
                     regime: str = 'GREEN',
                     n_trials: int = None) -> Optional[Dict]:
    """Run Optuna Bayesian optimization to find best pillar weights.
    
    Args:
        trade_history: List of closed trades with pillar_scores and return_pct
        regime: Market regime to optimize for
        n_trials: Number of optimization trials (default: OPTUNA_TRIALS)
    
    Returns:
        Dict with optimized weights and performance metrics, or None
    """
    if not OPTUNA_AVAILABLE:
        logger.warning('Optuna not installed. Using default weights.')
        return None

    n_trials = n_trials or OPTUNA_TRIALS

    # Filter trades for this regime
    regime_trades = [
        t for t in trade_history
        if t.get('regime', '').upper() == regime.upper()
    ]

    if len(regime_trades) < MIN_TRADES_FOR_OPTIMIZATION:
        logger.info(
            'Only %d trades for %s regime (need %d). Skipping.',
            len(regime_trades), regime, MIN_TRADES_FOR_OPTIMIZATION
        )
        return None

    logger.info(
        'Running Optuna optimization for %s regime (%d trades, %d trials)',
        regime, len(regime_trades), n_trials
    )

    def objective(trial):
        # Suggest weights within bounds
        w = {}
        for pillar, (lo, hi) in WEIGHT_BOUNDS.items():
            w[pillar] = trial.suggest_int(pillar, lo, hi)

        # Normalize to sum to WEIGHT_SUM_TARGET
        total = sum(w.values())
        if total == 0:
            return -999.0
        factor = WEIGHT_SUM_TARGET / total
        w = {k: round(v * factor) for k, v in w.items()}

        # Simulate returns with these weights
        returns = _compute_returns_for_weights(regime_trades, w)

        if len(returns) < 5:
            return -999.0

        sharpe = calculate_sharpe_ratio(returns)
        win_rate = calculate_win_rate(returns)

        # Multi-objective: primarily Sharpe, with win rate bonus
        score = sharpe + (win_rate * 0.5)
        return score

    # Create and run study
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    # Extract best weights
    best_params = study.best_params
    total = sum(best_params.values())
    if total == 0:
        return None
    factor = WEIGHT_SUM_TARGET / total
    optimized = {k: round(v * factor) for k, v in best_params.items()}

    # Calculate performance with optimized weights
    opt_returns = _compute_returns_for_weights(regime_trades, optimized)
    performance = {
        'sharpe': calculate_sharpe_ratio(opt_returns),
        'win_rate': calculate_win_rate(opt_returns),
        'profit_factor': calculate_profit_factor(opt_returns),
        'max_drawdown': calculate_max_drawdown(opt_returns),
        'trades': len(opt_returns)
    }

    logger.info(
        '%s optimized: Sharpe=%.2f, WinRate=%.1f%%, Weights=%s',
        regime, performance['sharpe'], performance['win_rate'] * 100,
        optimized
    )

    return {
        'weights': optimized,
        'performance': performance,
        'best_trial_value': round(study.best_value, 4),
        'n_trials': n_trials,
        'n_trades': len(regime_trades)
    }


# =============================================================
# BACKTESTING & VALIDATION
# =============================================================

def validate_new_weights(old_weights: Dict, new_weights: Dict,
                         historical_trades: List[Dict],
                         regime: str = 'GREEN') -> bool:
    """Validate new weights against historical data before adopting.
    
    Requires new weights to improve Sharpe by SHARPE_IMPROVEMENT_THRESHOLD.
    """
    regime_trades = [
        t for t in historical_trades
        if t.get('regime', '').upper() == regime.upper()
    ]

    if len(regime_trades) < 10:
        logger.info('Not enough historical trades for validation.')
        return False

    old_returns = _compute_returns_for_weights(regime_trades, old_weights)
    new_returns = _compute_returns_for_weights(regime_trades, new_weights)

    old_sharpe = calculate_sharpe_ratio(old_returns)
    new_sharpe = calculate_sharpe_ratio(new_returns)

    improvement = new_sharpe - old_sharpe

    logger.info(
        'Validation: Old Sharpe=%.4f, New Sharpe=%.4f, Improvement=%.4f',
        old_sharpe, new_sharpe, improvement
    )

    if improvement >= SHARPE_IMPROVEMENT_THRESHOLD:
        logger.info('New weights PASS validation (improvement >= %.2f)',
                     SHARPE_IMPROVEMENT_THRESHOLD)
        return True
    else:
        logger.info('New weights FAIL validation (improvement < %.2f)',
                     SHARPE_IMPROVEMENT_THRESHOLD)
        return False


# =============================================================
# CONTINUOUS LEARNING LOOP
# =============================================================

def continuous_weight_update(trade_history: List[Dict]) -> Dict:
    """After trades close, check if weights should be updated.
    
    Runs optimization for each regime and adopts improvements.
    Returns summary of what changed.
    """
    current_data = load_weights()
    changes = {'updated': [], 'skipped': [], 'errors': []}

    for regime in ['GREEN', 'YELLOW', 'RED']:
        try:
            # Get current weights
            current_weights = current_data.get(regime, {}).get(
                'weights', DEFAULT_WEIGHTS[regime]
            )

            # Run optimization
            result = optimize_weights(trade_history, regime)
            if result is None:
                changes['skipped'].append(regime)
                continue

            new_weights = result['weights']

            # Validate against backtest
            if validate_new_weights(
                current_weights, new_weights,
                trade_history, regime
            ):
                # Adopt new weights
                current_data[regime] = {
                    'weights': new_weights,
                    'performance': result['performance'],
                    'last_updated': datetime.now().isoformat(),
                    'confidence': min(
                        1.0,
                        result['performance']['trades'] / CONFIDENCE_HIGH_THRESHOLD
                    )
                }
                changes['updated'].append({
                    'regime': regime,
                    'old_weights': current_weights,
                    'new_weights': new_weights,
                    'sharpe': result['performance']['sharpe']
                })
                logger.info('Adopted new weights for %s regime', regime)
            else:
                changes['skipped'].append(regime)

        except Exception as e:
            logger.error('Error optimizing %s: %s', regime, e)
            changes['errors'].append({'regime': regime, 'error': str(e)})

    # Save updated weights
    if changes['updated']:
        save_weights(current_data)
        save_weight_history({
            'timestamp': datetime.now().isoformat(),
            'changes': changes
        })

    return changes


# =============================================================
# SCHEDULED OPTIMIZATION
# =============================================================

def scheduled_optimization(trade_history: List[Dict] = None) -> Dict:
    """Weekly scheduled optimization (run Friday 4:30 PM ET).
    
    Loads trade history if not provided, runs full optimization
    for all regimes, and returns results summary.
    """
    logger.info('=== Starting scheduled weight optimization ===')

    if trade_history is None:
        trade_history = load_trade_history()

    if not trade_history:
        logger.warning('No trade history available for optimization.')
        return {'status': 'no_data'}

    # Filter to trailing window
    cutoff = datetime.now() - timedelta(days=TRAILING_WINDOW_DAYS)
    recent_trades = [
        t for t in trade_history
        if t.get('close_date', t.get('date', '')) >= cutoff.isoformat()
    ]

    logger.info('Optimizing with %d recent trades (last %d days)',
                len(recent_trades), TRAILING_WINDOW_DAYS)

    changes = continuous_weight_update(recent_trades)

    # Build summary
    summary = {
        'status': 'completed',
        'timestamp': datetime.now().isoformat(),
        'total_trades': len(recent_trades),
        'regimes_updated': [c['regime'] for c in changes.get('updated', [])],
        'regimes_skipped': changes.get('skipped', []),
        'errors': changes.get('errors', [])
    }

    # Format Slack message
    if changes.get('updated'):
        for update in changes['updated']:
            w = update['new_weights']
            logger.info(
                'Slack: Weight Optimization: %s Sharpe=%.2f | '
                'R:%d T:%d P:%d M:%d Pat:%d EM:%d',
                update['regime'], update['sharpe'],
                w.get('regime', 0), w.get('trend', 0),
                w.get('pullback', 0), w.get('momentum', 0),
                w.get('pattern', 0), w.get('em_alignment', 0)
            )
    else:
        logger.info('No weight changes this cycle.')

    logger.info('=== Scheduled optimization complete ===')
    return summary


def load_trade_history() -> List[Dict]:
    """Load trade history from performance tracker."""
    history_path = DATA_DIR / 'trade_journal.json'
    try:
        if history_path.exists():
            with open(history_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error('Failed to load trade history: %s', e)
    return []


# =============================================================
# DISPLAY & REPORTING
# =============================================================

def show_current_weights() -> str:
    """Display current optimized weights for all regimes."""
    data = load_weights()
    lines = ['=== Current Optimized Weights ===']

    for regime in ['GREEN', 'YELLOW', 'RED']:
        entry = data.get(regime, {})
        weights = entry.get('weights', DEFAULT_WEIGHTS.get(regime, {}))
        perf = entry.get('performance', {})
        conf = entry.get('confidence', 0.5)
        updated = entry.get('last_updated', 'never')

        lines.append(f'\n--- {regime} Regime ---')
        lines.append(
            f"  Weights: R:{weights.get('regime', 0)} "
            f"T:{weights.get('trend', 0)} "
            f"P:{weights.get('pullback', 0)} "
            f"M:{weights.get('momentum', 0)} "
            f"Pat:{weights.get('pattern', 0)} "
            f"EM:{weights.get('em_alignment', 0)}"
        )
        lines.append(
            f"  Performance: Sharpe={perf.get('sharpe', 0):.2f} | "
            f"WinRate={perf.get('win_rate', 0)*100:.1f}% | "
            f"PF={perf.get('profit_factor', 0):.2f} | "
            f"Trades={perf.get('trades', 0)}"
        )
        lines.append(f'  Confidence: {conf:.0%} | Updated: {updated}')

    output = '\n'.join(lines)
    logger.info(output)
    return output


def show_weight_history(n: int = 10) -> str:
    """Show last N weight optimization events."""
    try:
        if not HISTORY_FILE.exists():
            logger.info('No weight history found.')
            return 'No history'
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
    except Exception:
        return 'Error loading history'

    lines = [f'=== Last {n} Weight Optimizations ===']
    for entry in history[-n:]:
        ts = entry.get('timestamp', '?')
        changes = entry.get('changes', {})
        updated = changes.get('updated', [])
        if updated:
            for u in updated:
                lines.append(
                    f"{ts}: {u['regime']} updated | Sharpe={u.get('sharpe', 0):.2f}"
                )
        else:
            lines.append(f'{ts}: No changes')

    output = '\n'.join(lines)
    logger.info(output)
    return output


def initialize_weights_file() -> bool:
    """Create initial optimized_weights.json with defaults."""
    data = {}
    for regime in ['GREEN', 'YELLOW', 'RED']:
        data[regime] = {
            'weights': DEFAULT_WEIGHTS[regime].copy(),
            'performance': {
                'sharpe': 0.0, 'win_rate': 0.0,
                'profit_factor': 0.0, 'trades': 0
            },
            'last_updated': datetime.now().isoformat(),
            'confidence': 0.5
        }
    return save_weights(data)


# =============================================================
# CLI INTERFACE
# =============================================================

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python dynamic_weights.py [--optimize|--show|--backtest|--init]')
        sys.exit(1)

    command = sys.argv[1]

    if command == '--optimize':
        print('Running manual optimization...')
        result = scheduled_optimization()
        print(f'Result: {json.dumps(result, indent=2, default=str)}')

    elif command == '--show':
        show_current_weights()
        print()
        show_weight_history()

    elif command == '--backtest':
        print('Running backtest validation...')
        history = load_trade_history()
        if not history:
            print('No trade history found.')
        else:
            for regime in ['GREEN', 'YELLOW', 'RED']:
                current = get_regime_weights(regime)
                trades = [
                    t for t in history
                    if t.get('regime', '').upper() == regime
                ]
                if len(trades) < 10:
                    print(f'{regime}: Not enough trades ({len(trades)})')
                    continue
                returns = _compute_returns_for_weights(trades, current)
                perf = {
                    'sharpe': calculate_sharpe_ratio(returns),
                    'win_rate': calculate_win_rate(returns),
                    'profit_factor': calculate_profit_factor(returns),
                    'trades': len(returns)
                }
                print(f'{regime}: {json.dumps(perf, indent=2)}')

    elif command == '--init':
        print('Initializing weights file...')
        if initialize_weights_file():
            print(f'Created {WEIGHTS_FILE}')
        else:
            print('Failed to create weights file.')

    else:
        print(f'Unknown command: {command}')
        print('Usage: python dynamic_weights.py [--optimize|--show|--backtest|--init]')
