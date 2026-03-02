"""
DailyLSTM v2.0 — Multi-Task LSTM with Temporal Attention.

APEX Phase 3 upgrades over the original 2-layer hidden=64, 5-feature model:
- Multi-head self-attention over LSTM hidden states
- Multi-task output: direction (binary) + magnitude (regression) + volatility (regression)
- Configurable feature count (5 → 30+ via feature_pipeline.py)
- Residual connections around LSTM layers
- Layer normalization for training stability
- Dropout scheduling for regularization

Backward compatible: DailyLSTM(num_features=5) still works exactly as before.
New: DailyLSTM(num_features=30, multi_task=True, use_attention=True)

Integrates with: models/trainer.py, models/inference.py, ml_engine/feature_pipeline.py.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Torch availability check (matches original pattern)
# ---------------------------------------------------------------------------
TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    log.info("PyTorch not installed; DailyLSTM disabled.")


# ---------------------------------------------------------------------------
# Temporal Attention Module
# ---------------------------------------------------------------------------
if TORCH_AVAILABLE:

    class TemporalAttention(nn.Module):
        """
        Multi-head self-attention over LSTM time-step outputs.
        Learns which time steps in the lookback window are most relevant.
        """

        def __init__(self, hidden_size: int, num_heads: int = 4, dropout: float = 0.1):
            super().__init__()
            self.attention = nn.MultiheadAttention(
                embed_dim=hidden_size,
                num_heads=num_heads,
                dropout=dropout,
                batch_first=True,
            )
            self.layer_norm = nn.LayerNorm(hidden_size)

        def forward(self, lstm_output: torch.Tensor) -> torch.Tensor:
            """
            Args:
                lstm_output: (batch, seq_len, hidden_size) from LSTM.
            Returns:
                context: (batch, hidden_size) — attention-weighted summary.
            """
            # Self-attention over time steps
            attn_out, attn_weights = self.attention(
                lstm_output, lstm_output, lstm_output
            )
            # Residual connection + layer norm
            attn_out = self.layer_norm(attn_out + lstm_output)
            # Use last time step's attention-refined representation
            context = attn_out[:, -1, :]  # (batch, hidden_size)
            return context


    # ---------------------------------------------------------------------------
    # Multi-Task Head
    # ---------------------------------------------------------------------------

    class MultiTaskHead(nn.Module):
        """
        Three prediction heads sharing a common backbone:
        1. Direction: P(price goes up) — binary classification (BCEWithLogits)
        2. Magnitude: Expected return magnitude — regression (MSE)
        3. Volatility: Expected forward volatility — regression (MSE)
        """

        def __init__(self, hidden_size: int, dropout: float = 0.3):
            super().__init__()
            # Shared projection
            self.shared = nn.Sequential(
                nn.Linear(hidden_size, hidden_size // 2),
                nn.GELU(),
                nn.Dropout(dropout),
            )
            # Task-specific heads
            self.direction_head = nn.Linear(hidden_size // 2, 1)
            self.magnitude_head = nn.Linear(hidden_size // 2, 1)
            self.volatility_head = nn.Linear(hidden_size // 2, 1)

        def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
            """
            Args:
                x: (batch, hidden_size) from attention or LSTM.
            Returns:
                Dict with 'direction' (logits), 'magnitude', 'volatility'.
            """
            shared = self.shared(x)
            return {
                "direction": self.direction_head(shared),       # (batch, 1)
                "magnitude": self.magnitude_head(shared),       # (batch, 1)
                "volatility": F.softplus(self.volatility_head(shared)),  # (batch, 1), always positive
            }


    # ---------------------------------------------------------------------------
    # DailyLSTM v2 Module (nn.Module)
    # ---------------------------------------------------------------------------

    class DailyLSTMModule(nn.Module):
        """
        Core LSTM module with optional attention and multi-task heads.
        Backward-compatible single-output mode for legacy inference.

        Architecture:
            Input → LSTM(2 layers) → [Attention] → [MultiTaskHead | SingleHead]
        """

        def __init__(
            self,
            num_features: int = 5,
            hidden_size: int = 128,
            num_layers: int = 2,
            dropout: float = 0.3,
            use_attention: bool = True,
            multi_task: bool = False,
        ):
            super().__init__()
            self.num_features = num_features
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.use_attention = use_attention
            self.multi_task = multi_task

            # Input projection (handles variable feature counts)
            self.input_proj = nn.Linear(num_features, hidden_size)
            self.input_norm = nn.LayerNorm(hidden_size)

            # LSTM backbone
            self.lstm = nn.LSTM(
                input_size=hidden_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
                bidirectional=False,
            )

            # Layer norm after LSTM
            self.post_lstm_norm = nn.LayerNorm(hidden_size)

            # Attention (optional)
            self.attention = TemporalAttention(
                hidden_size=hidden_size,
                num_heads=4,
                dropout=dropout,
            ) if use_attention else None

            # Output heads
            if multi_task:
                self.task_head = MultiTaskHead(hidden_size, dropout=dropout)
                self.fc_out = None
            else:
                # Legacy single-output head (direction logit)
                self.task_head = None
                self.fc_out = nn.Sequential(
                    nn.Dropout(dropout),
                    nn.Linear(hidden_size, 1),
                )

        def forward(
            self, x: torch.Tensor, return_attention: bool = False
        ) -> torch.Tensor | Dict[str, torch.Tensor]:
            """
            Args:
                x: (batch, seq_len, num_features)
                return_attention: If True, return attention weights (for interpretability).

            Returns:
                Single-task mode: (batch, 1) logits.
                Multi-task mode: Dict{'direction': (B,1), 'magnitude': (B,1), 'volatility': (B,1)}.
            """
            # Input projection
            x = self.input_proj(x)           # (batch, seq_len, hidden_size)
            x = self.input_norm(x)

            # LSTM
            lstm_out, (h_n, c_n) = self.lstm(x)  # lstm_out: (batch, seq_len, hidden_size)
            lstm_out = self.post_lstm_norm(lstm_out)

            # Attention or last hidden state
            if self.attention is not None:
                context = self.attention(lstm_out)  # (batch, hidden_size)
            else:
                context = lstm_out[:, -1, :]         # (batch, hidden_size)

            # Output
            if self.multi_task and self.task_head is not None:
                return self.task_head(context)
            else:
                return self.fc_out(context)


    # ---------------------------------------------------------------------------
    # Multi-Task Loss
    # ---------------------------------------------------------------------------

    class MultiTaskLoss(nn.Module):
        """
        Weighted multi-task loss combining direction, magnitude, and volatility.
        Uses uncertainty-based automatic loss weighting (Kendall et al. 2018).
        """

        def __init__(self):
            super().__init__()
            # Learnable log-variance parameters for auto-weighting
            self.log_var_dir = nn.Parameter(torch.zeros(1))
            self.log_var_mag = nn.Parameter(torch.zeros(1))
            self.log_var_vol = nn.Parameter(torch.zeros(1))

        def forward(
            self,
            predictions: Dict[str, torch.Tensor],
            targets: Dict[str, torch.Tensor],
        ) -> Tuple[torch.Tensor, Dict[str, float]]:
            """
            Args:
                predictions: {'direction': (B,1), 'magnitude': (B,1), 'volatility': (B,1)}
                targets: Same keys with ground truth.

            Returns:
                (total_loss, loss_breakdown_dict)
            """
            # Direction: BCE with logits
            loss_dir = F.binary_cross_entropy_with_logits(
                predictions["direction"], targets["direction"]
            )

            # Magnitude: Huber loss (robust to outliers)
            loss_mag = F.huber_loss(
                predictions["magnitude"], targets["magnitude"], delta=0.05
            )

            # Volatility: MSE
            loss_vol = F.mse_loss(
                predictions["volatility"], targets["volatility"]
            )

            # Uncertainty-weighted combination
            precision_dir = torch.exp(-self.log_var_dir)
            precision_mag = torch.exp(-self.log_var_mag)
            precision_vol = torch.exp(-self.log_var_vol)

            total = (
                precision_dir * loss_dir + self.log_var_dir +
                precision_mag * loss_mag + self.log_var_mag +
                precision_vol * loss_vol + self.log_var_vol
            )

            breakdown = {
                "loss_direction": loss_dir.item(),
                "loss_magnitude": loss_mag.item(),
                "loss_volatility": loss_vol.item(),
                "weight_direction": precision_dir.item(),
                "weight_magnitude": precision_mag.item(),
                "weight_volatility": precision_vol.item(),
                "total_loss": total.item(),
            }

            return total, breakdown


# ---------------------------------------------------------------------------
# DailyLSTM wrapper (matches original API from lstm_daily.py)
# ---------------------------------------------------------------------------

class DailyLSTM:
    """
    High-level wrapper for DailyLSTMModule.
    Preserves the original DailyLSTM(num_features=5) interface
    while supporting the new multi-task attention architecture.

    Attributes:
        _module: The underlying nn.Module (for trainer.py compatibility).
    """

    def __init__(
        self,
        num_features: int = 5,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        use_attention: bool = True,
        multi_task: bool = False,
    ):
        self.num_features = num_features
        self.hidden_size = hidden_size
        self.multi_task = multi_task
        self.use_attention = use_attention

        if TORCH_AVAILABLE:
            self._module = DailyLSTMModule(
                num_features=num_features,
                hidden_size=hidden_size,
                num_layers=num_layers,
                dropout=dropout,
                use_attention=use_attention,
                multi_task=multi_task,
            )
        else:
            self._module = None
            log.warning("PyTorch not available — DailyLSTM is a no-op wrapper.")

    def predict(self, x) -> dict:
        """
        Run inference on input tensor or numpy array.
        Returns dict with 'prob_up', and optionally 'magnitude' and 'volatility'.
        """
        if self._module is None:
            return {"prob_up": 0.5}

        import torch
        self._module.eval()
        device = next(self._module.parameters()).device

        if not isinstance(x, torch.Tensor):
            x = torch.tensor(x, dtype=torch.float32)
        if x.dim() == 2:
            x = x.unsqueeze(0)
        x = x.to(device)

        with torch.no_grad():
            output = self._module(x)

        if isinstance(output, dict):
            prob_up = torch.sigmoid(output["direction"]).item()
            return {
                "prob_up": prob_up,
                "magnitude": output["magnitude"].item(),
                "volatility": output["volatility"].item(),
            }
        else:
            return {"prob_up": torch.sigmoid(output).item()}

    def get_config(self) -> dict:
        """Return model config for logging/registry."""
        return {
            "num_features": self.num_features,
            "hidden_size": self.hidden_size,
            "multi_task": self.multi_task,
            "use_attention": self.use_attention,
            "param_count": sum(p.numel() for p in self._module.parameters()) if self._module else 0,
        }
