
import pytest
from unittest.mock import MagicMock

from tasksgodzilla.services.codemachine import CodeMachineService


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def service(mock_db):
    return CodeMachineService(db=mock_db)


def test_import_workspace_delegates_to_worker(service, mock_db, monkeypatch):
    mock_import = MagicMock()
    monkeypatch.setattr("tasksgodzilla.workers.codemachine_worker.import_codemachine_workspace", mock_import)

    service.import_workspace(
        project_id=1,
        protocol_run_id=100,
        workspace_path="/tmp/workspace",
        job_id="job-123"
    )

    mock_import.assert_called_once_with(
        1,
        100,
        "/tmp/workspace",
        mock_db,
    )
