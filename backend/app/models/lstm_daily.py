"""Daily LSTM for direction prediction (research doc architecture)."""
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    nn = None


class DailyLSTM:
    """Wrapper so we can define the class conditionally."""

    def __init__(self, num_features: int, hidden_size: int = 64, num_layers: int = 2):
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is required for LSTM. Install with: pip install torch")
        self._module = _DailyLSTM(num_features, hidden_size, num_layers)

    def __getattr__(self, name):
        return getattr(self._module, name)


if TORCH_AVAILABLE:

    class _DailyLSTM(nn.Module):
        def __init__(self, num_features: int, hidden_size: int = 64, num_layers: int = 2):
            super().__init__()
            self.lstm = nn.LSTM(
                input_size=num_features,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
            )
            self.fc = nn.Sequential(
                nn.Linear(hidden_size, 32),
                nn.ReLU(),
                nn.Linear(32, 1),
            )

        def forward(self, x):
            out, _ = self.lstm(x)
            last = out[:, -1, :]
            return self.fc(last)
