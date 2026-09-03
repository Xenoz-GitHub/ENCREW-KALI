"""SQLite persistence for targets, cases, observations, and findings."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS targets (id INTEGER PRIMARY KEY, value TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS observations (id TEXT PRIMARY KEY, case_name TEXT NOT NULL, target TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, case_name TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS commands (id INTEGER PRIMARY KEY, case_name TEXT, argv TEXT NOT NULL, returncode INTEGER NOT NULL, duration REAL NOT NULL, created_at TEXT NOT NULL);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path.expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def add_target(self, value: str) -> None:
        self.connection.execute("INSERT OR IGNORE INTO targets(value, created_at) VALUES (?, ?)", (value, now()))
        self.connection.commit()

    def targets(self) -> list[str]:
        return [row["value"] for row in self.connection.execute("SELECT value FROM targets ORDER BY value")]

    def remove_target(self, value: str) -> None:
        self.connection.execute("DELETE FROM targets WHERE value = ?", (value,))
        self.connection.commit()

    def create_case(self, name: str) -> None:
        self.connection.execute("INSERT INTO cases(name, created_at, status) VALUES (?, ?, ?)", (name, now(), "open"))
        self.connection.commit()

    def cases(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute("SELECT * FROM cases ORDER BY created_at DESC")]

    def case(self, name: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM cases WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

    def add_observation(self, identifier: str, case_name: str, target: str, kind: str, data: dict[str, Any]) -> None:
        self.connection.execute("INSERT OR REPLACE INTO observations VALUES (?, ?, ?, ?, ?, ?)", (identifier, case_name, target, kind, json.dumps(data), now()))
        self.connection.commit()

    def observations(self, case_name: str) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM observations WHERE case_name = ? ORDER BY created_at", (case_name,))
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]

    def add_finding(self, identifier: str, case_name: str, data: dict[str, Any]) -> None:
        self.connection.execute("INSERT OR REPLACE INTO findings VALUES (?, ?, ?, ?)", (identifier, case_name, json.dumps(data), now()))
        self.connection.commit()

    def findings(self, case_name: str) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM findings WHERE case_name = ? ORDER BY created_at", (case_name,))
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]

    def close(self) -> None:
        self.connection.close()
