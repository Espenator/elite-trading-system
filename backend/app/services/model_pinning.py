"""Model Pinning Registry — Asymmetric model-to-node mapping.

Maps models and tasks to specific nodes (PC1 vs PC2) to prevent Ollama
from constantly loading/unloading models from VRAM.

PC1 (Master / Rapid Responder):
    - Fast tactical models (Llama-3 8B, Mistral 7B)
    - High-frequency DAG stages: Market Perception, Risk, Sentiment, Execution

PC2 (Heavy Compute Node):
    - Deep thinking models (DeepSeek-R1 14B, Mixtral 8x7B)
    - Heavy DAG stages: Hypothesis Generation, Critic, Strategy

By isolating models to specific GPUs, Ollama keeps them persistently
loaded in memory — zero cold-start latency.

Part of #39 — E1.2
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NodeRole(str, Enum):
    """Node role in the cluster."""
    PC1 = "pc1"  # Master / Rapid Responder
    PC2 = "pc2"  # Heavy Compute


@dataclass
class ModelPin:
    """A model pinned to a specific node."""
    model: str
    node: NodeRole
    priority: int = 0  # Higher = preferred when multiple nodes have the model


@dataclass
class TaskAffinity:
    """A task's preferred node for inference."""
    task: str
    node: NodeRole


class ModelPinningRegistry:
    """Registry of model-to-node and task-to-node affinities.

    Loaded from config (MODEL_PIN_PC1, MODEL_PIN_PC2, MODEL_PIN_TASK_AFFINITY).
    The LLM Dispatcher queries this registry to determine where to route
    inference requests.
    """

    def __init__(self):
        self._model_pins: Dict[str, ModelPin] = {}
        self._task_affinities: Dict[str, TaskAffinity] = {}
        self._node_urls: Dict[NodeRole, str] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load pinning config from settings."""
        try:
            from app.core.config import settings
            pc1_models = settings.MODEL_PIN_PC1
            pc2_models = settings.MODEL_PIN_PC2
            task_affinity = settings.MODEL_PIN_TASK_AFFINITY
            pc2_host = settings.CLUSTER_PC2_HOST
            ollama_url = settings.OLLAMA_BASE_URL.rstrip("/")
        except Exception:
            import os
            pc1_models = os.getenv("MODEL_PIN_PC1", "llama3.2,mistral:7b")
            pc2_models = os.getenv("MODEL_PIN_PC2", "deepseek-r1:14b,mixtral:8x7b")
            task_affinity = os.getenv("MODEL_PIN_TASK_AFFINITY", "")
            pc2_host = os.getenv("CLUSTER_PC2_HOST", "")
            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

        # Set node URLs
        self._node_urls[NodeRole.PC1] = ollama_url
        if pc2_host:
            self._node_urls[NodeRole.PC2] = f"http://{pc2_host}:11434"

        # Parse model pins
        for model_name in self._parse_csv(pc1_models):
            self._model_pins[model_name] = ModelPin(
                model=model_name, node=NodeRole.PC1, priority=10,
            )
        for model_name in self._parse_csv(pc2_models):
            self._model_pins[model_name] = ModelPin(
                model=model_name, node=NodeRole.PC2, priority=10,
            )

        # Parse task affinities: "task1:pc1,task2:pc2"
        for pair in self._parse_csv(task_affinity):
            parts = pair.split(":")
            if len(parts) == 2:
                task_name, node_name = parts[0].strip(), parts[1].strip()
                try:
                    node = NodeRole(node_name)
                    self._task_affinities[task_name] = TaskAffinity(
                        task=task_name, node=node,
                    )
                except ValueError:
                    logger.warning(
                        "ModelPinning: invalid node '%s' for task '%s'",
                        node_name, task_name,
                    )

        logger.info(
            "ModelPinningRegistry: %d model pins, %d task affinities, nodes=%s",
            len(self._model_pins),
            len(self._task_affinities),
            {k.value: v for k, v in self._node_urls.items()},
        )

    @staticmethod
    def _parse_csv(value: str) -> List[str]:
        """Parse comma-separated string into list of stripped non-empty values."""
        if not value:
            return []
        return [v.strip() for v in value.split(",") if v.strip()]

    # -- Query methods ---------------------------------------------------------

    def get_node_for_model(self, model: str) -> Optional[NodeRole]:
        """Get the preferred node for a specific model.

        Returns None if no pinning exists (use round-robin fallback).
        """
        pin = self._model_pins.get(model)
        if pin:
            return pin.node

        # Try partial match (e.g., "llama3.2" matches "llama3.2:latest")
        for pinned_model, pin in self._model_pins.items():
            if model.startswith(pinned_model) or pinned_model.startswith(model):
                return pin.node

        return None

    def get_node_for_task(self, task: str) -> Optional[NodeRole]:
        """Get the preferred node for a specific task.

        Returns None if no affinity exists (use default routing).
        """
        affinity = self._task_affinities.get(task)
        return affinity.node if affinity else None

    def get_node_url(self, node: NodeRole) -> Optional[str]:
        """Get the Ollama URL for a specific node role."""
        return self._node_urls.get(node)

    def get_all_node_urls(self) -> Dict[NodeRole, str]:
        """Get all configured node URLs."""
        return dict(self._node_urls)

    def get_models_for_node(self, node: NodeRole) -> List[str]:
        """Get all models pinned to a specific node."""
        return [
            pin.model for pin in self._model_pins.values()
            if pin.node == node
        ]

    def get_preferred_model(self, task: str) -> Optional[str]:
        """Get the preferred model for a task based on node affinity.

        If a task is pinned to PC2, return the first PC2-pinned model.
        This is used for model degradation (e.g., falling back to PC1 model).
        """
        node = self.get_node_for_task(task)
        if node is None:
            return None
        models = self.get_models_for_node(node)
        return models[0] if models else None

    def get_fallback_model(self) -> str:
        """Get the fallback model when PC2 is unavailable."""
        try:
            from app.core.config import settings
            return settings.LLM_DISPATCHER_FALLBACK_MODEL
        except Exception:
            import os
            return os.getenv("LLM_DISPATCHER_FALLBACK_MODEL", "llama3.2")

    def update_node_url(self, node: NodeRole, url: str) -> None:
        """Dynamically update a node's URL (e.g., after discovery)."""
        old_url = self._node_urls.get(node)
        self._node_urls[node] = url.rstrip("/")
        if old_url != url:
            logger.info(
                "ModelPinning: updated %s URL: %s → %s",
                node.value, old_url, url,
            )

    def is_cluster_mode(self) -> bool:
        """True if PC2 is configured."""
        return NodeRole.PC2 in self._node_urls

    def get_status(self) -> Dict[str, Any]:
        """Return registry status for monitoring."""
        return {
            "cluster_mode": self.is_cluster_mode(),
            "nodes": {
                node.value: {
                    "url": url,
                    "pinned_models": self.get_models_for_node(node),
                }
                for node, url in self._node_urls.items()
            },
            "task_affinities": {
                task: aff.node.value
                for task, aff in self._task_affinities.items()
            },
            "model_pins": {
                model: pin.node.value
                for model, pin in self._model_pins.items()
            },
        }


# ── Module-level singleton ────────────────────────────────────────────────
_registry: Optional[ModelPinningRegistry] = None


def get_model_pinning() -> ModelPinningRegistry:
    """Get or create the singleton ModelPinningRegistry."""
    global _registry
    if _registry is None:
        _registry = ModelPinningRegistry()
    return _registry
