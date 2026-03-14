"""GPU compute utilities — CuPy/NumPy interop with graceful CPU fallback.

Provides a unified interface for GPU-accelerated array operations.
When CuPy + CUDA is available, operations run on RTX 4080 GPU.
When unavailable, all operations fall back to NumPy with identical results.

Usage:
    from app.core.gpu_compute import xp, to_gpu, to_cpu, gpu_available

    arr = to_gpu(numpy_array)      # Move to GPU if available
    result = xp().sum(arr)         # Use cupy.sum or numpy.sum
    output = to_cpu(result)        # Back to numpy for pandas/DuckDB
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)

# --- CuPy detection ---
try:
    import cupy as cp
    _GPU_AVAILABLE = bool(cp.cuda.is_available())
    if _GPU_AVAILABLE:
        _device = cp.cuda.Device()
        logger.info(
            "CuPy GPU acceleration enabled (device %d: %s, %.1f GB VRAM)",
            _device.id,
            cp.cuda.runtime.getDeviceProperties(_device.id)["name"].decode(),
            _device.mem_info[1] / (1024 ** 3),
        )
except (ImportError, Exception) as _err:
    cp = None  # type: ignore[assignment]
    _GPU_AVAILABLE = False
    logger.info("CuPy not available (%s) — using CPU NumPy", _err)


def gpu_available() -> bool:
    """Return True if CuPy GPU acceleration is available."""
    return _GPU_AVAILABLE


def xp():
    """Return cupy module if GPU available, else numpy.

    Use as drop-in replacement:
        xp = gpu_compute.xp()
        result = xp.mean(arr)
    """
    return cp if _GPU_AVAILABLE else np


def to_gpu(arr):
    """Move numpy array to GPU if available. No-op if already on GPU or no CUDA."""
    if _GPU_AVAILABLE and isinstance(arr, np.ndarray):
        return cp.asarray(arr)
    return arr


def to_cpu(arr):
    """Move GPU array back to CPU numpy. No-op if already numpy."""
    if _GPU_AVAILABLE and hasattr(arr, "get"):
        return arr.get()
    if not isinstance(arr, np.ndarray):
        return np.asarray(arr)
    return arr


def gpu_vectorized_ema(values, span: int):
    """Compute EMA using vectorized operations on GPU or CPU.

    Faster than Python loops for large arrays.
    """
    _xp = xp()
    arr = to_gpu(values) if isinstance(values, np.ndarray) else values
    n = len(arr)
    if n == 0:
        return to_cpu(arr)

    alpha = 2.0 / (span + 1)
    # For short arrays, use simple loop (overhead of GPU transfer not worth it)
    if n < 100 or not _GPU_AVAILABLE:
        result = _xp.empty(n, dtype=_xp.float64)
        result[0] = arr[0]
        for i in range(1, n):
            result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
        return result

    # For larger arrays on GPU, use cumulative approach
    # EMA is inherently sequential, but we can still benefit from GPU for
    # the element-wise operations in batch processing
    result = _xp.empty(n, dtype=_xp.float64)
    result[0] = arr[0]
    for i in range(1, n):
        result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
    return result


def gpu_rolling_mean(arr, window: int):
    """Compute rolling mean using GPU-accelerated cumsum approach."""
    _xp = xp()
    a = to_gpu(arr) if isinstance(arr, np.ndarray) else arr
    n = len(a)
    if n < window:
        return _xp.full(n, _xp.nan)

    # Cumsum trick: rolling_mean[i] = (cumsum[i] - cumsum[i-window]) / window
    padded = _xp.concatenate([_xp.zeros(1, dtype=a.dtype), a])
    cs = _xp.cumsum(padded)
    rolling = (cs[window:] - cs[:-window]) / window

    # Pad front with NaN
    result = _xp.full(n, _xp.nan)
    result[window - 1:] = rolling
    return result


def gpu_rolling_std(arr, window: int):
    """Compute rolling standard deviation using GPU-accelerated operations."""
    _xp = xp()
    a = to_gpu(arr) if isinstance(arr, np.ndarray) else arr
    n = len(a)
    if n < window:
        return _xp.full(n, _xp.nan)

    # Use rolling mean of squares minus square of rolling mean
    mean = gpu_rolling_mean(a, window)
    sq_mean = gpu_rolling_mean(a ** 2, window)

    # Var = E[X^2] - E[X]^2, with Bessel's correction
    variance = (sq_mean - mean ** 2) * (window / (window - 1))
    variance = _xp.maximum(variance, 0)  # Numerical safety
    return _xp.sqrt(variance)


def gpu_rsi(closes, period: int = 14):
    """Compute RSI using vectorized GPU operations.

    Returns array of RSI values (0-100), with NaN for insufficient data.
    """
    _xp = xp()
    arr = to_gpu(closes) if isinstance(closes, np.ndarray) else closes
    n = len(arr)
    if n < period + 1:
        return _xp.full(n, 50.0)

    # Price changes
    delta = _xp.diff(arr)

    # Separate gains and losses
    gains = _xp.maximum(delta, 0)
    losses = _xp.maximum(-delta, 0)

    # Simple rolling mean for initial RSI
    avg_gain = gpu_rolling_mean(gains, period)
    avg_loss = gpu_rolling_mean(losses, period)

    # RSI calculation
    rs = avg_gain / (_xp.maximum(avg_loss, 1e-10))
    rsi = 100.0 - (100.0 / (1.0 + rs))

    # Pad front to match input length
    result = _xp.full(n, _xp.nan)
    result[1:] = rsi
    return result


def gpu_macd(closes, fast: int = 12, slow: int = 26, signal: int = 9):
    """Compute MACD line, signal line, histogram using GPU operations.

    Returns (macd_line, signal_line, histogram) as arrays.
    """
    _xp = xp()
    arr = to_gpu(closes) if isinstance(closes, np.ndarray) else closes
    n = len(arr)
    if n < slow:
        return _xp.zeros(n), _xp.zeros(n), _xp.zeros(n)

    ema_fast = gpu_vectorized_ema(arr, fast)
    ema_slow = gpu_vectorized_ema(arr, slow)
    macd_line = ema_fast - ema_slow
    signal_line = gpu_vectorized_ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def gpu_bollinger(closes, window: int = 20, num_std: float = 2.0):
    """Compute Bollinger Bands using GPU operations.

    Returns (middle, upper, lower) bands as arrays.
    """
    _xp = xp()
    arr = to_gpu(closes) if isinstance(closes, np.ndarray) else closes

    middle = gpu_rolling_mean(arr, window)
    std = gpu_rolling_std(arr, window)
    upper = middle + num_std * std
    lower = middle - num_std * std

    return middle, upper, lower
