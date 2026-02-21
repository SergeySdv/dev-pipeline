import sys
from pathlib import Path

import pytest

# Ensure repository root is on sys.path so in-tree packages and demo modules import cleanly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _default_sqlite_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Prevent .env-provided Postgres URLs from leaking into SQLite-based tests.
    monkeypatch.setenv("DEVGODZILLA_DB_URL", "")
