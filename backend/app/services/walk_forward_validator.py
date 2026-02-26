"""Walk-Forward Validation for ML Training Pipeline.

Prevents overfitting by using rolling train/test windows that
never peek into future data. The LSTM and any future ensemble
models are validated on truly out-of-sample data.

Usage in ml_training.py:
    from app.services.walk_forward_validator import WalkForwardValidator
    validator = WalkForwardValidator(train_days=252, test_days=63)
    for train_df, test_df in validator.generate_splits(features_df):
        # train model on train_df, evaluate on test_df

Based on Perplexity model council recommendation (Intelligence Layer #1).
References: Duke backtesting protocol, IB research team guidelines.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Generator, List, Tuple

import numpy as np
import pandas as pd

try:
    import torch
    from torch.utils.data import TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = logging.getLogger(__name__)


@dataclass
class FoldResult:
    """Stores metrics for a single walk-forward fold."""
    fold: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_samples: int
    test_samples: int
    test_loss: float = 0.0
    test_accuracy: float = 0.0
    sharpe_ratio: float = 0.0


class WalkForwardValidator:
    """Time-series walk-forward cross-validator.

    Generates chronological train/test splits that roll forward.
    No data from the test window ever appears in training.

    Parameters
    ----------
    train_days : int
        Number of trading days in each training window (default 252 = 1yr).
    test_days : int
        Number of trading days in each validation window (default 63 = 1qtr).
    step_days : int | None
        How many days to advance between folds. Defaults to test_days
        (non-overlapping test windows).
    min_train_samples : int
        Minimum rows required in a training fold to proceed.
    """

    def __init__(
        self,
        train_days: int = 252,
        test_days: int = 63,
        step_days: int | None = None,
        min_train_samples: int = 100,
    ):
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days or test_days
        self.min_train_samples = min_train_samples

    # ------------------------------------------------------------------
    def generate_splits(
        self,
        df: pd.DataFrame,
        date_col: str = "timestamp",
    ) -> Generator[Tuple[pd.DataFrame, pd.DataFrame], None, None]:
        """Yield (train_df, test_df) tuples rolling forward in time.

        The dataframe MUST contain a datetime-parseable column `date_col`.
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col).reset_index(drop=True)

        total = len(df)
        window = self.train_days + self.test_days

        if total < window:
            logger.warning(
                "Only %d rows but need %d for one fold. "
                "Returning single emergency split.",
                total, window,
            )
            split = int(total * 0.8)
            yield df.iloc[:split], df.iloc[split:]
            return

        fold = 0
        for start in range(0, total - window + 1, self.step_days):
            train_end = start + self.train_days
            test_end = train_end + self.test_days

            train_df = df.iloc[start:train_end]
            test_df = df.iloc[train_end:test_end]

            if len(train_df) < self.min_train_samples:
                continue

            fold += 1
            logger.info(
                "Fold %d | train %s -> %s (%d rows) | test %s -> %s (%d rows)",
                fold,
                train_df[date_col].iloc[0].date(),
                train_df[date_col].iloc[-1].date(),
                len(train_df),
                test_df[date_col].iloc[0].date(),
                test_df[date_col].iloc[-1].date(),
                len(test_df),
            )
            yield train_df, test_df

        if fold == 0:
            logger.error("No valid folds produced. Check data length.")

    # ------------------------------------------------------------------
    def run_torch_walk_forward(
        self,
        features_df: pd.DataFrame,
        model,
        optimizer,
        criterion,
        prepare_fn,
        epochs: int = 50,
        date_col: str = "timestamp",
    ) -> Tuple[object, List[FoldResult]]:
        """Full walk-forward loop for a PyTorch model.

        Parameters
        ----------
        features_df : DataFrame with a date column + feature columns.
        model       : nn.Module (e.g. LSTMPredictor from ml_training.py).
        optimizer   : torch optimizer.
        criterion   : loss function.
        prepare_fn  : callable(df) -> (X_tensor, y_tensor).
        epochs      : training epochs per fold.
        date_col    : name of the datetime column.

        Returns
        -------
        model, list[FoldResult]
        """
        if not HAS_TORCH:
            raise ImportError("PyTorch required for run_torch_walk_forward")

        results: List[FoldResult] = []

        for train_df, test_df in self.generate_splits(features_df, date_col):
            fold_num = len(results) + 1

            X_train, y_train = prepare_fn(train_df)
            X_test, y_test = prepare_fn(test_df)

            # ---------- train ----------
            model.train()
            for epoch in range(epochs):
                optimizer.zero_grad()
                outputs = model(X_train)
                loss = criterion(outputs, y_train)
                loss.backward()
                optimizer.step()

            # ---------- validate ----------
            model.eval()
            with torch.no_grad():
                test_out = model(X_test)
                test_loss = criterion(test_out, y_test).item()

                # Binary accuracy (direction prediction)
                if test_out.shape[-1] == 1:
                    preds = (test_out.squeeze() > 0.5).float()
                    labels = y_test.squeeze()
                else:
                    preds = test_out.argmax(dim=1).float()
                    labels = y_test.float()
                accuracy = (preds == labels).float().mean().item() * 100

            fr = FoldResult(
                fold=fold_num,
                train_start=str(train_df[date_col].iloc[0].date()),
                train_end=str(train_df[date_col].iloc[-1].date()),
                test_start=str(test_df[date_col].iloc[0].date()),
                test_end=str(test_df[date_col].iloc[-1].date()),
                train_samples=len(train_df),
                test_samples=len(test_df),
                test_loss=round(test_loss, 4),
                test_accuracy=round(accuracy, 1),
            )
            results.append(fr)
            logger.info(
                "Fold %d complete | loss=%.4f | acc=%.1f%%",
                fold_num, test_loss, accuracy,
            )

        if results:
            avg_loss = np.mean([r.test_loss for r in results])
            avg_acc = np.mean([r.test_accuracy for r in results])
            logger.info(
                "Walk-Forward Complete: %d folds | avg_loss=%.4f | avg_acc=%.1f%%",
                len(results), avg_loss, avg_acc,
            )

        return model, results
