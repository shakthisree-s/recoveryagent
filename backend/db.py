"""
SQLite persistence for the Revenue Recovery Agent.

Tables
------
* ``cases``             - one row per benchmark case (full case dict as JSON)
* ``recovery_attempts`` - one row per execution / retry / approval attempt
* ``batch_runs``        - one row per batch execution (full response as JSON)
* ``audit_events``      - append-only, chronological audit trail
* ``meta``              - small key/value store (seed marker, schema version)

The database is created on first import. Seeding of the 8 benchmark cases is
idempotent - it only happens when the ``cases`` table is empty, so restarts
never duplicate data. ``reset()`` truncates everything so the caller can
re-seed a clean benchmark state.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from backend.config import DB_PATH

_LOCK = threading.Lock()
SCHEMA_VERSION = "2"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                case_id     INTEGER PRIMARY KEY,
                data        TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recovery_attempts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id      INTEGER NOT NULL,
                attempt_num  INTEGER NOT NULL,
                timestamp    TEXT NOT NULL,
                data         TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS batch_runs (
                batch_id    TEXT PRIMARY KEY,
                timestamp   TEXT NOT NULL,
                data        TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                case_id     INTEGER,
                data        TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS meta (
                key         TEXT PRIMARY KEY,
                value       TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (SCHEMA_VERSION,),
        )


# --------------------------------------------------------------------------- #
# Cases
# --------------------------------------------------------------------------- #
def case_count() -> int:
    with _LOCK, _connect() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0])


def save_case(case: Dict[str, Any]) -> None:
    from datetime import datetime

    with _LOCK, _connect() as conn:
        conn.execute(
            "INSERT INTO cases(case_id, data, updated_at) VALUES(?, ?, ?) "
            "ON CONFLICT(case_id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
            (case["case_id"], json.dumps(case), datetime.now().isoformat(timespec="seconds")),
        )


def save_cases(cases: List[Dict[str, Any]]) -> None:
    for c in cases:
        save_case(c)


def load_cases() -> List[Dict[str, Any]]:
    with _LOCK, _connect() as conn:
        rows = conn.execute("SELECT data FROM cases ORDER BY case_id").fetchall()
    return [json.loads(r["data"]) for r in rows]


# --------------------------------------------------------------------------- #
# Recovery attempts
# --------------------------------------------------------------------------- #
def add_attempt(case_id: int, attempt_num: int, record: Dict[str, Any]) -> None:
    with _LOCK, _connect() as conn:
        conn.execute(
            "INSERT INTO recovery_attempts(case_id, attempt_num, timestamp, data) VALUES(?, ?, ?, ?)",
            (case_id, attempt_num, record.get("timestamp", ""), json.dumps(record)),
        )


def get_attempts(case_id: int) -> List[Dict[str, Any]]:
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            "SELECT data FROM recovery_attempts WHERE case_id=? ORDER BY id", (case_id,)
        ).fetchall()
    return [json.loads(r["data"]) for r in rows]


# --------------------------------------------------------------------------- #
# Batch runs
# --------------------------------------------------------------------------- #
def save_batch(batch_id: str, timestamp: str, payload: Dict[str, Any]) -> None:
    with _LOCK, _connect() as conn:
        conn.execute(
            "INSERT INTO batch_runs(batch_id, timestamp, data) VALUES(?, ?, ?) "
            "ON CONFLICT(batch_id) DO UPDATE SET data=excluded.data",
            (batch_id, timestamp, json.dumps(payload)),
        )


def get_batch(batch_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK, _connect() as conn:
        row = conn.execute("SELECT data FROM batch_runs WHERE batch_id=?", (batch_id,)).fetchone()
    return json.loads(row["data"]) if row else None


def latest_batch() -> Optional[Dict[str, Any]]:
    with _LOCK, _connect() as conn:
        row = conn.execute(
            "SELECT data FROM batch_runs ORDER BY timestamp DESC, rowid DESC LIMIT 1"
        ).fetchone()
    return json.loads(row["data"]) if row else None


# --------------------------------------------------------------------------- #
# Audit events
# --------------------------------------------------------------------------- #
def append_audit(events: List[Dict[str, Any]]) -> None:
    if not events:
        return
    with _LOCK, _connect() as conn:
        conn.executemany(
            "INSERT INTO audit_events(timestamp, case_id, data) VALUES(?, ?, ?)",
            [(e.get("timestamp", ""), e.get("case_id"), json.dumps(e)) for e in events],
        )


def get_audit(case_id: Optional[int] = None, newest_first: bool = True) -> List[Dict[str, Any]]:
    order = "DESC" if newest_first else "ASC"
    with _LOCK, _connect() as conn:
        if case_id is not None:
            rows = conn.execute(
                f"SELECT data FROM audit_events WHERE case_id=? ORDER BY id {order}", (case_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT data FROM audit_events ORDER BY id {order}"
            ).fetchall()
    return [json.loads(r["data"]) for r in rows]


def audit_count() -> int:
    with _LOCK, _connect() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])


# --------------------------------------------------------------------------- #
# Reset
# --------------------------------------------------------------------------- #
def reset() -> None:
    with _LOCK, _connect() as conn:
        conn.executescript(
            "DELETE FROM cases; DELETE FROM recovery_attempts; "
            "DELETE FROM batch_runs; DELETE FROM audit_events;"
        )
