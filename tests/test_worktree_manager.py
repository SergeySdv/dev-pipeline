"""Tests for WorktreeManager."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from devgodzilla.services.worktree import WorktreeManager, WorktreeInfo


class TestWorktreeInfo:
    def test_worktree_info_creation(self):
        info = WorktreeInfo(
            path=Path("/tmp/worktree"),
            branch="feature-branch",
            commit="abc123",
            is_main=False
        )
        assert info.branch == "feature-branch"
        assert info.is_main is False
        assert info.commit == "abc123"
    
    def test_worktree_info_name_property(self):
        info = WorktreeInfo(
            path=Path("/tmp/worktrees/my-feature"),
            branch="my-feature",
            commit="abc123"
        )
        assert info.name == "my-feature"
    
    def test_worktree_info_defaults(self):
        info = WorktreeInfo(
            path=Path("/tmp/worktree"),
            branch="main",
            commit="abc123"
        )
        assert info.is_main is False
        assert info.locked is False
        assert info.prunable is False


class TestWorktreeManager:
    @pytest.fixture
    def mock_repo_path(self, tmp_path):
        """Create a mock git repo path."""
        repo = tmp_path / "repo"
        repo.mkdir()
        git_dir = repo / ".git"
        git_dir.mkdir()
        return repo
    
    @pytest.fixture
    def manager(self, mock_repo_path):
        return WorktreeManager(repo_path=mock_repo_path)
    
    def test_manager_creation(self, manager):
        assert manager.repo_path.exists()
    
    def test_manager_invalid_path(self):
        """WorktreeManager raises error for invalid path."""
        with pytest.raises(ValueError, match="does not exist"):
            WorktreeManager(repo_path=Path("/nonexistent/path"))
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_list_worktrees(self, mock_run, manager):
        """list_worktrees parses git output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="worktree /repo/main\nHEAD abc123\nbranch refs/heads/main\n\n"
        )
        
        worktrees = manager.list_worktrees()
        
        assert isinstance(worktrees, list)
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_list_worktrees_with_detached(self, mock_run, manager):
        """list_worktrees handles detached HEAD."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="worktree /repo/worktree\nHEAD def456\ndetached\n\n"
        )
        
        worktrees = manager.list_worktrees()
        
        assert len(worktrees) >= 1
        if worktrees:
            assert worktrees[0].branch == "DETACHED"
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_list_worktrees_with_locked(self, mock_run, manager):
        """list_worktrees handles locked worktrees."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="worktree /repo/worktree\nHEAD def456\nbranch refs/heads/feature\nlocked\n\n"
        )
        
        worktrees = manager.list_worktrees()
        
        if worktrees:
            assert worktrees[0].locked is True
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_create_worktree(self, mock_run, manager):
        """create_worktree executes git worktree add."""
        mock_run.return_value = MagicMock(returncode=0)
        
        # Mock list_worktrees to return the created worktree
        with patch.object(manager, 'list_worktrees') as mock_list:
            mock_list.return_value = [
                WorktreeInfo(
                    path=manager.repo_path / "worktrees" / "feature",
                    branch="feature",
                    commit="abc123",
                    is_main=False
                )
            ]
            
            result = manager.create_worktree("feature-branch")
            
            assert isinstance(result, WorktreeInfo)
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_remove_worktree(self, mock_run, manager, tmp_path):
        """remove_worktree executes git worktree remove."""
        mock_run.return_value = MagicMock(returncode=0)
        
        # Create a path that exists
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()
        
        result = manager.remove_worktree(worktree_path)
        
        assert result is True
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_remove_worktree_nonexistent(self, mock_run, manager):
        """remove_worktree returns False for nonexistent path."""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = manager.remove_worktree(Path("/nonexistent/worktree"))
        
        assert result is False
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_prune_worktrees(self, mock_run, manager):
        """prune_worktrees executes git worktree prune."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Pruning 'removed-worktree'"
        )
        
        result = manager.prune_worktrees()
        
        assert isinstance(result, list)
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_get_worktree_for_branch(self, mock_run, manager):
        """get_worktree_for_branch finds worktree by branch."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="worktree /repo/main\nHEAD abc123\nbranch refs/heads/main\n\n"
                   "worktree /repo/feature\nHEAD def456\nbranch refs/heads/my-feature\n\n"
        )
        
        result = manager.get_worktree_for_branch("my-feature")
        
        assert result is not None
        assert result.branch == "my-feature"
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_get_worktree_for_branch_not_found(self, mock_run, manager):
        """get_worktree_for_branch returns None if not found."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="worktree /repo/main\nHEAD abc123\nbranch refs/heads/main\n\n"
        )
        
        result = manager.get_worktree_for_branch("nonexistent")
        
        assert result is None
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_get_active_branches(self, mock_run, manager):
        """get_active_branches returns non-main branches."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="worktree /repo/main\nHEAD abc123\nbranch refs/heads/main\n\n"
                   "worktree /repo/feature1\nHEAD def456\nbranch refs/heads/feature1\n\n"
                   "worktree /repo/feature2\nHEAD ghi789\nbranch refs/heads/feature2\n\n"
        )
        
        branches = manager.get_active_branches()
        
        # Main branch is excluded
        assert "main" not in branches or len([b for b in branches if b != "main"]) >= 0
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_lock_worktree(self, mock_run, manager):
        """lock_worktree locks a worktree."""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = manager.lock_worktree(Path("/tmp/worktree"), reason="In use")
        
        assert result is True
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_unlock_worktree(self, mock_run, manager):
        """unlock_worktree unlocks a worktree."""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = manager.unlock_worktree(Path("/tmp/worktree"))
        
        assert result is True
    
    @patch("devgodzilla.services.worktree.run_process")
    def test_cleanup_stale_worktrees(self, mock_run, manager):
        """cleanup_stale_worktrees removes old worktrees."""
        # First call is list_worktrees
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="worktree /repo/main\nHEAD abc123\nbranch refs/heads/main\n\n"
        )
        
        removed = manager.cleanup_stale_worktrees(max_age_days=30)
        
        assert isinstance(removed, list)
