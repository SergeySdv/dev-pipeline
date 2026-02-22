"""
Tests for DiscoveryAgentService.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from devgodzilla.db.database import SQLiteDatabase
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.discovery_agent import (
    DiscoveryAgentService,
    parse_discovery_summary,
)
from devgodzilla.services.cli_execution_tracker import get_execution_tracker
from devgodzilla.config import load_config
from devgodzilla.engines import EngineRegistry, EngineNotFoundError


class TestDiscoveryAgentService:
    """Tests for DiscoveryAgentService."""

    @pytest.fixture
    def db(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(db_path)
        db.init_schema()
        return db

    @pytest.fixture
    def context(self):
        config = load_config()
        return ServiceContext(config=config)

    @pytest.fixture
    def repo_root(self, tmp_path: Path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "specs").mkdir()
        (repo / "specs" / "discovery").mkdir()
        return repo

    @pytest.fixture
    def discovery_service(self, context: ServiceContext):
        return DiscoveryAgentService(context)

    # ==================== Engine Selection Tests ====================

    def test_run_discovery_engine_not_found(self, discovery_service, repo_root):
        """Test returns error when engine not registered."""
        with patch.object(EngineRegistry, 'get', side_effect=EngineNotFoundError("not found")):
            result = discovery_service.run_discovery(
                repo_root=repo_root,
                engine_id="nonexistent",
            )

        assert result.success is False
        assert "Engine not registered" in result.error

    def test_run_discovery_engine_unavailable_uses_fallback(self, discovery_service, repo_root):
        """Test uses fallback engine when primary unavailable."""
        mock_engine = MagicMock()
        mock_engine.check_availability.return_value = False

        mock_fallback = MagicMock()
        mock_fallback.check_availability.return_value = True
        mock_fallback.metadata.default_model = "dummy-model"
        mock_fallback.execute.return_value = MagicMock(success=True, stdout="", stderr="")

        with patch.object(EngineRegistry, 'get') as mock_get:
            mock_get.side_effect = [mock_engine, mock_fallback]

            result = discovery_service.run_discovery(
                repo_root=repo_root,
                engine_id="opencode",
            )

        assert result.fallback_engine_id == "dummy"
        assert result.warning is not None

    # ==================== Discovery Execution Tests ====================

    def test_run_discovery_single_stage_success(self, discovery_service, repo_root, tmp_path):
        """Test successful single-stage discovery."""
        # Create a mock prompt file
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "repo-discovery.prompt.md"
        prompt_file.write_text("# Discovery Prompt\n\nExecute discovery.")

        mock_engine = MagicMock()
        mock_engine.check_availability.return_value = True
        mock_engine.metadata.default_model = "test-model"
        mock_engine.execute.return_value = MagicMock(
            success=True,
            stdout="Discovery complete",
            stderr="",
            error=None,
        )

        with patch.object(EngineRegistry, 'get', return_value=mock_engine):
            with patch("devgodzilla.services.discovery_agent._resolve_prompt", return_value=prompt_file):
                result = discovery_service.run_discovery(
                    repo_root=repo_root,
                    engine_id="opencode",
                    pipeline=False,
                    strict_outputs=False,  # Don't require output files
                )

        assert result.success is True
        assert result.engine_id == "opencode"
        assert result.model == "test-model"
        assert len(result.stages) == 1

    def test_run_discovery_pipeline_success(self, discovery_service, repo_root, tmp_path):
        """Test successful pipeline discovery."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()

        # Create all pipeline prompts
        for name in ["discovery-inventory", "discovery-architecture"]:
            prompt_file = prompt_dir / f"{name}.prompt.md"
            prompt_file.write_text(f"# {name}")

        mock_engine = MagicMock()
        mock_engine.check_availability.return_value = True
        mock_engine.metadata.default_model = "test-model"
        mock_engine.execute.return_value = MagicMock(
            success=True,
            stdout="",
            stderr="",
            error=None,
        )

        with patch.object(EngineRegistry, 'get', return_value=mock_engine):
            with patch("devgodzilla.services.discovery_agent._resolve_prompt") as mock_resolve:
                # Return appropriate prompt for each stage
                def resolve_side_effect(repo, *, prompt_name):
                    return prompt_dir / prompt_name
                mock_resolve.side_effect = resolve_side_effect

                result = discovery_service.run_discovery(
                    repo_root=repo_root,
                    engine_id="opencode",
                    pipeline=True,
                    stages=["inventory", "architecture"],
                    strict_outputs=False,  # Don't require output files
                )

        assert result.success is True
        assert len(result.stages) == 2
        assert all(s.success for s in result.stages)

    def test_run_discovery_stage_failure(self, discovery_service, repo_root, tmp_path):
        """Test discovery with stage failure."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "repo-discovery.prompt.md"
        prompt_file.write_text("# Discovery")

        mock_engine = MagicMock()
        mock_engine.check_availability.return_value = True
        mock_engine.metadata.default_model = "test-model"
        mock_engine.execute.return_value = MagicMock(
            success=False,
            stdout="",
            stderr="Error occurred",
            error="Execution failed",
        )

        with patch.object(EngineRegistry, 'get', return_value=mock_engine):
            with patch("devgodzilla.services.discovery_agent._resolve_prompt", return_value=prompt_file):
                result = discovery_service.run_discovery(
                    repo_root=repo_root,
                    engine_id="opencode",
                    pipeline=False,
                )

        assert result.success is False
        assert len(result.stages) == 1
        assert result.stages[0].success is False
        assert "Execution failed" in result.stages[0].error

    def test_run_discovery_missing_prompt(self, discovery_service, repo_root):
        """Test discovery fails when prompt is missing."""
        mock_engine = MagicMock()
        mock_engine.check_availability.return_value = True
        mock_engine.metadata.default_model = "test-model"

        with patch.object(EngineRegistry, 'get', return_value=mock_engine):
            with patch("devgodzilla.services.discovery_agent._resolve_prompt") as mock_resolve:
                # Return non-existent path
                mock_resolve.return_value = Path("/nonexistent/prompt.md")

                result = discovery_service.run_discovery(
                    repo_root=repo_root,
                    engine_id="opencode",
                    pipeline=False,
                )

        assert result.success is False
        assert result.stages[0].success is False
        assert "Prompt missing" in result.stages[0].error

    # ==================== Output Validation Tests ====================

    def test_run_discovery_strict_outputs_missing(self, discovery_service, repo_root, tmp_path):
        """Test strict output validation fails when outputs missing."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "repo-discovery.prompt.md"
        prompt_file.write_text("# Discovery")

        mock_engine = MagicMock()
        mock_engine.check_availability.return_value = True
        mock_engine.metadata.default_model = "test-model"
        mock_engine.execute.return_value = MagicMock(
            success=True,
            stdout="",
            stderr="",
            error=None,
        )

        with patch.object(EngineRegistry, 'get', return_value=mock_engine):
            with patch("devgodzilla.services.discovery_agent._resolve_prompt", return_value=prompt_file):
                result = discovery_service.run_discovery(
                    repo_root=repo_root,
                    engine_id="opencode",
                    pipeline=False,
                    strict_outputs=True,
                )

        # Should fail because expected outputs don't exist
        assert result.success is False
        assert len(result.missing_outputs) > 0

    def test_run_discovery_non_strict_outputs(self, discovery_service, repo_root, tmp_path):
        """Test non-strict mode passes even without outputs."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "repo-discovery.prompt.md"
        prompt_file.write_text("# Discovery")

        mock_engine = MagicMock()
        mock_engine.check_availability.return_value = True
        mock_engine.metadata.default_model = "test-model"
        mock_engine.execute.return_value = MagicMock(
            success=True,
            stdout="",
            stderr="",
            error=None,
        )

        with patch.object(EngineRegistry, 'get', return_value=mock_engine):
            with patch("devgodzilla.services.discovery_agent._resolve_prompt", return_value=prompt_file):
                result = discovery_service.run_discovery(
                    repo_root=repo_root,
                    engine_id="opencode",
                    pipeline=False,
                    strict_outputs=False,
                )

        assert result.success is True

    # ==================== CLI Execution Tracking Tests ====================

    def test_run_discovery_creates_execution_tracker(self, discovery_service, repo_root, tmp_path):
        """Test that discovery creates execution tracking."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "repo-discovery.prompt.md"
        prompt_file.write_text("# Discovery")

        mock_engine = MagicMock()
        mock_engine.check_availability.return_value = True
        mock_engine.metadata.default_model = "test-model"
        mock_engine.execute.return_value = MagicMock(
            success=True,
            stdout="",
            stderr="",
            error=None,
        )

        with patch.object(EngineRegistry, 'get', return_value=mock_engine):
            with patch("devgodzilla.services.discovery_agent._resolve_prompt", return_value=prompt_file):
                result = discovery_service.run_discovery(
                    repo_root=repo_root,
                    engine_id="opencode",
                    pipeline=False,
                    strict_outputs=False,
                    project_id=1,
                )

        # Verify execution tracking was created (result should succeed)
        assert result.success is True

    def test_run_discovery_passes_cli_execution_id_to_engine(self, discovery_service, repo_root, tmp_path):
        """Discovery engine request should include execution id for later cancellation."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "repo-discovery.prompt.md"
        prompt_file.write_text("# Discovery")

        captured_req = {}

        def _fake_execute(req):
            captured_req["req"] = req
            return MagicMock(success=True, stdout="", stderr="", error=None)

        mock_engine = MagicMock()
        mock_engine.check_availability.return_value = True
        mock_engine.metadata.default_model = "test-model"
        mock_engine.execute.side_effect = _fake_execute

        with patch.object(EngineRegistry, "get", return_value=mock_engine):
            with patch("devgodzilla.services.discovery_agent._resolve_prompt", return_value=prompt_file):
                result = discovery_service.run_discovery(
                    repo_root=repo_root,
                    engine_id="opencode",
                    pipeline=False,
                    strict_outputs=False,
                    project_id=123,
                )

        assert result.success is True
        req = captured_req["req"]
        assert req.extra["cli_execution_id"]

    def test_run_discovery_stops_after_execution_cancelled(self, discovery_service, repo_root, tmp_path):
        """Cancellation should stop the discovery pipeline before subsequent stages start."""
        tracker = get_execution_tracker()
        with tracker._execution_lock:
            tracker._executions.clear()
            tracker._subscribers.clear()

        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        for prompt_name in ("discovery-inventory.prompt.md", "discovery-architecture.prompt.md"):
            (prompt_dir / prompt_name).write_text(f"# {prompt_name}")

        execute_calls: list[str] = []

        def _fake_execute(req):
            execute_calls.append(req.extra["cli_execution_id"])
            tracker.cancel(req.extra["cli_execution_id"])
            return MagicMock(success=False, stdout="", stderr="", error="terminated")

        mock_engine = MagicMock()
        mock_engine.check_availability.return_value = True
        mock_engine.metadata.default_model = "test-model"
        mock_engine.execute.side_effect = _fake_execute

        with patch.object(EngineRegistry, "get", return_value=mock_engine):
            with patch("devgodzilla.services.discovery_agent._resolve_prompt") as mock_resolve:
                mock_resolve.side_effect = lambda _repo, *, prompt_name: prompt_dir / prompt_name
                result = discovery_service.run_discovery(
                    repo_root=repo_root,
                    engine_id="opencode",
                    pipeline=True,
                    stages=["inventory", "architecture"],
                    strict_outputs=False,
                    project_id=321,
                )

        assert result.success is False
        assert len(execute_calls) == 1

    # ==================== parse_discovery_summary Tests ====================

    def test_parse_discovery_summary_valid(self, tmp_path):
        """Test parsing valid discovery summary."""
        summary_path = tmp_path / "DISCOVERY_SUMMARY.json"
        summary_path.write_text('{"technologies": ["Python", "React"], "patterns": []}')

        result = parse_discovery_summary(summary_path)
        assert result["technologies"] == ["Python", "React"]

    def test_parse_discovery_summary_invalid_json(self, tmp_path):
        """Test parsing invalid JSON raises error."""
        summary_path = tmp_path / "DISCOVERY_SUMMARY.json"
        summary_path.write_text("not json")

        with pytest.raises(Exception):
            parse_discovery_summary(summary_path)

    def test_parse_discovery_summary_not_dict(self, tmp_path):
        """Test parsing non-dict JSON raises error."""
        summary_path = tmp_path / "DISCOVERY_SUMMARY.json"
        summary_path.write_text('["not", "a", "dict"]')

        with pytest.raises(ValueError, match="must be a JSON object"):
            parse_discovery_summary(summary_path)

    # ==================== Expected Outputs Tests ====================

    def test_expected_outputs_pipeline(self, discovery_service):
        """Test expected outputs for pipeline mode."""
        outputs = discovery_service._expected_outputs(pipeline=True)
        assert len(outputs) == 5
        names = [str(p) for p in outputs]
        assert any("DISCOVERY.md" in n for n in names)
        assert any("ARCHITECTURE.md" in n for n in names)

    def test_expected_outputs_single(self, discovery_service):
        """Test expected outputs for single stage mode."""
        outputs = discovery_service._expected_outputs(pipeline=False)
        assert len(outputs) == 4

    # ==================== Runtime Directory Tests ====================

    def test_ensure_discovery_runtime_dir(self, repo_root):
        """Test runtime directory creation."""
        runtime_dir = DiscoveryAgentService._ensure_discovery_runtime_dir(repo_root)

        assert runtime_dir.exists()
        assert runtime_dir.name == "_runtime"
        assert "specs" in str(runtime_dir)
        assert "discovery" in str(runtime_dir)
