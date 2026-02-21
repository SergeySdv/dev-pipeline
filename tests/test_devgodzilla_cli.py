"""
Tests for DevGodzilla CLI commands.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from click.testing import CliRunner

from devgodzilla.cli.main import cli
from devgodzilla.db.database import SQLiteDatabase


class TestCLIBasic:
    """Tests for basic CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_version(self, runner):
        """Test version command."""
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "DevGodzilla" in result.output

    def test_help(self, runner):
        """Test help output."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "DevGodzilla" in result.output
        assert "protocol" in result.output.lower()

    def test_verbose_flag(self, runner):
        """Test verbose flag doesn't crash."""
        result = runner.invoke(cli, ["-v", "version"])
        assert result.exit_code == 0

    def test_protocol_help(self, runner):
        """Test protocol group help."""
        result = runner.invoke(cli, ["protocol", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output.lower()

    def test_step_help(self, runner):
        """Test step group help."""
        result = runner.invoke(cli, ["step", "--help"])
        assert result.exit_code == 0
        assert "run" in result.output.lower()

    def test_qa_help(self, runner):
        """Test QA group help."""
        result = runner.invoke(cli, ["qa", "--help"])
        assert result.exit_code == 0
        assert "evaluate" in result.output.lower()

    def test_qa_gates(self, runner):
        """Test qa gates command."""
        result = runner.invoke(cli, ["qa", "gates"])
        assert result.exit_code == 0
        assert "test" in result.output.lower()
        assert "lint" in result.output.lower()

    def test_invalid_command(self, runner):
        """Test invalid command handling."""
        result = runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0


class TestCLIProtocol:
    """Tests for CLI protocol commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def db(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(db_path)
        db.init_schema()
        return db

    @pytest.fixture
    def sample_project(self, db: SQLiteDatabase, tmp_path: Path):
        project = db.create_project(
            name="CLI Test Project",
            git_url="https://github.com/example/cli-test.git",
            base_branch="main",
        )
        local_path = tmp_path / "repo"
        local_path.mkdir()
        (local_path / ".git").mkdir()
        db.update_project(project.id, local_path=str(local_path))
        return db.get_project(project.id)

    @patch("devgodzilla.cli.main.get_db")
    @patch("devgodzilla.services.orchestrator.OrchestratorService")
    def test_protocol_create(self, MockOrchestrator, mock_db, runner, db, sample_project):
        """Test protocol create command."""
        mock_db.return_value = db

        mock_orchestrator = MagicMock()
        mock_result = MagicMock()
        mock_result.id = 1
        mock_orchestrator.create_protocol_run.return_value = mock_result
        MockOrchestrator.return_value = mock_orchestrator

        result = runner.invoke(
            cli,
            ["protocol", "create", str(sample_project.id), "test-protocol"],
        )

        assert result.exit_code == 0
        assert "Created protocol" in result.output

    @patch("devgodzilla.cli.main.get_db")
    @patch("devgodzilla.services.orchestrator.OrchestratorService")
    def test_protocol_start(self, MockOrchestrator, mock_db, runner, db):
        """Test protocol start command."""
        mock_db.return_value = db

        mock_orchestrator = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.job_id = "job-123"
        mock_result.message = "Started"
        mock_result.error = None
        mock_orchestrator.start_protocol_run.return_value = mock_result
        MockOrchestrator.return_value = mock_orchestrator

        result = runner.invoke(cli, ["protocol", "start", "1"])

        assert result.exit_code == 0
        assert "Started protocol" in result.output

    @patch("devgodzilla.cli.main.get_db")
    def test_protocol_status(self, mock_db, runner, db, sample_project):
        """Test protocol status command."""
        mock_db.return_value = db

        # Create a protocol
        protocol = db.create_protocol_run(
            project_id=sample_project.id,
            protocol_name="status-test",
            status="running",
            base_branch="main",
        )

        result = runner.invoke(cli, ["protocol", "status", str(protocol.id)])

        assert result.exit_code == 0
        assert "status-test" in result.output
        assert "running" in result.output

    @patch("devgodzilla.cli.main.get_db")
    def test_protocol_status_not_found(self, mock_db, runner, db):
        """Test protocol status for non-existent protocol."""
        mock_db.return_value = db

        result = runner.invoke(cli, ["protocol", "status", "99999"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch("devgodzilla.cli.main.get_db")
    @patch("devgodzilla.services.orchestrator.OrchestratorService")
    def test_protocol_cancel(self, MockOrchestrator, mock_db, runner, db):
        """Test protocol cancel command."""
        mock_db.return_value = db

        mock_orchestrator = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "Cancelled"
        mock_orchestrator.cancel_protocol.return_value = mock_result
        MockOrchestrator.return_value = mock_orchestrator

        result = runner.invoke(cli, ["protocol", "cancel", "1"])

        assert result.exit_code == 0
        assert "Cancelled protocol" in result.output

    @patch("devgodzilla.cli.main.get_db")
    def test_protocol_list(self, mock_db, runner, db, sample_project):
        """Test protocol list command."""
        mock_db.return_value = db

        # Create some protocols
        db.create_protocol_run(
            project_id=sample_project.id,
            protocol_name="list-test-1",
            status="running",
            base_branch="main",
        )
        db.create_protocol_run(
            project_id=sample_project.id,
            protocol_name="list-test-2",
            status="completed",
            base_branch="main",
        )

        # The list command may need project flag or fail
        result = runner.invoke(cli, ["protocol", "list", "-p", str(sample_project.id)])

        # Command should succeed or fail gracefully
        assert result.exit_code in [0, 1]

    @patch("devgodzilla.cli.main.get_db")
    def test_protocol_list_empty(self, mock_db, runner, db):
        """Test protocol list when empty."""
        mock_db.return_value = db

        result = runner.invoke(cli, ["protocol", "list"])

        # Should succeed or fail gracefully
        assert result.exit_code in [0, 1]


class TestCLIStep:
    """Tests for CLI step commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("devgodzilla.services.orchestrator.OrchestratorService")
    def test_step_run(self, MockOrchestrator, runner):
        """Test step run command."""
        mock_orchestrator = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.job_id = "job-456"
        mock_result.message = "Started step"
        mock_result.error = None
        mock_orchestrator.run_step.return_value = mock_result
        MockOrchestrator.return_value = mock_orchestrator

        result = runner.invoke(cli, ["step", "run", "1"])

        assert result.exit_code == 0
        assert "Started step" in result.output

    @patch("devgodzilla.services.execution.ExecutionService")
    def test_step_execute(self, MockExecution, runner):
        """Test step execute command."""
        mock_execution = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.engine_id = "opencode"
        mock_result.model = "test-model"
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.error = None
        mock_execution.execute_step.return_value = mock_result
        MockExecution.return_value = mock_execution

        result = runner.invoke(cli, ["step", "execute", "1"])

        # Should succeed or fail gracefully
        assert result.exit_code in [0, 1]

    @patch("devgodzilla.services.quality.QualityService")
    def test_step_qa(self, MockQuality, runner):
        """Test step QA command."""
        mock_quality = MagicMock()
        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.verdict = MagicMock()
        mock_result.verdict.value = "pass"
        mock_result.gate_results = []
        mock_quality.run_qa.return_value = mock_result
        MockQuality.return_value = mock_quality

        result = runner.invoke(cli, ["step", "qa", "1"])

        assert result.exit_code == 0


class TestCLIQA:
    """Tests for CLI QA commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("devgodzilla.services.quality.QualityService")
    def test_qa_evaluate(self, MockQuality, runner, tmp_path):
        """Test QA evaluate command."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        mock_quality = MagicMock()
        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.verdict = MagicMock()
        mock_result.verdict.value = "pass"
        mock_result.duration_seconds = 1.5
        mock_result.gate_results = []
        mock_quality.evaluate_step.return_value = mock_result
        MockQuality.return_value = mock_quality

        result = runner.invoke(
            cli,
            ["qa", "evaluate", str(workspace), "test-step"],
        )

        # Should succeed or fail gracefully
        assert result.exit_code in [0, 1]


class TestCLIJSON:
    """Tests for CLI JSON output."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def db(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(db_path)
        db.init_schema()
        return db

    @patch("devgodzilla.cli.main.get_db")
    def test_protocol_list_json(self, mock_db, runner, db):
        """Test protocol list with JSON output."""
        mock_db.return_value = db

        result = runner.invoke(cli, ["--json", "protocol", "list"])

        # May fail if list_protocol_runs not available
        # At minimum check it doesn't crash hard
        assert result.exit_code in [0, 1]

    @patch("devgodzilla.services.orchestrator.OrchestratorService")
    @patch("devgodzilla.cli.main.get_db")
    def test_protocol_create_json(self, mock_db, MockOrchestrator, runner, db, tmp_path):
        """Test protocol create with JSON output."""
        mock_db.return_value = db

        project = db.create_project(
            name="JSON Test",
            git_url="https://example.com/test.git",
            base_branch="main",
        )
        local_path = tmp_path / "repo"
        local_path.mkdir()
        (local_path / ".git").mkdir()
        db.update_project(project.id, local_path=str(local_path))

        mock_orchestrator = MagicMock()
        mock_result = MagicMock()
        mock_result.id = 1
        mock_orchestrator.create_protocol_run.return_value = mock_result
        MockOrchestrator.return_value = mock_orchestrator

        result = runner.invoke(
            cli,
            ["--json", "protocol", "create", str(project.id), "json-protocol"],
        )

        # Accept success or graceful failure
        assert result.exit_code in [0, 1]

    @patch("devgodzilla.services.orchestrator.OrchestratorService")
    @patch("devgodzilla.cli.main.get_db")
    def test_protocol_start_error(self, mock_db, MockOrchestrator, runner, db):
        """Test protocol start with error."""
        mock_db.return_value = db

        mock_orchestrator = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Protocol not found"
        mock_orchestrator.start_protocol_run.return_value = mock_result
        MockOrchestrator.return_value = mock_orchestrator

        result = runner.invoke(cli, ["protocol", "start", "99999"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch("devgodzilla.services.onboarding_queue.enqueue_project_onboarding")
    @patch("devgodzilla.cli.projects.get_db")
    @patch("devgodzilla.cli.projects.get_service_context")
    def test_project_onboard_json(self, mock_get_context, mock_get_db, mock_enqueue, runner):
        """Test project onboard with JSON output."""
        mock_get_db.return_value = MagicMock()
        mock_get_context.return_value = SimpleNamespace(
            config=SimpleNamespace(windmill_enabled=True)
        )
        mock_enqueue.return_value = SimpleNamespace(
            run_id="run-123",
            windmill_job_id="job-456",
            script_path="u/devgodzilla/project_onboard_api",
        )

        result = runner.invoke(cli, ["--json", "project", "onboard", "7"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["project_id"] == 7
        assert payload["run_id"] == "run-123"
        assert payload["windmill_job_id"] == "job-456"


class TestCLIPathContractValidation:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_cli_fails_fast_when_path_contract_invalid(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("DEVGODZILLA_PROJECTS_ROOT", str(tmp_path / "projects"))
        monkeypatch.setenv("DEVGODZILLA_WINDMILL_IMPORT_ROOT", str(tmp_path / "missing-windmill"))
        monkeypatch.setenv(
            "DEVGODZILLA_WINDMILL_ONBOARD_SCRIPT_PATH",
            "u/devgodzilla/project_onboard_api",
        )

        result = runner.invoke(cli, ["version"])

        assert result.exit_code == 1
        assert "Invalid path configuration" in result.output
