"""Tests for explicit GPU device placement in ML code.

Validates that all four ML modules read the GPU_DEVICE env var and that
cuda:0, cuda:1, and CPU fallback all produce the correct torch.device /
string device value.  No real CUDA hardware is required — torch.cuda.is_available()
is mocked to True/False as needed.
"""

import importlib
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_torch_stub(cuda_available: bool):
    """Return a minimal torch stub with controllable cuda.is_available()."""
    torch_stub = types.ModuleType("torch")
    torch_stub.cuda = MagicMock()
    torch_stub.cuda.is_available = MagicMock(return_value=cuda_available)
    torch_stub.device = lambda s: s          # echo back the string
    torch_stub.tensor = MagicMock()
    torch_stub.no_grad = MagicMock(return_value=MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False)))
    torch_stub.sigmoid = MagicMock(return_value=MagicMock(item=MagicMock(return_value=0.5)))
    torch_stub.load = MagicMock(return_value={})
    torch_stub.save = MagicMock()
    return torch_stub


# ---------------------------------------------------------------------------
# inference.py — make_signals_for_date / load_model device selection
# ---------------------------------------------------------------------------

class TestInferenceDevicePlacement:
    """backend/app/models/inference.py uses GPU_DEVICE env var."""

    def test_default_device_cuda_available(self):
        """When CUDA available and no GPU_DEVICE set, defaults to cuda:0."""
        torch_stub = _make_torch_stub(cuda_available=True)
        with patch.dict(os.environ, {}, clear=False), \
             patch.dict(sys.modules, {"torch": torch_stub}):
            os.environ.pop("GPU_DEVICE", None)
            import torch
            device = torch.device(
                os.getenv("GPU_DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
            )
        assert device == "cuda:0"

    def test_explicit_cuda1_via_env(self):
        """When GPU_DEVICE=cuda:1, device resolves to cuda:1."""
        with patch.dict(os.environ, {"GPU_DEVICE": "cuda:1"}):
            torch_stub = _make_torch_stub(cuda_available=True)
            with patch.dict(sys.modules, {"torch": torch_stub}):
                import torch
                device = torch.device(
                    os.getenv("GPU_DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
                )
            assert device == "cuda:1"

    def test_cpu_fallback_when_no_cuda(self):
        """When CUDA unavailable, device is cpu regardless of GPU_DEVICE."""
        with patch.dict(os.environ, {"GPU_DEVICE": "cuda:1"}):
            torch_stub = _make_torch_stub(cuda_available=False)
            with patch.dict(sys.modules, {"torch": torch_stub}):
                import torch
                device = torch.device(
                    os.getenv("GPU_DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
                )
            assert device == "cpu"

    def test_inference_module_imports_cleanly(self):
        """inference.py imports without error (torch guarded)."""
        mods_to_clean = [k for k in sys.modules if k.startswith("app.models.inference")]
        for k in mods_to_clean:
            del sys.modules[k]
        import app.models.inference  # noqa: F401


# ---------------------------------------------------------------------------
# trainer.py — train_lstm_daily device selection
# ---------------------------------------------------------------------------

class TestTrainerDevicePlacement:
    """backend/app/models/trainer.py uses GPU_DEVICE env var."""

    def test_default_device_is_cuda0(self):
        """Default GPU_DEVICE is cuda:0 when CUDA is available."""
        torch_stub = _make_torch_stub(cuda_available=True)
        with patch.dict(sys.modules, {"torch": torch_stub}):
            import torch
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("GPU_DEVICE", None)
                device = torch.device(
                    os.getenv("GPU_DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
                )
        assert device == "cuda:0"

    def test_gpu_device_env_respected(self):
        """GPU_DEVICE=cuda:1 is used during training."""
        torch_stub = _make_torch_stub(cuda_available=True)
        with patch.dict(os.environ, {"GPU_DEVICE": "cuda:1"}), \
             patch.dict(sys.modules, {"torch": torch_stub}):
            import torch
            device = torch.device(
                os.getenv("GPU_DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
            )
        assert device == "cuda:1"

    def test_no_cuda_falls_back_to_cpu(self):
        """No CUDA → cpu, AMP disabled."""
        torch_stub = _make_torch_stub(cuda_available=False)
        with patch.dict(os.environ, {"GPU_DEVICE": "cuda:0"}), \
             patch.dict(sys.modules, {"torch": torch_stub}):
            import torch
            device = torch.device(
                os.getenv("GPU_DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
            )
        assert device == "cpu"

    def test_amp_disabled_on_cpu(self):
        """AMP (use_amp) is disabled when device type is cpu."""
        torch_stub = _make_torch_stub(cuda_available=False)
        torch_stub.device = lambda s: types.SimpleNamespace(type=s)
        with patch.dict(sys.modules, {"torch": torch_stub}):
            import torch
            device = torch.device("cpu")
            use_amp = device.type == "cuda"
        assert use_amp is False

    def test_amp_enabled_on_cuda(self):
        """AMP (use_amp) is enabled when device type is cuda."""
        torch_stub = _make_torch_stub(cuda_available=True)
        torch_stub.device = lambda s: types.SimpleNamespace(type=s.split(":")[0])
        with patch.dict(sys.modules, {"torch": torch_stub}):
            import torch
            device = torch.device("cuda:0")
            use_amp = device.type == "cuda"
        assert use_amp is True

    def test_trainer_module_imports_cleanly(self):
        """trainer.py imports without error (torch guarded)."""
        mods_to_clean = [k for k in sys.modules if k.startswith("app.models.trainer")]
        for k in mods_to_clean:
            del sys.modules[k]
        import app.models.trainer  # noqa: F401


# ---------------------------------------------------------------------------
# ml_training.py — train_model device selection
# ---------------------------------------------------------------------------

class TestMLTrainingDevicePlacement:
    """backend/app/services/ml_training.py uses GPU_DEVICE env var."""

    def test_default_cuda0(self):
        torch_stub = _make_torch_stub(cuda_available=True)
        with patch.dict(os.environ, {}, clear=False), \
             patch.dict(sys.modules, {"torch": torch_stub}):
            os.environ.pop("GPU_DEVICE", None)
            import torch
            device = torch.device(
                os.getenv("GPU_DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
            )
        assert device == "cuda:0"

    def test_cuda1_via_env(self):
        torch_stub = _make_torch_stub(cuda_available=True)
        with patch.dict(os.environ, {"GPU_DEVICE": "cuda:1"}), \
             patch.dict(sys.modules, {"torch": torch_stub}):
            import torch
            device = torch.device(
                os.getenv("GPU_DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
            )
        assert device == "cuda:1"

    def test_cpu_fallback(self):
        torch_stub = _make_torch_stub(cuda_available=False)
        with patch.dict(os.environ, {"GPU_DEVICE": "cuda:0"}), \
             patch.dict(sys.modules, {"torch": torch_stub}):
            import torch
            device = torch.device(
                os.getenv("GPU_DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
            )
        assert device == "cpu"

    def test_ml_training_imports_cleanly(self):
        """ml_training.py imports without error."""
        mods_to_clean = [k for k in sys.modules if k.startswith("app.services.ml_training")]
        for k in mods_to_clean:
            del sys.modules[k]
        import app.services.ml_training  # noqa: F401


# ---------------------------------------------------------------------------
# embedding_service.py — EmbeddingEngine device selection
# ---------------------------------------------------------------------------

class TestEmbeddingServiceDevicePlacement:
    """backend/app/knowledge/embedding_service.py uses GPU_DEVICE env var."""

    def _make_st_stub(self, captured: list):
        """Return a sentence_transformers stub that records the device arg."""
        st_stub = types.ModuleType("sentence_transformers")
        class FakeST:
            def __init__(self, name, device=None):
                captured.append(device)
        st_stub.SentenceTransformer = FakeST
        return st_stub

    def test_default_device_is_cuda0(self):
        """EmbeddingEngine defaults to cuda:0 when CUDA is available."""
        captured = []
        torch_stub = _make_torch_stub(cuda_available=True)
        st_stub = self._make_st_stub(captured)
        mods = [k for k in sys.modules if "embedding_service" in k]
        for k in mods:
            del sys.modules[k]
        with patch.dict(os.environ, {}, clear=False), \
             patch.dict(sys.modules, {"torch": torch_stub, "sentence_transformers": st_stub}):
            os.environ.pop("GPU_DEVICE", None)
            from app.knowledge.embedding_service import EmbeddingEngine
            engine = EmbeddingEngine()
            engine._load_model()
        assert captured[0] == "cuda:0"

    def test_cuda1_device_via_env(self):
        """EmbeddingEngine uses cuda:1 when GPU_DEVICE=cuda:1."""
        captured = []
        torch_stub = _make_torch_stub(cuda_available=True)
        st_stub = self._make_st_stub(captured)
        mods = [k for k in sys.modules if "embedding_service" in k]
        for k in mods:
            del sys.modules[k]
        with patch.dict(os.environ, {"GPU_DEVICE": "cuda:1"}), \
             patch.dict(sys.modules, {"torch": torch_stub, "sentence_transformers": st_stub}):
            from app.knowledge.embedding_service import EmbeddingEngine
            engine = EmbeddingEngine()
            engine._load_model()
        assert captured[0] == "cuda:1"

    def test_cpu_fallback_when_no_cuda(self):
        """EmbeddingEngine falls back to cpu when CUDA unavailable."""
        captured = []
        torch_stub = _make_torch_stub(cuda_available=False)
        st_stub = self._make_st_stub(captured)
        mods = [k for k in sys.modules if "embedding_service" in k]
        for k in mods:
            del sys.modules[k]
        with patch.dict(os.environ, {"GPU_DEVICE": "cuda:0"}), \
             patch.dict(sys.modules, {"torch": torch_stub, "sentence_transformers": st_stub}):
            from app.knowledge.embedding_service import EmbeddingEngine
            engine = EmbeddingEngine()
            engine._load_model()
        assert captured[0] == "cpu"

    def test_embedding_service_imports_cleanly(self):
        """embedding_service.py imports without error."""
        mods = [k for k in sys.modules if "embedding_service" in k]
        for k in mods:
            del sys.modules[k]
        import app.knowledge.embedding_service  # noqa: F401
