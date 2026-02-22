import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from devgodzilla.models.domain import SpecRunStatus
from devgodzilla.models.speckit import TaskStatus
from devgodzilla.services.specification import (
    SpecificationService,
    ClarifyResult,
    ChecklistResult,
    AnalyzeResult,
    ImplementResult,
)
from devgodzilla.services.base import ServiceContext


class TestSpecRunStatusValues:

    ALL_STATUSES = [
        SpecRunStatus.SPECIFYING,
        SpecRunStatus.SPECIFIED,
        SpecRunStatus.PLANNING,
        SpecRunStatus.PLANNED,
        SpecRunStatus.TASKS,
        SpecRunStatus.CLARIFIED,
        SpecRunStatus.CHECKLISTED,
        SpecRunStatus.ANALYZED,
        SpecRunStatus.IMPLEMENTED,
        SpecRunStatus.FAILED,
        SpecRunStatus.CLEANED,
    ]

    def test_all_11_values_exist(self):
        assert len(self.ALL_STATUSES) == 11

    def test_all_values_are_unique(self):
        assert len(set(self.ALL_STATUSES)) == 11

    def test_all_values_are_nonempty_strings(self):
        for status in self.ALL_STATUSES:
            assert isinstance(status, str)
            assert len(status) > 0

    def test_status_string_values(self):
        assert SpecRunStatus.SPECIFYING == "specifying"
        assert SpecRunStatus.SPECIFIED == "specified"
        assert SpecRunStatus.PLANNING == "planning"
        assert SpecRunStatus.PLANNED == "planned"
        assert SpecRunStatus.TASKS == "tasks"
        assert SpecRunStatus.CLARIFIED == "clarified"
        assert SpecRunStatus.CHECKLISTED == "checklisted"
        assert SpecRunStatus.ANALYZED == "analyzed"
        assert SpecRunStatus.IMPLEMENTED == "implemented"
        assert SpecRunStatus.FAILED == "failed"
        assert SpecRunStatus.CLEANED == "cleaned"


class TestSpecKitTaskStatusEnum:

    ALL_VALUES = [
        TaskStatus.PENDING,
        TaskStatus.IN_PROGRESS,
        TaskStatus.COMPLETED,
        TaskStatus.BLOCKED,
        TaskStatus.SKIPPED,
    ]

    def test_all_5_values_exist(self):
        assert len(self.ALL_VALUES) == 5

    def test_all_values_are_unique(self):
        assert len(set(self.ALL_VALUES)) == 5

    def test_values_serialize_correctly(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.SKIPPED.value == "skipped"

    def test_enum_from_string(self):
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("in_progress") == TaskStatus.IN_PROGRESS
        assert TaskStatus("completed") == TaskStatus.COMPLETED
        assert TaskStatus("blocked") == TaskStatus.BLOCKED
        assert TaskStatus("skipped") == TaskStatus.SKIPPED


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


@pytest.fixture
def initialized_workspace(tmp_path):
    specify_dir = tmp_path / ".specify"
    specify_dir.mkdir()
    (specify_dir / "memory").mkdir()
    (specify_dir / "templates").mkdir()
    (tmp_path / "specs").mkdir()
    (specify_dir / "memory" / "constitution.md").write_text("# Test Constitution\n")
    (specify_dir / "templates" / "spec-template.md").write_text("# {{ title }}\n{{ description }}")
    (specify_dir / "templates" / "plan-template.md").write_text("# {{ title }}\n{{ description }}")
    (specify_dir / "templates" / "tasks-template.md").write_text("# {{ title }}\n- [ ] Task 1")
    (specify_dir / "templates" / "checklist-template.md").write_text("# {{ title }}\n- [ ] Check 1")
    return tmp_path


@pytest.fixture
def service_context(monkeypatch):
    monkeypatch.setenv("DEVGODZILLA_SPECKIT_ENGINE_ID", "dummy")
    config = Mock()
    config.engine_defaults = {"planning": "dummy"}
    return ServiceContext(config=config)


@pytest.fixture
def mock_db():
    db = Mock()
    mock_project = Mock()
    mock_project.id = 1
    mock_project.local_path = "/tmp/repo"
    mock_project.constitution_version = None
    mock_project.constitution_hash = None
    db.get_project.return_value = mock_project
    db.update_project.return_value = None
    return db


@pytest.fixture
def service(service_context):
    return SpecificationService(service_context)


class TestSpecKitClarifyStage:

    def test_clarify_success(self, service, initialized_workspace):
        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        result = service.run_clarify(
            str(initialized_workspace),
            spec_result.spec_path,
            entries=[{"question": "Q1", "answer": "A1"}],
        )
        assert result.success
        assert result.clarifications_added >= 0

    def test_clarify_missing_spec(self, service, initialized_workspace):
        result = service.run_clarify(
            str(initialized_workspace),
            str(initialized_workspace / "specs" / "nonexistent" / "spec.md"),
        )
        assert not result.success
        assert result.error is not None

    def test_clarify_with_notes(self, service, initialized_workspace):
        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        result = service.run_clarify(
            str(initialized_workspace),
            spec_result.spec_path,
            notes="Additional context for the spec",
        )
        assert result.success


class TestSpecKitChecklistStage:

    def test_checklist_success(self, service, initialized_workspace):
        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        with patch.object(service, "_run_speckit_agent") as mock_agent:
            mock_agent.return_value = Mock(success=True)
            result = service.run_checklist(
                str(initialized_workspace),
                spec_result.spec_path,
            )
            assert result.success
            assert result.checklist_path is not None
            assert Path(result.checklist_path).exists()

    def test_checklist_agent_failure(self, service, initialized_workspace):
        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        with patch.object(service, "_run_speckit_agent") as mock_agent:
            mock_agent.return_value = Mock(success=False, error="Agent failed")
            result = service.run_checklist(
                str(initialized_workspace),
                spec_result.spec_path,
            )
            assert not result.success
            assert "failed" in result.error.lower()


class TestSpecKitAnalyzeStage:

    def test_analyze_success(self, service, initialized_workspace):
        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        with patch.object(service, "_run_speckit_agent") as mock_agent:
            mock_agent.return_value = Mock(success=True)
            result = service.run_analyze(
                str(initialized_workspace),
                spec_result.spec_path,
            )
            assert result.success
            assert result.report_path is not None
            assert Path(result.report_path).exists()

    def test_analyze_without_optional_plan_tasks(self, service, initialized_workspace):
        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        with patch.object(service, "_run_speckit_agent") as mock_agent:
            mock_agent.return_value = Mock(success=True)
            result = service.run_analyze(
                str(initialized_workspace),
                spec_result.spec_path,
                plan_path=None,
                tasks_path=None,
            )
            assert result.success
            content = Path(result.report_path).read_text()
            assert "N/A" in content


class TestSpecKitImplementStage:

    def test_implement_success(self, service, initialized_workspace):
        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        result = service.run_implement(
            str(initialized_workspace),
            spec_result.spec_path,
        )
        assert result.success
        assert result.run_path is not None
        assert result.metadata_path is not None
        assert Path(result.run_path).exists()
        assert Path(result.metadata_path).exists()

    def test_implement_creates_metadata_json(self, service, initialized_workspace):
        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        result = service.run_implement(
            str(initialized_workspace),
            spec_result.spec_path,
        )
        assert result.success
        import json
        metadata = json.loads(Path(result.metadata_path).read_text())
        assert "run_id" in metadata
        assert metadata["status"] == "initialized"


class TestSpecKitFullWorkflowChain:

    def test_full_chain_statuses(self, service, workspace):
        init_result = service.init_project(str(workspace))
        assert init_result.success

        (workspace / ".specify" / "templates" / "checklist-template.md").write_text(
            "# {{ title }}\n- [ ] Check 1"
        )

        spec_result = service.run_specify(str(workspace), "Auth feature")
        assert spec_result.success

        plan_result = service.run_plan(str(workspace), spec_result.spec_path)
        assert plan_result.success

        tasks_result = service.run_tasks(str(workspace), plan_result.plan_path)
        assert tasks_result.success

        clarify_result = service.run_clarify(
            str(workspace),
            spec_result.spec_path,
            entries=[{"question": "Auth method?", "answer": "JWT"}],
        )
        assert clarify_result.success

        with patch.object(service, "_run_speckit_agent") as mock_agent:
            mock_agent.return_value = Mock(success=True)
            checklist_result = service.run_checklist(str(workspace), spec_result.spec_path)
            assert checklist_result.success

        with patch.object(service, "_run_speckit_agent") as mock_agent:
            mock_agent.return_value = Mock(success=True)
            analyze_result = service.run_analyze(str(workspace), spec_result.spec_path)
            assert analyze_result.success

        implement_result = service.run_implement(str(workspace), spec_result.spec_path)
        assert implement_result.success
