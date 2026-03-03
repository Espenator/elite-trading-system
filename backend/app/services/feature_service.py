"""
Feature Service — Wires DuckDB storage to FeaturePipeline to XGBoost trainer.

This is the orchestration layer that closes the gap between
data ingestion and ML training.

Usage:
    from app.services.feature_service import feature_service
    df, manifest = feature_service.build_training_set(["AAPL", "MSFT"])
    # df has 30+ features + multi-horizon labels, ready for xgboost_trainer.py

Fixes Issue #25 — Wire Feature Pipeline to DuckDB.
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# Training window constants (from project state)
TRAINING_DAYS = 252    # 12 months of trading days
VALIDATION_DAYS = 63   # 3 months of trading days
CALENDAR_BUFFER = 1.5  # Calendar days per trading day ratio


class FeatureService:
    """Orchestrates DuckDB -> FeaturePipeline -> training-ready DataFrames."""

    def __init__(self):
        self._pipeline = None
        self._store = None

    @property
    def store(self):
        if self._store is None:
            from app.data.duckdb_storage import duckdb_store
            self._store = duckdb_store
        return self._store

    @property
    def pipeline(self):
        if self._pipeline is None:
            from app.modules.ml_engine.feature_pipeline import FeaturePipeline
            self._pipeline = FeaturePipeline()
        return self._pipeline

    def build_training_set(
        self,
        symbols: List[str],
        end_date: str = None,
        training_days: int = TRAINING_DAYS,
        validation_days: int = VALIDATION_DAYS,
        include_flow: bool = True,
        include_macro: bool = True,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        """Build train + validation DataFrames with walk-forward split.

        Args:
            symbols: List of tickers to include
            end_date: Last date for validation (defaults to today)
            training_days: Number of trading days for training window
            validation_days: Number of trading days for validation window
            include_flow: Include Unusual Whales options flow features
            include_macro: Include FRED macro features

        Returns:
            (train_df, val_df, manifest_dict)
            Both DataFrames have 30+ feature columns + label columns.
        """
        if end_date is None:
            end_date = date.today().isoformat()

        # Calculate date ranges (approximate calendar days)
        total_trading_days = training_days + validation_days
        calendar_days = int(total_trading_days * CALENDAR_BUFFER) + 250  # Extra buffer for 200d MA warmup
        start_date = (
            date.fromisoformat(end_date) - timedelta(days=calendar_days)
        ).isoformat()

        logger.info(
            "Building training set: %d symbols, %s to %s (%d+%d trading days)",
            len(symbols), start_date, end_date, training_days, validation_days
        )

        # Step 1: Pull joined data from DuckDB
        raw_df = self.store.get_training_window(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            include_indicators=True,
            include_flow=include_flow,
            include_macro=include_macro,
        )

        if raw_df.empty:
            logger.error("No data returned from DuckDB for symbols %s", symbols)
            return pd.DataFrame(), pd.DataFrame(), {}

        # Step 2: Generate features via pipeline
        df, manifest = self.pipeline.generate(
            raw_df,
            include_labels=True,
            include_options_flow=include_flow,
            include_macro=include_macro,
        )

        # Step 3: Walk-forward split
        # Drop NaN rows from rolling calculations warmup
        df = df.dropna(subset=manifest.feature_cols[:5])  # Core features must be non-null

        # Split by date: last validation_days trading days = validation
        unique_dates = sorted(df["date"].unique())
        if len(unique_dates) <= validation_days:
            logger.warning(
                "Only %d dates available, need %d for validation split",
                len(unique_dates), validation_days
            )
            return df, pd.DataFrame(), manifest.__dict__

        split_date = unique_dates[-validation_days]
        train_df = df[df["date"] < split_date].copy()
        val_df = df[df["date"] >= split_date].copy()

        logger.info(
            "Walk-forward split: train=%d rows (%s to %s), val=%d rows (%s to %s), features=%d",
            len(train_df), train_df["date"].min(), train_df["date"].max(),
            len(val_df), val_df["date"].min(), val_df["date"].max(),
            manifest.n_features,
        )

        return train_df, val_df, manifest.__dict__

    def build_inference_set(
        self,
        symbols: List[str],
        lookback_days: int = 250,
    ) -> Tuple[pd.DataFrame, Dict]:
        """Build feature DataFrame for real-time inference (no labels).

        Args:
            symbols: List of tickers
            lookback_days: Days of history for feature calculation

        Returns:
            (feature_df, manifest_dict)
        """
        raw_df = self.store.get_inference_snapshot(symbols, lookback_days)

        if raw_df.empty:
            logger.warning("No inference data for %s", symbols)
            return pd.DataFrame(), {}

        df, manifest = self.pipeline.generate(
            raw_df,
            include_labels=False,
            include_options_flow=True,
            include_macro=True,
        )

        # Return only the latest row per symbol (most recent features)
        latest = df.sort_values("date").groupby("symbol").tail(1)

        logger.info(
            "Inference set: %d symbols, %d features",
            len(latest), manifest.n_features,
        )
        return latest, manifest.__dict__

    def get_feature_health(self) -> Dict:
        """Return feature pipeline + storage health for monitoring."""
        storage_health = self.store.health_check()
        manifest = self.pipeline.manifest
        return {
            "storage": storage_health,
            "pipeline_version": "2.0.0",
            "feature_count": manifest.n_features if manifest else 0,
            "label_count": manifest.n_labels if manifest else 0,
            "manifest_exists": manifest is not None,
        }


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------
feature_service = FeatureService()
