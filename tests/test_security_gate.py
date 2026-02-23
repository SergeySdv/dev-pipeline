"""Tests for SecurityGate."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from devgodzilla.qa.gates.security import (
    SecurityGate,
    SecurityFinding,
)
from devgodzilla.qa.gates.interface import GateContext, GateVerdict


class TestSecurityFinding:
    """Tests for SecurityFinding dataclass."""

    def test_security_finding_creation(self):
        """Test creating a security finding."""
        finding = SecurityFinding(
            issue_text="Use of eval() detected",
            severity="HIGH",
            confidence="HIGH",
            filename="app.py",
            lineno=42,
            test_id="B307",
            test_name="eval_used",
            code="eval(user_input)",
        )
        assert finding.issue_text == "Use of eval() detected"
        assert finding.severity == "HIGH"
        assert finding.confidence == "HIGH"
        assert finding.filename == "app.py"
        assert finding.lineno == 42
        assert finding.test_id == "B307"
        assert finding.test_name == "eval_used"
        assert finding.code == "eval(user_input)"

    def test_security_finding_optional_code(self):
        """Test finding without code snippet."""
        finding = SecurityFinding(
            issue_text="Issue without code",
            severity="LOW",
            confidence="MEDIUM",
            filename="test.py",
            lineno=1,
            test_id="B001",
            test_name="test_issue",
        )
        assert finding.code is None


class TestSecurityGateMetadata:
    """Tests for SecurityGate initialization and metadata."""

    @pytest.fixture
    def gate(self):
        return SecurityGate()

    def test_gate_id(self, gate):
        """Test gate ID is 'security'."""
        assert gate.gate_id == "security"

    def test_gate_name(self, gate):
        """Test gate name is descriptive."""
        assert gate.gate_name == "Security Gate"

    def test_default_settings(self, gate):
        """Test default settings are applied."""
        assert gate.fail_on_high is True
        assert gate.fail_on_medium is False
        assert ".venv" in gate.exclude_dirs
        assert "node_modules" in gate.exclude_dirs
        assert gate.timeout == 120

    def test_custom_settings(self):
        """Test custom settings are applied."""
        gate = SecurityGate(
            fail_on_high=False,
            fail_on_medium=True,
            exclude_dirs=["custom_dir", "tests"],
            timeout=60,
        )
        assert gate.fail_on_high is False
        assert gate.fail_on_medium is True
        assert "custom_dir" in gate.exclude_dirs
        assert gate.timeout == 60

    def test_class_constants(self):
        """Test class constants are defined."""
        assert SecurityGate.NAME == "security"
        assert "Security" in SecurityGate.DESCRIPTION


class TestSecurityGateBandit:
    """Tests for Bandit integration."""

    @pytest.fixture
    def gate(self):
        return SecurityGate()

    @pytest.fixture
    def python_workspace(self, tmp_path):
        """Create a workspace with Python files."""
        (tmp_path / "app.py").write_text("x = eval(input())")
        (tmp_path / "setup.py").write_text("# setup")
        return tmp_path

    @patch("subprocess.run")
    def test_run_bandit_success_no_issues(self, mock_run, gate, python_workspace):
        """Test bandit run with no issues found."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps({"results": []}),
            stderr="",
            returncode=0,
        )

        findings, error = gate._run_bandit(python_workspace)
        assert findings == []
        assert error is None

    @patch("subprocess.run")
    def test_run_bandit_with_findings(self, mock_run, gate, python_workspace):
        """Test bandit parsing findings from output."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps({
                "results": [
                    {
                        "issue_text": "Use of eval detected",
                        "issue_severity": "HIGH",
                        "issue_confidence": "HIGH",
                        "filename": "app.py",
                        "line_number": 1,
                        "test_id": "B307",
                        "test_name": "eval_used",
                        "code": "x = eval(input())",
                    }
                ]
            }),
            stderr="",
            returncode=1,
        )

        findings, error = gate._run_bandit(python_workspace)
        assert len(findings) == 1
        assert findings[0].issue_text == "Use of eval detected"
        assert findings[0].severity == "HIGH"
        assert error is None

    @patch("subprocess.run")
    def test_run_bandit_not_installed(self, mock_run, gate, python_workspace):
        """Test handling when bandit is not installed."""
        mock_run.side_effect = FileNotFoundError()

        findings, error = gate._run_bandit(python_workspace)
        assert findings == []
        assert "bandit not installed" in error

    @patch("subprocess.run")
    def test_run_bandit_timeout(self, mock_run, gate, python_workspace):
        """Test handling bandit timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="bandit", timeout=120)

        findings, error = gate._run_bandit(python_workspace)
        assert findings == []
        assert "timed out" in error

    @patch("subprocess.run")
    def test_run_bandit_invalid_json(self, mock_run, gate, python_workspace):
        """Test handling invalid JSON output."""
        mock_run.return_value = MagicMock(
            stdout="not valid json",
            stderr="",
            returncode=1,
        )

        findings, error = gate._run_bandit(python_workspace)
        assert findings == []
        assert "Failed to parse" in error

    @patch("subprocess.run")
    def test_run_bandit_excludes_dirs(self, mock_run, gate, python_workspace):
        """Test that bandit excludes configured directories."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps({"results": []}),
            stderr="",
            returncode=0,
        )

        gate._run_bandit(python_workspace)
        
        # Check that --exclude was passed with configured dirs
        call_args = mock_run.call_args[0][0]
        assert "--exclude" in call_args
        exclude_idx = call_args.index("--exclude")
        excludes = call_args[exclude_idx + 1]
        assert ".venv" in excludes


class TestSecurityGateNpmAudit:
    """Tests for npm audit integration."""

    @pytest.fixture
    def gate(self):
        return SecurityGate()

    @pytest.fixture
    def node_workspace(self, tmp_path):
        """Create a workspace with package.json."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        return tmp_path

    @patch("subprocess.run")
    def test_run_npm_audit_no_vulnerabilities(self, mock_run, gate, node_workspace):
        """Test npm audit with no vulnerabilities."""
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="",
            returncode=0,
        )

        findings, error = gate._run_npm_audit(node_workspace)
        assert findings == []
        assert error is None

    @patch("subprocess.run")
    def test_run_npm_audit_with_vulnerabilities(self, mock_run, gate, node_workspace):
        """Test npm audit parsing vulnerabilities."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps({
                "vulnerabilities": {
                    "lodash": {
                        "severity": "high",
                        "title": "Prototype Pollution",
                        "name": "lodash"
                    }
                }
            }),
            stderr="",
            returncode=1,
        )

        findings, error = gate._run_npm_audit(node_workspace)
        assert len(findings) == 1
        assert findings[0].severity == "HIGH"
        assert findings[0].issue_text == "Prototype Pollution"
        assert error is None

    @patch("subprocess.run")
    def test_run_npm_audit_not_installed(self, mock_run, gate, node_workspace):
        """Test handling when npm is not installed."""
        mock_run.side_effect = FileNotFoundError()

        findings, error = gate._run_npm_audit(node_workspace)
        assert findings == []
        assert "npm not installed" in error

    @patch("subprocess.run")
    def test_run_npm_audit_timeout(self, mock_run, gate, node_workspace):
        """Test handling npm audit timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="npm", timeout=120)

        findings, error = gate._run_npm_audit(node_workspace)
        assert findings == []
        assert "timed out" in error


class TestSecurityGateRun:
    """Tests for the full gate run method."""

    @pytest.fixture
    def gate(self):
        return SecurityGate()

    @pytest.fixture
    def empty_workspace(self, tmp_path):
        """Create an empty workspace."""
        return tmp_path

    @pytest.fixture
    def mixed_workspace(self, tmp_path):
        """Create a workspace with both Python and Node.js."""
        (tmp_path / "app.py").write_text("print('hello')")
        (tmp_path / "package.json").write_text('{"name": "test"}')
        return tmp_path

    @patch("subprocess.run")
    def test_run_empty_workspace_passes(self, mock_run, gate, empty_workspace):
        """Test empty workspace passes (no scanners run)."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        
        context = GateContext(workspace_root=str(empty_workspace))
        result = gate.run(context)
        
        assert result.verdict == GateVerdict.PASS
        assert "No security vulnerabilities found" in result.metadata["summary"]

    @patch("subprocess.run")
    def test_run_python_only(self, mock_run, gate, tmp_path):
        """Test running only Python scanner."""
        (tmp_path / "app.py").write_text("x = 1")
        
        mock_run.return_value = MagicMock(
            stdout=json.dumps({"results": []}),
            stderr="",
            returncode=0,
        )
        
        context = GateContext(workspace_root=str(tmp_path))
        result = gate.run(context)
        
        assert result.verdict == GateVerdict.PASS

    @patch("subprocess.run")
    def test_run_fails_on_high_severity(self, mock_run, gate, mixed_workspace):
        """Test gate fails when HIGH severity issues found."""
        # Bandit returns HIGH severity finding
        bandit_output = json.dumps({
            "results": [{
                "issue_text": "Critical issue",
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
                "filename": "app.py",
                "line_number": 1,
                "test_id": "B001",
                "test_name": "critical_test",
            }]
        })
        
        def mock_subprocess(*args, **kwargs):
            cmd = args[0] if args else kwargs.get('cmd', [])
            if 'bandit' in cmd:
                return MagicMock(stdout=bandit_output, stderr="", returncode=1)
            return MagicMock(stdout="", stderr="", returncode=0)
        
        mock_run.side_effect = mock_subprocess
        
        context = GateContext(workspace_root=str(mixed_workspace))
        result = gate.run(context)
        
        assert result.verdict == GateVerdict.FAIL
        assert result.metadata["high_count"] == 1

    @patch("subprocess.run")
    def test_run_passes_on_low_severity(self, mock_run, gate, mixed_workspace):
        """Test gate passes when only LOW severity issues found."""
        bandit_output = json.dumps({
            "results": [{
                "issue_text": "Low issue",
                "issue_severity": "LOW",
                "issue_confidence": "MEDIUM",
                "filename": "app.py",
                "line_number": 1,
                "test_id": "B001",
                "test_name": "low_test",
            }]
        })
        
        mock_run.return_value = MagicMock(
            stdout=bandit_output,
            stderr="",
            returncode=1,
        )
        
        context = GateContext(workspace_root=str(mixed_workspace))
        result = gate.run(context)
        
        assert result.verdict == GateVerdict.PASS
        assert result.metadata["low_count"] == 1

    @patch("subprocess.run")
    def test_run_fail_on_medium_when_configured(self, mock_run, tmp_path):
        """Test gate fails on MEDIUM when fail_on_medium=True."""
        (tmp_path / "app.py").write_text("x = 1")
        gate = SecurityGate(fail_on_medium=True)
        
        bandit_output = json.dumps({
            "results": [{
                "issue_text": "Medium issue",
                "issue_severity": "MEDIUM",
                "issue_confidence": "MEDIUM",
                "filename": "app.py",
                "line_number": 1,
                "test_id": "B001",
                "test_name": "medium_test",
            }]
        })
        
        mock_run.return_value = MagicMock(
            stdout=bandit_output,
            stderr="",
            returncode=1,
        )
        
        context = GateContext(workspace_root=str(tmp_path))
        result = gate.run(context)
        
        assert result.verdict == GateVerdict.FAIL
        assert result.metadata["medium_count"] == 1

    @patch("subprocess.run")
    def test_run_includes_findings(self, mock_run, gate, mixed_workspace):
        """Test findings are included in result."""
        bandit_output = json.dumps({
            "results": [{
                "issue_text": "Test issue",
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
                "filename": "app.py",
                "line_number": 10,
                "test_id": "B307",
                "test_name": "eval_used",
                "code": "eval(x)",
            }]
        })
        
        mock_run.return_value = MagicMock(
            stdout=bandit_output,
            stderr="",
            returncode=1,
        )
        
        context = GateContext(workspace_root=str(mixed_workspace))
        result = gate.run(context)
        
        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.gate_id == "security"
        assert finding.severity == "critical"
        assert finding.file_path == "app.py"
        assert finding.line_number == 10
        assert finding.rule_id == "B307"

    @patch("subprocess.run")
    def test_run_metadata_counts(self, mock_run, gate, mixed_workspace):
        """Test metadata includes severity counts."""
        bandit_output = json.dumps({
            "results": [
                {"issue_text": "High 1", "issue_severity": "HIGH", "issue_confidence": "HIGH",
                 "filename": "a.py", "line_number": 1, "test_id": "B001", "test_name": "t1"},
                {"issue_text": "High 2", "issue_severity": "HIGH", "issue_confidence": "HIGH",
                 "filename": "b.py", "line_number": 1, "test_id": "B002", "test_name": "t2"},
                {"issue_text": "Medium 1", "issue_severity": "MEDIUM", "issue_confidence": "MEDIUM",
                 "filename": "c.py", "line_number": 1, "test_id": "B003", "test_name": "t3"},
                {"issue_text": "Low 1", "issue_severity": "LOW", "issue_confidence": "LOW",
                 "filename": "d.py", "line_number": 1, "test_id": "B004", "test_name": "t4"},
            ]
        })
        
        mock_run.return_value = MagicMock(
            stdout=bandit_output,
            stderr="",
            returncode=1,
        )
        
        context = GateContext(workspace_root=str(mixed_workspace))
        result = gate.run(context)
        
        assert result.metadata["high_count"] == 2
        assert result.metadata["medium_count"] == 1
        assert result.metadata["low_count"] == 1


class TestSecurityGateEvaluate:
    """Tests for the legacy evaluate method."""

    @pytest.fixture
    def gate(self):
        return SecurityGate()

    @patch("subprocess.run")
    def test_evaluate_wrapper(self, mock_run, gate, tmp_path):
        """Test evaluate() wraps run() correctly."""
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        
        result = gate.evaluate(
            workspace=str(tmp_path),
            step_name="test-step",
            context={"custom": "value"},
        )
        
        assert result.gate_id == "security"


class TestSecurityGateFindingConversion:
    """Tests for finding conversion to QA Finding."""

    @pytest.fixture
    def gate(self):
        return SecurityGate()

    def test_finding_to_result_high_severity(self, gate):
        """Test HIGH severity maps to critical."""
        security_finding = SecurityFinding(
            issue_text="Critical issue",
            severity="HIGH",
            confidence="HIGH",
            filename="app.py",
            lineno=42,
            test_id="B307",
            test_name="eval_used",
        )
        
        result = gate._finding_to_result(security_finding)
        
        assert result.severity == "critical"
        assert result.message == "Critical issue"
        assert result.file_path == "app.py"
        assert result.line_number == 42
        assert result.rule_id == "B307"

    def test_finding_to_result_medium_severity(self, gate):
        """Test MEDIUM severity maps to warning."""
        security_finding = SecurityFinding(
            issue_text="Warning issue",
            severity="MEDIUM",
            confidence="MEDIUM",
            filename="app.py",
            lineno=10,
            test_id="B001",
            test_name="test",
        )
        
        result = gate._finding_to_result(security_finding)
        
        assert result.severity == "warning"

    def test_finding_to_result_low_severity(self, gate):
        """Test LOW severity maps to info."""
        security_finding = SecurityFinding(
            issue_text="Info issue",
            severity="LOW",
            confidence="LOW",
            filename="app.py",
            lineno=5,
            test_id="B002",
            test_name="test",
        )
        
        result = gate._finding_to_result(security_finding)
        
        assert result.severity == "info"

    def test_finding_to_result_includes_metadata(self, gate):
        """Test finding includes confidence and code in metadata."""
        security_finding = SecurityFinding(
            issue_text="Issue with code",
            severity="HIGH",
            confidence="HIGH",
            filename="app.py",
            lineno=1,
            test_id="B307",
            test_name="eval_used",
            code="eval(x)",
        )
        
        result = gate._finding_to_result(security_finding)
        
        assert result.metadata["confidence"] == "HIGH"
        assert result.metadata["test_name"] == "eval_used"
        assert result.metadata["code"] == "eval(x)"
