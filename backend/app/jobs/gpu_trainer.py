"""GPU-accelerated XGBoost training for ProfitTrader (PC2).

Only runs overnight — never during market hours (09:30-16:00 ET).
Protects VRAM budget for gemma3:12b live inference.

VRAM Budget:
  gemma3:12b:     ~8.5 GB (market hours, always pre-warmed)
  qwen3:8b:       ~5.0 GB (on-demand)
  XGBoost buffer: ~2.0 GB (overnight ONLY)
  CUDA runtime:   ~1.0 GB
  Headroom:       ~0.7 GB
  Total:          17.2 GB
"""
import logging
import os
import time
from datetime import datetime, time as dt_time

logger = logging.getLogger(__name__)


def is_market_hours() -> bool:
    """Return True if US equity market is open (09:30-16:00 ET, weekdays).

    Used to block GPU training that would starve VRAM for gemma3:12b.
    """
    try:
        import pytz
        now = datetime.now(pytz.timezone("America/New_York"))
    except ImportError:
        from datetime import timezone, timedelta
        et_offset = timezone(timedelta(hours=-5))  # EST approximation
        now = datetime.now(et_offset)
    if now.weekday() >= 5:
        return False
    t = now.time()
    return dt_time(9, 30) <= t <= dt_time(16, 0)


def get_vram_free_gb() -> float:
    """Get free VRAM in GB via PyTorch. Returns 0.0 if CUDA unavailable."""
    try:
        import torch
        if not torch.cuda.is_available():
            return 0.0
        free_bytes, _total = torch.cuda.mem_get_info(0)
        return free_bytes / 1e9
    except Exception:
        try:
            import torch
            if not torch.cuda.is_available():
                return 0.0
            total = torch.cuda.get_device_properties(0).total_memory
            allocated = torch.cuda.memory_allocated(0)
            return (total - allocated) / 1e9
        except Exception:
            return 0.0


def get_xgb_params(base_params: dict) -> dict:
    """Return XGBoost params with CUDA if safe.

    Conditions for CUDA:
      - Market is closed (protect VRAM for gemma3:12b)
      - CUDA is available
      - At least 2.5GB VRAM free (2.0GB buffer + 0.5GB margin)

    Falls back to CPU otherwise.
    """
    if is_market_hours():
        logger.info(
            "[gpu_trainer] Market hours — XGBoost using CPU to protect VRAM for gemma3:12b"
        )
        return {**base_params, "device": "cpu", "tree_method": "hist"}

    try:
        import torch
        if not torch.cuda.is_available():
            logger.info("[gpu_trainer] CUDA unavailable — using CPU")
            return {**base_params, "device": "cpu", "tree_method": "hist"}
    except ImportError:
        logger.info("[gpu_trainer] PyTorch not installed — using CPU")
        return {**base_params, "device": "cpu", "tree_method": "hist"}

    vram_free = get_vram_free_gb()
    if vram_free < 2.5:
        logger.warning(
            "[gpu_trainer] VRAM too low (%.1fGB free) — using CPU", vram_free
        )
        return {**base_params, "device": "cpu", "tree_method": "hist"}

    logger.info(
        "[gpu_trainer] CUDA enabled — %.1fGB VRAM free, RTX 4080 Ada sm_89",
        vram_free,
    )
    return {
        **base_params,
        "device": "cuda",
        "tree_method": "hist",
        "max_bin": 256,  # optimal for Ada Lovelace histogram engine
        "sampling_method": "gradient_based",
    }


def train_with_timing(model_class, params: dict, X_train, y_train):
    """Train XGBoost and log GPU vs CPU path + duration."""
    xgb_params = get_xgb_params(params)
    device = xgb_params.get("device", "cpu")

    t0 = time.perf_counter()
    model = model_class(**xgb_params)
    model.fit(X_train, y_train)
    elapsed = time.perf_counter() - t0

    logger.info(
        "[gpu_trainer] Trained %d rows on %s in %.1fs",
        len(X_train), device, elapsed,
    )
    return model
