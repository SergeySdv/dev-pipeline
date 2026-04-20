from __future__ import annotations

import sqlite3
from pathlib import Path

from devgodzilla.db.database import PostgresDatabase, SQLiteDatabase


def test_sqlite_init_schema_backfills_protocol_linked_sprint_column(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.sqlite"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            git_url TEXT NOT NULL,
            base_branch TEXT NOT NULL
        );
        CREATE TABLE sprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id),
            name TEXT NOT NULL
        );
        CREATE TABLE protocol_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id),
            protocol_name TEXT NOT NULL,
            status TEXT NOT NULL,
            base_branch TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()

    db = SQLiteDatabase(db_path)
    db.init_schema()

    with sqlite3.connect(db_path) as check:
        columns = {row[1] for row in check.execute("PRAGMA table_info(protocol_runs)").fetchall()}
    assert "linked_sprint_id" in columns


def test_postgres_backfill_adds_linked_sprint_column_only_when_missing() -> None:
    class FakeCursor:
        def __init__(self, exists: bool) -> None:
            self.exists = exists
            self.executed: list[str] = []

        def execute(self, sql: str) -> None:
            self.executed.append(sql.strip())

        def fetchone(self):
            return {"exists": 1} if self.exists else None

    missing = FakeCursor(exists=False)
    PostgresDatabase._ensure_protocol_runs_linked_sprint_column(missing)
    assert any("ALTER TABLE protocol_runs ADD COLUMN linked_sprint_id" in sql for sql in missing.executed)

    present = FakeCursor(exists=True)
    PostgresDatabase._ensure_protocol_runs_linked_sprint_column(present)
    assert not any("ALTER TABLE protocol_runs ADD COLUMN linked_sprint_id" in sql for sql in present.executed)
