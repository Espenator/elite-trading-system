"""GPU Channel 3 — Monte Carlo VaR (10,000 correlated paths on RTX 4080).

Computes portfolio Value-at-Risk and Conditional VaR using Cholesky-decomposed
correlated random walks on the GPU. Target: ~20ms for 10K paths vs ~800ms CPU.

Falls back transparently to NumPy if CuPy is unavailable.

Usage:
    from app.modules.ml_engine.monte_carlo_var import compute_portfolio_var
    result = compute_portfolio_var(returns_matrix, weights, n_paths=10_000)
    # result = {"var_95": -0.023, "cvar_95": -0.031, "var_99": -0.038, ...}
"""
import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# GPU Channel 3: CuPy for GPU-accelerated Monte Carlo
try:
    import cupy as cp
    GPU_VAR = True
    logger.info("Monte Carlo VaR: CuPy GPU acceleration ENABLED")
except ImportError:
    cp = np  # type: ignore[assignment]
    GPU_VAR = False


def compute_portfolio_var(
    returns_matrix: np.ndarray,
    weights: np.ndarray,
    n_paths: int = 10_000,
    confidence_levels: List[float] = None,
    horizon_days: int = 1,
) -> Dict[str, Any]:
    """Compute portfolio VaR via Monte Carlo simulation.

    Args:
        returns_matrix: (n_days, n_positions) historical daily returns
        weights: (n_positions,) portfolio weights (sum to 1)
        n_paths: number of simulation paths (default 10K)
        confidence_levels: VaR confidence levels (default [0.95, 0.99])
        horizon_days: VaR horizon in days (default 1)

    Returns:
        Dict with var_95, cvar_95, var_99, cvar_99, max_loss, gpu_used, latency_ms
    """
    if confidence_levels is None:
        confidence_levels = [0.95, 0.99]

    t0 = time.monotonic()

    try:
        # Move to GPU if available
        xp = cp if GPU_VAR else np
        returns_gpu = xp.asarray(returns_matrix)
        weights_gpu = xp.asarray(weights)

        # Compute covariance matrix and mean returns
        cov_matrix = xp.cov(returns_gpu.T)
        mean_returns = xp.mean(returns_gpu, axis=0)

        # Cholesky decomposition for correlated sampling
        L = xp.linalg.cholesky(cov_matrix)

        # Generate correlated random paths
        n_positions = len(weights)
        z = xp.random.standard_normal((n_paths, n_positions))
        correlated_returns = mean_returns + z @ L.T

        # Scale for horizon
        if horizon_days > 1:
            correlated_returns = correlated_returns * xp.sqrt(horizon_days)

        # Portfolio returns for each path
        port_returns = correlated_returns @ weights_gpu

        # Sort for VaR calculation
        sorted_returns = xp.sort(port_returns)

        result: Dict[str, Any] = {
            "n_paths": n_paths,
            "n_positions": n_positions,
            "horizon_days": horizon_days,
            "gpu_used": GPU_VAR,
        }

        for level in confidence_levels:
            idx = int((1 - level) * n_paths)
            var_value = float(sorted_returns[idx])
            # CVaR = expected loss beyond VaR
            cvar_value = float(xp.mean(sorted_returns[:idx])) if idx > 0 else var_value
            level_str = str(int(level * 100))
            result[f"var_{level_str}"] = round(var_value, 6)
            result[f"cvar_{level_str}"] = round(cvar_value, 6)

        result["max_loss"] = round(float(sorted_returns[0]), 6)
        result["mean_return"] = round(float(xp.mean(port_returns)), 6)
        result["std_return"] = round(float(xp.std(port_returns)), 6)

    except Exception as e:
        logger.warning("Monte Carlo VaR failed (GPU=%s): %s", GPU_VAR, e)
        # Fallback: simple parametric VaR
        try:
            port_std = float(np.sqrt(weights @ np.cov(returns_matrix.T) @ weights))
            port_mean = float(np.mean(returns_matrix @ weights))
            from scipy import stats
            result = {
                "var_95": round(port_mean - 1.645 * port_std, 6),
                "cvar_95": round(port_mean - 2.063 * port_std, 6),
                "var_99": round(port_mean - 2.326 * port_std, 6),
                "cvar_99": round(port_mean - 2.665 * port_std, 6),
                "n_paths": 0,
                "gpu_used": False,
                "fallback": "parametric",
            }
        except Exception:
            result = {"var_95": 0.0, "cvar_95": 0.0, "error": str(e), "gpu_used": False}

    latency_ms = round((time.monotonic() - t0) * 1000, 1)
    result["latency_ms"] = latency_ms
    logger.info("Monte Carlo VaR: %d paths, GPU=%s, %.1fms", n_paths, GPU_VAR, latency_ms)
    return result


def compute_single_position_var(
    returns: np.ndarray,
    n_paths: int = 10_000,
) -> Dict[str, float]:
    """Simplified VaR for a single position (no correlation needed).

    Args:
        returns: 1D array of historical daily returns
        n_paths: simulation paths

    Returns:
        Dict with var_95, cvar_95, var_99
    """
    xp = cp if GPU_VAR else np
    r = xp.asarray(returns)
    mu = float(xp.mean(r))
    sigma = float(xp.std(r))
    sim = mu + sigma * xp.random.standard_normal(n_paths)
    sorted_sim = xp.sort(sim)
    idx_95 = int(0.05 * n_paths)
    idx_99 = int(0.01 * n_paths)
    return {
        "var_95": round(float(sorted_sim[idx_95]), 6),
        "cvar_95": round(float(xp.mean(sorted_sim[:idx_95])), 6) if idx_95 > 0 else 0.0,
        "var_99": round(float(sorted_sim[idx_99]), 6),
        "gpu_used": GPU_VAR,
    }
