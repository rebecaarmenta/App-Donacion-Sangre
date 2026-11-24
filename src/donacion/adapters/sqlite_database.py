"""Conexión a SQLite (biblioteca estándar, sin dependencias) y esquema de la base de datos.

Una sola conexión compartida, protegida con un candado: la API atiende peticiones en varios
hilos y el escalamiento automático corre en otro. Cada operación es una transacción.
"""
from __future__ import annotations

import secrets
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS donors (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    email            TEXT NOT NULL UNIQUE,
    password_hash    TEXT NOT NULL,
    birth_date       TEXT NOT NULL,
    weight_kg        REAL NOT NULL,
    blood_type       TEXT NOT NULL,
    lat              REAL NOT NULL,
    lon              REAL NOT NULL,
    last_donation    TEXT,
    eligibility      TEXT NOT NULL,
    eligibility_reasons TEXT NOT NULL,   -- JSON
    eligible_from    TEXT,
    alerts_received  INTEGER NOT NULL DEFAULT 0,
    alerts_accepted  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS donations (
    donor_id   TEXT NOT NULL REFERENCES donors(id) ON DELETE CASCADE,
    position   INTEGER NOT NULL,
    day        TEXT NOT NULL,
    request_id TEXT,
    hospital   TEXT,
    PRIMARY KEY (donor_id, position)
);
CREATE TABLE IF NOT EXISTS requests (
    id               TEXT PRIMARY KEY,
    requester_name   TEXT NOT NULL,
    blood_type       TEXT NOT NULL,
    units_needed     INTEGER NOT NULL,
    hospital_name    TEXT NOT NULL,
    hospital_lat     REAL NOT NULL,
    hospital_lon     REAL NOT NULL,
    urgency          TEXT NOT NULL,
    deadline         TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    status           TEXT NOT NULL,
    notified_donors  TEXT NOT NULL,   -- JSON
    confirmed_donors TEXT NOT NULL,   -- JSON
    waves_sent       INTEGER NOT NULL,
    last_wave_at     TEXT
);
CREATE INDEX IF NOT EXISTS requests_status ON requests(status);
CREATE TABLE IF NOT EXISTS alerts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    donor_id   TEXT NOT NULL,
    donor_name TEXT NOT NULL,
    wave       INTEGER NOT NULL,
    score      REAL NOT NULL,
    message    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS alerts_request ON alerts(request_id);
CREATE INDEX IF NOT EXISTS alerts_donor ON alerts(donor_id);
CREATE TABLE IF NOT EXISTS app_secrets (
    name  TEXT PRIMARY KEY,
    value BLOB NOT NULL
);
"""


class SqliteDatabase:
    def __init__(self, path: str) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self.transaction() as db:
            db.execute("PRAGMA foreign_keys = ON")
            if path != ":memory:":
                db.execute("PRAGMA journal_mode = WAL")
            db.executescript(SCHEMA)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Ejecuta un bloque como una transacción: todo se guarda o nada (rollback si falla)."""
        with self._lock:
            try:
                yield self._connection
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def secret(self, name: str) -> bytes:
        """Clave aleatoria que se crea la primera vez y se reutiliza después (p. ej. para firmar
        sesiones): así las sesiones siguen valiendo cuando se reinicia el servidor."""
        with self.transaction() as c:
            c.execute("INSERT OR IGNORE INTO app_secrets (name, value) VALUES (?, ?)",
                      (name, secrets.token_bytes(32)))
            return bytes(c.execute("SELECT value FROM app_secrets WHERE name = ?", (name,)).fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._connection.close()
