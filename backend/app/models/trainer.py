"""Training pipeline: sequence dataset, time split, LSTM training (research doc)."""
from datetime import date
from typing import List, Optional

import pandas as pd

FEATURE_COLS = ["return_1d", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel"]
TARGET_COL = "y_direction"


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


def get_daily_seq_dataset_class():
    """Return DailySeqDataset and train_lstm_daily if torch is available."""
    try:
        import torch
        from torch.utils.data import Dataset, DataLoader
    except ImportError:
        return None, None

    from app.models.lstm_daily import DailyLSTM, TORCH_AVAILABLE
    if not TORCH_AVAILABLE:
        return None, None

    class DailySeqDataset(Dataset):
        def __init__(self, df, feature_cols: List[str], target_col: str, seq_len: int = 60):
            self.feature_cols = feature_cols
            self.target_col = target_col
            self.seq_len = seq_len
            self.samples = []
            for symbol, g in df.groupby("symbol"):
                g = g.sort_values("date").dropna(subset=feature_cols + [target_col])
                values = g[feature_cols + [target_col]].to_numpy()
                if len(values) <= seq_len:
                    continue
                for i in range(len(values) - seq_len):
                    window = values[i : i + seq_len]
                    x = window[:, :-1]
                    y = window[-1, -1]
                    self.samples.append((x, y))

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            x, y = self.samples[idx]
            return (
                torch.tensor(x, dtype=torch.float32),
                torch.tensor(y, dtype=torch.float32),
            )

    def train_lstm_daily(
        df: pd.DataFrame,
        train_end: str,
        val_end: str,
        seq_len: int = 60,
        batch_size: int = 64,
        epochs: int = 10,
        lr: float = 1e-3,
    ):
        df_train, df_val = split_by_time(df, train_end, val_end)
        train_ds = DailySeqDataset(df_train, FEATURE_COLS, TARGET_COL, seq_len=seq_len)
        val_ds = DailySeqDataset(df_val, FEATURE_COLS, TARGET_COL, seq_len=seq_len)
        if len(train_ds) == 0:
            return None
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

        model = DailyLSTM(num_features=len(FEATURE_COLS))
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model._module.to(device)
        criterion = torch.nn.BCEWithLogitsLoss()
        optimizer = torch.optim.Adam(model._module.parameters(), lr=lr)

        for epoch in range(epochs):
            model._module.train()
            total_loss = 0.0
            for xb, yb in train_loader:
                xb, yb = xb.to(device), yb.to(device).unsqueeze(1)
                optimizer.zero_grad()
                logits = model._module(xb)
                loss = criterion(logits, yb)
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * xb.size(0)
            # Optional: validation
            model._module.eval()
            correct, total = 0, 0
            with torch.no_grad():
                for xb, yb in val_loader:
                    xb, yb = xb.to(device), yb.to(device).unsqueeze(1)
                    logits = model._module(xb)
                    probs = torch.sigmoid(logits)
                    preds = (probs > 0.5).float()
                    correct += (preds == yb).sum().item()
                    total += yb.size(0)
        return model

    return DailySeqDataset, train_lstm_daily
