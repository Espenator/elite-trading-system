"""LSTM Training Service - PyTorch GPU/CPU for regime prediction.

Trains on openclaw_signals features. GPU-accelerated when available.
Saves model artifacts + registers in models_registry table.
DB: backend/data/trading_orders.db
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "trading_orders.db"
ARTIFACT_DIR = Path(__file__).parent.parent.parent / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)


def get_device() -> str:
    """Detect best available device."""
    if not HAS_TORCH:
        return "cpu (torch not installed)"
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        return f"cuda ({name})"
    return "cpu"


class LSTMPredictor(nn.Module):
    """2-layer LSTM for win probability prediction."""

    def __init__(self, input_size=4, hidden_size=64, num_layers=2, output_size=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        _, (h_n, _) = self.lstm(x)
        out = self.fc(h_n[-1])
        return torch.sigmoid(out)


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def _ensure_tables(conn: sqlite3.Connection) -> None:
    # Keep schema compatible with TrainingStore (superset is OK).
    conn.execute(
        """CREATE TABLE IF NOT EXISTS models_registry (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            framework TEXT DEFAULT 'torch',
            trained_at TEXT,
            data_start TEXT, data_end TEXT,
            metrics_json TEXT,
            artifact_path TEXT,
            is_active BOOLEAN DEFAULT 0
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS training_runs (
            id INTEGER PRIMARY KEY,
            model_name TEXT,
            status TEXT DEFAULT 'queued',
            params_json TEXT,
            result_json TEXT,
            started_at TEXT, ended_at TEXT,
            error TEXT,
            dataset_source TEXT,
            algorithm TEXT,
            total_epochs INTEGER,
            validation_split TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS training_progress (
            run_id INTEGER PRIMARY KEY,
            epochs_completed INTEGER NOT NULL DEFAULT 0,
            total_epochs INTEGER NOT NULL DEFAULT 0,
            accuracy REAL,
            loss REAL,
            updated_at TEXT
        )"""
    )


class LSTMTrainer:
    """Train LSTM models on OpenClaw signal data."""

    def train(
        self,
        model_name: str,
        window_days: int = 252,
        epochs: int = 50,
        batch_size: int = 32,
        lr: float = 0.001,
        *,
        run_db_id: Optional[int] = None,
        dataset_source: Optional[str] = None,
        algorithm: Optional[str] = None,
        validation_split: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """Train an LSTM model and register it.

        progress_callback: called with dict:
          {epochsCompleted, totalEpochs, accuracy, loss}
        stop_check: if provided and returns True, stops early and returns {"stopped": True}
        """
        if not HAS_TORCH:
            return {"error": "PyTorch not installed"}

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Training {model_name} on {device}")

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row

        try:
            _ensure_tables(conn)
            conn.commit()

            end_date = datetime.utcnow().isoformat()
            start_date = (datetime.utcnow() - timedelta(days=window_days)).isoformat()

            # Fetch signals with score data
            df = pd.read_sql_query(
                """SELECT score, entry, stop, target, direction,
                          CASE WHEN direction='LONG' THEN
                            CASE WHEN target > entry THEN 1 ELSE 0 END
                          ELSE
                            CASE WHEN entry > target THEN 1 ELSE 0 END
                          END as label
                   FROM openclaw_signals
                   WHERE received_at BETWEEN ? AND ?
                   ORDER BY received_at""",
                conn,
                params=[start_date, end_date],
            )

            if len(df) < 50:
                return {"error": f"Insufficient data: {len(df)} rows (need 50+)"}

            # Feature engineering
            df["risk"] = abs(df["entry"] - df["stop"]).fillna(1.0)
            df["reward"] = abs(df["target"] - df["entry"]).fillna(1.0)
            df["rr_ratio"] = (df["reward"] / df["risk"]).clip(0, 10).fillna(1.0)
            df["dir_encoded"] = (df["direction"] == "LONG").astype(float)

            feature_cols = ["score", "rr_ratio", "risk", "dir_encoded"]
            features = df[feature_cols].fillna(0).values
            labels = df["label"].fillna(0).values.astype(int)

            X = torch.tensor(features, dtype=torch.float32).unsqueeze(1).to(device)
            y = torch.tensor(labels, dtype=torch.float32).unsqueeze(1).to(device)

            dataset = TensorDataset(X, y)
            loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

            model = LSTMPredictor(input_size=len(feature_cols)).to(device)
            criterion = nn.BCELoss()
            optimizer = optim.Adam(model.parameters(), lr=lr)

            # If training is tracked by an existing run row, mark start time (truthful)
            if run_db_id is not None:
                try:
                    conn.execute(
                        """
                        UPDATE training_runs
                        SET status='running',
                            started_at=COALESCE(started_at, ?),
                            model_name=?,
                            dataset_source=COALESCE(dataset_source, ?),
                            algorithm=COALESCE(algorithm, ?),
                            total_epochs=COALESCE(total_epochs, ?),
                            validation_split=COALESCE(validation_split, ?)
                        WHERE id=?
                        """,
                        (
                            _utc_now_iso(),
                            model_name,
                            dataset_source,
                            algorithm,
                            int(epochs),
                            validation_split,
                            int(run_db_id),
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO training_progress (run_id, epochs_completed, total_epochs, accuracy, loss, updated_at)
                        VALUES (?, 0, ?, NULL, NULL, ?)
                        ON CONFLICT(run_id) DO UPDATE SET total_epochs=excluded.total_epochs, updated_at=excluded.updated_at
                        """,
                        (int(run_db_id), int(epochs), _utc_now_iso()),
                    )
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Could not update training_runs start state for run_db_id={run_db_id}: {e}")

            # Training loop with progress callback + cooperative stop
            model.train()
            final_loss = 1.0
            last_acc: Optional[float] = None

            for epoch in range(int(epochs)):
                if stop_check and stop_check():
                    return {"stopped": True, "message": "Stop requested"}

                epoch_loss = 0.0
                for batch_x, batch_y in loader:
                    out = model(batch_x)
                    loss = criterion(out, batch_y)
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    epoch_loss += float(loss.item())

                final_loss = epoch_loss / max(len(loader), 1)

                # Evaluate (real) accuracy each epoch for progress reporting.
                model.eval()
                with torch.no_grad():
                    preds = model(X).detach().cpu().numpy().flatten()
                model.train()

                last_acc = float(np.mean((preds > 0.5) == labels))

                progress_payload = {
                    "epochsCompleted": int(epoch + 1),
                    "totalEpochs": int(epochs),
                    "accuracy": last_acc,
                    "loss": float(final_loss),
                }

                if progress_callback:
                    try:
                        progress_callback(progress_payload)
                    except Exception:
                        logger.exception("progress_callback failed")

                if run_db_id is not None:
                    try:
                        conn.execute(
                            """
                            INSERT INTO training_progress (run_id, epochs_completed, total_epochs, accuracy, loss, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(run_id) DO UPDATE SET
                                epochs_completed=excluded.epochs_completed,
                                total_epochs=excluded.total_epochs,
                                accuracy=excluded.accuracy,
                                loss=excluded.loss,
                                updated_at=excluded.updated_at
                            """,
                            (
                                int(run_db_id),
                                int(epoch + 1),
                                int(epochs),
                                float(last_acc),
                                float(final_loss),
                                _utc_now_iso(),
                            ),
                        )
                        conn.commit()
                    except Exception as e:
                        logger.warning(f"Failed to persist epoch progress for run_db_id={run_db_id}: {e}")

            # Final evaluation
            model.eval()
            with torch.no_grad():
                preds = model(X).cpu().numpy().flatten()

            accuracy = float(np.mean((preds > 0.5) == labels))
            sharpe_proxy = float(np.mean(preds * df["rr_ratio"].values))

            # Save artifact
            version = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            artifact_path = ARTIFACT_DIR / model_name / version / "model.pth"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), artifact_path)

            metrics = {
                "accuracy": round(accuracy, 6),  # 0..1
                "loss": round(float(final_loss), 6),
                "sharpe_proxy": round(sharpe_proxy, 6),
                "samples": int(len(df)),
                "device": str(device),
            }

            # Register in DB (real)
            run_id_written: Optional[int] = None
            try:
                # Deactivate old models with same name
                conn.execute("UPDATE models_registry SET is_active=0 WHERE name=?", (model_name,))
                conn.execute(
                    """INSERT INTO models_registry
                       (name, version, trained_at, data_start, data_end, metrics_json, artifact_path, is_active)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                    (
                        model_name,
                        version,
                        _utc_now_iso(),
                        start_date,
                        end_date,
                        json.dumps(metrics),
                        str(artifact_path),
                    ),
                )

                result_payload = {
                    "run_id": int(run_db_id) if run_db_id is not None else None,
                    "model_name": model_name,
                    "version": version,
                    "metrics": metrics,
                    "artifact_path": str(artifact_path),
                }

                if run_db_id is not None:
                    conn.execute(
                        """
                        UPDATE training_runs
                        SET status='success',
                            ended_at=?,
                            error=NULL,
                            result_json=?,
                            model_name=?,
                            dataset_source=COALESCE(dataset_source, ?),
                            algorithm=COALESCE(algorithm, ?),
                            total_epochs=COALESCE(total_epochs, ?),
                            validation_split=COALESCE(validation_split, ?)
                        WHERE id=?
                        """,
                        (
                            _utc_now_iso(),
                            json.dumps(result_payload),
                            model_name,
                            dataset_source,
                            algorithm,
                            int(epochs),
                            validation_split,
                            int(run_db_id),
                        ),
                    )
                    run_id_written = int(run_db_id)
                else:
                    # Backward-compatible behavior: create a run row if none was provided
                    run_id_written = conn.execute(
                        """INSERT INTO training_runs (model_name, status, started_at, ended_at, result_json)
                           VALUES (?, 'success', ?, ?, ?)""",
                        (model_name, _utc_now_iso(), _utc_now_iso(), json.dumps(result_payload)),
                    ).lastrowid

                conn.commit()
            except Exception as e:
                logger.error(f"DB registration failed: {e}")
                # If run_db_id exists, mark failed truthfully
                if run_db_id is not None:
                    try:
                        conn.execute(
                            "UPDATE training_runs SET status='failed', ended_at=?, error=? WHERE id=?",
                            (_utc_now_iso(), str(e), int(run_db_id)),
                        )
                        conn.commit()
                    except Exception:
                        pass
                run_id_written = -1

            logger.info(f"Training complete: {model_name} v{version} acc={accuracy:.3f}")
            return {
                "run_id": run_id_written,
                "model_name": model_name,
                "version": version,
                "metrics": metrics,
                "artifact_path": str(artifact_path),
            }

        finally:
            conn.close()


# Global instance
trainer = LSTMTrainer()
