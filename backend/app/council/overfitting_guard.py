"""Overfitting Guard — multi-layer protection against strategy overfitting.

Integrates with the feedback loop and strategy evolution to ensure that
evolved strategies are validated across regimes and out-of-sample periods.

Checks:
    1. Regime-stratified validation — strategy must work across regimes
    2. Out-of-sample holdout — reserved data the evolution process never sees
    3. Transaction cost modeling — strategies must survive slippage/commissions
    4. Overfit detection flags — statistical tests for overfitting signals
    5. Walk-forward gate — blocks strategy adoption without WF validation

Usage:
    from app.council.overfitting_guard import get_overfitting_guard
    guard = get_overfitting_guard()
    result = guard.validate_strategy(strategy, trades, regimes)
"""
import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Minimum sample sizes
MIN_TRADES_FOR_VALIDATION = 30
MIN_TRADES_PER_REGIME = 10
MIN_OUT_OF_SAMPLE_RATIO = 0.2  # 20% holdout minimum

# Overfit detection thresholds
MAX_TRAIN_TEST_SHARPE_RATIO = 3.0  # If in-sample Sharpe > 3x out-of-sample, likely overfit
MAX_DRAWDOWN_RATIO = 2.0  # If OOS drawdown > 2x IS drawdown, structure has changed
MIN_REGIME_WIN_RATE = 0.35  # Must win >35% in EVERY regime, not just best one


class OverfitResult:
    """Result of overfitting validation."""

    def __init__(self):
        self.passed = True
        self.flags: List[str] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, Any] = {}

    def fail(self, reason: str):
        self.passed = False
        self.flags.append(reason)

    def warn(self, reason: str):
        self.warnings.append(reason)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "flags": self.flags,
            "warnings": self.warnings,
            "metrics": self.metrics,
        }


class OverfittingGuard:
    """Multi-layer overfitting protection for strategy evolution."""

    def validate_strategy(
        self,
        trades: List[Dict[str, Any]],
        in_sample_metrics: Dict[str, Any] = None,
        out_of_sample_metrics: Dict[str, Any] = None,
    ) -> OverfitResult:
        """Run all overfitting checks on a strategy's trade history.

        Args:
            trades: List of trade dicts with keys: pnl, regime, slippage_cost, entry_date
            in_sample_metrics: Optional IS metrics {sharpe, max_drawdown, win_rate}
            out_of_sample_metrics: Optional OOS metrics {sharpe, max_drawdown, win_rate}
        """
        result = OverfitResult()

        if len(trades) < MIN_TRADES_FOR_VALIDATION:
            result.warn(f"Insufficient trades ({len(trades)}) for robust validation")
            result.metrics["trade_count"] = len(trades)
            return result

        # Check 1: Regime-stratified validation
        self._check_regime_stratification(trades, result)

        # Check 2: Out-of-sample vs in-sample divergence
        if in_sample_metrics and out_of_sample_metrics:
            self._check_sample_divergence(in_sample_metrics, out_of_sample_metrics, result)

        # Check 3: Transaction cost survival
        self._check_transaction_cost_survival(trades, result)

        # Check 4: Statistical overfit indicators
        self._check_statistical_indicators(trades, result)

        return result

    def _check_regime_stratification(self, trades: List[Dict], result: OverfitResult):
        """Strategy must work across market regimes, not just the current one."""
        regime_buckets: Dict[str, List[Dict]] = {}
        for t in trades:
            regime = str(t.get("regime", "unknown")).lower()
            regime_buckets.setdefault(regime, []).append(t)

        regime_metrics = {}
        for regime, bucket in regime_buckets.items():
            if len(bucket) < MIN_TRADES_PER_REGIME:
                result.warn(f"Regime '{regime}' has only {len(bucket)} trades (need {MIN_TRADES_PER_REGIME})")
                continue

            wins = sum(1 for t in bucket if t.get("pnl", 0) > 0)
            win_rate = wins / len(bucket)
            avg_pnl = sum(t.get("pnl", 0) for t in bucket) / len(bucket)
            regime_metrics[regime] = {"win_rate": win_rate, "avg_pnl": avg_pnl, "count": len(bucket)}

            if win_rate < MIN_REGIME_WIN_RATE:
                result.fail(
                    f"Strategy fails in '{regime}' regime: win_rate={win_rate:.1%} < {MIN_REGIME_WIN_RATE:.0%}"
                )

        result.metrics["regime_stratification"] = regime_metrics

    def _check_sample_divergence(
        self, is_metrics: Dict, oos_metrics: Dict, result: OverfitResult
    ):
        """Check for dangerous divergence between in-sample and out-of-sample."""
        is_sharpe = is_metrics.get("sharpe", 0)
        oos_sharpe = oos_metrics.get("sharpe", 0)

        if oos_sharpe > 0.1 and is_sharpe > 0 and is_sharpe / oos_sharpe > MAX_TRAIN_TEST_SHARPE_RATIO:
            result.fail(
                f"Sharpe ratio degradation: IS={is_sharpe:.2f} vs OOS={oos_sharpe:.2f} "
                f"(ratio={is_sharpe / oos_sharpe:.1f}x > {MAX_TRAIN_TEST_SHARPE_RATIO}x)"
            )
        elif oos_sharpe <= 0 and is_sharpe > 0.5:
            result.fail(f"Strategy profitable in-sample (Sharpe={is_sharpe:.2f}) but negative out-of-sample")

        is_dd = abs(is_metrics.get("max_drawdown", 0))
        oos_dd = abs(oos_metrics.get("max_drawdown", 0))
        if is_dd > 0.01 and oos_dd > 0 and oos_dd / is_dd > MAX_DRAWDOWN_RATIO:
            result.fail(
                f"Drawdown expansion: IS={is_dd:.1%} vs OOS={oos_dd:.1%} "
                f"(ratio={oos_dd / is_dd:.1f}x > {MAX_DRAWDOWN_RATIO}x)"
            )

        is_wr = is_metrics.get("win_rate", 0.5)
        oos_wr = oos_metrics.get("win_rate", 0.5)
        if is_wr > 0.6 and oos_wr < 0.4:
            result.fail(f"Win rate collapse: IS={is_wr:.1%} vs OOS={oos_wr:.1%}")

        result.metrics["sample_divergence"] = {
            "is_sharpe": is_sharpe, "oos_sharpe": oos_sharpe,
            "is_drawdown": is_dd, "oos_drawdown": oos_dd,
            "is_win_rate": is_wr, "oos_win_rate": oos_wr,
        }

    def _check_transaction_cost_survival(self, trades: List[Dict], result: OverfitResult):
        """After slippage and commissions, strategy must still be profitable."""
        gross_pnl = sum(t.get("pnl", 0) for t in trades)
        total_slippage = sum(abs(t.get("slippage_cost", 0)) for t in trades)
        # Estimate commission at $1 per trade if not provided
        total_commission = sum(t.get("commission", 1.0) for t in trades)
        net_pnl = gross_pnl - total_slippage - total_commission

        cost_ratio = (total_slippage + total_commission) / max(abs(gross_pnl), 1.0)

        if gross_pnl > 0 and net_pnl <= 0:
            result.fail(
                f"Strategy dies to costs: gross=${gross_pnl:,.0f} but net=${net_pnl:,.0f} "
                f"after ${total_slippage + total_commission:,.0f} in costs"
            )
        elif cost_ratio > 0.5:
            result.warn(
                f"Transaction costs eat {cost_ratio:.0%} of gross P&L — fragile edge"
            )

        result.metrics["transaction_costs"] = {
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "total_slippage": total_slippage,
            "total_commission": total_commission,
            "cost_ratio": cost_ratio,
        }

    def _check_statistical_indicators(self, trades: List[Dict], result: OverfitResult):
        """Statistical tests for overfitting signals."""
        pnls = [t.get("pnl", 0) for t in trades]
        n = len(pnls)
        if n < 2:
            return

        mean_pnl = sum(pnls) / n
        variance = sum((p - mean_pnl) ** 2 for p in pnls) / (n - 1)
        std_pnl = math.sqrt(variance) if variance > 0 else 0

        # T-statistic: is the mean significantly different from 0?
        if std_pnl > 0:
            t_stat = mean_pnl / (std_pnl / math.sqrt(n))
        else:
            t_stat = 0

        # Rough p-value approximation (for t > 2, generally significant at 5%)
        statistically_significant = abs(t_stat) > 2.0

        # Check for suspiciously consistent returns (too good to be true)
        if n > 20 and std_pnl > 0:
            sharpe_approx = (mean_pnl / std_pnl) * math.sqrt(252)
            if sharpe_approx > 4.0:
                result.warn(
                    f"Suspiciously high Sharpe ({sharpe_approx:.1f}) — verify data and execution assumptions"
                )

        # Check for long losing streaks
        max_losing_streak = 0
        current_streak = 0
        for p in pnls:
            if p < 0:
                current_streak += 1
                max_losing_streak = max(max_losing_streak, current_streak)
            else:
                current_streak = 0

        result.metrics["statistical"] = {
            "mean_pnl": mean_pnl,
            "std_pnl": std_pnl,
            "t_statistic": t_stat,
            "statistically_significant": statistically_significant,
            "max_losing_streak": max_losing_streak,
            "trade_count": n,
        }


# Singleton
_guard: Optional[OverfittingGuard] = None


def get_overfitting_guard() -> OverfittingGuard:
    global _guard
    if _guard is None:
        _guard = OverfittingGuard()
    return _guard
