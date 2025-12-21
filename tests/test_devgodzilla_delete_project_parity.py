import os

import pytest

from devgodzilla.db.database import PostgresDatabase, SQLiteDatabase


def _count_project_rows(db, table: str, project_id: int) -> int:
    allowed_tables = {
        "agent_assignments",
        "agent_overrides",
        "agent_assignment_settings",
    }
    if table not in allowed_tables:
        raise ValueError(f"Unexpected table name: {table}")
    placeholder = "?" if isinstance(db, SQLiteDatabase) else "%s"
    row = db._fetchone(
        f"SELECT COUNT(*) AS count FROM {table} WHERE project_id = {placeholder}",
        (project_id,),
    )
    if row is None:
        return 0
    if isinstance(row, dict):
        return int(row.get("count", 0))
    try:
        return int(row["count"])
    except Exception:
        return int(row[0])


def _setup_project_with_agent_rows(db) -> int:
    project = db.create_project(
        name="delete-project-parity",
        git_url="https://example.com/delete-project-parity.git",
        base_branch="main",
    )
    db.upsert_agent_assignment_settings(project.id, inherit_global=False)
    db.upsert_agent_assignment(
        project.id,
        "quality",
        {
            "agent_id": "agent-1",
            "enabled": True,
            "metadata": {"source": "test"},
        },
    )
    db.upsert_agent_override(project.id, "agent-1", {"temperature": 0.2})
    return project.id


def _assert_delete_project_cleans_agent_rows(db) -> None:
    project_id = _setup_project_with_agent_rows(db)

    assert _count_project_rows(db, "agent_assignments", project_id) == 1
    assert _count_project_rows(db, "agent_overrides", project_id) == 1
    assert _count_project_rows(db, "agent_assignment_settings", project_id) == 1

    db.delete_project(project_id)

    with pytest.raises(KeyError):
        db.get_project(project_id)

    assert _count_project_rows(db, "agent_assignments", project_id) == 0
    assert _count_project_rows(db, "agent_overrides", project_id) == 0
    assert _count_project_rows(db, "agent_assignment_settings", project_id) == 0


def test_delete_project_cleans_agent_rows_sqlite(tmp_path) -> None:
    db = SQLiteDatabase(tmp_path / "devgodzilla.sqlite")
    db.init_schema()
    _assert_delete_project_cleans_agent_rows(db)


@pytest.mark.skipif(
    not os.environ.get("DEVGODZILLA_TEST_DB_URL"),
    reason="DEVGODZILLA_TEST_DB_URL not set",
)
def test_delete_project_cleans_agent_rows_postgres() -> None:
    pytest.importorskip("psycopg")
    db = PostgresDatabase(os.environ["DEVGODZILLA_TEST_DB_URL"])
    db.init_schema()
    _assert_delete_project_cleans_agent_rows(db)
