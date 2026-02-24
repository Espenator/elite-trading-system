"""
TrainingStore - DB-backed storage for training datasets, runs, progress, configs, and deployment state.

Design goals:
- No mock / fabricated metrics.
- Stable API-friendly shaping of DB data (training.py should be thin).
- SQLite-first, compatible with existing ml_training.py + openclaw_db.py DB path.

DB: backend/data/trading_orders.db
Tables managed here (CREATE IF NOT EXISTS):
- training_runs
- training_progress
- training_configs
- models_registry (compat; created if missing)
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DB_PATH = Path(__file__).parent.parent.parent / "data" / "trading_orders.db"


def _utc_now_iso_z() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _safe_json_loads(s: Optional[str]) -> Optional[Dict[str, Any]]:
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [r[1] for r in rows] if rows else []


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return bool(row)


def _parse_public_run_id(run_id: str) -> Optional[int]:
    """
    Accepts:
      - "MT-000123"  -> 123
      - "123"        -> 123
    """
    if run_id is None:
        return None
    s = str(run_id).strip()
    if not s:
        return None
    if s.upper().startswith("MT-"):
        s = s[3:]
    try:
        return int(s)
    except Exception:
        return None


def _public_run_id(db_id: int) -> str:
    return f"MT-{int(db_id):06d}"


def _status_to_ui(status: Optional[str]) -> str:
    s = (status or "").lower().strip()
    if s in ("running",):
        return "Running"
    if s in ("queued", "pending"):
        return "Queued"
    if s in ("success", "completed", "done"):
        return "Completed"
    if s in ("failed", "error"):
        return "Failed"
    if s in ("stop_requested", "stopping"):
        return "Stopping"
    if s in ("stopped", "cancelled", "canceled"):
        return "Stopped"
    return status or "Unknown"


@dataclass
class TrainingRunCreate:
    model_name: str
    dataset_source: str
    algorithm: str
    epochs: int
    validation_split: str
    params: Dict[str, Any]


class TrainingStore:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_tables()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(DB_PATH))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_tables(self) -> None:
        conn = self._conn()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS training_runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name      TEXT,
                status          TEXT DEFAULT 'queued',
                params_json     TEXT,
                result_json     TEXT,
                started_at      TEXT,
                ended_at        TEXT,
                error           TEXT,

                -- optional metadata (may be NULL; used by API shaping)
                dataset_source  TEXT,
                algorithm       TEXT,
                total_epochs    INTEGER,
                validation_split TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_training_runs_status
                ON training_runs(status);

            CREATE INDEX IF NOT EXISTS idx_training_runs_started
                ON training_runs(started_at DESC);

            CREATE TABLE IF NOT EXISTS training_progress (
                run_id          INTEGER PRIMARY KEY,
                epochs_completed INTEGER NOT NULL DEFAULT 0,
                total_epochs    INTEGER NOT NULL DEFAULT 0,
                accuracy        REAL,
                loss            REAL,
                updated_at      TEXT,

                FOREIGN KEY(run_id) REFERENCES training_runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS training_configs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at      TEXT NOT NULL,
                config_json     TEXT NOT NULL
            );

            -- compatibility: ml_training.py also manages this; keep schema aligned
            CREATE TABLE IF NOT EXISTS models_registry (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                framework TEXT DEFAULT 'torch',
                trained_at TEXT,
                data_start TEXT, data_end TEXT,
                metrics_json TEXT,
                artifact_path TEXT,
                is_active BOOLEAN DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_models_registry_name
                ON models_registry(name);

            CREATE INDEX IF NOT EXISTS idx_models_registry_active
                ON models_registry(is_active);
            """
        )
        conn.commit()

    # -----------------------------
    # Runs
    # -----------------------------
    def has_active_run(self) -> bool:
        row = self._conn().execute(
            "SELECT id FROM training_runs WHERE status='running' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return bool(row)

    def create_run(self, spec: TrainingRunCreate) -> int:
        now = _utc_now_iso_z()
        conn = self._conn()
        cur = conn.execute(
            """
            INSERT INTO training_runs
                (model_name, status, params_json, started_at,
                 dataset_source, algorithm, total_epochs, validation_split)
            VALUES (?, 'running', ?, ?, ?, ?, ?, ?)
            """,
            (
                spec.model_name,
                json.dumps(spec.params or {}),
                now,
                spec.dataset_source,
                spec.algorithm,
                int(spec.epochs),
                spec.validation_split,
            ),
        )
        run_id = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO training_progress
                (run_id, epochs_completed, total_epochs, accuracy, loss, updated_at)
            VALUES (?, 0, ?, NULL, NULL, ?)
            """,
            (run_id, int(spec.epochs), now),
        )
        conn.commit()
        return run_id

    def request_stop(self, run_db_id: int) -> bool:
        conn = self._conn()
        cur = conn.execute(
            """
            UPDATE training_runs
            SET status='stop_requested'
            WHERE id=? AND status='running'
            """,
            (int(run_db_id),),
        )
        conn.commit()
        return cur.rowcount > 0

    def get_run_status(self, run_db_id: int) -> Optional[str]:
        row = self._conn().execute(
            "SELECT status FROM training_runs WHERE id=?",
            (int(run_db_id),),
        ).fetchone()
        return row["status"] if row else None

    def set_run_failed(self, run_db_id: int, error: str) -> None:
        now = _utc_now_iso_z()
        conn = self._conn()
        conn.execute(
            """
            UPDATE training_runs
            SET status='failed', ended_at=?, error=?
            WHERE id=?
            """,
            (now, error, int(run_db_id)),
        )
        conn.commit()

    def set_run_stopped(self, run_db_id: int, note: str = "Stopped") -> None:
        now = _utc_now_iso_z()
        conn = self._conn()
        conn.execute(
            """
            UPDATE training_runs
            SET status='stopped', ended_at=?, error=?
            WHERE id=?
            """,
            (now, note, int(run_db_id)),
        )
        conn.commit()

    def set_run_success(self, run_db_id: int, result: Dict[str, Any]) -> None:
        now = _utc_now_iso_z()
        conn = self._conn()
        conn.execute(
            """
            UPDATE training_runs
            SET status='success', ended_at=?, error=NULL, result_json=?
            WHERE id=?
            """,
            (now, json.dumps(result or {}), int(run_db_id)),
        )
        conn.commit()

    def upsert_progress(
        self,
        *,
        run_db_id: int,
        epochs_completed: int,
        total_epochs: int,
        accuracy: Optional[float],
        loss: Optional[float],
    ) -> None:
        conn = self._conn()
        now = _utc_now_iso_z()
        conn.execute(
            """
            INSERT INTO training_progress
                (run_id, epochs_completed, total_epochs, accuracy, loss, updated_at)
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
                int(epochs_completed),
                int(total_epochs),
                accuracy,
                loss,
                now,
            ),
        )
        conn.commit()

    # -----------------------------
    # API shaping
    # -----------------------------
    def get_active_progress_payload(self) -> Dict[str, Any]:
        conn = self._conn()
        run = conn.execute(
            """
            SELECT id, model_name, status
            FROM training_runs
            WHERE status IN ('running','stop_requested')
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        if not run:
            return {"active": False, "progress": None}

        prog = conn.execute(
            """
            SELECT epochs_completed, total_epochs, accuracy, loss
            FROM training_progress
            WHERE run_id=?
            """,
            (int(run["id"]),),
        ).fetchone()

        progress = None
        if prog:
            progress = {
                "epochsCompleted": int(prog["epochs_completed"] or 0),
                "totalEpochs": int(prog["total_epochs"] or 0),
                "accuracy": float(prog["accuracy"]) if prog["accuracy"] is not None else None,
                "loss": float(prog["loss"]) if prog["loss"] is not None else None,
            }

        return {
            "active": True,
            "progress": progress,
            "runId": _public_run_id(int(run["id"])),
        }

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT id, model_name, status, started_at, ended_at, error,
                   dataset_source, algorithm, total_epochs, validation_split,
                   params_json, result_json
            FROM training_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

        out: List[Dict[str, Any]] = []
        for r in rows:
            params = _safe_json_loads(r["params_json"]) or {}
            result = _safe_json_loads(r["result_json"]) or {}
            metrics = (result.get("metrics") if isinstance(result, dict) else None) or {}

            acc_val = metrics.get("accuracy")
            loss_val = metrics.get("loss")

            # Accuracy in ml_training is 0..1; present as "92.5%" only if real number present.
            accuracy_str = "N/A"
            if isinstance(acc_val, (int, float)):
                accuracy_str = f"{round(float(acc_val) * 100.0, 1)}%"

            loss_str = "N/A"
            if isinstance(loss_val, (int, float)):
                loss_str = str(round(float(loss_val), 4))

            out.append(
                {
                    "runId": _public_run_id(int(r["id"])),
                    "modelName": r["model_name"] or "",
                    "dataset": r["dataset_source"] or params.get("datasetSource") or "",
                    "algorithm": r["algorithm"] or params.get("algorithm") or "",
                    "startTime": (r["started_at"] or "")[:16].replace("T", " "),
                    "endTime": (r["ended_at"] or "")[:16].replace("T", " "),
                    "status": _status_to_ui(r["status"]),
                    "accuracy": accuracy_str,
                    "loss": loss_str,
                }
            )
        return out

    def get_run_details_payload(self, run_id: str) -> Dict[str, Any]:
        run_db_id = _parse_public_run_id(run_id)
        if run_db_id is None:
            raise KeyError("Run not found")

        conn = self._conn()
        r = conn.execute(
            """
            SELECT id, model_name, status, started_at, ended_at, error,
                   dataset_source, algorithm, total_epochs, validation_split,
                   params_json, result_json
            FROM training_runs
            WHERE id=?
            """,
            (int(run_db_id),),
        ).fetchone()

        if not r:
            raise KeyError("Run not found")

        params = _safe_json_loads(r["params_json"]) or {}
        result = _safe_json_loads(r["result_json"]) or {}
        metrics = (result.get("metrics") if isinstance(result, dict) else None) or {}

        # Keep the UI contract keys, but never fabricate missing metrics.
        accuracy = metrics.get("accuracy")  # 0..1 float
        loss = metrics.get("loss")

        perf_metrics: Dict[str, Any] = {
            "accuracy": float(accuracy) * 100.0 if isinstance(accuracy, (int, float)) else None,
            "precision": metrics.get("precision") if "precision" in metrics else None,
            "recall": metrics.get("recall") if "recall" in metrics else None,
            "f1Score": metrics.get("f1Score") if "f1Score" in metrics else None,
            "confusionMatrix": metrics.get("confusionMatrix") if "confusionMatrix" in metrics else None,
        }

        run_payload = {
            "runId": _public_run_id(int(r["id"])),
            "modelName": r["model_name"] or "",
            "dataset": r["dataset_source"] or params.get("datasetSource") or "",
            "algorithm": r["algorithm"] or params.get("algorithm") or "",
            "startTime": (r["started_at"] or "")[:16].replace("T", " "),
            "endTime": (r["ended_at"] or "")[:16].replace("T", " "),
            "status": _status_to_ui(r["status"]),
            "accuracy": (
                f"{round(float(accuracy) * 100.0, 1)}%" if isinstance(accuracy, (int, float)) else "N/A"
            ),
            "loss": str(round(float(loss), 4)) if isinstance(loss, (int, float)) else "N/A",
        }

        # Feature importance not computed by current LSTM pipeline; keep empty list (truthful).
        feature_importance = metrics.get("featureImportance")
        if not isinstance(feature_importance, list):
            feature_importance = []

        return {
            "run": run_payload,
            "performanceMetrics": perf_metrics,
            "featureImportance": feature_importance,
            "note": None if metrics else "No metrics yet",
            "error": r["error"],
        }

    def list_datasets_payload(self) -> List[Dict[str, Any]]:
        """
        training.py UI expects a list of dicts with:
          {name, size, lastUpdated, status}
        We derive this from real DB tables (OpenClaw ingests/signals).
        """
        conn = self._conn()

        if not (_table_exists(conn, "openclaw_ingests") and _table_exists(conn, "openclaw_signals")):
            return []

        row = conn.execute(
            """
            SELECT
                COUNT(*) AS signal_rows,
                MAX(received_at) AS last_signal_at
            FROM openclaw_signals
            """
        ).fetchone()
        signal_rows = int(row["signal_rows"] or 0) if row else 0
        last_signal_at = row["last_signal_at"] if row else None

        status = "Ready" if signal_rows > 0 else "Empty"
        last_updated = ""
        if last_signal_at:
            # stored as ISO+Z; keep date only if possible
            last_updated = str(last_signal_at)[:10]

        # "size" must be truthful; we do not invent GB/MB. Use rows count.
        size_str = f"{signal_rows} rows" if signal_rows > 0 else "0 rows"

        return [
            {
                "name": "OpenClawSignals",
                "size": size_str,
                "lastUpdated": last_updated,
                "status": status,
            }
        ]

    def model_comparison_payload(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        UI expects:
          {model, accuracy, precision, recall, f1Score, trainingTime, datasetSize}
        We provide real values where present; otherwise null/"N/A".
        """
        conn = self._conn()
        if not _table_exists(conn, "models_registry"):
            return []

        rows = conn.execute(
            """
            SELECT id, name, version, trained_at, metrics_json, artifact_path, is_active
            FROM models_registry
            ORDER BY trained_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

        out: List[Dict[str, Any]] = []
        for r in rows:
            metrics = _safe_json_loads(r["metrics_json"]) or {}
            acc = metrics.get("accuracy")
            out.append(
                {
                    "model": r["name"],
                    "accuracy": float(acc) * 100.0 if isinstance(acc, (int, float)) else None,
                    "precision": metrics.get("precision") if "precision" in metrics else None,
                    "recall": metrics.get("recall") if "recall" in metrics else None,
                    "f1Score": metrics.get("f1Score") if "f1Score" in metrics else None,
                    "trainingTime": "N/A",
                    "datasetSize": None,
                    "version": r["version"],
                    "isActive": bool(r["is_active"]),
                }
            )
        return out

    def save_config(self, config: Dict[str, Any]) -> int:
        conn = self._conn()
        now = _utc_now_iso_z()
        cur = conn.execute(
            "INSERT INTO training_configs (created_at, config_json) VALUES (?, ?)",
            (now, json.dumps(config or {})),
        )
        conn.commit()
        return int(cur.lastrowid)

    def deploy_model(self, model_name: Optional[str] = None, version: Optional[str] = None) -> Dict[str, Any]:
        """
        "Deploy" here means: mark one model registry row as active.
        This does not claim a prediction endpoint exists.
        """
        conn = self._conn()
        if not _table_exists(conn, "models_registry"):
            return {"deployed": False, "message": "No models_registry table found", "endpoint": None}

        target = None
        if model_name and version:
            target = conn.execute(
                """
                SELECT id, name, version FROM models_registry
                WHERE name=? AND version=?
                ORDER BY trained_at DESC LIMIT 1
                """,
                (model_name, version),
            ).fetchone()
        elif model_name:
            target = conn.execute(
                """
                SELECT id, name, version FROM models_registry
                WHERE name=?
                ORDER BY trained_at DESC LIMIT 1
                """,
                (model_name,),
            ).fetchone()
        else:
            target = conn.execute(
                """
                SELECT id, name, version FROM models_registry
                ORDER BY trained_at DESC LIMIT 1
                """
            ).fetchone()

        if not target:
            return {"deployed": False, "message": "No model found to deploy", "endpoint": None}

        # deactivate all of same name, then activate target
        conn.execute("UPDATE models_registry SET is_active=0 WHERE name=?", (target["name"],))
        conn.execute("UPDATE models_registry SET is_active=1 WHERE id=?", (int(target["id"]),))
        conn.commit()

        return {
            "deployed": True,
            "message": f"Model set active: {target['name']} v{target['version']}",
            "endpoint": None,
            "modelName": target["name"],
            "version": target["version"],
        }


# global instance
training_store = TrainingStore()
