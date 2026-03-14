"""GPU Configuration -- VRAM budgeting and Ollama model strategy for PC2.

Manages GPU resources across Ollama, PyTorch, and XGBoost to prevent
OOM errors on the RTX 4080 (16GB VRAM).

Model Strategy for RTX 4080:
  Primary:   gemma3:12b (8.1GB) -- hypothesis_agent, deep reasoning, trade thesis
  Secondary: qwen3:8b (5.2GB)   -- critic_agent, fast tasks, postmortems
  Embed:     nomic-embed-text (274MB) -- knowledge system embeddings

  These two models cannot be loaded simultaneously (13.3GB > safe limit).
  Ollama handles model swapping automatically, but we optimize by:
  1. Routing tasks to minimize swaps (batch similar tasks)
  2. Setting OLLAMA_KEEP_ALIVE to cache the primary model
  3. Pre-loading the primary model at startup

Fallback chain:
  GPU model -> smaller GPU model -> CPU-only deterministic logic
  (LLM is a tool, not the orchestrator -- council DAG stays deterministic)

Usage:
    from app.core.gpu_config import get_gpu_config
    config = get_gpu_config()
    model = config.model_for_task("hypothesis")
"""
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

log = logging.getLogger(__name__)


@dataclass
class OllamaModelConfig:
    """Configuration for a single Ollama model."""
    name: str
    vram_mb: int
    max_context: int = 4096
    temperature: float = 0.3
    keep_alive: str = "5m"       # How long to keep model loaded after use
    tasks: list = field(default_factory=list)  # Which tasks use this model


@dataclass
class GPUConfig:
    """GPU resource configuration for PC2."""

    # Available VRAM (auto-detected or override)
    vram_total_mb: int = 16384

    # Model assignments
    primary_model: OllamaModelConfig = field(default_factory=lambda: OllamaModelConfig(
        name="gemma3:12b",
        vram_mb=8100,
        max_context=8192,
        temperature=0.3,
        keep_alive="10m",  # Keep loaded longer -- it's the main model
        tasks=["hypothesis", "trade_thesis", "strategy_evolution",
               "deep_postmortem", "overnight_analysis"],
    ))

    secondary_model: OllamaModelConfig = field(default_factory=lambda: OllamaModelConfig(
        name="qwen3:8b",
        vram_mb=5200,
        max_context=4096,
        temperature=0.2,
        keep_alive="3m",
        tasks=["critic", "strategy_critic", "quick_hypothesis",
               "feature_summary", "risk_check"],
    ))

    embed_model: OllamaModelConfig = field(default_factory=lambda: OllamaModelConfig(
        name="nomic-embed-text",
        vram_mb=274,
        max_context=8192,
        keep_alive="30m",  # Embeddings are used frequently
        tasks=["embed"],
    ))

    # PyTorch CUDA allocation
    pytorch_max_mb: int = 1024       # Max VRAM for feature tensors
    xgboost_max_mb: int = 512        # Max VRAM for XGBoost histograms

    # Safety
    vram_headroom_mb: int = 1000     # Never allocate more than total - headroom
    cuda_runtime_mb: int = 500       # CUDA context overhead

    # Ollama server config
    ollama_host: str = "localhost"
    ollama_port: int = 11434
    ollama_num_gpu: int = 99         # Use all GPU layers (don't offload to CPU)
    ollama_num_parallel: int = 1     # Sequential inference (VRAM-safe)

    def model_for_task(self, task: str) -> str:
        """Get the appropriate model name for a task type.

        Falls back to secondary model for unknown tasks.
        """
        if task in self.primary_model.tasks:
            return self.primary_model.name
        if task in self.secondary_model.tasks:
            return self.secondary_model.name
        if task in self.embed_model.tasks:
            return self.embed_model.name
        # Default to secondary (faster, less VRAM)
        return self.secondary_model.name

    def max_concurrent_models(self) -> int:
        """How many models can be loaded simultaneously?"""
        usable = self.vram_total_mb - self.cuda_runtime_mb - self.vram_headroom_mb
        # Can primary + embed fit together?
        if self.primary_model.vram_mb + self.embed_model.vram_mb <= usable:
            return 2
        return 1

    def ollama_env(self) -> Dict[str, str]:
        """Environment variables to set for Ollama server on PC2."""
        return {
            "OLLAMA_HOST": f"{self.ollama_host}:{self.ollama_port}",
            "OLLAMA_NUM_PARALLEL": str(self.ollama_num_parallel),
            "OLLAMA_KEEP_ALIVE": self.primary_model.keep_alive,
            "OLLAMA_MAX_LOADED_MODELS": str(self.max_concurrent_models()),
            "CUDA_VISIBLE_DEVICES": "0",
        }

    def to_dict(self) -> dict:
        return {
            "vram_total_mb": self.vram_total_mb,
            "primary_model": self.primary_model.name,
            "primary_vram_mb": self.primary_model.vram_mb,
            "secondary_model": self.secondary_model.name,
            "secondary_vram_mb": self.secondary_model.vram_mb,
            "embed_model": self.embed_model.name,
            "pytorch_max_mb": self.pytorch_max_mb,
            "xgboost_max_mb": self.xgboost_max_mb,
            "max_concurrent_models": self.max_concurrent_models(),
        }


# ── Singleton ────────────────────────────────────────────────────

_config: Optional[GPUConfig] = None


def get_gpu_config() -> GPUConfig:
    """Get or create GPU config (singleton)."""
    global _config
    if _config is not None:
        return _config

    config = GPUConfig()

    # Override from env
    primary = os.getenv("OLLAMA_PRIMARY_MODEL")
    secondary = os.getenv("OLLAMA_SECONDARY_MODEL")
    if primary:
        config.primary_model.name = primary
    if secondary:
        config.secondary_model.name = secondary

    # Auto-detect VRAM
    try:
        from app.core.hardware_profile import get_hardware_profile
        profile = get_hardware_profile()
        if profile.gpu.available:
            config.vram_total_mb = profile.gpu.vram_total_mb
            config.primary_model = profile.vram_budget.primary_model and OllamaModelConfig(
                name=profile.vram_budget.primary_model,
                vram_mb=profile.vram_budget.ollama_primary_mb,
                tasks=config.primary_model.tasks,
                keep_alive=config.primary_model.keep_alive,
            ) or config.primary_model
            if profile.vram_budget.secondary_model:
                config.secondary_model = OllamaModelConfig(
                    name=profile.vram_budget.secondary_model,
                    vram_mb=profile.vram_budget.ollama_secondary_mb,
                    tasks=config.secondary_model.tasks,
                    keep_alive=config.secondary_model.keep_alive,
                )
    except Exception:
        pass

    _config = config
    log.info("GPU config: primary=%s (%dMB), secondary=%s (%dMB), VRAM=%dMB",
             config.primary_model.name, config.primary_model.vram_mb,
             config.secondary_model.name, config.secondary_model.vram_mb,
             config.vram_total_mb)
    return config
