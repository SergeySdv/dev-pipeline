import json
import os
import shutil

import pytest
from pathlib import Path
from unittest.mock import Mock

from devgodzilla.models.domain import SpecRunStatus
from devgodzilla.models.speckit import TaskStatus
from devgodzilla.services.specification import (
    SpecificationService,
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


def _skip_unless_real_agent():
    if os.environ.get("DEVGODZILLA_RUN_E2E_REAL_AGENT") != "1":
        pytest.skip("Set DEVGODZILLA_RUN_E2E_REAL_AGENT=1 to enable real-agent tests.")
    if shutil.which("opencode") is None:
        pytest.skip("opencode is required for real-agent tests.")


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


def _init_workspace(tmp_path):
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
def initialized_workspace(tmp_path):
    return _init_workspace(tmp_path)


@pytest.fixture
def service_context(monkeypatch):
    monkeypatch.setenv("DEVGODZILLA_SPECKIT_ENGINE_ID", "opencode")
    monkeypatch.setenv("DEVGODZILLA_DEFAULT_ENGINE_ID", "opencode")
    monkeypatch.setenv("DEVGODZILLA_OPENCODE_MODEL", os.environ.get("DEVGODZILLA_OPENCODE_MODEL", "zai-coding-plan/glm-5"))
    config = Mock()
    config.engine_defaults = {"planning": "opencode"}
    return ServiceContext(config=config)


@pytest.fixture
def service(service_context):
    return SpecificationService(service_context)


@pytest.mark.integration
class TestSpecKitClarifyStage:

    def test_clarify_success(self, service, initialized_workspace):
        _skip_unless_real_agent()

        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        result = service.run_clarify(
            str(initialized_workspace),
            spec_result.spec_path,
            entries=[{"question": "Q1", "answer": "A1"}],
        )
        assert result.success
        assert result.clarifications_added >= 0

        spec_content = Path(spec_result.spec_path).read_text()
        assert "Q1" in spec_content or "A1" in spec_content

    def test_clarify_missing_spec(self, service, initialized_workspace):
        _skip_unless_real_agent()

        result = service.run_clarify(
            str(initialized_workspace),
            str(initialized_workspace / "specs" / "nonexistent" / "spec.md"),
        )
        assert not result.success
        assert result.error is not None

    def test_clarify_with_notes(self, service, initialized_workspace):
        _skip_unless_real_agent()

        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        result = service.run_clarify(
            str(initialized_workspace),
            spec_result.spec_path,
            notes="Additional context for the spec",
        )
        assert result.success

        spec_content = Path(spec_result.spec_path).read_text()
        assert "Additional context" in spec_content


@pytest.mark.integration
class TestSpecKitChecklistStageRealAgent:

    def test_checklist_success(self, service, initialized_workspace):
        _skip_unless_real_agent()

        spec_result = service.run_specify(str(initialized_workspace), "Test feature with auth")
        assert spec_result.success

        result = service.run_checklist(
            str(initialized_workspace),
            spec_result.spec_path,
        )
        assert result.success
        assert result.checklist_path is not None
        checklist_file = Path(result.checklist_path)
        assert checklist_file.exists()
        content = checklist_file.read_text()
        assert len(content) > 10

    def test_checklist_agent_failure_on_missing_spec(self, service, initialized_workspace):
        _skip_unless_real_agent()

        result = service.run_checklist(
            str(initialized_workspace),
            str(initialized_workspace / "specs" / "nonexistent" / "spec.md"),
        )
        assert not result.success


@pytest.mark.integration
class TestSpecKitAnalyzeStageRealAgent:

    def test_analyze_success(self, service, initialized_workspace):
        _skip_unless_real_agent()

        spec_result = service.run_specify(str(initialized_workspace), "Test feature with database")
        assert spec_result.success

        result = service.run_analyze(
            str(initialized_workspace),
            spec_result.spec_path,
        )
        assert result.success
        assert result.report_path is not None
        report_file = Path(result.report_path)
        assert report_file.exists()
        content = report_file.read_text()
        assert "Analysis" in content or "Spec" in content or "analysis" in content

    def test_analyze_without_optional_plan_tasks(self, service, initialized_workspace):
        _skip_unless_real_agent()

        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        result = service.run_analyze(
            str(initialized_workspace),
            spec_result.spec_path,
            plan_path=None,
            tasks_path=None,
        )
        assert result.success
        content = Path(result.report_path).read_text()
        assert len(content) > 0


@pytest.mark.integration
class TestSpecKitImplementStage:

    def test_implement_success(self, service, initialized_workspace):
        _skip_unless_real_agent()

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
        _skip_unless_real_agent()

        spec_result = service.run_specify(str(initialized_workspace), "Test feature")
        assert spec_result.success

        result = service.run_implement(
            str(initialized_workspace),
            spec_result.spec_path,
        )
        assert result.success
        metadata = json.loads(Path(result.metadata_path).read_text())
        assert "run_id" in metadata
        assert metadata["status"] == "initialized"


@pytest.mark.integration
class TestSpecKitFullWorkflowChainRealAgent:

    def test_full_chain_statuses(self, service, workspace):
        _skip_unless_real_agent()

        init_result = service.init_project(str(workspace))
        assert init_result.success

        spec_result = service.run_specify(str(workspace), "Auth feature with JWT")
        assert spec_result.success
        assert Path(spec_result.spec_path).exists()
        assert Path(spec_result.spec_path).stat().st_size > 0

        plan_result = service.run_plan(str(workspace), spec_result.spec_path)
        assert plan_result.success
        assert Path(plan_result.plan_path).exists()
        assert Path(plan_result.plan_path).stat().st_size > 0

        tasks_result = service.run_tasks(str(workspace), plan_result.plan_path)
        assert tasks_result.success
        assert Path(tasks_result.tasks_path).exists()

        clarify_result = service.run_clarify(
            str(workspace),
            spec_result.spec_path,
            entries=[{"question": "Auth method?", "answer": "JWT"}],
        )
        assert clarify_result.success

        checklist_result = service.run_checklist(str(workspace), spec_result.spec_path)
        assert checklist_result.success
        assert Path(checklist_result.checklist_path).exists()
        checklist_content = Path(checklist_result.checklist_path).read_text()
        assert len(checklist_content) > 10

        analyze_result = service.run_analyze(str(workspace), spec_result.spec_path)
        assert analyze_result.success
        assert Path(analyze_result.report_path).exists()

        implement_result = service.run_implement(str(workspace), spec_result.spec_path)
        assert implement_result.success
        assert Path(implement_result.run_path).exists()
        metadata = json.loads(Path(implement_result.metadata_path).read_text())
        assert metadata["status"] == "initialized"
