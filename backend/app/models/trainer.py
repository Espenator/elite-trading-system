"""Training pipeline: sequence dataset, time split, LSTM training with mixed-precision.

APEX Phase 2 upgrades:
- torch.cuda.amp GradScaler for mixed-precision (FP16 on GPU, FP32 fallback on CPU)
- Gradient clipping (max_norm=1.0) to prevent exploding gradients
- Per-epoch training metrics logging (loss, val_loss, val_accuracy)
- Early stopping with configurable patience
- Model checkpoint saving (best val_loss) to MODEL_ARTIFACTS_PATH
- DailySeqDataset and load_feature_frame kept exactly as before
"""
from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature / target columns (unchanged)
# ---------------------------------------------------------------------------
FEATURE_COLS = ["return_1d", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel"]
TARGET_COL = "y_direction"


# ---------------------------------------------------------------------------
# DuckDB loader (unchanged)
# ---------------------------------------------------------------------------
def load_feature_frame(
    conn,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> pd.DataFrame:
    """Load feature DataFrame from DuckDB daily_features."""
    query = (
        "SELECT symbol, date, close, "
        + ", ".join(FEATURE_COLS + [TARGET_COL])
        + " FROM daily_features"
    )
    params = []
    if start and end:
        query += " WHERE date BETWEEN ? AND ?"
        params = [start, end]
    df = conn.execute(query, params).df()
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["symbol", "date"])


def split_by_time(df: pd.DataFrame, train_end: str, val_end: str):
    """Split DataFrame by date for train/val."""
    train_mask = df["date"] <= pd.to_datetime(train_end)
    val_mask = (df["date"] > pd.to_datetime(train_end)) & (df["date"] <= pd.to_datetime(val_end))
    return df[train_mask], df[val_mask]


# ---------------------------------------------------------------------------
# Dataset + training (torch-optional)
# ---------------------------------------------------------------------------
def get_daily_seq_dataset_class():
    """Return DailySeqDataset and train_lstm_daily if torch is available."""
    try:
        import torch
        import torch.nn as nn
        from torch.cuda.amp import GradScaler, autocast
        from torch.utils.data import DataLoader, Dataset
    except ImportError:
        return None, None

    from app.models.lstm_daily import DailyLSTM, TORCH_AVAILABLE

    if not TORCH_AVAILABLE:
        return None, None

    class DailySeqDataset(Dataset):  # noqa: D101
        def __init__(
            self,
            df: pd.DataFrame,
            feature_cols: List[str],
            target_col: str,
            seq_len: int = 60,
        ):
            self.feature_cols = feature_cols
            self.target_col = target_col
            self.seq_len = seq_len
            self.samples: List[Tuple] = []
            for _symbol, g in df.groupby("symbol"):
                g = g.sort_values("date").dropna(subset=feature_cols + [target_col])
                values = g[feature_cols + [target_col]].to_numpy()
                if len(values) <= seq_len:
                    continue
                for i in range(len(values) - seq_len):
                    window = values[i : i + seq_len]
                    x = window[:, :-1]
                    y = window[-1, -1]
                    self.samples.append((x, y))

        def __len__(self) -> int:
            return len(self.samples)

        def __getitem__(self, idx: int):
            x, y = self.samples[idx]
            return (
                torch.tensor(x, dtype=torch.float32),
                torch.tensor(y, dtype=torch.float32),
            )

    # -----------------------------------------------------------------------
    def train_lstm_daily(
        df: pd.DataFrame,
        train_end: str,
        val_end: str,
        seq_len: int = 60,
        batch_size: int = 64,
        epochs: int = 10,
        lr: float = 1e-3,
        patience: int = 3,
        max_grad_norm: float = 1.0,
        checkpoint_dir: Optional[str] = None,
    ) -> Optional[object]:
        """Train LSTM with AMP mixed-precision, gradient clipping, early stopping.

        Args:
            df: Full feature dataframe (all symbols).
            train_end: Inclusive end date for training split (YYYY-MM-DD).
            val_end: Inclusive end date for validation split (YYYY-MM-DD).
            seq_len: Lookback window length.
            batch_size: Mini-batch size.
            epochs: Maximum training epochs.
            lr: Adam learning rate.
            patience: Early-stopping patience (epochs without val_loss improvement).
            max_grad_norm: Gradient clipping max norm.
            checkpoint_dir: Directory to save best model checkpoint. Defaults to
                MODEL_ARTIFACTS_PATH env var or 'models/artifacts'.

        Returns:
            Trained DailyLSTM wrapper, or None if training data is empty.
        """
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        use_amp = device.type == "cuda"  # AMP only meaningful on CUDA
        log.info("Training device: %s  AMP: %s", device, use_amp)

        # --- data --------------------------------------------------------
        df_train, df_val = split_by_time(df, train_end, val_end)
        train_ds = DailySeqDataset(df_train, FEATURE_COLS, TARGET_COL, seq_len=seq_len)
        val_ds = DailySeqDataset(df_val, FEATURE_COLS, TARGET_COL, seq_len=seq_len)
        if len(train_ds) == 0:
            log.warning("train_lstm_daily: empty training dataset, aborting.")
            return None

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                                  pin_memory=use_amp, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                                pin_memory=use_amp, num_workers=0)

        # --- model -------------------------------------------------------
        model = DailyLSTM(num_features=len(FEATURE_COLS))
        model._module.to(device)

        criterion = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.Adam(model._module.parameters(), lr=lr)
        scaler = GradScaler(enabled=use_amp)

        # --- checkpoint dir ---------------------------------------------
        ckpt_dir = Path(
            checkpoint_dir
            or os.getenv("MODEL_ARTIFACTS_PATH", "models/artifacts")
        )
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        best_ckpt = ckpt_dir / "lstm_daily_best.pt"
        latest_ckpt = ckpt_dir / "lstm_daily_latest.pt"

        # --- training loop ----------------------------------------------
        best_val_loss: float = float("inf")
        patience_counter: int = 0
        history: List[Dict] = []

        for epoch in range(1, epochs + 1):
            # -- train --
            model._module.train()
            running_loss = 0.0
            n_train = 0
            for xb, yb in train_loader:
                xb = xb.to(device, non_blocking=True)
                yb = yb.to(device, non_blocking=True).unsqueeze(1)
                optimizer.zero_grad()
                with autocast(enabled=use_amp):
                    logits = model._module(xb)
                    loss = criterion(logits, yb)
                scaler.scale(loss).backward()
                # gradient clipping (unscale first so clip operates on real grads)
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model._module.parameters(), max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
                running_loss += loss.item() * xb.size(0)
                n_train += xb.size(0)

            train_loss = running_loss / max(n_train, 1)

            # -- validate --
            model._module.eval()
            val_loss_sum = 0.0
            correct = 0
            n_val = 0
            with torch.no_grad():
                for xb, yb in val_loader:
                    xb = xb.to(device, non_blocking=True)
                    yb = yb.to(device, non_blocking=True).unsqueeze(1)
                    with autocast(enabled=use_amp):
                        logits = model._module(xb)
                        v_loss = criterion(logits, yb)
                    val_loss_sum += v_loss.item() * xb.size(0)
                    preds = (torch.sigmoid(logits) > 0.5).float()
                    correct += (preds == yb).sum().item()
                    n_val += xb.size(0)

            val_loss = val_loss_sum / max(n_val, 1)
            val_acc = correct / max(n_val, 1)

            metrics = {
                "epoch": epoch,
                "train_loss": round(train_loss, 6),
                "val_loss": round(val_loss, 6),
                "val_accuracy": round(val_acc, 4),
            }
            history.append(metrics)
            log.info(
                "Epoch %d/%d  train_loss=%.4f  val_loss=%.4f  val_acc=%.3f",
                epoch, epochs, train_loss, val_loss, val_acc,
            )

            # -- checkpoint (best val_loss) -------------------------------
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                torch.save(model._module.state_dict(), best_ckpt)
                log.info("  -> New best checkpoint saved: %s", best_ckpt)
            else:
                patience_counter += 1
                log.info(
                    "  -> No improvement (%d/%d patience)", patience_counter, patience
                )

            # -- early stopping ------------------------------------------
            if patience_counter >= patience:
                log.info("Early stopping triggered at epoch %d.", epoch)
                break

        # save latest regardless
        torch.save(model._module.state_dict(), latest_ckpt)
        log.info("Latest checkpoint saved: %s", latest_ckpt)

        # attach training history to model for introspection
        model.training_history = history  # type: ignore[attr-defined]
        model.best_val_loss = best_val_loss  # type: ignore[attr-defined]
        return model

    return DailySeqDataset, train_lstm_daily
