"""Schema and query helpers. Every analysis lives in sql/*.sql so it can be read on its own."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

SCHEMA = """
CREATE TABLE users (
    user_id     INTEGER PRIMARY KEY,
    signup_date TEXT NOT NULL,
    channel     TEXT NOT NULL,
    country     TEXT NOT NULL
);
CREATE TABLE events (
    event_id   INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users (user_id),
    event_ts   TEXT NOT NULL,          -- ISO 8601, UTC
    event_name TEXT NOT NULL           -- signed_up, created_workspace, invited_teammate, session, upgraded
);
CREATE INDEX ix_events_user ON events (user_id, event_name);
CREATE INDEX ix_events_name_ts ON events (event_name, event_ts);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def sql_text(name: str) -> str:
    return (SQL_DIR / f"{name}.sql").read_text(encoding="utf-8")


def run(conn: sqlite3.Connection, name: str) -> tuple[list[str], list[tuple]]:
    """Run sql/<name>.sql and return (column names, rows)."""
    cur = conn.execute(sql_text(name))
    columns = [d[0] for d in cur.description]
    return columns, cur.fetchall()
