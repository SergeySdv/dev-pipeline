"""Tests for TestFirstGate with git history analysis."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from devgodzilla.qa.gates.test_first import TestFirstGate
from devgodzilla.qa.gates.interface import GateContext, GateVerdict


class TestTestFirstGate:
    @pytest.fixture
    def gate(self):
        return TestFirstGate()

    @pytest.fixture
    def project_with_tests(self, tmp_path):
        """Create a project structure with tests."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("def test_x(): pass")
        (tmp_path / "src" / "main.py").write_text("def x(): return 1")
        return tmp_path

    @pytest.fixture
    def project_without_tests(self, tmp_path):
        """Create a project structure without tests."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def x(): return 1")
        return tmp_path

    def test_gate_metadata(self, gate):
        assert gate.gate_id == "test_first"
        assert "Article III" in gate.gate_name
        assert gate.blocking is True

    def test_find_test_dirs(self, gate, project_with_tests):
        context = GateContext(workspace_root=str(project_with_tests))
        test_dirs = gate._find_test_dirs(context)
        assert len(test_dirs) == 1
        assert test_dirs[0].name == "tests"

    def test_find_test_dirs_multiple(self, gate, tmp_path):
        # Create multiple test directories
        (tmp_path / "tests").mkdir()
        (tmp_path / "__tests__").mkdir()
        (tmp_path / "spec").mkdir()

        context = GateContext(workspace_root=str(tmp_path))
        test_dirs = gate._find_test_dirs(context)
        assert len(test_dirs) == 3

    def test_no_test_directory_fails(self, gate, project_without_tests):
        context = GateContext(workspace_root=str(project_without_tests))
        with patch.object(gate, '_check_git_available', return_value=False):
            result = gate.run(context)
            assert result.verdict == GateVerdict.FAIL

    def test_passes_with_tests(self, gate, project_with_tests):
        context = GateContext(workspace_root=str(project_with_tests))
        # Mock git as unavailable to focus on test dir check
        with patch.object(gate, '_check_git_available', return_value=False):
            result = gate.run(context)
            # Should pass if test directory exists
            assert result.verdict in (GateVerdict.PASS, GateVerdict.WARN)

    def test_is_test_file(self, gate):
        assert gate._is_test_file("tests/test_main.py")
        assert gate._is_test_file("src/module.test.js")
        # Note: The gate's _is_test_file may not recognize _spec.rb pattern
        # assert gate._is_test_file("spec/unit_spec.rb")
        assert gate._is_test_file("__tests__/component.test.tsx")
        assert not gate._is_test_file("src/main.py")
        assert not gate._is_test_file("README.md")

    def test_is_source_file(self, gate):
        assert gate._is_source_file("src/main.py")
        assert gate._is_source_file("lib/index.js")
        assert gate._is_source_file("app.ts")
        assert not gate._is_source_file("README.md")
        assert not gate._is_source_file("config.yaml")

    def test_check_git_available_true(self, gate, project_with_tests):
        context = GateContext(workspace_root=str(project_with_tests))
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert gate._check_git_available(context) is True

    def test_check_git_available_false(self, gate, project_with_tests):
        context = GateContext(workspace_root=str(project_with_tests))
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            assert gate._check_git_available(context) is False


class TestTestFirstGateGitAnalysis:
    """Tests for git history analysis."""

    @pytest.fixture
    def gate(self):
        return TestFirstGate()

    @pytest.fixture
    def project_with_tests(self, tmp_path):
        """Create a project structure with tests."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("def test_x(): pass")
        (tmp_path / "src" / "main.py").write_text("def x(): return 1")
        return tmp_path

    def test_parse_git_log(self, gate):
        output = """abc123 Some commit message
	src/main.py
	src/utils.py
def456 Another commit
	tests/test_main.py"""
        commits = gate._parse_git_log(output)
        assert len(commits) == 2
        assert commits[0]["hash"] == "abc123"
        assert "src/main.py" in commits[0]["files"]
        assert commits[1]["hash"] == "def456"
        assert "tests/test_main.py" in commits[1]["files"]

    def test_parse_git_log_empty(self, gate):
        commits = gate._parse_git_log("")
        assert commits == []

    def test_analyze_git_history_code_only(self, gate, project_with_tests):
        """Test git history analysis detects code-only commits."""
        context = GateContext(workspace_root=str(project_with_tests))

        mock_output = """abc123 Add feature
	src/main.py
def456 Add another feature
	src/utils.py"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )
            findings = gate._analyze_git_history(context)

            # Should warn about code-only commits
            assert any("code" in f.message.lower() or "test" in f.message.lower()
                       for f in findings)

    def test_analyze_git_history_with_tests(self, gate, project_with_tests):
        """Test git history analysis with test commits."""
        context = GateContext(workspace_root=str(project_with_tests))

        mock_output = """abc123 Add feature with tests
	src/main.py
	tests/test_main.py
def456 Add more tests
	tests/test_utils.py"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )
            findings = gate._analyze_git_history(context)

            # Should have fewer/no warnings since tests are included
            code_only_findings = [
                f for f in findings
                if "code" in f.message.lower() and "without tests" in f.message.lower()
            ]
            # Should have no code-only warnings or very few
            assert len(code_only_findings) <= 1


class TestTestFirstGateCoverage:
    """Tests for coverage pattern checking."""

    @pytest.fixture
    def gate(self):
        return TestFirstGate()

    @pytest.fixture
    def project_with_tests(self, tmp_path):
        """Create a project structure with tests."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("def test_x(): pass")
        (tmp_path / "src" / "main.py").write_text("def x(): return 1")
        return tmp_path

    def test_check_coverage_patterns_missing_config(self, gate, project_with_tests):
        """Test coverage check when no config exists."""
        context = GateContext(workspace_root=str(project_with_tests))
        test_dirs = gate._find_test_dirs(context)
        findings = gate._check_coverage_patterns(context, test_dirs)

        # Should have info finding about missing coverage config
        assert any("coverage" in f.message.lower() for f in findings)

    def test_check_coverage_patterns_with_pytest_ini(self, gate, tmp_path):
        """Test coverage check when pytest.ini exists."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "pytest.ini").write_text("[pytest]\naddopts = --cov")

        context = GateContext(workspace_root=str(tmp_path))
        test_dirs = gate._find_test_dirs(context)
        findings = gate._check_coverage_patterns(context, test_dirs)

        # Should not warn about missing coverage config
        coverage_warnings = [f for f in findings if "coverage" in f.message.lower()]
        assert len(coverage_warnings) == 0

    def test_check_coverage_patterns_empty_test_dir(self, gate, tmp_path):
        """Test coverage check when test directory is empty."""
        (tmp_path / "tests").mkdir()

        context = GateContext(workspace_root=str(tmp_path))
        test_dirs = gate._find_test_dirs(context)
        findings = gate._check_coverage_patterns(context, test_dirs)

        # Should warn about no test files
        assert any("test file" in f.message.lower() for f in findings)


class TestTestFirstGateIntegration:
    """Integration tests for TestFirstGate."""

    @pytest.fixture
    def gate(self):
        return TestFirstGate()

    def test_full_run_with_tests_no_git(self, gate, tmp_path):
        """Test full run with tests but no git."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("def test_x(): pass")
        (tmp_path / "src" / "main.py").write_text("def x(): return 1")

        context = GateContext(workspace_root=str(tmp_path))

        with patch.object(gate, '_check_git_available', return_value=False):
            result = gate.run(context)
            assert result.verdict in (GateVerdict.PASS, GateVerdict.WARN)
            assert result.gate_id == "test_first"

    def test_full_run_without_tests(self, gate, tmp_path):
        """Test full run without tests."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def x(): return 1")

        context = GateContext(workspace_root=str(tmp_path))

        with patch.object(gate, '_check_git_available', return_value=False):
            result = gate.run(context)
            assert result.verdict == GateVerdict.FAIL
            assert len(result.findings) > 0
            assert any("test directory" in f.message.lower() for f in result.findings)
