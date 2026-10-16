"""Persistencia SQLite con idempotencia y registros/alertas atómicos."""
import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .models import Anomaly, ConflictError, IngestResult, TelemetryRecord


class SQLiteTelemetryRepository:
    def __init__(self, path: str | Path):
        self.path = str(path)
        parent = Path(self.path).parent
        if self.path != ":memory:":
            parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS telemetry (
                    record_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    trip_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    measured_at TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_trip_time ON telemetry(trip_id, measured_at);
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT NOT NULL REFERENCES telemetry(record_id),
                    code TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    UNIQUE(record_id, code)
                );
                CREATE INDEX IF NOT EXISTS idx_alert_status ON alerts(status, alert_id);
            """)
            conn.commit()
        finally:
            conn.close()

    def save(self, record: TelemetryRecord, anomalies: Iterable[Anomaly]) -> IngestResult:
        payload = asdict(record)
        # El instante de recepción cambia en cada reintento y no altera la identidad de la lectura.
        payload_for_fingerprint = {k: v for k, v in payload.items() if k != "received_at"}
        canonical = json.dumps(payload_for_fingerprint, sort_keys=True, allow_nan=False, separators=(",", ":"))
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        stored = json.dumps(payload, sort_keys=True, allow_nan=False, separators=(",", ":"))
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT fingerprint FROM telemetry WHERE record_id = ?", (record.record_id,)).fetchone()
            if existing is not None:
                if existing["fingerprint"] != fingerprint:
                    raise ConflictError("Registro conflictivo: identificador repetido con distinta telemetría")
                conn.commit()
                return IngestResult(record.record_id, "duplicate", 0)
            conn.execute("""INSERT INTO telemetry
                         (record_id, device_id, trip_id, sequence, measured_at, received_at, fingerprint, payload_json)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                         (record.record_id, record.device_id, record.trip_id, record.sequence,
                          record.measured_at, record.received_at, fingerprint, stored))
            count = 0
            for anomaly in anomalies:
                conn.execute("""INSERT INTO alerts(record_id, code, severity, message, value, threshold)
                                VALUES (?, ?, ?, ?, ?, ?)""",
                             (record.record_id, anomaly.code, anomaly.severity, anomaly.message,
                              anomaly.value, anomaly.threshold))
                count += 1
            conn.commit()
            return IngestResult(record.record_id, "accepted", count)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def summary(self) -> dict:
        conn = self._connect()
        try:
            counts = conn.execute("SELECT COUNT(*) AS n, COUNT(DISTINCT trip_id) AS trips, COUNT(DISTINCT device_id) AS devices FROM telemetry").fetchone()
            alerts = conn.execute("SELECT COUNT(*) AS n FROM alerts WHERE status = 'pending'").fetchone()
            return {"records": counts["n"], "trips": counts["trips"], "devices": counts["devices"], "alerts_pending": alerts["n"]}
        finally:
            conn.close()

    def recent(self, limit: int = 10) -> list[dict]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit entre 1 y 100")
        conn = self._connect()
        try:
            rows = conn.execute("SELECT payload_json FROM telemetry ORDER BY measured_at DESC, record_id DESC LIMIT ?", (limit,))
            return [json.loads(row["payload_json"]) for row in rows]
        finally:
            conn.close()

    def pending_alerts(self, limit: int = 10) -> list[dict]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit entre 1 y 100")
        conn = self._connect()
        try:
            rows = conn.execute("""SELECT alert_id, record_id, code, severity, message, value, threshold, status
                                    FROM alerts WHERE status = 'pending' ORDER BY alert_id DESC LIMIT ?""", (limit,))
            return [dict(row) for row in rows]
        finally:
            conn.close()
