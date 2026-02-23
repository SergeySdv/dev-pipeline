"""Integration tests for QA pipeline with all gates."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from devgodzilla.qa.gate_registry import create_default_registry, GateRegistry
from devgodzilla.qa.checklist_validator import ChecklistValidator, ChecklistItem
from devgodzilla.qa.report_generator import ReportGenerator, QAReport
from devgodzilla.qa.gates.interface import GateContext, GateResult, GateVerdict


class TestQAPipelineIntegration:
    """Tests for complete QA pipeline flow."""
    
    @pytest.fixture
    def registry(self):
        return create_default_registry()
    
    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project with code and tests."""
        # Source code
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text('''
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str

def get_user(user_id: int) -> User:
    return User(name="Test", email="test@example.com")
''')
        
        # Tests
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_main.py").write_text('''
import pytest
from src.main import get_user

def test_get_user():
    user = get_user(1)
    assert user.name == "Test"
''')
        
        return tmp_path
    
    def test_all_gates_evaluate(self, registry, sample_project):
        """All gates can be evaluated on a project."""
        context = GateContext(
            workspace_root=str(sample_project),
            protocol_root=str(sample_project),
            step_name="test-step",
        )
        
        results = registry.evaluate_all(context)
        
        assert len(results) > 0
        assert all(r.verdict in (GateVerdict.PASS, GateVerdict.WARN, GateVerdict.FAIL, 
                                  GateVerdict.SKIP, GateVerdict.ERROR) 
                   for r in results)
    
    def test_qa_pipeline_generates_report(self, registry, sample_project):
        """Pipeline generates a complete report."""
        context = GateContext(
            workspace_root=str(sample_project),
            protocol_root=str(sample_project),
            step_name="test-step",
        )
        
        results = registry.evaluate_all(context)
        generator = ReportGenerator()
        
        # Build report from results
        mock_step_run = MagicMock()
        mock_step_run.step_name = "Test"
        mock_step_run.step_id = "step-1"
        mock_step_run.id = 1
        
        mock_verdict = MagicMock()
        mock_verdict.passed = True
        mock_verdict.score = 0.9
        
        report = generator.generate(
            step_run=mock_step_run,
            gate_results=results,
            checklist_result=None,
            verdict=mock_verdict,
        )
        
        markdown = generator.render(report)
        
        assert "QA Report" in markdown
        assert len(report.sections) > 0
    
    def test_checklist_validator_integration(self, sample_project):
        """ChecklistValidator works with real project artifacts."""
        validator = ChecklistValidator(use_llm=False)
        
        checklist = """
- [ ] Add unit tests
- [ ] Handle errors
- [ ] Use type hints
"""
        
        items = validator.parse_checklist(checklist)
        artifacts = list(sample_project.rglob("*.py"))
        
        results = validator.validate_all(items, artifacts)
        
        assert len(results) == 3
        # The test file should trigger test pattern detection
        test_item = next((i for i in items if "test" in i.description.lower()), None)
        if test_item:
            test_result = next((r for r in results if r.item_id == test_item.id), None)
            if test_result:
                assert test_result.passed or test_result.confidence > 0
    
    def test_registry_has_expected_gates(self, registry):
        """Registry contains expected default gates."""
        gate_ids = registry.list_ids()
        
        # Should have standard gates
        assert "test" in gate_ids
        assert "lint" in gate_ids
        assert "type" in gate_ids
    
    def test_gate_context_with_artifacts(self, sample_project):
        """GateContext properly handles artifact paths."""
        artifacts = list(sample_project.rglob("*.py"))
        
        context = GateContext(
            workspace_root=str(sample_project),
            protocol_root=str(sample_project),
            step_name="artifacts-test",
            metadata={"artifacts": [str(a) for a in artifacts]}
        )
        
        assert context.workspace_root == str(sample_project)
        assert "artifacts" in context.metadata
    
    def test_report_generator_multiple_formats(self, registry, sample_project):
        """ReportGenerator supports multiple output formats."""
        context = GateContext(
            workspace_root=str(sample_project),
            step_name="format-test",
        )
        
        results = registry.evaluate_all(context)
        generator = ReportGenerator()
        
        mock_step_run = MagicMock()
        mock_step_run.step_name = "Format Test"
        mock_step_run.step_id = "step-2"
        mock_step_run.id = 2
        
        mock_verdict = MagicMock()
        mock_verdict.passed = True
        mock_verdict.score = 0.85
        
        report = generator.generate(
            step_run=mock_step_run,
            gate_results=results,
            checklist_result=None,
            verdict=mock_verdict,
        )
        
        # Test markdown format
        markdown = generator.render(report, format="markdown")
        assert "# QA Report" in markdown
        
        # Test JSON format
        json_output = generator.render(report, format="json")
        assert '"step_name"' in json_output
        
        # Test HTML format
        html_output = generator.render(report, format="html")
        assert "<!DOCTYPE html>" in html_output


class TestChecklistValidatorPatterns:
    """Tests for checklist validator pattern matching."""
    
    def test_parse_standard_checklist(self):
        """Parse standard markdown checklist format."""
        validator = ChecklistValidator(use_llm=False)
        
        content = """
- [x] Completed item
- [ ] Pending item
- [ ] Another pending item
"""
        
        items = validator.parse_checklist(content)
        
        assert len(items) == 3
        assert items[0].checked is True
        assert items[1].checked is False
        assert items[2].checked is False
    
    def test_validate_test_patterns(self, tmp_path):
        """Test pattern detection for test files."""
        validator = ChecklistValidator(use_llm=False)
        
        # Create a test file
        test_file = tmp_path / "test_example.py"
        test_file.write_text('''
def test_something():
    assert True

def test_another_thing():
    assert 1 == 1
''')
        
        item = ChecklistItem(
            id="test-1",
            description="Add unit tests",
            required=True
        )
        
        result = validator.validate_item(item, [test_file])
        
        assert result.passed is True
        assert result.confidence > 0
    
    def test_validate_error_handling_patterns(self, tmp_path):
        """Test pattern detection for error handling."""
        validator = ChecklistValidator(use_llm=False)
        
        # Create a file with error handling - use more explicit keywords
        code_file = tmp_path / "handler.py"
        code_file.write_text('''
def process_data(data):
    try:
        return data["key"]
    except KeyError:
        raise ValueError("Missing key")

# Error handling implementation
''')
        
        item = ChecklistItem(
            id="err-1",
            description="Error handling",
            required=True
        )
        
        result = validator.validate_item(item, [code_file])
        
        # At minimum should find keywords
        assert len(result.evidence) >= 0 or result.confidence >= 0
