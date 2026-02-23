"""Tests for SimplicityGate (Article VII)."""

import pytest
from pathlib import Path

from devgodzilla.qa.gates.simplicity import (
    SimplicityGate,
    SimplicitySummaryGate,
    ComplexityAnalyzer,
)
from devgodzilla.qa.gates.interface import GateContext, GateVerdict


class TestComplexityAnalyzer:
    """Tests for ComplexityAnalyzer helper class."""

    def test_count_cyclomatic_complexity_python(self):
        code = '''
def complex_func(x):
    if x > 0:
        if x > 10:
            return "high"
        else:
            return "medium"
    elif x < 0:
        return "negative"
    else:
        return "zero"
'''
        complexity = ComplexityAnalyzer.count_cyclomatic_complexity(code, "python")
        # Base(1) + if(1) + if(1) + elif(1) = 4+
        assert complexity >= 4

    def test_count_cyclomatic_complexity_javascript(self):
        code = '''
function check(x) {
    if (x > 0) {
        if (x > 10) {
            return "high";
        }
    }
    return "low";
}
'''
        complexity = ComplexityAnalyzer.count_cyclomatic_complexity(code, "javascript")
        assert complexity >= 2

    def test_count_parameters_python(self):
        line = "def process_data(data, options, config, settings, params, extras, more_params):"
        count = ComplexityAnalyzer.count_parameters(line, "python")
        assert count == 7

    def test_count_parameters_python_with_self(self):
        line = "def method(self, a, b, c):"
        count = ComplexityAnalyzer.count_parameters(line, "python")
        assert count == 3  # self should be filtered

    def test_count_parameters_javascript(self):
        line = "function process(data, options, config) {"
        count = ComplexityAnalyzer.count_parameters(line, "javascript")
        assert count == 3


class TestSimplicityGate:
    @pytest.fixture
    def gate(self):
        return SimplicityGate()

    @pytest.fixture
    def complex_code(self, tmp_path):
        code = tmp_path / "complex.py"
        code.write_text('''
def process_data(data, options, config, settings, params, extras, more_params):
    """Function with too many parameters."""
    if data:
        if options:
            if config:
                if settings:
                    for item in data:
                        for sub in item:
                            if sub.value:
                                return sub.value
    return None
''')
        return GateContext(workspace_root=str(tmp_path))

    @pytest.fixture
    def simple_code(self, tmp_path):
        code = tmp_path / "simple.py"
        code.write_text('''
from dataclasses import dataclass

@dataclass
class DataConfig:
    data: list
    options: dict

def process_data(config: DataConfig) -> str:
    """Simple function with single parameter."""
    return config.data[0] if config.data else None
''')
        return GateContext(workspace_root=str(tmp_path))

    def test_gate_metadata(self, gate):
        assert gate.gate_id == "simplicity"
        assert "Article VII" in gate.gate_name

    def test_detects_too_many_parameters(self, gate, complex_code):
        result = gate.run(complex_code)
        assert any("parameter" in f.message.lower() for f in result.findings)

    def test_detects_deep_nesting(self, gate, complex_code):
        result = gate.run(complex_code)
        # Should detect deep nesting
        assert len(result.findings) > 0

    def test_passes_simple_code(self, gate, simple_code):
        result = gate.run(simple_code)
        assert result.verdict == GateVerdict.PASS

    def test_metadata_includes_thresholds(self, gate, complex_code):
        result = gate.run(complex_code)
        assert "thresholds" in result.metadata
        assert "max_cyclomatic_complexity" in result.metadata["thresholds"]

    def test_metadata_includes_article_info(self, gate, complex_code):
        result = gate.run(complex_code)
        assert result.metadata.get("article") == "VII"

    def test_custom_thresholds(self, tmp_path):
        gate = SimplicityGate(
            max_cyclomatic_complexity=20,
            max_function_length=100,
            max_parameters=10,
        )
        code = tmp_path / "code.py"
        code.write_text('def simple(): pass')
        result = gate.run(GateContext(workspace_root=str(tmp_path)))
        assert gate.max_cyclomatic_complexity == 20
        assert gate.max_function_length == 100
        assert gate.max_parameters == 10


class TestSimplicitySummaryGate:
    @pytest.fixture
    def gate(self):
        return SimplicitySummaryGate()

    @pytest.fixture
    def context_with_issues(self, tmp_path):
        code = tmp_path / "complex.py"
        code.write_text('''
def process(data, options, config, settings, params, extras, more_params, even_more):
    if data:
        if options:
            if config:
                if settings:
                    for item in data:
                        for sub in item:
                            if sub.value:
                                return sub.value
    return None
''')
        return GateContext(workspace_root=str(tmp_path))

    def test_gate_id(self, gate):
        assert gate.gate_id == "simplicity-summary"

    def test_non_blocking(self, gate):
        assert gate.blocking is False

    def test_summarizes_findings(self, gate, context_with_issues):
        result = gate.run(context_with_issues)
        assert "issues_by_type" in result.metadata
        assert "total_issues" in result.metadata
