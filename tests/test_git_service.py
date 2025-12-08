
import pytest
from pathlib import Path
from unittest.mock import MagicMock, call

from tasksgodzilla.services.git import GitService
from tasksgodzilla.domain import ProtocolRun, ProtocolStatus, Project


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.append_event = MagicMock()
    db.update_protocol_status = MagicMock()
    return db


@pytest.fixture
def git_service(mock_db):
    return GitService(db=mock_db)


@pytest.fixture
def mock_project():
    return Project(
        id=1,
        name="test-project",
        git_url="git@github.com:test/repo.git",
        local_path=None,
        default_models={},
        ci_provider="github",
        created_at="now",
        base_branch="main",
        secrets={},
        updated_at="now",
    )


@pytest.fixture
def mock_run():
    return ProtocolRun(
        id=100,
        project_id=1,
        protocol_name="protocol-123-task",
        protocol_root="/tmp/protocol",
        template_config={},
        base_branch="main",
        status=ProtocolStatus.PENDING,
        worktree_path=None,
        description="test run",
        template_source="none",
        created_at="now",
        updated_at="now",
    )


def test_get_branch_name_single_worktree(git_service, monkeypatch):
    monkeypatch.setattr("tasksgodzilla.services.git.SINGLE_WORKTREE", True)
    monkeypatch.setattr("tasksgodzilla.services.git.DEFAULT_WORKTREE_BRANCH", "shared-branch")
    assert git_service.get_branch_name("whatever") == "shared-branch"


def test_get_branch_name_multi_worktree(git_service, monkeypatch):
    monkeypatch.setattr("tasksgodzilla.services.git.SINGLE_WORKTREE", False)
    assert git_service.get_branch_name("protocol-abc") == "protocol-abc"


def test_get_worktree_path(git_service, monkeypatch):
    monkeypatch.setattr("tasksgodzilla.services.git.SINGLE_WORKTREE", False)
    repo_root = Path("/tmp/repo")
    path, branch = git_service.get_worktree_path(repo_root, "protocol-abc")
    assert branch == "protocol-abc"
    assert path == Path("/tmp/worktrees/protocol-abc")


def test_ensure_repo_or_block_exists(git_service, mock_project, mock_run, monkeypatch):
    mock_resolve = MagicMock(return_value=Path("/tmp/repo"))
    monkeypatch.setattr("tasksgodzilla.services.git.resolve_project_repo_path", mock_resolve)
    monkeypatch.setattr("pathlib.Path.exists", lambda s: True)

    path = git_service.ensure_repo_or_block(mock_project, mock_run)
    assert path == Path("/tmp/repo")
    mock_resolve.assert_called_once()
    git_service.db.update_protocol_status.assert_not_called()


def test_ensure_repo_or_block_missing_blocks(git_service, mock_project, mock_run, monkeypatch):
    mock_resolve = MagicMock(side_effect=FileNotFoundError("not found"))
    monkeypatch.setattr("tasksgodzilla.services.git.resolve_project_repo_path", mock_resolve)

    path = git_service.ensure_repo_or_block(mock_project, mock_run)
    assert path is None
    git_service.db.update_protocol_status.assert_called_with(mock_run.id, ProtocolStatus.BLOCKED)
    git_service.db.append_event.assert_called()


def test_ensure_worktree_creates_if_missing(git_service, monkeypatch):
    mock_run_process = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.git.run_process", mock_run_process)
    monkeypatch.setattr("tasksgodzilla.services.git.SINGLE_WORKTREE", False)
    
    # Mock Path.exists to return False then True
    repo_root = Path("/tmp/repo")
    
    # We need to mock the Path object used inside the method
    with monkeypatch.context() as m:
        m.setattr("pathlib.Path.exists", lambda self: False)
        path = git_service.ensure_worktree(
            repo_root, "protocol-abc", "main", protocol_run_id=100
        )
        # Verify run_process called with correct args
        mock_run_process.assert_called_once()
        cmd = mock_run_process.call_args[0][0]
        assert "git" in cmd
        assert "worktree" in cmd
        assert "add" in cmd
        assert "protocol-abc" in cmd  # branch name
        assert str(path) in cmd


def test_push_and_open_pr_success(git_service, monkeypatch):
    mock_run_process = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.git.run_process", mock_run_process)
    # Mock _remote_branch_exists
    git_service._remote_branch_exists = MagicMock(return_value=False)
    # Mock _create_pr_if_possible
    git_service._create_pr_if_possible = MagicMock(return_value=True)

    result = git_service.push_and_open_pr(
        Path("/tmp/worktree"), "protocol-abc", "main"
    )
    assert result is True
    # Should attempt commit and push
    assert mock_run_process.call_count >= 2


def test_push_and_open_pr_pushed_but_pr_failed(git_service, monkeypatch):
    mock_run_process = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.git.run_process", mock_run_process)
    git_service._remote_branch_exists = MagicMock(return_value=False)
    # PR creation fails/returns False
    git_service._create_pr_if_possible = MagicMock(return_value=False)

    result = git_service.push_and_open_pr(
        Path("/tmp/worktree"), "protocol-abc", "main"
    )
    # It returns True because push succeeded (implied by execution flow reaching return)
    assert result is True


def test_trigger_ci(git_service, monkeypatch):
    mock_trigger = MagicMock(return_value=True)
    monkeypatch.setattr("tasksgodzilla.services.git.trigger_ci", mock_trigger)

    result = git_service.trigger_ci(
        Path("/tmp/repo"), "branch", "github"
    )
    assert result is True
    mock_trigger.assert_called_with("github", Path("/tmp/repo"), "branch")
